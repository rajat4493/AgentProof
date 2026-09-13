"""Unit tests for app.adapter_stripe.StripeEvidenceAdapter using an injected
StripeReadCaller — no real Stripe API call. Also exercises the full
evidence -> verdict_engine.evaluate() path with the real STRIPE_REFUND_V1
proof definition, the same way test_primitives.py checks REFUND_COMPLETED_V1
end-to-end, so this claim type's proof definition is proven against actual
(faked) evidence, not just structurally registered.
"""

import pytest

from app.adapter_stripe import StripeChargeResult, StripeEvidenceAdapter
from app.models import Verdict
from app.proof import STRIPE_REFUND_V1
from app.schemas import ExpectedOutcome, StripeRefundClaim
from app.verdict_engine import evaluate


def _expected() -> ExpectedOutcome:
    return ExpectedOutcome(
        task_id="TASK-stripe-3",
        order_id="ch_test_555",
        customer_id="cus_test_555",
        expected_amount_minor_units=2000,
        currency="USD",
        notification_required=False,
    )


def _claim() -> StripeRefundClaim:
    return StripeRefundClaim(
        claim_type="stripe_refund",
        charge_id="ch_test_555",
        amount_claimed_minor_units=2000,
        currency_claimed="USD",
        refund_claimed=True,
    )


@pytest.mark.asyncio
async def test_verified_when_stripe_charge_matches_expected_outcome():
    def fake_reader(*, charge_id: str) -> StripeChargeResult:
        assert charge_id == "ch_test_555"
        return StripeChargeResult(
            reachable=True,
            charge={
                "id": charge_id,
                "customer": "cus_test_555",
                "refunded": True,
                "amount_refunded": 2000,
                "currency": "usd",  # Stripe returns lowercase — adapter must normalize
            },
        )

    adapter = StripeEvidenceAdapter(read_caller=fake_reader)
    collection = await adapter.collect_evidence(_claim(), _expected(), "RUN-stripe-3")

    verdict, results = evaluate(STRIPE_REFUND_V1, _expected(), collection.normalized(), collection.unreachable_fields())
    assert verdict == Verdict.VERIFIED
    assert all(r.passed for r in results)


@pytest.mark.asyncio
async def test_contradicted_when_charge_was_never_refunded():
    """The FALSE_ACK-equivalent case for Stripe: the agent claims a refund
    happened but the charge shows otherwise."""

    def fake_reader(*, charge_id: str) -> StripeChargeResult:
        return StripeChargeResult(
            reachable=True,
            charge={"id": charge_id, "customer": "cus_test_555", "refunded": False, "amount_refunded": 0, "currency": "usd"},
        )

    adapter = StripeEvidenceAdapter(read_caller=fake_reader)
    collection = await adapter.collect_evidence(_claim(), _expected(), "RUN-stripe-4")

    verdict, results = evaluate(STRIPE_REFUND_V1, _expected(), collection.normalized(), collection.unreachable_fields())
    assert verdict == Verdict.CONTRADICTED
    failed_fields = {r.field for r in results if r.passed is False}
    assert "charge.refunded" in failed_fields
    assert "charge.amount_refunded" in failed_fields


@pytest.mark.asyncio
async def test_indeterminate_when_stripe_is_unreachable():
    def fake_reader(*, charge_id: str) -> StripeChargeResult:
        return StripeChargeResult(reachable=False, charge=None)

    adapter = StripeEvidenceAdapter(read_caller=fake_reader)
    collection = await adapter.collect_evidence(_claim(), _expected(), "RUN-stripe-5")

    verdict, results = evaluate(STRIPE_REFUND_V1, _expected(), collection.normalized(), collection.unreachable_fields())
    assert verdict == Verdict.INDETERMINATE
    assert all(r.passed is None for r in results)


@pytest.mark.asyncio
async def test_charge_exists_false_when_charge_not_found():
    def fake_reader(*, charge_id: str) -> StripeChargeResult:
        return StripeChargeResult(reachable=True, charge=None)

    adapter = StripeEvidenceAdapter(read_caller=fake_reader)
    collection = await adapter.collect_evidence(_claim(), _expected(), "RUN-stripe-6")

    normalized = collection.normalized()
    assert normalized["charge_exists"] is False

    verdict, results = evaluate(STRIPE_REFUND_V1, _expected(), normalized, collection.unreachable_fields())
    assert verdict == Verdict.CONTRADICTED
