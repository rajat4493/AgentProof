"""Unit tests for the Milestone 3 extracted primitives: the claim-schema
registry, the typed ProofDefinition/ProofCheck, and the evidence adapter
registry. These primitives should be pure structure — no new behavior —
so these tests check the registries are internally consistent and that the
invariants they encode (e.g. exactly one of expected/source) actually hold,
not new business logic."""

import pytest
from pydantic import ValidationError

from app.adapter import ADAPTER_REGISTRY, EvidenceAdapter, PaymentCustomerEvidenceAdapter
from app.claims import CLAIM_SCHEMAS, KNOWN_CLAIM_TYPES
from app.proof import PROOF_DEFINITIONS_BY_CLAIM_TYPE, ProofCheck, REFUND_COMPLETED_V1


def test_claim_schema_registry_matches_known_claim_types():
    assert set(CLAIM_SCHEMAS.keys()) == set(KNOWN_CLAIM_TYPES)
    assert "refund_and_notify" in CLAIM_SCHEMAS


def test_proof_definition_registry_keyed_by_its_own_claim_type():
    assert PROOF_DEFINITIONS_BY_CLAIM_TYPE["refund_and_notify"] is REFUND_COMPLETED_V1
    assert REFUND_COMPLETED_V1.proof_id == "refund_completed_v1"
    assert len(REFUND_COMPLETED_V1.required_checks) == 9


def test_every_registered_claim_type_has_a_proof_definition_and_adapter():
    """The three Milestone 3 registries (claims, proofs, adapters) must stay
    in lockstep — every claim type the normalizer can produce must have
    somewhere to be verified."""
    for claim_type in CLAIM_SCHEMAS:
        assert claim_type in PROOF_DEFINITIONS_BY_CLAIM_TYPE, f"no proof definition for {claim_type!r}"
        assert claim_type in ADAPTER_REGISTRY, f"no adapter for {claim_type!r}"


def test_adapter_registry_holds_the_real_adapter_not_a_stub():
    adapter = ADAPTER_REGISTRY["refund_and_notify"]
    assert isinstance(adapter, PaymentCustomerEvidenceAdapter)
    assert adapter.id == "payment_customer_simulator_v1"


def test_proof_check_rejects_both_expected_and_source():
    with pytest.raises(ValidationError):
        ProofCheck(field="x", expected=True, source="order_id")


def test_proof_check_rejects_neither_expected_nor_source():
    with pytest.raises(ValidationError):
        ProofCheck(field="x")


def test_proof_check_accepts_exactly_one():
    assert ProofCheck(field="x", expected=True).expected is True
    assert ProofCheck(field="y", source="order_id").source == "order_id"


def test_get_proofs_endpoint_serializes_typed_proof_definitions(client):
    resp = client.get("/api/proofs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["proof_id"] == "refund_completed_v1"
    assert body[0]["claim_type"] == "refund_and_notify"
    assert len(body[0]["required_checks"]) == 9
    assert body[0]["required_checks"][0]["field"] == "refund_exists"
