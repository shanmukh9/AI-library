import argparse

from runbook_rag import (
    DEFAULT_MIN_SCORE,
    expand_query_for_retrieval,
    format_evidence,
    load_runbook_index,
    search_runbooks,
    select_candidate_chunks,
)


parser = argparse.ArgumentParser(description="Query the local runbook index.")
parser.add_argument(
    "query",
    nargs="*",
    help="Operational alert text.",
)
parser.add_argument("--platform", help="Optional exact platform metadata filter.")
parser.add_argument("--category", help="Optional exact category metadata filter.")
parser.add_argument(
    "--metadata-mode",
    choices=["strict", "fallback"],
    default="fallback",
    help="Fallback retries all chunks when metadata finds no candidates.",
)
parser.add_argument(
    "--ranking",
    choices=["vector", "reranked"],
    default="vector",
    help="Optionally rerank vector results using detected query intent.",
)
args = parser.parse_args()

query = " ".join(args.query).strip()
if not query:
    query = "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"

expanded_query = expand_query_for_retrieval(query)
metadata_filters = {
    field: value
    for field, value in {
        "platform": args.platform,
        "category": args.category,
    }.items()
    if value
}
index = load_runbook_index()
candidate_chunks, fallback_used = select_candidate_chunks(
    index["chunks"],
    metadata_filters=metadata_filters,
    fallback_on_empty=args.metadata_mode == "fallback",
)
results = search_runbooks(
    query,
    top_k=3,
    min_score=DEFAULT_MIN_SCORE,
    metadata_filters=metadata_filters,
    metadata_fallback=args.metadata_mode == "fallback",
    use_reranking=args.ranking == "reranked",
)
fallback_used = bool(results and results[0].get("metadata_fallback_used"))
if fallback_used:
    candidate_chunks = index["chunks"]

print(f"Query: {query}")
if expanded_query != query:
    print(f"Expanded query: {expanded_query}")
if metadata_filters:
    rendered_filters = ", ".join(
        f"{field}={value}" for field, value in metadata_filters.items()
    )
    print(f"Metadata filters: {rendered_filters}")
    print(f"Metadata mode: {args.metadata_mode}")
    print(f"Metadata fallback used: {'yes' if fallback_used else 'no'}")
print(f"Candidate chunks: {len(candidate_chunks)}/{len(index['chunks'])}")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print(f"Ranking mode: {args.ranking}")
print()
print(format_evidence(results))
