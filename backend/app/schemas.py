"""Pydantic schemas.

Pydantic is the sole authoritative validation boundary for normalized claims
(per docs/PROOF_MODEL.md and docs/ARCHITECTURE.md § LLM boundary). Unknown or
extra fields, missing required fields, and unrecognized claim types must all
fail validation here.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.scenario import ScenarioMode


# --- Structured task / expected outcome --------------------------------------
# This is the single object both the agent and AgentProof receive. It is
# created before agent execution and never mutated afterward.


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    customer_id: str
    expected_amount_minor_units: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    notification_required: bool = True
    original_request: str
    # Demo/test control only (docs/MVP_SCOPE.md § Milestone 2) — deliberately
    # NOT part of ExpectedOutcome below, which stays the pure business-outcome
    # contract and is never touched by test-mode concerns.
    scenario_mode: ScenarioMode = "NORMAL"


class ExpectedOutcome(BaseModel):
    """The immutable structured expected outcome derived from a task.

    Both the Claude agent and AgentProof's verifier receive this same object
    independently. AgentProof always verifies against these values — never
    against values extracted from the agent's own claim.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str
    order_id: str
    customer_id: str
    expected_amount_minor_units: int
    currency: str
    notification_required: bool


class TaskResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    expected_amount_minor_units: int
    currency: str
    notification_required: bool
    original_request: str
    scenario_mode: str
    created_at: datetime


# --- Claim normalization ------------------------------------------------------
# claim_type is selected by the LLM from this fixed set. Each claim type has
# its own strict schema. The LLM may only populate fields declared here — it
# may never invent predicates or influence the verdict.

KNOWN_CLAIM_TYPES = ("refund_and_notify",)


class RefundAndNotifyClaim(BaseModel):
    """Normalized claim schema for claim_type = refund_and_notify.

    Fields here are for display/audit only. The verdict engine never compares
    against amount_claimed/currency_claimed — it always compares observed
    evidence against the original ExpectedOutcome (task.*).
    """

    model_config = ConfigDict(extra="forbid")

    claim_type: Literal["refund_and_notify"]
    order_id: str
    customer_id: str
    amount_claimed_minor_units: int
    currency_claimed: str
    refund_claimed: bool
    notification_claimed: bool


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str


class RunClaimRequest(BaseModel):
    """Optional override for supplying a claim directly (e.g. for tests).

    In the normal flow, POST /api/runs already drives the agent and records
    its claim; POST /api/runs/:id/claim re-normalizes the recorded raw claim.
    """

    model_config = ConfigDict(extra="forbid")

    raw_claim: str | None = None


class PredicateResult(BaseModel):
    field: str
    operator: str
    expected: object | None = None
    observed: object | None = None
    passed: bool | None = None  # None when INDETERMINATE (could not be evaluated)
    reason: str | None = None


class RunResponse(BaseModel):
    id: str
    task_id: str
    status: str
    agent_identity: str
    agent_model: str | None
    created_at: datetime
    raw_claim: str | None
    claim_type: str | None
    normalized_claim: dict | None
    normalization_error: str | None
    proof_definition_id: str | None
    proof_definition_version: str | None
    systems_queried: list | None
    credential_role_used: str | None
    raw_evidence: dict | None
    normalized_evidence: dict | None
    predicate_results: list | None
    verdict: str | None
    verdict_explanation: str | None
    verified_at: datetime | None

    # Always shown alongside the verdict — never a bare VERIFIED/CONTRADICTED.
    task: TaskResponse
