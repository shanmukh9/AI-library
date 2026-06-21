# Week 03 - Advanced RAG

> Status: Complete locally

## Goal

Improve retrieval quality with a measured baseline-versus-improved comparison.

## Focus

- query rewriting for terse alerts
- metadata filtering
- reranking
- retrieval evaluation

## What Was Added Today

- Deterministic query expansion in `runbook_rag.py`.
- Five terse positive eval cases in `evaluate_runbook_rag.py`.
- Expanded-query visibility in `query_runbooks.py`.
- Baseline versus expanded eval mode using `--mode baseline` and `--mode expanded`.
- Query expansion rules moved into `data/query_expansions.json`.
- TOML metadata added to every runbook.
- Optional `platform` and `category` filters added before vector ranking.
- Candidate-count visibility added to `query_runbooks.py`.
- Strict and observable fallback metadata policies added.
- Metadata policy evaluator added in `evaluate_metadata_filtering.py`.
- Optional intent-aware section reranking added.
- Vector-only versus reranked evaluation added in `evaluate_reranking.py`.
- Reranked Top 3 evidence integrated into `basic_chain.py`.
- Controlled timeout-phrase normalization added before gating and embedding.
- Dedicated signal-gate evaluation added in `evaluate_signal_gate.py`.

## Why This Matters

Real alerts are often short and messy. A user may write:

```text
auth pod memory killed repeatedly
api cpu hot
db maxed connections
checkout throwing bad gateway
api is slow
```

But runbooks may use more precise operational language:

```text
OOMKilled pod crash-looping memory limit exceeded
high CPU usage exceeded 95 percent saturation
RDS connection pool exhausted max database connections reached
ALB health checks failing 502 responses increasing checkout service
API slow responses high CPU usage saturation
```

Query expansion bridges the user's shorthand to the language that appears in
runbooks before embedding search happens.

## Before and After

Before query expansion:

```text
auth pod memory killed repeatedly -> no retrieved runbook evidence
api cpu hot                       -> no retrieved runbook evidence
db maxed connections              -> no retrieved runbook evidence
checkout throwing bad gateway     -> no retrieved runbook evidence
api is slow                       -> no retrieved runbook evidence
```

After query expansion:

```text
auth pod memory killed repeatedly
-> kubernetes-oomkill.md

api cpu hot
-> api-cpu-saturation.md

db maxed connections
-> rds-connection-pool.md

checkout throwing bad gateway
-> alb-502-health-checks.md

api is slow
-> api-cpu-saturation.md
```

## Measured Results

Baseline mode, without query expansion:

```text
Positive cases:     11
Top-1 accuracy:     6/11
Top-3 hit rate:     6/11
Negative no-match:  2/2
Minimum similarity: 0.60
```

Expanded mode, with query expansion:

```text
Positive cases:     11
Top-1 accuracy:     11/11
Top-3 hit rate:     11/11
Negative no-match:  2/2
Minimum similarity: 0.60
```

Improvement:

```text
Top-1 accuracy: +45.5 percentage points
Top-3 hit rate: +45.5 percentage points
Negative no-match: unchanged at 2/2
```

## Failure Analysis Discipline

Not every failed query deserves an expansion rule.

```text
logs delayed -> no retrieved evidence
```

This is acceptable because the current knowledge base does not contain a
log-pipeline or observability-delay runbook. Returning no evidence is safer than
forcing a weak match into the LLM context.

## Metadata Filtering

Each runbook now starts with TOML front matter:

```toml
+++
platform = "aws-lambda"
category = "timeout"
+++
```

The chunking pipeline parses this once and copies the metadata onto every
chunk created from that runbook:

```text
Runbook
  -> parse TOML metadata
  -> split Markdown sections
  -> attach metadata to each chunk
  -> embed and save in runbook_index.json
```

At query time, metadata filtering happens before cosine similarity:

```text
Expanded alert query
  -> operational signal gate
  -> optional metadata filter
  -> query embedding
  -> cosine similarity over remaining chunks
  -> min_score filter
```

Measured example:

```text
Query: payment processor timeout failure

Without metadata:
Candidate chunks: 30/30
Top result: lambda-timeout.md

With platform=aws-lambda:
Candidate chunks: 5/30
Top result: lambda-timeout.md
```

The metadata filter did not improve top-1 accuracy in this example because
vector search already ranked the correct runbook first. It reduced the candidate
search space from 30 chunks to 5 and prevented unrelated platforms from
competing.

Run the comparison:

```powershell
python .\query_runbooks.py "payment processor timeout failure"
python .\query_runbooks.py "payment processor timeout failure" --platform aws-lambda
```

Metadata filtering is optional because incorrect metadata can hide the correct
runbook. For example, filtering the same Lambda alert with
`--platform kubernetes` returns no evidence.

## Strict Versus Fallback Metadata

Strict mode fully trusts supplied metadata:

```powershell
python .\query_runbooks.py "payment processor timeout failure" `
  --platform kubernetes `
  --metadata-mode strict
```

Result:

```text
Candidate chunks: 5/30
Metadata fallback used: no
No retrieved runbook evidence.
```

Fallback mode retries unfiltered retrieval when the metadata-filtered search
produces no usable evidence:

```powershell
python .\query_runbooks.py "payment processor timeout failure" `
  --platform kubernetes `
  --metadata-mode fallback
```

Result:

```text
Candidate chunks: 30/30
Metadata fallback used: yes
Top result: lambda-timeout.md
```

Fallback activates in two situations:

```text
1. Metadata matches zero chunks.
2. Metadata matches chunks, but none pass min_score.
```

The same query embedding is reused during fallback. The system does not make a
second embedding-model request.

Evaluate both policies:

```powershell
python .\evaluate_metadata_filtering.py
```

Measured locally:

```text
Strict policy:   3/3 expected behaviors
Fallback policy: 3/3 expected behaviors
Expanded RAG:    11/11 positive, 2/2 negative
```

Fallback is more resilient, but it should never be silent. The CLI reports
`Metadata fallback used: yes` because the final evidence no longer obeys the
original metadata constraint.

## Intent-Aware Reranking

Vector similarity finds semantically related chunks, but it may not rank the
section that best answers the user's question.

Measured Lambda examples before reranking:

```text
Cause question   -> Overview ranked above Probable Causes
Action question  -> Overview ranked above Immediate Actions
Symptom question -> Symptoms already ranked first
```

The lightweight reranker detects three intents:

```text
cause   -> boost Probable Causes by 0.13
action  -> boost Immediate Actions by 0.10
symptom -> boost Symptoms by 0.05
```

The original vector similarity must pass `min_score=0.60` before a bonus is
applied. Reranking can reorder grounded evidence, but it cannot rescue a weak
chunk that failed the retrieval threshold.

Action-query example:

```text
Overview:
vector = 0.8052
bonus  = 0.00
final  = 0.8052

Immediate Actions:
vector = 0.7074
bonus  = 0.10
final  = 0.8074
```

Compare both modes:

```powershell
python .\query_runbooks.py `
  "What should I do immediately for the Lambda timeout failure?" `
  --platform aws-lambda `
  --ranking vector

python .\query_runbooks.py `
  "What should I do immediately for the Lambda timeout failure?" `
  --platform aws-lambda `
  --ranking reranked
```

Evaluate reranking:

```powershell
python .\evaluate_reranking.py
```

Measured locally:

```text
Vector-only intent Top-1: 1/3
Reranked intent Top-1:    3/3
Expanded RAG:             11/11 positive, 2/2 negative
Metadata policies:        3/3 strict, 3/3 fallback
```

### Main LLM Chain Integration

The main chain keeps retrieval meaning and downstream task intent separate:

```text
Embedding query: original alert text
Reranking task:  identify root cause and recommend immediate action
```

It now requests the final Top 3 reranked chunks and sends them to the chat
model. Bonuses apply only to sections from the runbook with the strongest
original vector match. This prevents a well-labelled section from an unrelated
runbook from overtaking the correct source.

End-to-end local result:

```text
CPU saturation:    P1 match
Lambda timeout:    P1 match
Kubernetes OOM:    P1 match
Severity matches:  3/3
```

## Operational Signal Normalization

The signal gate is deterministic string logic, so semantically equivalent
phrases previously behaved differently:

```text
timeout    -> pass
timed out  -> reject
timing out -> reject
```

Week 3 now canonicalizes controlled timeout variations:

```text
timed out
timing out
time out
times out
timed-out
    -> timeout
```

The normalized query is used by both the operational gate and embedding search.
The manual query CLI prints the normalized form when it changes.

This is safer than expanding `lambda acting weird` into a timeout because
normalization preserves a known failure meaning instead of inventing one. The
unsafe vague expansion was removed.

Evaluate:

```powershell
python .\evaluate_signal_gate.py
```

Measured locally:

```text
Signal gate cases: 10/10
Timeout variants:  6/6 passed
Vague/normal text: 4/4 rejected

lambda timing out repeatedly
-> normalized to: lambda timeout repeatedly
-> lambda-timeout.md Top-1: 0.8283

lambda acting weird
-> no retrieved evidence
```

## Important Lesson

Week 2 proved that vector search can retrieve relevant runbook evidence. Week 3
made that retrieval pipeline more robust, selective, explainable, and useful to
the downstream LLM.

This is still not LLM query rewriting. It is a deterministic, explainable first
step.

The expansion rules are configuration-driven:

```text
data/query_expansions.json
```

This keeps domain aliases separate from retrieval logic. New aliases can be
added without editing the core search code.

Today's measurement is an ablation test:

```text
baseline = retrieval without query expansion
expanded = retrieval with query expansion
```

The only intended difference is the query expansion step, so the metric delta
shows whether the new component helped.

## Known Limits

- The expansion rules are hand-written and small.
- The eval set is still synthetic.
- The reranker uses small hand-written intent rules and section bonuses.
- No hybrid keyword/vector retrieval or learned cross-encoder reranker has been
  added yet.
- Query expansion can overfit if rules are added without failure cases.
- Incorrect metadata can remove the correct runbook from the candidate set.
- Fallback can retrieve evidence outside the supplied platform, so callers must
  expose that fallback occurred.
- Signal normalization currently covers controlled timeout variants only.
- The signal gate remains deterministic and does not understand arbitrary
  natural-language descriptions.

## Next Step

Begin Week 4 by documenting retrieval architecture decisions: when the current
vector pipeline is sufficient, and when hybrid retrieval, routing, or a learned
reranker would be justified.
