"""The experiment of "RLC circuits and resonance" (electromagnetism 05)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.electromagnetism.experiments.rlc_circuits_and_resonance"
PAGE = "electromagnetism/05-rlc-circuits-and-resonance"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("rlc_circuits_and_resonance")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_step_responses_follow_the_closed_forms(results):
    _, found = results
    rows = found["tables"]["step-response"]["rows"]
    assert [row[0] for row in rows] == ["underdamped", "critical", "overdamped"]
    assert all(row[4] == "below 1e-09" for row in rows)
    # Only the underdamped circuit overshoots the step.
    assert float(rows[0][3]) > 1.5
    assert float(rows[1][3]) == pytest.approx(1.0, abs=1e-4)
    assert float(rows[2][3]) < 1.0


def test_the_simulated_resonance_curve_is_the_impedance_response(results):
    _, found = results
    for row in found["tables"]["resonance-curve"]["rows"]:
        assert float(row[1]) == pytest.approx(float(row[2]), rel=1e-4)
        assert float(row[3]) == pytest.approx(float(row[4]), abs=1e-3)
    assert found["numbers"]["amplitude-gap"] == "below 1e-09"


def test_the_peak_and_the_width_are_those_of_the_closed_forms(results):
    _, found = results
    rows = {
        row[0]: (float(row[1]), float(row[2]))
        for row in found["tables"]["resonance-measures"]["rows"]
    }
    assert rows["peak of the current"] == pytest.approx((1.0, 1.0), abs=1e-6)
    width = rows["half-power width"]
    assert width[0] == pytest.approx(width[1], abs=1e-6)
    # The width over omega_0 is 1 / Q.
    assert width[1] == pytest.approx(
        1 / float(found["numbers"]["quality-factor"]), rel=1e-3
    )
    capacitor = rows["peak of the capacitor voltage"]
    assert capacitor[0] == pytest.approx(capacitor[1], abs=1e-6)
    assert capacitor[0] < 0.999


def test_the_energy_lost_per_cycle_gives_q(results):
    _, found = results
    row = found["tables"]["energy-per-cycle"]["rows"][0]
    assert float(row[3]) == pytest.approx(float(row[4]), rel=1e-4)
