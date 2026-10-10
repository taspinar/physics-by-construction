"""Leave code and printed output out of the search index.

Quarto writes ``search.json`` from the text of every section, which includes
the code of every cell and what it printed. A reader searches for a concept,
not for a line of code, and the code makes the index grow by tens of
kilobytes per lesson, against a budget (``docs/architecture.md``, "Budgets").
This script removes from each entry the text of the ``pre`` elements of its
page. Runs after the site is rendered (``post-render``); idempotent; no
inputs but the built files.
"""

import html
import json
import os
import re
from pathlib import Path

PRE = re.compile(r"<pre\b[^>]*>(.*?)</pre>", re.DOTALL)
TAG = re.compile(r"<[^>]+>")
BLANK_LINES = re.compile(r"\n\s*\n+")


def code_texts(page: str) -> list[str]:
    """The text of every ``pre`` element of a page, longest first, so that a
    block that contains another one is removed before the other."""
    texts = set()
    for block in PRE.findall(page):
        text = html.unescape(TAG.sub("", block)).strip()
        # The index holds a block with its angle brackets escaped.
        texts |= {text, text.replace("<", "&lt;").replace(">", "&gt;")}
    return sorted((text for text in texts if text), key=len, reverse=True)


def without_code(text: str, code: list[str]) -> str:
    """The text without the code blocks. Quarto and the page differ in the
    white space of a block (an annotated excerpt has none between its lines),
    so a block is found by its characters, whatever white space lies between
    them."""
    for block in code:
        wanted = "".join(block.split())
        while wanted:
            positions = [i for i, char in enumerate(text) if not char.isspace()]
            start = "".join(text[i] for i in positions).find(wanted)
            if start < 0:
                break
            end = positions[start + len(wanted) - 1] + 1
            text = text[: positions[start]] + "\n" + text[end:]
    return BLANK_LINES.sub("\n", text).strip()


def main() -> None:
    output = Path(os.environ.get("QUARTO_PROJECT_OUTPUT_DIR", "_site"))
    index = output / "search.json"
    if not index.is_file():
        return
    entries = json.loads(index.read_text(encoding="utf-8"))
    code: dict[str, list[str]] = {}
    for entry in entries:
        page = entry["href"].split("#")[0]
        if page not in code:
            built = output / page
            code[page] = (
                code_texts(built.read_text(encoding="utf-8")) if built.is_file() else []
            )
        entry["text"] = without_code(entry["text"], code[page])
    index.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
