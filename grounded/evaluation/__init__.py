"""evaluation — golden PRs + precision/recall + regression gate. The 'or it doesn't count' bar."""

from grounded.evaluation.golden import GoldenCase, load_golden_cases
from grounded.evaluation.harness import CaseResult, EvalReport, evaluate

__all__ = ["GoldenCase", "load_golden_cases", "CaseResult", "EvalReport", "evaluate"]
