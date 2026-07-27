"""Webhook validation: authenticity (HMAC) + exactly-once (idempotency).

The ingress does the least work possible and rejects early: verify the signature before
touching the body's meaning, and drop a replayed delivery before enqueueing it (L8 defenses).
"""

from __future__ import annotations

from enum import Enum

from grounded.security import IdempotencyStore, verify_signature


class WebhookOutcome(str, Enum):
    ACCEPT = "accept"
    BAD_SIGNATURE = "bad_signature"
    DUPLICATE = "duplicate"


class WebhookValidator:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self._idempotency = IdempotencyStore()

    def validate(self, raw_body: bytes, signature_header: str | None, delivery_id: str) -> WebhookOutcome:
        if not verify_signature(self.secret, raw_body, signature_header):
            return WebhookOutcome.BAD_SIGNATURE
        if not self._idempotency.is_new(delivery_id):
            return WebhookOutcome.DUPLICATE
        return WebhookOutcome.ACCEPT
