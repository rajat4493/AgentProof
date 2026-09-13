# Duck — stripe-integration

First real (non-simulator) AgentProof integration, per the user's explicit
request ("add Stripe, github, shopify, hubspot in that order") and
`docs/INTEGRATION_TARGETS.md`'s recommended build order (Stripe first —
highest plug-and-play score, closest shape to the existing refund scenario).

## Intent

Everything AgentProof had proven up to now — evidence correlation,
credential separation, the deterministic verdict engine, agent-implementation
independence — was proven against one system: AgentProof's own simulator.
This closes the "no real system integration" gap flagged as the biggest
blocker before a first paying customer, by adding a genuine second
`EvidenceAdapter` and agent write-path against Stripe's real API (test mode),
without touching the verdict engine, the proof-definition format, the claim
normalizer's validation logic, or the simulator path.

## Scope

- `backend/app/models.py` — `Task` gains `target_system` (default
  `"simulator"`, selects which agent write-path and adapter a run uses) and
  `task_payload` (JSON, nullable, for future platform-specific fields not
  needed by Stripe's first pass).
- `backend/app/schemas.py` — `StripeRefundClaim` (claim_type=`stripe_refund`,
  refund-only — Stripe has no notification concept in AgentProof's scope).
  `TaskCreateRequest`/`TaskResponse` extended with `target_system`/`task_payload`.
- `backend/app/claims.py` — `stripe_refund` registered in `CLAIM_SCHEMAS`.
- `backend/app/proof.py` — `STRIPE_REFUND_V1`: 5 checks against a Stripe
  `Charge` object (`charge_exists`, `charge.customer_id`, `charge.refunded`,
  `charge.amount_refunded`, `charge.currency`).
- `backend/app/adapter_stripe.py` — `StripeEvidenceAdapter`: independently
  queries `GET /v1/charges/{charge_id}` with a **read-only-scoped** Stripe
  Restricted Key (`STRIPE_READ_KEY`), normalizes Stripe's lowercase currency
  to AgentProof's uppercase convention. Registered in `ADAPTER_REGISTRY`.
- `backend/app/agent_stripe.py` — a Claude-driven agent write-path with one
  tool (`create_stripe_refund`) that calls `POST /v1/refunds` with a
  **write-only-scoped** Stripe Restricted Key (`STRIPE_WRITE_KEY`) — a
  distinct credential from the read key, the same separation the simulator
  enforces between `AGENT_WRITE_CREDENTIAL`/`VERIFIER_READ_CREDENTIAL`.
  `run_id` is stamped into Stripe's own `metadata[run_id]` by the harness,
  never exposed to the model's tool schema.
- `backend/app/claim_normalizer.py` — generalized (not rewritten) to
  recognize both `refund_and_notify` and `stripe_refund` claim types from one
  tool schema; each claim type populates only the subset of fields it needs.
- `backend/app/main.py` — `create_run()` routes to `run_agent` or
  `run_agent_stripe` by `task.target_system`; `verify_run()`'s existing
  generic `claim_type`-keyed resolution (`PROOF_DEFINITIONS_BY_CLAIM_TYPE`,
  `CLAIM_SCHEMAS`, `ADAPTER_REGISTRY`) needed no changes at all — this is the
  Milestone 3 extraction paying off exactly as intended.
- `backend/app/config.py` — `STRIPE_API_BASE`/`STRIPE_WRITE_KEY`/`STRIPE_READ_KEY`.
- Offline tests: `tests/test_agent_stripe.py`, `tests/test_adapter_stripe.py`
  (VERIFIED / CONTRADICTED / INDETERMINATE / charge-not-found cases, all
  through the real `STRIPE_REFUND_V1` proof definition), plus lockstep
  registry coverage added to `tests/test_primitives.py`.
- `backend/scripts/test_stripe_integration.py` — one-shot live test script,
  not yet run (see Unverified).

**Testing approach decision:** extended the project's existing
injectable-caller pattern (`ClaudeCaller`/`NormalizerCaller`) with
`StripeReadCaller`/`StripeWriteCaller` protocols, rather than adding a new
HTTP-mocking dependency (`respx` was considered, not installed, not added) —
consistent with the codebase's established convention and avoids a new
dependency for something the existing pattern already solves.

**Correlation note (documented limitation):** the simulator's adapter scopes
evidence by `run_id` because multiple runs can share an `(order_id,
customer_id)`. Stripe's `charge_id` is already the unique identifier for the
exact resource acted on, so `StripeEvidenceAdapter` does not need — and does
not do — additional `run_id` scoping on its read. If a future scenario needs
to distinguish multiple refund attempts against the *same* charge, that
would require reading the charge's `refunds` list and matching by the
`run_id` the write-path already stamps into Stripe's `metadata` — not
implemented in this first pass, since nothing in this integration yet
exercises that case.

## Assumptions

- "Stripe" here means refund verification against `Charge` objects specifically
  (matching the already-proven refund_and_notify shape) — not subscriptions,
  disputes, or payment intents, none of which were requested.
- The agent only issues refunds; it does not create charges. A real Stripe
  test-mode charge must exist before a task can be created — this mirrors
  how the simulator's Order/Customer rows are seeded ahead of a task, just
  via Stripe's own test-mode tooling instead of AgentProof's seed data.
- No notification step exists for Stripe in this scope (unlike
  refund_and_notify) — not asked for, and Stripe has no native concept for
  AgentProof to verify against here without inventing a new evidence source.

## Tests Run

**Offline (no live API calls) — 30/30 passing, includes 7 new tests:**
- `test_agent_stripe.py::test_agent_calls_create_stripe_refund_with_run_id_stamped_by_harness`
  — confirms the harness stamps `run_id` into Stripe's metadata field, invisible
  to the model's tool schema (same discipline as the simulator agent).
- `test_agent_stripe.py::test_agent_receives_structured_task_with_order_id_as_charge_id`
  — confirms the agent is given the exact structured field values, not asked
  to infer the charge id from prose.
- `test_adapter_stripe.py`, 4 cases against the real `STRIPE_REFUND_V1`
  proof definition and `verdict_engine.evaluate()`: VERIFIED (matching
  charge), CONTRADICTED (charge never refunded — the FALSE_ACK-equivalent
  case for Stripe), INDETERMINATE (Stripe unreachable), CONTRADICTED
  (charge_id not found at Stripe).
- `test_primitives.py::test_stripe_claim_type_registered_in_lockstep` — the
  three-registry lockstep invariant (claims/proofs/adapters) holds for the
  new claim type, same as it does for `refund_and_notify`.
- Full regression suite re-run after every change: 30/30 passing throughout.
- Manual smoke test against the real running API (not pytest): created a
  `target_system="stripe"` task through `POST /api/tasks` and confirmed both
  proof definitions serialize correctly from `GET /api/proofs` — this
  exercises the actual FastAPI route and Pydantic response models, not just
  unit-level code.

## Verified

- The claim/proof/adapter three-registry pattern (Milestone 3's extraction)
  generalizes to a second, real claim type with zero changes to
  `verify_run()`'s resolution logic, the verdict engine, or the proof
  definition format — this was the specific architectural claim
  `docs/INTEGRATION_TARGETS.md` said a real second adapter would test, and
  it held.
- `StripeEvidenceAdapter` correctly distinguishes VERIFIED / CONTRADICTED /
  INDETERMINATE cases against (faked) Stripe evidence, including the
  currency-casing normalization (Stripe: lowercase, AgentProof convention:
  uppercase) and the charge-not-found case.
- `run_agent_stripe` stamps `run_id` into Stripe's own `metadata` field via
  harness code the model never sees, mirroring the existing agent's
  discipline exactly.
- The claim normalizer's one tool schema now correctly branches between two
  claim types without weakening either schema's `extra="forbid"` boundary
  (nulls for the unused claim type's fields are dropped before Pydantic
  validation, same mechanism as before).

## Unverified

- **No live Stripe API call has been made.** `STRIPE_WRITE_KEY`/`STRIPE_READ_KEY`
  are not yet configured — nothing in this Duck should be read as claiming
  the real Stripe integration works end to end against Stripe's actual
  servers. `backend/scripts/test_stripe_integration.py` exists to run that
  test but has not been run.
- No live Claude API call was made for the Stripe agent path specifically
  (the offline tests use a scripted `ClaudeCaller`, same convention as the
  original agent's offline test suite) — a live run is part of the same
  pending step as the live Stripe call above, since both need real
  credentials.
- Stripe idempotency behavior (what happens on a genuine retry of the same
  refund) was not investigated or tested — out of scope until it's the
  actual failure mode being verified.

## Failures

None encountered. The only environment issue was the expected one: the dev
Postgres schema needed a manual drop/recreate to pick up `Task`'s two new
columns, since this project has no migration tool (documented, existing
project convention — same as every prior schema change in Milestones 1-3).

## Scope Drift

None. GitHub, Shopify, and HubSpot were explicitly requested next but not
started — per the user's own stated order and this project's
one-platform-at-a-time discipline, Stripe is built, offline-tested, and
stopped here pending real credentials before moving on.

## Implementation SHA

Pending commit on branch `claude/agentproof-v0-spec-2po6c9` (this Duck is
committed in the same commit as the code it describes).

## Next Step

Stop and request from the user, for Stripe test mode only (no real money):
1. A **write-scoped** Stripe Restricted API key (`rk_test_...`) — Write-only
   on Refunds.
2. A separate **read-scoped** Stripe Restricted API key (`rk_test_...`) —
   Read-only on Charges.
3. A pre-existing Stripe test-mode charge id (and its amount/currency) to
   refund against, created via the Stripe dashboard's test mode or API —
   AgentProof's agent does not create charges, only refunds them.

Once supplied (placed in `backend/.env` as `STRIPE_WRITE_KEY`/`STRIPE_READ_KEY`,
never committed), run `backend/scripts/test_stripe_integration.py` for a
genuine VERIFIED case, then intentionally test a CONTRADICTED case (e.g. by
pointing the verifier at a charge that was never refunded) before Stripe is
considered done — matching the VERIFIED+CONTRADICTED minimum bar
`duck/agent-sdk-independence-test.md` used for the prior live-test question.
Only after that should GitHub (next in the user's stated order) begin.
