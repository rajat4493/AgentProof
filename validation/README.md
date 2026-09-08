# Validation Tracker

`validation_tracker.csv` — one row per conversation with a prospective buyer, logged after every
call, demo, or substantive reply (including a clear "no"). The three example rows are marked
`EXAMPLE —` in the `company` column; delete them once real rows exist, or leave them at the
bottom as a reference for what a filled-in row looks like.

## Fields

| Field | What goes here |
|---|---|
| `date` | When the conversation happened (not when you logged it, if different). |
| `company` | Company name. |
| `contact_name` | Who you talked to. |
| `contact_role` | Their actual title/function — helps validate `docs/BUYER_PROFILE.md`'s segments against reality. |
| `segment` | Which `docs/BUYER_PROFILE.md` segment they map to (or "none of the above" — log that too, it's signal). |
| `use_case` | What they'd actually use AgentProof to verify, in their words. |
| `reaction` | Free text — what they said, especially direct quotes. This is the most valuable field; don't summarize it into blandness. |
| `pain_level` | 1-4 scale (below). Your honest read, not a hopeful one. |
| `willingness_to_pilot` | Would they actually run a pilot? Yes / Maybe / No + why. |
| `willingness_to_pay` | Any signal at all on budget/pricing tolerance, even "no signal yet." |
| `objections` | Specific, not vague. "Too early" is not an objection; "we don't let agents write to prod yet" is. |
| `next_step` | The concrete next action, with an owner and rough timeframe. "Follow up" alone is not a next step. |
| `owner` | Who on the team owns this relationship. |
| `status` | Free text — keep it short and current (e.g. "Pilot conversation," "Follow-up scheduled," "Not yet - revisit later," "Passed"). |

### `pain_level` scale

1. **No current pain** — no write-capable agent yet, or hasn't thought about this.
2. **Aware of the risk** — sees the problem conceptually, no specific incident.
3. **Has felt it** — a near-miss or a vague "yeah that's worried us" but no concrete incident.
4. **Has a real incident** — a specific story of an agent falsely reporting success. This is the
   strongest signal in the sheet; if `pain_level` is 4, `next_step` should never be "revisit
   later."

## What this tracker is for

It exists to answer one question honestly: **is the pain real enough that people will pilot and
eventually pay, or are we telling ourselves a story?** Log every conversation, including the ones
that go nowhere — a pattern of "not our buyer, here's why" across ten rows is exactly as useful as
a pattern of "yes, when can we start," because both tell you whether `docs/BUYER_PROFILE.md` is
right. Revise the buyer profile from this data, not the other way around.

## How to use it

- Log a row within a day of the conversation, while the quotes are still fresh — `reaction` loses
  almost all its value if written from memory a week later.
- Don't round pain up. A hopeful `pain_level` of 3 for a contact who said "we're not really
  worried about this" corrupts the whole exercise.
- Review the sheet as a whole every ~10 rows: is one segment converting and another one not? Is
  the same objection showing up three times? That's the point where `docs/BUYER_PROFILE.md` and
  `docs/OUTREACH_TEMPLATES.md` should change.
