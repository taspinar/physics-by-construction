"""The experiment of "Unknown physical worlds" (agents-llm 15)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.unknown_physical_worlds"
PAGE = "agents-llm/15-unknown-physical-worlds"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("unknown_physical_worlds")
    return directory, run_entry_point(MODULE, directory)


def _rows(found: dict, name: str) -> dict[str, list[str]]:
    return {row[0]: row[1:] for row in found["tables"][name]["rows"]}


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_least_squares_recovers_and_newton_and_whole_powers_fail(results):
    _, found = results
    baselines = _rows(found, "d5-baselines")
    assert baselines["random + least squares"][3] == "yes"
    assert baselines["random + Newton's gravity"][2:4] == ["no", "no"]
    assert baselines["random + sparse identification"][2:4] == ["no", "no"]
    # The sparse sum dropped a pair altogether.
    assert {t.split()[0] for t in _rows(found, "d5-sparse")} != {"k12", "k13", "k23"}


def test_the_agent_recovers_with_a_repulsive_pair_and_an_exponent_not_two(results):
    _, found = results
    score = _rows(found, "d5-score")
    assert found["numbers"]["outcome"] == score["outcome"][0] == "recovered"
    assert float(score["claimed k13"][0]) < 0
    assert float(score["claimed exponent"][0]) != 2
    assert found["numbers"]["agent-fit-consistent"] == "yes"
    for fit, claimed in _rows(found, "d5-agent-readings").values():
        assert float(claimed) == pytest.approx(float(fit), abs=0.01)


def test_the_couplings_are_not_proportional_to_the_masses(results):
    _, found = results
    ratios = [float(row[-1]) for row in found["tables"]["coupling-ratios"]["rows"]]
    assert max(ratios) - min(ratios) > 0.1 and min(ratios) < 0
    assert all(row[-1] == "yes" for row in found["tables"]["budget-scan"]["rows"])
