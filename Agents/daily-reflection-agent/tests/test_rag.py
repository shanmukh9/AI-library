from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rag import build_index, retrieve, save_index, split_markdown
from vector_rag import cosine_similarity


class RagTests(unittest.TestCase):
    def test_split_markdown_preserves_headings(self) -> None:
        chunks = split_markdown(
            "# Career\nBuild one AI artifact.\n\n# Fitness\nTake a short walk.",
            max_words=20,
            overlap=2,
        )

        self.assertEqual(chunks[0][0], "Career")
        self.assertEqual(chunks[1][0], "Fitness")

    def test_keyword_retrieval_finds_relevant_heading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            knowledge = root / "knowledge"
            knowledge.mkdir()
            (knowledge / "profile.md").write_text(
                "# AI Career\nBuild a visible AI project artifact before watching another course.\n\n"
                "# Fitness\nProtect energy with a short walk and mobility routine.\n",
                encoding="utf-8",
            )
            index_path = root / "rag_index.json"
            save_index(build_index(knowledge), index_path)

            chunks = retrieve("I watched an AI course but avoided building", top_k=1, index_path=index_path)

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].heading, "AI Career")

    def test_cosine_similarity_distinguishes_vectors(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)
        self.assertEqual(cosine_similarity([], []), 0.0)


if __name__ == "__main__":
    unittest.main()
