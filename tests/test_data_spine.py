"""Tiger/Postgres data spine — SQL construction + graceful fallback, no live DB required."""

import asyncio

from grounded.core.config import Settings
from grounded.data import make_code_store, persist_sync
from grounded.database import MIGRATION_PATH
from grounded.database.repositories import TruthRepository
from grounded.memory import InMemoryCodeStore
from grounded.memory.tiger_client import TigerCodeStore
from grounded.models import AgentType, Category, Decision, Evidence, Finding, Review, Severity
from grounded.observability import AgentEvent, EventLog
from grounded.observability.tiger_events import EventRepository


class FakeConn:
    def __init__(self, dense=None, fts=None) -> None:
        self.calls: list = []
        self._dense = dense or []
        self._fts = fts or []

    async def execute(self, sql, *args):
        self.calls.append(("execute", sql, args))

    async def executemany(self, sql, rows):
        self.calls.append(("executemany", sql, list(rows)))

    async def fetch(self, sql, *args):
        self.calls.append(("fetch", sql, args))
        if "<=>" in sql:
            return self._dense
        if "plainto_tsquery" in sql:
            return self._fts
        return []


def _finding():
    return Finding(rule_id="r", agent_type=AgentType.SECURITY, category=Category.SECURITY,
                   severity=Severity.CRITICAL, summary="s", file_path="a.py", line_start=1,
                   line_end=1, confidence=0.9, evidence=[Evidence(file_path="a.py", line=1, snippet="x")])


def _review():
    return Review(review_id="rid", mode="specialists", decision=Decision.REQUEST_CHANGES,
                  findings=[_finding()], escalated=True, cost_usd=0.002, latency_ms=900)


# -- fallback -----------------------------------------------------------------
def test_code_store_falls_back_to_in_memory_without_url():
    assert isinstance(make_code_store(Settings()), InMemoryCodeStore)


def test_persist_sync_skips_without_url():
    assert persist_sync(Settings(), _review(), EventLog(), "acme/shop", 1) is False


# -- event repository ---------------------------------------------------------
def test_event_flush_batches_inserts():
    log = EventLog()
    log.record("rid", "llm", "llm.call", model="x", cost_usd=0.001,
               payload={"tokens_in": 10, "tokens_out": 5})
    repo = EventRepository(FakeConn())
    n = asyncio.run(repo.flush(log.for_review("rid")))
    assert n == 1
    kind, sql, rows = repo.conn.calls[0]
    assert kind == "executemany" and "INSERT INTO agent_events" in sql
    assert len(rows[0]) == 12  # all columns bound


# -- truth repository ---------------------------------------------------------
def test_save_review_writes_review_and_findings():
    conn = FakeConn()
    asyncio.run(TruthRepository(conn).save_review(_review(), "acme/shop", 7))
    sqls = " ".join(c[1] for c in conn.calls)
    assert "INSERT INTO pr_review_records" in sqls
    assert "DELETE FROM finding_records" in sqls
    assert "INSERT INTO finding_records" in sqls


# -- Tiger code store (pgvector + FTS + RRF) ----------------------------------
def test_tiger_hybrid_search_merges_by_rrf():
    dense = [{"path": "a.py", "chunk_index": 0, "content": "charge_customer"}]
    fts = [{"path": "b.py", "chunk_index": 0, "content": "refresh_session"}]
    store = TigerCodeStore(FakeConn(dense=dense, fts=fts))
    results = asyncio.run(store.hybrid_search("charge", k=2))
    paths = {c.path for c in results}
    assert paths == {"a.py", "b.py"}  # both signals contribute
    # verify both queries were issued
    sqls = " ".join(c[1] for c in store.conn.calls if c[0] == "fetch")
    assert "<=>" in sqls and "plainto_tsquery" in sqls


# -- migration ----------------------------------------------------------------
def test_migration_defines_all_lanes():
    sql = MIGRATION_PATH.read_text()
    for obj in ["code_chunks", "create_hypertable('agent_events'", "agent_health_1m",
                "pr_cost_hourly", "pr_review_records", "finding_records"]:
        assert obj in sql, f"migration missing {obj}"
