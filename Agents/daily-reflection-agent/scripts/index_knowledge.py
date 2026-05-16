from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag import KNOWLEDGE_DIR, build_index, save_index


def main() -> None:
    if not KNOWLEDGE_DIR.exists():
        raise SystemExit(f"Knowledge folder not found: {KNOWLEDGE_DIR}")

    index = build_index(KNOWLEDGE_DIR)
    output_path = save_index(index)
    print(f"Indexed {index['document_count']} chunks from {KNOWLEDGE_DIR}")
    print(f"Saved RAG index to {output_path}")


if __name__ == "__main__":
    main()
