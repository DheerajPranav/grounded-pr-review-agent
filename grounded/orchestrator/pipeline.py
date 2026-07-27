"""Review pipeline — drives one review end to end.

Flow: parse diff -> fan out agent(s) via the workflow engine (parallel, per-node timeout,
partial completion) -> aggregate -> emit events -> Review. One agent (M1/M2) or four
grounded specialists (M3) run through the SAME engine and aggregator — the Finding contract
is the only interface between them.

Failure-mode discipline: a stalled/failing node degrades to a recorded partial result; the
join never hangs. Cost lands on the spine; the BudgetGuard hard-blocks before spend (ADR-004).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from grounded.agents.base import Agent
from grounded.aggregation import Aggregator
from grounded.core.context import ReviewContext
from grounded.diffing.parser import parse_unified_diff
from grounded.economics import BudgetGuard
from grounded.models import Review
from grounded.observability import EventLog
from grounded.orchestrator.local_engine import FanoutInput, LocalFanoutEngine
from grounded.security import scan_injection

DEFAULT_AGENT_TIMEOUT_S = 30.0


class ReviewPipeline:
    def __init__(self, agents: list[Agent], mode: str, *, events: EventLog | None = None,
                 agent_timeout_s: float = DEFAULT_AGENT_TIMEOUT_S,
                 daily_cap_usd: float | None = None,
                 retriever: Callable[[str, int], list] | None = None) -> None:
        self.agents = agents
        self.mode = mode
        self.events = events or EventLog()
        self.aggregator = Aggregator()
        self.engine = LocalFanoutEngine(node_timeout_s=agent_timeout_s)
        self.retriever = retriever
        self.budget = (
            BudgetGuard(daily_cap_usd, self.events.total_cost) if daily_cap_usd is not None else None
        )

    def review_text(self, diff_text: str, *, review_id: str | None = None) -> Review:
        review_id = review_id or str(uuid.uuid4())
        started = time.time()
        self.events.record(review_id, "pipeline", "span.start", payload={"mode": self.mode})

        diff = parse_unified_diff(diff_text)
        for err in diff.parse_errors:
            self.events.record(review_id, "diffing", "tool.call", outcome="parse_error",
                               payload={"error": err})

        # Prompt-injection guard: if the change tries to talk to the reviewer, force a human.
        injection = scan_injection("\n".join(a.content for _, a in diff.added_lines))
        if injection:
            self.events.record(review_id, "security", "decision",
                               outcome="prompt_injection_detected", payload={"patterns": injection})

        def emit_span(**kw) -> None:
            self.events.record(review_id, kw.pop("agent"), kw.pop("event_type"), **kw)

        fan = self.engine.run(review_id, FanoutInput(
            agents=self.agents, diff=diff,
            context_for=lambda name: self._context_for(review_id, name),
            emit_span=emit_span,
        ))

        # Preserve agent order for deterministic aggregation.
        agent_findings = [fan.results[a.name] for a in self.agents if a.name in fan.results]
        review = self.aggregator.merge(review_id, self.mode, agent_findings)
        review.degraded = fan.degraded
        if injection and not review.escalated:
            review.escalated = True
            review.escalation_reason = (
                f"prompt injection detected ({', '.join(injection)}) — routed to a human"
            )
        review.latency_ms = int((time.time() - started) * 1000)
        review.cost_usd = self.events.total_cost()

        self.events.record(review_id, "aggregator", "decision",
                           outcome=review.decision.value, confidence=review.overall_confidence)
        if review.escalated:
            self.events.record(review_id, "aggregator", "escalation",
                               outcome="human_queue", payload={"reason": review.escalation_reason})
        self.events.record(review_id, "pipeline", "span.end", outcome=review.decision.value,
                           latency_ms=review.latency_ms)
        return review

    def _context_for(self, review_id: str, agent_name: str) -> ReviewContext:
        def emit(**kw) -> None:
            self.events.record(review_id, kw.pop("agent", agent_name),
                               kw.pop("event_type", "tool.call"), **kw)

        return ReviewContext(
            review_id=review_id,
            emit=emit,
            check_budget=(self.budget.check if self.budget is not None else ReviewContext.check_budget),
            retrieve=(self.retriever if self.retriever is not None else ReviewContext.retrieve),
        )
