# Duck — milestone-1

## Intent

Build one complete, working vertical loop for the refund-verification scenario: a structured
refund task drives a real Claude agent against a stateful payment/customer simulator, the agent
produces a free-text completion claim, and AgentProof independently verifies that claim against
the simulator's real state (via a separate read-only credential) — producing VERIFIED or
CONTRADICTED with a full evidence trail shown in a verification detail UI. No other scenario,
adapter, or failure-injection mode is built in this milestone.

## Scope

As approved, with two clarifications applied throughout:

- **Money is represented as integer minor units** everywhere — `Task.expected_amount_minor_units`,
  `Order.amount_minor_units`, `Refund.amount_minor_units`, the proof definition's
  `refund.amount_minor_units` check, and the UI's `formatMoney()` helper (divides by 100 for
  display only). No floats are used for currency amounts anywhere in the stack.
- **The agent receives the complete structured task object directly.** `app/agent.py` serializes
  the full `ExpectedOutcome` (order_id, customer_id, expected_amount_minor_units, currency,
  notification_required) as JSON into the user message and instructs the model to use those exact
  field values for its tool calls — the original natural-language request is included only as
  context, explicitly marked non-authoritative. `test_agent_receives_structured_task_not_asked_to_infer_from_prose`
  asserts the literal structured JSON is present in the message sent to Claude.

Built:

- Postgres schema: `customers`, `orders`, `refunds`, `messages` (simulator/system-of-record) and
  `tasks`, `runs` (AgentProof), the latter persisting the full evidence trail per row.
- FastAPI simulator with two credential-separated route groups: `/simulator/actions/*` (agent
  write credential only: create refund, send notification) and `/simulator/read/*` (verifier
  read-only credential only: read order/customer/refunds/messages). Enforced via
  `app/security.py` dependency functions checked on every request; a credential valid for one
  role is rejected on the other role's endpoints (403).
- `app/agent.py`: manual Claude tool-use loop (no beta Tool Runner dependency) driving
  `claude-opus-5` against the two simulator action tools over real HTTP, using the agent's write
  credential — a genuine network boundary, not an in-process shortcut.
- `app/claim_normalizer.py`: a forced single-tool Claude call (`strict: true`) that selects
  `claim_type` from a fixed list (`refund_and_notify` or `not_mappable`) and fills only that
  type's declared fields. `app/schemas.py`'s `RefundAndNotifyClaim` (Pydantic, `extra="forbid"`)
  is the sole authoritative validation boundary — unknown/extra/missing fields all fail closed to
  NOT_VERIFIABLE, regardless of what the LLM call itself returned.
- `app/proof.py` (`refund_completed_v1`, 9 checks) + `app/adapter.py`
  (`PaymentCustomerEvidenceAdapter`, one `EvidenceAdapter` implementation, real HTTP GETs with the
  verifier's read-only credential) + `app/verdict_engine.py` (deterministic equality checks only,
  comparing evidence against the original `ExpectedOutcome`, never the agent's claim).
- Full API surface: `POST /api/tasks`, `POST /api/runs`, `POST /api/runs/:id/claim`,
  `POST /api/runs/:id/verify`, `GET /api/runs`, `GET /api/runs/:id`, `GET /api/proofs`,
  `GET /api/health`.
- Next.js + TypeScript + Tailwind UI: task-creation/run-trigger form, live feed of past runs with
  hero metrics, and a run detail page rendering task → expected outcome → agent claim →
  independent proof checklist → verdict → evidence sources, matching the `docs/PRODUCT.md` mock.

Not built (deferred, as instructed):

- FALSE_ACK / DROP_NOTIFICATION / READ_UNAVAILABLE simulator modes and the demo control panel —
  Milestone 2.
- INDETERMINATE's full failure-path testing (a live unreachable-evidence-source run) — explicitly
  deferred to Milestone 2 per this milestone's approval. The verdict engine's INDETERMINATE branch
  exists and is unit-reachable (any predicate whose evidence field is marked unreachable resolves
  to INDETERMINATE, checked ahead of a would-be VERIFIED outcome), but no scenario in this
  milestone drives it end-to-end, since nothing yet makes a read endpoint fail on demand.
- Extraction of generic claim/proof/adapter/engine primitives — Milestone 3.
- Second scenario, second adapter, visual proof builder, connector registry — none present.

## Assumptions

Carried over from the plan, all held:

- Single hardcoded demo tenant, no login/auth beyond the two static simulator credentials.
- Two static API keys (`AGENT_WRITE_CREDENTIAL`, `VERIFIER_READ_CREDENTIAL`) checked by FastAPI
  dependencies — not a full IAM system.
- Simulator state is real Postgres rows (created via SQLAlchemy, queried via real HTTP GETs), not
  canned responses.
- Milestone 1 exercises the NORMAL path (and CONTRADICTED via absence of state, and
  NOT_VERIFIABLE via unmappable/incomplete claims) end-to-end; INDETERMINATE is deferred per
  clarification above.

One assumption changed from the plan during implementation: the automated test suite needed a
real running HTTP server (not just an in-process ASGI transport), because `app/agent.py` and
`app/adapter.py` both make real `httpx` calls to `settings.simulator_base_url` — this is the
credential-separation boundary being tested, so it has to be exercised over the wire. `tests/conftest.py`
spins up a real `uvicorn.Server` in a background thread on a dedicated test port for the session.

## Planned Tests — outcome

| # | Planned test | Result |
|---|---|---|
| 1 | Genuine success → VERIFIED | **Run live**, twice, through the real Claude API — see below. Also covered offline in `test_genuine_success_is_verified`. |
| 2 | Claim/evidence independence (verify never trusts the agent's tool-call result or claim-extracted amount) | `test_false_completion_is_contradicted` — agent claims success in text with no refund ever created; verifier independently finds `refund_exists=False` → CONTRADICTED. |
| 3 | Credential separation enforcement | `test_agent_credential_rejected_on_read_endpoint`, `test_verifier_credential_rejected_on_write_endpoint`, plus manual curl checks (403 in both directions, 200 with correct role). |
| 4 | Normalizer validation (unmappable claim, incomplete claim) | `test_unmappable_claim_is_not_verifiable`, `test_normalizer_missing_required_field_is_not_verifiable` — both terminate as NOT_VERIFIABLE before the verdict engine ever runs (`predicate_results` stays `null`). |
| 5 | Evidence persistence (full trail, never a bare verdict) | `test_get_run_returns_full_evidence_trail` — asserts every evidence field is populated on `GET /api/runs/:id`. |
| 6 | UI smoke test (claim vs. reality layout) | Done in a real browser (Playwright + Chromium) against the live backend — see below. |

Additional test written beyond the original plan: `test_missing_notification_is_contradicted_with_exact_predicate`
(refund succeeds, notification withheld, agent still claims full completion) — this is Success
Criteria Test 3 from `docs/PRODUCT.md`, achievable in Milestone 1 without simulator failure-injection
modes since it only requires withholding one of the agent's own tool calls, not faking the
simulator's response.

## Tests Run

**Automated (offline, deterministic — the two Claude-calling seams are faked via dependency
injection, everything else is real: real Postgres, real HTTP, real FastAPI, real Pydantic
validation, real verdict engine):**

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

10 passed in 1.78s
```

**Frontend build (Next.js 16 / Turbopack, TypeScript strict):**

```
$ npm run build
✓ Compiled successfully in 5.4s
  Running TypeScript ... Finished TypeScript in 3.2s
Route (app)
┌ ○ /
├ ○ /_not-found
└ ƒ /runs/[id]
```

**Live end-to-end test, real Claude API (`claude-opus-5`), run twice via two different paths:**

1. Direct API calls (`curl`) — task `TASK-49bf8000`, run `RUN-838e4bb9`. Real agent call produced:
   > "I processed the €185.00 refund for Order ORD-1047 (customer C-891) and emailed the customer
   > a confirmation."

   Independent verification (separate `httpx` calls, verifier read-only credential) found a real
   `Refund` row (`RF-42fee168`, status `succeeded`, 18500 EUR-minor-units) and a real `Message`
   row (`MSG-f6957f08`) both correctly attributed to `ORD-1047` / `C-891`. All 9 proof checks
   passed → **VERDICT: VERIFIED**.

2. Full browser click-through (Playwright + real Chromium) against the live Next.js dev server and
   live FastAPI backend: filled the task form, clicked "Run agent + verify", which drove the same
   real agent call, real normalization call, and real verification call from the browser, then
   auto-navigated to the run detail page. Second live run (`RUN-e216c18c`) produced an
   independently-worded claim — "I refunded €185.00 (18500 minor units) for Order ORD-1047 to
   customer C-891 and emailed them a confirmation." — confirming this was a fresh live call, not a
   cached response. Result: **VERDICT: VERIFIED**, all 9 checks green, full evidence trail
   rendered (task → expected outcome → agent claim → independent proof → verdict → evidence
   sources), matching the `docs/PRODUCT.md` mock.

   Two dev-only bugs were found and fixed during this browser test (see Failures below), neither
   affecting the API/verdict logic.

**Manual credential-separation check (`curl`, real running server):**

```
-- wrong credential on write endpoint --        403
-- correct write credential --                  200 (refund created)
-- agent credential on read endpoint --          403
-- verifier credential on read endpoint --       200 (refund returned)
```

## Verified

- Genuine success end-to-end with the real Claude API, twice, via two independent client paths
  (curl and a real browser session) → VERIFIED, full evidence trail present both times.
- False completion is caught: the agent's own claim is never trusted as evidence; AgentProof's
  independent query is what determines the verdict.
- Incomplete business outcome (refund succeeds, notification withheld) is caught with the exact
  failing predicate named.
- Unmappable and incomplete claims fail closed to NOT_VERIFIABLE before the verdict engine runs —
  the normalizer never guesses.
- Credential separation is enforced in both directions, over real HTTP, not just in application
  logic.
- The full evidence trail (task, expected outcome, raw claim, normalized claim, proof definition +
  version, systems queried, credential role used, raw evidence, normalized evidence, per-predicate
  results, verdict, timestamps) is persisted and returned on every run — never a bare verdict.
- Money is integer minor units throughout, with no float arithmetic on currency amounts anywhere
  in the stack.
- The agent is given the complete structured task object and instructed to use it verbatim, not
  asked to parse amounts/IDs out of prose.

## Unverified

- **INDETERMINATE, end-to-end.** The verdict engine's INDETERMINATE branch is implemented and
  structurally reachable (any check whose evidence field the adapter marks unreachable resolves to
  INDETERMINATE ahead of VERIFIED), but no scenario in this milestone drives a real read-endpoint
  failure to exercise it live. Per this milestone's approval, this is explicitly deferred to
  Milestone 2's READ_UNAVAILABLE mode.
- The DROP_NOTIFICATION / FALSE_ACK *simulator* failure-injection modes themselves (as opposed to
  the equivalent outcomes achieved here by simply not calling a tool) — Milestone 2.
- Multi-user/concurrent-run behavior — not exercised; out of scope for a single-tenant V0 demo.

## Failures (and fixes)

Two issues were only caught by actually running the app in a browser, not by the automated suite
(which never exercises the browser or CORS):

1. **Run detail page stuck on "Loading…" forever.** The client component used React's `use()` to
   unwrap the Next.js `params` Promise; in this Next.js 16 / Turbopack dev build the component's
   `useEffect` never fired (confirmed via a temporary `console.log` — the effect body simply never
   ran). Root cause was independent of `use()` per se; switching to `useParams()` from
   `next/navigation` (the documented App Router client-component pattern) fixed it immediately —
   `node_modules/next/dist/docs/.../use-params.md` was checked before making the change, per this
   session's `claude-api` skill guidance to verify against bundled docs rather than trained
   priors for an unfamiliar Next.js version.
2. **CORS rejection from the browser.** The FastAPI CORS middleware only allowed
   `http://localhost:3000`; the dev browser session was on `http://127.0.0.1:3000`, so the
   preflight was rejected. Fixed by allowing both origins in dev.

Both are dev-configuration fixes, not defects in the verification logic; both are covered by the
"Fix dev-only wiring found during live UI verification" commit and re-confirmed by re-running the
full pytest suite (still 10/10) and a fresh live browser run afterward.

## Scope Drift

None beyond the two user-approved clarifications (integer minor units; structured task passed
directly). Reviewed against the spec's "do not build" list before writing code and again before
closing this milestone: no incident/identity adapters, no connector registry/marketplace, no
visual proof builder, no OAuth platform, no second scenario, no retry/HITL/gate-mode logic, no
generic claim-type plugin system. The one addition beyond the original milestone-1-plan.md test
list — `test_missing_notification_is_contradicted_with_exact_predicate` — is in scope because it
exercises Success Criteria Test 3 from `docs/PRODUCT.md` using only the verdict engine and the
agent's own tool-call choices, not a simulator failure-injection mode; it was called out above
rather than silently added.

## Implementation SHA

`9c0dc4c88aba9760a2e34f625d95ed813af05e92` (branch `claude/agentproof-v0-spec-2po6c9`) — includes
both the Milestone 1 implementation commit (`a379c66`) and the dev-wiring fixes found during live
UI verification (`9c0dc4c`). This is the commit the tests above were run against.

## Next Step

Await explicit human approval before starting Milestone 2 (deterministic failure injection:
NORMAL / FALSE_ACK / DROP_NOTIFICATION / READ_UNAVAILABLE simulator modes, the demo control panel,
and the live INDETERMINATE test deferred above).
