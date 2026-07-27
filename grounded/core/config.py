"""Runtime settings, read from the environment (never hard-coded — secrets live in .env).

Lives in core (depends on nothing) so both the api layer and the job runner can read it
without violating the inward-only dependency rule.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    github_webhook_secret: str = ""
    github_token: str = ""
    review_mode: str = "baseline"          # baseline | llm | specialists
    daily_cap_usd: float | None = None
    tiger_database_url: str = ""
    groq_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        cap = os.environ.get("DAILY_CAP_USD")
        return cls(
            github_webhook_secret=os.environ.get("GITHUB_WEBHOOK_SECRET", ""),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            review_mode=os.environ.get("REVIEW_MODE", "baseline"),
            daily_cap_usd=float(cap) if cap else None,
            tiger_database_url=os.environ.get("TIGER_DATABASE_URL", ""),
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        )

    @property
    def webhook_configured(self) -> bool:
        return bool(self.github_webhook_secret)
