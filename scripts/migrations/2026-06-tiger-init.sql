-- grounded-pr-review-agent — Tiger Cloud / TimescaleDB schema (ADR-003)
-- Idempotent: safe to re-run. Three lanes in one Postgres-compatible store:
--   memory (code_chunks + pgvector/pgvectorscale), time (agent_events hypertable),
--   rollups (continuous aggregates), and ordinary relational truth tables.
-- The embedding dim (256) matches the default local HashingEmbedder so the same code path
-- works locally and on Tiger; swap the embedder and the VECTOR(n) dim together.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale;

-- ---------------------------------------------------------------- Lane 1: memory
CREATE TABLE IF NOT EXISTS code_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo TEXT NOT NULL,
  path TEXT NOT NULL,
  symbol TEXT,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(256) NOT NULL,
  token_count INT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS code_chunks_emb_idx
  ON code_chunks USING diskann (embedding vector_cosine_ops);
ALTER TABLE code_chunks
  ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX IF NOT EXISTS code_chunks_fts_idx ON code_chunks USING GIN (content_tsv);
CREATE UNIQUE INDEX IF NOT EXISTS code_chunks_unique_idx ON code_chunks (repo, path, chunk_index);

-- freshness: only re-embed files that changed
CREATE TABLE IF NOT EXISTS repo_file_index (
  repo TEXT NOT NULL,
  path TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  last_indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (repo, path)
);

-- ---------------------------------------------------------------- Lane 2: time
CREATE TABLE IF NOT EXISTS agent_events (
  ts TIMESTAMPTZ NOT NULL,
  review_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  span_id UUID NOT NULL DEFAULT gen_random_uuid(),
  parent_span UUID,
  event_type TEXT NOT NULL,
  model TEXT,
  tokens_in INT,
  tokens_out INT,
  cost_usd NUMERIC(10,6),
  latency_ms INT,
  outcome TEXT,
  confidence NUMERIC(4,3),
  payload JSONB
);
SELECT create_hypertable('agent_events', by_range('ts', INTERVAL '1 day'), if_not_exists => TRUE);

-- ---------------------------------------------------------------- Lane 3: rollups
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_health_1m
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts) AS bucket, agent,
       count(*) FILTER (WHERE event_type = 'llm.call') AS llm_calls,
       sum(cost_usd) AS cost_usd,
       approx_percentile(0.95, percentile_agg(latency_ms)) AS p95_ms,
       count(*) FILTER (WHERE outcome = 'rejected')::float
         / NULLIF(count(*) FILTER (WHERE outcome IS NOT NULL), 0) AS rejection_rate
FROM agent_events GROUP BY bucket, agent WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS pr_cost_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', ts) AS bucket, review_id,
       sum(cost_usd) AS total_cost_usd,
       count(DISTINCT agent) AS agents_used,
       max(confidence) AS max_confidence
FROM agent_events GROUP BY bucket, review_id WITH NO DATA;

-- ---------------------------------------------------------------- Truth (ordinary relational)
CREATE TABLE IF NOT EXISTS pr_review_records (
  review_id TEXT PRIMARY KEY,
  repo TEXT NOT NULL,
  pr_number INT NOT NULL,
  mode TEXT NOT NULL,
  decision TEXT NOT NULL,
  overall_confidence NUMERIC(4,3),
  escalated BOOLEAN NOT NULL DEFAULT FALSE,
  cost_usd NUMERIC(10,6),
  latency_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS finding_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id TEXT NOT NULL REFERENCES pr_review_records(review_id) ON DELETE CASCADE,
  rule_id TEXT NOT NULL,
  agent_type TEXT NOT NULL,
  category TEXT NOT NULL,
  severity TEXT NOT NULL,
  summary TEXT NOT NULL,
  file_path TEXT NOT NULL,
  line_start INT NOT NULL,
  line_end INT NOT NULL,
  confidence NUMERIC(4,3) NOT NULL
);

CREATE TABLE IF NOT EXISTS hitl_reviews (
  review_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  reviewer TEXT,
  note TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hitl_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id TEXT NOT NULL,
  useful BOOLEAN NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
