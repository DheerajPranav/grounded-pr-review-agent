"""Enumerations shared across the Finding contract."""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    """Ordered by how much a wrong-or-missed call costs. CRITICAL blocks/escalates."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}[self.value]


class Category(str, Enum):
    SECURITY = "security"
    QUALITY = "quality"
    TESTS = "tests"
    DOCS = "docs"


class AgentType(str, Enum):
    """Who produced the finding. Baseline is the deterministic M1 reviewer."""

    BASELINE = "baseline"
    SECURITY = "security"
    QUALITY = "quality"
    TESTS = "tests"
    DOCS = "docs"
    AGGREGATOR = "aggregator"


class Decision(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    ESCALATE = "escalate"  # route to a human (uncertain / critical / irreversible)
