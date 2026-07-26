import json

from myers.agents import LLMReviewAgent
from myers.core.llm import FakeLLM
from myers.diffing import parse_unified_diff
from myers.models import Category, Severity

DIFF = (
    "diff --git a/app.py b/app.py\n"
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/app.py\n"
    "@@ -0,0 +1,2 @@\n"
    "+password = \"hunter2000\"\n"
    "+x = 1\n"
)

CANNED = json.dumps({
    "findings": [
        {"file_path": "app.py", "line": 1, "category": "security", "severity": "critical",
         "summary": "hardcoded password", "suggestion": "use env", "confidence": 0.9},
        # line 99 does not exist in the diff -> must be dropped (grounded-or-nothing)
        {"file_path": "app.py", "line": 99, "category": "quality", "severity": "low",
         "summary": "ghost finding", "confidence": 0.5},
    ]
})


def _review(canned):
    agent = LLMReviewAgent(FakeLLM(canned))
    return agent.review(parse_unified_diff(DIFF))


def test_parses_and_grounds_findings():
    findings = _review(CANNED)
    assert len(findings) == 1  # the ungrounded line-99 finding was dropped
    f = findings[0]
    assert f.category is Category.SECURITY and f.severity is Severity.CRITICAL
    assert f.line_start == 1
    assert f.evidence[0].snippet == 'password = "hunter2000"'
    assert f.evidence[0].source == "llm"


def test_deterministic_with_fake_llm():
    a = [f.model_dump() for f in _review(CANNED)]
    b = [f.model_dump() for f in _review(CANNED)]
    assert a == b


def test_i_dont_know_and_garbage_yield_nothing():
    assert _review('{"findings": []}') == []
    assert _review("not json at all") == []
    assert _review("{}") == []


def test_bare_array_shape_accepted():
    canned = json.dumps([
        {"file_path": "app.py", "line": 2, "category": "quality", "severity": "info",
         "summary": "x unused", "confidence": 0.4}
    ])
    findings = _review(canned)
    assert len(findings) == 1 and findings[0].line_start == 2


def test_invalid_category_is_skipped():
    canned = json.dumps({"findings": [
        {"file_path": "app.py", "line": 1, "category": "made-up", "severity": "high",
         "summary": "x", "confidence": 0.9}
    ]})
    assert _review(canned) == []
