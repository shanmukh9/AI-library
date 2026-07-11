# Week 05 - BM25 Lexical Retrieval Baseline

> Status: Complete locally

## Goal

Add a dependency-free BM25 retriever as a measured baseline beside the existing
vector RAG pipeline.

The goal is not to replace vector search. The goal is to learn when exact-token
retrieval is useful before adding production hybrid retrieval.

## Why BM25 Was Added

Vector search answers:

```text
Which chunks mean something similar to this alert?
```

BM25 answers:

```text
Which chunks contain the exact important words from this alert?
```

This matters for production RAG because operational systems often contain exact
terms that should not be blurred:

```text
HTTP 504
HTTP 502
OOMKilled
ORA-00020
AccessDenied
ThrottlingException
```

Query expansion and normalization help only when we already know the rewrite
rules. BM25 gives a second retrieval signal for exact tokens.

## What Changed

```text
1. Added bm25_retriever.py.
2. Added query_bm25_runbooks.py for manual lexical search.
3. Added evaluate_bm25_baseline.py to compare BM25 with vector + expansion + reranking.
```

## How BM25 Works Here

```text
Runbook chunks
    |
    v
Lowercase tokenization
    |
    v
Term frequency per chunk
    |
    v
Document frequency across all chunks
    |
    v
BM25 score
    |
    v
Top-K lexical results
```

BM25 ranking favors:

```text
1. Query terms that appear in the chunk.
2. Rare terms that do not appear everywhere.
3. Chunks where the matching terms are concentrated.
```

## Commands

Run a direct BM25 query:

```powershell
python .\query_bm25_runbooks.py "checkout HTTP 504 gateway timeout"
```

Run the comparison evaluator:

```powershell
python .\evaluate_bm25_baseline.py
```

## Results

Measured locally:

```text
Cases:                         7
BM25-only Top-1:               6/7
BM25-only Top-3:               6/7
Vector+Expansion+Rerank Top-1: 7/7
Vector+Expansion+Rerank Top-3: 7/7
```

BM25 succeeded on exact-token cases:

```text
checkout HTTP 504 gateway timeout -> http-504-gateway-timeout.md
ALB 502 health checks failing      -> alb-502-health-checks.md
pod OOMKilled                      -> kubernetes-oomkill.md
lambda timeout failure             -> lambda-timeout.md
RDS max database connections       -> rds-connection-pool.md
```

BM25 failed on:

```text
checkout throwing bad gateway -> retrieved HTTP 504 evidence
```

Why it failed:

```text
BM25 matched the exact word "gateway" strongly, but it did not understand that
"bad gateway" is usually associated with HTTP 502. Vector search + expansion
retrieved the ALB 502 runbook correctly.
```

## Architecture Decision

Do not wire BM25 into the production chain yet.

Current decision:

```text
Keep BM25 as an experimental baseline until hybrid retrieval proves it improves
Top-1 or Top-3 without increasing false positives.
```

## Memory Hook

BM25 is the exact-word specialist.
Vector search is the meaning specialist.
Hybrid retrieval is justified only when measured evidence shows that both
signals together outperform either one alone.
