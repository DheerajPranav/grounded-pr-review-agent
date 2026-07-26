# CURRENT — rolling state

**Active milestone:** M2 COMPLETE (verified green, provider: Groq) → next M3
**Loop phase:** M2 exited L4 VERIFY green; one item (live LLM-vs-baseline eval) needs the user's GROQ_API_KEY
**Last updated:** 2026-07-27

## What exists (M1 + M2 shipped)
- Genesis spine + ingested architecture (`.genesis/`).
- M1: modular monolith, deterministic baseline reviewer, golden eval, events spine, HITL confidence gate.
- M2: **single LLM reviewer on Groq** (OpenAI-compatible, free tier), behind `core.llm`:
  - `tools/GroqLLMClient` (lazy import, GROQ_API_KEY, per-model cost); `FakeLLM` for offline tests.
  - `agents/LLMReviewAgent`: grounded-or-nothing (drops findings whose cited line isn't in the diff),
    prompt-injection-aware (diff is untrusted data), allows "I don't know".
  - `core/ReviewContext` seam (emit / check_budget / retrieve) + `economics/BudgetGuard` (ADR-004 hard-block).
  - Pipeline wires cost events onto the spine; `--cap` enforces a daily budget.
- **37 tests pass**, all offline. `.env.example` documents GROQ_API_KEY.

## To finish the last M2 checkbox (needs the user)
- Get a free key at https://console.groq.com, `export GROQ_API_KEY=...`, then:
  - `pip install -e ".[llm]"`
  - `python -m myers eval --mode llm --cap 0.50`  → records the live LLM-vs-baseline numbers.

## Next — M3: grounded specialist fan-out
- Four specialists (security/quality/tests/docs) behind `core.workflow_engine`, run in parallel.
- Hybrid retrieval for grounding (Groq has no embeddings API → use a local embedder).
- Aggregator already merges/dedups/scores N agents (built in M1) — reuse it.

## Notes / decisions
- Provider: **Groq** (replaced any OpenAI/GPT references). Chat inference only; embeddings for M3 are local.
- Commits: author Dheeraj Pranav, NO AI co-author trailer. Push on each major milestone.
- Attribution: Dheeraj + Genesis only. No original-author/cohort/assignment references committed.
