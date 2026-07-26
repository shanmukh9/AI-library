# OIA Weekly Build Notes

These notes capture how the Ops Intelligence Agent evolves one week at a time.

Use them to:

- recollect concepts a few months later
- explain the project incrementally in interviews
- preserve measured results before the architecture grows
- separate completed work from future plans

| Week | Focus | Status |
| --- | --- | --- |
| [Week 01](week-01-llm-foundations.md) | LLM foundations, structured output, local embeddings, cosine similarity | Complete |
| [Week 02](week-02-runbook-rag.md) | Runbook RAG | Complete locally |
| [Week 03](week-03-advanced-rag.md) | Normalization, expansion, metadata, fallback, and reranking | Complete locally |
| [Week 04](week-04-architecture-decisions.md) | Retrieval evaluation and architecture decisions | Complete locally |
| [Week 05](week-05-tool-calling.md) | Hybrid retrieval and evidence acceptance | Complete locally |
| [Week 06](week-06-evaluation-engineering.md) | Pipeline evaluation contracts, dataset splits, and stage metrics | In progress |
| [Week 07](week-07-agent-specialization.md) | Agent specialization only if justified | Planned |
| [Week 08](week-08-incident-memory.md) | Similar-incident memory | Planned |
| [Week 09](week-09-mcp-server.md) | MCP server | Planned |
| [Week 10](week-10-evals-guardrails.md) | Evals, guardrails, and observability | Planned |
| [Week 11](week-11-fastapi-docker.md) | FastAPI and Docker | Planned |
| [Week 12](week-12-portfolio-packaging.md) | Demo, architecture, and portfolio packaging | Planned |

## Weekly Writing Rule

Update only the week you are actively building. Record:

```text
what existed before
what you changed
what you measured
what you learned
what remains limited
```

Do not document future features as if they already exist.
