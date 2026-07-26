"""Agent base contract. Every reviewer implements review(diff) -> list[Finding]."""

from __future__ import annotations

from abc import ABC, abstractmethod

from myers.diffing.parser import ParsedDiff
from myers.models import Finding


class Agent(ABC):
    """A reviewer. Contract: consume a parsed diff (+ optional grounding), emit Findings.

    Shared shape for the baseline and, later, the four LLM specialists — so the aggregator
    and orchestrator treat them uniformly (the Finding contract is the only interface).
    """

    name: str = "agent"

    @abstractmethod
    def review(self, diff: ParsedDiff) -> list[Finding]:
        ...
