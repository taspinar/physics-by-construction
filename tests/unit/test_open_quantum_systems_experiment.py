"""The experiment of "Open quantum systems and decoherence" (quantum 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.open_quantum_systems"
PAGE = "quantum/06-open-quantum-systems"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("open_quantum_systems")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_exponential_integrator_keeps_trace_and_positivity(results):
    _, found = results

    for row in found["tables"]["integrators"]["rows"]:
        name, _, drift, lowest, length, completely, _ = row
        assert drift == "below 1e-12"
        if name == "exponential":
            assert float(lowest) > 0
            assert float(length) <= 1.0
            assert completely == "zero to round-off"


def test_euler_leaves_the_bloch_ball_at_the_coarse_step(results):
    _, found = results

    rows = {(row[0], row[1]): row for row in found["tables"]["integrators"]["rows"]}
    euler = rows["explicit Euler", "0.5"]
    assert float(euler[3]) < 0
    assert float(euler[4]) > 1
    assert float(euler[5]) < 0


def test_the_integrators_converge_at_their_orders(results):
    _, found = results

    assert float(found["numbers"]["order-euler"]) == pytest.approx(1.0, abs=0.15)
    assert float(found["numbers"]["order-rk4"]) == pytest.approx(4.0, abs=0.05)
    for row in found["tables"]["convergence"]["rows"]:
        assert row[-1] == "below 1e-12"
