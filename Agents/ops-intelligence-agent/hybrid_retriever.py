from bm25_retriever import bm25_search
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


def build_hybrid_retrieval_query(query):
    return normalize_operational_signals(expand_query_for_retrieval(query))


def should_run_hybrid_retrieval(query):
    return has_operational_problem_signal(build_hybrid_retrieval_query(query))


def hybrid_search_rrf(
    query,
    top_k=3,
    candidate_k=5,
    rrf_k=60,
    vector_min_score=DEFAULT_MIN_SCORE,
):
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
