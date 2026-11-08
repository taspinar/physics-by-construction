"""Helpers for the unit tests of the lessons' experiments (``pbc.experiment``)."""

import importlib
import json
import re
from collections import Counter
from html import unescape
from pathlib import Path

from pbc.experiment import RESULTS_FILE, main
from support.paths import REPO_ROOT

_FIGURE_LABEL = re.compile(r"^#\|\s*label:\s*(fig-[a-z0-9-]+)\s*$", re.MULTILINE)
_NAMED = re.compile(
    r"""result(?:\.table|\.show|\.widget|\.output|\.display)?[\[(]["']([a-z0-9-]+)["'][\])]"""
)


def run_entry_point(module: str, directory: Path) -> dict:
    """Run the experiment ``module`` as the learner's command does, into
    ``directory``, and return its results file."""
    main(importlib.import_module(module).run, [str(directory)])
    return json.loads((directory / RESULTS_FILE).read_text(encoding="utf-8"))


def page_of(lesson: str) -> str:
    """The source of the lesson page ``lesson``, such as
    ``mechanics/01-kinematics-as-a-program``."""
    return (REPO_ROOT / "site" / "lessons" / lesson / "index.qmd").read_text(
        encoding="utf-8"
    )


def figure_labels(page: str) -> set[str]:
    """The labels of the figure cells of a page."""
    return set(_FIGURE_LABEL.findall(page))


def names_the_page_reads(page: str) -> set[str]:
    """The numbers, tables, and figures a page reads from its ``result``."""
    return set(_NAMED.findall(page))


def assert_the_page_and_the_results_agree(lesson: str, directory: Path, found: dict):
    """The command wrote one file per figure of the page, and its results hold
    exactly the numbers, tables, and figures the page reads."""
    page = page_of(lesson)
    labels = figure_labels(page)
    assert labels, f"{lesson} labels no figure"
    assert {f"{label}.png" for label in labels} == set(found["figures"])
    for label in labels:
        assert (directory / f"{label}.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    recorded = (
        set(found["numbers"])
        | set(found["tables"])
        | {name.removesuffix(".png") for name in found["figures"]}
        | {name.removesuffix(".json") for name in found["widgets"]}
        | set(found["outputs"])
        | set(found["displays"])
    )
    assert names_the_page_reads(page) == recorded


# --- The experiment against the built page (ADR 016 decision 4) ---------------

_TAG = re.compile(r"<[^>]+>")
_TABLE = re.compile(r"<table\b.*?</table>", re.DOTALL)
_CAPTION = re.compile(r"<caption>(.*?)</caption>", re.DOTALL)
_CELL = re.compile(r"<t([hd])\b[^>]*>(.*?)</t[hd]>", re.DOTALL)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
_OUTPUT = re.compile(
    r'<div class="cell-output cell-output-stdout">\s*'
    r"<pre[^>]*><code>(.*?)</code></pre>",
    re.DOTALL,
)
# A number of a display, without the Markdown and the quoting around it.
_WORD = re.compile(r"[^\s*`_|()\[\]{},;:\"'<>]*\d[^\s*`_|()\[\]{},;:\"'<>]*")


def _text(html: str) -> str:
    """The text of an HTML fragment, with white space collapsed."""
    return " ".join(unescape(_TAG.sub(" ", html)).split())


def _tables(html: str) -> dict[str, tuple[list[str], list[list[str]]]]:
    """Every table of a page with a caption: its header and its rows."""
    found = {}
    for table in _TABLE.findall(html):
        caption = _CAPTION.search(table)
        if caption is None:
            continue
        header, rows = [], []
        for row in _ROW.findall(table):
            cells = _CELL.findall(row)
            if cells and all(kind == "h" for kind, _ in cells):
                header = [_text(cell) for _, cell in cells]
            elif cells:
                rows.append([_text(cell) for _, cell in cells])
        found[_text(caption.group(1))] = (header, rows)
    return found


def _widget(html: str, page_dir: Path, name: str) -> object | None:
    """The data of the widget ``name`` as the page carries it: in the page,
    or as its on-demand file."""
    embedded = re.search(
        rf'<script type="application/json" id="{re.escape(name)}-data">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if embedded is not None:
        return json.loads(embedded.group(1))
    asset = page_dir / "index_files" / "figure-html" / f"{name}.json"
    return json.loads(asset.read_text(encoding="utf-8")) if asset.is_file() else None


# --- The place of an inline number (#203) --------------------------------------
#
# A number the prose reads inline, `{python} result["name"]`, must be on the
# built page at its place: between the words that surround the expression in
# its paragraph of the source. A token found anywhere on the page is not
# enough, because a stale inline number whose new value also appears
# elsewhere ('24', '0.1') would pass.
#
# The rule. The place of an inline read is up to PLACE_WORDS words before
# the expression and up to PLACE_WORDS after it, within its block of the
# source (a paragraph, a heading, a table row, a caption line; a code cell,
# a div fence, and the front matter are no prose). A word is a run of
# letters of a token that holds no digit, so the numbers around it, which
# the page shows as values, never count, and the Markdown and the LaTeX of
# the source give the words the built page shows: math is shown as its
# LaTeX (the built page keeps it as the annotation of its MathML), emphasis
# and quotes are no letters. What rendering replaces by
# other words ends the place: a cross-reference or a citation, a link
# target, an attribute, the edge of a span or a link (a claim's span gets a
# label), and any other inline expression. The other inline
# reads of the block are written in as their recorded values. Every inline
# read of a value at a place is counted: the page must show the value at
# that place as often as the source reads it there.
#
# What the rule cannot see (false negatives): a number read only in a code
# cell (an f-string, a caption option), which keeps the rule "the token is
# on the page"; an inline read with no word around it in its block; and a
# stale value that is the same text as the new one at the same place.
# What could fail a correct page (false positives): rendering that changes
# the words next to an expression in a way the rule does not undo; the
# tests show the published lessons pass.
PLACE_WORDS = 3
_INLINE = re.compile(r"""`\{python\}\s*result\[["']([a-z0-9-]+)["']\]\s*`""")
_OTHER_INLINE = re.compile(r"`\{python\}[^`]*`")
_FENCE = re.compile(r"^(```|~~~)")
_BLOCK_LINE = re.compile(r"^\s*(#{1,6}\s|:::|: |\|)")
_BREAKS = [
    re.compile(r"\[?-?@[A-Za-z][\w:.-]*\]?"),  # cross-references, citations
    re.compile(r"\]\([^)]*\)"),  # a link target
    re.compile(r"(?<=[\]`])\{[^}]*\}|\s\{[#.][^}]*\}"),  # an attribute
    re.compile(r"\[\^[^\]]*\]"),  # a footnote mark
    # A span: rendering may add words at its edges (a claim's label).
    re.compile(r"[\[\]]"),
    re.compile(r"<!--.*?-->", re.DOTALL),
]
_TARGET, _BREAK = "\x00", "\x01"


_MATH = re.compile(r"<math\b.*?</math>", re.DOTALL)
_ANNOTATION = re.compile(
    r'<annotation encoding="application/x-tex">(.*?)</annotation>', re.DOTALL
)


def place_text(main: str) -> str:
    """The text of the built ``main`` as the rule of the place reads it: each
    formula as the LaTeX the source wrote, which the page keeps as the
    formula's annotation, not as the symbols of its MathML."""

    def latex(formula: re.Match) -> str:
        found = _ANNOTATION.search(formula.group(0))
        return f" {found.group(1)} " if found else " "

    return _text(_MATH.sub(latex, main))


def _words(text: str) -> list[str]:
    """The words of ``text``: the letter runs of its tokens without a digit."""
    return [
        word
        for token in text.split()
        if not any(c.isdigit() for c in token)
        for word in re.findall(r"[^\W\d_]+", token)
    ]


def _prose_blocks(source: str) -> list[str]:
    """The blocks of prose of a page source, without its front matter and its
    code cells."""
    if source.startswith("---\n"):
        end = source.find("\n---\n", 4)
        source = source[end + 5 :] if end != -1 else source
    blocks, current, fence = [], [], None
    for line in source.splitlines():
        if fence is not None:
            if line.strip().startswith(fence):
                fence = None
            continue
        opened = _FENCE.match(line.strip())
        if opened or not line.strip() or _BLOCK_LINE.match(line):
            if current:
                blocks.append("\n".join(current))
            current = []
            if opened:
                fence = opened.group(1)
            elif _BLOCK_LINE.match(line):
                blocks.append(line)
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def inline_places(source: str, numbers: dict[str, str]) -> Counter:
    """How often the prose of ``source`` reads each recorded number inline at
    each place: (words before, value, words after) to the count."""
    places: Counter = Counter()
    for block in _prose_blocks(source):
        reads = list(_INLINE.finditer(block))
        for target in reads:
            name = target.group(1)
            if name not in numbers:
                continue  # names_the_page_reads reports a name not recorded
            parts, last = [], 0
            for read in reads:
                parts.append(block[last : read.start()])
                if read is target:
                    parts.append(f" {_TARGET} ")
                else:
                    parts.append(f" {numbers.get(read.group(1), _BREAK)} ")
                last = read.end()
            parts.append(block[last:])
            text = _OTHER_INLINE.sub(f" {_BREAK} ", "".join(parts))
            for pattern in _BREAKS:
                text = pattern.sub(f" {_BREAK} ", text)
            before, after = text.split(_TARGET)
            before = _words(before.rsplit(_BREAK, 1)[-1])[-PLACE_WORDS:]
            after = _words(after.split(_BREAK, 1)[0])[:PLACE_WORDS]
            value = " ".join(numbers[name].split())
            places[(tuple(before), value, tuple(after))] += 1
    return places


def _token(value: str) -> re.Pattern:
    """A whole token of the page: 9.8 is not shown by 9.80665."""
    return re.compile(rf"(?<![\w.]){re.escape(value)}(?!\w|\.\d)")


def _words_before(text: str, end: int, count: int) -> list[str]:
    """The last ``count`` words of ``text[:end]``, read from a window that
    grows until it holds them, so a long page is not read again per token."""
    width = 256
    while True:
        start = max(0, end - width)
        window = text[start:end]
        if start > 0:  # the first token of the window may be cut
            window = window.partition(" ")[2]
        words = _words(window)
        if len(words) >= count or start == 0:
            return words[-count:] if count else []
        width *= 4


def _words_after(text: str, start: int, count: int) -> list[str]:
    """The first ``count`` words of ``text[start:]``, as _words_before."""
    width = 256
    while True:
        end = min(len(text), start + width)
        window = text[start:end]
        if end < len(text):  # the last token of the window may be cut
            window = window.rpartition(" ")[0]
        words = _words(window)
        if len(words) >= count or end == len(text):
            return words[:count]
        width *= 4


def shown_at(text: str, before: tuple, value: str, after: tuple) -> int:
    """How often the page text shows ``value`` between the words ``before``
    and ``after``."""
    count = 0
    for found in _token(value).finditer(text):
        ahead = _words_before(text, found.start(), len(before))
        behind = _words_after(text, found.end(), len(after))
        count += list(before) == ahead and list(after) == behind
    return count


def compare_with_page(
    results: Path, page: Path, source: Path | None = None
) -> list[str]:
    """What the experiment wrote into ``results`` that the built ``page`` does
    not show: a figure file that is not the page's byte for byte, a number,
    a table cell, a printed line, a display, or the data of a widget that
    differs at the precision the page shows. With the page's ``source``, a
    number the prose reads inline must be shown at its place (#203; above).
    Empty when they agree."""
    problems = []
    if not (results / RESULTS_FILE).is_file():
        return [f"the experiment wrote no {RESULTS_FILE}"]
    found = json.loads((results / RESULTS_FILE).read_text(encoding="utf-8"))
    html = page.read_text(encoding="utf-8")
    main = html[html.find("<main") : html.find("</main>")]
    text = _text(main)
    for name in found["figures"]:
        shown = (
            page.parent
            / "index_files"
            / "figure-html"
            / name.replace(".png", "-output-1.png")
        )
        written = results / name
        if not written.is_file():
            problems.append(f"the experiment wrote no {name}")
        elif not shown.is_file():
            problems.append(f"the page shows no figure {name}")
        elif written.read_bytes() != shown.read_bytes():
            problems.append(f"the figure {name} is not the page's, byte for byte")
    for name, value in found["numbers"].items():
        if not _token(" ".join(value.split())).search(text):
            problems.append(f"the number {name} = {value!r} is not on the page")
    if source is not None:
        text = place_text(main)
        places = inline_places(source.read_text(encoding="utf-8"), found["numbers"])
        values = {" ".join(v.split()): n for n, v in found["numbers"].items()}
        for (before, value, after), times in places.items():
            if not _token(value).search(text):
                continue  # reported above as not on the page
            if shown_at(text, before, value, after) < times:
                place = " ".join([*before, "…", *after])
                problems.append(
                    f"the number {values[value]} = {value!r} is not at its place"
                    f" on the page ({place!r})"
                )
    tables = _tables(main)
    for name, table in found["tables"].items():
        caption = " ".join(table["caption"].split())
        if caption not in tables:
            problems.append(f"the page shows no table {name} ({caption!r})")
            continue
        header, rows = tables[caption]
        if header != table["columns"]:
            problems.append(f"the header of the table {name} differs: {header}")
        if rows != table["rows"]:
            problems.append(f"the cells of the table {name} differ from the page's")
    printed = [unescape(block) for block in _OUTPUT.findall(main)]
    for name, value in found["outputs"].items():
        if value.rstrip("\n") not in (block.rstrip("\n") for block in printed):
            problems.append(f"the page does not print the output {name}")
    words = set(_WORD.findall(text))
    for name, value in found["displays"].items():
        missing = [word for word in _WORD.findall(value) if word not in words]
        if missing:
            problems.append(f"the display {name} shows what the page lacks: {missing}")
    for name in found["widgets"]:
        stem = name.removesuffix(".json")
        data = json.loads((results / name).read_text(encoding="utf-8"))
        if _widget(html, page.parent, stem) != data:
            problems.append(f"the data of the widget {stem} is not the page's")
    return problems


def split_footer_commands(commands: list[str]) -> tuple[str | None, list[str]]:
    """The experiment command of a page's footer and the commands after it
    that check proofs. A proof-only Lean lesson computes nothing: its footer
    has no ``uv sync``, so there is no experiment command (None) and all the
    commands after the clone are Lean's."""
    if "uv sync --locked --no-dev" not in commands:
        start = next(
            (i for i, c in enumerate(commands) if c == "cd lean"), len(commands)
        )
        return None, [c for c in commands[start:] if c != "cd lean"]
    setup = commands.index("uv sync --locked --no-dev")
    lean = [c for c in commands[setup + 2 :] if c != "cd lean"]
    return commands[setup + 1], lean
