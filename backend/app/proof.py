"""The one V0 proof definition.

Lives in code, per docs/PROOF_MODEL.md — no visual builder. Field names match
the normalized evidence field names produced by
app.adapter.PaymentCustomerEvidenceAdapter; `source` references resolve
against the original structured ExpectedOutcome (task.*) — never against the
agent's claim.
"""

REFUND_COMPLETED_V1 = {
    "proof_id": "refund_completed_v1",
    "claim_type": "refund_and_notify",
    "required_checks": [
        {"field": "refund_exists", "operator": "equals", "expected": True},
        {"field": "refund.order_id", "operator": "equals", "source": "order_id"},
        {"field": "refund.customer_id", "operator": "equals", "source": "customer_id"},
        {"field": "refund.amount_minor_units", "operator": "equals", "source": "expected_amount_minor_units"},
        {"field": "refund.currency", "operator": "equals", "source": "currency"},
        {"field": "refund.status", "operator": "equals", "expected": "succeeded"},
        {"field": "notification.customer_id", "operator": "equals", "source": "customer_id"},
        {"field": "notification.order_id", "operator": "equals", "source": "order_id"},
        {"field": "notification.exists", "operator": "equals", "source": "notification_required"},
    ],
}

PROOF_DEFINITIONS_BY_CLAIM_TYPE = {
    REFUND_COMPLETED_V1["claim_type"]: REFUND_COMPLETED_V1,
}
