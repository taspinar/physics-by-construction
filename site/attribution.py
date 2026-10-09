"""Write the footer attribution line into every built page.

``_quarto.yml`` holds the token ``PBC-ATTRIBUTION``; the line itself comes from
``pbc.authoring.identity``, the one source of the attribution wording. Runs
after the site is rendered (``post-render``); idempotent.
"""

import os
from pathlib import Path

from pbc.authoring.identity import footer_html

TOKEN = "PBC-ATTRIBUTION"


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    line = footer_html()
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if TOKEN in text:
            page.write_text(text.replace(TOKEN, line), encoding="utf-8")


if __name__ == "__main__":
    main()
