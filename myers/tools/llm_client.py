"""Groq-backed LLM client (implements core.llm.LLMClient).

We use Groq: an OpenAI-compatible inference API with a free tier and a simple API key.
The ``groq`` SDK is imported lazily so the package installs and the baseline/tests run with
no provider dependency at all — only constructing a GroqLLMClient needs it.

Cost is computed here (the client knows the model's per-token price) and carried on the
response so the events spine and BudgetGuard can attribute spend per call (ADR-004).
"""

from __future__ import annotations

import os

from myers.core.llm import LLMClient, LLMResponse

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Illustrative Groq pricing, USD per token (public per-1M-token rates / 1e6).
# Used only for cost attribution/observability — Groq's free tier bills nothing.
_PRICING: dict[str, tuple[float, float]] = {
    "llama-3.3-70b-versatile": (0.59e-6, 0.79e-6),
    "llama-3.1-8b-instant": (0.05e-6, 0.08e-6),
}
_DEFAULT_PRICE = (0.50e-6, 0.80e-6)


class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str | None = None, default_model: str = DEFAULT_MODEL) -> None:
        try:
            from groq import Groq
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "The 'groq' package is required for --mode llm. Install with: pip install groq"
            ) from exc

        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
                "and export GROQ_API_KEY=... (see .env.example)."
            )
        self._client = Groq(api_key=key)
        self.default_model = default_model

    def complete(self, *, system: str, user: str, model: str | None = None) -> LLMResponse:
        model = model or self.default_model
        resp = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,  # best-effort determinism
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        pin, pout = _PRICING.get(model, _DEFAULT_PRICE)
        return LLMResponse(
            text=text,
            model=model,
            tokens_in=tin,
            tokens_out=tout,
            cost_usd=round(tin * pin + tout * pout, 6),
        )
