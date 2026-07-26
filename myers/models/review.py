"""The Review — a structured verdict over a PR, plus the audit fields the spine needs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from myers.models.enums import Decision
from myers.models.findings import Finding


class Review(BaseModel):
    review_id: str
    mode: str  # "baseline" | "llm" | "specialists"
    decision: Decision
    findings: list[Finding] = Field(default_factory=list)
    overall_confidence: float = Field(1.0, ge=0.0, le=1.0)
    escalated: bool = False
    escalation_reason: str = ""
    degraded: list[str] = Field(
        default_factory=list,
        description="Components that failed and were degraded (e.g. 'quality: timeout'). "
        "Degrade slower-but-correct, never fast-but-wrong.",
    )
    cost_usd: float = 0.0
    latency_ms: int = 0

    def render(self) -> str:
        """Human-readable review body (what would be posted to the PR / printed by the CLI)."""
        lines: list[str] = []
        head = f"Review {self.review_id} [{self.mode}] -> {self.decision.value.upper()}"
        lines.append(head)
        lines.append("=" * len(head))
        if self.escalated:
            lines.append(f"[ESCALATED TO HUMAN] {self.escalation_reason}")
        if self.degraded:
            lines.append(f"[DEGRADED] {', '.join(self.degraded)}")
        lines.append(
            f"{len(self.findings)} finding(s) | overall confidence "
            f"{self.overall_confidence:.2f} | cost ${self.cost_usd:.4f} | {self.latency_ms}ms"
        )
        lines.append("")
        if not self.findings:
            lines.append("No findings. Mechanical review clean.")
        for f in self.findings:
            agree = f" (also raised by: {', '.join(a.value for a in f.agreed_by)})" if f.agreed_by else ""
            lines.append(
                f"[{f.severity.value.upper():8}] {f.category.value}/{f.rule_id} "
                f"@ {f.file_path}:{f.line_start}"
                + (f"-{f.line_end}" if f.line_end != f.line_start else "")
            )
            lines.append(f"    {f.summary}{agree}")
            if f.suggestion:
                lines.append(f"    -> {f.suggestion}")
            for ev in f.evidence:
                lines.append(f"    | {ev.file_path}:{ev.line}  {ev.snippet.strip()[:100]}  [{ev.source}]")
            lines.append(f"    confidence {f.confidence:.2f}")
        return "\n".join(lines)
