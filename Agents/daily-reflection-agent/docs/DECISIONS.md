# Architecture Decisions

## 1. Local-First Inference

**Decision:** Use LM Studio instead of a cloud LLM API.

**Reason:** Reflection notes may contain private emotional, career, and health-adjacent details. Local inference makes the privacy boundary understandable and avoids an API-key requirement.

**Tradeoff:** Local generation can take 40-90 seconds depending on hardware and prompt depth.

## 2. Two Reflection Depths

**Decision:** Provide `Fast` and `Deep` paths.

**Reason:** A daily habit needs a low-friction path. Personalized context is valuable, but it should be an explicit choice when the user wants a deeper review.

**Tradeoff:** Fast mode is less personalized because it skips RAG, active goals, and recent history.

## 3. Keyword and Vector RAG

**Decision:** Keep both retrievers.

**Reason:** Keyword RAG is easy to inspect and provides a useful baseline. Vector RAG demonstrates semantic retrieval with local embeddings. The eval harness makes the comparison measurable.

**Tradeoff:** Vector RAG requires a second loaded model and a manually generated local index.

## 4. SQLite Memory

**Decision:** Store reflections, promise status, and goals in SQLite.

**Reason:** SQLite provides durable local memory with no external service and is appropriate for a single-user laptop application.

**Tradeoff:** A hosted product would need a different persistence and authentication design.

## 5. Calm Main UI, Optional Debug UI

**Decision:** Hide retrieval details unless the user enables Deep-mode RAG debug.

**Reason:** The primary experience should feel soothing and focused. Retrieval scores are useful while learning and debugging, but overwhelming during a normal daily reflection.

**Tradeoff:** Debug data is less discoverable for a first-time technical reviewer, so the README and demo guide make it explicit.
