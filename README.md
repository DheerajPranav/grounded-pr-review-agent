# grounded-pr-review-agent

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
python -m grounded review examples/sample.diff     # M1 deterministic baseline review
python -m grounded eval                             # score the golden PRs (precision/recall)
pytest                                           # full test suite
```

### LLM reviewer (M2 — uses Groq, free tier)
The LLM reviewer runs on **[Groq](https://console.groq.com)** (OpenAI-compatible, free API key).
```bash
pip install -e ".[llm]"                          # installs the groq client
cp .env.example .env                             # then paste your key into .env
export GROQ_API_KEY=...                          # or `source .env`
python -m grounded review examples/sample.diff --mode llm --cap 0.50
```
`--cap` sets a daily budget; the LLM is hard-blocked once spend reaches it (BudgetGuard, ADR-004).
Every LLM call is recorded to the events spine with its model, tokens, and cost. Tests never call
Groq — they use a deterministic `FakeLLM`, so the suite stays free and offline.

### Grounded specialist fan-out (M3)
Four specialists — **security / quality / tests / docs** — run in **parallel**, each grounded by
hybrid retrieval (dense + exact-identifier) over a code memory, merged by the aggregator.
```bash
python -m grounded review examples/sample.diff --mode specialists --cap 0.50
python -m grounded review path/to.diff --mode specialists --repo /path/to/checkout   # ground on a real repo
```
Since Groq has no embeddings API, retrieval uses a local, deterministic embedder (no extra key,
no model download) behind a swappable `Embedder` interface — a neural embedder or Tiger pgvector
drops in later without changing the specialists.

### Human-in-the-loop + proof (M4)
Confident, non-critical reviews auto-post; CRITICAL / low-confidence / prompt-injection reviews
are **routed to a human approval queue**. Every action is on an append-only events spine, so any
review is fully reconstructable:
```bash
python -m grounded review path/to.diff --mode specialists --emit-events events.jsonl
python -m grounded trace <review_id> --events events.jsonl        # replay the whole review
python -m grounded eval --mode baseline --min-precision 0.9       # regression gate (CI)
```
See [`reports/eval_baseline_vs_upgraded.md`](reports/eval_baseline_vs_upgraded.md) for the measured
baseline-vs-upgraded comparison.

## Status — M1→M4 sprint complete ✅
- **M1 — deterministic baseline reviewer:** ✅
- **M2 — single LLM reviewer (Groq) behind a swappable interface, with cost events + BudgetGuard:** ✅
- **M3 — grounded specialist fan-out (parallel, per-node timeout, retrieval-grounded):** ✅
- **M4 — confidence-routed HITL + prompt-injection/HMAC/idempotency + trace viewer + eval report/regression gate:** ✅

## Production (P1–P4) ✅
The full production path is built and runs behind graceful fallbacks — it lights up the real
services when you add credentials, and runs in-process otherwise.
```bash
pip install -e ".[server]"
python -m grounded serve      # FastAPI webhook ingress on :8000, dashboard at http://localhost:8000
```
- **P1 — ingress:** FastAPI `POST /webhook/github` (HMAC verify + idempotency + enqueue, 200 fast),
  a worker (in-process BackgroundTask, or ARQ/Redis), and a GitHub client that posts the review.
- **P2 — data spine:** the Tiger Cloud / Postgres schema (`scripts/migrations/`), event + truth
  repositories, and a pgvector code store — all behind the same seams (in-memory fallback if unset).
- **P3 — dashboard + API:** a self-contained dashboard at `/` (cost, HITL queue, approve/reject) and
  `/api/*` routers (economics, reviews, trace, HITL).
- **P4 — deploy:** `Dockerfile`, `docker-compose.yml` (Tiger + Redis + app + worker), `Procfile`,
  `railway.json`.

**To go fully live** (Groq, a GitHub App, Tiger Cloud, Railway) follow [`SETUP.md`](SETUP.md).
See [`.genesis/CURRENT.md`](.genesis/CURRENT.md) for live status.

## How it was built
Built by **Dheeraj** using **Genesis** — a loop-based, AI-native development method.
The system was designed from first principles, the architecture ingested into a durable
`.genesis/` spine (definition-of-done gates, a context graph with invariants, a milestone
plan with runnable demo commands, and a wiki of ADRs, schema, and failure matrices), then
implemented milestone-by-milestone through BUILD → VERIFY loops on the agentic-swe-kit
20-phase production lifecycle.
