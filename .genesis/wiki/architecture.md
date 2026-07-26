# Architecture — the full system

```
GitHub PR
   │  webhook (pull_request)
   ▼
FASTAPI INGRESS ── HMAC verify · idempotency (X-GitHub-Delivery) ── 200 OK fast
   │  enqueue(review_job)
   ▼
Redis + ARQ queue        (decouples ingress from review — a slow LLM never times out the webhook)
   │
   ▼
ARQ WORKER → LangGraph engine (behind core.workflow_engine)
   │  build_context → Send API fan-out
   ├─ security  specialist ─┐
   ├─ quality   specialist ─┤  all run in PARALLEL, each grounded by hybrid retrieval
   ├─ tests     specialist ─┤  each returns List[Finding]
   └─ docs      specialist ─┘
   ▼
AGGREGATOR — merge · dedup (keep highest confidence, note agreement) · score overall_confidence
   ▼
HITL confidence gate — confident & no CRITICAL → post_to_github ; else → human approval queue
   ▼
GitHub review posted            Next.js dashboard reads continuous aggregates

Beneath everything: Tiger Cloud · TimescaleDB (one managed Postgres)
  · pgvectorscale · DiskANN · code_chunks (memory)
  · agent_events hypertable, partitioned by 1 day (time)
  · agent_health_1m · pr_cost_hourly continuous aggregates (rollups)
  · relational truth tables (pr_review_records, finding_records, hitl_*)
Redis stays as queue + LangGraph checkpoint store.  Deployed on Railway.
```

## The retrieval path (grounding)
Diff → embed (text-embedding-3-large, 256-dim) → run **both** DiskANN ANN search over
embeddings **and** FTS (GIN) keyword search over `content_tsv` on the same `code_chunks`
table → **reciprocal-rank fusion** → top-k chunks into the specialist prompt.
Vector search catches meaning; FTS catches exact identifiers (function names, error codes,
config keys). `repo_file_index.last_indexed_at` drives incremental re-embedding.

## The events spine (proof)
Every span/LLM call/tool call/decision is one append-only row in `agent_events`.
Three consumers read that one table: **trace viewer** (`WHERE review_id=$1 ORDER BY ts`),
**audit trail** (immutable by construction), **cost ledger** (reads continuous aggregates;
so does BudgetGuard, which hard-blocks before an LLM call when the daily cap is exceeded).

## How this maps to our build (local-first)
- Ingress/queue/LangGraph/Tiger are the **production** shape (M3+ / beyond-M4).
- M1–M2 realize the same reasoning locally: a CLI drives `build_context → review → aggregate → gate`
  in-process, retrieval is in-memory, events go to SQLite, LLM is behind `core.llm`.
- The seams (`core.workflow_engine`, `core.llm`, memory backend) are where the production
  swaps happen — one file each, per ADR-001/003.
