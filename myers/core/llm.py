"""Abstract LLM interface + a deterministic fake (the M2 seam).

No module ever imports a provider SDK directly — only this interface. Tests and the M1
baseline never touch the network. M2 adds a Groq-backed implementation (tools/llm_client.py);
the FakeLLM keeps the whole suite deterministic and free (failure modes: determinism-in-tests,
cost blowout).

Cost is computed by the concrete client (which knows the model's pricing) and carried on the
response so the events spine and BudgetGuard can attribute spend per call (ADR-004).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float = 0.0


class LLMClient(ABC):
    @abstractmethod
    def complete(self, *, system: str, user: str, model: str | None = None) -> LLMResponse:
        """Return a completion. Implementations MUST allow the model to say 'I don't know'."""


class FakeLLM(LLMClient):
    """Deterministic stand-in used by every test and offline demo.

    Returns a canned reply verbatim; same input -> same output, always, cost 0.
    """

    def __init__(self, canned: str = "[]") -> None:
        self._canned = canned

    def complete(self, *, system: str, user: str, model: str | None = None) -> LLMResponse:
        return LLMResponse(
            text=self._canned,
            model=model or "fake",
            tokens_in=len(system.split()) + len(user.split()),
            tokens_out=len(self._canned.split()),
            cost_usd=0.0,
        )
