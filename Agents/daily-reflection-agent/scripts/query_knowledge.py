from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the local RAG knowledge index.")
    parser.add_argument("query", help="Question or daily-note text to retrieve context for.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to return.")
    args = parser.parse_args()

    chunks = retrieve(args.query, top_k=args.top_k)
    if not chunks:
        print("No chunks found. Run: python scripts/index_knowledge.py")
        return

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n[{index}] {chunk.source} - {chunk.heading} (score: {chunk.score:.2f})")
        print(chunk.text[:700])


if __name__ == "__main__":
    main()
