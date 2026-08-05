# Week 06 - Pipeline Evaluation Engineering

> Status: In progress

## Goal

Move from several isolated evaluation scripts to one stage-by-stage contract for
the complete OIA decision pipeline:

```text
query
  -> signal gate
  -> hybrid retrieval
  -> evidence acceptance
  -> LLM routing decision
```

The objective is not to maximize one accuracy number. It is to identify where a
failure happened and whether the system should retrieve, clarify, abstain, or
call the LLM.

## What Changed

- `evals/pipeline_cases.json` defines expected behaviour for complete scenarios.
- `validate_pipeline_cases.py` validates the evaluation-data contract.
- `evaluate_pipeline.py` measures the real pipeline stage by stage.
- `--top-k` and `--candidate-k` support controlled retrieval experiments.
- `--split` isolates development, validation, and held-out evaluation cases.
- Retrieval evaluation reports both required-source recall and candidate-source
  precision so extra irrelevant evidence cannot hide behind 100% coverage.

## Dataset Splits

| Split | Purpose | Usage rule |
| --- | --- | --- |
| Development | Build and debug the pipeline | May be run repeatedly and used for code changes |
| Validation | Compare candidate configurations | Use to choose between alternatives such as `top_k=3` and `top_k=5` |
| Held-out | Final unbiased evaluation | Keep sealed until the configuration is frozen |

Memory hook:

> Development builds. Validation chooses. Held-out proves.

Normal evaluation defaults to the development split:

```powershell
python .\evaluate_pipeline.py
python .\evaluate_pipeline.py --split development
python .\evaluate_pipeline.py --split validation
python .\evaluate_pipeline.py --split held_out
```

Running every split requires an explicit choice:

```powershell
python .\evaluate_pipeline.py --split all
```

## Current Evidence

The data-contract validator currently reports:

```text
Validated 11 pipeline cases
Splits: development=9, held_out=0, validation=2
Data contract: PASS
```

The first held-out round covered a supported RDS incident, an RDS and IAM
conflict, unsupported DynamoDB throttling, and a healthy DynamoDB statement.
The frozen `top_k=3`, `candidate_k=5` configuration produced:

```text
Signal gate: 4/4
Required-source recall: 66.7%
Candidate-source precision: 66.7%
Decision and LLM-routing accuracy: 3/4
```

The RDS and IAM conflict retrieved only the RDS source, so evidence acceptance
incorrectly allowed the LLM. Because this result now influences development,
the consumed held-out cases have become development regression cases. A fresh
held-out set is required for the next final evaluation.

## Validation Decision

Two configurations were compared using only the validation split:

| Configuration | Required-source recall | Candidate-source precision | Decision accuracy |
| --- | --- | --- | --- |
| `top_k=3` | 100% | 100% | 2/2 |
| `top_k=5` | 100% | 75% | 2/2 |

`top_k=5` introduced `lambda-timeout.md` for the SSL and IAM conflict without
improving recall or the final decision. The frozen configuration for held-out
evaluation is therefore `top_k=3`, with `candidate_k=5`.

## Experimental Source-Level Ranking

The held-out failure showed that the first three fused chunks can all come from
one runbook. An experimental `source` ranking mode now:

1. retrieves a deeper candidate pool,
2. groups fused chunks by runbook source,
3. sums up to three RRF chunk scores per source,
4. sends one representative candidate from each top-ranked source to evidence
   acceptance.

It is evaluation-only; the production chain still uses normal chunk ranking.

```powershell
python .\evaluate_pipeline.py --split development --top-k 3 --candidate-k 10 --ranking-mode chunk
python .\evaluate_pipeline.py --split development --top-k 3 --candidate-k 10 --ranking-mode source
```

Measured comparison:

| Split | Mode | Source recall | Source precision | Final decisions | Irrelevant sources |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | Chunk | 66.7% | 80% | 6/8 | 1 |
| Development | Source | 100% | 50% | 8/8 | 6 |
| Validation | Chunk | 100% | 100% | 2/2 | 0 |
| Validation | Source | 100% | 50% | 2/2 | 3 |

Source aggregation recovered the Lambda/IAM and RDS/IAM conflicts, but it
substantially increased irrelevant evidence. It is therefore not promoted to
the global default. The next hypothesis is conditional source discovery only
when the query contains credible signals for multiple incident categories.

## Conditional Ranking Experiment

The next experiment used negation-aware incident-profile detection:

```text
zero or one active supported incident source -> chunk ranking
two or more active supported sources        -> source ranking
```

The development set added:

```text
Lambda timed out, but logs confirm it was not AccessDenied.
```

The router correctly detected only `lambda-timeout.md`; the negated IAM signal
did not trigger source ranking.

Measured comparison with `top_k=3` and `candidate_k=10`:

| Split | Mode | Source recall | Source precision | Final decisions |
| --- | --- | ---: | ---: | ---: |
| Development | Chunk | 71.4% | 83.3% | 7/9 |
| Development | Conditional | 100% | 70% | 9/9 |
| Validation | Chunk | 100% | 100% | 2/2 |
| Validation | Conditional | 100% | 75% | 2/2 |

Conditional routing fixed the known Lambda/IAM and RDS/IAM development
conflicts, but it broadened the already-correct SSL/IAM validation case and
introduced `lambda-timeout.md` without improving the decision.

The policy is therefore not promoted to `basic_chain.py`. A stronger next
hypothesis is adaptive retry:

1. run precise chunk ranking first,
2. compare retrieved sources with the active incident sources detected in the
   query,
3. retry with source aggregation only when a multi-signal query is missing an
   expected source,
4. send the resulting candidates to evidence acceptance.

## Adaptive Retry Experiment

Adaptive mode preserves precise retrieval as the first attempt:

```text
chunk retrieval
  -> compare active incident sources with retrieved sources
  -> retry with source aggregation only when a multi-signal query is missing
     at least one detected source
  -> evidence acceptance makes the final trust decision
```

The retry uses `candidate_k=10`; non-retried queries remain at `candidate_k=5`.

Measured comparison:

| Split | Mode | Source recall | Source precision | Final decisions | Retries |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | Chunk | 71.4% | 71.4% | 7/9 | 0 |
| Development | Adaptive | 100% | 63.6% | 9/9 | 2 |
| Validation | Chunk | 100% | 100% | 2/2 | 0 |
| Validation | Adaptive | 100% | 100% | 2/2 | 0 |

Adaptive mode retried only the Lambda/IAM and RDS/IAM development conflicts.
It did not retry the already-correct SSL/IAM validation case or the negated IAM
development case. This recovered conflict evidence without reducing validation
precision.

The result supports creating a fresh held-out evaluation, but it is not yet
enough evidence to change the production path in `basic_chain.py`.

## Learning

- A split describes which cases are being used; a metric describes how their
  results are measured.
- Repeatedly inspecting held-out failures creates evaluation leakage.
- Once a held-out case directly influences a code change, it must become a
  development or regression case.
- Stage-level results are more actionable than a single end-to-end percentage.

## Remaining Work

1. Design and freeze a fresh held-out set.
2. Run chunk and adaptive policies once against that set.
3. Promote adaptive retry only if held-out decisions improve without an
   unacceptable precision or latency regression.
4. Record the final Week 6 architecture decision.
