from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import KNOWLEDGE_DIR
from vector_rag import DEFAULT_EMBEDDING_MODEL, build_vector_index, save_vector_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local vector index from knowledge notes.")
    parser.add_argument("--model", default=DEFAULT_EMBEDDING_MODEL, help="LM Studio embedding model id.")
    args = parser.parse_args()

    if not KNOWLEDGE_DIR.exists():
        raise SystemExit(f"Knowledge folder not found: {KNOWLEDGE_DIR}")

    index = build_vector_index(KNOWLEDGE_DIR, model=args.model)
    output_path = save_vector_index(index)
    print(f"Embedded {index['document_count']} chunks from {KNOWLEDGE_DIR}")
    print(f"Embedding model: {index['model']}")
    print(f"Saved vector index to {output_path}")


if __name__ == "__main__":
    main()
