"""In-process review pipeline (M1 engine).

Flow: parse diff -> run agent(s) -> aggregate -> emit events -> Review.
Built to accept a LIST of agents so the M3 specialist fan-out reuses it unchanged; the
only difference there is four agents behind the LangGraph engine instead of one in-process.

Failure-mode discipline (from the failure matrix):
  - Every agent runs under a per-node TIMEOUT. A stalled/failing agent cannot hang the join;
    its slot degrades to "partial completion" recorded on the Review — degrade slower-but-correct.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from myers.agents.base import Agent
from myers.aggregation import Aggregator
from myers.diffing.parser import parse_unified_diff
from myers.models import Finding, Review
from myers.observability import EventLog

DEFAULT_AGENT_TIMEOUT_S = 30.0


class ReviewPipeline:
    def __init__(self, agents: list[Agent], mode: str, *, events: EventLog | None = None,
                 agent_timeout_s: float = DEFAULT_AGENT_TIMEOUT_S) -> None:
        self.agents = agents
        self.mode = mode
        self.events = events or EventLog()
        self.aggregator = Aggregator()
        self.agent_timeout_s = agent_timeout_s

    def review_text(self, diff_text: str, *, review_id: str | None = None) -> Review:
        review_id = review_id or str(uuid.uuid4())
        started = time.time()
        self.events.record(review_id, "pipeline", "span.start", payload={"mode": self.mode})

        diff = parse_unified_diff(diff_text)
        for err in diff.parse_errors:
            self.events.record(review_id, "diffing", "tool.call", outcome="parse_error",
                               payload={"error": err})

        agent_findings: list[list[Finding]] = []
        degraded: list[str] = []
        for agent in self.agents:
            self.events.record(review_id, agent.name, "span.start")
            t0 = time.time()
            try:
                findings = self._run_with_timeout(agent, diff)
                agent_findings.append(findings)
                self.events.record(review_id, agent.name, "span.end",
                                   latency_ms=int((time.time() - t0) * 1000),
                                   payload={"n_findings": len(findings)})
            except (FuturesTimeout, Exception) as exc:  # degrade, never crash the review
                degraded.append(f"{agent.name}: {type(exc).__name__}")
                self.events.record(review_id, agent.name, "span.end", outcome="degraded",
                                   payload={"error": type(exc).__name__})

        review = self.aggregator.merge(review_id, self.mode, agent_findings)
        review.degraded = degraded
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

    def _run_with_timeout(self, agent: Agent, diff) -> list[Finding]:
        with ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(agent.review, diff).result(timeout=self.agent_timeout_s)
