from myers.agents import BaselineAgent
from myers.diffing import parse_unified_diff
from myers.models import Category, Severity

SAMPLE = (
    "diff --git a/payments.py b/payments.py\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/payments.py\n"
    "@@ -0,0 +1,6 @@\n"
    "+API_KEY = \"sk-abc123def456ghi789jkl012mno\"\n"
    "+def charge(user):\n"
    "+    print(user)\n"
    "+    try:\n"
    "+        pass\n"
    "+    except:\n"
)


def _review(text):
    return BaselineAgent().review(parse_unified_diff(text))


def test_finds_planted_issues():
    findings = _review(SAMPLE)
    by_rule = {f.rule_id: f for f in findings}
    assert "hardcoded-api-key" in by_rule
    assert by_rule["hardcoded-api-key"].severity is Severity.CRITICAL
    assert by_rule["hardcoded-api-key"].line_start == 1
    assert "debug-print" in by_rule and by_rule["debug-print"].line_start == 3
    assert "bare-except" in by_rule and by_rule["bare-except"].line_start == 6
    # a non-test file changed with no tests -> tests category finding
    assert any(f.category is Category.TESTS for f in findings)


def test_every_finding_is_grounded():
    for f in _review(SAMPLE):
        assert f.evidence, f"{f.rule_id} has no evidence"
        assert f.evidence[0].file_path == f.file_path


def test_deterministic():
    a = [f.model_dump() for f in _review(SAMPLE)]
    b = [f.model_dump() for f in _review(SAMPLE)]
    assert a == b


def test_clean_diff_yields_no_findings():
    clean = (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
        "@@ -1,1 +1,2 @@\n x = 1\n+assert x == 1\n"
    )
    assert _review(clean) == []
