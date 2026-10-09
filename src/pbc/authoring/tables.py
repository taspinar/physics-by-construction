"""Numeric results as semantic tables.

A lesson shows a computed result with ``table``, called from a code cell that
the build executes, so the numbers on the page are computed, not typed
(ADR 002). The table has a caption, header cells that carry the unit, and
numbers formatted at a stated precision. ``docs/authoring.md`` ("Numbers")
gives the rule a result table follows; ``is_numeric_console_block`` is the
check for a cell that breaks it.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from html import escape
from numbers import Real

from pbc.authoring.widgets import _raw_html

# A column is (name, unit, format): ``unit`` is empty for a quantity without
# one, and ``format`` is a format specification such as ".3f" or "d".
Column = tuple[str, str, str]


def _is_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _header(name: str, unit: str, numeric: bool) -> str:
    label = escape(name) + (f" ({escape(unit)})" if unit else "")
    align = ' class="num"' if numeric else ""
    return f'<th scope="col"{align}>{label}</th>'


def _cell(value: object, spec: str) -> str:
    if value is None:
        return "<td></td>"
    text = escape(format(value, spec))
    return f'<td class="num">{text}</td>' if _is_number(value) else f"<td>{text}</td>"


def table_markup(
    rows: Iterable[Sequence[object]], columns: Sequence[Column], caption: str
) -> str:
    """The HTML of a table of ``rows`` with one cell per column. A cell that is
    ``None`` is left empty."""
    if not caption.strip():
        raise ValueError("a result table needs a caption")
    if not columns:
        raise ValueError("a result table needs at least one column")
    body = [list(row) for row in rows]
    for row in body:
        if len(row) != len(columns):
            raise ValueError(
                f"a row has {len(row)} cells but the table has {len(columns)} columns"
            )
    numeric = [any(_is_number(row[i]) for row in body) for i in range(len(columns))]
    head = "".join(
        _header(name, unit, numeric[i]) for i, (name, unit, _) in enumerate(columns)
    )
    lines = [
        # A table wider than the screen scrolls inside this box, which a
        # keyboard reaches because it is focusable (docs/authoring.md).
        f'<div class="table-scroll" role="region" tabindex="0" '
        f'aria-label="{escape(caption, quote=True)}">',
        '<table class="result-table">',
        f"<caption>{escape(caption)}</caption>",
        f"<thead><tr>{head}</tr></thead>",
        "<tbody>",
    ]
    for row in body:
        cells = "".join(_cell(value, columns[i][2]) for i, value in enumerate(row))
        lines.append(f"<tr>{cells}</tr>")
    lines += ["</tbody>", "</table>", "</div>"]
    return "\n".join(lines)


@dataclass(frozen=True)
class ResultTable:
    """As the result of a code cell it renders a semantic table."""

    markup: str

    def _repr_markdown_(self) -> str:
        return _raw_html(self.markup)


def table(
    rows: Iterable[Sequence[object]], columns: Sequence[Column], caption: str
) -> ResultTable:
    """A table of ``rows`` with a ``caption`` and one ``(name, unit, format)``
    per column.

    Call it as the last expression of a cell with ``#| echo: false`` or, to
    show the code, without. The sentence that says what the reader should
    conclude follows in the text.
    """
    return ResultTable(table_markup(rows, columns, caption))


_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def is_numeric_console_block(output: str) -> bool:
    """Whether ``output``, the text of a cell's output (what it printed, or the
    markdown a ``table`` cell yields, which is never flagged), is a fixed-width
    block of numbers: two or more lines that each hold two or more numbers. A result
    in that form belongs in ``table``. One line, or a line of prose with a
    single number in it, is not flagged."""
    numeric_lines = 0
    for line in output.splitlines():
        tokens = line.split()
        if sum(1 for token in tokens if _NUMBER.fullmatch(token)) >= 2:
            numeric_lines += 1
    return numeric_lines >= 2
