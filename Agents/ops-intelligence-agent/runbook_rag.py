import json
import math
import re
import tomllib
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
RUNBOOK_DIR = PROJECT_ROOT / "runbooks"
INDEX_PATH = PROJECT_ROOT / "data" / "runbook_index.json"
QUERY_EXPANSIONS_PATH = PROJECT_ROOT / "data" / "query_expansions.json"
EMBEDDINGS_URL = "http://127.0.0.1:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_MIN_SCORE = 0.60
REQUIRED_METADATA_FIELDS = ("platform", "category")
INTENT_RULES = {
    "cause": {
        "keywords": ("cause", "caused", "why", "reason", "root cause"),
        "section": "Probable Causes",
        "bonus": 0.13,
    },
    "action": {
        "keywords": ("fix", "resolve", "remediate", "immediate", "action"),
        "section": "Immediate Actions",
        "bonus": 0.10,
    },
    "symptom": {
        "keywords": ("symptom", "confirm", "sign", "indicate"),
        "section": "Symptoms",
        "bonus": 0.05,
    },
}

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
    "504",
    "latency",
    "exhausted",
    "denied",
    "unhealthy",
    "expiring",
    "expires",
    "accessdenied",
    "consumer lag",
]

NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|never|without)\b(?:\W+\w+){0,3}\W*$",
    flags=re.IGNORECASE,
)

HEALTHY_STATE_SUFFIX_PATTERN = re.compile(
    r"^\W*(?:(?:rate|level|count|usage|percentage)\W+)?"
    r"(?:(?:is|are|was|were|remains?|stays?)\W+)?"
    r"(?:normal|healthy|stable)\b",
    flags=re.IGNORECASE,
)

OPERATIONAL_SIGNAL_NORMALIZATIONS = [
    (r"\btimed[\s-]+out\b", "timeout"),
    (r"\btiming[\s-]+out\b", "timeout"),
    (r"\btimes[\s-]+out\b", "timeout"),
    (r"\btime[\s-]+out\b", "timeout"),
    (
        r"\bconnections?\s+(?:is|are|was|were|became)\s+exhausted\b",
        "connections exhausted",
    ),
]

OPERATIONAL_PROBLEM_PATTERNS = [
    r"\b(?:rds|database|db)\b.{0,40}\bmax(?:imum)?\b.{0,30}\bconnections?\b.{0,30}\breached\b",
    r"\b(?:rds|database|db)\b.{0,40}\bconnections?\b.{0,30}\bmax(?:ed|imum)?\b",
    (
        r"^(?!.*\b(?:review(?:ing)?|reading|studying)\b.{0,40}"
        r"\b(?:documentation|docs?|guide|tutorial|example)\b).*"
        r"\brequests?\b.{0,40}\b(?P<signal>throttl(?:ed|ing))\b"
    ),
    r"\b(?:restart|restarted|restarts|restarting)\b",
    r"\bcrashloop(?:backoff)?\b",
]


def normalize_operational_signals(query):
    normalized_query = query
    for pattern, replacement in OPERATIONAL_SIGNAL_NORMALIZATIONS:
        normalized_query = re.sub(
            pattern,
            replacement,
            normalized_query,
            flags=re.IGNORECASE,
        )
    return normalized_query


def is_signal_negated(text, signal_start):
    prefix = text[max(0, signal_start - 60) : signal_start]
    return bool(NEGATION_PATTERN.search(prefix))


def is_signal_marked_healthy(text, signal_end):
    suffix = text[signal_end : signal_end + 40]
    return bool(HEALTHY_STATE_SUFFIX_PATTERN.search(suffix))


def contains_asserted_signal(text, signal):
    pattern = rf"(?<![a-z0-9]){re.escape(signal)}(?![a-z0-9])"
    return any(
        not is_signal_negated(text, match.start())
        and not is_signal_marked_healthy(text, match.end())
        for match in re.finditer(pattern, text, flags=re.IGNORECASE)
    )


def contains_asserted_pattern(text, pattern):
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        signal_start = (
            match.start("signal")
            if match.groupdict().get("signal") is not None
            else match.start()
        )
        if not is_signal_negated(text, signal_start):
            return True
    return False


def has_operational_problem_signal(query):
    normalized_query = normalize_operational_signals(query)
    return any(
        contains_asserted_signal(normalized_query, signal)
        for signal in OPERATIONAL_PROBLEM_SIGNALS
    ) or any(
        contains_asserted_pattern(normalized_query, pattern)
        for pattern in OPERATIONAL_PROBLEM_PATTERNS
    )


def load_query_expansion_rules(path=QUERY_EXPANSIONS_PATH):
    if not path.exists():
        raise FileNotFoundError(f"Query expansion config not found at {path}")

    rules = json.loads(path.read_text(encoding="utf-8"))
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule.get("triggers"), list) or not rule.get("expansion"):
            raise ValueError(f"Invalid query expansion rule at position {index}")
    return rules


def expand_query_for_retrieval(query):
    rules = load_query_expansion_rules()
    expansions = [
        rule["expansion"]
        for rule in rules
        if any(
            contains_asserted_signal(query, trigger)
            for trigger in rule["triggers"]
        )
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


def parse_runbook(markdown_text):
    if not markdown_text.startswith("+++\n"):
        raise ValueError("Runbook must start with TOML front matter")

    try:
        metadata_text, body = markdown_text[4:].split("\n+++\n", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Runbook TOML front matter is not closed with +++") from exc

    metadata = tomllib.loads(metadata_text)
    missing_fields = [
        field for field in REQUIRED_METADATA_FIELDS if not metadata.get(field)
    ]
    if missing_fields:
        raise ValueError(
            f"Runbook metadata is missing: {', '.join(missing_fields)}"
        )

    return metadata, body.lstrip()


def load_runbook_chunks(runbook_dir=RUNBOOK_DIR):
    chunks = []
    for path in sorted(runbook_dir.glob("*.md")):
        metadata, body = parse_runbook(path.read_text(encoding="utf-8"))
        title = body.splitlines()[0].removeprefix("# ").strip()
        for section_title, section_text in split_runbook_sections(body):
            chunks.append(
                {
                    "id": f"{path.stem}:{section_title.lower().replace(' ', '-')}",
                    "source": path.name,
                    "runbook": title,
                    "section": section_title,
                    "text": section_text,
                    "metadata": metadata,
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


def filter_chunks_by_metadata(chunks, metadata_filters=None):
    if not metadata_filters:
        return list(chunks)

    return [
        chunk
        for chunk in chunks
        if all(
            chunk.get("metadata", {}).get(field) == expected_value
            for field, expected_value in metadata_filters.items()
        )
    ]


def select_candidate_chunks(
    chunks,
    metadata_filters=None,
    fallback_on_empty=True,
):
    filtered_chunks = filter_chunks_by_metadata(
        chunks,
        metadata_filters=metadata_filters,
    )
    fallback_used = bool(
        metadata_filters and not filtered_chunks and fallback_on_empty
    )
    if fallback_used:
        return list(chunks), True
    return filtered_chunks, False


def detect_query_intents(query):
    normalized_query = query.lower()
    return [
        intent
        for intent, rule in INTENT_RULES.items()
        if any(keyword in normalized_query for keyword in rule["keywords"])
    ]


def detect_query_intent(query):
    intents = detect_query_intents(query)
    return intents[0] if intents else None


def rerank_by_intent(query, results):
    intents = detect_query_intents(query)
    if not intents:
        return [
            {
                **result,
                "rerank_intent": None,
                "rerank_bonus": 0.0,
                "score": result["similarity_score"],
            }
            for result in results
        ]

    leading_source = max(
        results,
        key=lambda item: item["similarity_score"],
    )["source"]
    reranked_results = []
    for result in results:
        matched_intents = [
            intent
            for intent in intents
            if (
                result["source"] == leading_source
                and result["section"] == INTENT_RULES[intent]["section"]
            )
        ]
        bonus = sum(INTENT_RULES[intent]["bonus"] for intent in matched_intents)
        reranked_results.append(
            {
                **result,
                "rerank_intent": ",".join(intents),
                "rerank_bonus": bonus,
                "rerank_source": leading_source,
                "score": result["similarity_score"] + bonus,
            }
        )
    return sorted(
        reranked_results,
        key=lambda item: item["score"],
        reverse=True,
    )


def search_runbooks(
    query,
    top_k=3,
    min_score=DEFAULT_MIN_SCORE,
    index_path=INDEX_PATH,
    use_expansion=True,
    metadata_filters=None,
    metadata_fallback=True,
    use_reranking=False,
    reranking_query=None,
):
    expanded_query = expand_query_for_retrieval(query) if use_expansion else query
    normalized_query = normalize_operational_signals(expanded_query)
    if not has_operational_problem_signal(normalized_query):
        return []
    index = load_runbook_index(index_path)
    candidate_chunks, fallback_used = select_candidate_chunks(
        index["chunks"],
        metadata_filters=metadata_filters,
        fallback_on_empty=metadata_fallback,
    )
    if not candidate_chunks:
        return []

    query_embedding = embed_text(normalized_query)

    def rank_chunks(chunks):
        scored_chunks = []
        for chunk in chunks:
            similarity_score = cosine_similarity(
                query_embedding,
                chunk["embedding"],
            )
            scored_chunks.append(
                {
                    "score": similarity_score,
                    "similarity_score": similarity_score,
                    "rerank_intent": None,
                    "rerank_bonus": 0.0,
                    "source": chunk["source"],
                    "runbook": chunk["runbook"],
                    "section": chunk["section"],
                    "text": chunk["text"],
                    "metadata": chunk.get("metadata", {}),
                }
            )

        ranked_chunks = sorted(
            scored_chunks,
            key=lambda item: item["score"],
            reverse=True,
        )
        return [
            chunk
            for chunk in ranked_chunks
            if min_score is None or chunk["similarity_score"] >= min_score
        ]

    results = rank_chunks(candidate_chunks)
    should_retry_unfiltered = (
        metadata_filters
        and metadata_fallback
        and not results
        and len(candidate_chunks) < len(index["chunks"])
    )
    if should_retry_unfiltered:
        results = rank_chunks(index["chunks"])
        fallback_used = True

    if use_reranking:
        results = rerank_by_intent(
            reranking_query or normalized_query,
            results,
        )
    results = results[:top_k]

    for result in results:
        result["metadata_fallback_used"] = fallback_used
    return results


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
                    (
                        "metadata: "
                        f"platform={result['metadata'].get('platform', 'unknown')}, "
                        f"category={result['metadata'].get('category', 'unknown')}"
                    ),
                    f"similarity: {result.get('similarity_score', result['score']):.4f}",
                    (
                        "reranking: "
                        f"intent={result.get('rerank_intent') or 'none'}, "
                        f"source={result.get('rerank_source', 'none')}, "
                        f"bonus={result.get('rerank_bonus', 0.0):.2f}, "
                        f"vector={result.get('similarity_score', result['score']):.4f}, "
                        f"final={result['score']:.4f}"
                    ),
                    result["text"],
                ]
            )
        )
    return "\n\n".join(formatted)
