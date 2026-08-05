# Week 06 - Pipeline Evaluation Engineering

> Status: Complete locally

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
Validated 23 pipeline cases
Splits: development=17, held_out=4, validation=2
Data contract: PASS
```

Week 6 used three evaluation lifecycles:

1. Development cases exposed failures and became permanent regressions.
2. Validation cases selected `top_k=3`, `candidate_k=5` over the noisier
   `top_k=5` alternative.
3. A fresh four-case held-out set was opened once after the adaptive
   configuration and shared signal semantics were frozen.

Earlier held-out cases that influenced implementation were moved into the
development split. This avoids presenting tuned examples as unbiased proof.

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

This result justified a fresh held-out evaluation. At that point it was not yet
enough evidence to change the main path in `basic_chain.py`.

## Shared Signal Semantics

The fresh held-out set exposed an important cross-stage consistency problem.
Retrieval found the required runbooks, but the signal gate and evidence
acceptance interpreted phrases such as `latency remains stable`, `error rate is
normal`, and `connections are exhausted` differently.

The final design centralizes asserted-signal interpretation in
`runbook_rag.py`. It now handles:

- prefix negation, such as `not AccessDenied`,
- healthy suffixes, such as `latency is normal`,
- optional metric nouns, such as `error rate is normal`,
- operational normalization, such as `connections are exhausted` becoming
  `connections exhausted`.

`evidence_acceptance.py` reuses the same asserted-signal function instead of
maintaining a second partially overlapping matcher. This is code reuse with a
safety purpose: all stages now agree on whether a signal is active.

## Final Held-Out Evaluation

The frozen configuration was:

```text
ranking mode: adaptive
top_k:        3
candidate_k:  5
retry depth:  10 candidates only when a credible multi-source query is missing
              a detected source
```

The fresh held-out cases covered a healthy metric beside an SSL incident, an
RDS and SSL conflict, unsupported Elasticsearch failure, and a fully healthy
API statement.

| Measure | Result |
| --- | ---: |
| Signal-gate decisions | 4/4 |
| Required sources found | 3/3 |
| Required-source coverage | 100% |
| Candidate-source precision | 75% |
| Evidence decisions | 4/4 |
| Accepted-source decisions | 4/4 |
| LLM-routing decisions | 4/4 |
| Unsafe LLM calls | 0 |

No adaptive retry was needed in this held-out run because precise chunk
retrieval already surfaced both required sources for the conflict case. That
is desirable: adaptive mode is a recovery path, not a mandatory second search.

## Main-Chain Promotion

`basic_chain.py` now uses adaptive Hybrid RRF retrieval with the frozen
configuration. Every result contains a compact retrieval trace with:

```text
requested ranking mode
resolved ranking mode
whether adaptive retry ran
detected, initial, missing, candidate, and accepted sources
evidence-acceptance decision
```

`evaluate_main_chain_routing.py` exercises the real local retrieval and routing
path while replacing only the slow chat-model call with a deterministic fake.
This verifies that Python, rather than the LLM, owns the routing policy.

```text
Routing scenarios: 5/5
Actual fake LLM calls: 1
Expected fake LLM calls: 1
```

The accepted single-source incident reached the model. Conflict,
no-coverage, and no-incident scenarios did not.

## Final Week 6 Decision

Adaptive retrieval is promoted to the local main chain because it recovered
known multi-source failures, preserved validation precision, passed the fresh
held-out routing decisions, and avoided unnecessary retries. Evidence
acceptance remains the trust boundary: retrieval proposes candidates, but only
an `accept` decision permits an LLM call.

## Learning

- A split describes which cases are being used; a metric describes how their
  results are measured.
- Repeatedly inspecting held-out failures creates evaluation leakage.
- Once a held-out case directly influences a code change, it must become a
  development or regression case.
- Stage-level results are more actionable than a single end-to-end percentage.
- Required-source coverage can be perfect while final routing is still wrong.
- Shared semantic interpretation across gates matters as much as retrieval
  ranking.
- Adaptive retrieval controls search breadth; evidence acceptance controls
  trust.
- Candidate precision must be measured alongside recall so irrelevant sources
  cannot hide behind a successful final decision.

## Known Limitations

1. The datasets are small, synthetic, and local; the results are learning
   evidence, not a production accuracy claim.
2. Raw candidate-source precision remains `68.4%` on development and `75%` on
   held-out data. Evidence acceptance contains this noise before generation,
   but retrieval precision remains an improvement target.
3. Deterministic incident profiles cannot yet represent every operational
   phrasing or service family.
4. Retrieval still depends on the local LM Studio embedding endpoint, while
   accepted generation depends on the local Gemma model.
