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

## Quick start

### Baseline reviewer (zero setup, no API key)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m myers review examples/sample.diff     # M1 deterministic baseline review
python -m myers eval                             # score the golden PRs (precision/recall)
pytest                                           # full test suite
```

### LLM reviewer (M2 — uses Groq, free tier)
The LLM reviewer runs on **[Groq](https://console.groq.com)** (OpenAI-compatible, free API key).
```bash
pip install -e ".[llm]"                          # installs the groq client
cp .env.example .env                             # then paste your key into .env
export GROQ_API_KEY=...                          # or `source .env`
python -m myers review examples/sample.diff --mode llm --cap 0.50
```
`--cap` sets a daily budget; the LLM is hard-blocked once spend reaches it (BudgetGuard, ADR-004).
Every LLM call is recorded to the events spine with its model, tokens, and cost. Tests never call
Groq — they use a deterministic `FakeLLM`, so the suite stays free and offline.

### Grounded specialist fan-out (M3)
Four specialists — **security / quality / tests / docs** — run in **parallel**, each grounded by
hybrid retrieval (dense + exact-identifier) over a code memory, merged by the aggregator.
```bash
python -m myers review examples/sample.diff --mode specialists --cap 0.50
python -m myers review path/to.diff --mode specialists --repo /path/to/checkout   # ground on a real repo
```
Since Groq has no embeddings API, retrieval uses a local, deterministic embedder (no extra key,
no model download) behind a swappable `Embedder` interface — a neural embedder or Tiger pgvector
drops in later without changing the specialists.

## Status
- **M1 — deterministic baseline reviewer:** ✅ done.
- **M2 — single LLM reviewer (Groq) behind a swappable interface, with cost events + BudgetGuard:** ✅ done.
- **M3 — grounded specialist fan-out (parallel, per-node timeout, retrieval-grounded):** ✅ done.
- **M4 — confidence-routed HITL + trace viewer + baseline-vs-upgraded eval report:** next.

Production stack (Tiger Cloud spine, GitHub App, Next.js dashboard, Railway) lands in a later
sprint — everything through M4 runs locally. See [`.genesis/CURRENT.md`](.genesis/CURRENT.md) for live status.

## How it was built
Built by **Dheeraj** using **Genesis** — a loop-based, AI-native development method.
The system was designed from first principles, the architecture ingested into a durable
`.genesis/` spine (definition-of-done gates, a context graph with invariants, a milestone
plan with runnable demo commands, and a wiki of ADRs, schema, and failure matrices), then
implemented milestone-by-milestone through BUILD → VERIFY loops on the agentic-swe-kit
20-phase production lifecycle.
