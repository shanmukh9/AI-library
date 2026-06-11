# Week 02 - Runbook RAG

> Status: Complete locally

## Goal

Retrieve relevant runbook chunks before generating remediation guidance.

## Build Checklist

- [x] Add synthetic runbook Markdown files
- [x] Chunk runbook content
- [x] Embed and index chunks
- [x] Embed an incoming alert query
- [x] Rank chunks with cosine similarity
- [x] Inject top chunks into the Gemma prompt
- [x] Show retrieved evidence with the generated response
- [x] Measure retrieval results on labeled test queries

## What Was Built

- `runbook_rag.py`: reusable embedding, indexing, cosine search, and evidence formatting.
- `index_runbooks.py`: embeds runbook chunks and writes `data/runbook_index.json`.
- `query_runbooks.py`: quick manual retrieval demo for one alert query.
- `evaluate_runbook_rag.py`: checks whether expected runbooks appear in the top results.
- `runbooks/*.md`: synthetic operational runbooks for API CPU, Lambda timeout, Kubernetes OOMKilled, RDS pool exhaustion, and ALB 502 health checks.
- `basic_chain.py`: now injects retrieved runbook evidence before asking the chat model for structured alert analysis.

## Architecture

```text
runbooks/*.md
    |
    v
section chunks
    |
    v
embedding model in LM Studio
    |
    v
data/runbook_index.json
    |
    v
alert query embedding
    |
    v
cosine similarity ranking
    |
    v
top runbook evidence
    |
    v
Gemma chat model + severity policy
    |
    v
structured JSON response
```

## Measured Results

| Check | Result |
| --- | --- |
| Runbook files | `6` |
| Positive retrieval cases | `6` |
| Top-1 accuracy | `6/6` |
| Top-3 hit rate | `6/6` |
| Negative no-match cases | `2/2` |
| Minimum similarity cutoff | `0.60` |
| RAG-backed severity check | `3/3` on selected P1 alerts |

## Retrieval Example

Query:

```text
CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes
```

Top result:

```text
api-cpu-saturation.md / Symptoms
similarity: 0.7431
```

After adding the SSL certificate runbook, this query:

```text
SSL certificate expires in 7 days
```

returns only the strong SSL match because weak chunks below `0.60` are filtered:

```text
ssl-certificate-expiry.md / Overview
similarity: 0.7529
```

Negative query:

```text
employee laptop password reset request
lambda ok
```

Expected behavior:

```text
No chunks passed the minimum similarity cutoff
```

## Important Lesson

RAG alone does not make the system correct. Retrieval finds relevant evidence,
but a severity policy is still needed to classify alerts consistently.

Observed during implementation:

```text
RAG evidence present, no severity policy -> severity regressed to 1/3
RAG evidence plus severity policy       -> severity recovered to 3/3
```

Top-k retrieval also needs a quality gate. Without a cutoff, the retriever will
always return the nearest chunks, even when the second and third chunks are weak
or irrelevant. A minimum similarity cutoff prevents weak evidence from being
sent to the LLM.

Today, the eval was improved from a single "did it appear anywhere?" check into
three clearer measurements:

```text
Top-1 accuracy  -> was the best chunk from the expected runbook?
Top-3 hit rate  -> did the expected runbook appear anywhere in the top results?
Negative no-match -> did an unrelated query correctly return no evidence?
```

## Safety Lesson

Runbook evidence should ground recommendations, but it should not authorize
remediation by itself. Future remediation needs deterministic safety checks and
human approval for risky actions.

## Known Limits

- Runbooks are synthetic and small.
- Evaluation uses six positive labeled queries and one negative no-match query.
- Retrieval is vector-only; no keyword or hybrid retrieval yet.
- The generated vector index is local output and is ignored by Git.
- The chat model can still make mistakes even with retrieved evidence.

## Commands

```powershell
python .\index_runbooks.py
python .\query_runbooks.py "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"
python .\evaluate_runbook_rag.py
python .\basic_chain.py
```

## Interview Explanation

In Week 2, I added retrieval before generation. I created synthetic CloudOps
runbooks, chunked them by section, embedded each chunk with a local embedding
model, and ranked chunks with cosine similarity for each incoming alert. The
main alert-analysis chain now receives only retrieved evidence above a minimum
similarity cutoff before generating structured JSON. The key lesson was that RAG
improves grounding, but classification still needs an explicit severity policy
and retrieval needs a quality gate. I also evaluated retrieval with top-1
accuracy, top-3 hit rate, and a negative query that should return no evidence.
