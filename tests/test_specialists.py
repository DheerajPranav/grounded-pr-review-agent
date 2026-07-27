"""M3: grounded specialist fan-out (offline via FakeLLM)."""

import json
import time

from myers.agents import LLMReviewAgent, build_specialists
from myers.agents.base import Agent
from myers.core.llm import FakeLLM
from myers.diffing import parse_unified_diff
from myers.memory import InMemoryCodeStore
from myers.models import AgentType, Category, Decision
from myers.orchestrator import ReviewPipeline

DIFF = (
    "diff --git a/app.py b/app.py\nnew file mode 100644\n--- /dev/null\n+++ b/app.py\n"
    "@@ -0,0 +1,2 @@\n+password = \"secret123\"\n+def foo(): pass\n"
)

# One canned response with a finding in each domain; every specialist filters to its own.
CANNED = json.dumps({"findings": [
    {"file_path": "app.py", "line": 1, "category": "security", "severity": "critical",
     "summary": "hardcoded password", "confidence": 0.95},
    {"file_path": "app.py", "line": 2, "category": "quality", "severity": "low",
     "summary": "one-liner def", "confidence": 0.6},
    {"file_path": "app.py", "line": 1, "category": "tests", "severity": "medium",
     "summary": "no tests for change", "confidence": 0.5},
    {"file_path": "app.py", "line": 2, "category": "docs", "severity": "low",
     "summary": "foo undocumented", "confidence": 0.5},
]})


def _pipeline(agents):
    store = InMemoryCodeStore()
    store.ingest_diff_context(parse_unified_diff(DIFF))
    return ReviewPipeline(agents, "specialists", retriever=store.hybrid_search, agent_timeout_s=5)


def test_build_specialists_shape():
    specialists = build_specialists(FakeLLM(CANNED))
    assert [s.name for s in specialists] == ["security", "quality", "tests", "docs"]


def test_each_specialist_keeps_only_its_domain():
    specialists = {s.name: s for s in build_specialists(FakeLLM(CANNED))}
    sec = specialists["security"].review(parse_unified_diff(DIFF))
    assert len(sec) == 1 and sec[0].category is Category.SECURITY
    assert sec[0].agent_type is AgentType.SECURITY
    docs = specialists["docs"].review(parse_unified_diff(DIFF))
    assert len(docs) == 1 and docs[0].category is Category.DOCS


def test_fanout_merges_all_four_domains():
    review = _pipeline(build_specialists(FakeLLM(CANNED))).review_text(DIFF, review_id="rid")
    cats = {f.category for f in review.findings}
    assert cats == {Category.SECURITY, Category.QUALITY, Category.TESTS, Category.DOCS}
    assert len(review.findings) == 4
    assert review.decision is Decision.REQUEST_CHANGES and review.escalated  # security CRITICAL


def test_fanout_ran_four_parallel_nodes_with_grounding():
    pipe = _pipeline(build_specialists(FakeLLM(CANNED)))
    pipe.review_text(DIFF, review_id="rid2")
    events = pipe.events.for_review("rid2")
    assert sum(1 for e in events if e.event_type == "llm.call") == 4
    retrievals = [e for e in events if e.event_type == "tool.call" and e.outcome == "retrieval"]
    assert len(retrievals) == 4
    assert all(e.payload.get("k", 0) >= 1 for e in retrievals)  # each specialist got context


class _Staller(Agent):
    name = "staller"

    def review(self, diff, ctx=None):
        time.sleep(5)
        return []


def test_stalled_specialist_degrades_join_survives():
    agents = [build_specialists(FakeLLM(CANNED))[0], _Staller()]  # security + a staller
    pipe = ReviewPipeline(agents, "specialists", agent_timeout_s=0.2,
                          retriever=InMemoryCodeStore().hybrid_search)
    review = pipe.review_text(DIFF)
    assert any("staller" in d for d in review.degraded)
    assert any(f.category is Category.SECURITY for f in review.findings)  # others still land


def test_specialist_drops_out_of_domain_finding():
    only_quality = json.dumps({"findings": [
        {"file_path": "app.py", "line": 1, "category": "quality", "severity": "low",
         "summary": "x", "confidence": 0.5}
    ]})
    sec = LLMReviewAgent(FakeLLM(only_quality), agent_type=AgentType.SECURITY,
                         only_category=Category.SECURITY).review(parse_unified_diff(DIFF))
    assert sec == []
