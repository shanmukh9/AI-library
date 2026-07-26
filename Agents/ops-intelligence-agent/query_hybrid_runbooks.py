import argparse

from hybrid_retriever import hybrid_search_rrf


parser = argparse.ArgumentParser(description="Query runbooks with hybrid RRF retrieval.")
parser.add_argument("query", nargs="*", help="Operational alert text.")
parser.add_argument("--top-k", type=int, default=3)
parser.add_argument("--candidate-k", type=int, default=5)
parser.add_argument(
    "--ranking-mode",
    choices=("chunk", "source"),
    default="chunk",
)
args = parser.parse_args()

query = " ".join(args.query).strip()
if not query:
    query = "checkout HTTP 504 gateway timeout"

results = hybrid_search_rrf(
    query,
    top_k=args.top_k,
    candidate_k=args.candidate_k,
    ranking_mode=args.ranking_mode,
)

print(f"Query: {query}")
print(f"Ranking mode: Hybrid RRF ({args.ranking_mode})")
print(f"Candidate depth per retriever: {args.candidate_k}")
print()

if not results:
    print("No hybrid evidence.")
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
        print(f"retrieved_by: {', '.join(result['retrieved_by'])}")
        print(
            "ranks: "
            f"vector={result['vector_rank'] or '-'}, "
            f"bm25={result['bm25_rank'] or '-'}"
        )
        vector_score = (
            f"{result['vector_score']:.4f}"
            if result["vector_score"] is not None
            else "-"
        )
        bm25_score = (
            f"{result['bm25_score']:.4f}"
            if result["bm25_score"] is not None
            else "-"
        )
        print(
            "scores: "
            f"rrf={result['rrf_score']:.5f}, "
            f"vector={vector_score}, "
            f"bm25={bm25_score}"
        )
        if args.ranking_mode == "source":
            print(
                "source aggregation: "
                f"score={result['source_rrf_score']:.5f}, "
                f"chunks={result['source_supporting_chunks']}, "
                f"sections={result['source_supporting_sections']}"
            )
        print(result["text"])
        print()
