"""Simulator read (verification) endpoints.

Only AgentProof's read-only credential is accepted here. These are the
endpoints the evidence adapter queries to independently observe real state —
never the agent's own action-endpoint responses.

Reads are scoped to a specific run_id, not just order_id/customer_id — the
same order/customer can have more than one refund or message on record
(a repeated run, a retry, or a prior FALSE_ACK/NORMAL run), and evidence
must correlate to the specific run being verified rather than picking the
first match (see docs/PROOF_MODEL.md § Evidence).

These endpoints take NO scenario_mode of their own — AgentProof's verifier
always performs the same neutral read and only ever observes the resulting
system state or failure. Whether this run's read path is "up" is a property
of the simulator/run environment (SimulatorRunConfig, configured by the
write endpoints as they're called — see app/simulator/actions.py), looked
up here by run_id alone.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Message, Order, Refund, SimulatorRunConfig
from app.scenario import READ_UNAVAILABLE
from app.security import require_verifier_read_credential
from app.simulator.schemas import CustomerOut, MessageOut, OrderOut, RefundOut

router = APIRouter(prefix="/simulator/read", tags=["simulator-reads"])


def _check_run_environment_available(db: Session, run_id: str) -> None:
    config = db.get(SimulatorRunConfig, run_id)
    if config is not None and config.scenario_mode == READ_UNAVAILABLE:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "System of record unavailable.")


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
    run_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    _check_run_environment_available(db, run_id)
    stmt = select(Refund).where(
        Refund.order_id == order_id, Refund.customer_id == customer_id, Refund.run_id == run_id
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/messages", response_model=list[MessageOut])
def read_messages(
    order_id: str,
    customer_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    _credential: str = Depends(require_verifier_read_credential),
):
    _check_run_environment_available(db, run_id)
    stmt = select(Message).where(
        Message.order_id == order_id, Message.customer_id == customer_id, Message.run_id == run_id
    )
    return list(db.execute(stmt).scalars().all())
