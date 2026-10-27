"""The experiment of "The quantum harmonic oscillator" (quantum 03)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.quantum_harmonic_oscillator"
PAGE = "quantum/03-the-quantum-harmonic-oscillator"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("quantum_harmonic_oscillator")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_levels_are_the_spectrum_with_the_predicted_error(results):
    _, found = results

    for n, energy, exact, error, predicted, _ in found["tables"]["levels"]["rows"]:
        assert float(exact) == int(n) + 0.5
        assert float(energy) - float(exact) == pytest.approx(float(error), abs=2e-6)
        assert float(error) == pytest.approx(float(predicted), rel=2e-3)


def test_the_eigenvalues_converge_at_order_two(results):
    _, found = results

    for n in (0, 2, 5):
        assert float(found["numbers"][f"order-{n}"]) == pytest.approx(2.0, abs=0.05)
    ratios = [float(row[-1]) for row in found["tables"]["convergence"]["rows"]]
    assert ratios == sorted(ratios, reverse=True)
    assert ratios[-1] == pytest.approx(1.0, abs=1e-3)


def test_close_walls_raise_the_levels(results):
    _, found = results

    rows = found["tables"]["walls"]["rows"]
    assert all(float(value) > 0 for value in rows[0][1:])
    assert all(float(value) < 0 for value in rows[-1][1:])
