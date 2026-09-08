# Marketing / Landing Page

`landing.html` is the buyer-facing landing page — self-contained (screenshots embedded as base64
data URIs), openable directly in a browser with no server. It's also published as a Claude
Artifact for sharing a live link; see the team for the current URL, or republish with the
Artifact tool (`file_path: marketing/landing.html`) to get one.

## Files

- `landing_template.html` — the source of truth. Has `{{IMG_...}}` placeholders instead of
  inlined image data — edit this, not `landing.html` directly.
- `screenshots/` — the five screenshots used in the "Exhibits" gallery section, captured live
  against a running instance (see `docs/DEMO_SCRIPT.md` for the click-through, `docs/RUNNING_LOCALLY.md`
  for getting the app running first).
- `build.py` — regenerates `landing.html` from the template + screenshots. Run
  `python3 build.py` after editing the template or recapturing screenshots.
- `landing.html` — the generated, shippable file. Committed so the page is usable straight from
  a checkout without a build step.

## Updating

1. Edit `landing_template.html` (copy, layout, styling).
2. If screenshots need to change, recapture them (same filenames, `screenshots/`) — a real run
   against a live instance, not a mockup. This page's whole premise is that every screenshot is
   real, so don't fake one.
3. `python3 build.py`
4. Republish the Artifact if a live link is in use.
