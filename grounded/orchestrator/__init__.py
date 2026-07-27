"""orchestrator — drives the review flow. M1: an in-process pipeline; M3: LangGraph fan-out."""

from grounded.orchestrator.pipeline import ReviewPipeline

__all__ = ["ReviewPipeline"]
