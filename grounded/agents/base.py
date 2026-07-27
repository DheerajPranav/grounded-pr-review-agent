"""Agent base contract. Every reviewer implements review(diff) -> list[Finding]."""

from __future__ import annotations

from abc import ABC, abstractmethod

from grounded.core.context import ReviewContext
from grounded.diffing.parser import ParsedDiff
from grounded.models import Finding


class Agent(ABC):
    """A reviewer. Contract: consume a parsed diff (+ optional context), emit Findings.

    Shared shape for the baseline and, later, the four LLM specialists — so the aggregator
    and orchestrator treat them uniformly (the Finding contract is the only interface).
    The ``ctx`` carries per-review capabilities (event emit, budget check, retrieval); agents
    that need none of them (the baseline) simply ignore it.
    """

    name: str = "agent"

    @abstractmethod
    def review(self, diff: ParsedDiff, ctx: ReviewContext | None = None) -> list[Finding]:
        ...
