"""Give the search control a fallback for readers without JavaScript.

Quarto leaves the search control as an empty element that its script fills.
Without the script nothing is shown, so this script puts a link to the
learning path in that element, inside ``noscript``: a reader with scripts
sees only the search control, a reader without sees the link. Runs after the
site is rendered (``post-render``); idempotent; no inputs but the built files.
The element is declared an enhancement (``data-enhancement``): the script
adds the search control to it, which the built-site checks allow only there.
"""

import os
import re
from pathlib import Path

CONTROL = re.compile(r'<div id="quarto-search"([^>]*)>(</div>)')
PATH_PAGE = "path/index.html"


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        if "search-fallback" in text or not CONTROL.search(text):
            continue
        depth = len(page.relative_to(output).parts) - 1
        href = "../" * depth + PATH_PAGE
        link = (
            '<noscript><a class="search-fallback" '
            f'href="{href}">Find a lesson: learning path</a></noscript>'
        )
        page.write_text(
            CONTROL.sub(
                lambda m, link=link: (
                    f'<div id="quarto-search" data-enhancement{m.group(1)}>'
                    f"{link}{m.group(2)}"
                ),
                text,
                count=1,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
