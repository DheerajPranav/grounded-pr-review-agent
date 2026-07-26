# Tiger schema — three lanes, one store (ingested DDL)

Reference DDL from the architecture study. Realized against Tiger Cloud at M3+/beyond-M4;
mirrored locally by an in-memory chunk store + a SQLite events table until then.
Canonical file (production): `scripts/migrations/2026-06-tiger-init.sql`.

## Lane 1 — Memory: `code_chunks`
```sql
CREATE TABLE IF NOT EXISTS code_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo TEXT NOT NULL,
  path TEXT NOT NULL,
  symbol TEXT,                     -- function/class name (nullable)
  chunk_index INT NOT NULL,        -- order within file
  content TEXT NOT NULL,
  embedding VECTOR(256) NOT NULL,  -- text-embedding-3-large, 256 dims
  token_count INT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS code_chunks_emb_idx
  ON code_chunks USING diskann (embedding vector_cosine_ops);
ALTER TABLE code_chunks
  ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX IF NOT EXISTS code_chunks_fts_idx
  ON code_chunks USING GIN (content_tsv);
-- upsert key so re-embed overwrites stale chunks
CREATE UNIQUE INDEX IF NOT EXISTS code_chunks_unique_idx
  ON code_chunks (repo, path, chunk_index);
```
Hybrid retrieval = DiskANN ANN over embeddings + FTS over `content_tsv`, merged by RRF.

## Lane 2 — Time: `agent_events` (hypertable)
```sql
CREATE TABLE IF NOT EXISTS agent_events (
  ts TIMESTAMPTZ NOT NULL,
  review_id UUID NOT NULL,
  agent TEXT NOT NULL,             -- security|quality|tests|docs|aggregator
  span_id UUID NOT NULL DEFAULT gen_random_uuid(),
  parent_span UUID,
  event_type TEXT NOT NULL,        -- span.start|span.end|llm.call|tool.call|decision|escalation
  model TEXT, tokens_in INT, tokens_out INT,
  cost_usd NUMERIC(10,6), latency_ms INT,
  outcome TEXT,                    -- approved|request_changes|critical_block|escalated
  confidence NUMERIC(4,3),
  payload JSONB
);
SELECT create_hypertable('agent_events', by_range('ts', INTERVAL '1 day'), if_not_exists => TRUE);
```

## Lane 3 — Rollups: continuous aggregates
```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_health_1m
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts) AS bucket, agent,
       count(*) FILTER (WHERE event_type='llm.call') AS llm_calls,
       sum(cost_usd) AS cost_usd,
       approx_percentile(0.95, percentile_agg(latency_ms)) AS p95_ms,
       count(*) FILTER (WHERE outcome='rejected')::float
         / NULLIF(count(*) FILTER (WHERE outcome IS NOT NULL),0) AS rejection_rate
FROM agent_events GROUP BY bucket, agent WITH NO DATA;
-- pr_cost_hourly: per-PR cost + token rollup, refreshed hourly
```
BudgetGuard reads `agent_health_1m` for the day's running cost; rising `rejection_rate`
per agent is the drift/calibration signal for continuous learning.

## Truth lane (ordinary relational, same DB, same transaction)
`pr_review_records` (one row/review), `finding_records` (one row/finding),
`hitl_reviews` (human review state), `hitl_feedback` (human feedback).

## Access styles
SQLAlchemy for normal relational work; asyncpg for hot paths (event inserts, chunk upserts).

## Credentials (never in source — `.env` only)
`GROQ_API_KEY` (LLM inference — free tier),
`TIGER_DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DB?sslmode=require`,
`GITHUB_APP_ID`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_PRIVATE_KEY_PATH`.

> **Provider note.** This implementation uses **Groq** (OpenAI-compatible, free tier) for
> LLM inference. Groq offers chat inference only — no embeddings endpoint — so the M3
> retrieval embeddings use a local embedding model, not a hosted one. The `VECTOR(256)`
> dimension in the DDL above is adjusted to whatever the chosen local embedder produces.
