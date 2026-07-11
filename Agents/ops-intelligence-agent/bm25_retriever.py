import math
import re
from collections import Counter, defaultdict

from runbook_rag import INDEX_PATH, load_runbook_index


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)


def tokenize(text):
    return TOKEN_PATTERN.findall(text.lower())


def build_bm25_corpus(index_path=INDEX_PATH):
    index = load_runbook_index(index_path)
    documents = []
    document_frequencies = defaultdict(int)
    total_length = 0

    for chunk in index["chunks"]:
        searchable_text = " ".join(
            [
                chunk["runbook"],
                chunk["section"],
                chunk["text"],
                chunk.get("metadata", {}).get("platform", ""),
                chunk.get("metadata", {}).get("category", ""),
            ]
        )
        tokens = tokenize(searchable_text)
        term_counts = Counter(tokens)
        total_length += len(tokens)

        for token in term_counts:
            document_frequencies[token] += 1

        documents.append(
            {
                **chunk,
                "tokens": tokens,
                "term_counts": term_counts,
                "length": len(tokens),
            }
        )

    average_document_length = total_length / len(documents) if documents else 0
    return documents, document_frequencies, average_document_length


def score_bm25(
    query_tokens,
    document,
    document_frequencies,
    corpus_size,
    average_document_length,
    k1=1.5,
    b=0.75,
):
    score = 0.0
    for token in query_tokens:
        term_frequency = document["term_counts"].get(token, 0)
        if term_frequency == 0:
            continue

        document_frequency = document_frequencies.get(token, 0)
        inverse_document_frequency = math.log(
            1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
        )
        length_ratio = (
            document["length"] / average_document_length
            if average_document_length
            else 0
        )
        denominator = term_frequency + k1 * (1 - b + b * length_ratio)
        score += inverse_document_frequency * (
            (term_frequency * (k1 + 1)) / denominator
        )

    return score


def bm25_search(query, top_k=3, min_score=0.0, index_path=INDEX_PATH):
    documents, document_frequencies, average_document_length = build_bm25_corpus(
        index_path=index_path
    )
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    results = []
    for document in documents:
        score = score_bm25(
            query_tokens=query_tokens,
            document=document,
            document_frequencies=document_frequencies,
            corpus_size=len(documents),
            average_document_length=average_document_length,
        )
        if score >= min_score and score > 0:
            results.append(
                {
                    "score": score,
                    "source": document["source"],
                    "runbook": document["runbook"],
                    "section": document["section"],
                    "text": document["text"],
                    "metadata": document.get("metadata", {}),
                    "matched_terms": [
                        token
                        for token in query_tokens
                        if document["term_counts"].get(token, 0) > 0
                    ],
                }
            )

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]
