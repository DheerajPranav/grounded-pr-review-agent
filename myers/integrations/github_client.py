"""GitHub REST client: fetch a PR's diff, post a structured review.

Thin wrapper over httpx with retry on transient failures. Auth is a token (a GitHub App
installation token in production, or a PAT for local testing) read from the environment.
The httpx client is injectable so tests run fully offline against a mock transport.
"""

from __future__ import annotations

import os
import time

from myers.models import Decision, Review

_API = "https://api.github.com"
# Map our decision to a GitHub review event.
_EVENT = {
    Decision.APPROVE: "APPROVE",
    Decision.REQUEST_CHANGES: "REQUEST_CHANGES",
    Decision.ESCALATE: "COMMENT",  # escalated -> comment only, a human makes the call
}


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str = _API, client=None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = base_url.rstrip("/")
        self._client = client  # injectable httpx.Client; created lazily if None

    def _http(self):
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=20.0)
        return self._client

    def _headers(self, accept: str = "application/vnd.github+json") -> dict:
        h = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get_pr_diff(self, repo_full_name: str, pr_number: int) -> str:
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        resp = self._request("GET", url, headers=self._headers("application/vnd.github.v3.diff"))
        return resp.text

    def post_review(self, repo_full_name: str, pr_number: int, review: Review) -> dict:
        """Post the review. Escalated reviews post as COMMENT (a human decides)."""
        event = "COMMENT" if review.escalated else _EVENT.get(review.decision, "COMMENT")
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        body = {"event": event, "body": self._summary(review), "comments": self._comments(review)}
        resp = self._request("POST", url, headers=self._headers(), json=body)
        return resp.json() if resp.content else {}

    # -- rendering -----------------------------------------------------------
    def _summary(self, review: Review) -> str:
        head = f"**myers-pr-review-agent** [{review.mode}] — {review.decision.value}"
        if review.escalated:
            head += f"\n\n> ⚠️ Escalated to a human reviewer: {review.escalation_reason}"
        if review.degraded:
            head += f"\n\n> ⚙️ Degraded: {', '.join(review.degraded)}"
        head += (f"\n\n{len(review.findings)} finding(s) · overall confidence "
                 f"{review.overall_confidence:.2f} · cost ${review.cost_usd:.4f} · {review.latency_ms}ms")
        return head

    def _comments(self, review: Review) -> list[dict]:
        out = []
        for f in review.findings:
            body = (f"**[{f.severity.value}] {f.category.value}/{f.rule_id}** — {f.summary}"
                    + (f"\n\n_Suggestion:_ {f.suggestion}" if f.suggestion else "")
                    + f"\n\n_confidence {f.confidence:.2f}_")
            out.append({"path": f.file_path, "line": f.line_start, "body": body})
        return out

    # -- transport with retry ------------------------------------------------
    def _request(self, method: str, url: str, *, retries: int = 2, **kw):
        last = None
        for attempt in range(retries + 1):
            resp = self._http().request(method, url, **kw)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp
            last = resp
            time.sleep(0.2 * (attempt + 1))  # backoff on 5xx
        last.raise_for_status()
        return last
