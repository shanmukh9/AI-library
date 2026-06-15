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
- Two terse positive eval cases in `evaluate_runbook_rag.py`.
- Expanded-query visibility in `query_runbooks.py`.
- Baseline versus expanded eval mode using `--mode baseline` and `--mode expanded`.

## Why This Matters

Real alerts are often short and messy. A user may write:

```text
auth pod memory killed repeatedly
api cpu hot
```

But runbooks may use more precise operational language:

```text
OOMKilled pod crash-looping memory limit exceeded
high CPU usage exceeded 95 percent saturation
```

Query expansion bridges the user's shorthand to the language that appears in
runbooks before embedding search happens.

## Before and After

Before query expansion:

```text
auth pod memory killed repeatedly -> no retrieved runbook evidence
api cpu hot                       -> no retrieved runbook evidence
```

After query expansion:

```text
auth pod memory killed repeatedly
-> kubernetes-oomkill.md

api cpu hot
-> api-cpu-saturation.md
```

## Measured Results

Baseline mode, without query expansion:

```text
Positive cases:     8
Top-1 accuracy:     6/8
Top-3 hit rate:     6/8
Negative no-match:  2/2
Minimum similarity: 0.60
```

Expanded mode, with query expansion:

```text
Positive cases:     8
Top-1 accuracy:     8/8
Top-3 hit rate:     8/8
Negative no-match:  2/2
Minimum similarity: 0.60
```

Improvement:

```text
Top-1 accuracy: +25 percentage points
Top-3 hit rate: +25 percentage points
Negative no-match: unchanged at 2/2
```

## Important Lesson

Week 2 proved that vector search can retrieve relevant runbook evidence. Week 3
starts to improve retrieval quality by rewriting terse human language into more
searchable operational language.

This is still not LLM query rewriting. It is a deterministic, explainable first
step.

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

## Next Step

Move expansion rules out of Python into a small configuration file, then rerun
the same baseline-versus-expanded eval.
