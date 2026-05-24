from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import retrieve
from vector_rag import retrieve_vector


DEFAULT_CASES_PATH = ROOT / "evals" / "rag_eval_cases.json"


def load_cases(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Eval cases file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def retrieve_for_mode(query: str, top_k: int, mode: str):
    if mode == "keyword":
        return retrieve(query, top_k=top_k)
    if mode == "vector":
        return retrieve_vector(query, top_k=top_k)
    raise ValueError(f"Unsupported RAG mode: {mode}")


def evaluate_case(case: dict, top_k: int, mode: str) -> dict:
    retrieved = retrieve_for_mode(case["query"], top_k=top_k, mode=mode)
    retrieved_headings = [chunk.heading for chunk in retrieved]
    expected_headings = case.get("expected_headings", [])
    hits = [heading for heading in retrieved_headings if heading in expected_headings]

    return {
        "name": case["name"],
        "mode": mode,
        "query": case["query"],
        "passed": bool(hits),
        "hits": hits,
        "expected_headings": expected_headings,
        "retrieved": [
            {
                "rank": index + 1,
                "heading": chunk.heading,
                "source": chunk.source,
                "score": round(chunk.score, 2),
            }
            for index, chunk in enumerate(retrieved)
        ],
    }


def print_result(result: dict) -> None:
    status = "PASS" if result["passed"] else "FAIL"
    print(f"\n[{status}] {result['name']} ({result['mode']})")
    print(f"Query: {result['query']}")
    print(f"Expected any of: {', '.join(result['expected_headings'])}")
    print("Retrieved:")
    for item in result["retrieved"]:
        marker = "*" if item["heading"] in result["expected_headings"] else " "
        print(
            f"  {marker} {item['rank']}. {item['heading']} "
            f"({item['source']}, score={item['score']})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate local RAG retrieval quality.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to eval cases JSON.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of retrieved chunks to evaluate.")
    parser.add_argument("--mode", choices=["keyword", "vector"], default="keyword", help="Retriever to evaluate.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    args = parser.parse_args()

    cases = load_cases(Path(args.cases))
    results = [evaluate_case(case, top_k=args.top_k, mode=args.mode) for case in cases]
    passed = sum(1 for result in results if result["passed"])
    total = len(results)

    if args.json:
        print(json.dumps({"passed": passed, "total": total, "results": results}, indent=2))
        return

    for result in results:
        print_result(result)

    print("\nSummary")
    print(f"Passed: {passed}/{total}")
    print(f"Hit rate: {(passed / total * 100) if total else 0:.1f}%")


if __name__ == "__main__":
    main()
