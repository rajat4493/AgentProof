"""One-shot live test: drives a real Stripe test-mode refund through
AgentProof end-to-end — a genuine Claude agent issues the refund against
Stripe's own API with a write-scoped Restricted Key, then AgentProof
independently re-queries Stripe with a *separate* read-scoped Restricted Key
and verifies.

Requires:
  - A running backend (docs/RUNNING_LOCALLY.md)
  - STRIPE_WRITE_KEY / STRIPE_READ_KEY set in backend/.env — both rk_test_...
    Restricted Keys (test mode, no real money): write key scoped to
    Write-only on Refunds + Read on Charges (it must read a charge to see
    the amount to refund isn't needed here, but Stripe's refund endpoint
    itself only needs Refunds:Write); read key scoped to Read-only on
    Charges, nothing else.
  - A pre-existing Stripe TEST MODE charge (created out of band — e.g. via
    the Stripe dashboard's test-mode "create a payment" or the API with a
    test card token). AgentProof's agent only refunds; it does not create
    charges. Pass that charge's id and amount as argv.
  - A real ANTHROPIC_API_KEY (same as every other live test in this repo).

Usage:
    cd backend && source .venv/bin/activate
    python3 scripts/test_stripe_integration.py <charge_id> <amount_minor_units> <currency> [customer_id]

Example:
    python3 scripts/test_stripe_integration.py ch_3Pxxxxxxxx 2500 USD cus_Pxxxxxxxx

Deliberately makes ONE live run per invocation — this drives real Claude API
calls plus real (test-mode) Stripe API calls. Don't loop this in CI.
"""

import asyncio
import sys

import httpx

sys.path.insert(0, ".")


async def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(1)

    charge_id = sys.argv[1]
    amount_minor_units = int(sys.argv[2])
    currency = sys.argv[3]
    customer_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"

    from app.config import settings

    print(f"=== Testing Stripe integration against real charge {charge_id} (test mode) ===\n")

    with httpx.Client(base_url=settings.simulator_base_url, timeout=10) as client:
        task_resp = client.post(
            "/api/tasks",
            json={
                "order_id": charge_id,
                "customer_id": customer_id,
                "expected_amount_minor_units": amount_minor_units,
                "currency": currency,
                "notification_required": False,
                "original_request": f"Refund {amount_minor_units} {currency} minor units for Stripe charge {charge_id}.",
                "target_system": "stripe",
            },
        )
        task_resp.raise_for_status()
        task = task_resp.json()
        print(f"Task created: {task['id']} (target_system=stripe)")

        run_resp = client.post("/api/runs", json={"task_id": task["id"]})
        run_resp.raise_for_status()
        run = run_resp.json()
        print(f"\nAgent raw_claim: {run['raw_claim']!r}")

        claim_resp = client.post(f"/api/runs/{run['id']}/claim", json={})
        claim_resp.raise_for_status()
        claim_body = claim_resp.json()
        print(f"\nNormalized claim_type: {claim_body['claim_type']!r}")
        print(f"Normalized claim: {claim_body['normalized_claim']}")

        verify_resp = client.post(f"/api/runs/{run['id']}/verify")
        verify_resp.raise_for_status()
        verify_body = verify_resp.json()

    print(f"\n=== VERDICT: {verify_body['verdict']} ===")
    print(verify_body["verdict_explanation"])
    print("\nPredicate results:")
    for p in verify_body["predicate_results"] or []:
        mark = "PASS" if p["passed"] is True else ("FAIL" if p["passed"] is False else "????")
        print(f"  [{mark}] {p['field']}: expected={p['expected']!r} observed={p['observed']!r}")

    print(f"\nRaw Stripe evidence: {verify_body['raw_evidence']}")


if __name__ == "__main__":
    asyncio.run(main())
