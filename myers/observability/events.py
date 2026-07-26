"""The events spine (local shape of the agent_events hypertable).

Every action is one append-only row. A whole review is reconstructable from these rows
(trace viewer, audit trail, cost ledger all read this one stream). In production this is the
TimescaleDB hypertable; locally it is an in-process append-only log that can flush to JSONL.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentEvent:
    ts: float
    review_id: str
    agent: str
    event_type: str  # span.start | span.end | llm.call | tool.call | decision | escalation
    outcome: str = ""
    confidence: float | None = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    model: str = ""
    payload: dict = field(default_factory=dict)


class EventLog:
    """Append-only. Never mutated in place — immutability is the audit guarantee."""

    def __init__(self) -> None:
        self._events: list[AgentEvent] = []

    def emit(self, event: AgentEvent) -> None:
        self._events.append(event)

    def record(self, review_id: str, agent: str, event_type: str, **kw) -> AgentEvent:
        ev = AgentEvent(ts=time.time(), review_id=review_id, agent=agent, event_type=event_type, **kw)
        self.emit(ev)
        return ev

    def for_review(self, review_id: str) -> list[AgentEvent]:
        return [e for e in self._events if e.review_id == review_id]

    def total_cost(self) -> float:
        return round(sum(e.cost_usd for e in self._events), 6)

    def flush_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            for e in self._events:
                fh.write(json.dumps(asdict(e)) + "\n")
