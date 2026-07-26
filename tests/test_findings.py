import pytest
from pydantic import ValidationError

from myers.models import AgentType, Category, Evidence, Finding, Severity


def _finding(**kw):
    base = dict(
        rule_id="r", agent_type=AgentType.BASELINE, category=Category.QUALITY,
        severity=Severity.LOW, summary="s", file_path="f.py",
        line_start=5, line_end=5, confidence=0.5,
    )
    base.update(kw)
    return Finding(**base)


def test_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        _finding(confidence=1.5)


def test_line_end_must_not_precede_start():
    with pytest.raises(ValidationError):
        _finding(line_start=10, line_end=3)


def test_dedup_key_ignores_severity():
    a = _finding(severity=Severity.LOW)
    b = _finding(severity=Severity.CRITICAL)
    assert a.dedup_key == b.dedup_key == ("f.py", 5, "r")


def test_sort_key_orders_critical_first():
    low = _finding(severity=Severity.LOW, line_start=1, line_end=1)
    crit = _finding(severity=Severity.CRITICAL, line_start=99, line_end=99)
    assert sorted([low, crit], key=lambda f: f.sort_key)[0] is crit


def test_evidence_is_frozen():
    ev = Evidence(file_path="f.py", line=1, snippet="x")
    with pytest.raises(ValidationError):
        ev.line = 2
