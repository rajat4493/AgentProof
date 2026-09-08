# AgentProof — Outreach Templates

Paired with `docs/BUYER_PROFILE.md`. These are starting points, not scripts — replace every
`[bracket]`, and delete the line asking for a war story if you already know theirs. The goal of
every message here is a 15-minute call to watch the 30-second demo live, not a sale.

## Cold email — Segment 1 (AI automation / agent platform leads)

**Subject:** does your agent ever lie to you?

> Hi [name],
>
> Saw [specific: their post about the agent they shipped / a talk they gave / a project on
> GitHub] — curious how you're handling this: when your agent says a task succeeded, how do you
> actually know?
>
> I've been building AgentProof, which doesn't trust the agent's own tool-call response — it
> independently re-queries the real system with a separate read-only credential and returns one
> of four verdicts (VERIFIED / CONTRADICTED / INDETERMINATE / NOT_VERIFIABLE). The moment that
> sells it is watching a real Claude agent get lied to by its own tools and confidently report
> success anyway — AgentProof catches it in about 15 seconds, live.
>
> Would a 15-minute call be useful? I'd rather show you than describe it.
>
> [name]

## Cold email — Segment 2 (fintech / payments ops)

**Subject:** the refund that "succeeded"

> Hi [name],
>
> Quick question: if an agent (or an automated workflow) at [company] reports a refund as
> processed, is there anything that independently confirms it actually happened before a customer
> tells you otherwise?
>
> I'm working on AgentProof — it's built around exactly this case. It watched a real agent get a
> false "accepted" response from a refund API, confidently report success, and independently
> catch that nothing was ever persisted — using a separate read-only credential the agent never
> touches.
>
> If you've got a war story like this, I'd genuinely like to hear it even if the timing's wrong
> for a call. If it's not wrong for a call — 15 minutes, I'll show you the live run.
>
> [name]

## LinkedIn connection note (character-limited)

> Hi [name] — building AgentProof, independent verification for AI agents (catches when an agent
> confidently reports success on something that didn't actually happen). Following your work on
> [specific]. Would love to get your read on it if useful.

## LinkedIn DM after connecting

> Thanks for connecting. Not trying to sell you anything on a first message — genuinely want a
> practitioner's reaction. AgentProof independently checks whether an agent's claimed action
> actually happened, using a separate read-only credential so it never just trusts the agent's own
> tool response. The clearest way to explain it is 30 seconds of watching it catch a false
> success live: [demo link]. If that's interesting, happy to do a quick call; if it's not a fit,
> also genuinely useful to hear why not.

## Community post (Slack / Discord / forum — not a DM)

> Been heads-down on a problem that's been bugging me: agents report their own completion, and
> most of us just... trust that. Built AgentProof to stop trusting it — independent read-only
> re-verification against the real system of record, four deterministic verdicts, no confidence
> scores. Demo shows it catching a real Claude agent getting fed a false "success" response and
> confidently reporting it anyway. If anyone's hit this in production I'd love to compare notes —
> link to the demo below, and also just curious whether this resonates or if I'm solving a
> problem nobody else has.

## Warm intro ask (to someone who can introduce you)

> Hey [name] — you mentioned [contact] is running agents in production at [company]. I'm working
> on independent verification for exactly that (agents self-reporting success that isn't real).
> Would you be comfortable making an intro? Happy to send you a one-line blurb they can forward,
> or the 30-second demo link so you can see if it's actually relevant before you vouch for it.

## Follow-up (no response after ~5-7 days)

> Hi [name] — following up in case this got buried. No pressure either way, but if it's useful:
> here's the 30-second version instead of asking for a call up front — [demo link]. If it lands,
> I'd love five minutes of reaction; if it doesn't, a one-line "not relevant because X" is
> genuinely more useful to me than silence.

## After a call — thank-you + next step

> Really appreciate the time today, and especially [specific thing they said — quote it if you
> can]. Next step on my end: [what you said you'd do]. If you're open to it, I'd like to check
> back in [N weeks] once [specific thing: they've tried it / their next agent ships / etc.] — and
> in the meantime, is there anyone else on your team who'd have a useful reaction to this?

---

## House rules for all of the above

- Never claim a capability that doesn't exist yet (multi-scenario support, SOC2, SSO — none of
  that is real at V0). If asked, say what's real today and what's roadmap, plainly.
- Lead with the demo, not the architecture. Nobody's first message should mention Pydantic.
- Every reply — yes, no, or silence after a follow-up — gets logged in
  `validation/validation_tracker.csv`. A "no" with a real objection is more valuable than a "yes"
  with no reason attached.
