"""integrations — external systems. GitHub REST wrapper + webhook payload models."""

from myers.integrations.github_client import GitHubClient
from myers.integrations.models import PullRequestEvent

__all__ = ["GitHubClient", "PullRequestEvent"]
