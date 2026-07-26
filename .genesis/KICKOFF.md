# KICKOFF — myers-pr-review-agent

**Cognitive job (one line):** selectively review a PR diff, surface high-value findings
each grounded in cited code, and route uncertain/critical/irreversible calls to a human.

**Current milestone:** M1 — deterministic baseline reviewer.
**Demo of done:** `python -m myers review examples/sample.diff` prints structured Findings + a decision.

**First loop:** G0 pre-flight (read CURRENT.md) → L1 BUILD the diff parser + Finding contract
+ static-check baseline agent + CLI + golden eval → L2 self-check (`pytest`, demo) → L4 VERIFY.

**Read before building:** `wiki/index.md` (ingested architecture), `DONE.html` (gates),
`context-graph.json` (invariants + dependency rule).

**Non-negotiables:** one Finding contract; deterministic decisions stay deterministic;
import inward only; degrade slower-but-correct; commit as Dheeraj Pranav, no AI trailer.
