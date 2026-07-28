# CURRENT — rolling state

**Status:** M1→M4 + production P1→P4 COMPLETE. Renamed to `grounded` / grounded-pr-review-agent.
**Last updated:** 2026-07-28

## Shipped
- **M1–M4** (local, runs free): deterministic baseline → single LLM (Groq) behind `core.llm` +
  BudgetGuard → grounded 4-specialist parallel fan-out behind `core.workflow_engine` + hybrid
  retrieval → confidence-routed HITL + prompt-injection/HMAC/idempotency + trace viewer + eval report.
- **Production P1–P4** (behind graceful fallbacks, lit up by credentials):
  - P1 FastAPI webhook ingress (HMAC+idempotency+enqueue+200 fast) → worker → GitHub post; ARQ-ready.
  - P2 Tiger/Postgres spine: migration DDL, async pool, event+truth repos, pgvector code store.
  - P3 API routers (economics/reviews/trace/HITL) + self-contained dashboard at `/`.
  - P4 Dockerfile, docker-compose (Tiger+Redis+app+worker), Procfile, railway.json, `grounded migrate`, SETUP.md.
- **79 tests pass, all offline.** `python -m grounded serve` boots; dashboard + /api verified.

## To go fully live (user's account-only steps — see SETUP.md)
- Groq key (have it, in .env — rotate it), a GitHub App (webhook secret + token), Tiger Cloud URL
  (`grounded migrate`), Railway deploy. Each is optional; the app degrades gracefully without it.

## Verified locally (no accounts)
- baseline/llm/specialists reviews; eval P=1.00/0.60/0.22 (measured); trace; HITL routing;
  FastAPI ingress with a fake GitHub client; dashboard + economics/HITL API.

## Not end-to-end verified (no local infra)
- Live Tiger writes/retrieval, live Redis/ARQ worker, real GitHub App webhook, Railway deploy —
  built + unit-tested behind fakes/fallbacks; verification is the SETUP.md checklist.

## Notes / decisions
- Provider: Groq (chat only); embeddings local. Commits: Dheeraj, no AI trailer. Public repo.
- Attribution: Dheeraj + Genesis only. No original-author/cohort/assignment references committed.
