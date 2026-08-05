from bm25_retriever import bm25_search
from evidence_acceptance import detect_supported_incident_sources
from runbook_rag import (
    DEFAULT_MIN_SCORE,
    expand_query_for_retrieval,
    has_operational_problem_signal,
    normalize_operational_signals,
    search_runbooks,
)


def chunk_key(result):
    return f"{result['source']}::{result['section']}"


def reciprocal_rank(rank, k=60):
    return 1 / (k + rank)


def rank_candidates_by_source(ranked_chunks, top_k, score_chunk_limit=3):
    grouped = {}
    for rank, chunk in enumerate(ranked_chunks, start=1):
        source_group = grouped.setdefault(
            chunk["source"],
            {
                "chunks": [],
                "first_chunk_rank": rank,
            },
        )
        source_group["chunks"].append(chunk)

    source_candidates = []
    for source_group in grouped.values():
        supporting_chunks = source_group["chunks"][:score_chunk_limit]
        representative = dict(source_group["chunks"][0])
        representative["source_rrf_score"] = sum(
            chunk["rrf_score"] for chunk in supporting_chunks
        )
        representative["source_supporting_chunks"] = len(supporting_chunks)
        representative["source_supporting_sections"] = [
            chunk["section"] for chunk in supporting_chunks
        ]
        representative["source_first_chunk_rank"] = source_group["first_chunk_rank"]
        source_candidates.append(representative)

    source_candidates.sort(
        key=lambda item: (
            item["source_rrf_score"],
            item["source_supporting_chunks"],
            -item["source_first_chunk_rank"],
        ),
        reverse=True,
    )
    return source_candidates[:top_k]


def build_hybrid_retrieval_query(query):
    return normalize_operational_signals(expand_query_for_retrieval(query))


def should_run_hybrid_retrieval(query):
    return has_operational_problem_signal(build_hybrid_retrieval_query(query))


def resolve_hybrid_ranking_mode(query, ranking_mode):
    if ranking_mode == "conditional":
        detected_sources = detect_supported_incident_sources(query)
        return "source" if len(detected_sources) >= 2 else "chunk"
    if ranking_mode == "adaptive":
        return "chunk"
    return ranking_mode


def annotate_adaptive_results(
    results,
    *,
    retry_used,
    initial_sources,
    missing_sources,
    resolved_ranking_mode,
):
    annotated = []
    for result in results:
        item = dict(result)
        item["adaptive_retry_used"] = retry_used
        item["adaptive_initial_sources"] = sorted(initial_sources)
        item["adaptive_missing_sources"] = sorted(missing_sources)
        item["resolved_ranking_mode"] = resolved_ranking_mode
        annotated.append(item)
    return annotated


def hybrid_search_rrf(
    query,
    top_k=3,
    candidate_k=5,
    rrf_k=60,
    vector_min_score=DEFAULT_MIN_SCORE,
    ranking_mode="chunk",
):
    if ranking_mode not in {"chunk", "source", "conditional", "adaptive"}:
        raise ValueError(f"Unsupported hybrid ranking mode: {ranking_mode}")

    if ranking_mode == "adaptive":
        detected_sources = set(detect_supported_incident_sources(query))
        initial_results = hybrid_search_rrf(
            query,
            top_k=top_k,
            candidate_k=candidate_k,
            rrf_k=rrf_k,
            vector_min_score=vector_min_score,
            ranking_mode="chunk",
        )
        initial_sources = {result["source"] for result in initial_results}
        missing_sources = detected_sources.difference(initial_sources)
        retry_used = len(detected_sources) >= 2 and bool(missing_sources)

        if retry_used:
            retry_results = hybrid_search_rrf(
                query,
                top_k=top_k,
                candidate_k=max(candidate_k, 10),
                rrf_k=rrf_k,
                vector_min_score=vector_min_score,
                ranking_mode="source",
            )
            return annotate_adaptive_results(
                retry_results,
                retry_used=True,
                initial_sources=initial_sources,
                missing_sources=missing_sources,
                resolved_ranking_mode="source",
            )

        return annotate_adaptive_results(
            initial_results,
            retry_used=False,
            initial_sources=initial_sources,
            missing_sources=missing_sources,
            resolved_ranking_mode="chunk",
        )

    resolved_ranking_mode = resolve_hybrid_ranking_mode(query, ranking_mode)
    retrieval_query = build_hybrid_retrieval_query(query)
    if not has_operational_problem_signal(retrieval_query):
        return []

    vector_results = search_runbooks(
        query,
        top_k=candidate_k,
        min_score=vector_min_score,
        use_expansion=True,
        use_reranking=True,
        reranking_query=query,
    )
    bm25_results = bm25_search(retrieval_query, top_k=candidate_k)
    fused = {}

    for rank, result in enumerate(vector_results, start=1):
        key = chunk_key(result)
        fused[key] = {
            "source": result["source"],
            "runbook": result["runbook"],
            "section": result["section"],
            "text": result["text"],
            "metadata": result.get("metadata", {}),
            "retrieved_by": ["vector"],
            "vector_rank": rank,
            "bm25_rank": None,
            "vector_score": result.get("similarity_score", result["score"]),
            "bm25_score": None,
            "rrf_score": reciprocal_rank(rank, rrf_k),
        }

    for rank, result in enumerate(bm25_results, start=1):
        key = chunk_key(result)
        if key not in fused:
            fused[key] = {
                "source": result["source"],
                "runbook": result["runbook"],
                "section": result["section"],
                "text": result["text"],
                "metadata": result.get("metadata", {}),
                "retrieved_by": ["bm25"],
                "vector_rank": None,
                "bm25_rank": rank,
                "vector_score": None,
                "bm25_score": result["score"],
                "rrf_score": reciprocal_rank(rank, rrf_k),
            }
        else:
            fused[key]["retrieved_by"].append("bm25")
            fused[key]["bm25_rank"] = rank
            fused[key]["bm25_score"] = result["score"]
            fused[key]["rrf_score"] += reciprocal_rank(rank, rrf_k)

    ranked = sorted(
        fused.values(),
        key=lambda item: (
            item["rrf_score"],
            len(item["retrieved_by"]),
            -(item["vector_rank"] or 999),
            -(item["bm25_rank"] or 999),
        ),
        reverse=True,
    )
    if resolved_ranking_mode == "source":
        return rank_candidates_by_source(ranked, top_k=top_k)
    return ranked[:top_k]


def format_hybrid_evidence(results):
    if not results:
        return "No accepted runbook evidence."

    formatted = []
    for index, result in enumerate(results, start=1):
        vector_score = (
            f"{result['vector_score']:.4f}"
            if result["vector_score"] is not None
            else "none"
        )
        bm25_score = (
            f"{result['bm25_score']:.4f}"
            if result["bm25_score"] is not None
            else "none"
        )
        formatted.append(
            "\n".join(
                [
                    f"[{index}] {result['runbook']} / {result['section']}",
                    f"source: {result['source']}",
                    (
                        "metadata: "
                        f"platform={result['metadata'].get('platform', 'unknown')}, "
                        f"category={result['metadata'].get('category', 'unknown')}"
                    ),
                    f"retrieved_by: {', '.join(result['retrieved_by'])}",
                    (
                        f"scores: rrf={result['rrf_score']:.5f}, "
                        f"vector={vector_score}, bm25={bm25_score}"
                    ),
                    result["text"],
                ]
            )
        )
    return "\n\n".join(formatted)
