"""The experiment of "An interactive discovery benchmark" (agents-llm 11, EV2)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.interactive_discovery_benchmarks"
PAGE = "agents-llm/12-interactive-discovery-benchmarks"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("interactive_discovery_benchmarks")
    return directory, run_entry_point(MODULE, directory)


def _table(found: dict, name: str) -> list[list[str]]:
    return found["tables"][name]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_within_each_system_only_the_task_text_differs(results):
    _, found = results
    for environment, *shared in _table(found, "ev2-fairness"):
        assert shared[:-1] == ["same"] * (len(shared) - 1), environment
        assert shared[-1] == "differs"


def test_the_grid_is_scored_as_it_is_and_every_run_had_the_information(results):
    _, found = results
    scores = {(e, c): row[-2] for e, c, *row in _table(found, "ev2-scores")}
    assert len(scores) == 9
    assert {k for k, v in scores.items() if v != "recovered"} == {
        ("oscillator", "partial"),
        ("oscillator", "none"),
    }
    assert found["numbers"]["recovered"] == "7"
    assert {row[-1] for row in _table(found, "ev2-readings")} == {"yes"}


def test_the_check_refuses_comparisons_across_systems_and_worlds(results):
    _, found = results
    verdicts = dict(_table(found, "ev2-comparisons"))
    meaningful = [w for w, v in verdicts.items() if v == "comparable"]
    refused = {w: v for w, v in verdicts.items() if v != "comparable"}
    assert len(meaningful) == 2
    assert any("environments differ" in v for v in refused.values())
    assert any("hidden worlds differ" in v for v in refused.values())


def test_one_run_per_cell_cannot_tell_the_conditions_apart(results):
    _, found = results
    assert all(float(p) > 0.5 for _, p in _table(found, "ev2-chance"))


def test_the_diagram_task_is_scored_against_the_computed_key(results):
    _, found = results
    tally = {row[0]: row[1:] for row in _table(found, "ae2-item-tally")}
    assert set(tally) == {"reading", "concept", "physical tool", "counterfactual"}
    assert found["numbers"]["items-pictures"] == "9"
    assert found["numbers"]["items-text"] == "6"
    # Without the pictures, the readings fail and the concepts hold.
    assert tally["reading"][2] == "0"
    assert tally["concept"][2] == tally["concept"][0]
    assert tally["counterfactual"][2] == tally["counterfactual"][0]


def test_the_drawn_world_is_judged_like_the_grid(results):
    _, found = results
    world = {row[0]: row[1:] for row in _table(found, "ae2-world")}
    assert world["agent"][3] == "yes"
    assert world["grid + sparse identification"][3] == "no"
    for method, row in world.items():
        assert row[0] == found["numbers"]["budget"]
        if method != "agent":
            assert row[-1] == "comparable"
    assert {row[1] for row in _table(found, "ae2-withheld")} == {"yes"}
    verdicts = [v for _, v in _table(found, "ae2-world-comparisons")]
    assert verdicts[0] == "comparable"
    assert "hidden worlds differ" in verdicts[1]


def test_the_baselines_spread_over_seeds_and_worlds(results):
    _, found = results
    spread = {row[0]: row[2:] for row in _table(found, "ae2-world-spread")}
    runs, recovered = map(
        int, spread["random + least squares, other seeds of the probes"]
    )
    assert 0 < recovered < runs
    assert spread["grid + sparse identification"][1] == "0"
