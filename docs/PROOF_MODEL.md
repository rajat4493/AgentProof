# AgentProof — Proof Model

## Proof definition format

Proof definitions live in code/config for V0 — no visual builder. A proof definition is a JSON
document keyed by `claim_type`, listing the mandatory checks a verdict is computed from.

```json
{
  "proof_id": "refund_completed_v1",
  "claim_type": "refund_and_notify",
  "required_checks": [
    { "field": "refund_exists", "operator": "equals", "expected": true },
    { "field": "refund.order_id", "operator": "equals", "source": "task.order_id" },
    { "field": "refund.customer_id", "operator": "equals", "source": "task.customer_id" },
    { "field": "refund.amount", "operator": "equals", "source": "task.expected_amount" },
    { "field": "refund.currency", "operator": "equals", "source": "task.currency" },
    { "field": "refund.status", "operator": "equals", "expected": "succeeded" },
    { "field": "notification.customer_id", "operator": "equals", "source": "task.customer_id" },
    { "field": "notification.order_id", "operator": "equals", "source": "task.order_id" },
    { "field": "notification.exists", "operator": "equals", "source": "task.notification_required" }
  ]
}
```

Each check compares an observed evidence field against either a literal `expected` value or a
`source` reference into the original structured task (never into the agent's claim). Checks must
correlate entities (e.g. a notification must be tied to the correct `customer_id` **and**
`order_id`) — a bare `notification_exists = true` without correlation is not a valid check.

Proof definitions are versioned (`proof_id` includes a version suffix, e.g. `_v1`) and persisted
alongside every run so historical runs remain interpretable even if the definition later changes.

Proof definitions are architected so that a visual builder could edit this same JSON shape later
— but no builder is built in V0.

## Verdicts

- **VERIFIED** — every required check passes against evidence independently collected by
  AgentProof.
- **CONTRADICTED** — at least one required check deterministically fails (evidence was
  successfully collected but does not match).
- **INDETERMINATE** — a required evidence source could not be reached/queried, so one or more
  checks cannot be evaluated either way.
- **NOT_VERIFIABLE** — the agent's claim could not be normalized to a known `claim_type`, or a
  field required by that claim type's schema could not be populated; the proof engine never runs.

No probabilistic scoring, confidence intervals, or semantic similarity is used to reach a verdict.
Every check is a deterministic equality/comparison against independently observed state.

## Claim normalization

The claim normalizer (LLM-backed) translates the agent's free-text completion claim into a
structured object:

```
"Refund done and customer told"
        ↓ normalization
claim_type = refund_and_notify
order_id = ORD-1047
amount_claimed = 185
        ↓
PREDEFINED PROOF (refund_completed_v1)
        ↓
DETERMINISTIC ENGINE
        ↓
VERDICT
```

The normalizer selects `claim_type` from a fixed, known list and fills only the fields that
claim type's Pydantic schema declares. It never invents predicates, infers new success
conditions, or touches the expected outcome. Its output is validated by a strict Pydantic model:
unknown fields, extra fields, missing required fields, or an unrecognized `claim_type` all fail
validation and the run terminates as NOT_VERIFIABLE — the normalizer never guesses or partially
fills values.

Note the amount extracted from the claim (`amount_claimed`) is retained for display/audit only.
It is never substituted for `task.expected_amount` in a check — the engine always compares
against the original structured task value.

## Evidence

Evidence is what AgentProof itself observes by independently querying the system of record with
its own read-only credential — never what the agent reports or what a tool call to the agent
returned. Both raw evidence (the verbatim API response) and normalized evidence (the fields the
proof definition's checks operate on) are persisted per run, together with which system was
queried, when, and which credential role was used.

**Evidence is correlated to the specific run, not just to the order/customer.** The same
order/customer can have more than one refund or message on record — a repeated run, a retry, or
a prior run in a different demo scenario mode — so the evidence adapter never selects "the first
matching record" for a given `(order_id, customer_id)`. Every simulator write is tagged with a
`run_id` (stamped by the agent's tool-execution harness — never something the model supplies or
could get wrong, the same way the agent's write credential is a harness concern, not a model
concern), and every simulator read the adapter performs is scoped to that same `run_id`. This
guarantees a run's verdict reflects only its own evidence, even when the same demo order/customer
is reused across many runs (see the correlation fix and its test in the Milestone 2 Duck
artifact, `/duck/milestone-2.md`).

## Evidence adapter interface

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

V0 implements exactly one adapter, for the payment/customer simulator. The interface is written
generically so future adapters (not built in V0) could implement it without changing the verdict
engine or proof definition format.
