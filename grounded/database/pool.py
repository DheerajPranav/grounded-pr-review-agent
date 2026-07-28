"""Async connection pool over Tiger Cloud / Postgres.

asyncpg is imported lazily, so the package installs and the whole test suite runs with no DB
and no driver. A Database is only constructed when TIGER_DATABASE_URL is set; the repositories
take a plain connection object, so they unit-test against a fake without a live server.
"""

from __future__ import annotations

from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "scripts" / "migrations" / "2026-06-tiger-init.sql"


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None

    async def connect(self):
        import asyncpg  # lazy: only needed when actually talking to Tiger
        self._pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=5)
        return self

    def acquire(self):
        """Async context manager yielding a connection (asyncpg pool.acquire())."""
        if self._pool is None:
            raise RuntimeError("Database.connect() must be awaited first")
        return self._pool.acquire()

    async def apply_migration(self, path: Path | str = MIGRATION_PATH) -> None:
        sql = Path(path).read_text(encoding="utf-8")
        async with self.acquire() as conn:
            await conn.execute(sql)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
