"""The experiment of "Molecular dynamics" (thermodynamics 05)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.thermodynamics.experiments.molecular_dynamics"
PAGE = "thermodynamics/05-molecular-dynamics"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("molecular_dynamics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_energy_error_is_of_second_order_without_drift(results):
    _, found = results

    assert float(found["numbers"]["energy-order"]) == pytest.approx(2.0, abs=0.2)
    assert float(found["numbers"]["drift-ratio"]) < 1.0


def test_the_species_and_the_directions_share_one_temperature(results):
    _, found = results

    assert float(found["numbers"]["species-distance"]) < 4.0
    assert float(found["numbers"]["axes-distance"]) < 4.0


def test_too_large_a_step_fails(results):
    _, found = results

    rows = found["tables"]["larger-steps"]["rows"]
    assert rows[-1][1].startswith("above 1")
    assert float(rows[0][1]) < float(rows[1][1]) < 1.0
