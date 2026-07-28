"""TigerCodeStore — the production code memory (pgvector + FTS), same shape as InMemoryCodeStore.

Whole-repo memory that outlives a single PR (the in-memory store only holds the current diff).
Hybrid retrieval mirrors the local store: pgvector cosine (DiskANN) + Postgres FTS, fused by
RRF in Python. Takes an async connection so the SQL is unit-tested without a live Tiger server;
a background ingestion pipeline (data/) populates code_chunks and keeps it fresh.
"""

from __future__ import annotations

from grounded.memory.embedder import Embedder, HashingEmbedder
from grounded.memory.store import CodeChunk

_RRF_K = 60

_UPSERT = (
    "INSERT INTO code_chunks (repo, path, symbol, chunk_index, content, embedding) "
    "VALUES ($1,$2,$3,$4,$5,$6::vector) "
    "ON CONFLICT (repo, path, chunk_index) DO UPDATE SET "
    "content = EXCLUDED.content, embedding = EXCLUDED.embedding, updated_at = now()"
)
_DENSE = (
    "SELECT path, chunk_index, content FROM code_chunks WHERE repo = $1 "
    "ORDER BY embedding <=> $2::vector LIMIT $3"
)
_FTS = (
    "SELECT path, chunk_index, content FROM code_chunks "
    "WHERE repo = $1 AND content_tsv @@ plainto_tsquery('english', $2) "
    "ORDER BY ts_rank(content_tsv, plainto_tsquery('english', $2)) DESC LIMIT $3"
)


def _vec(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"


class TigerCodeStore:
    def __init__(self, conn, embedder: Embedder | None = None, repo: str = "local") -> None:
        self.conn = conn
        self.embedder = embedder or HashingEmbedder()
        self.repo = repo

    async def add_chunk(self, path: str, content: str, symbol: str = "", chunk_index: int = 0) -> None:
        await self.conn.execute(_UPSERT, self.repo, path, symbol, chunk_index, content,
                                _vec(self.embedder.embed(content)))

    async def hybrid_search(self, query: str, k: int = 3) -> list[CodeChunk]:
        dense = await self.conn.fetch(_DENSE, self.repo, _vec(self.embedder.embed(query)), k)
        fts = await self.conn.fetch(_FTS, self.repo, query, k)

        scores: dict[tuple, float] = {}
        rows: dict[tuple, dict] = {}
        for ranked in (dense, fts):
            for rank, row in enumerate(ranked):
                key = (row["path"], row["chunk_index"])
                scores[key] = scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
                rows[key] = row
        top = sorted(scores, key=lambda key: scores[key], reverse=True)[:k]
        return [CodeChunk(repo=self.repo, path=rows[key]["path"],
                          chunk_index=rows[key]["chunk_index"], content=rows[key]["content"])
                for key in top]
