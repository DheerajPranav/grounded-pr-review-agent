"""Shared exception types. Lives in core so every module can raise/catch them."""


class GroundedError(Exception):
    """Base class for all grounded errors."""


class DiffParseError(GroundedError):
    """A diff could not be parsed. Callers degrade: skip the file, keep reviewing."""


class BudgetExceededError(GroundedError):
    """BudgetGuard hard-block: the daily cost cap was reached (ADR-004)."""


class ReviewTimeoutError(GroundedError):
    """A reviewer/specialist exceeded its per-node timeout. Join must not hang."""
