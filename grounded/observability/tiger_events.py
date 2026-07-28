"""Persist the events spine to the Tiger `agent_events` hypertable (production).

Takes any connection exposing async ``executemany`` / ``fetchrow`` (asyncpg in production, a
fake in tests), so the batch-insert SQL and the cost query are unit-tested without a live DB.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from grounded.observability.events import AgentEvent

_INSERT = (
    "INSERT INTO agent_events "
    "(ts, review_id, agent, event_type, model, tokens_in, tokens_out, cost_usd, "
    " latency_ms, outcome, confidence, payload) "
    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)"
)


def _row(e: AgentEvent) -> tuple:
    payload = e.payload or {}
    return (
        datetime.fromtimestamp(e.ts, tz=timezone.utc),
        e.review_id, e.agent, e.event_type, e.model or None,
        payload.get("tokens_in"), payload.get("tokens_out"),
        e.cost_usd, e.latency_ms or None,
        e.outcome or None,
        e.confidence,
        json.dumps(payload),
    )


class EventRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    async def flush(self, events: list[AgentEvent]) -> int:
        if not events:
            return 0
        await self.conn.executemany(_INSERT, [_row(e) for e in events])
        return len(events)

    async def daily_cost(self) -> float:
        """Running spend today, read from the continuous aggregate (BudgetGuard source)."""
        row = await self.conn.fetchrow(
            "SELECT COALESCE(sum(cost_usd), 0) AS c FROM agent_health_1m "
            "WHERE bucket > now() - INTERVAL '1 day'"
        )
        return float(row["c"] if row and row["c"] is not None else 0.0)
