# Duck — milestone-2

## Intent

Add deterministic, repeatable failure injection (NORMAL, FALSE_ACK, DROP_NOTIFICATION,
READ_UNAVAILABLE) so the demo — and INDETERMINATE's live end-to-end path, deferred from
Milestone 1 — don't depend on the model spontaneously hallucinating. Also fix a correctness gap
flagged in Milestone 1 review: evidence collection selected the first matching refund/message for
an `(order_id, customer_id)` pair (`refund = refunds_payload[0] if refunds_payload else None`)
rather than correlating to the specific run — wrong the moment the same order/customer has more
than one refund or message on record.

## Scope

As approved in `duck/milestone-2-plan.md`, delivered in full:

- **Correlation fix**, applied to the Milestone 1 vertical loop itself, not just new failure
  modes. Every simulator write (`create_refund`, `send_notification`) now requires a `run_id`,
  stamped by `app/agent.py`'s tool-execution harness — added to the outgoing HTTP payload after
  the LLM's tool call returns, never present in the LLM-facing tool schema, so the model has no
  way to see, reason about, or influence it. `Refund`/`Message` rows persist `run_id` as a plain
  string column (not a foreign key into AgentProof's own `runs` table, keeping the simulator's
  schema independent — the same way a real payment processor stores a caller-supplied reference
  string without knowing anything about the caller's object model). The simulator's read
  endpoints now require `run_id` and filter to it. `app/adapter.py`'s "first match" selection
  (`refunds_payload[0]`) is gone — replaced by `_most_recent()`, used only as a tie-breaker for
  the anomalous case of more than one record somehow sharing a `run_id`, with a comment
  explaining that case is itself worth investigating, not routine.
- **scenario_mode** on `Task` (`NORMAL` default), deliberately kept out of `ExpectedOutcome` —
  it's a demo/test control, not a business-outcome fact, and `ExpectedOutcome` stays exactly the
  contract defined in `docs/PROOF_MODEL.md`. Threaded through the same harness-stamping mechanism
  as `run_id`: `app/agent.py`'s tool executor stamps it onto every write, `app/adapter.py` stamps
  it onto every read.
- **FALSE_ACK**: `create_refund` returns `{"accepted": true, "operation_id": "RF-..."}` without
  persisting a `Refund` row.
- **DROP_NOTIFICATION**: `send_notification` returns an accepted-looking response without
  persisting a `Message` row. `create_refund` is unaffected by this mode.
- **READ_UNAVAILABLE**: `/simulator/read/refunds` and `/simulator/read/messages` return `503`
  regardless of what's actually persisted. Write endpoints are unaffected — the agent's actions
  genuinely succeed while AgentProof's independent read path is unreachable.
- **Demo panel**: four buttons in the frontend (Run Successful / Run False Success / Run Partial
  Failure / Run Evidence Unavailable) driving the existing four-endpoint flow with a preset
  `scenario_mode` — no new backend endpoints. Deterministic, repeatable, resettable without
  manual DB edits: each click creates a fresh task+run and, thanks to the correlation fix, is
  automatically isolated from every prior run even against the same demo order/customer
  (`ORD-1047` / `C-891`, reused across all four buttons and the manual form).

Not built: incident/identity scenarios, a generic fault-injection framework beyond these four
named modes, scenario history/analytics beyond what Milestone 1 already persists per run.

## Assumptions

All held from the plan:

- No migration tooling exists yet (V0); the `run_id` and `scenario_mode` columns were applied via
  a full `drop_all`/`create_all` dev reset (verified via `\d tasks` / `\d refunds` in `psql`
  before re-running anything).
- `scenario_mode` defaults to `NORMAL`, so nothing that doesn't explicitly opt in changes
  behavior — confirmed by the full Milestone 1 test suite still passing unmodified in substance
  (same assertions, only the write/read helper functions were extended to pass the now-required
  `run_id`).
- The demo panel reuses `ORD-1047` / `C-891` across all four buttons; isolation comes from the
  correlation fix, not a DB reset. Confirmed live — see Tests Run.

## Tests Run

**Automated (offline, deterministic — real Postgres, real HTTP between the agent/adapter and a
real running server, real credential checks, real Pydantic validation, real verdict engine; only
the two Claude-calling functions are faked):**

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

15 passed in 3.79s
```

The correlation test (`test_repeated_run_evidence_is_correlated_to_this_run_not_first_match`)
specifically: Run A gets a refund for the wrong amount (9900), Run B gets the correct refund
(18500), both against the same task/order/customer. Run A's verification observes 9900 (its own
refund, not Run B's) and CONTRADICTED. Run B's verification observes 18500 (its own refund, not
Run A's) and VERIFIED. Neither run leaks into the other's evidence.

`test_agent_calls_refund_and_notification_then_claims_completion` additionally confirms, via a
real read call against a real running server, that the refund created through the fake-Claude
agent loop carries exactly the `run_id` the test asked for and no other — proof the harness-level
stamping (not the model) is what determines correlation.

**Frontend build:** clean (`npm run build`, Turbopack, TypeScript strict) — no errors introduced
by the demo panel or the `scenario_mode`/`ScenarioMode` type additions.

**Live end-to-end, real Claude API (`claude-opus-5`), all four demo-panel buttons clicked in a
real browser (Playwright + Chromium) against the live backend, in order, reusing `ORD-1047` /
`C-891` for all four — proving the correlation fix holds under real repeated runs, not just the
unit test:**

1. **Run Successful Scenario** (`RUN-47a294e1`) — real agent call: *"I processed the €185.00
   refund for Order ORD-1047 (customer C-891) and emailed the customer a confirmation."* All 9
   checks passed → **VERIFIED**.
2. **Run False Success Scenario** (`RUN-e3b93544`, `scenario_mode=FALSE_ACK`) — real agent call,
   genuinely fooled by the simulator's accepted-looking response, produced an *identically
   confident* claim: *"I processed the €185.00 refund for Order ORD-1047 (customer C-891) and
   emailed the customer a confirmation."* Independent read found `refund_exists=false` → all 6
   refund checks failed, both notification correlation checks passed (a real notification for
   this run did exist) → **CONTRADICTED**. "demo mode: FALSE_ACK" tag rendered correctly.
3. **Run Partial Failure Scenario** (`RUN-c2e3d216`, `scenario_mode=DROP_NOTIFICATION`) — real
   agent call: *"I processed the €185.00 refund for Order ORD-1047 (customer C-891) and sent the
   customer a confirmation notification."* All 6 refund checks passed (the refund genuinely
   persisted); all 3 notification checks failed → **CONTRADICTED**, exactly matching the spec's
   "financial action succeeded, but the claimed customer notification cannot be confirmed"
   example.
4. **Run Evidence Unavailable Scenario** (`RUN-927b8173`, `scenario_mode=READ_UNAVAILABLE`) —
   real agent call: *"I refunded €185.00 (18500 minor units) for Order ORD-1047 to customer C-891
   and emailed them a confirmation."* The refund and notification genuinely persisted (confirmed
   independently before proving unreadability — see `test_scenario_read_unavailable_is_indeterminate`
   for the same check done offline), but both simulator read endpoints returned 503 to the
   verifier. All 9 predicates resolved to "unreachable" (`passed: null`), none to `false` →
   **INDETERMINATE**, never a silent VERIFIED. This is the live end-to-end INDETERMINATE test
   explicitly deferred from Milestone 1.

The home page's live feed correctly displayed all runs with their `scenario_mode` tags (hidden
for NORMAL, shown for the other three) and correct verdict badges, hero metrics counted them
correctly (1 verified / 2 contradicted / 1 indeterminate, plus one earlier
`READ_UNAVAILABLE`→INDETERMINATE run left over from the automated test suite sharing the same dev
database — confirmed harmless, not a defect).

## Verified

- The evidence correlation bug flagged in review is fixed: evidence is now scoped to
  `(order_id, customer_id, run_id)`, never "first match." Proven both offline (a controlled
  wrong-amount/right-amount pair) and live (four real runs against the same demo order/customer
  in sequence, each independently and correctly verified).
- `run_id` and `scenario_mode` are stamped by the harness, never exposed to or influenced by the
  LLM — confirmed by the tool schemas (`app/agent.py: TOOLS`) not declaring either field, and by
  a test that reads back the actually-persisted `run_id` after a full fake-agent loop.
- All four scenario modes work exactly as specified, both offline and live with the real Claude
  API: NORMAL → VERIFIED, FALSE_ACK → CONTRADICTED (refund_exists), DROP_NOTIFICATION →
  CONTRADICTED (notification predicates only, refund predicates unaffected), READ_UNAVAILABLE →
  INDETERMINATE (never silently VERIFIED).
- The demo panel is deterministic, repeatable, and requires no manual database edits between
  scenarios — verified by running all four back-to-back against the same order/customer.
- `ExpectedOutcome` remains untouched by `scenario_mode` — confirmed by inspection of
  `app/schemas.py` and by the fact that no test needed to change any `ExpectedOutcome`-touching
  assertion.

## Unverified

- Behavior under genuinely concurrent runs (two runs racing against the same task at the same
  wall-clock time) — not exercised; V0 remains single-tenant/demo-scale and this was not called
  for.
- A `run_id` collision path (more than one refund/message legitimately sharing a `run_id`) beyond
  the `_most_recent()` tie-breaker's existence — not reachable under the current agent (it never
  calls a tool twice per run in practice) and not deliberately forced in a test; flagged in the
  code comment rather than silently assumed impossible.

## Failures

None during this milestone's implementation beyond ordinary iteration (an initial `drop_all`/
`create_all` invocation appeared to succeed but left the old schema in place — root-caused via
`psql \d tasks` showing the column truly absent, then re-run and reconfirmed via the same command
before any test was trusted). No test needed correction beyond one assertion in
`test_scenario_drop_notification_is_contradicted` that had over-narrowly assumed only
`notification.exists` would fail when a notification is fully absent — correlation checks on a
`None` record also fail equality against their expected non-null values, which is correct given
the proof definition (`docs/PROOF_MODEL.md`), not a defect; the assertion was loosened to match.

## Scope Drift

None. Reviewed against the spec's "do not build" list again before closing: no generic
fault-injection framework beyond the four named modes, no scenario-history/analytics beyond
Milestone 1's existing evidence trail, no new API endpoints (the demo panel composes the existing
four), no incident/identity scaffolding. The correlation fix itself was not scope creep — it was
raised in review as a defect in already-shipped Milestone 1 code and folded into this milestone
per instruction, with its own dedicated test as requested ("at minimum, document and test the
repeated-run/multiple-refund case").

## Implementation SHA

`a9ed24e46e6ca65cce998901d3497e3be210ee85` (branch `claude/agentproof-v0-spec-2po6c9`) — this is
the commit the automated suite, frontend build, and all four live browser runs above were run
against.

## Post-review correction (same milestone)

Review caught an independence defect in the design above: `app/adapter.py`'s evidence read calls
were passing `scenario_mode` as a query parameter, meaning AgentProof's own verifier was telling
the simulator what failure to simulate — the verifier configuring the very fault it's supposed to
independently catch, not observing an environment fault that exists independently of it.

Fixed by moving failure-mode configuration entirely onto the simulator side: a new
`SimulatorRunConfig` table (`run_id` primary key) is upserted by the write endpoints as they're
called — configuring the run's environment the same way a real chaos-engineering fault injector
would be, ahead of/alongside the traffic it affects, never told what to fake by the client doing
the observing. `app/simulator/reads.py`'s `read_refunds`/`read_messages` no longer accept
`scenario_mode` at all; they consult the stored config by `run_id` alone.
`EvidenceAdapter.collect_evidence` dropped the `scenario_mode` parameter entirely — AgentProof's
verifier now always performs the same neutral read and only ever observes the resulting system
state or an `httpx` error, with no way to know or influence *why* a read failed.

**Tests run after the fix:** full suite still 15/15
(`test_scenario_read_unavailable_is_indeterminate` was rewritten to confirm persisted state via a
direct DB query instead of a `scenario_mode`-bypassed read, then assert the read endpoint returns
`503` with no bypass available). **Live confirmation:** a manual read call against a
`READ_UNAVAILABLE` run, deliberately attempting `scenario_mode=NORMAL` as a bypass, still returned
`503` — then the same run verified end-to-end through the real API to INDETERMINATE, and a second
live run under `FALSE_ACK` was re-confirmed CONTRADICTED to show the write-side behavior was
unaffected.

**Corrected Implementation SHA:** `f5004497fab1b20d2f7cc53e32b835d15d432559` — supersedes the SHA
above for the read-independence property specifically; the rest of this Duck's evidence still
holds against the original SHA and was re-confirmed passing against this one.

## Next Step

Await explicit human approval before starting Milestone 3 (extraction of proven generic
primitives — claim model, proof definition, evidence adapter interface, verdict engine — from the
now-twice-exercised working refund implementation).
