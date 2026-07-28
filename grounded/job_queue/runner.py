"""The review job: fetch a PR's diff, review it, route through HITL, post the result.

This is the heavy work the webhook decouples itself from. In production it runs in an ARQ
worker off Redis; locally it runs in a FastAPI BackgroundTask. Same function either way — the
queue is a delivery detail, not where the logic lives.
"""

from __future__ import annotations

from dataclasses import dataclass

from grounded.agents import BaselineAgent, LLMReviewAgent, build_specialists
from grounded.diffing import parse_unified_diff
from grounded.hitl import ApprovalQueue
from grounded.memory import InMemoryCodeStore
from grounded.models import Review
from grounded.observability import EventLog
from grounded.orchestrator import ReviewPipeline


@dataclass(frozen=True)
class JobPayload:
    repo_full_name: str
    pr_number: int
    delivery_id: str = ""


def _agents_for(mode: str, groq_api_key: str):
    if mode == "baseline":
        return [BaselineAgent()], "baseline"
    from grounded.tools import GroqLLMClient
    client = GroqLLMClient(api_key=groq_api_key or None)
    if mode == "llm":
        return [LLMReviewAgent(client)], "llm"
    return build_specialists(client), "specialists"


def run_review_job(payload: JobPayload, *, settings, github, events: EventLog | None = None) -> Review:
    events = events or EventLog()
    diff_text = github.get_pr_diff(payload.repo_full_name, payload.pr_number)

    agents, mode = _agents_for(settings.review_mode, settings.groq_api_key)
    store = InMemoryCodeStore()
    store.ingest_diff_context(parse_unified_diff(diff_text))
    pipeline = ReviewPipeline(agents, mode, events=events, retriever=store.hybrid_search,
                              daily_cap_usd=settings.daily_cap_usd)

    review_id = f"{payload.repo_full_name}#{payload.pr_number}@{payload.delivery_id or 'local'}"
    review = pipeline.review_text(diff_text, review_id=review_id)

    # Confidence-routed HITL: escalated reviews are posted as a COMMENT (a human decides),
    # confident ones as the actual APPROVE / REQUEST_CHANGES.
    ApprovalQueue(events=events).submit(review)
    github.post_review(payload.repo_full_name, payload.pr_number, review)

    # Durable persistence to the Tiger spine when configured (best-effort; degrades to no-op).
    from grounded.data import persist_sync
    persist_sync(settings, review, events, payload.repo_full_name, payload.pr_number)
    return review
