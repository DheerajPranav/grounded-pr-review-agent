"""Ingress defenses: HMAC signature verification + delivery idempotency.

A GitHub webhook is authenticated by an HMAC-SHA256 of the raw body under a shared secret,
sent as `X-Hub-Signature-256: sha256=<hex>`. We verify it in constant time (reject forgeries
before any work), and drop replayed deliveries by their `X-GitHub-Delivery` UUID so a retried
delivery is acknowledged once, not reviewed twice (the L8 idempotency defense).
"""

from __future__ import annotations

import hashlib
import hmac


def sign(secret: str | bytes, payload: bytes) -> str:
    """Produce a GitHub-style signature header value: 'sha256=<hexdigest>'."""
    key = secret.encode() if isinstance(secret, str) else secret
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str | bytes, payload: bytes, signature_header: str | None) -> bool:
    """Constant-time verification. Returns False on any malformed/missing/forged signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = sign(secret, payload)
    return hmac.compare_digest(expected, signature_header)


class IdempotencyStore:
    """Tracks seen delivery ids so a replayed webhook is dropped. In-memory here; a durable
    table (or Redis) in production. Atomic check-and-add prevents a double-review race."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_new(self, delivery_id: str) -> bool:
        """True the first time a delivery id is seen; False for every replay."""
        if not delivery_id or delivery_id in self._seen:
            return False
        self._seen.add(delivery_id)
        return True
