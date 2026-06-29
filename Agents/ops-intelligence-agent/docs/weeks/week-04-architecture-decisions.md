# Week 04 - Retrieval Evaluation and Architecture Decisions

> Status: In progress

## Goal

Move from "RAG works" to "RAG can be diagnosed." Week 4 focuses on
identifying why retrieval fails before adding more architecture.

The main engineering question:

```text
Should OIA add hybrid keyword + vector retrieval now, or should we first
improve knowledge coverage, evaluation cases, query expansion, metadata, and
reranking?
```

Current decision:

```text
Do not add hybrid retrieval yet.
```

The recent tests show the bigger issue is not that vector search is generally
weak. The bigger issue is deciding what type of failure happened and choosing
the smallest correct fix.

## Current Retrieval Pipeline

```text
Alert query
    |
    v
Operational signal gate
    |
    v
Normalization and query expansion
    |
    v
Query embedding
    |
    v
Optional metadata candidate filtering
    |
    v
Cosine similarity against indexed runbook chunks
    |
    v
min_score filtering
    |
    v
Top-K evidence
    |
    v
Intent-aware reranking
    |
    v
Grounded LLM prompt
    |
    v
Structured incident analysis
```

## Failure Diagnosis Matrix

| Failure type | Symptom | Best first fix | What not to do first |
| --- | --- | --- | --- |
| Missing knowledge | Correct incident type has no runbook | Add the missing runbook and eval case | Force a weak neighboring runbook |
| Vague alert | Query is too broad to identify a cause | Ask for clarification or add a broad troubleshooting runbook | Assume the closest keyword match is correct |
| Terse operational shorthand | Human shorthand does not match runbook wording | Add controlled query expansion | Lower threshold globally |
| Equivalent wording | Same meaning appears in different word forms | Add normalization | Add broad expansion that guesses new meaning |
| Wrong metadata | Filter hides the right runbook | Use fallback mode and fix metadata | Trust strict filtering blindly |
| Right runbook, wrong section | Overview wins when user asks for cause/action/symptom | Use intent-aware reranking | Add a new runbook |
| Relevant evidence below threshold | Good chunk scores just under `min_score` | Add eval, inspect runbook wording, then tune threshold if justified | Lower threshold without measuring false positives |
| Correct evidence, wrong answer | Retrieval is good but LLM gives wrong severity/RCA/action | Improve prompt, severity policy, examples, or model | Change retrieval first |
| Wrong evidence, confident answer | LLM produces polished answer from irrelevant context | Fix retrieval and add safety checks | Trust model confidence |

## Diagnosed Examples

| Query | Diagnosis | Best fix | Why |
| --- | --- | --- | --- |
| `checkout HTTP 504` | Missing knowledge | Add a 504 gateway timeout runbook and eval case | 504 is not the same as 502. Returning no evidence is safer than forcing the 502 runbook. |
| `certificate error` | Vague alert | Clarify, require stronger evidence, or add a broad certificate troubleshooting runbook | Certificate errors may mean expiry, hostname mismatch, trust chain, TLS, renewal, or wrong certificate. |
| `pod CrashLoopBackOff` | Broad Kubernetes symptom | Add a general CrashLoopBackOff runbook or require stronger cause signals like `OOMKilled` | CrashLoopBackOff is a state, not a single root cause. |
| `db maxed connections` | Terse operational shorthand | Query expansion | Expansion maps human shorthand to runbook language such as connection pool exhaustion and max database connections. |
| `how do I fix Lambda timeout?` | Right runbook, action intent | Intent-aware reranking | Retrieval should find Lambda timeout; reranking should prefer the `Immediate Actions` section. |

## Why Hybrid Retrieval Is Deferred

Hybrid retrieval can combine exact keyword matching with vector search. That can
be valuable, but it should be added only when evaluation proves vector search is
missing exact operational terms that keyword search would recover.

Current observations:

```text
checkout HTTP 502        -> vector retrieval finds ALB 502 evidence
pod OOMKilled            -> vector retrieval finds Kubernetes OOM evidence
pod CrashLoopBackOff     -> vector retrieval finds Kubernetes OOM evidence, but the query is broad
certificate expires      -> vector retrieval finds SSL expiry evidence
certificate error        -> vector retrieval finds SSL evidence, but the query is ambiguous
checkout HTTP 504        -> no evidence, likely because 504 knowledge is missing
```

These results do not justify hybrid retrieval yet. They point to knowledge
coverage, ambiguity handling, and evaluation design.

## When Hybrid Retrieval Becomes Justified

Add hybrid retrieval only if a measured eval shows this pattern:

```text
1. The correct runbook exists.
2. The exact operational term is present in the runbook.
3. Vector search fails to retrieve it above threshold.
4. Keyword search retrieves it reliably.
5. The hybrid method improves Top-1 or Top-3 without increasing false positives.
```

Candidate future examples:

```text
HTTP 429
ORA-00020
OOMKilled
CrashLoopBackOff
TLS handshake failed
AccessDenied
ThrottlingException
```

## Architect Rule

Do not treat every retrieval miss as a retrieval-engine problem.

Use this order:

```text
1. Is the runbook missing?
2. Is the query too vague?
3. Is the wording too terse?
4. Is metadata hiding the right chunks?
5. Is the right runbook retrieved but the wrong section ranked first?
6. Is the threshold too strict?
7. Did the LLM fail even with good evidence?
8. Only then consider a new retrieval architecture.
```

## What Was Learned

Week 4 is about engineering restraint. A stronger system is not always built by
adding more layers. It is built by classifying failures correctly and applying
the smallest fix that can be measured.

The key distinction:

```text
RAG failure:
The LLM received wrong, weak, or missing evidence.

LLM failure:
The LLM received good evidence but produced a wrong answer.
```

Debug retrieval before blaming the model. Debug the prompt and severity policy
only after evidence quality is confirmed.

## Next Practical Step

Add a small Week 4 evaluation set that labels each test case by failure type:

```text
missing_knowledge
vague_alert
terse_shorthand
right_runbook_wrong_section
exact_term_retrieval
correct_evidence_wrong_answer
```

This will turn architecture decisions into measurable evidence instead of
opinions.

## Week 4 Diagnosis Evaluator

The first diagnosis evaluator is implemented in:

```powershell
python .\evaluate_retrieval_diagnosis.py
```

Unlike a pure accuracy test, this evaluator separates outcomes into:

```text
PASS   -> behavior is acceptable
REVIEW -> retrieval is mechanically explainable but needs architecture judgment
FAIL   -> expected behavior broke
```

Measured locally:

```text
Cases:                 6
Passes:                3
Failures:              0
Review-required cases: 3
```

Current review cases:

| Query | Why it needs review |
| --- | --- |
| `certificate error` | Retrieves SSL expiry evidence, but the alert is too broad to assume expiry. |
| `pod CrashLoopBackOff` | Retrieves OOM evidence, but CrashLoopBackOff alone is a broad Kubernetes symptom. |
| `how do I fix Lambda timeout?` | Detects action intent, but the Overview chunk still outranks Immediate Actions for short fix-oriented wording. |

The Lambda case is especially useful because it shows a subtle limitation:

```text
Reranking can only gently adjust already relevant chunks.
If the Overview vector score is much stronger than the action section score,
a small bonus may not be enough to move Immediate Actions to Top-1.
```

This does not automatically mean the reranking bonus should be increased.
Possible fixes should be evaluated:

```text
1. Improve action-intent detection for short wording like "fix".
2. Improve section text so Immediate Actions embeds closer to fix-oriented queries.
3. Tune the reranking bonus only after checking false positives.
4. Use an explicit answer-intent field in a later typed-output or router layer.
```

## Reranking Sensitivity Experiment

The short action query created a useful architecture question:

```text
How large would the action-intent bonus need to be before Immediate Actions
beats Overview for "how do I fix Lambda timeout?"
```

Run:

```powershell
python .\evaluate_reranking_sensitivity.py
```

Measured locally:

```text
Action bonus 0.10 -> expected-section hits 3/4
Action bonus 0.12 -> expected-section hits 3/4
Action bonus 0.15 -> expected-section hits 3/4
Action bonus 0.20 -> expected-section hits 3/4
Action bonus 0.22 -> expected-section hits 4/4
Action bonus 0.25 -> expected-section hits 4/4
```

Finding:

```text
The short action query needs about 0.22 bonus to move Immediate Actions above
Overview in this small Lambda-only test.
```

Decision:

```text
Do not change the production reranking bonus yet.
```

Reason:

```text
A higher bonus fixes this one short action query, but it may also over-promote
action sections in broader cases. The next step is to add more action, cause,
and symptom evals across multiple runbooks before changing the default bonus.
```

## Broader Reranking Safety Experiment

The next experiment tests the same action-bonus question across multiple
runbooks and intents instead of only Lambda.

Run:

```powershell
python .\evaluate_reranking_broader.py
```

Scope:

```text
Runbooks tested: 4
Cases per bonus: 16
Intents: action, cause, symptom
```

Measured locally:

```text
Action bonus 0.10 -> expected-section Top-1: 7/16
Action bonus 0.15 -> expected-section Top-1: 9/16
Action bonus 0.20 -> expected-section Top-1: 11/16
Action bonus 0.22 -> expected-section Top-1: 11/16
Action bonus 0.25 -> expected-section Top-1: 11/16
```

Important diagnosis:

```text
Increasing the action bonus helps some action-intent cases, but it does not
fix all misses.
```

Why:

```text
1. RDS max-connection queries are blocked by the operational signal gate.
2. Kubernetes cause intent still ranks Overview above Probable Causes.
3. Some action queries need a stronger bonus, but that is only one failure type.
```

Current decision:

```text
Do not change the production action bonus yet.
```

Reason:

```text
The broader eval shows that reranking bonus is only part of the problem.
Before tuning defaults, fix or evaluate the signal gate for database connection
incidents and add more cause/action/symptom cases across the full runbook set.
```
