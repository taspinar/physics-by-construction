from html.parser import HTMLParser

import numpy as np
import pytest

from pbc.authoring import is_numeric_console_block, table

COLUMNS = [("steps", "", "d"), ("time step", "s", ".3f"), ("ratio", "", ".2f")]


class Cells(HTMLParser):
    """The text of each header cell and data cell, with its attributes."""

    def __init__(self, markup):
        super().__init__()
        self.cells = []
        self._open = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag in ("th", "td"):
            self._open = [tag, dict(attrs), ""]

    def handle_data(self, data):
        if self._open:
            self._open[2] += data

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self.cells.append(tuple(self._open))
            self._open = None


def markup(**changes):
    arguments = {
        "rows": [(6, 0.4, None), (12, np.float64(0.2), 2.0)],
        "columns": COLUMNS,
        "caption": "Time steps.",
    } | changes
    return table(**arguments).markup


def test_headers_carry_scope_and_unit_and_cells_the_stated_precision():
    cells = Cells(markup()).cells

    assert [(t, a.get("scope"), x) for t, a, x in cells[:3]] == [
        ("th", "col", "steps"),
        ("th", "col", "time step (s)"),
        ("th", "col", "ratio"),
    ]
    assert [x for _t, _a, x in cells[3:]] == ["6", "0.400", "", "12", "0.200", "2.00"]


def test_numbers_are_right_aligned_and_text_is_not():
    cells = Cells(
        markup(rows=[("a", 1.0, 2.0)], columns=[("k", "", ""), *COLUMNS[1:]])
    ).cells

    assert [a.get("class") for _t, a, _x in cells] == [None, "num", "num"] * 2


def test_the_caption_is_in_the_table_and_names_the_scrolling_box():
    html = markup(caption="Error <m> & more")

    assert "<caption>Error &lt;m&gt; &amp; more</caption>" in html
    assert 'aria-label="Error &lt;m&gt; &amp; more"' in html
    assert 'tabindex="0"' in html


@pytest.mark.parametrize(
    "changes",
    [
        {"caption": " "},
        {"columns": []},
        {"rows": [(1, 2.0)]},
    ],
)
def test_a_table_without_caption_or_columns_or_with_a_ragged_row_is_refused(changes):
    with pytest.raises(ValueError):
        markup(**changes)


def test_a_cell_result_passes_the_markup_through_as_raw_html():
    assert (
        table([(1, 0.5, 1.0)], COLUMNS, "C")
        ._repr_markdown_()
        .startswith("```{=html}\n<div")
    )


PRINTED = """ steps    time step (s)    error (m)
    24         0.100000     0.000000
    48         0.050000    -0.058860
"""


def test_the_check_flags_a_console_block_of_numbers():
    assert is_numeric_console_block(PRINTED)


def test_the_check_accepts_a_table_and_ordinary_output():
    cell = table([(6, 0.4, 1.0), (12, 0.2, 2.0)], COLUMNS, "Time steps.")
    assert not is_numeric_console_block(cell._repr_markdown_())
    assert not is_numeric_console_block(cell.markup)
    assert not is_numeric_console_block("largest time step: 12.3 microseconds\n")
    assert not is_numeric_console_block(
        "steps needed:      7\nerror with them:   0.5 mm\n"
    )
    assert not is_numeric_console_block("")
