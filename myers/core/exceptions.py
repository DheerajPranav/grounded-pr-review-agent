"""Shared exception types. Lives in core so every module can raise/catch them."""


class MyersError(Exception):
    """Base class for all myers errors."""


class DiffParseError(MyersError):
    """A diff could not be parsed. Callers degrade: skip the file, keep reviewing."""


class BudgetExceededError(MyersError):
    """BudgetGuard hard-block: the daily cost cap was reached (ADR-004)."""


class ReviewTimeoutError(MyersError):
    """A reviewer/specialist exceeded its per-node timeout. Join must not hang."""
