"""Aggregator: the deterministic merge + confidence gate.

This is a DETERMINISTIC decision step (invariant: no LLM behind a deterministic decision).
It merges findings from one-or-many agents, deduplicates ones raised on the same file+line+rule
(keeping the highest-confidence copy and recording which agents agreed — the correlated-agent
defense), computes an overall confidence in the *decision it makes*, and routes:

    CRITICAL present            -> request_changes AND escalate to a human (critical/irreversible)
    HIGH present                -> request_changes
    driver below conf floor     -> escalate (uncertain)  [full HITL queue lands at M4]
    otherwise                   -> approve (with comments)
"""

from __future__ import annotations

from grounded.models import Decision, Finding, Review, Severity

ESCALATE_CONF_FLOOR = 0.40  # below this, an actionable finding is too uncertain to auto-act on


class Aggregator:
    def merge(self, review_id: str, mode: str, agent_findings: list[list[Finding]]) -> Review:
        merged: dict[tuple, Finding] = {}
        for findings in agent_findings:
            for f in findings:
                key = f.dedup_key
                existing = merged.get(key)
                if existing is None:
                    merged[key] = f
                else:
                    # Keep the higher-confidence copy; record agreement (data, not prose).
                    keep, other = (f, existing) if f.confidence > existing.confidence else (existing, f)
                    agreed = list(dict.fromkeys([*keep.agreed_by, keep.agent_type, other.agent_type]))
                    merged[key] = keep.model_copy(update={"agreed_by": agreed})

        findings = sorted(merged.values(), key=lambda f: f.sort_key)
        decision, confidence, escalated, reason = self._route(findings)
        return Review(
            review_id=review_id,
            mode=mode,
            decision=decision,
            findings=findings,
            overall_confidence=confidence,
            escalated=escalated,
            escalation_reason=reason,
        )

    def _route(self, findings: list[Finding]) -> tuple[Decision, float, bool, str]:
        if not findings:
            return Decision.APPROVE, 1.0, False, ""

        driver = findings[0]  # highest severity, then deterministic order
        confidence = driver.confidence

        if driver.severity is Severity.CRITICAL:
            return (Decision.REQUEST_CHANGES, confidence, True,
                    f"CRITICAL finding '{driver.rule_id}' — critical/irreversible, routed to a human.")

        if driver.severity is Severity.HIGH:
            if confidence < ESCALATE_CONF_FLOOR:
                return (Decision.REQUEST_CHANGES, confidence, True,
                        f"HIGH finding '{driver.rule_id}' below confidence floor — routed to a human.")
            return Decision.REQUEST_CHANGES, confidence, False, ""

        # MEDIUM and below: approve-with-comments, but escalate if it's actionable yet uncertain.
        if driver.severity is Severity.MEDIUM and confidence < ESCALATE_CONF_FLOOR:
            return (Decision.APPROVE, confidence, True,
                    f"MEDIUM finding '{driver.rule_id}' below confidence floor — flagged for a human.")
        return Decision.APPROVE, confidence, False, ""
