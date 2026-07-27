"""memory — code chunk store + hybrid retrieval (the grounding lane).

Local, offline, dependency-light by default. The Embedder and CodeStore are interfaces so a
neural embedder or the Tiger Cloud pgvector/pgvectorscale store drops in behind them later
(ADR-003) without touching callers.
"""

from grounded.memory.embedder import Embedder, HashingEmbedder
from grounded.memory.store import CodeChunk, InMemoryCodeStore

__all__ = ["Embedder", "HashingEmbedder", "CodeChunk", "InMemoryCodeStore"]
