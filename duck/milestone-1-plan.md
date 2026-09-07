# Duck — milestone-1-plan

## Intent

Build one complete, working vertical loop for the refund-verification scenario: a structured
refund task drives a Claude agent against a stateful payment/customer simulator, the agent
produces a completion claim, and AgentProof independently verifies that claim against the
simulator's real state using a separate read-only credential, producing VERIFIED or CONTRADICTED
with a full evidence trail shown in a verification detail UI.

## Scope

In scope:

- Postgres schema for: `tasks`, `runs`, `customers`, `orders`, `refunds`, `messages` (simulator
  entities), plus run-scoped storage for raw claim, normalized claim, raw evidence, normalized
  evidence, predicate results, and verdict.
- FastAPI backend:
  - Simulator endpoints, split into an **action** path (agent write credential: create refund,
    send notification) and a **verification** path (AgentProof read-only credential: read
    order/customer/refund/messages). Two distinct credential values, checked on every request.
  - `POST /api/tasks` — create a structured refund task (the single source of the expected
    outcome).
  - `POST /api/runs` — start a run for a task; invokes the Claude agent against the simulator's
    action endpoints using the agent credential.
  - `POST /api/runs/:id/claim` — accept/record the agent's free-text claim, run it through the
    Pydantic-validated normalizer for `claim_type = refund_and_notify` only.
  - `POST /api/runs/:id/verify` — run the deterministic verdict engine against the one proof
    definition (`refund_completed_v1`) using evidence collected via the one evidence adapter.
  - `GET /api/runs`, `GET /api/runs/:id`, `GET /api/proofs`, `GET /api/health`.
- One `EvidenceAdapter` implementation for the payment/customer simulator (as specified in
  `docs/PROOF_MODEL.md`), used directly — not registered in any plugin/registry system.
- One proof definition, `refund_completed_v1`, exactly matching the 9 checks in
  `docs/PROOF_MODEL.md`, hardcoded as version-1 JSON/config.
- One Pydantic schema for `claim_type = refund_and_notify` normalized claims.
- Claude agent integration: single system/task prompt instructing the agent to use the
  simulator's action endpoints and then state completion in free text; no framework, no tool
  loop abstraction beyond what's needed to call two simulator actions (create refund, send
  notification).
- Next.js/Tailwind/shadcn UI:
  - A form/trigger to create a task and run it (Milestone 1 needs only a NORMAL-mode run — no
    failure-injection UI yet; that's Milestone 2).
  - A run detail page rendering: task, expected outcome, agent claim, per-predicate proof
    checklist (✓/✕), verdict, evidence-source timestamps — matching the mock in
    `PRODUCT.md §Verification detail screen`.
  - A minimal run list.

Out of scope (deferred to later milestones / post-V0, not touched here):

- Failure-injection modes (FALSE_ACK, DROP_NOTIFICATION, READ_UNAVAILABLE) and the demo control
  panel — Milestone 2.
- Extracting generic `claim model` / `proof definition` / `evidence adapter` / `verdict engine`
  primitives as reusable, named modules — Milestone 3. Milestone 1 code may be structured
  sensibly but is not required to already be "generic."
- Dashboard hero metrics, live feed, polish — Milestone 6.
- Any second scenario, adapter, or claim type.
- Any auth/multi-tenant concerns beyond the two hardcoded credential roles needed to prove
  credential separation.

## Assumptions

- A single hardcoded demo tenant/user is sufficient; no login system for V0.
- The Claude agent uses a fixed system prompt scoped to only the two simulator action endpoints
  it needs (create refund, send notification) — not a general-purpose tool-use framework.
- "Separate credentials" for V0 means two distinct static API keys/tokens checked by the
  simulator's FastAPI middleware — not a full IAM system.
- The simulator's state is an actual Postgres-backed store (rows persist), not in-memory mocked
  responses, per the "must not be a canned-response stub" requirement.
- Money amounts are stored as integers (minor units, e.g. cents) or fixed-precision decimals to
  avoid float comparison bugs in the verdict engine; exact representation decided during
  implementation.
- Milestone 1 runs only the NORMAL path end-to-end; CONTRADICTED/INDETERMINATE/NOT_VERIFIABLE
  verdict *logic* should exist in the engine (since the engine must be deterministic and general
  over the checks), but proving those paths live via failure injection is Milestone 2.

## Planned tests

1. **Genuine success (VERIFIED)** — create a task for ORD-1047/C-891/€185/EUR/notification
   required; run the agent in NORMAL mode; agent creates a real refund and sends a real
   notification; verify step independently queries the simulator and returns VERIFIED with all 9
   checks passing.
2. **Claim/evidence independence** — confirm (by code inspection + a test double) that the
   verify step never reads the agent's tool-call response or the claim's extracted amount as a
   source of truth; it only reads via the read-only verification endpoints and only compares
   against `task.*` fields.
3. **Credential separation enforcement** — verification endpoints reject requests made with the
   agent's write credential (and vice versa) with an authorization error.
4. **Normalizer validation** — a claim that cannot be mapped to `refund_and_notify` (or is
   missing a required field) fails Pydantic validation and the run terminates as
   NOT_VERIFIABLE, without ever invoking the verdict engine.
5. **Evidence persistence** — after a run, `GET /api/runs/:id` returns the full trail: task,
   structured expected outcome, raw claim, normalized claim, proof definition + version, systems
   queried, credential role used, raw evidence, normalized evidence, individual predicate
   results, verdict, timestamps — nothing collapsed to just the verdict.
6. **UI smoke test** — run detail page renders claim vs. reality correctly for a VERIFIED run,
   matching the intended "claim vs proof vs verdict" layout, checked manually in a browser.

## Known unknowns

- Exact Claude API tool-calling shape to use for the agent's two simulator actions (raw function
  calling vs. a minimal wrapper) — will decide during implementation, kept as small as possible.
- Exact numeric representation for currency amounts in Postgres/Pydantic (integer minor units vs
  `Decimal`) — will fix once schema is drafted.
- Whether the agent's system prompt should also see the notification requirement explicitly, or
  infer it from the task description text — leaning toward giving it explicitly since the task
  object is the shared structured source both sides receive.
- Level of retry/timeout handling FastAPI should have when the agent's write calls hit the
  simulator — kept minimal for Milestone 1 since deliberate unreliability is Milestone 2's job
  (READ_UNAVAILABLE etc.), not Milestone 1's.

## Premature-abstraction check

Explicitly reviewed this plan against the spec's "do not build" list and confirmed the following
are absent from Milestone 1 scope: incident/identity adapters or schemas, a connector
marketplace or generic integration registry, OAuth platform, a visual proof builder, generic
claim-type plugin registration, speculative enterprise/multi-tenant infrastructure, retry/HITL/
gate-mode logic, and any second scenario's folders or interfaces. The `EvidenceAdapter` protocol
and proof-definition JSON shape are taken as given by the spec (§7, §6) since the spec itself
defines them as the intended interface shape to prove out with one implementation — they are not
additional abstraction invented here. Milestone 3's job of *extracting* named generic primitives
from this working code is explicitly deferred, not done now.

## Status

Plan only. No implementation code has been written. Awaiting explicit human approval to begin
Milestone 1 implementation.
