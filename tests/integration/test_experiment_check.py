"""The experiment check reports an experiment whose output is not the page's
(ADR 016 decision 4, F117).

The check of the built site runs every selected lesson's experiment with the
reader's commands and compares what it wrote with the built page
(``support.experiments.compare_with_page``). Here a page is built by hand from
what the experiment of the lesson template writes, so the two agree; each
case then changes one thing on one side, and the comparison must say so. A
lesson without an experiment fails the lesson source checks, which
test_lesson_checks.py shows.
"""

import json
import shutil
from html import escape
from pathlib import Path

import pytest
from support.experiments import compare_with_page, inline_places, run_entry_point

MODULE = "pbc.mechanics.experiments.lesson_template"


def _page(results: Path, page: Path) -> None:
    """A built page that shows everything the experiment recorded."""
    found = json.loads((results / "results.json").read_text())
    figures = page.parent / "index_files" / "figure-html"
    figures.mkdir(parents=True)
    for name in found["figures"]:
        shutil.copy(results / name, figures / name.replace(".png", "-output-1.png"))
    numbers = "".join(f"<p>It is {escape(v)} m.</p>" for v in found["numbers"].values())
    printed = "".join(
        '<div class="cell-output cell-output-stdout">'
        f"<pre><code>{escape(text)}</code></pre></div>"
        for text in found["outputs"].values()
    )
    page.write_text(f"<html><body><main>{numbers}{printed}</main></body></html>")


@pytest.fixture
def lesson(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results"
    run_entry_point(MODULE, results)
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir()
    _page(results, page)
    return results, page


def _change(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


def test_an_experiment_that_agrees_with_its_page_passes(lesson):
    assert compare_with_page(*lesson) == []


def test_a_changed_number_fails(lesson):
    results, page = lesson
    _change(results / "results.json", '"2.000"', '"2.001"')

    assert compare_with_page(results, page) == [
        "the number exact-position = '2.001' is not on the page"
    ]


def test_a_changed_figure_fails(lesson):
    results, page = lesson
    figure = results / "fig-replace-with-a-name.png"
    figure.write_bytes(figure.read_bytes() + b"\0")

    problems = compare_with_page(results, page)

    assert problems == [
        "the figure fig-replace-with-a-name.png is not the page's, byte for byte"
    ]


def test_changed_printed_output_fails(lesson):
    results, page = lesson
    _change(page, "largest error: 0.", "largest error: 9.")

    assert compare_with_page(results, page) == [
        "the page does not print the output largest-error"
    ]


def test_a_changed_table_cell_fails(lesson):
    results, page = lesson
    found = json.loads((results / "results.json").read_text())
    found["tables"]["errors"] = {
        "caption": "Errors.",
        "columns": ["t (s)", "error (m)"],
        "rows": [["0.5", "0.125"]],
    }
    (results / "results.json").write_text(json.dumps(found))
    table = (
        "<table><caption>Errors.</caption><thead><tr><th>t (s)</th>"
        "<th>error (m)</th></tr></thead><tbody><tr><td>0.5</td><td>0.126</td>"
        "</tr></tbody></table>"
    )
    _change(page, "</main>", f"{table}</main>")

    assert compare_with_page(results, page) == [
        "the cells of the table errors differ from the page's"
    ]


# --- An inline number at its place (#203) -------------------------------------

SOURCE = """\
---
title: "A lesson"
lesson:
  id: a-lesson
---

The ball is at `{python} result["exact-position"]` m after the fall. The
second ball starts 3.000 m away.

```{python}
#| echo: false
print(result["exact-position"])
```
"""
PAGE = (
    "<html><body><main><h1>A lesson</h1>"
    "<p>The ball is at {value} m after the fall. The second ball starts 3.000 m"
    " away.</p></main></body></html>"
)


@pytest.fixture
def placed(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A page that shows the number of the lesson template at the place where
    its source reads it, and the same digits elsewhere."""
    results = tmp_path / "results"
    run_entry_point(MODULE, results)
    found = json.loads((results / "results.json").read_text())
    found["outputs"], found["figures"] = {}, []
    (results / "results.json").write_text(json.dumps(found))
    page = tmp_path / "site" / "index.html"
    page.parent.mkdir()
    page.write_text(PAGE.format(value="2.000"))
    source = tmp_path / "index.qmd"
    source.write_text(SOURCE)
    return results, page, source


def test_an_inline_number_at_its_place_passes(placed):
    assert compare_with_page(*placed) == []


def test_a_changed_inline_number_whose_value_is_elsewhere_on_the_page_fails(placed):
    # The experiment now gives 3.000; the page still shows 2.000 where the
    # prose reads the number, and 3.000 only in another sentence.
    results, page, source = placed
    _change(results / "results.json", '"2.000"', '"3.000"')

    # A token anywhere on the page, the rule before #203, lets it pass.
    assert compare_with_page(results, page) == []
    assert compare_with_page(results, page, source) == [
        "the number exact-position = '3.000' is not at its place on the page"
        " ('ball is at … m after the')"
    ]


def test_an_inline_number_shown_at_another_place_only_fails(placed):
    results, page, source = placed
    page.write_text(PAGE.format(value="1.000").replace("starts 3.000", "starts 2.000"))

    assert compare_with_page(results, page, source) == [
        "the number exact-position = '2.000' is not at its place on the page"
        " ('ball is at … m after the')"
    ]


def test_an_absent_inline_number_is_reported_once(placed):
    results, page, source = placed
    _change(results / "results.json", '"2.000"', '"2.001"')

    assert compare_with_page(results, page, source) == [
        "the number exact-position = '2.001' is not on the page"
    ]


def test_a_number_read_twice_at_one_place_must_be_shown_twice(placed):
    results, page, source = placed
    twice = 'The ball is at `{python} result["exact-position"]` m after the fall.'
    source.write_text(SOURCE.replace("away.", f"away.\n\n{twice}\n\n{twice}", 1))
    once = "<p>The ball is at 2.000 m after the fall.</p>"
    page.write_text(PAGE.format(value="2.000").replace("</main>", f"{once}</main>"))
    problems = compare_with_page(results, page, source)
    assert problems and "is not at its place" in problems[0]

    page.write_text(
        PAGE.format(value="2.000").replace("</main>", f"{once}{once}</main>")
    )
    assert compare_with_page(results, page, source) == []


def test_the_rendering_of_the_prose_keeps_a_number_at_its_place(placed):
    # What the false positives of the rule would come from: math, which the
    # page shows as MathML with the LaTeX as its annotation; a claim, whose
    # span gets a label; a cross-reference and a link, which rendering
    # rewrites; emphasis and curly quotes; and the other inline numbers of
    # the paragraph, which the page shows as their values.
    results, page, source = placed
    found = json.loads((results / "results.json").read_text())
    found["numbers"]["drop"] = "below 1e-12"
    (results / "results.json").write_text(json.dumps(found))
    source.write_text(
        SOURCE.replace(
            "The ball is at",
            "As @fig-fall shows and [the notes](https://example.org) say,"
            " [the *ball's* height $h$ is"
            ' `{python} result["drop"]`]{.claim type="numerically-verified"}'
            " and the ball is at",
        )
    )
    math = (
        '<math display="inline"><semantics><mi>h</mi>'
        '<annotation encoding="application/x-tex">h</annotation></semantics></math>'
    )
    page.write_text(
        PAGE.format(value="2.000").replace(
            "The ball is at",
            "As Figure 1 shows and <a href='x'>the notes</a> say, Numerically"
            f" verified (here) : the <em>ball\u2019s</em> height {math} is below"
            " 1e-12 and the ball is at",
        )
    )
    assert compare_with_page(results, page, source) == []
    assert (("height", "h", "is"), "below 1e-12", ()) in inline_places(
        source.read_text(), found["numbers"]
    )
    # And the place still binds: a stale value there fails, also when the
    # new value is on the page elsewhere.
    stale = page.read_text().replace("is below 1e-12", "is below 1e-11")
    page.write_text(
        stale.replace("</main>", "<p>Elsewhere it is below 1e-12.</p></main>")
    )
    assert compare_with_page(results, page, source) == [
        "the number drop = 'below 1e-12' is not at its place on the page"
        " ('height h is …')"
    ]


def test_the_places_come_from_the_prose_only():
    numbers = {"exact-position": "2.000"}
    places = inline_places(SOURCE, numbers)
    # The read in the code cell has no place; it keeps the rule "the token is
    # on the page" (a false negative of the rule, written in its comment).
    assert places == {(("ball", "is", "at"), "2.000", ("m", "after", "the")): 1}
    # A read with no word around it in its block has an empty place, which
    # any occurrence of the value meets.
    lone = inline_places('Text.\n\n`{python} result["exact-position"]`\n', numbers)
    assert lone == {((), "2.000", ()): 1}


def test_an_experiment_that_wrote_nothing_fails(lesson, tmp_path: Path):
    _, page = lesson

    assert compare_with_page(tmp_path / "nothing", page) == [
        "the experiment wrote no results.json"
    ]


def test_a_proof_only_footer_has_no_experiment_to_run():
    from support.experiments import split_footer_commands

    proof = [
        "git clone https://example.org/r.git",
        "cd r",
        "git checkout abc",
        "cd lean",
        "lake exe cache get",
        "lake build PBC.Lesson",
    ]
    assert split_footer_commands(proof) == (
        None,
        ["lake exe cache get", "lake build PBC.Lesson"],
    )
    both = [
        *proof[:3],
        "uv sync --locked --no-dev",
        "uv run --locked --no-dev python -m m results",
        *proof[3:],
    ]
    assert split_footer_commands(both) == (
        "uv run --locked --no-dev python -m m results",
        ["lake exe cache get", "lake build PBC.Lesson"],
    )
