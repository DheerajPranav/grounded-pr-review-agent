"""The degrade-safe invariant: a failing/stalled agent must not sink the whole review."""

import time

from myers.agents import BaselineAgent
from myers.agents.base import Agent
from myers.orchestrator import ReviewPipeline

DIFF = (
    "diff --git a/a.py b/a.py\nnew file mode 100644\n--- /dev/null\n+++ b/a.py\n"
    "@@ -0,0 +1,1 @@\n+print('hi')\n"
)


class ExplodingAgent(Agent):
    name = "exploding"

    def review(self, diff):
        raise RuntimeError("boom")


class StallingAgent(Agent):
    name = "stalling"

    def review(self, diff):
        time.sleep(5)
        return []


def test_failing_agent_is_degraded_not_fatal():
    pipeline = ReviewPipeline([BaselineAgent(), ExplodingAgent()], "specialists")
    review = pipeline.review_text(DIFF)
    # the baseline's finding still lands; the exploding agent is recorded as degraded
    assert any(f.rule_id == "debug-print" for f in review.findings)
    assert any("exploding" in d for d in review.degraded)


def test_stalled_agent_times_out_and_degrades():
    pipeline = ReviewPipeline([BaselineAgent(), StallingAgent()], "specialists", agent_timeout_s=0.2)
    review = pipeline.review_text(DIFF)
    assert any("stalling" in d for d in review.degraded)
    # review still completed with the baseline's findings
    assert any(f.rule_id == "debug-print" for f in review.findings)


def test_events_reconstruct_the_review():
    pipeline = ReviewPipeline([BaselineAgent()], "baseline")
    review = pipeline.review_text(DIFF, review_id="rid-1")
    events = pipeline.events.for_review("rid-1")
    kinds = [e.event_type for e in events]
    assert "span.start" in kinds and "decision" in kinds and "span.end" in kinds
