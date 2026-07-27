"""The baseline must fully score its own golden set: this is the regression anchor."""

from grounded.agents import BaselineAgent
from grounded.evaluation import evaluate, load_golden_cases


def test_golden_cases_load():
    cases = load_golden_cases()
    names = {c.name for c in cases}
    assert {"security_pr", "clean_pr"} <= names


def test_baseline_scores_golden_perfectly():
    report = evaluate([BaselineAgent()], "baseline")
    # Ground-truth labels were authored to exactly match the deterministic baseline:
    # every expected finding is caught (recall) and nothing spurious is raised (precision).
    assert report.recall == 1.0, report.render()
    assert report.precision == 1.0, report.render()
    assert report.f1 == 1.0


def test_clean_case_has_no_false_positives():
    report = evaluate([BaselineAgent()], "baseline")
    clean = next(c for c in report.cases if c.name == "clean_pr")
    assert clean.fp == 0 and clean.tp == 0 and clean.fn == 0
