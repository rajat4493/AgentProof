import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Verdict(str, enum.Enum):
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INDETERMINATE = "INDETERMINATE"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"


class RunStatus(str, enum.Enum):
    CREATED = "created"
    AGENT_EXECUTED = "agent_executed"
    CLAIMED = "claimed"
    VERIFIED = "verified"


# --- Simulator: system of record (payment / customer domain) -----------------


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"RF-{uuid.uuid4().hex[:8]}")
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    # Plain string reference supplied by the caller — not a foreign key into
    # AgentProof's own `runs` table. The simulator is a separate system of
    # record and only knows an opaque correlation string, the same way a
    # real payment processor would (docs/PROOF_MODEL.md).
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[RefundStatus] = mapped_column(Enum(RefundStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"MSG-{uuid.uuid4().hex[:8]}")
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False, default="email")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SimulatorRunConfig(Base):
    """A property of the simulator/run environment, not of any single
    request — deliberately NOT something AgentProof's verifier supplies on
    its read calls. Written by the simulator's own write (action) endpoints
    as they're called (the same way a real chaos-engineering fault injector
    would be configured against a target environment ahead of/alongside
    real traffic, not told what to fake by the client doing the observing).
    Read endpoints consult this by run_id alone to decide whether they are
    "up" for this run — AgentProof always performs the same neutral read
    and only ever observes the resulting system state or failure."""

    __tablename__ = "simulator_run_config"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    scenario_mode: Mapped[str] = mapped_column(String, nullable=False, default="NORMAL")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


# --- AgentProof: task / run / evidence trail ----------------------------------


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"TASK-{uuid.uuid4().hex[:8]}")
    order_id: Mapped[str] = mapped_column(String, nullable=False)
    customer_id: Mapped[str] = mapped_column(String, nullable=False)
    expected_amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notification_required: Mapped[bool] = mapped_column(nullable=False, default=True)
    original_request: Mapped[str] = mapped_column(Text, nullable=False)
    # Demo/test control only — never part of ExpectedOutcome, never seen by
    # the LLM. Drives deterministic failure injection in the simulator
    # (docs/MVP_SCOPE.md § Milestone 2).
    scenario_mode: Mapped[str] = mapped_column(String, nullable=False, default="NORMAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    runs: Mapped[list["Run"]] = relationship(back_populates="task")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"RUN-{uuid.uuid4().hex[:8]}")
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), nullable=False, default=RunStatus.CREATED)

    agent_identity: Mapped[str] = mapped_column(String, nullable=False, default="refund-support-agent")
    agent_model: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Agent execution + claim
    agent_transcript: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_claim: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Normalization
    claim_type: Mapped[str | None] = mapped_column(String, nullable=True)
    normalized_claim: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    normalization_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification
    proof_definition_id: Mapped[str | None] = mapped_column(String, nullable=True)
    proof_definition_version: Mapped[str | None] = mapped_column(String, nullable=True)
    systems_queried: Mapped[list | None] = mapped_column(JSON, nullable=True)
    credential_role_used: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    normalized_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    predicate_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    verdict: Mapped[Verdict | None] = mapped_column(Enum(Verdict), nullable=True)
    verdict_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[Task] = relationship(back_populates="runs")
