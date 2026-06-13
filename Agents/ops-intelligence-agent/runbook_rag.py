import json
import math
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
RUNBOOK_DIR = PROJECT_ROOT / "runbooks"
INDEX_PATH = PROJECT_ROOT / "data" / "runbook_index.json"
EMBEDDINGS_URL = "http://127.0.0.1:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_MIN_SCORE = 0.60

OPERATIONAL_PROBLEM_SIGNALS = [
    "timeout",
    "failed",
    "failure",
    "error",
    "exceeded",
    "high",
    "crash",
    "crashloop",
    "oomkilled",
    "502",
    "latency",
    "exhausted",
    "denied",
    "unhealthy",
    "expiring",
    "expires",
]

QUERY_EXPANSION_RULES = [
    {
        "triggers": ["memory killed", "pod memory killed"],
        "expansion": "OOMKilled pod crash-looping memory limit exceeded",
    },
    {
        "triggers": ["cpu hot", "server hot", "api hot"],
        "expansion": "high CPU usage exceeded 95 percent saturation",
    },
]


def has_operational_problem_signal(query):
    normalized_query = query.lower()
    return any(signal in normalized_query for signal in OPERATIONAL_PROBLEM_SIGNALS)


def expand_query_for_retrieval(query):
    normalized_query = query.lower()
    expansions = [
        rule["expansion"]
        for rule in QUERY_EXPANSION_RULES
        if any(trigger in normalized_query for trigger in rule["triggers"])
    ]
    if not expansions:
        return query
    return " ".join([query, *expansions])


def embed_text(text):
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }
    request = urllib.request.Request(
        EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach LM Studio embeddings endpoint. "
            "Start LM Studio and load the embedding model."
        ) from exc
    return [float(value) for value in body["data"][0]["embedding"]]


def cosine_similarity(left, right):
    dot_product = sum(a * b for a, b in zip(left, right))
    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0
    return dot_product / (left_magnitude * right_magnitude)


def split_runbook_sections(markdown_text):
    sections = []
    current_title = "Overview"
    current_lines = []

    for line in markdown_text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.removeprefix("## ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [(title, content) for title, content in sections if content]


def load_runbook_chunks(runbook_dir=RUNBOOK_DIR):
    chunks = []
    for path in sorted(runbook_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].removeprefix("# ").strip()
        for section_title, section_text in split_runbook_sections(text):
            chunks.append(
                {
                    "id": f"{path.stem}:{section_title.lower().replace(' ', '-')}",
                    "source": path.name,
                    "runbook": title,
                    "section": section_title,
                    "text": section_text,
                }
            )
    return chunks


def build_runbook_index(runbook_dir=RUNBOOK_DIR, index_path=INDEX_PATH):
    chunks = load_runbook_chunks(runbook_dir)
    if not chunks:
        raise RuntimeError(f"No runbook markdown files found in {runbook_dir}")

    indexed_chunks = []
    for chunk in chunks:
        indexed_chunks.append({**chunk, "embedding": embed_text(chunk["text"])})

    index = {
        "embedding_model": EMBEDDING_MODEL,
        "chunk_count": len(indexed_chunks),
        "chunks": indexed_chunks,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def load_runbook_index(index_path=INDEX_PATH):
    if not index_path.exists():
        raise FileNotFoundError(
            f"Runbook index not found at {index_path}. Run: python index_runbooks.py"
        )
    return json.loads(index_path.read_text(encoding="utf-8"))


def search_runbooks(query, top_k=3, min_score=DEFAULT_MIN_SCORE, index_path=INDEX_PATH):
    expanded_query = expand_query_for_retrieval(query)
    if not has_operational_problem_signal(expanded_query):
        return []
    index = load_runbook_index(index_path)
    query_embedding = embed_text(expanded_query)
    scored_chunks = []

    for chunk in index["chunks"]:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored_chunks.append(
            {
                "score": score,
                "source": chunk["source"],
                "runbook": chunk["runbook"],
                "section": chunk["section"],
                "text": chunk["text"],
            }
        )

    ranked_chunks = sorted(scored_chunks, key=lambda item: item["score"], reverse=True)
    filtered_chunks = [
        chunk for chunk in ranked_chunks if min_score is None or chunk["score"] >= min_score
    ]
    return filtered_chunks[:top_k]


def format_evidence(results):
    if not results:
        return "No retrieved runbook evidence."

    formatted = []
    for index, result in enumerate(results, start=1):
        formatted.append(
            "\n".join(
                [
                    f"[{index}] {result['runbook']} / {result['section']}",
                    f"source: {result['source']}",
                    f"similarity: {result['score']:.4f}",
                    result["text"],
                ]
            )
        )
    return "\n\n".join(formatted)
