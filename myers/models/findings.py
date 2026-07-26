"""The Finding contract — FROZEN at M1 (see .genesis/DONE.html §2, invariant list).

Every reviewer (baseline, single-LLM, or specialist) emits exactly this. The aggregator
merges DATA, not prose. Structured output is what makes the downstream steps deterministic.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from myers.models.enums import AgentType, Category, Severity


class Evidence(BaseModel):
    """Grounding for a finding: the exact code it points at.

    An upgraded (retrieval-grounded) finding without evidence is INVALID — grounding is
    the defense against hallucination in a critical path. The baseline cites the changed
    line itself; specialists additionally cite retrieved code chunks.
    """

    file_path: str
    line: int
    snippet: str
    source: str = "diff"  # "diff" | "retrieval:<repo>/<path>#<chunk>"

    model_config = {"frozen": True}


class Finding(BaseModel):
    """One reviewable observation, grounded and severity-scored."""

    rule_id: str = Field(..., description="Stable id of the check that produced this.")
    agent_type: AgentType
    category: Category
    severity: Severity
    summary: str = Field(..., description="One-line, human-readable.")
    file_path: str
    line_start: int
    line_end: int
    suggestion: str = ""
    rationale: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    agreed_by: list[AgentType] = Field(
        default_factory=list,
        description="Set by the aggregator when multiple agents raised the same finding.",
    )

    @field_validator("line_end")
    @classmethod
    def _end_after_start(cls, v: int, info):
        start = info.data.get("line_start")
        if start is not None and v < start:
            raise ValueError("line_end must be >= line_start")
        return v

    @property
    def dedup_key(self) -> tuple[str, int, str]:
        """Two findings on the same file+line+rule are the same finding."""
        return (self.file_path, self.line_start, self.rule_id)

    @property
    def sort_key(self) -> tuple:
        """Deterministic ordering: worst severity first, then file/line/rule."""
        return (-self.severity.rank, self.file_path, self.line_start, self.rule_id)
