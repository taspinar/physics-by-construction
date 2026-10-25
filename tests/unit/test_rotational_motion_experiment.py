"""The experiment of "Rotational motion, torque, and angular momentum"
(mechanics 19)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.rotational_motion"
PAGE = "mechanics/19-rotational-motion"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("rotational-motion")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_disc_converges_to_its_closed_form_and_the_parallel_axis_holds(results):
    _, found = results

    assert float(found["numbers"]["disc-order"]) == pytest.approx(2.0, abs=0.05)
    assert found["numbers"]["parallel-gap"] == "below 1e-12"


def test_the_torque_energy_and_angular_momentum_checks_hold(results):
    _, found = results
    rows = {row[0]: row[1] for row in found["tables"]["conservation"]["rows"]}

    assert float(rows["dL/dt by central differences against the torque"]) < 1e-4
    assert float(rows["energy"]) < 1e-6
    assert rows["vertical component of L"] == "below 1e-12"
    assert float(rows["component of L along the axis"]) < 1e-6


def test_the_precession_rate_converges_to_the_fast_top_limit(results):
    _, found = results
    rows = found["tables"]["precession"]["rows"]

    differences = [float(row[4]) for row in rows]
    assert differences == sorted(differences, reverse=True)
    assert differences[-1] < 5e-3
    assert float(found["numbers"]["precession-power"]) == pytest.approx(2.0, abs=0.1)
    # The fast spins also agree with the slow steady rate.
    assert float(rows[-1][1]) == pytest.approx(float(rows[-1][2]), rel=1e-3)


def test_steady_precession_and_the_unit_check(results):
    _, found = results

    assert found["numbers"]["steady-difference"] == "below 1e-06"
    assert found["numbers"]["units-difference"] == "below 1e-09"


def test_a_longer_arm_about_doubles_the_rate(results):
    _, found = results

    assert 2.0 < float(found["numbers"]["arm-ratio"]) < 2.3
    for row in found["tables"]["tilted-spin"]["rows"]:
        assert row[1] == row[2]
