# Two-Minute Demo Guide

## Before Recording

1. Load a Gemma chat model in LM Studio.
2. Load `text-embedding-nomic-embed-text-v1.5` if showing Vector RAG.
3. Start LM Studio's local server.
4. Run `.\scripts\start.ps1`.
5. Open `http://127.0.0.1:8765`.

Use sanitized notes during any public recording.

## Walkthrough

### 0:00 - Problem

"Daily notes are often messy and easy to abandon. I built a private local AI reflection agent that turns rough notes into one useful review without sending personal data to a cloud API."

### 0:20 - Daily Flow

Paste:

```text
- Finished work tasks
- Watched an AI talk but delayed coding
- Took a short evening walk
- Want to build one visible artifact tomorrow
```

Choose `Fast`, click `Reflect`, and point out the loading state, structured response, score explanation, tomorrow promise, and auto-save.

### 0:55 - Personalized Deep Mode

Choose `Deep`, select `Vector`, enable RAG debug, and reflect again. Explain that:

- private Markdown notes were embedded locally at index time
- today's notes are embedded locally at query time
- cosine similarity selects the most relevant chunks
- the model receives only a small bounded context

### 1:25 - Memory and Review

Open History and Insights. Show local reflection history, behavior signals, and the weekly review action. Return to Reflect and use one Review Mode button such as `Tiny steps`.

### 1:50 - Security Boundary

Open Privacy and explain:

- localhost-only server
- per-launch API token
- origin checks
- SQLite local memory
- Git-ignored private notes and indexes

## Closing Line

"This project taught me how to take a personal workflow from idea to local AI product: UX, structured output, vector RAG, retrieval evals, memory, privacy hardening, and latency tradeoffs."
