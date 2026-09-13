"""One-shot live test: proves AgentProof's independent verification works
identically when the *agent itself* is a real Claude Agent SDK agent
(app.agent_via_claude_sdk) instead of the default raw-Messages-API agent
(app.agent). Requires a running backend (docs/RUNNING_LOCALLY.md) and a
real ANTHROPIC_API_KEY.

Usage:
    cd backend && source .venv/bin/activate
    python3 scripts/test_agent_sdk_integration.py [NORMAL|FALSE_ACK|DROP_NOTIFICATION|READ_UNAVAILABLE]

Deliberately makes ONE live run per invocation — this drives real Claude API
calls (agent execution + claim normalization), so don't loop this in CI or
call it repeatedly without reason.
"""

import asyncio
import sys

import httpx

sys.path.insert(0, ".")

from app.agent_via_claude_sdk import run_agent_via_claude_sdk  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Run, RunStatus  # noqa: E402
from app.schemas import ExpectedOutcome  # noqa: E402

BASE_TASK = {
    "order_id": "ORD-1047",
    "customer_id": "C-891",
    "expected_amount_minor_units": 18500,
    "currency": "EUR",
    "notification_required": True,
    "original_request": "Refund €185 for Order 1047 and notify the customer.",
}


async def main() -> None:
    scenario_mode = sys.argv[1] if len(sys.argv) > 1 else "FALSE_ACK"
    print(f"=== Testing app.agent_via_claude_sdk against scenario_mode={scenario_mode} ===\n")

    with httpx.Client(base_url=settings.simulator_base_url, timeout=10) as client:
        task_resp = client.post("/api/tasks", json={**BASE_TASK, "scenario_mode": scenario_mode})
        task_resp.raise_for_status()
        task = task_resp.json()
    print(f"Task created: {task['id']} (scenario_mode={scenario_mode})")

    db = SessionLocal()
    try:
        run = Run(task_id=task["id"], status=RunStatus.CREATED)
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()
    print(f"Run row created: {run_id}")

    expected_outcome = ExpectedOutcome(
        task_id=task["id"],
        order_id=task["order_id"],
        customer_id=task["customer_id"],
        expected_amount_minor_units=task["expected_amount_minor_units"],
        currency=task["currency"],
        notification_required=task["notification_required"],
    )

    print("\n--- Driving the REAL Claude Agent SDK (not app.agent's raw loop) ---")
    result = await run_agent_via_claude_sdk(
        expected_outcome, task["original_request"], run_id, scenario_mode
    )
    print(f"Agent SDK raw_claim: {result['raw_claim']!r}")

    with httpx.Client(base_url=settings.simulator_base_url, timeout=30) as client:
        claim_resp = client.post(f"/api/runs/{run_id}/claim", json={"raw_claim": result["raw_claim"]})
        claim_resp.raise_for_status()
        claim_body = claim_resp.json()
        print(f"\nNormalized claim_type: {claim_body['claim_type']!r}")

        verify_resp = client.post(f"/api/runs/{run_id}/verify")
        verify_resp.raise_for_status()
        verify_body = verify_resp.json()

    print(f"\n=== VERDICT: {verify_body['verdict']} ===")
    print(verify_body["verdict_explanation"])
    print("\nPredicate results:")
    for p in verify_body["predicate_results"] or []:
        mark = "PASS" if p["passed"] is True else ("FAIL" if p["passed"] is False else "????")
        print(f"  [{mark}] {p['field']}: expected={p['expected']!r} observed={p['observed']!r}")


if __name__ == "__main__":
    asyncio.run(main())
