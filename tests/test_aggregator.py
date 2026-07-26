from myers.aggregation import Aggregator
from myers.models import AgentType, Category, Decision, Evidence, Finding, Severity


def _f(agent, rule="r", sev=Severity.HIGH, conf=0.8, line=5):
    return Finding(
        rule_id=rule, agent_type=agent, category=Category.SECURITY, severity=sev,
        summary="s", file_path="f.py", line_start=line, line_end=line, confidence=conf,
        evidence=[Evidence(file_path="f.py", line=line, snippet="x")],
    )


def test_dedup_keeps_highest_confidence_and_records_agreement():
    low = _f(AgentType.QUALITY, conf=0.6)
    high = _f(AgentType.SECURITY, conf=0.9)
    review = Aggregator().merge("rid", "specialists", [[low], [high]])
    assert len(review.findings) == 1
    kept = review.findings[0]
    assert kept.confidence == 0.9
    assert set(kept.agreed_by) == {AgentType.SECURITY, AgentType.QUALITY}


def test_critical_requests_changes_and_escalates():
    review = Aggregator().merge("rid", "baseline", [[_f(AgentType.BASELINE, sev=Severity.CRITICAL, conf=0.95)]])
    assert review.decision is Decision.REQUEST_CHANGES
    assert review.escalated is True


def test_high_requests_changes_without_escalation():
    review = Aggregator().merge("rid", "baseline", [[_f(AgentType.BASELINE, sev=Severity.HIGH, conf=0.8)]])
    assert review.decision is Decision.REQUEST_CHANGES
    assert review.escalated is False


def test_no_findings_approves():
    review = Aggregator().merge("rid", "baseline", [[]])
    assert review.decision is Decision.APPROVE
    assert review.overall_confidence == 1.0


def test_low_severity_approves_with_comments():
    review = Aggregator().merge("rid", "baseline", [[_f(AgentType.BASELINE, sev=Severity.LOW, conf=0.85)]])
    assert review.decision is Decision.APPROVE
    assert len(review.findings) == 1
