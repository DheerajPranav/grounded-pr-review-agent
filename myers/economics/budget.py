"""BudgetGuard — the cost-blowout defense (ADR-004).

Reads the running spend (in production, from the agent_health_1m continuous aggregate; here,
from any cost source callable) and HARD-BLOCKS before an LLM call once the daily cap is hit.
The system degrades to slower-but-correct (baseline static review), never fast-but-wrong.
"""

from __future__ import annotations

from collections.abc import Callable

from myers.core.exceptions import BudgetExceededError


class BudgetGuard:
    def __init__(self, daily_cap_usd: float, spent_source: Callable[[], float]) -> None:
        self.daily_cap_usd = daily_cap_usd
        self._spent_source = spent_source

    def spent(self) -> float:
        return self._spent_source()

    def remaining(self) -> float:
        return max(0.0, self.daily_cap_usd - self.spent())

    def check(self) -> None:
        """Raise if the cap is already reached. Call BEFORE incurring a new LLM cost."""
        spent = self.spent()
        if spent >= self.daily_cap_usd:
            raise BudgetExceededError(
                f"daily budget cap ${self.daily_cap_usd:.4f} reached "
                f"(spent ${spent:.4f}); blocking further LLM calls"
            )
