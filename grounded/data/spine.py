"""The data-spine factory.

`make_code_store` and the sink both DEGRADE GRACEFULLY: with no TIGER_DATABASE_URL the system
runs entirely on the in-memory store and skips durable persistence; set the URL and the same
code path writes to Tiger. Persistence is best-effort — a DB hiccup is recorded on the spine
and never fails the review (degrade slower-but-correct).
"""

from __future__ import annotations

import asyncio

from grounded.core.config import Settings
from grounded.database import Database
from grounded.database.repositories import TruthRepository
from grounded.memory import InMemoryCodeStore
from grounded.observability import EventLog
from grounded.observability.tiger_events import EventRepository


class NoopSink:
    enabled = False

    async def persist(self, review, events, repo: str, pr_number: int) -> None:
        return None


class TigerSink:
    enabled = True

    def __init__(self, db: Database) -> None:
        self.db = db

    async def persist(self, review, events, repo: str, pr_number: int) -> None:
        async with self.db.acquire() as conn:
            await EventRepository(conn).flush(events)
            await TruthRepository(conn).save_review(review, repo, pr_number)


def make_code_store(settings: Settings, conn=None):
    """In-memory per-PR store by default; the Tiger whole-repo store when a connection is given."""
    if conn is not None and settings.tiger_database_url:
        from grounded.memory.tiger_client import TigerCodeStore
        return TigerCodeStore(conn)
    return InMemoryCodeStore()


def persist_sync(settings: Settings, review, event_log: EventLog, repo: str, pr_number: int) -> bool:
    """Best-effort durable persistence. Returns True if written, False if skipped/failed."""
    if not settings.tiger_database_url:
        return False

    async def _run() -> None:
        db = await Database(settings.tiger_database_url).connect()
        try:
            await TigerSink(db).persist(review, event_log.for_review(review.review_id), repo, pr_number)
        finally:
            await db.close()

    try:
        asyncio.run(_run())
        return True
    except Exception as exc:  # never fail the review over persistence
        event_log.record(review.review_id, "database", "tool.call",
                         outcome="persist_failed", payload={"error": type(exc).__name__})
        return False
