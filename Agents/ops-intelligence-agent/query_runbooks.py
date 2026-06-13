import sys

from runbook_rag import (
    DEFAULT_MIN_SCORE,
    expand_query_for_retrieval,
    format_evidence,
    search_runbooks,
)


query = " ".join(sys.argv[1:]).strip()
if not query:
    query = "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"

expanded_query = expand_query_for_retrieval(query)
results = search_runbooks(query, top_k=3, min_score=DEFAULT_MIN_SCORE)

print(f"Query: {query}")
if expanded_query != query:
    print(f"Expanded query: {expanded_query}")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print()
print(format_evidence(results))
