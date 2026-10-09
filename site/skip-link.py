"""Put the skip link at the start of the body of every built page.

Quarto places the content of ``include-before-body`` inside the main element,
after the navigation bar, where a skip link no longer skips anything. This
script runs after the site is rendered (``post-render`` in ``_quarto.yml``).
It is idempotent and has no inputs but the built files.
"""

import os
import re
from pathlib import Path

LINK = '<a class="skip-link" href="#quarto-document-content">Skip to main content</a>'
BODY = re.compile(r"<body\b[^>]*>")


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if 'id="quarto-document-content"' not in text:
            continue
        updated = text
        if 'class="skip-link"' not in updated:
            updated = BODY.sub(
                lambda body: f"{body.group(0)}\n{LINK}", updated, count=1
            )
        # Focusable by script, so that the skip link moves keyboard focus.
        if 'id="quarto-document-content" tabindex="-1"' not in updated:
            updated = updated.replace(
                'id="quarto-document-content"',
                'id="quarto-document-content" tabindex="-1"',
                1,
            )
        if updated != text:
            page.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
