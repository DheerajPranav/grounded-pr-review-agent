# CURRENT — rolling state

**Active milestone:** M4 COMPLETE (verified green) — the M1→M4 sprint is DONE.
**Loop phase:** all four milestone gates green (offline tests + live Groq runs).
**Last updated:** 2026-07-27

## Shipped (M1 → M4)
- M1: modular monolith, deterministic baseline reviewer, golden eval, events spine, confidence gate.
- M2: single LLM reviewer on Groq behind `core.llm`; cost events + BudgetGuard (ADR-004).
- M3: grounded specialist fan-out (4 specialists, parallel, per-node timeout) behind `core.workflow_engine`;
  hybrid retrieval (dense + exact, RRF) over a local code memory.
- M4: confidence-routed HITL:
  - `hitl/ApprovalQueue`: auto-post vs enqueue; decide (approve/reject); dispute; feedback — all on the spine.
  - `security/`: prompt-injection guard (forces escalation), HMAC verify (constant-time), idempotency store.
  - `observability/trace.py` + `myers trace <id> --events`: full review reconstruction from the spine.
  - `reports/eval_baseline_vs_upgraded.md` + JSON; `--min-precision` regression gate.
- **62 tests pass, all offline** (FakeLLM). CLI: review (baseline|llm|specialists), eval (+--report, --min-precision), trace.

## Measured (live on Groq, 2026-07-27)
- baseline P=1.00 R=1.00 · llm P=0.60 R=0.75 · specialists P=0.22 R=1.00.
- Recall rises toward the fan-out; precision trades off → resolved by the HITL confidence gate + human triage.
- Cost ≈ $0.0005 (llm) / $0.0020 (specialists) per review; ~1s.

## Beyond M4 (separate production sprint — needs paid accounts)
Tiger Cloud spine (pgvector/hypertables/continuous aggregates), real GitHub App webhook + posting,
Next.js dashboard, Railway deploy, CI/CD eval gates. The seams (`core.workflow_engine`, `core.llm`,
memory `Embedder`/store, `security` ingress primitives) are already in place for these to drop in.

## Notes / decisions
- Provider: Groq (chat only); embeddings local behind a swappable interface.
- Commits: author Dheeraj Pranav, NO AI trailer. Public repo. Attribution: Dheeraj + Genesis only.
