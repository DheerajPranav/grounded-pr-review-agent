"""Embeddings for the vector lane.

Groq offers chat inference only — no embeddings endpoint — so the default embedder is a
local, deterministic hashing bag-of-tokens vectorizer: it needs no model download, no key,
and no network, and it is reproducible. It is a lexical proxy for semantic similarity, not a
neural embedding; a real sentence embedder or Tiger's hosted embeddings implement the same
``Embedder`` interface and swap in without changing retrieval or the specialists.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Identifiers/words, lowercased, plus snake/camel subtokens for better matching."""
    tokens: list[str] = []
    for tok in _TOKEN_RE.findall(text):
        low = tok.lower()
        tokens.append(low)
        # split snake_case and camelCase into subtokens
        parts = re.split(r"_|(?<=[a-z0-9])(?=[A-Z])", tok)
        tokens.extend(p.lower() for p in parts if len(p) >= 2 and p.lower() != low)
    return tokens


class Embedder(ABC):
    dim: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...


class HashingEmbedder(Embedder):
    """Hash each token into a fixed-dim vector, count, L2-normalize. Deterministic."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0  # signed hashing reduces collisions
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            return vec
        return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # inputs are L2-normalized
