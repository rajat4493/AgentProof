"""Stripe evidence adapter — AgentProof's first real (non-simulator)
EvidenceAdapter, per docs/PROOF_MODEL.md's evidence-adapter interface.

Same independence guarantee as PaymentCustomerEvidenceAdapter
(app/adapter.py): this always re-queries Stripe directly with a
read-only-scoped Restricted API key, never trusts the agent's claim or the
agent's own tool-call result as evidence.

Correlation note: the simulator adapter scopes evidence to a run_id because
multiple runs can share the same (order_id, customer_id). Here, each task's
`order_id` field holds a Stripe charge_id, which is already the unique
identifier for the exact resource the agent acted on — there is nothing to
additionally scope by. If AgentProof ever needs to tell apart multiple
refund attempts against the *same* charge, that would require reading the
charge's `refunds` list and matching by metadata (e.g. a run_id stamped by
app/agent_stripe.py) rather than only the top-level `refunded`/
`amount_refunded` fields used here — out of scope for this first pass, and
noted for a future Duck if it becomes real.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from app.adapter import Evidence, EvidenceCollectionResult
from app.config import settings
from app.schemas import ExpectedOutcome, StripeRefundClaim

SYSTEM_STRIPE = "stripe"


@dataclass
class StripeChargeResult:
    reachable: bool
    charge: dict[str, Any] | None


class StripeReadCaller(Protocol):
    """Abstraction over 'fetch a Stripe charge by id', for test injection —
    same pattern as app.agent.ClaudeCaller / app.claim_normalizer.NormalizerCaller."""

    def __call__(self, *, charge_id: str) -> StripeChargeResult: ...


def real_stripe_read_caller(base_url: str, api_key: str) -> StripeReadCaller:
    def call(*, charge_id: str) -> StripeChargeResult:
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(base_url=base_url, timeout=10.0) as client:
                resp = client.get(f"/v1/charges/{charge_id}", headers=headers)
                resp.raise_for_status()
                return StripeChargeResult(reachable=True, charge=resp.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return StripeChargeResult(reachable=True, charge=None)
            return StripeChargeResult(reachable=False, charge=None)
        except httpx.HTTPError:
            return StripeChargeResult(reachable=False, charge=None)

    return call


class StripeEvidenceAdapter:
    id = "stripe_charges_v1"
    name = "Stripe (real system of record)"

    def __init__(self, read_caller: StripeReadCaller | None = None):
        self._read_caller = read_caller

    def _caller(self) -> StripeReadCaller:
        if self._read_caller is not None:
            return self._read_caller
        if not settings.stripe_read_key:
            raise RuntimeError("STRIPE_READ_KEY is not configured.")
        return real_stripe_read_caller(settings.stripe_api_base, settings.stripe_read_key)

    async def collect_evidence(
        self,
        claim: StripeRefundClaim,
        expected_outcome: ExpectedOutcome,
        run_id: str,
    ) -> EvidenceCollectionResult:
        ts = datetime.now(timezone.utc).isoformat()
        result = self._caller()(charge_id=expected_outcome.order_id)

        raw: dict[str, Any] = {"charge": result.charge}
        evidence: list[Evidence] = []

        if not result.reachable:
            for field in (
                "charge_exists",
                "charge.customer_id",
                "charge.refunded",
                "charge.amount_refunded",
                "charge.currency",
            ):
                evidence.append(Evidence(SYSTEM_STRIPE, field, None, False, ts))
        else:
            charge = result.charge
            evidence.append(Evidence(SYSTEM_STRIPE, "charge_exists", charge is not None, True, ts))
            evidence.append(
                Evidence(SYSTEM_STRIPE, "charge.customer_id", charge.get("customer") if charge else None, True, ts)
            )
            evidence.append(
                Evidence(SYSTEM_STRIPE, "charge.refunded", charge.get("refunded") if charge else None, True, ts)
            )
            evidence.append(
                Evidence(
                    SYSTEM_STRIPE, "charge.amount_refunded", charge.get("amount_refunded") if charge else None, True, ts
                )
            )
            # Stripe returns currency lowercase ("usd"); AgentProof's task
            # convention (matching the simulator) is uppercase ISO-4217, so
            # normalize here rather than making every task-creator match
            # Stripe's casing.
            evidence.append(
                Evidence(
                    SYSTEM_STRIPE,
                    "charge.currency",
                    charge.get("currency").upper() if charge and charge.get("currency") else None,
                    True,
                    ts,
                )
            )

        return EvidenceCollectionResult(
            systems_queried=[SYSTEM_STRIPE],
            credential_role_used="verifier_read",
            raw=raw,
            evidence=evidence,
        )
