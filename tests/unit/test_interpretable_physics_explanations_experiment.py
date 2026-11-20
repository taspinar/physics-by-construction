"""The experiment of "A prediction and its explanation" (agents-llm 15, AI7)."""

import re
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.interpretable_physics_explanations"
PAGE = "agents-llm/17-interpretable-physics-explanations"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("interpretable_physics_explanations")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_recorded_run_passes_every_test(results):
    _, found = results
    for row in found["tables"]["ai7-explanations"]["rows"]:
        assert row[4:] == ["yes"] * 6


def test_the_curve_fit_misses_only_the_counterfactual(results):
    _, found = results
    fit = {row[0]: row[3] for row in found["tables"]["ai7-baselines"]["rows"]}
    assert fit["3"].endswith("(outside)")
    assert all(fit[n].endswith("(within)") for n in ("1", "2", "4"))


def test_dimensional_analysis_leaves_the_history_undecided(results):
    _, found = results
    forms = {row[0]: row[4] for row in found["tables"]["ai7-baselines"]["rows"]}
    assert forms["1"] == "v = m g / b" and forms["2"] == "tau = m / b"
    assert forms["4"].startswith("not identified")


def test_the_constructed_answers_fail_where_the_page_says(results):
    _, found = results
    rows = found["tables"]["ai7-examples"]["rows"]
    # prediction, dimensions, physics, support
    assert rows[0][3:] == ["yes", "yes", "no", "no"]
    assert rows[1][3:] == ["no", "yes", "yes", "no"]
    assert rows[2][3:] == ["yes", "no", "no", "no"]


# --- The experiment report (SA8). ---

PAGE_FILE = Path(__file__).parents[2] / "site/lessons" / PAGE / "index.qmd"


def test_every_statement_resolves_to_a_record_or_is_marked(results):
    _, found = results
    rows = found["tables"]["report-statements"]["rows"]

    assert {row[2] for row in rows} == {"observed", "computed", "proposed"}
    for _, _, kind, status in rows:
        if kind == "proposed":
            assert status == "proposed, not evaluated"
        else:
            assert status == "completed"


def test_every_traced_statement_names_runs_figures_assumptions_and_uncertainty(
    results,
):
    _, found = results
    kinds = {row[0]: row[2] for row in found["tables"]["report-statements"]["rows"]}
    labels = set(re.findall(r"^#\|\s*label:\s*(\S+)\s*$", PAGE_FILE.read_text(), re.M))
    for id_, runs, data, shown, assumptions, uncertainty in found["tables"][
        "report-traces"
    ]["rows"]:
        if kinds[id_] == "proposed":
            assert (runs, data, shown, assumptions) == ("none",) * 4
            continue
        assert runs != "none" and uncertainty != "none"
        assert set(shown.split(", ")) <= labels
        assert all(1 <= int(a) <= 5 for a in assumptions.split(", "))
        if kinds[id_] == "observed":
            assert data == "replay.json"


def test_the_run_record_holds_the_assumptions_of_the_page():
    from pbc.agents.explanation_lab import PREDICTION_TOLERANCE
    from pbc.mechanics.experiments.interpretable_physics_explanations import (
        ASSUMPTIONS,
    )

    page = PAGE_FILE.read_text()
    section = page.split("## Assumptions", 1)[1].split("\n## ", 1)[0]
    headings = re.findall(r"^\d+\. \*\*(.+?)\*\*", section, re.M | re.S)
    tolerance = '`{python} result["prediction-tolerance"]`'
    percent = f"{100 * PREDICTION_TOLERANCE:.0f}"
    headings = [" ".join(h.replace(tolerance, percent).split()) for h in headings]

    assert headings == list(ASSUMPTIONS)


def test_a_changed_recording_withdraws_what_rests_on_it(results):
    _, found = results
    rows = {row[0]: row[1:] for row in found["tables"]["report-changed"]["rows"]}

    for _kind, before, _after in rows.values():
        assert before in ("completed", "proposed, not evaluated")
    assert rows["answers"][2] == rows["interval"][2] == "not evaluated"
    assert rows["fit"][2] == rows["dimensions"][2] == "completed"
    assert rows["harder-scene"][2] == "proposed, not evaluated"
