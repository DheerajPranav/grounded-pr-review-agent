"""FastAPI ingress — fully offline: a fake GitHub client, the deterministic baseline reviewer."""

import json

from fastapi.testclient import TestClient

from myers.api.app import create_app
from myers.api.config import Settings
from myers.observability import EventLog
from myers.security import sign

SECRET = "test-webhook-secret"
DIFF = (
    "diff --git a/pay.py b/pay.py\nnew file mode 100644\n--- /dev/null\n+++ b/pay.py\n"
    "@@ -0,0 +1,2 @@\n+API_KEY = \"sk-abc123def456ghi789jkl012mno\"\n+print(x)\n"
)


class FakeGitHub:
    def __init__(self, diff: str) -> None:
        self.diff = diff
        self.posted: list = []

    def get_pr_diff(self, repo, pr):
        return self.diff

    def post_review(self, repo, pr, review):
        self.posted.append((repo, pr, review))
        return {"id": 1}


def _client(github, events=None, mode="baseline", secret=SECRET):
    settings = Settings(github_webhook_secret=secret, review_mode=mode)
    return TestClient(create_app(settings, github=github, events=events or EventLog()))


def _pr_payload(action="opened"):
    return {"action": action, "number": 7,
            "repository": {"full_name": "acme/shop"},
            "pull_request": {"number": 7, "head": {"sha": "abc"}, "title": "t"}}


def _post(client, payload, delivery="d1"):
    raw = json.dumps(payload).encode()
    return client.post("/webhook/github", content=raw, headers={
        "X-Hub-Signature-256": sign(SECRET, raw),
        "X-GitHub-Delivery": delivery,
        "Content-Type": "application/json",
    })


def test_healthz():
    r = _client(FakeGitHub(DIFF)).get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_valid_webhook_queues_and_posts_review():
    gh = FakeGitHub(DIFF)
    resp = _post(_client(gh), _pr_payload())
    assert resp.status_code == 200 and resp.json()["status"] == "queued"
    assert len(gh.posted) == 1                       # background job ran and posted
    _, _, review = gh.posted[0]
    assert any(f.rule_id == "hardcoded-api-key" for f in review.findings)
    assert review.escalated  # CRITICAL secret -> escalated (posted as COMMENT for a human)


def test_bad_signature_rejected():
    gh = FakeGitHub(DIFF)
    raw = json.dumps(_pr_payload()).encode()
    resp = _client(gh).post("/webhook/github", content=raw, headers={
        "X-Hub-Signature-256": "sha256=deadbeef", "X-GitHub-Delivery": "d9"})
    assert resp.status_code == 401
    assert gh.posted == []


def test_duplicate_delivery_dropped():
    gh = FakeGitHub(DIFF)
    client = _client(gh)
    first = _post(client, _pr_payload(), delivery="same")
    second = _post(client, _pr_payload(), delivery="same")
    assert first.json()["status"] == "queued"
    assert second.json()["status"] == "duplicate"
    assert len(gh.posted) == 1  # only reviewed once


def test_non_reviewable_action_ignored():
    gh = FakeGitHub(DIFF)
    resp = _post(_client(gh), _pr_payload(action="labeled"), delivery="d2")
    assert resp.json()["status"] == "ignored"
    assert gh.posted == []


def test_webhook_not_configured_returns_503():
    gh = FakeGitHub(DIFF)
    resp = _post(_client(gh, secret=""), _pr_payload(), delivery="d3")
    assert resp.status_code == 503
