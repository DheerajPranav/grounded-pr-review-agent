"""Eval harness: run a set of agents over the golden PRs and score precision / recall / F1.

A finding matches an expected label when (category, file_path, line_start) are equal —
mode-agnostic, so a regex baseline and an LLM are scored against the same ground truth. This
is the baseline-vs-upgraded comparison anchor and the regression gate input (M4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from myers.agents.base import Agent
from myers.evaluation.golden import GoldenCase, load_golden_cases
from myers.orchestrator import ReviewPipeline


@dataclass
class CaseResult:
    name: str
    tp: int
    fp: int
    fn: int
    decision: str
    escalated: bool

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 1.0


@dataclass
class EvalReport:
    mode: str
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def tp(self) -> int: return sum(c.tp for c in self.cases)
    @property
    def fp(self) -> int: return sum(c.fp for c in self.cases)
    @property
    def fn(self) -> int: return sum(c.fn for c in self.cases)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def render(self) -> str:
        lines = [f"EVAL [{self.mode}]  precision={self.precision:.2f} recall={self.recall:.2f} "
                 f"f1={self.f1:.2f}  (TP={self.tp} FP={self.fp} FN={self.fn})",
                 "-" * 72]
        for c in self.cases:
            lines.append(f"  {c.name:24} P={c.precision:.2f} R={c.recall:.2f} "
                         f"TP={c.tp} FP={c.fp} FN={c.fn}  -> {c.decision}"
                         + ("  [escalated]" if c.escalated else ""))
        return "\n".join(lines)


def evaluate(agents: list[Agent], mode: str, cases: list[GoldenCase] | None = None,
             daily_cap_usd: float | None = None) -> EvalReport:
    cases = cases if cases is not None else load_golden_cases()
    report = EvalReport(mode=mode)
    pipeline = ReviewPipeline(agents, mode, daily_cap_usd=daily_cap_usd)
    for case in cases:
        review = pipeline.review_text(case.diff_text, review_id=case.name)
        found = {(f.category.value, f.file_path, f.line_start) for f in review.findings}
        tp = len(found & case.expected)
        fp = len(found - case.expected)
        fn = len(case.expected - found)
        report.cases.append(CaseResult(
            name=case.name, tp=tp, fp=fp, fn=fn,
            decision=review.decision.value, escalated=review.escalated,
        ))
    return report
