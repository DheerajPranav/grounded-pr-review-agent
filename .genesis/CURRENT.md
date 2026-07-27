# CURRENT — rolling state

**Active milestone:** M3 COMPLETE (verified green, live on Groq) → next M4
**Loop phase:** M3 exited L4 VERIFY green (all four gate items met, offline tests + live demo)
**Last updated:** 2026-07-27

## What exists (M1 + M2 + M3 shipped)
- Genesis spine + ingested architecture (`.genesis/`).
- M1: modular monolith, deterministic baseline reviewer, golden eval, events spine, HITL confidence gate.
- M2: single LLM reviewer on Groq behind `core.llm`; cost events + BudgetGuard (ADR-004).
- M3: **grounded specialist fan-out**:
  - `memory/`: `Embedder` interface + local `HashingEmbedder` (deterministic, offline), `InMemoryCodeStore`
    with hybrid retrieval (dense cosine + exact-identifier, RRF). Ingest from a diff or a repo dir.
  - `orchestrator/local_engine.py`: `LocalFanoutEngine` implements `core.workflow_engine` — runs the four
    specialists in PARALLEL with per-node timeout + partial-completion checkpoint (swap for LangGraph/Temporal).
  - `agents/specialists.py`: security/quality/tests/docs specialists (LLMReviewAgent scoped per domain,
    retrieval-grounded, category-filtered). Aggregator (built in M1) merges/dedups/records agreement.
- **49 tests pass, all offline** (FakeLLM). CLI: `--mode specialists [--repo DIR]`.

## Live demo (Groq, 2026-07-27)
- `python -m myers review examples/sample.diff --mode specialists --cap 0.50`
- 4 parallel calls, ~1s, **$0.0020**, 10 findings across all four domains; security+quality both catch the
  secret; tests flags untested paths; docs flags the missing docstring (agreement recorded); CRITICAL escalated.

## Next — M4: confidence-routed HITL + proof
- Human approval queue for CRITICAL/low-confidence/irreversible; escalation + dispute + feedback.
- Prompt-injection guard + (later) HMAC/idempotency on ingress; full event-spine trace viewer (`trace <id>`).
- Baseline-vs-upgraded eval report + regression gate on precision drop.

## Notes / decisions
- Provider: Groq (chat only). Embeddings are local (hashing vectorizer) behind a swappable interface.
- Commits: author Dheeraj Pranav, NO AI co-author trailer. Push per milestone. Public repo.
- Attribution: Dheeraj + Genesis only. No original-author/cohort/assignment references committed.
