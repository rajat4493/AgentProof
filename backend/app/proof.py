"""Proof definition primitive.

Extracted from Milestones 1-2's one working proof definition
(`refund_completed_v1`) per docs/MVP_SCOPE.md § Milestone 3: `ProofCheck`
and `ProofDefinition` are now importable types instead of an implicit JSON
convention, per docs/PROOF_MODEL.md's "architected so a visual builder could
be added later." Still exactly one proof definition, in code — no visual
builder, no file/config-driven loader.

Field names in `required_checks` match the normalized evidence field names
produced by an EvidenceAdapter (app/adapter.py); `source` references resolve
against the original structured ExpectedOutcome (task.*) — never against the
agent's claim.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class ProofCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    operator: str = "equals"
    # Exactly one of these is set: `expected` for a fixed literal, `source`
    # for a reference into the original ExpectedOutcome (task.*).
    expected: Any | None = None
    source: str | None = None

    @model_validator(mode="after")
    def _exactly_one_of_expected_or_source(self) -> "ProofCheck":
        if (self.expected is None) == (self.source is None):
            raise ValueError(f"ProofCheck {self.field!r} must set exactly one of `expected` or `source`.")
        return self


class ProofDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_id: str
    claim_type: str
    required_checks: list[ProofCheck]


REFUND_COMPLETED_V1 = ProofDefinition(
    proof_id="refund_completed_v1",
    claim_type="refund_and_notify",
    required_checks=[
        ProofCheck(field="refund_exists", expected=True),
        ProofCheck(field="refund.order_id", source="order_id"),
        ProofCheck(field="refund.customer_id", source="customer_id"),
        ProofCheck(field="refund.amount_minor_units", source="expected_amount_minor_units"),
        ProofCheck(field="refund.currency", source="currency"),
        ProofCheck(field="refund.status", expected="succeeded"),
        ProofCheck(field="notification.customer_id", source="customer_id"),
        ProofCheck(field="notification.order_id", source="order_id"),
        ProofCheck(field="notification.exists", source="notification_required"),
    ],
)

STRIPE_REFUND_V1 = ProofDefinition(
    proof_id="stripe_refund_v1",
    claim_type="stripe_refund",
    required_checks=[
        ProofCheck(field="charge_exists", expected=True),
        ProofCheck(field="charge.customer_id", source="customer_id"),
        ProofCheck(field="charge.refunded", expected=True),
        ProofCheck(field="charge.amount_refunded", source="expected_amount_minor_units"),
        ProofCheck(field="charge.currency", source="currency"),
    ],
)

PROOF_DEFINITIONS_BY_CLAIM_TYPE: dict[str, ProofDefinition] = {
    REFUND_COMPLETED_V1.claim_type: REFUND_COMPLETED_V1,
    STRIPE_REFUND_V1.claim_type: STRIPE_REFUND_V1,
}
