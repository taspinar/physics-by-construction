"""Complete the caption of every figure that declares its provenance.

A figure whose PNG carries the record of ``pbc.data.figure_provenance``
(Issue #524) gets the statuses it combines, its dataset card's short credit,
and the full provenance in a closed ``<details>`` at its caption
(``pbc.authoring.figure_credits``). It fails the build when a caption or a
card disagrees with the record. Runs after the site is rendered
(``post-render``), after ``context.py``; idempotent.
"""

import os
import sys
from pathlib import Path

from pbc.authoring.figure_credits import InvalidFigure, annotate


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    figures = 0
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if "<figure" not in text:
            continue
        try:
            changed, count = annotate(text, page.parent)
        except InvalidFigure as error:
            print(f"ERROR: {page.relative_to(output)}: {error}", file=sys.stderr)
            sys.exit(1)
        if count:
            page.write_text(changed, encoding="utf-8")
            figures += count
    print(f"Figure credits added to {figures} figure(s).")


if __name__ == "__main__":
    main()
