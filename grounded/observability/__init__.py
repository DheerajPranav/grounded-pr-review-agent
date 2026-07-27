"""observability — the append-only events spine (cross-cutting). Depends only on models."""

from grounded.observability.events import AgentEvent, EventLog

__all__ = ["AgentEvent", "EventLog"]
