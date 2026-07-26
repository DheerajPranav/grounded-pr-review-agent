# Module map + 20-phase roadmap (ingested)

## The 23 modules of the monolith (ADR-002, inward-only deps)
| Module | Files | Purpose |
|---|---|---|
| agents/ | base_agent, contracts, security_agent, quality_agent, test_agent, docs_agent | 4 specialists + shared base + Finding contract |
| api/ | reviews, economics_router, hitl_router, queue, schemas | REST endpoints |
| auth/ | dependencies | RBAC deps for FastAPI |
| core/ | workflow_engine, exceptions | abstract orchestration interface + shared exceptions |
| data/ | ingestion, freshness | code-chunk ingestion + re-embed freshness |
| database/ | postgres, models, repository | async engine + Tiger pool + init schema; ORM; repos |
| economics/ | cost_repository, budget, routing_advisor | aggregate reads; BudgetGuard; model routing |
| evaluation/ | golden_dataset, judge, regression_gate | golden PRs, LLM-as-judge, regression gate |
| hitl/ | queue, escalation, feedback, dispute | approval queue, escalation, feedback, dispute |
| integrations/ | github_client, github_models | GitHub REST wrapper + payload models |
| job_queue/ | arq_worker | ARQ worker consuming review jobs |
| memory/ | tiger_client, embedder, context_retriever, redis_client | pgvectorscale+hybrid, embedding, retrieval, cache |
| models/ | enums, findings, review, webhook | Pydantic: Finding, Review, WebhookEvent, enums |
| observability/ | events, tracing, audit, alerting, logging, workflow_context | emit_agent_event → hypertable; OTel; audit; alerts |
| orchestrator/ | graph, nodes, state, langgraph_engine | LangGraph StateGraph, nodes, typed state, engine impl |
| prompts/ | registry, templates/ | prompt registry + versioned prompt files |
| reliability/ | retry, circuit_breaker, idempotency, timeout | the reliability mechanics |
| security/ | threat_model, injection_guard, rbac, masking | threat model, injection guard, RBAC, secret masking |
| tools/ | tool_registry, model_router, llm_client, sandbox, capability_scope | tool catalog, routing, LLM client, Docker sandbox, scoping |
| webhook_receiver/ | validator, parser, router | HMAC validation, parsing, routing to queue |
| migrations | scripts/migrations/2026-06-tiger-init.sql | idempotent schema DDL |
| frontend/ | src/app, components, lib | Next.js dashboard, HITL queue, trace viewer, economics |

> Our local build implements a pragmatic subset first (core, models, diffing, agents,
> memory, observability, economics, evaluation, hitl, security, cli) and grows toward the
> full surface. Names are kept aligned so production modules drop in behind the seams.

## The Finding contract (frozen at M1)
`agent_type · severity · category · summary · file_path · line_start/line_end · suggestion
· confidence · rationale · evidence[]`. Structured output is what makes the aggregator merge
DATA, not prose.

## 20-phase build roadmap (each phase proves one thing, ends green)
0 Cognitive Design · 1 System Architecture · 2 Frontend · 3 Backend & API ·
4 Workflow Orchestration · 5 LLM & Reasoning · 6 Memory (Tiger) · 7 Tooling & Sandboxing ·
8 Multi-Agent · 9 Evaluation · 10 Observability (Tiger) · 11 Security · 12 Reliability ·
13 Infrastructure (Tiger) · 14 Data Engineering (Tiger) · 15 Governance · 16 Economics (Tiger) ·
17 Developer Experience · 18 CI/CD for AI · 19 Human-in-the-Loop · 20 Continuous Learning (Tiger).

Our milestone ladder collapses these into M1 (0,1,3) → M2 (5,10,16) → M3 (4,6,8) → M4 (9,11,12,19),
with 13/14/17/18/20 in the beyond-M4 production sprint.

## Tiger integration plan (ADR-003, 4 staged phases)
A·Infra (provision, run migration, verify extensions) · B·Events (wire emit_agent_event) ·
C·Memory (retire qdrant, hybrid retrieval on code_chunks) · D·Dashboard (aggregate endpoints).
Greenfield migration — no live data — each phase leaves the system green.
