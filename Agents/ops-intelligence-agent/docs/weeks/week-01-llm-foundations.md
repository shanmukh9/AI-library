# Week 01 - LLM Foundations and Project Launch

> Status: Complete

## Goal

Create the smallest measurable Ops Intelligence Agent baseline:

```text
synthetic CloudOps alert
-> local chat model
-> structured JSON
-> parse and validate
-> compare predicted severity with synthetic label
```

## What It Does

The current baseline reads CloudOps alerts from `data/alerts.json` and returns structured JSON with:

- probable root cause
- severity classification: `P1`, `P2`, or `P3`
- model confidence: qualitative display-only opinion
- immediate-action recommendation

## Sample Input

```json
{
  "id": "ALT001",
  "text": "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes",
  "service": "api",
  "severity_hint": "P1"
}
```

## Sample Output

```json
{
  "root_cause": "The API server is experiencing critical resource saturation, likely due to unexpected traffic spikes or an inefficient process loop.",
  "severity": "P1",
  "model_confidence": 0.98,
  "immediate_action": "Scale out the affected service and investigate current request metrics for unusual endpoints."
}
```

The sample output is illustrative local-model output. It is not an approved production action.

## Measured Results

| Check | Result |
| --- | --- |
| Synthetic alerts created | `15` |
| Parsed structured responses | `3/3` |
| Severity matches on selected P1 alerts | `3/3` |
| Embedding vector dimensions | `768` |
| Related CPU/API alert similarity | `0.7274` |
| Unrelated CPU/certificate alert similarity | `0.5487` |
| Cosine similarity gap | `0.1787` |

All metrics were measured locally with synthetic data.

## Architecture - Current State

```text
data/alerts.json
       |
       v
basic_chain.py
       |
       v
System prompt + alert text
       |
       v
LM Studio OpenAI-compatible API
       |
       v
Local Gemma chat model
       |
       v
Model-generated JSON text
       |
       v
Wrapper cleanup + json.loads()
       |
       v
Severity comparison with severity_hint
```

The embedding experiment is separate:

```text
alert pair
   |
   v
LM Studio embeddings endpoint
   |
   v
Nomic embedding model
   |
   v
768-dimensional vectors
   |
   v
Manual cosine-similarity calculation
```

## Concepts Learned

| Concept | What I should remember |
| --- | --- |
| Token | Models process text as smaller token units, not as complete sentences |
| Context window | Alert text, instructions, and future retrieved chunks compete for bounded input space |
| Inference | LM Studio runs an already-trained local model to generate output |
| Structured output | Model text becomes useful to code only after cleanup, parsing, and validation |
| Embedding | A separate model converts text into a numerical meaning representation |
| Vector space | Semantically related texts tend to produce closer vectors |
| Cosine similarity | A ranking signal that compares vector direction |
| Attention | Internal chat-model mechanism for weighing token relationships in the active context |

Important distinction:

```text
Embedding model -> retrieval before the chat-model call
Attention       -> contextual token relationships inside chat-model generation
```

## Safety Lesson

`model_confidence` is not calibrated probability. It must not authorize a restart, scaling operation, deletion, or any other risky action.

Future decision flow:

```text
retrieval evidence
-> deterministic policy checks
-> human approval for risky actions
```

## Files Added or Changed

```text
basic_chain.py
cosine_sim_demo.py
data/alerts.json
README.md
```

## Known Limits

- severity baseline uses only three selected P1 alerts
- labels are synthetic hints, not expert-reviewed ground truth
- JSON fields are cleaned and parsed but not yet validated with a typed schema
- recommendations come from general model knowledge, not retrieved runbooks
- cosine similarity is demonstrated on one related and one unrelated pair

## Next Week

Add runbook RAG:

```text
alert query
-> embed query
-> retrieve relevant runbook chunks
-> inject bounded context
-> generate a grounded recommendation
```
