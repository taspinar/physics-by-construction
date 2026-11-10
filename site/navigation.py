"""Give the shared header its compact form on a narrow screen (F158, round 2
of Issue #462; docs/atelier.md, "Header").

Quarto renders the header as the mark and the title, two lists of entries
(the three menu items and the start link), the tools, and the search. This
script, run after the site is rendered (``post-render`` in ``_quarto.yml``),
rewrites it on every built page:

- the title becomes two spans, the full name and its short form (the initials,
  "PBC"), of which the style sheet shows one below the break point of the
  compact header and keeps the other rendered but clipped, so the home link
  keeps the full name as its accessible name and no text is hidden;
- the two lists are moved after the search and wrapped in a native
  ``<details class="pbc-menu" open>`` whose ``<summary>`` is the menu toggle
  (an icon drawn by the style sheet; a button named "Menu" with its state
  in ``aria-expanded``, since a browser exposes a bare summary without a
  name or a state): open in the HTML, so a reader without scripts has the
  four entries under the bar as before, and the toggle still works;
  ``site/learner/menu.js``, loaded right after it, closes the menu below
  the break point before the first paint and keeps the state in step.

Idempotent; no inputs but the built files.
"""

import os
import re
from pathlib import Path

TITLE = re.compile(r'<span class="navbar-title">([^<]+)</span>')
LISTS = re.compile(
    r'\s*(<ul class="navbar-nav[^"]*">.*?</ul>)'
    r'\s*(<ul class="navbar-nav[^"]*">.*?</ul>)',
    re.S,
)
SEARCH = re.compile(r'<div id="quarto-search"[^>]*>.*?</div>', re.S)
MENU = "pbc-menu"
SCRIPT = "learner/menu.js"


def short_form(title: str) -> str:
    """The initials of the title's words, in capitals: "PBC"."""
    return "".join(word[0].upper() for word in title.split())


def compact(text: str, depth: int) -> str:
    """The page ``text`` with its header in the compact form, or unchanged
    when it has no header or already has the form."""
    if MENU in text or not (title := TITLE.search(text)) or not LISTS.search(text):
        return text
    name = title.group(1).strip()
    text = TITLE.sub(
        '<span class="navbar-title"><span class="pbc-title-full">'
        f'{name}</span><span class="pbc-title-short" aria-hidden="true">'
        f"{short_form(name)}</span></span>",
        text,
        count=1,
    )
    lists = LISTS.search(text)
    menu = (
        f'<details class="{MENU}" id="{MENU}" open>'
        '<summary class="pbc-menu-toggle" role="button" aria-label="Menu"'
        ' aria-expanded="true">'
        '<span class="pbc-menu-icon"></span></summary>'
        f'<div class="pbc-menu-panel">{lists.group(1)}{lists.group(2)}</div>'
        f'</details><script src="{"../" * depth}{SCRIPT}"></script>'
    )
    text = text[: lists.start()] + text[lists.end() :]
    search = SEARCH.search(text)
    # After the search, so that the keyboard reaches the toggle after the
    # search as the eye does; the style sheet orders the bar.
    return text[: search.end()] + menu + text[search.end() :]


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    for page in sorted(output.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        depth = len(page.relative_to(output).parts) - 1
        updated = compact(text, depth)
        if updated != text:
            page.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
