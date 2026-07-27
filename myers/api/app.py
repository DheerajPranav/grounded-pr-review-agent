"""FastAPI ingress.

The endpoint does exactly three things and returns fast (GitHub expects a quick ack):
verify the HMAC signature, drop replayed deliveries (idempotency), and enqueue the review.
The heavy work runs off the request — an ARQ worker in production, a BackgroundTask locally —
so a slow LLM or a crashed worker can never time out the webhook (the L2/L8 decoupling).
"""

from __future__ import annotations

import functools
import json

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from myers.core.config import Settings
from myers.integrations import GitHubClient, PullRequestEvent
from myers.job_queue import JobPayload, run_review_job
from myers.observability import EventLog
from myers.webhook_receiver import WebhookValidator
from myers.webhook_receiver.validator import WebhookOutcome


def create_app(settings: Settings | None = None, *, github=None, events: EventLog | None = None,
               job_runner=None) -> FastAPI:
    settings = settings or Settings.from_env()
    events = events or EventLog()
    github = github or GitHubClient(token=settings.github_token)
    validator = WebhookValidator(settings.github_webhook_secret)
    if job_runner is None:
        job_runner = functools.partial(run_review_job, settings=settings, github=github, events=events)

    app = FastAPI(title="myers-pr-review-agent", version="0.1.0")
    app.state.settings = settings
    app.state.events = events

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "mode": settings.review_mode,
                "webhook_configured": settings.webhook_configured}

    @app.post("/webhook/github")
    async def github_webhook(request: Request, background: BackgroundTasks) -> dict:
        if not settings.webhook_configured:
            raise HTTPException(503, "GITHUB_WEBHOOK_SECRET not configured")
        raw = await request.body()
        outcome = validator.validate(
            raw,
            request.headers.get("X-Hub-Signature-256"),
            request.headers.get("X-GitHub-Delivery", ""),
        )
        if outcome is WebhookOutcome.BAD_SIGNATURE:
            raise HTTPException(401, "invalid signature")
        if outcome is WebhookOutcome.DUPLICATE:
            return {"status": "duplicate"}  # 200: acknowledged, not re-reviewed

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(400, "invalid JSON")
        event = PullRequestEvent.from_webhook(payload)
        if not event.is_reviewable:
            return {"status": "ignored", "action": event.action}

        background.add_task(job_runner, JobPayload(
            repo_full_name=event.repo_full_name, pr_number=event.number,
            delivery_id=request.headers.get("X-GitHub-Delivery", ""),
        ))
        return {"status": "queued", "repo": event.repo_full_name, "pr": event.number}

    return app


# Module-level app for `uvicorn myers.api.app:app` / Railway. Reads settings from the env;
# the webhook stays 503 until GITHUB_WEBHOOK_SECRET is configured.
app = create_app()
