# AgentProof — One-Page Explainer

*(Buyer-facing. If you want the technical spec, see `docs/PRODUCT.md` and `docs/ARCHITECTURE.md`.)*

## The problem

AI agents report their own success. "I processed the refund." "I sent the email." "I updated the
record." Teams building on agentic AI have no independent way to know if that's true — they're
trusting the same system that might be wrong, hallucinating, or being lied to by a flaky
downstream API.

That gap gets expensive fast: a refund that was never issued, a notification that never sent, an
update that silently failed — all reported as done, all discovered later, usually by a customer.

## What AgentProof does

AgentProof is an independent verification layer that sits *outside* the agent. Given a task with
a structured expected outcome, it:

1. Lets the agent act, using its own credentials.
2. Independently re-queries the real system of record — using a **separate, read-only
   credential** the agent never has access to.
3. Compares what it finds against the original expected outcome — never against what the agent
   claims happened.
4. Returns one of four deterministic verdicts.

No probability score. No confidence interval. No "looks about right." A verdict.

## The four verdicts

| Verdict | Meaning |
|---|---|
| **VERIFIED** | Every required condition was independently confirmed. |
| **CONTRADICTED** | The real system contradicts the agent's claim or the expected outcome. |
| **INDETERMINATE** | AgentProof couldn't reach the system of record — it says so, it never guesses. |
| **NOT_VERIFIABLE** | The claim couldn't be mapped to anything checkable in the first place. |

## Why this is hard to fake

The agent's write credential and AgentProof's read credential are different, enforced at the API
level. The agent literally cannot hand AgentProof a tool-call result and have it accepted as
proof — AgentProof always goes and looks for itself. This is the same reason a second signature
on a check matters: it has to come from somewhere the first signer doesn't control.

## What we've proven (V0)

One real scenario, end-to-end, live against the real Claude API — not a mockup:

- A support agent processes a refund and notifies the customer.
- Four controlled failure modes prove the four verdicts are real, not theoretical: a system that
  falsely acknowledges a refund it never persisted, a notification that silently fails to send, a
  system-of-record that goes unreachable mid-verification.
- Every run produces a full evidence trail — what was checked, when, with which credential —
  never just a bare verdict.

See the [30-second demo](../marketing/landing.html) or `docs/DEMO_SCRIPT.md` for the live click-through.

## What AgentProof is not

- Not observability or a logging dashboard — it doesn't watch, it verifies.
- Not a testing or eval framework for prompts.
- Not an orchestration engine, agent framework, or guardrail layer — it doesn't run your agent or
  block it; it tells you, after the fact, whether it actually did what it said.

## Where this is headed

V0 proves the mechanism on one scenario (refund verification). The architecture — structured
task, independent evidence adapter, deterministic verdict engine — is built to extend to other
business-critical agent actions (the roadmap includes incident response and account/access
changes) without changing the core trust model. Nothing beyond the refund scenario is built yet;
this document describes what exists today.
