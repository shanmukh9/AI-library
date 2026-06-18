# Week 03 - Advanced RAG

> Status: In progress

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

## Important Lesson

Week 2 proved that vector search can retrieve relevant runbook evidence. Week 3
starts to improve retrieval quality by rewriting terse human language into more
searchable operational language.

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
- No reranker or hybrid keyword/vector retrieval has been added yet.
- Query expansion can overfit if rules are added without failure cases.
- Incorrect metadata can remove the correct runbook from the candidate set.
- The signal gate currently recognizes `timeout` but not the phrase
  `timing out`; metadata is never reached if the alert fails that earlier gate.

## Next Step

Add metadata-aware evaluation cases, then decide whether filtering should be
strict or should fall back to unfiltered retrieval when metadata produces zero
candidates.
