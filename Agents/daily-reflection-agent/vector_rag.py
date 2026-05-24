from __future__ import annotations

import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from rag import KNOWLEDGE_DIR, RetrievedChunk, split_markdown


ROOT = Path(__file__).parent.resolve()
VECTOR_INDEX_PATH = ROOT / "data" / "vector_index.json"
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_EMBEDDINGS_URL = f"{LM_STUDIO_BASE_URL}/embeddings"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"


@dataclass
class VectorDocument:
    source: str
    heading: str
    text: str
    embedding: list[float]


def call_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> list[float]:
    payload = {"model": model, "input": text}
    request = urllib.request.Request(
        LM_STUDIO_EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode("utf-8"))
    return [float(value) for value in body["data"][0]["embedding"]]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def build_vector_index(
    knowledge_dir: Path = KNOWLEDGE_DIR,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> dict:
    documents = []
    for path in sorted(knowledge_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        for index, (heading, chunk_text) in enumerate(split_markdown(content)):
            embedding_input = f"{heading}\n\n{chunk_text}"
            documents.append(
                {
                    "id": f"{path.stem}:{index}",
                    "source": path.name,
                    "heading": heading,
                    "text": chunk_text,
                    "embedding": call_embedding(embedding_input, model=model),
                }
            )

    return {
        "version": 1,
        "model": model,
        "document_count": len(documents),
        "documents": documents,
    }


def save_vector_index(index: dict, output_path: Path = VECTOR_INDEX_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index), encoding="utf-8")
    return output_path


def load_vector_index(index_path: Path = VECTOR_INDEX_PATH) -> dict:
    if not index_path.exists():
        return {}
    return json.loads(index_path.read_text(encoding="utf-8"))


def retrieve_vector(
    query: str,
    top_k: int = 3,
    index_path: Path = VECTOR_INDEX_PATH,
) -> list[RetrievedChunk]:
    index = load_vector_index(index_path)
    documents = index.get("documents", [])
    if not documents:
        raise RuntimeError(
            f"Vector index not found or empty: {index_path}. "
            "Run: python scripts/index_knowledge_vectors.py"
        )

    query_embedding = call_embedding(query, model=index.get("model", DEFAULT_EMBEDDING_MODEL))
    scored = []
    for doc in documents:
        score = cosine_similarity(query_embedding, doc.get("embedding", []))
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
