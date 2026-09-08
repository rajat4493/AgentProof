# Duck — validation-package

Not a numbered milestone. This sits alongside V0's implementation work (Milestones 1-3, complete)
as a parallel, non-technical effort: a "V0 Product Validation Package" — presentation, demo
repeatability, and buyer-facing material only. It is explicitly not Milestone 4 (incident triage,
reserved and untouched in `docs/MVP_SCOPE.md`'s roadmap) and adds no product capability.

## Intent

Make the already-working V0 refund-verification scenario understandable and demoable to a buyer
in under 30 seconds, and give the team a repeatable way to find out — honestly, with a paper
trail — whether anyone outside engineering actually wants this. Per the request: presentation,
demo repeatability, buyer-facing material. Not incident triage, identity, new connectors, SDKs,
or marketplace work.

## Scope

Delivered:

1. **30-second demo path** — `docs/DEMO_SCRIPT.md`, built entirely on the four existing
   Milestone 2 scenarios. No new scenario, no new backend behavior.
2. **Landing page** — `marketing/landing.html` (also published as a Claude Artifact), built
   around "Your agent says it's done. Check reality." A hero "exhibit" showing a real claim next
   to a real CONTRADICTED stamp, a six-stage verification-chain diagram, and a closing CTA.
3. **Verdict visual section** — the landing page's "docket" section: four cards, one per verdict
   (VERIFIED / CONTRADICTED / INDETERMINATE / NOT_VERIFIABLE), each with its real meaning and a
   real example predicate.
4. **Screenshots/demo gallery** — `marketing/screenshots/` (five real screenshots captured live
   against a running instance with the real Claude API — not mockups) plus the landing page's
   "Exhibits" section presenting them.
5. **One-page product explainer** — `docs/ONE_PAGER.md`, buyer-facing, distinct from the
   engineering-facing `docs/PRODUCT.md`.
6. **Buyer profile** — `docs/BUYER_PROFILE.md`, defining first-target-user segments for this
   validation stage specifically (not a generic eventual-enterprise-buyer ICP).
7. **Outreach message templates** — `docs/OUTREACH_TEMPLATES.md`, tied to the buyer profile's
   segments.
8. **Validation tracker** — `validation/validation_tracker.csv` + `validation/README.md`, with
   exactly the requested fields (company, contact, use case, reaction, pain level, willingness to
   pilot, willingness to pay, objections, next step) plus date/segment/owner/status, a pain-level
   rubric, and three worked example rows.

Also delivered, in service of #1 (demo repeatability), not as scope creep: `docs/RUNNING_LOCALLY.md`
(referenced by the demo script, didn't exist before) and light presentational polish to the
existing demo panel in `frontend/app/page.tsx` (a starred "30-second pick" scenario and
timing/repeatability copy — no new endpoints, no new component logic, no new backend behavior).

Explicitly not built, per the request: incident triage, identity, new connectors, SDKs,
marketplace work, or any change to the verdict engine, proof definition, evidence adapter, or API
surface. Reviewed against this before closing — nothing in this package touches
`backend/app/` beyond the untouched demo panel's presentational props.

## Assumptions

- "Landing page" meant a standalone buyer-facing page, not a new route mixed into the operational
  Next.js app (which is the working tool itself, not marketing collateral for it) — built as a
  self-contained HTML artifact instead, publishable both as a Claude Artifact (shareable link)
  and as a plain file openable with no server.
- Real screenshots (captured live, this session, against the real Claude API) were required
  throughout — no placeholder/mockup imagery anywhere in the package. This is a direct
  consequence of the product's own claim ("check reality") — a validation package that fakes its
  own screenshots would undercut the pitch it's making.
- The validation tracker's exact requested fields were kept as named; a few operational fields
  (date, segment, owner, status) were added as this is unusable as a real tracker without them,
  called out explicitly rather than silently expanding scope.
- No CI/build pipeline changes were needed or made — `marketing/build.py` is a manual regeneration
  script, not wired into any automated build.

## Tests Run

Since this milestone touches almost no application code, "tests" here means: confirming the one
UI change didn't regress anything, and confirming every piece of buyer-facing content is accurate
to what the product actually does (no aspirational claims).

- **Frontend build** (`npm run build`): clean, no errors, after the demo-panel polish.
- **Backend test suite** (`pytest`): 23/23 passing, unchanged — confirms the demo-panel
  presentational change touched nothing that could regress backend behavior (it didn't touch the
  backend at all).
- **Landing page correctness pass**: rendered locally with Playwright before publishing (per this
  session's `artifact-design` skill discipline), in both light and dark color schemes. Found and
  fixed two real bugs this way: an overlapping label under the hero's rotated verdict stamp, and
  a gallery image that failed to load (`loading="lazy"` deferred an off-screen image past the
  full-page screenshot capture — removed `loading="lazy"` from all five images, since they're
  already-embedded data URIs with no network benefit to lazy-loading). Re-verified via
  `img.complete`/`naturalWidth` in a headless browser after the fix, not just visually.
- **Content accuracy pass**: every claim on the landing page, one-pager, and buyer profile
  checked against what V0 actually does — the hero exhibit's claim text and predicate rows are
  taken verbatim from a real captured run (`RUN-466e2d0d`), not invented copy. The one-pager's
  "What we've proven" section lists only the five success-criteria tests actually run live in
  Milestones 1-3's Duck artifacts.
- **CSV validity**: `validation_tracker.csv` parsed with Python's `csv.DictReader` to confirm no
  quoting/escaping errors before committing.

## Verified

- The 30-second demo path is real and repeatable: it's the same "Run False Success Scenario"
  button already proven live and deterministic in the Milestone 2 Duck artifact, now scripted
  with exact timing and talking points.
- The landing page builds and renders correctly in both light and dark themes, with all five
  embedded screenshots loading (confirmed programmatically, not just by eye).
- No application behavior changed — confirmed by the unmodified 23-test backend suite and a clean
  frontend build.
- Every screenshot in the gallery and every quoted agent claim on the landing page is from a real
  live run captured this session, traceable to a specific `RUN-...` ID.

## Unverified

- **Whether any of this actually lands with a real buyer.** That's the entire point of the
  package, not a gap in it — `validation/validation_tracker.csv` exists specifically because this
  cannot be verified by an agent; it can only be verified by running real conversations and
  logging what happens. Nothing in this Duck artifact should be read as evidence that the
  positioning is correct, only that the material to go find out now exists.
- The landing page has not been tested against real buyer traffic, a11y-audited beyond
  Playwright's basic rendering check, or load-tested (it's a static self-contained file — none of
  that is likely to matter, but none of it was explicitly checked either).

## Failures

Two bugs, both caught and fixed before publishing (see Tests Run): the stamp/label overlap and
the `loading="lazy"` image that failed to load off-screen. No failure reached the published
artifact.

## Scope Drift

None beyond the two explicitly-justified additions (`docs/RUNNING_LOCALLY.md`,
demo-panel copy polish) already called out in Scope above, both in direct service of "demo
repeatability" as requested. No incident triage, identity, connector, SDK, or marketplace work
was added. No change to `backend/app/` beyond what's already noted.

## Product Learning

What this exercise surfaced about making a technical MVP legible to a buyer, worth carrying into
future work (not a request for approval — a record for whoever plans the next round of buyer
conversations):

1. **The claim/verdict pairing is the entire pitch — everything else is supporting cast.** The
   single highest-leverage moment in both the demo script and the landing page is the same one:
   a confident, specific, wrong agent claim sitting next to a red CONTRADICTED stamp. Nothing
   about credentials, Pydantic, or the verdict engine's determinism needs to be said out loud to
   land the point — a buyer gets it from that one juxtaposition faster than from any
   explanation. Future buyer-facing work should keep protecting this moment rather than
   surrounding it with architecture explanation.
2. **"Real, not staged" has to be provable, not asserted.** Simply writing "this is a real Claude
   agent" on the page is a claim like any other. What actually carries conviction is specific,
   falsifiable detail: a real run ID (`RUN-466e2d0d`), the exact predicate failures
   (`expected true, observed false`), a timestamp. The landing page's exhibit works because it
   reads like a system log, not a mockup — that specificity is worth preserving even as the copy
   gets iterated.
3. **The four-verdict framing needs a buyer-side translation, not just the engineering one.**
   Internally, `VERIFIED/CONTRADICTED/INDETERMINATE/NOT_VERIFIABLE` are precise and load-bearing.
   To a buyer on a first call, `INDETERMINATE` in particular needs one extra sentence
   ("it says 'I don't know' instead of guessing yes") before its significance lands — this
   sentence is now baked into the demo script and the docket section specifically because it
   didn't land on the first draft of the landing page without it.
4. **A validation package can quietly overclaim its own roadmap if no one checks for it.**
   `docs/ONE_PAGER.md` mentions where the architecture is headed (other business-critical agent
   actions); every buyer-facing document was deliberately re-read against "is this built, or is
   this roadmap" before being finalized, and the roadmap mention was written as an explicit,
   separate, clearly-labeled closing section rather than folded into the "what we've proven"
   claims. That check needs to stay a standing discipline for future buyer-facing material, not a
   one-time pass — the cost of a buyer catching an overclaim in month one is much higher than the
   cost of writing "not built yet" plainly now.
5. **The tracker only works if pain is logged un-rounded.** The buyer profile and outreach
   templates are hypotheses; nothing in this package can validate them by construction. The one
   design choice that matters most in the tracker is the instruction (in `validation/README.md`)
   not to round `pain_level` up — a technical MVP's biggest risk at this stage isn't a bad demo,
   it's a team convincing itself of product-market fit from a handful of polite reactions.

## Implementation SHA

`2649270de50a6ca335271e05716fd934d539e055` (branch `claude/agentproof-v0-spec-2po6c9`) — this is
the commit the frontend build, backend test suite, and landing-page rendering checks above were
run against.

## Next Step

This package is ready to use — start logging real conversations in
`validation/validation_tracker.csv`. No further engineering approval is needed to *use* it, since
it added no product capability; the standing V0 approval boundary (no work beyond Milestones 1-3
without explicit approval) is unaffected and still holds for any actual product work the
validation conversations surface.
