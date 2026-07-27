"""ARQ worker — the production consumer of review jobs off Redis.

Not imported by the package by default (keeps arq/redis optional). Run in production with:
    arq myers.job_queue.arq_worker.WorkerSettings
The webhook enqueues 'review' jobs; this worker drains them and runs the same run_review_job
used by the local BackgroundTask path — the queue is just the delivery mechanism.
"""

from __future__ import annotations

import asyncio
import os


async def review_task(ctx, repo_full_name: str, pr_number: int, delivery_id: str = "") -> str:
    from myers.core.config import Settings
    from myers.integrations import GitHubClient
    from myers.job_queue.runner import JobPayload, run_review_job

    settings = Settings.from_env()
    github = GitHubClient(token=settings.github_token)
    payload = JobPayload(repo_full_name=repo_full_name, pr_number=pr_number, delivery_id=delivery_id)
    # run the sync runner off the event loop so httpx/pipeline don't block the worker
    review = await asyncio.to_thread(run_review_job, payload, settings=settings, github=github)
    return review.decision.value


try:  # only importable when the 'queue' extra is installed (arq CLI runs this module)
    from arq.connections import RedisSettings
    _REDIS = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
except Exception:  # pragma: no cover - arq optional
    _REDIS = None


class WorkerSettings:
    """arq entrypoint. `functions` are the jobs; the webhook enqueues 'review_task'."""

    functions = [review_task]
    redis_settings = _REDIS
