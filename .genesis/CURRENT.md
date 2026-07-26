# CURRENT — rolling state

**Active milestone:** M1 COMPLETE (verified green) → next M2
**Loop phase:** M1 exited L4 VERIFY green; M2 not yet started
**Last updated:** 2026-07-27

## What exists (M1 shipped)
- Genesis spine (`.genesis/`) + architecture fully ingested into `wiki/`.
- Python modular monolith: core (interfaces+exceptions), models (frozen Finding contract),
  diffing (unified-diff parser), agents (deterministic baseline), aggregation (merge+dedup+gate),
  orchestrator (in-process pipeline with per-agent timeout + safe degradation),
  observability (append-only events spine), evaluation (golden PRs + precision/recall + regression gate), cli.
- **28 tests pass.** Demo commands runnable with zero paid services:
  - `python -m myers review examples/sample.diff` → 7 findings, CRITICAL secret escalated to human, exit 1.
  - `python -m myers eval` → precision=1.00 recall=1.00 f1=1.00 over 2 golden PRs.
  - `python -m myers eval --min-precision 0.9` → regression gate passes (exit 0).
- Standalone git repo; both source docs git-ignored.

## Next — M2: single LLM reviewer behind core.llm
- Implement an LLM reviewer emitting the same Finding contract, behind `core.llm` (FakeLLM already there for deterministic tests).
- Wire cost/latency events into the spine on every llm.call; add BudgetGuard hard-block (ADR-004).
- Extend eval to compare llm-vs-baseline on the golden set (the improvement story, measured).

## Notes / decisions
- Commits: author Dheeraj Pranav, NO AI co-author trailer. Push on each major milestone.
- Attribution: Dheeraj + Genesis only. No original-author/cohort/assignment references anywhere committed.
- Tiger Cloud / GitHub App / OpenAI remain gated to M3+/M2; everything through M1 runs locally.
