"""BudgetGuard (ADR-004): hard-block before spend; degrade to baseline, never fast-but-wrong."""

import json

import pytest

from grounded.agents import LLMReviewAgent
from grounded.core.exceptions import BudgetExceededError
from grounded.core.llm import FakeLLM, LLMClient, LLMResponse
from grounded.economics import BudgetGuard
from grounded.orchestrator import ReviewPipeline

DIFF = (
    "diff --git a/a.py b/a.py\nnew file mode 100644\n--- /dev/null\n+++ b/a.py\n"
    "@@ -0,0 +1,1 @@\n+password = \"p@ssw0rd123\"\n"
)
CANNED = json.dumps({"findings": [
    {"file_path": "a.py", "line": 1, "category": "security", "severity": "critical",
     "summary": "secret", "confidence": 0.9}
]})


class CostingLLM(LLMClient):
    """Fake client that reports a nonzero cost, to exercise cost attribution."""

    def complete(self, *, system, user, model=None):
        return LLMResponse(text=CANNED, model="stub", tokens_in=100, tokens_out=20, cost_usd=0.02)


def test_budget_guard_blocks_at_cap():
    spent = 0.0
    guard = BudgetGuard(daily_cap_usd=0.0, spent_source=lambda: spent)
    with pytest.raises(BudgetExceededError):
        guard.check()


def test_pipeline_blocks_llm_when_capped_and_degrades():
    # cap 0.0 -> the guard blocks before the (fake) call; the review still completes, degraded.
    pipeline = ReviewPipeline([LLMReviewAgent(FakeLLM(CANNED))], "llm", daily_cap_usd=0.0)
    review = pipeline.review_text(DIFF)
    assert any("llm" in d and "BudgetExceededError" in d for d in review.degraded)
    assert review.findings == []


def test_llm_call_cost_lands_on_the_spine():
    pipeline = ReviewPipeline([LLMReviewAgent(CostingLLM())], "llm")
    review = pipeline.review_text(DIFF, review_id="rid-cost")
    events = pipeline.events.for_review("rid-cost")
    assert any(e.event_type == "llm.call" and e.cost_usd == 0.02 for e in events)
    assert pipeline.events.total_cost() == 0.02
    assert review.cost_usd == 0.02  # attributed to the review


def test_second_call_blocked_after_budget_consumed():
    # Two LLM agents, cap just above one call: the first spends, the second is blocked.
    pipeline = ReviewPipeline(
        [LLMReviewAgent(CostingLLM()), LLMReviewAgent(CostingLLM())],
        "llm", daily_cap_usd=0.02,
    )
    review = pipeline.review_text(DIFF)
    assert any("BudgetExceededError" in d for d in review.degraded)
