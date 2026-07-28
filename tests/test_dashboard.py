"""API routers + dashboard, driven through a real webhook review (offline)."""

import json

from fastapi.testclient import TestClient

from grounded.api.app import create_app
from grounded.core.config import Settings
from grounded.security import sign

SECRET = "test-webhook-secret"
DIFF = (
    "diff --git a/pay.py b/pay.py\nnew file mode 100644\n--- /dev/null\n+++ b/pay.py\n"
    "@@ -0,0 +1,1 @@\n+API_KEY = \"sk-abc123def456ghi789jkl012mno\"\n"
)
RID = "acme_shop_pr7_d1"  # run_review_job builds a URL-safe review_id


class FakeGitHub:
    def __init__(self, diff): self.diff = diff; self.posted = []
    def get_pr_diff(self, repo, pr): return self.diff
    def post_review(self, repo, pr, review): self.posted.append(review); return {"id": 1}


def _client_with_one_review():
    client = TestClient(create_app(Settings(github_webhook_secret=SECRET), github=FakeGitHub(DIFF)))
    payload = {"action": "opened", "number": 7, "repository": {"full_name": "acme/shop"},
               "pull_request": {"number": 7, "head": {"sha": "abc"}, "title": "t"}}
    raw = json.dumps(payload).encode()
    client.post("/webhook/github", content=raw, headers={
        "X-Hub-Signature-256": sign(SECRET, raw), "X-GitHub-Delivery": "d1"})
    return client


def test_dashboard_page_served():
    r = TestClient(create_app(Settings(github_webhook_secret=SECRET))).get("/")
    assert r.status_code == 200 and "grounded" in r.text.lower()


def test_economics_and_reviews_reflect_the_review():
    client = _client_with_one_review()
    summary = client.get("/api/economics/summary").json()
    assert summary["n_reviews"] == 1 and summary["n_events"] > 0
    reviews = client.get("/api/reviews").json()
    assert len(reviews) == 1 and reviews[0]["status"] == "pending"  # CRITICAL secret -> escalated


def test_trace_endpoint_reconstructs_review():
    events = _client_with_one_review().get(f"/api/reviews/{RID}/trace").json()
    kinds = [e["event_type"] for e in events["events"]]
    assert "decision" in kinds and "span.end" in kinds


def test_hitl_decide_moves_ticket_out_of_pending():
    client = _client_with_one_review()
    r = client.post(f"/api/hitl/{RID}/decide", json={"decision": "approve", "reviewer": "dheeraj"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert client.get("/api/hitl/pending").json() == []


def test_trace_404_for_unknown_review():
    assert _client_with_one_review().get("/api/reviews/nope/trace").status_code == 404
