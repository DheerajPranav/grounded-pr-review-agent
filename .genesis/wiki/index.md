# Wiki — ingested architecture

Genesis "ingest before you implement". This wiki is the durable knowledge distilled from
the two source docs (git-ignored, kept local):
- `AI_PR_Review_Agent_Project_Brief.pdf` — the cohort execution checklist.
- `pr-review-agent.html` — the first-principles architecture study (Ayush Singh).

## Pages
- [architecture.md](architecture.md) — the full system, boxes earned from first principles.
- [adrs.md](adrs.md) — the four architecture decisions (LangGraph, modular monolith, Tiger spine, cost control).
- [tiger-schema.md](tiger-schema.md) — the three data lanes: memory / time / truth (real DDL).
- [module-map.md](module-map.md) — the 23 modules of the monolith + the 20-phase roadmap.
- [failure-matrix.md](failure-matrix.md) — per-component failure modes → prevention → recovery → evidence.

## agentic-swe-master concept pointers (loaded per phase)
- Phase 0 Cognitive Design → engineering-mindset. (done in DONE.html §1)
- Phase 1 Architecture / Phase 3 Backend → modular-architecture + production-readiness.
- Phase 4 Orchestration / 5 LLM / 6 Memory / 8 Multi-agent / 9 Eval → llmops-ai-agents (+ distributed, data).
- Phase 11 Security → security-engineering.
- Phase 10/12/16 Observability/Reliability/Economics → production-readiness.

## The one-sentence design
A PR review agent is not a linter with an LLM bolted on — it is a **fan-out of specialist
reasoners over a diff, grounded in retrieved codebase context, with every action written
to one time-ordered spine**, and a confidence gate that hands hard calls to a human.
