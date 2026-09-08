from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapter import PaymentCustomerEvidenceAdapter
from app.agent import run_agent
from app.claim_normalizer import normalize_claim
from app.database import Base, engine, get_db
from app.models import Run, RunStatus, Task, Verdict
from app.proof import PROOF_DEFINITIONS_BY_CLAIM_TYPE
from app.schemas import (
    ExpectedOutcome,
    PredicateResult,
    RunClaimRequest,
    RunCreateRequest,
    RunResponse,
    TaskCreateRequest,
    TaskResponse,
)
from app.verdict_engine import evaluate

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AgentProof API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.simulator.actions import router as simulator_actions_router  # noqa: E402
from app.simulator.reads import router as simulator_reads_router  # noqa: E402

app.include_router(simulator_actions_router)
app.include_router(simulator_reads_router)


# --- helpers -------------------------------------------------------------


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        order_id=task.order_id,
        customer_id=task.customer_id,
        expected_amount_minor_units=task.expected_amount_minor_units,
        currency=task.currency,
        notification_required=task.notification_required,
        original_request=task.original_request,
        scenario_mode=task.scenario_mode,
        created_at=task.created_at,
    )


def _run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        task_id=run.task_id,
        status=run.status.value,
        agent_identity=run.agent_identity,
        agent_model=run.agent_model,
        created_at=run.created_at,
        raw_claim=run.raw_claim,
        claim_type=run.claim_type,
        normalized_claim=run.normalized_claim,
        normalization_error=run.normalization_error,
        proof_definition_id=run.proof_definition_id,
        proof_definition_version=run.proof_definition_version,
        systems_queried=run.systems_queried,
        credential_role_used=run.credential_role_used,
        raw_evidence=run.raw_evidence,
        normalized_evidence=run.normalized_evidence,
        predicate_results=run.predicate_results,
        verdict=run.verdict.value if run.verdict else None,
        verdict_explanation=run.verdict_explanation,
        verified_at=run.verified_at,
        task=_task_to_response(run.task),
    )


def _expected_outcome(task: Task) -> ExpectedOutcome:
    return ExpectedOutcome(
        task_id=task.id,
        order_id=task.order_id,
        customer_id=task.customer_id,
        expected_amount_minor_units=task.expected_amount_minor_units,
        currency=task.currency,
        notification_required=task.notification_required,
    )


# --- API surface -----------------------------------------------------------


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/proofs")
def list_proofs():
    return list(PROOF_DEFINITIONS_BY_CLAIM_TYPE.values())


@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreateRequest, db: Session = Depends(get_db)):
    task = Task(
        order_id=body.order_id,
        customer_id=body.customer_id,
        expected_amount_minor_units=body.expected_amount_minor_units,
        currency=body.currency,
        notification_required=body.notification_required,
        original_request=body.original_request,
        scenario_mode=body.scenario_mode,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_response(task)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown task_id {task_id!r}")
    return _task_to_response(task)


@app.post("/api/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(body: RunCreateRequest, db: Session = Depends(get_db)):
    """Create a run and drive the Claude agent to completion against the
    simulator's action endpoints. The agent receives the complete structured
    task object (ExpectedOutcome) directly — not asked to infer it from
    prose. Records the agent's raw free-text completion claim."""

    task = db.get(Task, body.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown task_id {body.task_id!r}")

    run = Run(task_id=task.id, agent_model=None)
    db.add(run)
    db.commit()
    db.refresh(run)

    expected_outcome = _expected_outcome(task)
    result = run_agent(expected_outcome, task.original_request, run.id, task.scenario_mode)

    run.raw_claim = result["raw_claim"]
    run.agent_transcript = result["transcript"]
    run.agent_model = run.agent_model or _agent_model_used()
    run.status = RunStatus.AGENT_EXECUTED
    db.commit()
    db.refresh(run)
    return _run_to_response(run)


def _agent_model_used() -> str:
    from app.config import settings

    return settings.claude_model


@app.post("/api/runs/{run_id}/claim", response_model=RunResponse)
def claim_run(run_id: str, body: RunClaimRequest, db: Session = Depends(get_db)):
    """Normalize the agent's raw claim into a structured, schema-validated
    record. If normalization fails, the run terminates as NOT_VERIFIABLE —
    the normalizer never guesses."""

    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown run_id {run_id!r}")

    raw_claim = body.raw_claim if body and body.raw_claim is not None else run.raw_claim
    if not raw_claim:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Run has no raw_claim to normalize.")

    run.raw_claim = raw_claim
    result = normalize_claim(raw_claim)

    if not result.ok:
        run.normalization_error = result.error
        run.verdict = Verdict.NOT_VERIFIABLE
        run.verdict_explanation = result.error
        run.verified_at = datetime.now(timezone.utc)
        run.status = RunStatus.CLAIMED
        db.commit()
        db.refresh(run)
        return _run_to_response(run)

    run.claim_type = result.claim.claim_type
    run.normalized_claim = result.claim.model_dump()
    run.normalization_error = None
    run.status = RunStatus.CLAIMED
    db.commit()
    db.refresh(run)
    return _run_to_response(run)


@app.post("/api/runs/{run_id}/verify", response_model=RunResponse)
async def verify_run(run_id: str, db: Session = Depends(get_db)):
    """Independently verify the run. Never reads the agent's tool-call
    results — always re-queries the system of record with AgentProof's
    read-only credential."""

    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown run_id {run_id!r}")

    if run.verdict is not None:
        return _run_to_response(run)  # already terminal (e.g. NOT_VERIFIABLE from claim step)

    if run.claim_type is None or run.normalized_claim is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Run has no normalized claim yet — call POST /api/runs/{id}/claim first.",
        )

    proof_definition = PROOF_DEFINITIONS_BY_CLAIM_TYPE.get(run.claim_type)
    if proof_definition is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No proof definition for claim_type {run.claim_type!r}")

    task = run.task
    expected_outcome = _expected_outcome(task)

    from app.schemas import RefundAndNotifyClaim

    claim = RefundAndNotifyClaim(**run.normalized_claim)

    adapter = PaymentCustomerEvidenceAdapter()
    collection = await adapter.collect_evidence(claim, expected_outcome, run.id, task.scenario_mode)

    verdict, predicate_results = evaluate(
        proof_definition, expected_outcome, collection.normalized(), collection.unreachable_fields()
    )

    run.proof_definition_id = proof_definition["proof_id"]
    run.proof_definition_version = proof_definition["proof_id"].split("_v")[-1]
    run.systems_queried = collection.systems_queried
    run.credential_role_used = collection.credential_role_used
    run.raw_evidence = collection.raw
    run.normalized_evidence = collection.normalized()
    run.predicate_results = [r.model_dump() for r in predicate_results]
    run.verdict = verdict
    run.verdict_explanation = _explain(verdict, predicate_results)
    run.verified_at = datetime.now(timezone.utc)
    run.status = RunStatus.VERIFIED
    db.commit()
    db.refresh(run)
    return _run_to_response(run)


def _explain(verdict: Verdict, results: list[PredicateResult]) -> str:
    failed = [r for r in results if r.passed is False]
    unreachable = [r for r in results if r.passed is None]
    if verdict == Verdict.VERIFIED:
        return "All required proof conditions were independently confirmed."
    if verdict == Verdict.CONTRADICTED:
        fields = ", ".join(r.field for r in failed)
        return f"Observed state contradicts the expected outcome and/or claim on: {fields}."
    if verdict == Verdict.INDETERMINATE:
        fields = ", ".join(r.field for r in unreachable)
        return f"Could not independently confirm: {fields} — evidence source unreachable."
    return "Claim could not be verified."


@app.get("/api/runs", response_model=list[RunResponse])
def list_runs(db: Session = Depends(get_db)):
    runs = db.execute(select(Run).order_by(Run.created_at.desc())).scalars().all()
    return [_run_to_response(r) for r in runs]


@app.get("/api/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown run_id {run_id!r}")
    return _run_to_response(run)
