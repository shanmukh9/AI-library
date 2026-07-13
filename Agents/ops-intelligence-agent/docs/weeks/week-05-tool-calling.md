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
4. Added hybrid_retriever.py with Reciprocal Rank Fusion.
5. Added query_hybrid_runbooks.py for manual hybrid inspection.
6. Added evaluate_hybrid_rrf.py to compare vector-only, BM25-only, and hybrid retrieval.
7. Added iam-accessdenied.md to fix a missing incident-family knowledge gap.
8. Added AccessDenied eval coverage to BM25 and Hybrid RRF evaluations.
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

Run the hybrid RRF evaluator:

```powershell
python .\evaluate_hybrid_rrf.py
```

## Results

Measured locally:

```text
Cases:                         8
BM25-only Top-1:               7/8
BM25-only Top-3:               7/8
Vector+Expansion+Rerank Top-1: 8/8
Vector+Expansion+Rerank Top-3: 8/8
```

Hybrid RRF measured locally:

```text
Cases:                         8
Vector+Expansion+Rerank Top-1: 8/8
Vector+Expansion+Rerank Top-3: 8/8
BM25-only Top-1:               7/8
BM25-only Top-3:               7/8
Hybrid RRF Top-1:              8/8
Hybrid RRF Top-3:              8/8
```

Knowledge coverage update:

```text
Runbook chunks: 40
Added:          iam-accessdenied.md
Eval case:      payment service AccessDenied after deploy
```

BM25 succeeded on exact-token cases:

```text
checkout HTTP 504 gateway timeout -> http-504-gateway-timeout.md
ALB 502 health checks failing      -> alb-502-health-checks.md
pod OOMKilled                      -> kubernetes-oomkill.md
lambda timeout failure             -> lambda-timeout.md
RDS max database connections       -> rds-connection-pool.md
payment service AccessDenied       -> iam-accessdenied.md
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

## Hybrid RRF

Hybrid RRF combines candidate lists by rank instead of adding raw scores.

This matters because BM25 and vector scores use different scales:

```text
BM25 score:        13.3183
Vector similarity: 0.7247
```

Adding those raw numbers would let BM25 dominate. RRF converts each result to a
rank-based vote:

```text
RRF score = 1 / (k + rank)
```

If the same chunk appears in both retrievers, the text is deduplicated but the
retrieval signal is preserved:

```text
retrieved_by = ["vector", "bm25"]
```

For `checkout throwing bad gateway`, raw BM25 retrieved 504 evidence because it
matched the word `gateway`. Hybrid RRF succeeds only after both retrievers share
the same preprocessing layer:

```text
raw query
    |
    v
query expansion + normalization
    |
    v
vector retrieval + BM25 retrieval
    |
    v
RRF merge and dedupe
```

That distinction is important:

```text
Naive hybrid can amplify wrong evidence.
Preprocessed hybrid can combine exact-word and meaning signals more safely.
```

## AccessDenied Knowledge Coverage

`payment service AccessDenied after deploy` is a missing-knowledge case when no
IAM or permission runbook exists. Vector search can drift toward a nearby
deployment-related incident, and BM25 cannot retrieve evidence that is not in
the corpus.

The correct fix is:

```text
Add IAM AccessDenied runbook coverage.
Add an eval case.
Rebuild the runbook vector index.
```

The incorrect fixes are:

```text
lowering min_score
forcing Lambda timeout evidence
reranking wrong candidates
patching the Lambda runbook to cover IAM failures
```

## Architecture Decision

Do not wire BM25 into the production chain yet.

Current decision:

```text
Keep BM25 and Hybrid RRF as experimental retrieval modes until a larger eval set
proves hybrid improves Top-1 or Top-3 without increasing false positives.
```

## Memory Hook

BM25 is the exact-word specialist.
Vector search is the meaning specialist.
Hybrid retrieval is justified only when measured evidence shows that both
signals together outperform either one alone.

RRF ranks candidates; it does not understand incidents by itself.
Reranking fixes ordering; it does not fix absence.
Closest neighbor is not coverage.
