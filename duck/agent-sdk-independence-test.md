# Duck — agent-sdk-independence-test

Not a milestone — a targeted technical test requested directly ("test it around real agents
Claude has"), scoped to answering one question: does AgentProof's independent verification
actually work when the agent under test is a *different, real* Claude agent implementation, not
just the one hand-rolled loop it's always been tested against?

## Intent

`app/agent.py` drives the refund task via a manual loop directly against the raw Messages API.
That's one valid way to build a Claude agent, but it's the *only* one AgentProof had ever been
tested against. The claim underlying the whole product — that AgentProof verifies independently
of how the agent is built — had never been tested against a second, materially different agent
implementation. This closes that gap using the real Claude Agent SDK (`claude-agent-sdk`, the
actual library that powers Claude Code), not a second hand-rolled loop dressed up differently.

## Scope

- `backend/app/agent_via_claude_sdk.py` — a new, alternate agent runner with the same external
  contract as `app.agent.run_agent()` (`{"raw_claim": str, "transcript": list}`), but internally
  driven by `claude_agent_sdk.query()` against an in-process SDK MCP server exposing
  `create_refund`/`send_notification` as real custom tools. Same harness-stamping discipline as
  the existing agent: `run_id` and `scenario_mode` are added to the outgoing HTTP payload by this
  module, never present in the tool's `input_schema`, so the SDK-driven model has no more
  visibility into either than the original agent did.
- `backend/scripts/test_agent_sdk_integration.py` — a one-shot live test script: creates a task,
  drives it through the new agent runner, then hands off to AgentProof's **completely unchanged**
  claim-normalization and verification pipeline (`POST /api/runs/:id/claim`,
  `POST /api/runs/:id/verify`).
- `requirements.txt` updated with `claude-agent-sdk==0.2.152`.

**Not wired into the default flow.** `app.agent.run_agent` remains what `POST /api/runs` calls.
This is deliberately an alternate, swappable implementation used to prove a property of the
system, not a replacement — swapping the default agent implementation was not asked for and
would be a separate decision.

**No verification-side code was touched at all** — not the adapter, not the verdict engine, not
the proof definition, not the normalizer. The entire point is that none of it needed to change.

## Assumptions

- "Test it around real agents Claude has" meant: use an actual Anthropic-built agent framework
  (the Claude Agent SDK — the library Claude Code itself is built on) as the agent under test,
  confirmed directly with the user before building anything.
- One live run per scenario mode (not the full four-scenario matrix) is sufficient evidence for
  this specific question, given the four-scenario matrix was already exhaustively proven against
  the original agent implementation in Milestones 1–2's Duck artifacts. Proving the two
  "opposite" verdicts (VERIFIED and CONTRADICTED) with the new agent is enough to establish
  independence; it would not be a better use of a second agent's worth of live API calls to
  re-prove DROP_NOTIFICATION/READ_UNAVAILABLE too, since those failure modes live entirely in the
  simulator and normalizer, neither of which differs by agent implementation.

## Tests Run — live, real Claude API, both via the actual Claude Agent SDK

**Test A — FALSE_ACK (the compelling case):**

```
Agent SDK raw_claim: "I refunded €185.00 (18500 EUR minor units) on order ORD-1047 for
customer C-891 and sent them a confirmation notification."

VERDICT: CONTRADICTED
  [FAIL] refund_exists: expected=True observed=False
  [FAIL] refund.order_id / customer_id / amount_minor_units / currency / status: all observed=None
  [PASS] notification.customer_id / order_id / exists
```

A genuinely different agent implementation was fooled by the same simulator lie the original
agent was fooled by in Milestone 2, produced an equally confident false claim, and AgentProof's
unmodified verification pipeline caught it the same way.

**Test B — NORMAL (the baseline):**

```
Agent SDK raw_claim: "I refunded €185.00 (18500 EUR minor units) for order ORD-1047 to
customer C-891 and sent them a confirmation notification."

VERDICT: VERIFIED
  All 9 checks passed.
```

**Regression check:** full existing pytest suite re-run after adding the new module and
dependency — 23/23 passing, unchanged.

## Verified

- AgentProof's verdict is correct and identical in kind (VERIFIED / CONTRADICTED, with the same
  specific predicates passing/failing) regardless of whether the agent under test is
  `app.agent`'s raw Messages-API loop or a real Claude Agent SDK agent using genuine custom
  in-process MCP tools.
- The harness-stamping discipline (`run_id`/`scenario_mode` added by the calling code, never
  exposed to the model) holds under the Agent SDK's tool-calling mechanism just as it does under
  raw Messages API tool use — confirmed by the correlation and failure-injection behavior working
  correctly with no code changes on the simulator or verification side.
- Adding the new dependency and module introduced no regression in the existing suite.

## Unverified

- DROP_NOTIFICATION and READ_UNAVAILABLE were not re-tested against the SDK agent (see
  Assumptions) — not expected to differ, since both failure modes are entirely properties of the
  simulator and (for READ_UNAVAILABLE) the verifier's read path, neither of which the agent
  implementation touches.
- No claim is made about production-readiness of swapping the default agent implementation — this
  was a test of an architectural property, not a proposal to change `POST /api/runs`'s default
  behavior.

## Failures (environment, not code)

The stored `ANTHROPIC_API_KEY` from the prior session had gone invalid (401) between sessions —
caught by testing the key directly before assuming a code defect, isolated to the normalization
step (which uses that key), and resolved by the user supplying a fresh key. Notable finding along
the way: in this sandboxed environment, `claude_agent_sdk` authenticates via the ambient Claude
Code session's own credentials, not `backend/.env`'s `ANTHROPIC_API_KEY` — the SDK agent ran
successfully even while the key used by the rest of the pipeline (normalization) was dead. This is
an artifact of running inside a nested Claude Code session and would not apply to a standalone
production deployment of `claude-agent-sdk`, which authenticates the same way the rest of the
Anthropic SDKs do (see `shared/anthropic-cli.md` / API key resolution order) — worth knowing if
this module is ever exercised outside a Claude Code sandbox.

## Scope Drift

None. No verification-side code touched; the new agent runner is additive and unused by default.

## Implementation SHA

`0283da7` (branch `claude/agentproof-v0-spec-2po6c9`) for the code; this Duck records live test
results captured against that commit with a corrected (user-supplied) API key — no code changed
between the failed and successful runs, only `backend/.env`, which is not committed.

## Next Step

None required — this was a scoped technical test, answered. If there's ever interest in offering
the Claude Agent SDK as a selectable agent backend in the actual product (rather than a
proof-of-concept module), that would be a separate, explicit decision — not implied by this test.
