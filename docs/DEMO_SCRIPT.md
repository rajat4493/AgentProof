# AgentProof — 30-Second Demo Script

Part of the V0 Product Validation Package. This script uses only what already exists (the four
Milestone 2 demo scenarios) — no new product capability. It exists to make the demo repeatable:
any teammate should be able to run it cold, live, in front of a buyer, and land the point in
under 30 seconds.

## Before you start

- Backend and frontend running locally (`docs/RUNNING_LOCALLY.md` if you need setup steps).
- Open the app to the home page. The demo panel ("Demo scenarios — deterministic failure
  injection") should be visible without scrolling.
- Each button is deterministic and repeatable — you can click any of them again immediately
  after, on the same order/customer, with no reset needed (this is itself worth saying out loud
  if a buyer asks "can you run that again?").
- Each click takes roughly 8–15 seconds end-to-end (a real Claude API call, twice — once to act,
  once to normalize the claim — plus one independent verification call). Talk through what's
  happening while it runs; don't wait in silence.

## The 30-second path

This is the one sequence to memorize. It uses the second button only — **Run False Success
Scenario** — because it is the single moment that proves the product in one click. If you have
more than 30 seconds, the extended path below covers all four.

**0:00 — Say the line.**
> "Your agent says it's done. AgentProof checks reality before you believe it."

**0:03 — Click "Run False Success Scenario."**
> "This is a real Claude agent processing a real refund request right now — not a canned demo."

**0:10 — While it runs.**
> "The refund system just told the agent 'accepted' — and the agent believes the job is done."

**0:18 — The page lands on the run detail screen. Point at the Agent Claim card.**
> "Here's what the agent says happened: [read the claim aloud]. Confident. Specific. Wrong."

**0:24 — Point at the Independent Proof checklist — all six refund checks in red.**
> "AgentProof never trusted that tool response. It went and checked the real system of record
> itself — with a separate, read-only credential the agent doesn't even have — and found no
> refund ever happened."

**0:29 — Point at the CONTRADICTED verdict badge.**
> "That's the product. Not a monitoring dashboard. A verdict."

## The extended path (all four scenarios, ~2 minutes)

Run these in order — it's a narrative, not just a feature tour:

1. **Run Successful Scenario → VERIFIED.** Establishes the baseline: when the agent's claim is
   true, AgentProof says so, with the full evidence trail, not a leap of faith either way.
2. **Run False Success Scenario → CONTRADICTED.** The 30-second moment above. The system lied to
   the agent; AgentProof caught it independently.
3. **Run Partial Failure Scenario → CONTRADICTED.** A more subtle failure: the refund is real, the
   notification silently never sent. Say: *"This is the failure mode nobody's dashboard catches —
   the money moved, the customer just never heard about it."*
4. **Run Evidence Unavailable Scenario → INDETERMINATE.** Say: *"And when AgentProof itself can't
   reach the system of record, it says so — it never guesses VERIFIED to be agreeable."* This is
   the line that separates a real verification product from a rubber stamp.

Close on the four-verdict framing: **VERIFIED, CONTRADICTED, INDETERMINATE, NOT_VERIFIABLE — four
outcomes, never a maybe.**

## If something goes wrong live

- **A scenario takes longer than expected:** normal — it's a live Claude API call, not a mock.
  Keep talking (see script above); don't apologize for real latency.
- **You want to re-run the same scenario:** just click it again. Every run is isolated by
  `run_id` even against the same demo order — this was fixed and tested specifically so the demo
  never needs a database reset mid-pitch.
- **A buyer asks to see the raw evidence:** scroll to the Evidence card at the bottom of the run
  detail page — it shows which system was queried, the credential role used, and the timestamp.
  This is the "we're not making this up" card.

## What NOT to do

- Don't narrate the internal architecture (credentials, Pydantic, the verdict engine) unless
  asked — the demo's job is the verdict moment, not the implementation.
- Don't run more than the four existing scenarios or improvise a fifth "what if" live — if asked
  a hypothetical, answer in words, don't try to fake a new scenario in the UI.
