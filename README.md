# myers-pr-review-agent

A **selective, grounded, failure-aware** AI pull-request reviewer.

Not an AI replacement for a senior reviewer. It handles the mechanical parts of review
consistently, surfaces high-value findings *with cited evidence*, and **routes uncertain,
critical, or irreversible judgments to a human**.

> A PR review agent is not a linter with an LLM bolted on. It is a fan-out of specialist
> reasoners over a diff, grounded in retrieved codebase context, with every action written
> to one time-ordered spine — behind a confidence gate that hands hard calls to a human.

Built with **Genesis** (loop-based, AI-native development) on the **agentic-swe-kit**
20-phase production lifecycle. The design is ingested and traceable in [`.genesis/`](.genesis/).

## The improvement story (milestones)
1. **M1 — deterministic baseline reviewer** (this is what runs today): parse a diff → static
   checks → structured `Finding`s + a decision. The baseline we preserve and must beat.
2. **M2 — single LLM reviewer** behind a swappable `core.llm` interface, with cost/latency
   events and a hard budget guard.
3. **M3 — grounded specialist fan-out**: security / quality / tests / docs specialists run in
   parallel, each grounded by hybrid (semantic + exact-identifier) retrieval, merged by an aggregator.
4. **M4 — confidence-routed HITL** + full event-spine traces + baseline-vs-upgraded eval.

See [`.genesis/PLAN.md`](.genesis/PLAN.md) for the sprint plan and demo commands, and
[`.genesis/wiki/`](.genesis/wiki/) for the ingested architecture, ADRs, and failure matrices.

## Quick start (local, zero paid services)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m myers review examples/sample.diff     # M1 baseline review
python -m myers eval                             # score the golden PRs
pytest
```

## Status
M1 in progress. Production stack (Tiger Cloud spine, GitHub App, Next.js dashboard, Railway)
lands in a later sprint — everything through M4 runs locally.

## How it was built
Built by **Dheeraj** using **Genesis** — a loop-based, AI-native development method.
The system was designed from first principles, the architecture ingested into a durable
`.genesis/` spine (definition-of-done gates, a context graph with invariants, a milestone
plan with runnable demo commands, and a wiki of ADRs, schema, and failure matrices), then
implemented milestone-by-milestone through BUILD → VERIFY loops on the agentic-swe-kit
20-phase production lifecycle.
