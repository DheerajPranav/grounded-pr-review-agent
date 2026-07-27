"""The human-in-the-loop approval queue (autonomy level: 'human handles exceptions').

The confidence gate lives in the aggregator (it sets review.escalated). This queue acts on it:
a confident, non-critical review is AUTO_POSTED; an escalated one is held PENDING for a human,
who approves or rejects it. Disputes remove/flag a bad finding; feedback is captured as the
continuous-learning signal. Every human action is written to the SAME events spine as the
review, so a trace shows the full story including the human decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from grounded.models import Review
from grounded.observability import EventLog


class TicketStatus(str, Enum):
    AUTO_POSTED = "auto_posted"   # confident, no CRITICAL -> posted without a human
    PENDING = "pending"           # escalated -> waiting on a human
    APPROVED = "approved"         # human approved the (possibly edited) review
    REJECTED = "rejected"         # human rejected it


class HumanDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class ReviewTicket:
    review_id: str
    mode: str
    status: TicketStatus
    escalated: bool
    reason: str
    n_findings: int
    reviewer: str = ""
    note: str = ""
    disputes: list[dict] = field(default_factory=list)
    feedback: list[dict] = field(default_factory=list)


class ApprovalQueue:
    def __init__(self, events: EventLog | None = None) -> None:
        self.events = events
        self._tickets: dict[str, ReviewTicket] = {}

    def _emit(self, review_id: str, outcome: str, **payload) -> None:
        if self.events is not None:
            self.events.record(review_id, "hitl", "decision", outcome=outcome, payload=payload)

    def submit(self, review: Review) -> ReviewTicket:
        """Route a completed review: hold for a human if escalated, else auto-post."""
        status = TicketStatus.PENDING if review.escalated else TicketStatus.AUTO_POSTED
        ticket = ReviewTicket(
            review_id=review.review_id, mode=review.mode, status=status,
            escalated=review.escalated, reason=review.escalation_reason,
            n_findings=len(review.findings),
        )
        self._tickets[review.review_id] = ticket
        self._emit(review.review_id, status.value, reason=review.escalation_reason)
        return ticket

    def pending(self) -> list[ReviewTicket]:
        return [t for t in self._tickets.values() if t.status is TicketStatus.PENDING]

    def get(self, review_id: str) -> ReviewTicket | None:
        return self._tickets.get(review_id)

    def decide(self, review_id: str, decision: HumanDecision, reviewer: str, note: str = "") -> ReviewTicket:
        ticket = self._require(review_id)
        if ticket.status is not TicketStatus.PENDING:
            raise ValueError(f"ticket {review_id} is {ticket.status.value}, not pending")
        ticket.status = TicketStatus.APPROVED if decision is HumanDecision.APPROVE else TicketStatus.REJECTED
        ticket.reviewer = reviewer
        ticket.note = note
        self._emit(review_id, f"human_{ticket.status.value}", reviewer=reviewer, note=note)
        return ticket

    def dispute(self, review_id: str, rule_id: str, reason: str) -> ReviewTicket:
        ticket = self._require(review_id)
        ticket.disputes.append({"rule_id": rule_id, "reason": reason})
        self._emit(review_id, "disputed", rule_id=rule_id, reason=reason)
        return ticket

    def feedback(self, review_id: str, useful: bool, note: str = "") -> ReviewTicket:
        ticket = self._require(review_id)
        ticket.feedback.append({"useful": useful, "note": note})
        self._emit(review_id, "feedback", useful=useful, note=note)
        return ticket

    def _require(self, review_id: str) -> ReviewTicket:
        ticket = self._tickets.get(review_id)
        if ticket is None:
            raise KeyError(f"no ticket for review {review_id}")
        return ticket
