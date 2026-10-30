"""The experiment of "A prediction and its explanation" (agents-llm 15, AI7)."""

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
