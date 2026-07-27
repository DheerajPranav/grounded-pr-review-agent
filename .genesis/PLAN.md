# PLAN — grounded-pr-review-agent

The improvement story the design demands, sliced into milestones. Each milestone has a
**single outcome**, an **exact demo command** (its contract), a **freeze boundary**
(what M(n) locks so M(n+1) can't churn it), and **assigned agentic-swe-master skills**.

> lint/static baseline → single LLM reviewer → grounded specialist fan-out → confidence-routed HITL

This is a **multi-day sprint**, designed to pause/resume daily. Estimates assume focused sessions.

---

## M1 — Deterministic baseline reviewer  ·  Day 1 (this session)
- **Outcome:** a diff in → deterministic static-check Findings + a review decision out, with a golden-PR eval and tests. The baseline we must *preserve and beat*.
- **Demo:** `python -m grounded review examples/sample.diff`
- **Also:** `python -m grounded eval` (baseline precision/recall on the golden set) · `pytest`
- **Freeze:** the `Finding` contract (models/) and the diff parser (diffing/). Everything downstream emits this contract; changing it is a scope change via DONE.html.
- **Skills:** engineering-mindset, modular-architecture, production-readiness.
- **Failure modes covered:** deterministic-by-design (no hallucination surface yet); parser edge cases (renames, new files, binary, empty hunks).

## M2 — Single LLM reviewer behind an interface  ·  Day 1–2
- **Outcome:** one LLM reviewer that emits the same contract, behind `core.llm`, with cost/latency events and a BudgetGuard. Beats baseline on the golden set — measured.
- **Demo:** `python -m grounded review examples/sample.diff --mode llm`
- **Freeze:** the `core.llm` interface, the events schema, the BudgetGuard contract.
- **Skills:** llmops-ai-agents, production-readiness (Phases 5, 10, 16).
- **Failure modes:** hallucination (citation + "I don't know"), cost blowout (BudgetGuard), determinism-in-tests (FakeLLM).

## M3 — Grounded specialist fan-out  ·  Day 2–3
- **Outcome:** four specialists (security/quality/tests/docs) run in parallel behind `core.workflow_engine`, each grounded by hybrid retrieval, merged + deduped by the aggregator with a computed overall confidence.
- **Demo:** `python -m grounded review examples/sample.diff --mode specialists`
- **Freeze:** the workflow-engine interface, the retrieval interface, the aggregator merge rules.
- **Skills:** llmops-ai-agents, distributed-systems, data-systems-engineering (Phases 4, 6, 8).
- **Failure modes:** stale/poisoned context (freshness+provenance), correlated hallucination (dedup records agreement), orchestration deadlock (per-node timeout, partial completion).

## M4 — Confidence-routed HITL + proof  ·  Day 3–4
- **Outcome:** confidence gate routes CRITICAL/low-confidence to a human queue; ingress HMAC+idempotency+injection guard; full event-spine traces; baseline-vs-upgraded eval report + regression gate.
- **Demo:** `python -m grounded eval --report`  ·  `python -m grounded trace <review_id>`
- **Freeze:** the HITL policy, the eval report format, the regression threshold.
- **Skills:** security-engineering, llmops-ai-agents, production-readiness (Phases 9, 11, 12, 19).
- **Failure modes:** human-queue overload, prompt injection, ingress abuse, silent regression.

## Beyond M4 (production, needs paid accounts — separate sprint)
Tiger Cloud spine (pgvector/hypertables/continuous aggregates), GitHub App + real webhook,
Next.js dashboard, Railway deploy, CI/CD eval gates. These are the "13+ / infra" phases and
carry the external-account + cost dependencies.

---

## Loop discipline
Every milestone: **G0 existence pre-flight → L1 BUILD → L4 VERIFY (separate pass)**.
Do not open M(n+1) until M(n)'s DONE.html gate is green, graded by the verifier, not the maker.
