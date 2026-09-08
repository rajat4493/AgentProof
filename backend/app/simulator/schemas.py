from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.scenario import ScenarioMode


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    amount_minor_units: int
    currency: str


class CreateRefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str
    customer_id: str
    amount_minor_units: int
    currency: str
    # Caller-supplied correlation string (stamped by the agent's tool-call
    # harness, never by the LLM) and demo/test failure-injection mode. Both
    # are opaque to this simulator beyond deciding whether to persist.
    run_id: str
    scenario_mode: ScenarioMode = "NORMAL"


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    order_id: str
    customer_id: str
    run_id: str
    amount_minor_units: int
    currency: str
    status: str
    created_at: datetime


class SendNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str
    order_id: str
    channel: str = "email"
    body: str
    run_id: str
    scenario_mode: ScenarioMode = "NORMAL"


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    order_id: str
    run_id: str
    channel: str
    body: str
    created_at: datetime
