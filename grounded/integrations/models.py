"""GitHub webhook payload models (only the fields we need — tolerant of the rest)."""

from __future__ import annotations

from pydantic import BaseModel


class PullRequestEvent(BaseModel):
    action: str
    number: int
    repo_full_name: str  # "owner/repo"
    head_sha: str
    title: str = ""

    model_config = {"extra": "ignore"}

    @classmethod
    def from_webhook(cls, payload: dict) -> "PullRequestEvent":
        pr = payload.get("pull_request", {}) or {}
        return cls(
            action=payload.get("action", ""),
            number=payload.get("number") or pr.get("number") or 0,
            repo_full_name=(payload.get("repository", {}) or {}).get("full_name", ""),
            head_sha=(pr.get("head", {}) or {}).get("sha", ""),
            title=pr.get("title", ""),
        )

    @property
    def is_reviewable(self) -> bool:
        # Review on open and on new commits; ignore label/assignee/close noise.
        return self.action in {"opened", "synchronize", "reopened"}
