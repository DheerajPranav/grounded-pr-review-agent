import pytest

from myers.hitl import ApprovalQueue, HumanDecision, TicketStatus
from myers.models import Decision, Review
from myers.observability import EventLog


def _review(escalated: bool) -> Review:
    return Review(
        review_id="r-esc" if escalated else "r-ok",
        mode="specialists",
        decision=Decision.REQUEST_CHANGES if escalated else Decision.APPROVE,
        escalated=escalated,
        escalation_reason="CRITICAL finding" if escalated else "",
    )


def test_confident_review_auto_posts():
    ticket = ApprovalQueue().submit(_review(escalated=False))
    assert ticket.status is TicketStatus.AUTO_POSTED


def test_escalated_review_is_held_pending():
    q = ApprovalQueue()
    ticket = q.submit(_review(escalated=True))
    assert ticket.status is TicketStatus.PENDING
    assert [t.review_id for t in q.pending()] == ["r-esc"]


def test_human_approve_and_reject():
    q = ApprovalQueue()
    q.submit(_review(escalated=True))
    t = q.decide("r-esc", HumanDecision.APPROVE, reviewer="dheeraj", note="looks fine")
    assert t.status is TicketStatus.APPROVED and t.reviewer == "dheeraj"
    assert q.pending() == []


def test_cannot_decide_twice():
    q = ApprovalQueue()
    q.submit(_review(escalated=True))
    q.decide("r-esc", HumanDecision.REJECT, reviewer="d")
    with pytest.raises(ValueError):
        q.decide("r-esc", HumanDecision.APPROVE, reviewer="d")


def test_dispute_and_feedback_recorded_to_spine():
    events = EventLog()
    q = ApprovalQueue(events=events)
    q.submit(_review(escalated=True))
    q.dispute("r-esc", rule_id="llm-security", reason="false positive")
    q.feedback("r-esc", useful=False, note="noisy")
    outcomes = {e.outcome for e in events.for_review("r-esc")}
    assert {"pending", "disputed", "feedback"} <= outcomes
