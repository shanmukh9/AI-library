from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vector_rag import retrieve_vector


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the local vector RAG index.")
    parser.add_argument("query", help="Question or daily-note text to retrieve context for.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to return.")
    args = parser.parse_args()

    chunks = retrieve_vector(args.query, top_k=args.top_k)
    if not chunks:
        print("No vector chunks found. Run: python scripts/index_knowledge_vectors.py")
        return

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n[{index}] {chunk.source} - {chunk.heading} (similarity: {chunk.score:.4f})")
        print(chunk.text[:700])


if __name__ == "__main__":
    main()
