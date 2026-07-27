"""ReviewContext — the per-review capabilities an agent may use, passed in by the orchestrator.

Lives in ``core`` so agents can depend on it without importing outer modules (observability,
economics, memory). It carries only plain callables — the orchestrator wires them to the real
event log, budget guard, and (from M3) the retriever. Agents that ignore it (the baseline) work
unchanged; the default no-op context makes an agent runnable standalone.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


def _noop_emit(**_: Any) -> None:  # pragma: no cover - trivial
    return None


def _noop_check() -> None:  # pragma: no cover - trivial
    return None


def _noop_retrieve(_query: str, _k: int = 5) -> list[Any]:  # pragma: no cover - trivial
    return []


@dataclass(frozen=True)
class ReviewContext:
    review_id: str = "local"
    #: emit an event to the spine (agent=..., event_type=..., cost_usd=..., ...)
    emit: Callable[..., None] = field(default=_noop_emit)
    #: raise BudgetExceededError if the daily cap is already reached (call BEFORE an LLM call)
    check_budget: Callable[[], None] = field(default=_noop_check)
    #: hybrid retrieval hook for grounding (wired at M3)
    retrieve: Callable[[str, int], list] = field(default=_noop_retrieve)
