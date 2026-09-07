# AgentProof — Product

## Thesis

AI agents frequently report that a task is complete because a tool call succeeded, a workflow
finished, or the model inferred success. AgentProof does not trust the agent's statement. It
independently checks the relevant system of record and determines whether the intended business
outcome actually occurred.

**Core promise:** Your agent says it is done. AgentProof checks reality.

## What AgentProof is

An independent outcome-verification layer for AI agents. Given a structured task with an expected
outcome, and an agent's claim that the task is complete, AgentProof re-queries the system of
record (using credentials the agent never touches) and issues a deterministic verdict.

## What AgentProof is not

- Not an agent framework or orchestration engine.
- Not observability or monitoring.
- Not a testing framework or generic prompt evaluation.
- Not a connector marketplace or enterprise IAM platform.
- Not a visual proof builder (V0).
- Not a separate "TheDuck" application — TheDuck is a documentation discipline used to build
  this product, not a feature of it.

## Verdicts

Every verification run resolves to exactly one of four verdicts:

- **VERIFIED** — observed state satisfies all mandatory proof conditions.
- **CONTRADICTED** — observed state deterministically conflicts with the expected outcome and/or
  the agent's claim.
- **INDETERMINATE** — AgentProof cannot obtain enough evidence to establish truth (e.g. the
  system of record is unreachable).
- **NOT_VERIFIABLE** — the claim cannot be mapped to a known, checkable proof, or required
  normalized fields cannot be established.

No probabilistic or semantic judgment is permitted in an authoritative verdict. Verification is
deterministic.

## V0 scope

One scenario, built end-to-end: **customer refund verification.** An agent is asked to refund an
order and notify the customer. AgentProof independently confirms whether the refund exists, is
correctly attributed, matches the expected amount and currency, succeeded, and that a correlated
customer notification exists.

Incident triage and employee offboarding are explicitly out of scope for V0 and are not
scaffolded in any form (no adapters, models, schemas, or folders for them).

## Positioning language

- **AgentProof** — Independent outcome verification for AI agents.
- "Your agent says it's done. Check reality."
- "Never trust done without proof."

Do not position AgentProof as observability, monitoring, a testing framework, orchestration,
guardrails, or an evaluation platform.

## Success criteria for V0

Demonstrated live, using the deterministic failure-injection simulator:

1. **Genuine success** — agent completes the action, AgentProof independently confirms it →
   VERIFIED.
2. **False completion** — agent claims success, the system proves it did not happen →
   CONTRADICTED.
3. **Incomplete business outcome** — refund succeeds, required notification does not, agent
   claims full completion → CONTRADICTED, with the exact missing outcome identified.
4. **Verifier unavailable** — AgentProof cannot reach the system of record through its
   independent read path → INDETERMINATE (never silently VERIFIED).
5. **Unknown claim** — the normalizer cannot map the claim to a known schema, or required fields
   are missing → NOT_VERIFIABLE (never a guess).

An AI startup founder or enterprise automation lead should understand within 30 seconds that the
agent claimed something happened, AgentProof independently checked reality, and proved whether it
actually happened.
