import argparse

from bm25_retriever import bm25_search
from runbook_rag import load_runbook_index


parser = argparse.ArgumentParser(description="Query runbooks with BM25 lexical search.")
parser.add_argument("query", nargs="*", help="Operational alert text.")
parser.add_argument("--top-k", type=int, default=3)
parser.add_argument("--min-score", type=float, default=0.0)
args = parser.parse_args()

query = " ".join(args.query).strip()
if not query:
    query = "checkout HTTP 504 gateway timeout"

index = load_runbook_index()
results = bm25_search(query, top_k=args.top_k, min_score=args.min_score)

print(f"Query: {query}")
print(f"Runbook chunks: {len(index['chunks'])}")
print(f"Ranking mode: BM25 lexical search")
print()

if not results:
    print("No BM25 results.")
else:
    for rank, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        print(f"[{rank}] {result['runbook']} / {result['section']}")
        print(f"source: {result['source']}")
        print(
            "metadata: "
            f"platform={metadata.get('platform', 'unknown')}, "
            f"category={metadata.get('category', 'unknown')}"
        )
        print(f"bm25 score: {result['score']:.4f}")
        print(f"matched terms: {', '.join(result['matched_terms'])}")
        print(result["text"])
        print()
