# Ops Intelligence Agent

An applied AI learning project for CloudOps alert analysis. The current Week 1 baseline sends synthetic operational alerts to a local Gemma model through LM Studio, parses the structured JSON response, and compares predicted severity with a synthetic expected label.

## Weekly Build Notes

The [12-week engineering diary](docs/weeks/README.md) records each increment,
its measurements, limitations, and the concepts worth recollecting later.
Start with the [Week 1 retrospective](docs/weeks/week-01-llm-foundations.md).

## Visual Learning

Open the [OIA Visual Operating System](docs/visuals/week2-rag-motion.html)
in a browser to move week by week through the project. It currently visualizes
the Week 1 LLM baseline, Week 2 Runbook RAG layer, and complete Week 3
advanced-retrieval pipeline, including normalization, expansion, metadata,
fallback, reranking, and the grounded LLM chain.

## Current Status

- Week 1: local structured alert analysis baseline complete.
- Week 2: runbook RAG baseline complete locally.
- Week 3: advanced RAG complete locally.

## Week 1 Baseline

Current flow:

```text
Synthetic CloudOps alert
        |
        v
System prompt + alert text
        |
        v
Local Gemma inference through LM Studio
        |
        v
Model-generated JSON text
        |
        v
Markdown cleanup + JSON parsing
        |
        v
Predicted severity compared with severity_hint
```

Measured baseline:

```text
Alerts tested:          3
Valid parsed responses: 3/3
Severity label matches: 3/3
```

This is an initial learning baseline, not a production accuracy claim. The dataset is small and synthetic.

## Run Locally

1. Start LM Studio.
2. Load the local Gemma chat model.
3. Start LM Studio's local server at `http://localhost:1234`.
4. Run:

```powershell
python .\basic_chain.py
```

## Week 1 Quick Reference

### LLM Generation Path

The current baseline uses this path:

```text
Alert text
    |
    v
Chat-model tokenization
    |
    v
Model context window
    |
    v
Internal attention over token relationships
    |
    v
Generated JSON response
```

### Future RAG Retrieval Path

Week 2 will add a separate retrieval path before generation:

```text
Alert query
    |
    v
Embedding model
    |
    v
Query vector
    |
    v
Cosine similarity search
    |
    v
Relevant runbook or incident chunks
    |
    v
Chunks inserted into chat-model context window
    |
    v
Local Gemma response generation
```

The key distinction:

```text
Embedding model -> finds semantically related external context before the LLM call
Attention       -> connects token relationships inside the chat LLM during generation
```

### Concepts

| Concept | Quick meaning | OIA connection |
| --- | --- | --- |
| Token | A small unit of text processed by a model | Alert text, instructions, and retrieved runbook chunks consume tokens |
| Context window | The bounded amount of input available to the chat model during one request | RAG should inject useful chunks instead of stuffing every runbook into the prompt |
| Inference | Running a trained model to generate an output | LM Studio runs the loaded Gemma model locally |
| Embedding | A numerical vector representing semantic meaning | Future incident and runbook retrieval will compare meaning, not only exact keywords |
| Vector space | A mathematical space where semantically related vectors tend to be closer | Similar incidents should rank above unrelated incidents |
| Cosine similarity | A measure of vector-direction similarity | Used to rank the most relevant historical incidents or runbook chunks |
| RAG | Retrieve relevant external context before asking the chat model to answer | Grounds recommendations in runbooks and incident history |
| Attention | An internal model mechanism that weighs relationships between tokens in the current context | Helps the LLM connect a deployment, timestamp, service, and failure symptom |
| Structured output | A machine-readable response format such as JSON | Downstream code can parse and validate the analysis |

### AIOps Example

```text
Production alert
    |
    v
Retrieve similar incidents and relevant runbook chunks
    |
    v
Send concise context to the chat model
    |
    v
Generate probable root cause, severity, and remediation guidance
    |
    v
Apply deterministic safety policy and human approval before any risky action
```

## Important Safety Note

`model_confidence` is the model's qualitative opinion. It is not calibrated probability and must not authorize operational actions.

Future safety decisions should use:

```text
retrieval evidence + deterministic policy checks + human approval
```

## Cosine Similarity Demo

Run:

```powershell
python .\cosine_sim_demo.py
```

Measured locally with `text-embedding-nomic-embed-text-v1.5`:

```text
Vector dimensions: 768

Related pair:
"CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"
"High processor utilization detected on the production API node"
Similarity: 0.7274

Unrelated pair:
"CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"
"SSL certificate for api.internal.company.com expires in 7 days"
Similarity: 0.5487

Similarity gap: 0.1787
Result: PASS
```

The useful result is the ranking: the related pair scores higher than the unrelated pair. A fixed threshold such as `0.85` would be misleading because similarity ranges depend on the embedding model and the text.

## Next Step

Week 2 added runbook RAG so alert analysis can use retrieved operational
context rather than only the model's general training knowledge.

## Week 2 Runbook RAG

Current retrieval flow:

```text
CloudOps alert
    |
    v
Embedding model
    |
    v
Alert query vector
    |
    v
Cosine similarity against runbook chunk vectors
    |
    v
Top runbook evidence
    |
    v
Gemma chat model + severity policy
    |
    v
Structured JSON analysis
```

Build the local runbook index:

```powershell
python .\index_runbooks.py
```

Query the runbook retriever:

```powershell
python .\query_runbooks.py "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"
```

Evaluate retrieval:

```powershell
python .\evaluate_runbook_rag.py
```

Measured locally:

```text
Minimum similarity:      0.60
Top-1 accuracy:          6/6
Top-3 hit rate:          6/6
Negative no-match:       2/2
RAG-backed severity:     3/3 on selected P1 alerts
```

The retriever filters weak chunks below `0.60` similarity so unrelated top-k
results do not pollute the LLM context. The eval also includes a negative query
that should return no runbook evidence.

The generated vector index is ignored by Git. Rebuild it locally with
`python .\index_runbooks.py` after changing runbook content.

## Week 3 Query Expansion

Week 3 adds a deterministic query-expansion layer for terse operational
language. The goal is to translate vague alert shorthand into the language used
inside runbooks before embedding search runs.

Example:

```text
db maxed connections
    -> RDS connection pool exhausted max database connections reached

checkout throwing bad gateway
    -> ALB health checks failing 502 responses increasing checkout service
```

Compare baseline and expanded retrieval:

```powershell
python .\evaluate_runbook_rag.py --mode baseline
python .\evaluate_runbook_rag.py --mode expanded
```

Measured locally:

```text
Baseline top-1 accuracy:      6/11
Expanded top-1 accuracy:      11/11
Baseline top-3 hit rate:      6/11
Expanded top-3 hit rate:      11/11
Negative no-match:            2/2 in both modes
Minimum similarity:           0.60
```

The important lesson is restraint: `logs delayed` still returns no evidence
because the project does not yet contain a log-pipeline runbook. Missing
knowledge should be fixed by adding the right runbook, not by forcing a weak
retrieval match.

### Operational Signal Normalization

Controlled normalization canonicalizes equivalent failure wording before the
signal gate and embedding call:

```text
timed out
timing out
time out
times out
timed-out
    -> timeout
```

This preserves known meaning. It does not guess that vague wording such as
`lambda acting weird` means a timeout.

Evaluate the gate without calling LM Studio:

```powershell
python .\evaluate_signal_gate.py
```

Measured locally:

```text
Signal gate cases: 10/10
Timeout variants:  6/6 passed
Vague/normal text: 4/4 rejected
```

### Metadata Filtering

Runbooks also carry TOML metadata such as:

```toml
+++
platform = "aws-lambda"
category = "timeout"
+++
```

Use optional metadata filters to narrow the candidate set before cosine
similarity ranking:

```powershell
python .\query_runbooks.py "payment processor timeout failure" --platform aws-lambda
```

Measured locally, the platform filter reduced the search space from `30` chunks
to `5` while preserving the correct Lambda runbook as top-1. Filters are
optional because incorrect metadata can hide the correct evidence.

Choose strict or fallback metadata behavior:

```powershell
python .\query_runbooks.py "payment processor timeout failure" `
  --platform kubernetes `
  --metadata-mode strict

python .\query_runbooks.py "payment processor timeout failure" `
  --platform kubernetes `
  --metadata-mode fallback
```

Fallback mode retries all chunks when filtered candidates are empty or when
none pass `min_score`. It explicitly prints when fallback was used.

Evaluate the policy:

```powershell
python .\evaluate_metadata_filtering.py
```

Measured locally:

```text
Strict policy:   3/3 expected behaviors
Fallback policy: 3/3 expected behaviors
```

### Intent-Aware Reranking

Vector similarity retrieves relevant evidence. Optional reranking then adjusts
the order based on whether the query asks for causes, actions, or symptoms.

Compare modes:

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

Evaluate:

```powershell
python .\evaluate_reranking.py
```

Measured locally:

```text
Vector-only intent Top-1: 1/3
Reranked intent Top-1:    3/3
```

The rerank bonus changes ordering only after the original vector similarity
passes `min_score`; it cannot promote rejected evidence.

`basic_chain.py` enables reranking and sends the final Top 3 evidence chunks to
the chat model. The original alert remains the embedding query, while the
reranker separately receives the downstream task intent: root-cause analysis
and immediate action.

Bonuses are limited to the runbook with the strongest original vector match so
an unrelated source cannot win merely because it has a preferred section name.

Measured end to end:

```text
Selected P1 severity matches with reranked evidence: 3/3
```

Week 3 regression summary:

```text
Signal normalization:     10/10
Expanded retrieval:       11/11
Negative no-match:        2/2
Metadata strict/fallback: 3/3 and 3/3
Intent reranking:         1/3 -> 3/3
End-to-end severity:      3/3
```
