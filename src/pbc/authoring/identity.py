"""The project's identity text: the one source of the attribution wording.

The canonical sentence says what the project is and who is behind it. The home
page, the About page, the README, and ``CITATION.cff`` carry it verbatim; the
footer carries the line derived from it. No surface types either text by hand:
the pages call :func:`description` and :func:`footer_line`, and
``python -m pbc.authoring.identity`` writes the README and ``CITATION.cff``
(``--check`` only compares). A test reads all five surfaces against this
module. ``docs/authoring.md`` states the rules.
"""

import argparse
import re
import sys
from pathlib import Path

from pbc.authoring.repository import REPOSITORY_ROOT

NAME = "Physics by Construction"
KIND = "open-source educational initiative"
ORGANISATION = "JIDAI"
ORGANISATION_URL = "https://jidai.nl"
CREATOR = "Ahmet Taspinar"

# Where the single attribution link of the home page leads.
ABOUT_ANCHOR = "about.html#creator-and-jidai"

README_START = "<!-- identity:start (written by pbc.authoring.identity) -->"
README_END = "<!-- identity:end -->"
README_BLOCK = re.compile(
    re.escape(README_START) + r".*?" + re.escape(README_END), re.S
)
CITATION_ABSTRACT = re.compile(r'^abstract: ".*"$', re.M)


def description() -> str:
    """Return the canonical sentence."""
    return f"{NAME} is a free, {KIND} by {ORGANISATION}, created by {CREATOR}."


def footer_line() -> str:
    """Return the footer attribution: the sentence without its subject."""
    return f"An {KIND} by {ORGANISATION}, created by {CREATOR}"


def footer_html() -> str:
    """Return the footer line with its one link, for the built pages."""
    line = footer_line().replace(
        ORGANISATION, f'<a href="{ORGANISATION_URL}">{ORGANISATION}</a>', 1
    )
    return line


def readme_block() -> str:
    return f"{README_START}\n{description()}\n{README_END}"


def sync_readme(text: str) -> str:
    return README_BLOCK.sub(lambda _: readme_block(), text, count=1)


def sync_citation(text: str) -> str:
    return CITATION_ABSTRACT.sub(
        lambda _: f'abstract: "{description()}"', text, count=1
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only compare")
    arguments = parser.parse_args(argv)
    stale = []
    for name, sync in (("README.md", sync_readme), ("CITATION.cff", sync_citation)):
        path: Path = REPOSITORY_ROOT / name
        text = path.read_text(encoding="utf-8")
        updated = sync(text)
        if updated != text:
            stale.append(name)
            if not arguments.check:
                path.write_text(updated, encoding="utf-8")
    if stale:
        print(("Out of date: " if arguments.check else "Updated: ") + ", ".join(stale))
    return 1 if stale and arguments.check else 0


if __name__ == "__main__":
    sys.exit(main())
