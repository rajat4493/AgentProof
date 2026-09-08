# AgentProof — Architecture (V0)

## Core model

Every verification is represented as a chain:

```
TASK → EXPECTED OUTCOME → AGENT EXECUTION → AGENT CLAIM → OBSERVED REAL-WORLD STATE → EVIDENCE → VERDICT
```

## Trust boundary: expected outcome is authoritative

The expected outcome is created from structured task data **before** agent execution and is
immutable for that run. The agent never creates, modifies, reinterprets, or replaces it, and
never supplies the values AgentProof verifies against.

```
                   ┌───────────────┐
                   │ STRUCTURED    │
                   │ TASK          │
                   └──────┬────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          CLAUDE AGENT         AGENTPROOF
```

Both the agent and AgentProof receive the same structured task independently. AgentProof always
verifies against the original structured expected outcome — never against values extracted from
the agent's own claim.

## Independence is the whole product

The agent must never hand AgentProof a tool-call result as proof.

**Bad:**
```
Claude → refund API → API responds "success" → Claude tells AgentProof "success"
```

**Good:**
```
Claude → refund API → performs action
AgentProof → independently queries payment system → independently observes persisted state
```

AgentProof always re-queries the system of record itself.

## Credential separation

The agent and AgentProof use separate credentials and separate permission scopes, enforced even
in the V0 simulator.

```
CLAUDE AGENT
    │
    │ WRITE CREDENTIAL
    ▼
SYSTEM OF RECORD
    ▲
    │ READ-ONLY VERIFICATION CREDENTIAL
    │
AGENTPROOF
```

- **Agent credential**: may create a refund, trigger a notification. Never used by AgentProof.
- **Verification credential**: may read order/customer/refund/messages. Must not create a
  refund, modify a refund, send a notification, or mutate any business state.

## LLM boundary

Claim normalization is translation, not judgment.

The LLM (claim normalizer) may:
- select a predefined `claim_type` from a known list
- populate only fields explicitly declared by that claim type's schema

The LLM may never invent proof predicates, infer new success conditions, modify expected
outcomes, change expected task values, determine pass/fail, or influence the verdict.

Normalizer output is validated against a strict Pydantic schema keyed by `claim_type`: unknown
fields fail validation, extra fields fail validation, missing required fields fail validation,
and an unrecognized claim type fails validation. Pydantic is the sole authoritative validation
boundary (no parallel schema system).

If no known `claim_type` can be confidently selected, or required fields cannot be populated, or
validation fails, the run terminates as **NOT_VERIFIABLE**. The normalizer never guesses,
defaults to the closest type, partially fills required values, or fabricates missing values.

## Components (V0)

- **Frontend** — Next.js, TypeScript, Tailwind, shadcn/ui. Dashboard, run list, verification
  detail screen, demo control panel.
- **Backend** — FastAPI, Python. Task/run orchestration, claim normalizer, deterministic
  verdict engine, evidence adapter(s).
- **Database** — PostgreSQL. Persists tasks, runs, claims, evidence, verdicts.
- **Validation** — Pydantic. Authoritative schema boundary for normalized claims and proof
  definitions.
- **Agent** — Anthropic Claude API. Executes the task against the simulator using its own write
  credential and produces a natural-language completion claim.
- **Simulator** — a stateful payment/customer system of record (part of the backend for V0):
  customers, orders, refunds, messages. Exposes separate write (action) and read-only
  (verification) endpoints. Every write carries a caller-supplied `run_id` (stamped by the
  agent's tool-execution harness, never the model) and every read the evidence adapter performs
  is scoped to that same `run_id` — evidence is correlated to the specific run, not just to the
  order/customer. Write and read behavior is further controlled by a `scenario_mode`
  (`NORMAL`/`FALSE_ACK`/`DROP_NOTIFICATION`/`READ_UNAVAILABLE`, set on `Task` at creation time)
  for deterministic, repeatable failure injection — see `docs/MVP_SCOPE.md` § Milestone 2.

## Evidence adapter interface

One generic interface, implemented only for the payment/customer system in V0:

```python
class EvidenceAdapter(Protocol):
    id: str
    name: str
    async def collect_evidence(
        self,
        claim: AgentClaim,
        expected_outcome: ExpectedOutcome,
    ) -> list[Evidence]:
        ...
```

No connector marketplace, OAuth platform, generic integration registry, or adapters for
unimplemented scenarios (incident, identity) are built in V0. The interface exists to prove it
can generalize later, not to generalize now.

## Verdict engine

A deterministic engine evaluates a proof definition's `required_checks` against normalized
evidence and the original expected outcome. Each check is a field/operator/expected(or
source-referenced) comparison. All checks must pass for VERIFIED; any deterministic mismatch
produces CONTRADICTED; unreachable evidence sources produce INDETERMINATE; unmapped/invalid
claims produce NOT_VERIFIABLE before the engine ever runs.

## Evidence persistence

Every run persists, in full: task ID, run ID, agent identity/model, task creation timestamp,
original request text, structured expected outcome, raw agent claim, normalized claim, proof
definition + version, systems queried, credential role used for verification, raw evidence,
normalized evidence, individual predicate results, final verdict, and verification timestamp. The
UI never shows a bare verdict without the evidence trail.

## API surface (V0 minimum)

```
POST /api/tasks
POST /api/runs
POST /api/runs/:id/claim
POST /api/runs/:id/verify
GET  /api/runs
GET  /api/runs/:id
GET  /api/proofs
GET  /api/health
```

This is the seam future webhook/SDK/MCP integrations may attach to later — those integrations are
not built in V0.

## Locked stack

Frontend: Next.js, TypeScript, Tailwind, shadcn/ui.
Backend: FastAPI, Python.
Database: PostgreSQL.
Validation: Pydantic.
Agent: Anthropic Claude API.

No alternative stack without explicit human approval.
