# Duck — milestone-3

## Intent

Extract only the generic primitives that Milestones 1–2's working refund implementation already
proved out — claim model, proof definition, evidence adapter interface, verdict engine — as
named, reusable shapes, per `docs/MVP_SCOPE.md` § Milestone 3. No new capability, no second
scenario. This is the last milestone of V0.

## Scope

As approved in `duck/milestone-3-plan.md`, delivered in full:

1. **Claim model** — `app/claims.py`'s `CLAIM_SCHEMAS: dict[str, type[BaseModel]]` (still one
   entry, `refund_and_notify -> RefundAndNotifyClaim`). `app/claim_normalizer.py`'s
   `normalize_claim()` now does `schema = CLAIM_SCHEMAS.get(claim_type)` instead of hardcoding
   `RefundAndNotifyClaim`; `app/main.py`'s `verify_run()` does the same
   (`CLAIM_SCHEMAS.get(run.claim_type)`) instead of importing the concrete model directly.
   `KNOWN_CLAIM_TYPES` is now derived from the registry (`tuple(CLAIM_SCHEMAS.keys())`) rather
   than a separately hardcoded tuple, removing a place the two could drift.
2. **Proof definition** — `app/proof.py`'s `ProofCheck`/`ProofDefinition` are now typed Pydantic
   models (`extra="forbid"`) instead of a raw dict literal. `ProofCheck` has a model validator
   enforcing the invariant the code already implicitly relied on: exactly one of `expected`/
   `source` is set, never both, never neither. `REFUND_COMPLETED_V1` is now a `ProofDefinition`
   instance built from `ProofCheck(...)` calls, same 9 checks, same field names, same semantics.
   `GET /api/proofs` needed no code change — FastAPI serializes the Pydantic models the same way
   it serialized the dicts.
3. **Evidence adapter interface** — the `EvidenceAdapter` Protocol already existed from
   Milestone 1 and is unchanged in shape (its `claim` parameter is now typed `BaseModel`
   generically rather than the one concrete claim model, matching the spec's own illustrative
   `AgentClaim` placeholder name). What was missing: `app/main.py`'s `verify_run()` hardcoded
   `PaymentCustomerEvidenceAdapter()` directly. Extracted `app/adapter.py`'s
   `ADAPTER_REGISTRY: dict[str, EvidenceAdapter]` (still one entry) so `verify_run()` does
   `ADAPTER_REGISTRY.get(run.claim_type)` instead.
4. **Verdict engine** — confirmed `app/verdict_engine.py`'s `evaluate()` already contained no
   refund-specific logic (it only ever did proof-definition-driven equality checks against an
   `ExpectedOutcome`); updated its signature to take the newly-typed `ProofDefinition` and to
   read `check.field`/`check.operator`/`check.expected`/`check.source` as attributes instead of
   dict keys. No change to verdict semantics.

All three claim_type-keyed registries (`CLAIM_SCHEMAS`, `PROOF_DEFINITIONS_BY_CLAIM_TYPE`,
`ADAPTER_REGISTRY`) are asserted to stay in lockstep by `tests/test_primitives.py` — every
registered claim type must resolve to a proof definition and an adapter.

Not built (per the plan, correctly out of scope): a second scenario/claim type/adapter to prove
the registries "really" generalize, a config-driven or file-based proof-definition loader,
dynamic adapter discovery or plugin loading, any change to the API surface or verdict semantics.

## Assumptions

Both held:

- "Extraction" meant introducing types/registries around existing logic, not rewriting behavior.
  Confirmed — every pre-existing test (15 from Milestones 1–2) passes with **zero changes**, not
  even an import-path update: no existing test file imports `app.proof`, `app.claim_normalizer`'s
  internals, or `app.adapter`'s concrete class directly, so the refactor was fully invisible to
  them.
- No database migration needed — confirmed, this milestone touched no SQLAlchemy model.
- One live smoke test (not all four scenarios) is sufficient regression evidence, since this
  milestone changes no runtime behavior — confirmed by a live VERIFIED run plus a direct
  `GET /api/proofs` check that the typed models serialize correctly.

## Tests Run

**Automated — the full pre-existing suite (15 tests) plus 8 new tests targeting the extracted
primitives themselves (23 total):**

```
$ python -m pytest -v
tests/test_agent_runner.py::test_agent_calls_refund_and_notification_then_claims_completion PASSED
tests/test_agent_runner.py::test_agent_receives_structured_task_not_asked_to_infer_from_prose PASSED
tests/test_api_flow.py::test_genuine_success_is_verified PASSED
tests/test_api_flow.py::test_false_completion_is_contradicted PASSED
tests/test_api_flow.py::test_missing_notification_is_contradicted_with_exact_predicate PASSED
tests/test_api_flow.py::test_unmappable_claim_is_not_verifiable PASSED
tests/test_api_flow.py::test_normalizer_missing_required_field_is_not_verifiable PASSED
tests/test_api_flow.py::test_agent_credential_rejected_on_read_endpoint PASSED
tests/test_api_flow.py::test_verifier_credential_rejected_on_write_endpoint PASSED
tests/test_api_flow.py::test_get_run_returns_full_evidence_trail PASSED
tests/test_api_flow.py::test_repeated_run_evidence_is_correlated_to_this_run_not_first_match PASSED
tests/test_api_flow.py::test_scenario_normal_is_verified PASSED
tests/test_api_flow.py::test_scenario_false_ack_is_contradicted PASSED
tests/test_api_flow.py::test_scenario_drop_notification_is_contradicted PASSED
tests/test_api_flow.py::test_scenario_read_unavailable_is_indeterminate PASSED
tests/test_primitives.py::test_claim_schema_registry_matches_known_claim_types PASSED
tests/test_primitives.py::test_proof_definition_registry_keyed_by_its_own_claim_type PASSED
tests/test_primitives.py::test_every_registered_claim_type_has_a_proof_definition_and_adapter PASSED
tests/test_primitives.py::test_adapter_registry_holds_the_real_adapter_not_a_stub PASSED
tests/test_primitives.py::test_proof_check_rejects_both_expected_and_source PASSED
tests/test_primitives.py::test_proof_check_rejects_neither_expected_nor_source PASSED
tests/test_primitives.py::test_proof_check_accepts_exactly_one PASSED
tests/test_primitives.py::test_get_proofs_endpoint_serializes_typed_proof_definitions PASSED

23 passed in 3.82s
```

**Frontend build:** clean (`npm run build`) — untouched by this milestone, confirmed regardless
since API response shapes must not change.

**Live end-to-end, real Claude API (`claude-opus-5`):** created a task, ran the real agent, real
normalization, and real verification through the refactored registries — claim:
*"I refunded €185.00 (18500 EUR minor units) on Order ORD-1047 for customer C-891 and emailed them
a confirmation."* All 9 checks passed → **VERIFIED**, identical shape and content to Milestone
1/2's live runs. `GET /api/proofs` confirmed to serialize the now-typed `ProofDefinition`/
`ProofCheck` models correctly (`proof_id`, `claim_type`, `required_checks[].field/operator/
expected/source` all present and correctly `null`-vs-set). Confirmed in the browser UI via
screenshot — run detail page renders identically to Milestones 1–2, no visual or functional
regression.

## Verified

- All three claim_type-keyed registries exist, are internally consistent, and stay in lockstep
  (enforced by a dedicated test, not just eyeballed).
- `ProofCheck`'s exactly-one-of-expected-or-source invariant is now enforced by Pydantic, not
  just an implicit convention in the JSON literal it replaced.
- `app/main.py` no longer imports or hardcodes any concrete claim model or adapter class in
  `verify_run()` — it resolves both via the `claim_type`-keyed registries, the same shape as it
  already resolved the proof definition.
- Zero observable behavior change: same verdicts, same evidence trail shape, same API responses,
  same UI — confirmed by the unmodified pre-existing test suite and a live run.
- The verdict engine contains no refund-specific logic — confirmed by inspection (it was already
  true from Milestone 1; this milestone only formalized its input type).

## Unverified

- Whether the registries genuinely make adding a second claim type painless — not exercised,
  since building a second scenario is explicitly out of scope for V0 (`docs/MVP_SCOPE.md`
  reserves that for Milestone 4+, not authorized here). The registries are shaped to make that
  addition require no change to `claim_normalizer.py`/`verdict_engine.py`/`main.py`'s
  `verify_run()` logic, but this is a design claim substantiated by the current single-entry
  case, not by a second entry actually having been added.

## Failures

None. This milestone was a pure refactor with a pre-existing regression suite to check it
against; no test needed correction, no behavior needed fixing.

## Scope Drift

None. Reviewed against the plan and the spec's "do not build" list before closing: no second
scenario/claim type, no config-driven or file-based proof-definition loader, no dynamic adapter
discovery/plugin system, no visual builder, no API surface change. The `pydantic.BaseModel`
import added to `app/adapter.py`'s `EvidenceAdapter.collect_evidence` type hint is the only
"new" typing surface, and it exists solely to type the parameter generically instead of to one
concrete model — not new capability.

## V0 status

**V0 is complete.** `docs/MVP_SCOPE.md`: "V0 contains only Milestones 1–3. Do not proceed beyond
V0 without explicit human approval." All three milestones are implemented, tested (offline and
live against the real Claude API), and documented with real evidence in their respective Duck
artifacts (`duck/milestone-1.md`, `duck/milestone-2.md`, this file). The refund-verification
scenario demonstrates all five of `docs/PRODUCT.md`'s V0 success criteria: genuine success
(VERIFIED), false completion (CONTRADICTED via FALSE_ACK), incomplete business outcome
(CONTRADICTED via DROP_NOTIFICATION), verifier unavailable (INDETERMINATE via READ_UNAVAILABLE),
and unknown claim (NOT_VERIFIABLE via the normalizer's fail-closed path) — each proven live, not
just in the automated suite.

## Implementation SHA

`5c4c5a6b8833ed181034976d87f80ca27289d777` (branch `claude/agentproof-v0-spec-2po6c9`) — this is
the commit the automated suite, frontend build, and live smoke test above were run against.

## Next Step

Await explicit human approval before any post-V0 work. Per `docs/MVP_SCOPE.md`, that roadmap
(Milestone 4: incident triage, Milestone 5: employee offboarding, Milestone 6: dashboard polish,
Milestone 7: external integration/API hardening) is listed for reference only and none of it is
authorized by V0's approval.
