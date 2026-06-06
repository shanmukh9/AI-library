# Ops Intelligence Agent

An applied AI learning project for CloudOps alert analysis. The current Week 1 baseline sends synthetic operational alerts to a local Gemma model through LM Studio, parses the structured JSON response, and compares predicted severity with a synthetic expected label.

## Weekly Build Notes

The [12-week engineering diary](docs/weeks/README.md) records each increment,
its measurements, limitations, and the concepts worth recollecting later.
Start with the [Week 1 retrospective](docs/weeks/week-01-llm-foundations.md).

## Current Status

- Week 1: local structured alert analysis baseline complete.
- Week 2: runbook RAG baseline complete locally.

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
Retrieval eval:          6/6
Retrieval hit rate:      100.0%
RAG-backed severity:     3/3 on selected P1 alerts
```

The retriever filters weak chunks below `0.60` similarity so unrelated top-k
results do not pollute the LLM context.

The generated vector index is ignored by Git. Rebuild it locally with
`python .\index_runbooks.py` after changing runbook content.
