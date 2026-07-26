# Failure matrix (per-component loop)

For each component: purpose & contract → assumptions → failure modes → prevention/detection
→ recovery/safe degradation → test & observable evidence. Filled in as each milestone builds
the component. `[M1]` = covered now; later tags = planned.

## Ingress & queue  (M4 / beyond)
- Failure: forged webhook · replayed delivery · slow LLM times out the endpoint · queue backpressure.
- Prevent/detect: HMAC-SHA256 verify · idempotency on X-GitHub-Delivery · enqueue then 200 fast · dead-letter.
- Recover: drop duplicates; retries with backoff; extract ingress+worker at measured scale (ADR-002).
- Evidence: tests reject bad signature & replayed delivery; event row per enqueue.

## Diff parsing  `[M1]`
- Contract: unified diff → files→hunks→changed lines with correct NEW-file line numbers.
- Failure: renames · new/deleted files · binary files · empty/malformed hunks · CRLF · very large diffs.
- Prevent/detect: strict hunk-header parse; skip binary with a recorded note; cap size.
- Recover: unparseable file → recorded skip, review continues on the rest (degrade, don't crash).
- Evidence: `tests/test_diffing.py` covers rename/new/delete/binary/multi-hunk.

## Reviewers / specialists  `[M1 baseline, M2 llm, M3 fan-out]`
- Contract: emit `List[Finding]` against the frozen schema; every upgraded finding cites a chunk.
- Failure: hallucination in a critical path · correlated-agent hallucination · specialist timeout/stall.
- Prevent/detect: citation requirement + "I don't know" allowed; independent prompts; per-node timeout.
- Recover: on stall → partial completion with a recorded degradation; deterministic severity/routing.
- Evidence: FakeLLM determinism test; timeout test; dedup-records-agreement test.

## Retrieval / grounding  (M3)
- Failure: stale/poisoned context (chunk describes refactored code) · missing context · irrelevant top-k.
- Prevent/detect: freshness index (last_indexed_at) + incremental re-embed; provenance on every citation; hybrid RRF.
- Recover: no relevant chunk → finding downgraded to low confidence / withheld, not fabricated.
- Evidence: recall check on golden retrieval set; provenance present on every M3 finding.

## Aggregation & HITL  (M3/M4)
- Failure: conflicting findings · miscalibrated confidence · human-queue overload · false CRITICAL blocks merge.
- Prevent/detect: dedup keeps highest confidence + notes agreement; deterministic confidence gate;
  escalation-rate monitoring + queue prioritization.
- Recover: uncertain/critical/irreversible → human queue (never auto-post); dispute path removes a bad review.
- Evidence: gate routing tests; escalation-rate metric on the spine.

## Data / proof / economics  (M2 events, M4 trace)
- Failure: cost blowout · un-reconstructable review · lost audit trail.
- Prevent/detect: append-only events; BudgetGuard hard-block (ADR-004); per-span cost.
- Recover: budget exceeded → block before the call, degrade to baseline static review.
- Evidence: `trace <review_id>` reconstructs the run; BudgetGuard block test.

## Evaluation & learning  (M1 baseline, M4 report)
- Failure: silent regression · overfit to golden set · feedback-loop poisoning.
- Prevent/detect: golden PRs with labeled expected findings; precision/recall; regression gate on precision drop.
- Recover: gate blocks the change; min-evidence threshold + decay on feedback.
- Evidence: `eval --report` prints baseline-vs-upgraded; regression gate fails a seeded regression.
