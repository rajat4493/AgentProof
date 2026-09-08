"""Simulator action (write) endpoints.

Only the agent's write credential is accepted here. These endpoints are the
only way business state (refunds, notifications) is mutated. AgentProof never
calls these endpoints and never holds the credential that would let it.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Message, Order, Refund, RefundStatus
from app.security import require_agent_write_credential
from app.simulator.schemas import (
    CreateRefundRequest,
    MessageOut,
    RefundOut,
    SendNotificationRequest,
)

router = APIRouter(prefix="/simulator/actions", tags=["simulator-actions"])


@router.post("/refunds", response_model=RefundOut)
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

    refund = Refund(
        order_id=body.order_id,
        customer_id=body.customer_id,
        amount_minor_units=body.amount_minor_units,
        currency=body.currency,
        status=RefundStatus.SUCCEEDED,
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund


@router.post("/notifications", response_model=MessageOut)
def send_notification(
    body: SendNotificationRequest,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_agent_write_credential),
):
    message = Message(
        customer_id=body.customer_id,
        order_id=body.order_id,
        channel=body.channel,
        body=body.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
