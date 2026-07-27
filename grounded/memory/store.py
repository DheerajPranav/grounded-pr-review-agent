"""In-memory code chunk store with hybrid retrieval.

Hybrid = two independent signals fused by Reciprocal Rank Fusion (RRF):
  - dense:  cosine over embeddings          (catches meaning / related code)
  - exact:  identifier overlap with the query (catches exact names — functions, keys, codes)
Pure vector search misses exact identifiers; pure keyword search misses semantic relatives.
This mirrors the DiskANN + FTS(GIN) design of the Tiger `code_chunks` table (see wiki),
realized locally so grounding works offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from grounded.memory.embedder import Embedder, HashingEmbedder, cosine, tokenize

_RRF_K = 60
_CHUNK_LINES = 12
_CODE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs", ".c", ".cpp", ".h"}


@dataclass
class CodeChunk:
    repo: str
    path: str
    chunk_index: int
    content: str
    symbol: str = ""
    embedding: list[float] = field(default_factory=list)

    @property
    def citation(self) -> str:
        return f"{self.path}#{self.chunk_index}"


class InMemoryCodeStore:
    def __init__(self, embedder: Embedder | None = None, repo: str = "local") -> None:
        self.embedder = embedder or HashingEmbedder()
        self.repo = repo
        self._chunks: list[CodeChunk] = []
        self._token_index: list[set[str]] = []  # per-chunk token set, for exact match

    def __len__(self) -> int:
        return len(self._chunks)

    # -- ingestion -----------------------------------------------------------
    def add_chunk(self, path: str, content: str, symbol: str = "") -> None:
        chunk = CodeChunk(
            repo=self.repo, path=path, chunk_index=len(self._chunks),
            content=content, symbol=symbol, embedding=self.embedder.embed(content),
        )
        self._chunks.append(chunk)
        self._token_index.append(set(tokenize(content)))

    def add_file(self, path: str, content: str) -> None:
        """Chunk a file into ~fixed-size line windows (structure-aware enough for grounding)."""
        lines = content.splitlines()
        for start in range(0, max(len(lines), 1), _CHUNK_LINES):
            window = "\n".join(lines[start:start + _CHUNK_LINES]).strip()
            if window:
                self.add_chunk(path, window, symbol=_guess_symbol(window))

    def ingest_directory(self, root: str | Path) -> int:
        root = Path(root)
        before = len(self._chunks)
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix in _CODE_SUFFIXES and ".venv" not in p.parts:
                try:
                    self.add_file(str(p.relative_to(root)), p.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, OSError):
                    continue  # skip unreadable/binary; degrade, don't crash
        return len(self._chunks) - before

    def ingest_diff_context(self, parsed) -> int:
        """Fallback grounding when no repo snapshot is given: index the added code itself,
        so specialists can retrieve related lines within the changeset."""
        before = len(self._chunks)
        for f in parsed.files:
            if f.is_binary or not f.added_lines:
                continue
            content = "\n".join(a.content for a in f.added_lines)
            self.add_file(f.path, content)
        return len(self._chunks) - before

    # -- retrieval -----------------------------------------------------------
    def hybrid_search(self, query: str, k: int = 3) -> list[CodeChunk]:
        if not self._chunks:
            return []
        q_emb = self.embedder.embed(query)
        dense_rank = sorted(range(len(self._chunks)),
                            key=lambda i: cosine(q_emb, self._chunks[i].embedding), reverse=True)

        q_tokens = set(tokenize(query))
        overlaps = [(i, len(q_tokens & self._token_index[i])) for i in range(len(self._chunks))]
        exact_rank = [i for i, n in sorted(overlaps, key=lambda t: t[1], reverse=True) if n > 0]

        scores: dict[int, float] = {}
        for rank, i in enumerate(dense_rank):
            scores[i] = scores.get(i, 0.0) + 1.0 / (_RRF_K + rank)
        for rank, i in enumerate(exact_rank):
            scores[i] = scores.get(i, 0.0) + 1.0 / (_RRF_K + rank)

        top = sorted(scores, key=lambda i: scores[i], reverse=True)[:k]
        return [self._chunks[i] for i in top]


def _guess_symbol(text: str) -> str:
    import re
    m = re.search(r"\b(?:def|function|func|class)\s+([A-Za-z_]\w*)", text)
    return m.group(1) if m else ""
