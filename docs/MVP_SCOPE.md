# AgentProof — MVP (V0) Scope

## In scope for V0

One scenario, built vertically and end-to-end before anything is generalized:
**customer refund verification.**

Example task: "Refund €185 for Order 1047 and notify the customer."

```
order_id = ORD-1047
customer_id = C-891
expected_amount = 185
currency = EUR
notification_required = true
```

### Milestone 1 — one complete vertical loop

```
Structured refund task
  ↓
Claude agent
  ↓
Stateful payment/customer simulator
  ↓
Agent claim
  ↓
AgentProof independent verification
  ↓
VERIFIED / CONTRADICTED
  ↓
Verification detail UI
```

One complete working path. No other scenarios, no generalization yet.

### Milestone 2 — deterministic failure injection

Four simulator modes, each reliable and repeatable:

- **NORMAL** — refund and notification both persist → VERIFIED.
- **FALSE_ACK** — the refund action endpoint returns an accepted-looking response (e.g.
  `{"accepted": true, "operation_id": "RF-882"}`) but deliberately does not persist the refund →
  CONTRADICTED.
- **DROP_NOTIFICATION** — refund persists, notification does not, agent claims full completion →
  CONTRADICTED, with the failed notification predicate shown clearly.
- **READ_UNAVAILABLE** — the agent's action may complete, but AgentProof's independent read path
  is unavailable → INDETERMINATE (never silently VERIFIED).

A demo panel drives these four scenarios (Run Successful / Run False Success / Run Partial
Failure / Run Evidence Unavailable), each deterministic, repeatable, resettable, and runnable
without manual DB edits.

### Milestone 3 — extract only proven generic primitives

Only after Milestones 1–2 work: extract the claim model, proof definition, evidence adapter
interface, and verdict engine as named, reusable primitives — extracted from the working refund
implementation, not invented ahead of it.

V0 = Milestones 1–3 only. Do not proceed beyond V0 without explicit human approval, and do not
proceed to the next milestone without a completed Duck artifact for the current one.

## Explicitly out of scope for V0 (do not build)

- Another agent framework or orchestration engine.
- Generic LLM observability.
- A connector marketplace or generic integration registry.
- Generic prompt evaluation.
- An enterprise IAM platform.
- Dozens of integrations.
- Incident triage or employee offboarding scenarios, or any adapters/models/schemas/folders for
  them.
- A visual proof builder.
- A separate TheDuck application.
- Generic abstractions or scaffolding for future scenarios before the refund workflow works
  end-to-end.
- Real Stripe integration or real enterprise connectors.
- Customer-defined proof policies through the UI.
- SDK, webhook ingestion, MCP, framework integrations.
- Gate mode, workflow blocking, retry/recovery, human-in-the-loop.
- Proof marketplace, cryptographically signed evidence, cross-agent verification.
- Agent SLA, Agent Passport.
- Generic multi-tenant platform infrastructure.

None of the above should influence V0 design beyond avoiding obviously irreversible decisions.

## Post-V0 roadmap (not authorized by V0 approval)

- **Milestone 4** — Incident triage scenario.
- **Milestone 5** — Employee offboarding scenario.
- **Milestone 6** — Dashboard polish, run-history improvements, demo hardening.
- **Milestone 7** — External integration/API hardening.

Each milestone requires its own explicit human approval, gated on a completed Duck artifact for
the prior milestone.
