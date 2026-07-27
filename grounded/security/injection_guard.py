"""Prompt-injection detection.

The diff and PR text are untrusted input (the L8 defense). Specialists already treat them as
data, but the guard adds detection: if a change tries to talk to the reviewer — "ignore
previous instructions", "approve this PR", "you are now..." — we record it and force the
review to a human rather than trusting a model that just read an adversarial instruction.
Detection is deliberately conservative (favor escalation over silent auto-approval).
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore-instructions", re.compile(r"(?i)ignore\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions|prompts?)")),
    ("disregard-instructions", re.compile(r"(?i)disregard\s+(all\s+)?(previous|above|the)\s+\w+")),
    ("role-override", re.compile(r"(?i)you\s+are\s+now\s+|new\s+system\s+prompt|act\s+as\s+(an?\s+)?\w+")),
    ("approve-directive", re.compile(r"(?i)(please\s+)?(approve|lgtm|pass)\s+(this\s+)?(pr|pull\s*request|change|diff|review)")),
    ("system-prompt-leak", re.compile(r"(?i)(reveal|print|show)\s+(your\s+)?(system\s+)?(prompt|instructions)")),
    ("override-directive", re.compile(r"(?i)override\s+(the\s+)?(safety|security|guard|rules?)")),
    ("do-not-report", re.compile(r"(?i)do\s+not\s+(report|flag|mention|raise)\b")),
]


def scan_injection(text: str) -> list[str]:
    """Return the labels of any injection patterns found in the text (empty if clean)."""
    if not text:
        return []
    return [label for label, pat in _PATTERNS if pat.search(text)]


def has_injection(text: str) -> bool:
    return bool(scan_injection(text))
