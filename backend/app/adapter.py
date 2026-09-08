"""Evidence adapter interface + the one V0 implementation.

Per docs/PROOF_MODEL.md § Evidence adapter interface. AgentProof always
collects evidence by independently querying the system of record with its
own read-only credential — never by trusting the agent's claim or the
agent's own tool-call results.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.config import settings
from app.schemas import ExpectedOutcome, RefundAndNotifyClaim

SYSTEM_PAYMENT_CUSTOMER = "payment_customer_system"


@dataclass
class Evidence:
    system: str
    field: str
    value: Any
    reachable: bool
    checked_at: str


@dataclass
class EvidenceCollectionResult:
    systems_queried: list[str]
    credential_role_used: str
    raw: dict[str, Any]
    evidence: list[Evidence]

    def normalized(self) -> dict[str, Any]:
        return {e.field: e.value for e in self.evidence}

    def unreachable_fields(self) -> set[str]:
        return {e.field for e in self.evidence if not e.reachable}


class EvidenceAdapter(Protocol):
    id: str
    name: str

    async def collect_evidence(
        self, claim: RefundAndNotifyClaim, expected_outcome: ExpectedOutcome
    ) -> EvidenceCollectionResult: ...


class PaymentCustomerEvidenceAdapter:
    """The one V0 evidence adapter: the payment/customer simulator.

    No other adapters (incident, identity, ...) exist in V0 — this interface
    is written generically so future adapters could implement it later, not
    to be generalized now.
    """

    id = "payment_customer_simulator_v1"
    name = "Payment & customer system of record (simulator)"

    def __init__(self, base_url: str | None = None, credential: str | None = None):
        self.base_url = base_url or settings.simulator_base_url
        self.credential = credential or settings.verifier_read_credential

    async def collect_evidence(
        self, claim: RefundAndNotifyClaim, expected_outcome: ExpectedOutcome
    ) -> EvidenceCollectionResult:
        from datetime import datetime, timezone

        headers = {"X-AgentProof-Credential": self.credential}
        raw: dict[str, Any] = {}
        evidence: list[Evidence] = []

        def checked_at() -> str:
            return datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            refunds_reachable = True
            refunds_payload: list[dict] = []
            try:
                resp = await client.get(
                    "/simulator/read/refunds",
                    params={"order_id": expected_outcome.order_id, "customer_id": expected_outcome.customer_id},
                    headers=headers,
                )
                resp.raise_for_status()
                refunds_payload = resp.json()
            except httpx.HTTPError:
                refunds_reachable = False
            raw["refunds"] = refunds_payload if refunds_reachable else None

            messages_reachable = True
            messages_payload: list[dict] = []
            try:
                resp = await client.get(
                    "/simulator/read/messages",
                    params={"order_id": expected_outcome.order_id, "customer_id": expected_outcome.customer_id},
                    headers=headers,
                )
                resp.raise_for_status()
                messages_payload = resp.json()
            except httpx.HTTPError:
                messages_reachable = False
            raw["messages"] = messages_payload if messages_reachable else None

        ts = checked_at()

        if refunds_reachable:
            refund = refunds_payload[0] if refunds_payload else None
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund_exists", refund is not None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund.order_id", refund["order_id"] if refund else None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund.customer_id", refund["customer_id"] if refund else None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund.amount_minor_units", refund["amount_minor_units"] if refund else None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund.currency", refund["currency"] if refund else None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "refund.status", refund["status"] if refund else None, True, ts))
        else:
            for field in (
                "refund_exists",
                "refund.order_id",
                "refund.customer_id",
                "refund.amount_minor_units",
                "refund.currency",
                "refund.status",
            ):
                evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, field, None, False, ts))

        if messages_reachable:
            message = messages_payload[0] if messages_payload else None
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "notification.exists", message is not None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "notification.customer_id", message["customer_id"] if message else None, True, ts))
            evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, "notification.order_id", message["order_id"] if message else None, True, ts))
        else:
            for field in ("notification.exists", "notification.customer_id", "notification.order_id"):
                evidence.append(Evidence(SYSTEM_PAYMENT_CUSTOMER, field, None, False, ts))

        return EvidenceCollectionResult(
            systems_queried=[SYSTEM_PAYMENT_CUSTOMER],
            credential_role_used="verifier_read",
            raw=raw,
            evidence=evidence,
        )
