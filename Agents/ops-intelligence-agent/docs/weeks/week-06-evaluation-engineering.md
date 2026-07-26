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
Validated 10 pipeline cases
Splits: development=8, held_out=0, validation=2
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

## Learning

- A split describes which cases are being used; a metric describes how their
  results are measured.
- Repeatedly inspecting held-out failures creates evaluation leakage.
- Once a held-out case directly influences a code change, it must become a
  development or regression case.
- Stage-level results are more actionable than a single end-to-end percentage.

## Remaining Work

1. Evaluate conditional source discovery on development and validation cases.
2. Keep normal single-incident queries on precise chunk ranking.
3. Design and freeze a fresh held-out set.
4. Run the final selected policy once against that fresh held-out split.
