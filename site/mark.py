"""Give the project mark in the header of every built page its dimensions.

Quarto writes the navigation bar's logo as an image without ``width`` and
``height``, so the browser cannot reserve its box before the file loads, and
the built-site checks require both on every image. The mark is square; its
displayed size is set by site.css. This script runs after the site is
rendered (``post-render`` in ``_quarto.yml``). It is idempotent and has no
inputs but the built files.
"""

import os
import re
from pathlib import Path

# The side of the mark in CSS pixels, as site.css draws it (2.25rem).
SIZE = 36
LOGO = re.compile(r'<img (?![^>]*\bwidth=)([^>]*\bclass="navbar-logo[^"]*"[^>]*)>')


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        updated = LOGO.sub(
            lambda image: f'<img width="{SIZE}" height="{SIZE}" {image.group(1)}>',
            text,
        )
        if updated != text:
            page.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
