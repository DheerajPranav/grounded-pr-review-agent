"""security — the trust-boundary defenses. Depends only on models/stdlib.

Prompt-injection detection (the diff is untrusted), plus the ingress primitives (HMAC
signature verification and delivery idempotency) that protect the webhook path.
"""

from myers.security.hmac_verify import IdempotencyStore, sign, verify_signature
from myers.security.injection_guard import has_injection, scan_injection

__all__ = ["IdempotencyStore", "sign", "verify_signature", "has_injection", "scan_injection"]
