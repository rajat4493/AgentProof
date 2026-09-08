# Duck — milestone-2-plan

## Intent

Add deterministic, repeatable failure injection to the refund scenario (NORMAL, FALSE_ACK,
DROP_NOTIFICATION, READ_UNAVAILABLE) so the WOW demo — and INDETERMINATE's live end-to-end
path, deferred from Milestone 1 — don't depend on the model spontaneously hallucinating. Also
fix a correctness gap identified in Milestone 1 review: evidence collection selected the first
matching refund/message for an (order_id, customer_id) pair rather than correlating to the
specific run, which is wrong the moment the same order/customer has more than one refund or
message on record (a repeated run, a retry, or — starting this milestone — a FALSE_ACK run
followed by a NORMAL run on the same order).

## Scope

**Correlation fix (applies retroactively to the Milestone 1 vertical loop, not just new failure
modes):**

- The simulator's write endpoints (`create_refund`, `send_notification`) now require a `run_id`
  on every request. It is stamped by `app/agent.py`'s tool-execution harness itself — never
  exposed to the LLM's tool schema, never something the model types out — the same way the
  agent's write credential is a harness concern, not a model concern.
- `Refund` and `Message` rows persist their `run_id`.
- The simulator's read endpoints now require `run_id` too, and filter to it in addition to
  `order_id`/`customer_id`. `app/adapter.py` passes the current run's id on every read.
- `run_id` is a plain string column on the simulator side — not a foreign key into AgentProof's
  `runs` table — keeping the two systems' schemas independent, the same way a real payment
  processor stores a caller-supplied reference string without knowing anything about the
  caller's internal object model.
- If more than one refund/message somehow shares a `run_id` (not expected — the agent is
  instructed not to call a tool more than once, and each call is independently stamped with the
  same run_id — but not structurally impossible if a run were retried against the same run row),
  the adapter takes the most recently created one and this is called out in a code comment; it is
  not silently arbitrary.

**Simulator modes** (docs/MVP_SCOPE.md, spec §12), threaded through the harness the same way as
`run_id` — the agent never sees or reasons about `scenario_mode`, only `app/agent.py`'s tool
executor and `app/adapter.py`'s evidence collector do:

- **NORMAL** — unchanged Milestone 1 behavior.
- **FALSE_ACK** — `create_refund` returns an accepted-looking response
  (`{"accepted": true, "operation_id": "RF-..."}`) but does not persist a `Refund` row.
- **DROP_NOTIFICATION** — `send_notification` returns a success-looking response but does not
  persist a `Message` row. `create_refund` is unaffected by this mode.
- **READ_UNAVAILABLE** — the simulator's read endpoints (`/simulator/read/refunds`,
  `/simulator/read/messages`) return `503` regardless of what's actually persisted. Write
  endpoints are unaffected — the agent's action can genuinely succeed while AgentProof's
  independent read path is unreachable, which is the whole point of the scenario.

`scenario_mode` lives on `Task` (set at task-creation time, part of AgentProof's own demo
control — not part of `ExpectedOutcome`, which stays exactly the business-outcome contract
defined in `docs/PROOF_MODEL.md` and is never touched by test-mode concerns).

**Demo panel**: four buttons in the frontend (Run Successful / Run False Success / Run Partial
Failure / Run Evidence Unavailable), each creating a task with a preset scenario_mode and
running the existing four-endpoint flow (task → run → claim → verify) — no new backend
endpoints, since the existing API surface already composes into a full scenario. Deterministic,
repeatable, and resettable without manual DB edits, since each click creates a fresh task+run and
(thanks to the correlation fix above) is automatically isolated from prior runs even against the
same demo order/customer.

Not in scope: incident/identity scenarios, a generic fault-injection framework beyond these four
named modes, persisting scenario history/analytics beyond what Milestone 1 already persists per
run.

## Assumptions

- No migration tooling exists yet (V0); the `run_id` column addition and `scenario_mode` column
  addition are applied via a full `drop_all`/`create_all` dev reset, documented as a one-time
  break from any previously seeded demo data — acceptable since V0 has no production data.
- `scenario_mode` defaults to `NORMAL` so nothing calling the API without it (including the
  Milestone 1 test suite, updated only where it explicitly asserts a mode) changes behavior.
- The demo panel reuses the same order/customer as Milestone 1 (`ORD-1047` / `C-891`) across all
  four buttons, relying on the correlation fix rather than a DB reset for isolation.

## Planned Tests

1. **Repeated-run / multiple-refund correlation** (the case flagged in review): two separate
   runs against the same task, one tagged with a deliberately wrong amount, verified
   independently — each run's verdict must reflect only its own evidence.
2. **NORMAL** → VERIFIED (already covered in Milestone 1; re-asserted here with explicit
   `scenario_mode="NORMAL"` now that the field exists).
3. **FALSE_ACK** → CONTRADICTED, `refund_exists` fails, driven by a real (faked) simulator
   response the agent genuinely believed.
4. **DROP_NOTIFICATION** → CONTRADICTED, `notification.exists` fails specifically, driven by a
   real simulator write call that silently no-ops.
5. **READ_UNAVAILABLE** → INDETERMINATE — the live end-to-end test deferred from Milestone 1.
6. Live smoke test of all four via the real Claude API and the browser demo panel.

## Known Unknowns

- Whether `run_id`-scoping needs to extend to the `orders`/`customers` read endpoints too — not
  currently queried by the adapter, so out of scope unless a future milestone's evidence needs
  them.
- Exact wording/UX for surfacing `scenario_mode` in the run detail screen (e.g. a small "demo
  mode: FALSE_ACK" tag) — will decide during implementation, kept minimal.
