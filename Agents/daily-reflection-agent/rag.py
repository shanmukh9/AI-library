from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
KNOWLEDGE_DIR = ROOT / "knowledge"
RAG_INDEX_PATH = ROOT / "data" / "rag_index.json"

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
    "you",
    "your",
}

DOMAIN_BOOSTS = {
    "career": {"ai", "agent", "agents", "build", "building", "project", "career", "code", "github", "rag"},
    "health": {"health", "fitness", "workout", "walk", "gym", "energy", "body", "sleep", "diet"},
    "mental": {"mental", "emotion", "confidence", "comfort", "zone", "stress", "anxiety", "burnout"},
    "communication": {"communication", "speak", "speaking", "message", "relationship", "soft", "skills"},
}


@dataclass
class RetrievedChunk:
    source: str
    heading: str
    text: str
    score: float


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
    return [word for word in words if word not in STOP_WORDS and len(word) > 2]


def split_markdown(text: str, max_words: int = 180, overlap: int = 35) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    heading = "General"
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        words = " ".join(buffer).split()
        start = 0
        while start < len(words):
            slice_words = words[start : start + max_words]
            if slice_words:
                chunks.append((heading, " ".join(slice_words)))
            if start + max_words >= len(words):
                break
            start += max_words - overlap
        buffer = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            heading = stripped.lstrip("#").strip() or "General"
            continue
        if stripped:
            buffer.append(stripped)
    flush()
    return chunks


def build_index(knowledge_dir: Path = KNOWLEDGE_DIR) -> dict:
    documents = []
    for path in sorted(knowledge_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        for index, (heading, chunk_text) in enumerate(split_markdown(content)):
            tokens = tokenize(chunk_text)
            documents.append(
                {
                    "id": f"{path.stem}:{index}",
                    "source": path.name,
                    "heading": heading,
                    "text": chunk_text,
                    "tokens": tokens,
                    "term_counts": dict(Counter(tokens)),
                }
            )

    document_count = len(documents)
    doc_freq: Counter[str] = Counter()
    for doc in documents:
        doc_freq.update(set(doc["tokens"]))

    idf = {
        term: math.log((1 + document_count) / (1 + freq)) + 1
        for term, freq in doc_freq.items()
    }
    return {"version": 1, "document_count": document_count, "documents": documents, "idf": idf}


def save_index(index: dict, output_path: Path = RAG_INDEX_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return output_path


def load_index(index_path: Path = RAG_INDEX_PATH) -> dict:
    if not index_path.exists():
        return {}
    return json.loads(index_path.read_text(encoding="utf-8"))


def retrieve(query: str, top_k: int = 3, index_path: Path = RAG_INDEX_PATH) -> list[RetrievedChunk]:
    index = load_index(index_path)
    documents = index.get("documents", [])
    if not documents:
        return []

    idf = index.get("idf", {})
    query_terms = Counter(tokenize(query))
    if not query_terms:
        return []
    query_term_set = set(query_terms)

    scored: list[RetrievedChunk] = []
    for doc in documents:
        term_counts = doc.get("term_counts", {})
        heading_terms = set(tokenize(doc.get("heading", "")))
        score = 0.0
        for term, query_count in query_terms.items():
            if term in term_counts:
                score += query_count * term_counts[term] * float(idf.get(term, 1.0))
            if term in heading_terms:
                score += query_count * 2.5

        for domain, terms in DOMAIN_BOOSTS.items():
            if query_term_set & terms and heading_terms & terms:
                score += 6.0
            elif query_term_set & terms and domain in " ".join(heading_terms):
                score += 4.0
        if score > 0:
            scored.append(
                RetrievedChunk(
                    source=doc["source"],
                    heading=doc["heading"],
                    text=doc["text"],
                    score=score,
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""

    lines = ["Relevant personal knowledge:"]
    for index, chunk in enumerate(chunks, start=1):
        lines.append(
            f"\n[{index}] {chunk.source} - {chunk.heading}\n"
            f"{chunk.text}"
        )
    return "\n".join(lines)
