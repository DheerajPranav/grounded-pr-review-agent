# ADRs — architecture decisions (ingested)

## ADR-001 — Orchestration: LangGraph now, Temporal later, behind an interface
**Need:** coordinate 4 parallel sub-agents, persist workflow state across steps, retry cleanly.
**Decision:** LangGraph for Phases 1–12 — runs in-process (zero extra infra), first-class parallel
fan-out via the Send API, checkpoints to the same Redis the queue uses, tight LLM tool-calling.
**Discipline:** a single abstract interface `core/workflow_engine.py` with `run / resume / get_state`.
All orchestrator code imports from `core.workflow_engine`, never LangGraph directly. If scale demands
Temporal (sustained >50 concurrent workflows/min, cross-service coordination, or Redis checkpointing
proves insufficient), write a Temporal impl of the same interface and swap one file.
**Generalizes:** defer the expensive decision; put it behind a narrow seam.

## ADR-002 — Modular monolith, inward-only dependencies
**Decision:** one process, 23 internal modules, dependency rule = outer depends inward only;
`core` depends on nothing; observability is cross-cutting (injected as middleware).
You can delete any outer module and the inner ones still compile.
**Scale answer:** if the trigger is *measured* (10k PRs/min), extract the webhook receiver as a
stateless ingress service and the orchestrator as a worker pool — the boundaries already exist.

## ADR-003 — One Tiger Cloud data spine (memory + truth + time)
**Decision:** collapse Qdrant (vectors) + a time-series store + Postgres (truth) into one
Postgres-compatible Tiger Cloud (TimescaleDB + pgvector + pgvectorscale). Three lanes, one store,
one PR identity tying memory ↔ truth ↔ time.
**Rejected:** keep Qdrant+Postgres (splits memory from audit truth); plain Postgres only (weak at
large vector memory + time-series rollups); ClickHouse/Jaeger (another durable store + failure mode).
**Kept separate:** Redis (queue/cache is short-lived high-churn; not the durable spine).
**Test of the rule:** consolidate only when the single store handles each shape *honestly* — name
the shapes, name the missing capabilities, verify the store has them.

## ADR-004 — Cost control: BudgetGuard hard-blocks
**Decision:** BudgetGuard reads the day's running cost from the `agent_health_1m` continuous
aggregate at the top of every agent run and hard-blocks before any LLM call if the daily cap is
exceeded. Cost is attributed per span. Model routing (cheap model for classification, reasoning
model for planning) reduces spend.
