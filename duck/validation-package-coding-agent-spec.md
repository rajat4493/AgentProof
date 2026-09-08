# AgentProof Validation Package — Coding-Agent Spec

For an agent picking up this work later — extending the landing page, refreshing screenshots,
adding to the buyer material, or building whatever comes after validation. Read this before
touching anything under `marketing/`, `validation/`, or the buyer-facing files in `docs/`.

## What exists and where

```
docs/
  DEMO_SCRIPT.md          — 30-second + extended demo scripts, live-demo troubleshooting
  RUNNING_LOCALLY.md       — quick-start referenced by DEMO_SCRIPT.md
  ONE_PAGER.md             — buyer-facing one-pager (NOT the same audience as PRODUCT.md)
  BUYER_PROFILE.md         — first-target-user segments for this validation stage
  OUTREACH_TEMPLATES.md    — cold email / LinkedIn / community / follow-up templates

marketing/
  landing_template.html    — SOURCE OF TRUTH for the landing page (has {{IMG_*}} placeholders)
  build.py                 — regenerates landing.html from the template + screenshots/
  landing.html             — GENERATED. Do not hand-edit; edit the template and rebuild.
  screenshots/*.png        — 5 real screenshots (900px wide, PNG) used in the gallery
  README.md                — how to update this folder

validation/
  validation_tracker.csv   — company, contact_name, contact_role, segment, use_case, reaction,
                              pain_level, willingness_to_pilot, willingness_to_pay, objections,
                              next_step, owner, status  (3 EXAMPLE rows at present)
  README.md                — field definitions, pain_level rubric, how to use the tracker

frontend/app/page.tsx      — ONE presentational change: DEMO_SCENARIOS[].thirtySecondPick,
                              rendered as a star + highlighted border on the FALSE_ACK card,
                              plus updated copy in the demo panel's intro paragraph. No new
                              props, no new API calls, no new component.
```

## Hard constraints for anyone extending this

1. **No product capability changes here.** This package's entire mandate was presentation, demo
   repeatability, and buyer material — not touching `backend/app/` (proof definitions, verdict
   engine, adapters, API surface) or adding scenarios. If a future task needs product changes,
   that's a different work item with its own approval, not an extension of this one.
2. **Every screenshot must be real.** Never generate, mock up, or hand-edit a screenshot into
   looking like a run that didn't happen. If the UI changes and screenshots go stale, recapture
   them live (see "Regenerating screenshots" below) — don't Photoshop the old ones.
3. **`landing.html` is a build artifact.** Never hand-edit it directly — edits get silently
   destroyed the next time someone runs `build.py`. Edit `landing_template.html`.
4. **Keep the `{{IMG_*}}` placeholder contract.** `build.py` asserts each placeholder appears
   exactly once in the template and fails loudly otherwise — this is deliberate (a silent
   duplicate or missing placeholder previously would have meant a broken or missing image with no
   error). Preserve that assertion if you touch `build.py`.

## Regenerating the landing page after a screenshot refresh

1. Get the app running locally: `docs/RUNNING_LOCALLY.md`. A real `ANTHROPIC_API_KEY` is
   required — there is no offline demo mode, by design.
2. Reset to a clean demo state (optional but recommended for a clean gallery):
   ```sql
   DELETE FROM runs; DELETE FROM tasks; DELETE FROM messages;
   DELETE FROM refunds; DELETE FROM simulator_run_config;
   ```
3. Click through the four demo scenarios (`docs/DEMO_SCRIPT.md`'s extended path) plus the home
   page, capturing full-page screenshots. This session used Playwright + Chromium headless at a
   1100px viewport width; any equivalent tool works. Order used, mapped to filenames:
   - `00_home.png` — home page after all four scenarios have run once (populated live feed)
   - `01_verified.png` — Run Successful Scenario result page
   - `02_contradicted_false_ack.png` — Run False Success Scenario result page
   - `03_contradicted_drop_notification.png` — Run Partial Failure Scenario result page
   - `04_indeterminate.png` — Run Evidence Unavailable Scenario result page
4. Resize to 900px width (keeps the page light — full-resolution originals aren't needed for a
   web gallery) and save into `marketing/screenshots/`, overwriting the old files:
   ```python
   from PIL import Image
   im = Image.open(src_path)
   if im.width > 900:
       im = im.resize((900, int(im.height * 900 / im.width)), Image.LANCZOS)
   im.save(dest_path, optimize=True)
   ```
5. `cd marketing && python3 build.py`
6. Open `landing.html` locally (or via the Artifact tool's read/republish flow) and eyeball it
   once before shipping — check both color schemes if you touched CSS
   (`prefers-color-scheme: dark` — Playwright: `browser.new_page(color_scheme="dark")`).
7. If publishing as a Claude Artifact and updating an existing one: pass the existing artifact's
   `url` so it updates in place rather than creating a duplicate (see the Artifact tool's own
   docs on this — read the artifact first if you didn't publish it in the current session).

## Design system reference

The landing page's design tokens (colors, type, spacing) are defined once at the top of
`landing_template.html`'s `<style>` block — light palette in bare `:root`, dark overrides in both
`@media (prefers-color-scheme: dark)` (guarded `:not([data-theme="light"])`) and
`:root[data-theme="dark"]`, per the three-state theme contract (system/light/dark). Semantic
verdict colors (`--verified`, `--contradicted`, `--indeterminate`, `--notverifiable`) are
deliberately separate from the page's own accent color (`--accent`, a navy-ink tone) — don't
reuse a verdict color as a UI accent or vice versa; that conflation was a specific design choice
to keep verdict semantics legible against the page's own branding.

Fonts: Fraunces (display/headlines), IBM Plex Sans (body/UI), IBM Plex Mono (data, evidence
fields, run IDs) — loaded from Google Fonts via `<link>`, per the Artifact CSP. If adding new
type usage, reuse these three rather than introducing a fourth face.

## Known limitations / things intentionally left undone

- The landing page's CTA links are `mailto:` placeholders (`hello@agentproof.dev`) — replace with
  a real contact address/form before actually distributing the link externally; this was left as
  a placeholder since a functioning contact form would be new capability, out of this package's
  scope.
- No analytics/tracking on the landing page — deliberately, since a validation package's job is
  to drive real conversations logged by a human in `validation_tracker.csv`, not to be
  instrumented as if it were a production marketing funnel yet.
- The demo panel's "starred" scenario (`thirtySecondPick`) is currently hardcoded to `FALSE_ACK`
  in `frontend/app/page.tsx`'s `DEMO_SCENARIOS` array — if the recommended 30-second scenario
  ever changes, update both that flag and `docs/DEMO_SCRIPT.md` together; they will silently
  drift apart otherwise since nothing enforces they agree.

## Testing expectations for future changes here

- `frontend`: `npm run build` must stay clean.
- `backend`: unaffected by anything in this package; the full `pytest` suite (23 tests as of this
  writing) should still be run if you touch `frontend/app/page.tsx`, since it's the one file this
  package shares with the operational app, even though the change itself was presentational.
- `marketing/landing.html`: no automated test exists (it's static content) — the discipline is
  the manual one-look-before-publish pass described in the `artifact-design` skill: render once,
  fix what's visibly broken, don't loop on aesthetic polish.
