# AgentProof Validation Package — Human Summary

*For anyone who wants to know what got built without reading code or specs.*

## What you asked for

A package to help figure out whether real people would care about AgentProof — without building
anything new. Just: make the existing demo good enough to show someone in 30 seconds, make a
landing page that explains it, and give the team a way to track what happens when they actually
talk to people.

## What you got

**A 30-second demo script.** Uses the four demo buttons that already existed. Tells whoever's
running the demo exactly what to click, what to say, and when — timed to the second — so anyone
on the team can run it cold and it'll land the same way every time.

**A landing page.** One page, built around the line you gave me: "Your agent says it's done.
Check reality." It opens with a real example — an actual AI agent that got fooled by a fake
"success" message, confidently reported the refund as done, and got caught by AgentProof a few
seconds later. That's the whole pitch in one screen. Below that: how it works in six steps, the
four possible outcomes explained in plain terms, and five real screenshots from an actual live
run — not mockups. You can look at it here: the link is in the wrap-up message, and the source is
saved in the project under `marketing/`.

**A one-page explainer** (`docs/ONE_PAGER.md`) — the thing you'd forward to someone before a
call, written for a person evaluating this, not an engineer building it.

**A buyer profile** (`docs/BUYER_PROFILE.md`) — who to actually talk to right now. Not "enterprise
CTOs" in the abstract — specifically, the engineer who already has an AI agent doing something
real (like processing refunds) and is quietly worried it's lying to them sometimes. It also says
plainly who's *not* worth talking to yet, which is just as useful.

**Outreach templates** (`docs/OUTREACH_TEMPLATES.md`) — cold email, LinkedIn message, a
community-post version, and a follow-up, all built around getting someone to watch the 30-second
demo rather than trying to sell them on a first message.

**A tracker** (`validation/validation_tracker.csv`) — one row per conversation. Company, contact,
what they'd use it for, how they reacted, how much it actually hurts them, whether they'd pilot
it, whether they'd pay, what their objections were, what happens next. Comes with three filled-in
example rows so it's obvious how to use it, and a short guide on not kidding yourself when you
fill it in (don't round pain up).

## What I did NOT change

Nothing about how AgentProof actually works. No new scenarios, no new checks, no new API. The one
UI change I made was cosmetic — I starred one demo button as "the 30-second pick" and added a
timing note. That's it. Everything else is new documents and one new webpage.

## What I'd flag to you directly

The whole package is built on real screenshots and a real quoted example from an actual run — I
was careful not to fake or mock up anything, since a validation package for a product whose pitch
is "we check reality" would be a bad place to fudge a screenshot. If you ever need to refresh
those screenshots (say, the UI changes later), there's a script (`marketing/build.py`) that
regenerates the page from fresh ones.

The one thing I can't do for you: whether anyone actually wants this. That's what the tracker is
for. Go have the conversations; the honest answer lives in that spreadsheet, not in anything I
can write.
