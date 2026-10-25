"""The experiment of "Nonlinear dynamics and bifurcations" (mechanics 18)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.nonlinear_dynamics_and_bifurcations"
PAGE = "mechanics/18-nonlinear-dynamics-and-bifurcations"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("nonlinear-dynamics-and-bifurcations")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_diagram_brackets_the_known_threshold_and_follows_the_branch(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["below"]) < float(numbers["omega-c"]) < float(numbers["above"])
    assert numbers["branch-gap"] == "below 1e-06"
    for row in found["tables"]["bifurcation-diagram"]["rows"]:
        assert float(row[3]) == pytest.approx(float(row[2]), abs=1e-4)
        assert float(row[4]) == pytest.approx(-float(row[2]), abs=1e-4)


def test_the_decay_is_linear_below_the_threshold_and_algebraic_at_it(results):
    _, found = results

    for row in found["tables"]["near-threshold"]["rows"]:
        assert row[1] == row[2]
    rates = [float(row[1]) for row in found["tables"]["near-threshold"]["rows"]]
    assert rates == sorted(rates, reverse=True)
    assert float(found["numbers"]["slope-difference"]) < 1e-2


def test_the_limit_cycle_grows_from_zero_as_twice_the_root_of_mu(results):
    _, found = results

    assert abs(float(found["numbers"]["hopf-threshold"])) < 1e-3
    assert float(found["numbers"]["hopf-slope"]) == pytest.approx(4.0, abs=0.01)


def test_linearisation_holds_for_small_motion_and_fails_near_the_threshold(results):
    _, found = results

    assert float(found["numbers"]["tilted-difference"]) < 1e-3
    assert float(found["numbers"]["near-small"]) == pytest.approx(1.0, abs=0.01)
    assert float(found["numbers"]["near-large"]) < 0.9
