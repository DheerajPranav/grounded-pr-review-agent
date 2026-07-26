# CURRENT — rolling state

**Active milestone:** M1 — Deterministic baseline reviewer
**Loop phase:** L1 BUILD
**Last updated:** 2026-07-26

## What exists
- Genesis spine scaffolded (`.genesis/`): DONE.html, context-graph.json, PLAN.md, LOOPS.md, wiki/.
- Architecture fully ingested from the two source docs into `wiki/` (ADRs, Tiger schema, module map, failure matrix).
- Standalone git repo; both source docs git-ignored.

## In progress
- M1: Python modular-monolith skeleton (models/, core/, diffing/) + deterministic baseline reviewer + golden eval + tests.

## Next
- M1 VERIFY (separate pass) against DONE.html Section 2 → M1 gate green.
- Then M2 (single LLM reviewer behind `core.llm`).

## Notes / decisions
- Commits: author Dheeraj Pranav, NO AI co-author trailer. Push on each major milestone.
- Everything in M1–M2 runs locally with zero paid services; Tiger Cloud / GitHub App / OpenAI are gated to M3+.
