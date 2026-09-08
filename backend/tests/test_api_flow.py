"""Integration tests against the real FastAPI app + real Postgres + real
simulator HTTP endpoints. Only the two Claude-calling functions are faked
(via monkeypatch), so these run offline and deterministically."""

import httpx
import pytest

from app.config import settings
from tests.fakes import fixed_normalizer_caller

BASE_TASK = {
    "order_id": "ORD-1047",
    "customer_id": "C-891",
    "expected_amount_minor_units": 18500,
    "currency": "EUR",
    "notification_required": True,
    "original_request": "Refund €185 for Order 1047 and notify the customer.",
}


def _create_task(client, **overrides):
    resp = client.post("/api/tasks", json={**BASE_TASK, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_run_row(task_id: str, raw_claim: str) -> str:
    """Create a run without invoking the live agent (that path is covered by
    test_agent_runner.py + the live smoke test) — write a Run row via the DB
    session the way POST /api/runs would, but with a pre-set raw_claim so
    /claim can be exercised without a live Claude call."""
    from app.database import SessionLocal
    from app.models import Run, RunStatus

    db = SessionLocal()
    try:
        run = Run(task_id=task_id, raw_claim=raw_claim, status=RunStatus.AGENT_EXECUTED)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def _claim_output(amount=18500, currency="EUR", refund_claimed=True, notification_claimed=True):
    return {
        "claim_type": "refund_and_notify",
        "order_id": "ORD-1047",
        "customer_id": "C-891",
        "amount_claimed_minor_units": amount,
        "currency_claimed": currency,
        "refund_claimed": refund_claimed,
        "notification_claimed": notification_claimed,
    }


VALID_NORMALIZER_OUTPUT = _claim_output()


def _headers(role: str):
    cred = settings.agent_write_credential if role == "agent" else settings.verifier_read_credential
    return {"X-AgentProof-Credential": cred}


def _write_refund(run_id, order_id="ORD-1047", customer_id="C-891", amount=18500, currency="EUR", scenario_mode="NORMAL"):
    with httpx.Client(base_url=settings.simulator_base_url, timeout=10) as h:
        resp = h.post(
            "/simulator/actions/refunds",
            json={
                "order_id": order_id,
                "customer_id": customer_id,
                "amount_minor_units": amount,
                "currency": currency,
                "run_id": run_id,
                "scenario_mode": scenario_mode,
            },
            headers=_headers("agent"),
        )
        resp.raise_for_status()
        return resp.json()


def _write_notification(run_id, order_id="ORD-1047", customer_id="C-891", scenario_mode="NORMAL"):
    with httpx.Client(base_url=settings.simulator_base_url, timeout=10) as h:
        resp = h.post(
            "/simulator/actions/notifications",
            json={
                "customer_id": customer_id,
                "order_id": order_id,
                "body": "Your refund is complete.",
                "run_id": run_id,
                "scenario_mode": scenario_mode,
            },
            headers=_headers("agent"),
        )
        resp.raise_for_status()
        return resp.json()


def _create_real_refund_and_notification(run_id, **kwargs):
    _write_refund(run_id, **kwargs)
    _write_notification(run_id, **{k: v for k, v in kwargs.items() if k in ("order_id", "customer_id")})


def _patch_normalizer(monkeypatch, output: dict):
    monkeypatch.setattr(
        "app.main.normalize_claim",
        lambda raw_claim: __import__("app.claim_normalizer", fromlist=["normalize_claim"]).normalize_claim(
            raw_claim, fixed_normalizer_caller(output)
        ),
    )


# --- Test 1: genuine success -> VERIFIED -------------------------------------


def test_genuine_success_is_verified(client, monkeypatch):
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "Refund completed successfully and the customer has been notified.")
    _create_real_refund_and_notification(run_id)

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)

    claim_resp = client.post(f"/api/runs/{run_id}/claim", json={})
    assert claim_resp.status_code == 200, claim_resp.text
    assert claim_resp.json()["claim_type"] == "refund_and_notify"

    verify_resp = client.post(f"/api/runs/{run_id}/verify")
    assert verify_resp.status_code == 200, verify_resp.text
    body = verify_resp.json()
    assert body["verdict"] == "VERIFIED"
    assert all(p["passed"] is True for p in body["predicate_results"])
    # Full evidence trail, never a bare verdict.
    assert body["raw_evidence"] is not None
    assert body["normalized_evidence"] is not None
    assert body["systems_queried"] == ["payment_customer_system"]
    assert body["credential_role_used"] == "verifier_read"
    assert body["proof_definition_id"] == "refund_completed_v1"


# --- Test 2: false completion -> CONTRADICTED (independence) ----------------


def test_false_completion_is_contradicted(client, monkeypatch):
    """Agent claims success in text but the refund was never actually
    created. AgentProof must not trust the claim — it independently queries
    the simulator and finds nothing."""
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "Refund completed successfully and the customer has been notified.")
    # Deliberately do NOT create the refund/notification.

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)

    client.post(f"/api/runs/{run_id}/claim", json={})
    verify_resp = client.post(f"/api/runs/{run_id}/verify")
    body = verify_resp.json()
    assert body["verdict"] == "CONTRADICTED"
    refund_exists_check = next(p for p in body["predicate_results"] if p["field"] == "refund_exists")
    assert refund_exists_check["passed"] is False
    assert refund_exists_check["observed"] is False
    assert refund_exists_check["expected"] is True


# --- Test 3: incomplete business outcome -> CONTRADICTED, notification named --


def test_missing_notification_is_contradicted_with_exact_predicate(client, monkeypatch):
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "Refund completed successfully and the customer has been notified.")
    _write_refund(run_id)
    # No notification sent.

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)

    client.post(f"/api/runs/{run_id}/claim", json={})
    verify_resp = client.post(f"/api/runs/{run_id}/verify")
    body = verify_resp.json()
    assert body["verdict"] == "CONTRADICTED"
    failed_fields = {p["field"] for p in body["predicate_results"] if p["passed"] is False}
    assert "notification.exists" in failed_fields
    refund_checks = [p for p in body["predicate_results"] if p["field"].startswith("refund")]
    assert all(p["passed"] is True for p in refund_checks)


# --- Test 5: unknown/unmappable claim -> NOT_VERIFIABLE ----------------------


def test_unmappable_claim_is_not_verifiable(client, monkeypatch):
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "The weather in Paris is lovely today.")

    unmappable_output = {
        "claim_type": "not_mappable",
        "order_id": None,
        "customer_id": None,
        "amount_claimed_minor_units": None,
        "currency_claimed": None,
        "refund_claimed": None,
        "notification_claimed": None,
    }
    _patch_normalizer(monkeypatch, unmappable_output)

    claim_resp = client.post(f"/api/runs/{run_id}/claim", json={})
    body = claim_resp.json()
    assert body["verdict"] == "NOT_VERIFIABLE"
    assert body["claim_type"] is None
    # The verdict engine must never have run.
    assert body["predicate_results"] is None

    # /verify on an already-terminal run is a no-op, not a re-evaluation.
    verify_resp = client.post(f"/api/runs/{run_id}/verify")
    assert verify_resp.json()["verdict"] == "NOT_VERIFIABLE"


def test_normalizer_missing_required_field_is_not_verifiable(client, monkeypatch):
    """Pydantic is the authoritative boundary: even if the LLM selects the
    right claim_type, a missing required field must still fail closed."""
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "Refund done.")

    incomplete_output = {
        "claim_type": "refund_and_notify",
        "order_id": "ORD-1047",
        "customer_id": "C-891",
        "amount_claimed_minor_units": None,  # missing
        "currency_claimed": "EUR",
        "refund_claimed": True,
        "notification_claimed": None,  # missing
    }
    _patch_normalizer(monkeypatch, incomplete_output)

    claim_resp = client.post(f"/api/runs/{run_id}/claim", json={})
    body = claim_resp.json()
    assert body["verdict"] == "NOT_VERIFIABLE"
    assert body["normalization_error"] is not None


# --- Credential separation ---------------------------------------------------


def test_agent_credential_rejected_on_read_endpoint(client):
    resp = httpx.get(
        f"{settings.simulator_base_url}/simulator/read/refunds",
        params={"order_id": "ORD-1047", "customer_id": "C-891", "run_id": "irrelevant"},
        headers=_headers("agent"),
    )
    assert resp.status_code == 403


def test_verifier_credential_rejected_on_write_endpoint(client):
    resp = httpx.post(
        f"{settings.simulator_base_url}/simulator/actions/refunds",
        json={"order_id": "ORD-1047", "customer_id": "C-891", "amount_minor_units": 100, "currency": "EUR", "run_id": "irrelevant"},
        headers=_headers("verifier"),
    )
    assert resp.status_code == 403


# --- Evidence persistence: full trail, never a bare verdict -----------------


def test_get_run_returns_full_evidence_trail(client, monkeypatch):
    task = _create_task(client)
    run_id = _create_run_row(task["id"], "Refund completed and customer notified.")
    _create_real_refund_and_notification(run_id)

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)
    client.post(f"/api/runs/{run_id}/claim", json={})
    client.post(f"/api/runs/{run_id}/verify")

    resp = client.get(f"/api/runs/{run_id}")
    body = resp.json()
    for field in (
        "id",
        "task_id",
        "agent_identity",
        "created_at",
        "raw_claim",
        "normalized_claim",
        "proof_definition_id",
        "proof_definition_version",
        "systems_queried",
        "credential_role_used",
        "raw_evidence",
        "normalized_evidence",
        "predicate_results",
        "verdict",
        "verified_at",
        "task",
    ):
        assert body[field] is not None, f"missing evidence field: {field}"
    assert body["task"]["order_id"] == "ORD-1047"


# --- Repeated-run / multiple-refund correlation (flagged in review) ---------


def test_repeated_run_evidence_is_correlated_to_this_run_not_first_match(client, monkeypatch):
    """Two runs against the same task/order/customer. Run A's refund is for
    the wrong amount (simulating some earlier bad run); Run B's refund is
    correct. Each run's verdict must reflect only its own evidence — Run B
    must not be contaminated by Run A's refund merely because both match on
    (order_id, customer_id), and Run A must not be masked by Run B's later,
    correct refund."""
    task = _create_task(client)

    run_a = _create_run_row(task["id"], "Refund completed and customer notified.")
    _write_refund(run_a, amount=9900)  # wrong amount — this run's own anomaly
    _write_notification(run_a)

    run_b = _create_run_row(task["id"], "Refund completed and customer notified.")
    _write_refund(run_b, amount=18500)  # correct
    _write_notification(run_b)

    _patch_normalizer(monkeypatch, _claim_output(amount=9900))
    client.post(f"/api/runs/{run_a}/claim", json={})
    verify_a = client.post(f"/api/runs/{run_a}/verify").json()
    assert verify_a["verdict"] == "CONTRADICTED"
    amount_check_a = next(p for p in verify_a["predicate_results"] if p["field"] == "refund.amount_minor_units")
    assert amount_check_a["passed"] is False
    assert amount_check_a["observed"] == 9900  # Run A's own refund, not Run B's
    assert amount_check_a["expected"] == 18500  # still the task's true expected amount, not the claim

    _patch_normalizer(monkeypatch, _claim_output(amount=18500))
    client.post(f"/api/runs/{run_b}/claim", json={})
    verify_b = client.post(f"/api/runs/{run_b}/verify").json()
    assert verify_b["verdict"] == "VERIFIED"
    amount_check_b = next(p for p in verify_b["predicate_results"] if p["field"] == "refund.amount_minor_units")
    assert amount_check_b["observed"] == 18500  # Run B's own refund, not Run A's wrong one


# --- Milestone 2: deterministic failure injection ----------------------------


def test_scenario_normal_is_verified(client, monkeypatch):
    task = _create_task(client, scenario_mode="NORMAL")
    run_id = _create_run_row(task["id"], "Refund completed and customer notified.")
    _write_refund(run_id, scenario_mode="NORMAL")
    _write_notification(run_id, scenario_mode="NORMAL")

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)
    client.post(f"/api/runs/{run_id}/claim", json={})
    body = client.post(f"/api/runs/{run_id}/verify").json()
    assert body["verdict"] == "VERIFIED"


def test_scenario_false_ack_is_contradicted(client, monkeypatch):
    """create_refund returns an accepted-looking response but persists
    nothing. The agent has no way to tell — only AgentProof's independent
    read catches it."""
    task = _create_task(client, scenario_mode="FALSE_ACK")
    run_id = _create_run_row(task["id"], "Refund completed and customer notified.")

    fake_ack = _write_refund(run_id, scenario_mode="FALSE_ACK")
    assert fake_ack.get("accepted") is True
    assert "operation_id" in fake_ack
    _write_notification(run_id, scenario_mode="FALSE_ACK")

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)
    client.post(f"/api/runs/{run_id}/claim", json={})
    body = client.post(f"/api/runs/{run_id}/verify").json()
    assert body["verdict"] == "CONTRADICTED"
    refund_exists = next(p for p in body["predicate_results"] if p["field"] == "refund_exists")
    assert refund_exists["passed"] is False
    assert refund_exists["observed"] is False


def test_scenario_drop_notification_is_contradicted(client, monkeypatch):
    """Refund persists genuinely; send_notification silently no-ops while
    returning a success-looking response."""
    task = _create_task(client, scenario_mode="DROP_NOTIFICATION")
    run_id = _create_run_row(task["id"], "Refund completed and customer notified.")

    _write_refund(run_id, scenario_mode="DROP_NOTIFICATION")
    fake_ack = _write_notification(run_id, scenario_mode="DROP_NOTIFICATION")
    assert fake_ack.get("accepted") is True

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)
    client.post(f"/api/runs/{run_id}/claim", json={})
    body = client.post(f"/api/runs/{run_id}/verify").json()
    assert body["verdict"] == "CONTRADICTED"
    failed = {p["field"] for p in body["predicate_results"] if p["passed"] is False}
    # Notification is fully absent, so its correlation checks fail too, not
    # just notification.exists — that's correct given the proof definition
    # (docs/PROOF_MODEL.md), not a bug. Refund checks must be unaffected.
    assert "notification.exists" in failed
    assert failed <= {"notification.exists", "notification.customer_id", "notification.order_id"}
    refund_checks = [p for p in body["predicate_results"] if p["field"].startswith("refund")]
    assert all(p["passed"] is True for p in refund_checks)


def test_scenario_read_unavailable_is_indeterminate(client, monkeypatch):
    """The refund and notification genuinely succeed — AgentProof's
    independent read path is simply unreachable. Must never silently return
    VERIFIED."""
    task = _create_task(client, scenario_mode="READ_UNAVAILABLE")
    run_id = _create_run_row(task["id"], "Refund completed and customer notified.")

    # Writes are unaffected by READ_UNAVAILABLE — they genuinely succeed.
    _write_refund(run_id, scenario_mode="READ_UNAVAILABLE")
    _write_notification(run_id, scenario_mode="READ_UNAVAILABLE")

    # Confirm the data really is there before we prove it's unreadable.
    real_check = httpx.get(
        f"{settings.simulator_base_url}/simulator/read/refunds",
        params={"order_id": "ORD-1047", "customer_id": "C-891", "run_id": run_id, "scenario_mode": "NORMAL"},
        headers=_headers("verifier"),
    )
    assert len(real_check.json()) == 1

    _patch_normalizer(monkeypatch, VALID_NORMALIZER_OUTPUT)
    client.post(f"/api/runs/{run_id}/claim", json={})
    body = client.post(f"/api/runs/{run_id}/verify").json()
    assert body["verdict"] == "INDETERMINATE"
    assert all(p["passed"] is not False for p in body["predicate_results"])  # never a false failure
    unreachable = {p["field"] for p in body["predicate_results"] if p["passed"] is None}
    assert "refund_exists" in unreachable
    assert "notification.exists" in unreachable
