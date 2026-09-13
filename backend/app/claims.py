"""Claim model primitive.

Extracted from Milestones 1-2's one working claim type (`refund_and_notify`)
per docs/MVP_SCOPE.md § Milestone 3: a `claim_type -> Pydantic schema`
registry, so app/claim_normalizer.py looks up the schema to validate against
generically instead of hardcoding one model class. Still exactly one entry —
this registry exists so a second claim type could be added later without
touching the normalizer's logic, not because a second type is built in V0.

Pydantic remains the sole authoritative validation boundary (each schema
here is `extra="forbid"`) — this registry only decides *which* schema
applies for a given claim_type; it adds no validation behavior of its own.
"""

from pydantic import BaseModel

from app.schemas import RefundAndNotifyClaim, StripeRefundClaim

CLAIM_SCHEMAS: dict[str, type[BaseModel]] = {
    "refund_and_notify": RefundAndNotifyClaim,
    "stripe_refund": StripeRefundClaim,
}

KNOWN_CLAIM_TYPES: tuple[str, ...] = tuple(CLAIM_SCHEMAS.keys())
