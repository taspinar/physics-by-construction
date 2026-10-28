"""The experiment of "Spin and Stern-Gerlach measurements" (quantum 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.spin_and_stern_gerlach"
PAGE = "quantum/04-spin-and-stern-gerlach"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("spin_and_stern_gerlach")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_quantum_atoms_land_in_two_spots_and_classical_ones_in_a_band(results):
    _, found = results

    quantum, classical = found["tables"]["screen"]["rows"]
    spot = float(found["numbers"]["spot"])
    assert float(quantum[2]) == pytest.approx(spot, rel=2e-3)
    assert float(quantum[3]) == 0.0
    assert float(classical[2]) == pytest.approx(spot / 2, rel=0.02)
    assert float(classical[3]) == pytest.approx(0.5, abs=0.02)


def test_the_sampled_fractions_follow_the_born_rule(results):
    _, found = results

    for _, fraction, born, error, deviation in found["tables"]["angles"]["rows"]:
        assert abs(float(fraction) - float(born)) <= 3.5 * float(error) + 5e-4
        assert abs(float(deviation)) < 3.5


def test_a_measurement_along_x_erases_the_z_result(results):
    _, found = results

    rows = {(row[0], row[1]): row for row in found["tables"]["sequence"]["rows"]}
    assert float(rows["z, z, z", "3"][3]) == 1.0
    assert float(rows["z, x, z", "3"][3]) == pytest.approx(0.5, abs=0.03)
