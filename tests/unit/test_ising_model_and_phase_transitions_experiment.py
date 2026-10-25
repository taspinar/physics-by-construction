"""The experiment of "Ising model and phase transitions" (thermodynamics 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.thermodynamics.experiments.ising_model_and_phase_transitions"
PAGE = "thermodynamics/04-ising-model-and-phase-transitions"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("ising_model_and_phase_transitions")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_sampler_finds_the_exact_averages_of_the_small_lattice(results):
    _, found = results

    assert float(found["numbers"]["exact-largest"]) < 4.0


def test_the_large_lattice_follows_onsager_below_tc(results):
    _, found = results

    assert float(found["numbers"]["onsager-largest"]) < 4.0


def test_the_crossings_approach_the_exact_critical_temperature_from_below(results):
    _, found = results

    deviations = [float(row[3]) for row in found["tables"]["crossings"]["rows"]]
    assert all(d < 0.0 for d in deviations)
    assert abs(deviations[-1]) < abs(deviations[0])
    assert abs(deviations[-1]) < 1.0  # per cent of the exact Tc


def test_the_susceptibility_peaks_move_towards_tc_with_size(results):
    _, found = results

    peaks = [float(row[1]) for row in found["tables"]["susceptibility-peaks"]["rows"]]
    assert peaks == sorted(peaks, reverse=True)
    assert peaks[0] > peaks[-1]
