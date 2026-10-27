"""The experiment of "Quantum tunnelling" (quantum 02)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.quantum_tunnelling"
PAGE = "quantum/02-quantum-tunnelling"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("quantum_tunnelling")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_transmission_is_the_closed_form_and_r_plus_t_is_one(results):
    _, found = results

    assert found["numbers"]["spectrum-gap"] == "below 1e-06"
    assert found["numbers"]["balance"] == "below 1e-06"
    for energy, closed, computed, reflected in found["tables"]["spectrum"]["rows"]:
        assert float(computed) == pytest.approx(float(closed), abs=1e-6)
        assert float(computed) + float(reflected) == pytest.approx(1.0, abs=2e-6)
        if float(energy) < 1.0:
            assert 0.0 < float(computed) < 0.5


def test_the_integration_is_fourth_order(results):
    _, found = results

    assert float(found["numbers"]["order"]) > 3.85


def test_the_packet_passes_with_the_averaged_transmission(results):
    _, found = results

    rows = found["tables"]["packet"]["rows"]
    gaps = [abs(float(row[4])) for row in rows]
    assert gaps[1] < 1e-4 and gaps[2] < gaps[0]
    for row in rows:
        assert float(row[2]) + float(row[3]) == pytest.approx(1.0, abs=1e-6)
