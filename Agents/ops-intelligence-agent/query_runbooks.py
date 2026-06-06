import sys

from runbook_rag import DEFAULT_MIN_SCORE, format_evidence, search_runbooks


query = " ".join(sys.argv[1:]).strip()
if not query:
    query = "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"

results = search_runbooks(query, top_k=3, min_score=DEFAULT_MIN_SCORE)

print(f"Query: {query}")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print()
print(format_evidence(results))
