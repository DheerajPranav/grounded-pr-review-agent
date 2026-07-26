# LOOPS — how work happens here

Loops prompt the agent, not the human. Each milestone runs the same cycle.

## G0 — Existence Pre-Flight (before any BUILD)
- Read `CURRENT.md`. Confirm which milestone is active and its DONE.html gate.
- Confirm the freeze boundary of the previous milestone is respected (don't churn frozen files).
- Confirm the demo command exists and is runnable (or is the thing this loop creates).

## L1 — BUILD
- Implement the smallest slice that moves the active milestone's gate toward green.
- Every new component records: purpose & contract → assumptions → failure modes →
  prevention/detection → recovery/degradation → test + observable evidence
  (the brief's failure-mode loop; see `wiki/failure-matrix.md`).
- Keep the dependency rule: import inward only.

## L2 — SELF-CHECK (maker)
- Run `pytest` and the milestone demo command. Fix reds.

## L3 — CHECKPOINT
- Update `CURRENT.md` (what changed, what's next). On a major change, commit + push
  (as Dheeraj Pranav, no AI trailer) and note the SHA.

## L4 — VERIFY (separate pass — never the maker grading itself)
- A fresh pass (new context or a subagent) checks each DONE.html checkbox for the
  milestone against actual evidence (test output, demo output, event rows).
- Only the verifier flips a gate to green. If red, write why in `CURRENT.md` and loop back to L1.

## Stop / advance
- Milestone advances only when its DONE.html gate is fully green per the verifier.
- Then update `CURRENT.md` to the next milestone and re-run G0.
