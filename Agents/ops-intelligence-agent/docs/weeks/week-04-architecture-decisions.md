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
| `checkout HTTP 504` | Retrieval OK after 504 coverage | Keep 504-specific runbook coverage and monitor confusion with 502 | 504 first failed at the gate, then borrowed 502 evidence, and now retrieves the 504 runbook after dedicated coverage was added. |
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
checkout HTTP 504        -> retrieves HTTP 504 Gateway Timeout evidence after dedicated runbook coverage
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
Action bonus 0.10 -> expected-section Top-1: 10/16
Action bonus 0.15 -> expected-section Top-1: 13/16
Action bonus 0.20 -> expected-section Top-1: 15/16
Action bonus 0.22 -> expected-section Top-1: 15/16
Action bonus 0.25 -> expected-section Top-1: 15/16
```

Important diagnosis:

```text
Increasing the action bonus helps some action-intent cases, but it does not
fix all misses.
```

Why:

```text
1. RDS max-connection queries now pass the signal gate and reach retrieval.
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
Before tuning defaults, add more cause/action/symptom cases across the full
runbook set and resolve the remaining cause-ranking miss.
```

## Failure Stage Diagnosis Evaluator

The next Week 4 artifact diagnoses where a case failed in the pipeline instead
of only checking whether the final retrieval result is correct.

Run:

```powershell
python .\evaluate_failure_stage_diagnosis.py
```

Measured locally:

```text
Cases:                   5
Stage diagnosis matches: 5/5
```

Stages covered:

| Query | Diagnosed stage | Best first fix |
| --- | --- | --- |
| `RDS max database connections reached` | `retrieval_ok` | Keep controlled database max-connection signal coverage. |
| `how do I fix Lambda timeout?` | `wrong_section_after_retrieval` | Evaluate reranking weight, action-intent handling, or section wording. |
| `checkout HTTP 504` | `retrieval_ok` | Keep 504-specific runbook coverage and monitor confusion with 502. |
| `certificate error` | `ambiguous_but_retrieved` | Clarify the alert or add broader certificate troubleshooting coverage. |
| `db maxed connections` | `retrieval_ok` | Keep controlled query expansion and monitor false positives. |

This corrected an earlier assumption:

```text
checkout HTTP 504 was first blocked by the signal gate.
After adding 504 as a controlled signal, it reached retrieval but borrowed 502 evidence.
After adding a 504 runbook, it retrieves the 504 evidence.
```

Architect lesson:

```text
Diagnose the earliest failed stage first. Do not tune reranking when the query
never reached retrieval.
```

## Signal-Gate Coverage Experiment

After the failure-stage evaluator showed database and 504 cases were blocked
too early, the signal gate was expanded carefully.

Run:

```powershell
python .\evaluate_signal_gate_coverage.py
```

Measured locally:

```text
Cases:           10
Correct:         10/10
False negatives: 0
False positives: 0
```

What changed:

```text
1. Added `504` as a controlled operational signal.
2. Added narrow regex patterns for database max-connection incidents.
3. Did not add broad words like `connection`, `database`, `HTTP`, or `certificate`.
```

Why:

```text
Broad words increase false positives.
Controlled phrases improve recall without letting normal text enter retrieval.
```

Resulting stage change:

```text
RDS max database connections reached
    before -> blocked_by_signal_gate
    after  -> retrieval_ok

checkout HTTP 504
    before -> blocked_by_signal_gate
    after signal fix -> wrong_runbook_after_retrieval
    after 504 runbook -> retrieval_ok
```

This is progress: each fix moved the failure downstream until the query
retrieved grounded 504 evidence.

## 504 Runbook Coverage Fix

The 504 failure became clear only after the signal gate allowed `504` through.
The retriever then borrowed neighboring 502 evidence, which showed that the
knowledge base needed a 504-specific runbook.

Added:

```text
runbooks/http-504-gateway-timeout.md
```

Rebuilt:

```powershell
python .\index_runbooks.py
```

Measured locally:

```text
Runbook chunks:            35
Expanded Top-1 accuracy:   12/12
Expanded Top-3 hit rate:   12/12
Negative no-match:         2/2
504 direct Top-1 source:   http-504-gateway-timeout.md
504 direct similarity:     0.8986
```

Memory hook:

```text
When retrieval chooses the closest wrong document, the fix is usually better
knowledge coverage, not reranking.
```
