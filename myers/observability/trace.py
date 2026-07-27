"""Trace viewer — reconstruct any review from the append-only events spine.

Reads the JSONL the pipeline flushes and renders the ordered timeline: spans, LLM/tool calls
(with cost + latency), retrieval, the decision, escalation, recovery/degradation, and any
human decisions. This is the proof requirement — a review is fully reconstructable from one
time-ordered stream (locally JSONL; the TimescaleDB hypertable in production).
"""

from __future__ import annotations

import json
from pathlib import Path

from myers.observability.events import AgentEvent


def load_events(path: str | Path) -> list[AgentEvent]:
    events: list[AgentEvent] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(AgentEvent(**json.loads(line)))
    return events


def render_trace(events: list[AgentEvent], review_id: str) -> str:
    rows = sorted((e for e in events if e.review_id == review_id), key=lambda e: e.ts)
    if not rows:
        return f"no events for review {review_id}"

    t0 = rows[0].ts
    lines = [f"TRACE {review_id}  ({len(rows)} events)", "=" * 72]
    total_cost = 0.0
    for e in rows:
        total_cost += e.cost_usd
        offset = f"+{(e.ts - t0) * 1000:7.1f}ms"
        bits = [f"{offset}  {e.agent:10} {e.event_type:12}"]
        if e.outcome:
            bits.append(f"[{e.outcome}]")
        if e.model:
            bits.append(f"model={e.model}")
        if e.cost_usd:
            bits.append(f"${e.cost_usd:.5f}")
        if e.latency_ms:
            bits.append(f"{e.latency_ms}ms")
        if e.confidence is not None:
            bits.append(f"conf={e.confidence:.2f}")
        if e.payload:
            bits.append(_short(e.payload))
        lines.append(" ".join(bits))
    lines.append("-" * 72)
    lines.append(f"total LLM cost ${total_cost:.5f}")
    return "\n".join(lines)


def _short(payload: dict) -> str:
    items = []
    for k, v in payload.items():
        s = str(v)
        items.append(f"{k}={s[:60]}")
    return "{" + ", ".join(items) + "}"
