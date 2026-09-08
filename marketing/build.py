#!/usr/bin/env python3
"""Regenerate landing.html from landing_template.html + screenshots/.

Run whenever the demo scenarios change and new screenshots are captured:

    cd marketing && python3 build.py

To recapture screenshots: see docs/DEMO_SCRIPT.md for the demo flow and
re-run the same click-through with Playwright against a locally running app
(docs/RUNNING_LOCALLY.md), saving into screenshots/ with the same filenames.
"""

import base64
from pathlib import Path

HERE = Path(__file__).parent

IMAGE_MAP = {
    "{{IMG_HOME}}": "screenshots/00_home.png",
    "{{IMG_VERIFIED}}": "screenshots/01_verified.png",
    "{{IMG_FALSEACK}}": "screenshots/02_contradicted_false_ack.png",
    "{{IMG_DROPNOTIF}}": "screenshots/03_contradicted_drop_notification.png",
    "{{IMG_INDETERMINATE}}": "screenshots/04_indeterminate.png",
}


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> None:
    html = (HERE / "landing_template.html").read_text()
    for placeholder, rel_path in IMAGE_MAP.items():
        assert html.count(placeholder) == 1, f"expected exactly one {placeholder}"
        html = html.replace(placeholder, data_uri(HERE / rel_path))
    out_path = HERE / "landing.html"
    out_path.write_text(html)
    print(f"wrote {out_path} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
