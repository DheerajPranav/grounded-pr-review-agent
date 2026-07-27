"""Abstract orchestration interface (ADR-001).

The orchestrator swap-point. Orchestrator code imports ONLY from here, never from
LangGraph/Temporal directly. M1 ships a trivial in-process engine; M3 adds the
LangGraph fan-out implementation of the same three methods; a Temporal impl can
replace it at scale by changing one file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class WorkflowState(Protocol):
    """Typed state that flows through the graph and is checkpointed at node boundaries."""

    def to_dict(self) -> dict[str, Any]: ...


class WorkflowEngine(ABC):
    """Coordinate steps, persist state across them, retry/resume on failure."""

    @abstractmethod
    def run(self, workflow_id: str, input: Any) -> Any:
        """Execute the workflow to completion, returning its final state/result."""

    @abstractmethod
    def resume(self, workflow_id: str, state: Any) -> Any:
        """Resume from the last checkpointed state after a crash."""

    @abstractmethod
    def get_state(self, workflow_id: str) -> Any:
        """Return the last checkpointed state for a workflow."""
