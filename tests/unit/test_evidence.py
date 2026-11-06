"""Reading the claims of a lesson for the evidence map."""

import platform
import subprocess

import pytest

from pbc.authoring import evidence
from pbc.authoring.evidence import COMPUTED, Evidence, cell_labels, read_claims

PAGE = "lessons/mechanics/01-sample/index.qmd"

SOURCE = """\
---
title: "Sample"
---

```{python}
#| label: result
claim = "[Not a claim]{.claim type='observational'}"
```

[The energy is `{python} f"{energy:.1f}"` J, or $a | b$ for
[a value]{.not-verified}.]{.claim type="numerically-verified"
scope="one step" evidence="result, euler-error  card"}

::: {.claim type="formal-theorem"}
First paragraph.

Second paragraph.
:::
"""


def test_claims_are_read_in_document_order_with_their_attributes():
    first, second = read_claims(PAGE, SOURCE)

    assert (first.number, first.anchor) == (1, "claim-1")
    assert first.type == "numerically-verified"
    assert first.scope == "one step"
    assert first.evidence == ("result", "euler-error", "card")
    assert (second.number, second.type, second.evidence) == (2, "formal-theorem", ())


def test_a_claim_in_a_code_cell_is_no_claim():
    assert len(read_claims(PAGE, SOURCE)) == 2


def test_a_statement_hides_computed_values_and_marks_unverified_text():
    first, second = read_claims(PAGE, SOURCE)

    assert COMPUTED in first.statement
    assert "energy:" not in first.statement
    assert "a value (not verified)" in first.statement
    # A pipe would end the cell of the table the statement goes into.
    assert "a \\| b" in first.statement
    assert second.statement == "First paragraph. Second paragraph."


def test_only_labelled_executed_python_cells_are_evidence():
    text = (
        "```{python}\n#| label: ran\nx = 1\n```\n\n"
        "```{python}\n#| label: skipped\n#| eval: false\nx = 1\n```\n\n"
        "```{python}\nx = 2\n```\n\n"
        "```{r}\n#| label: other-engine\n```\n"
    )

    assert cell_labels(text) == {"ran"}


def test_a_replay_is_linked_at_its_repository_path_also_from_a_copy_of_the_site(
    tmp_path,
):
    # The determinism check builds a copy of the site outside the repository.
    copy = tmp_path / "copy"
    lesson = copy / "lessons" / "agents-llm" / "01-sample"
    lesson.mkdir(parents=True)
    (lesson / "index.qmd").write_text(SOURCE)
    (lesson / "replay-full.json").write_text("{}")
    evidence = Evidence(site=copy)
    page = "lessons/agents-llm/01-sample/index.qmd"
    found = evidence.resolve(page, "replay-full")
    assert found is not None and found.kind == "replay"
    assert found.href.endswith("/site/lessons/agents-llm/01-sample/replay-full.json")
    assert evidence.resolve(page, "replay") is None


def _run_result(returncode: int = 0, stdout: str = "{}", stderr: str = ""):
    def run(command, **kwargs):
        run.commands.append(command)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    run.commands = []
    return run


def test_pandoc_is_started_directly_when_the_package_ships_it(monkeypatch):
    run = _run_result()
    monkeypatch.setattr(evidence, "_bundled_pandoc", lambda: "/pkg/tools/pandoc")
    monkeypatch.setattr(evidence.subprocess, "run", run)

    assert evidence._pandoc(["--to", "json"], "text") == "{}"
    assert run.commands == [["/pkg/tools/pandoc", "--to", "json"]]


def test_pandoc_falls_back_to_quarto_when_the_package_has_none(monkeypatch):
    run = _run_result()
    monkeypatch.setattr(evidence, "_bundled_pandoc", lambda: None)
    monkeypatch.setattr(evidence.subprocess, "run", run)

    evidence._pandoc(["--to", "json"], "text")

    assert run.commands == [["quarto", "pandoc", "--to", "json"]]


def test_a_failing_pandoc_still_names_the_lesson_it_could_not_read(monkeypatch):
    monkeypatch.setattr(evidence, "_bundled_pandoc", lambda: "/pkg/tools/pandoc")
    monkeypatch.setattr(
        evidence.subprocess, "run", _run_result(1, stderr="bad markdown")
    )

    with pytest.raises(RuntimeError, match="pandoc could not read a lesson: bad"):
        evidence._pandoc([], "text")


def test_the_package_ships_a_pandoc_on_the_machines_the_project_supports():
    evidence._bundled_pandoc.cache_clear()
    machine = platform.machine()
    if machine not in evidence._PANDOC_DIRECTORIES:
        return  # a machine without a directory of its own uses quarto pandoc

    assert evidence._bundled_pandoc() is not None


def test_the_claims_are_the_same_through_the_bundled_pandoc_and_through_quarto(
    monkeypatch,
):
    through_bundle = read_claims(PAGE, SOURCE)
    monkeypatch.setattr(evidence, "_bundled_pandoc", lambda: None)
    through_quarto = read_claims(PAGE, SOURCE)

    assert through_bundle and through_bundle == through_quarto


def test_the_whole_site_gives_the_same_claims_through_both_ways(monkeypatch):
    """Criterion 1 of Issue 388: every claim of every lesson, both ways."""
    assert evidence.lesson_pages(evidence.REPOSITORY_ROOT / "site")
    evidence._bundled_pandoc.cache_clear()
    assert evidence._bundled_pandoc() is not None
    through_bundle = evidence.read_all()
    monkeypatch.setattr(evidence, "_bundled_pandoc", lambda: None)
    through_quarto = evidence.read_all()

    assert through_bundle and through_bundle == through_quarto
