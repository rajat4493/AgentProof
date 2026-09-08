# AgentProof — Buyer Profile (V0 Validation Stage)

This defines who to talk to *right now*, at V0 — not the eventual enterprise buyer. At this
stage the goal is 15-30 minutes of a real practitioner's time and an honest reaction, not a
closed deal. Revisit this document once `validation/validation_tracker.csv` has real signal in
it — it should change based on what people actually say, not stay fixed as a hypothesis.

## Who we're validating with first

### Segment 1 — AI automation / agent platform leads (primary)

**Who:** The engineer or team lead who owns "the agent that does X" inside a company already
running an LLM agent against a real backend system — refunds, ticket resolution, account changes,
data entry. Titles vary wildly at this stage: "AI Engineer," "Automation Lead," "Head of AI,"
"Staff Engineer, Agents." What matters is they personally own an agent in production or about to
ship one, not that they carry a specific title.

**Why they're first:** They feel the pain directly and immediately understand the pitch without
translation — "your agent already lied to you at least once, you just didn't know it." No one
else in the buying chain needs this explained to them.

**Qualifying signal:** They've shipped (or are about to ship) an agent that takes a real
write action against a real system — not just a chatbot that answers questions. If the agent
only reads and summarizes, there's nothing for AgentProof to verify.

**Where to find them:** AI engineering Slack/Discord communities, LangChain/Anthropic/OpenAI
agent-builder meetups, "agents in production" conference talks (they're often the speaker), and
directly inside companies known to be running agent pilots in support/ops.

### Segment 2 — Fintech & payments ops engineering (wedge-specific)

**Who:** Engineering leads at companies where an agent (or a human-plus-automation workflow)
touches money movement — refunds, chargebacks, payouts, ledger adjustments. This maps directly
to the V0 demo scenario, so the demo requires zero translation.

**Why they're second, not first:** Smaller pool, but the demo is a perfect fit and the pain
(a false "refund succeeded" is a real incident, not a hypothetical) is viscerally obvious in
under 30 seconds.

**Qualifying signal:** They already have (or are building) an agent or automated workflow with
write access to a payments or ledger system, and a war story about something going wrong
silently.

### Segment 3 — Trust & safety / platform reliability for internal agent tooling (secondary)

**Who:** The person responsible for "are we allowed to let this agent run unsupervised yet" —
often a platform or reliability engineer, sometimes a risk/compliance-adjacent technical role at
larger companies building internal agent infrastructure.

**Why they're secondary at V0:** They care about the same problem, but their buying motion is
slower and more process-heavy — better validated once Segment 1 conversations have sharpened the
pitch and produced war stories to reference.

## Who is explicitly NOT the V0 target

- **Non-technical business buyers** (ops managers, customer support directors) — they feel the
  downstream pain (an angry customer) but don't own the technical decision and can't evaluate a
  live demo of tool-call credentials and evidence trails. Talk to them *after* a technical
  champion is bought in, not instead of one.
- **Companies with no agent in production yet** — interesting for later, but there's no pain to
  validate against today. A "we're thinking about agents" conversation is a different, slower
  sales motion than "we shipped one and it already scared us."
- **Enterprise procurement / security review contacts** — V0 has no SOC2, no enterprise auth, no
  multi-tenant story. Talking to procurement now wastes their time and ours.

## What "good pain" looks like in a first conversation

Listen for these, and write them down verbatim in the validation tracker's `pain_level` /
`reaction` fields:

- A specific incident: "we had a refund that the agent said went through and it didn't" (this is
  gold — ask if you can use it, anonymized, as a story).
- "How would I even know if my agent lied to me?" asked with genuine uncertainty, not rhetorically.
- Any mention of a **second system of record they'd need to check manually** after an agent run —
  that's the exact gap AgentProof fills.
- Skepticism specifically about **trusting the agent's own tool-call response** — this means they
  already understand the core insight and you can skip straight to the demo.

## What "not our buyer yet" looks like

- "We don't let our agents write to anything yet, only read" — no pain to solve today; log it and
  follow up when that changes.
- "We already log everything the agent does" — probe further (logging isn't independent
  verification), but if they conflate the two and don't see the difference after the false-success
  demo, they're not ready.
