"""Abstract LLM interface + a deterministic fake (the M2 seam).

No module ever imports openai directly — only this interface. Tests and the M1 baseline
never touch the network. M2 adds an OpenAI-backed implementation; the FakeLLM keeps the
whole suite deterministic and free (failure mode: determinism-in-tests, cost blowout).
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

    @property
    def cost_usd(self) -> float:
        # Illustrative pricing; real numbers come from the model_router at M2.
        return round((self.tokens_in * 0.000_003) + (self.tokens_out * 0.000_015), 6)


class LLMClient(ABC):
    @abstractmethod
    def complete(self, *, system: str, user: str, model: str = "default") -> LLMResponse:
        """Return a completion. Implementations MUST allow the model to say 'I don't know'."""


class FakeLLM(LLMClient):
    """Deterministic stand-in: echoes a canned reply keyed off the prompt length.

    Used until M2 wires a real provider. Same input -> same output, always.
    """

    def __init__(self, canned: str = "NO_FINDINGS") -> None:
        self._canned = canned

    def complete(self, *, system: str, user: str, model: str = "fake") -> LLMResponse:
        return LLMResponse(
            text=self._canned,
            model=model,
            tokens_in=len(system.split()) + len(user.split()),
            tokens_out=len(self._canned.split()),
        )
