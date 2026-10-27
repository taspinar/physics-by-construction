"""The experiment of "Quantum entanglement, Bell and CHSH" (quantum 05)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.quantum.experiments.quantum_entanglement"
PAGE = "quantum/05-quantum-entanglement"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("quantum_entanglement")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_sampled_singlet_breaks_the_local_bound_and_not_tsirelsons(results):
    _, found = results

    singlet, local = found["tables"]["chsh"]["rows"]
    s, error = float(singlet[1]), float(singlet[2])
    assert s - 2 > 20 * error
    assert abs(s - 2 * 2**0.5) < 4 * error
    assert abs(float(local[1]) - 2) < 4 * float(local[2])


def test_no_deterministic_local_strategy_exceeds_two(results):
    _, found = results

    assert found["numbers"]["strategies"] == "16"
    assert found["numbers"]["largest-strategy"] == "2"


def test_the_sampled_correlations_follow_their_models(results):
    _, found = results

    for _, singlet, cosine, local, line in found["tables"]["correlations"]["rows"]:
        assert float(singlet) == pytest.approx(float(cosine), abs=0.1)
        assert float(local) == pytest.approx(float(line), abs=0.1)
