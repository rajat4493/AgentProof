"""Simulator action (write) endpoints.

Only the agent's write credential is accepted here. These endpoints are the
only way business state (refunds, notifications) is mutated. AgentProof never
calls these endpoints and never holds the credential that would let it.

Each request carries a caller-supplied run_id (stamped by the agent's
tool-execution harness, never by the LLM — see app/agent.py) and a
scenario_mode used for deterministic failure injection (docs/MVP_SCOPE.md
§ Milestone 2). NORMAL persists genuinely. FALSE_ACK and DROP_NOTIFICATION
return an accepted-looking response without persisting anything — the agent
has no way to distinguish this from a real success, which is the point.

Every call also configures this run's simulator environment (SimulatorRunConfig)
so the read endpoints — which AgentProof's verifier calls and which never
accept a scenario_mode of their own — know whether they are "up" for this
run. Failure-mode configuration lives in the simulator/run environment, not
something the verifier supplies (see app/simulator/reads.py).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Message, Order, Refund, RefundStatus, SimulatorRunConfig
from app.scenario import DROP_NOTIFICATION, FALSE_ACK
from app.security import require_agent_write_credential
from app.simulator.schemas import (
    CreateRefundRequest,
    MessageOut,
    RefundOut,
    SendNotificationRequest,
)

router = APIRouter(prefix="/simulator/actions", tags=["simulator-actions"])


def _configure_run_environment(db: Session, run_id: str, scenario_mode: str) -> None:
    config = db.get(SimulatorRunConfig, run_id)
    if config is None:
        db.add(SimulatorRunConfig(run_id=run_id, scenario_mode=scenario_mode))
    else:
        config.scenario_mode = scenario_mode
    db.commit()


@router.post("/refunds")
def create_refund(
    body: CreateRefundRequest,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_agent_write_credential),
):
    order = db.get(Order, body.order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown order_id {body.order_id!r}")
    customer = db.get(Customer, body.customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown customer_id {body.customer_id!r}")

    _configure_run_environment(db, body.run_id, body.scenario_mode)

    if body.scenario_mode == FALSE_ACK:
        # Deliberately does NOT persist a Refund row. Returns an
        # accepted-looking response so the agent has no signal that
        # anything is wrong (spec §12 FALSE_ACK).
        return {"accepted": True, "operation_id": f"RF-{uuid.uuid4().hex[:8]}"}

    refund = Refund(
        order_id=body.order_id,
        customer_id=body.customer_id,
        run_id=body.run_id,
        amount_minor_units=body.amount_minor_units,
        currency=body.currency,
        status=RefundStatus.SUCCEEDED,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return RefundOut.model_validate(refund).model_dump()


@router.post("/notifications")
def send_notification(
    body: SendNotificationRequest,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_agent_write_credential),
):
    _configure_run_environment(db, body.run_id, body.scenario_mode)

    if body.scenario_mode == DROP_NOTIFICATION:
        # Deliberately does NOT persist a Message row (spec §12
        # DROP_NOTIFICATION). create_refund is unaffected by this mode.
        return {
            "accepted": True,
            "message_id": f"MSG-{uuid.uuid4().hex[:8]}",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

    message = Message(
        customer_id=body.customer_id,
        order_id=body.order_id,
        run_id=body.run_id,
        channel=body.channel,
        body=body.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageOut.model_validate(message).model_dump()
