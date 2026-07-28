"""Relational truth: one row per review, one per finding, plus HITL state.

Takes a plain async connection (asyncpg or a fake), so the SQL is unit-tested without a DB.
"""

from __future__ import annotations

from grounded.models import Review

_REVIEW_UPSERT = (
    "INSERT INTO pr_review_records "
    "(review_id, repo, pr_number, mode, decision, overall_confidence, escalated, cost_usd, latency_ms) "
    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) "
    "ON CONFLICT (review_id) DO UPDATE SET decision = EXCLUDED.decision, "
    "overall_confidence = EXCLUDED.overall_confidence, escalated = EXCLUDED.escalated, "
    "cost_usd = EXCLUDED.cost_usd, latency_ms = EXCLUDED.latency_ms"
)
_FINDING_INSERT = (
    "INSERT INTO finding_records "
    "(review_id, rule_id, agent_type, category, severity, summary, file_path, line_start, line_end, confidence) "
    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)"
)


class TruthRepository:
    def __init__(self, conn) -> None:
        self.conn = conn

    async def save_review(self, review: Review, repo: str, pr_number: int) -> None:
        await self.conn.execute(
            _REVIEW_UPSERT, review.review_id, repo, pr_number, review.mode,
            review.decision.value, review.overall_confidence, review.escalated,
            review.cost_usd, review.latency_ms,
        )
        # replace findings for this review, then insert the current set
        await self.conn.execute("DELETE FROM finding_records WHERE review_id = $1", review.review_id)
        if review.findings:
            await self.conn.executemany(_FINDING_INSERT, [
                (review.review_id, f.rule_id, f.agent_type.value, f.category.value,
                 f.severity.value, f.summary, f.file_path, f.line_start, f.line_end, f.confidence)
                for f in review.findings
            ])
