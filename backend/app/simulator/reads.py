"""Simulator read (verification) endpoints.

Only AgentProof's read-only credential is accepted here. These are the
endpoints the evidence adapter queries to independently observe real state —
never the agent's own action-endpoint responses.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Message, Order, Refund
from app.security import require_verifier_read_credential
from app.simulator.schemas import CustomerOut, MessageOut, OrderOut, RefundOut

router = APIRouter(prefix="/simulator/read", tags=["simulator-reads"])


@router.get("/orders/{order_id}", response_model=OrderOut)
def read_order(
    order_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown order_id {order_id!r}")
    return order


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def read_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown customer_id {customer_id!r}")
    return customer


@router.get("/refunds", response_model=list[RefundOut])
def read_refunds(
    order_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    stmt = select(Refund).where(Refund.order_id == order_id, Refund.customer_id == customer_id)
    return list(db.execute(stmt).scalars().all())


@router.get("/messages", response_model=list[MessageOut])
def read_messages(
    order_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    stmt = select(Message).where(Message.order_id == order_id, Message.customer_id == customer_id)
    return list(db.execute(stmt).scalars().all())
