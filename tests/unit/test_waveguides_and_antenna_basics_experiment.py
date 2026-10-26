"""The experiment of "Waveguides and antenna basics" (electromagnetism 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.electromagnetism.experiments.waveguides_and_antenna_basics"
PAGE = "electromagnetism/06-waveguides-and-antenna-basics"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("waveguides_and_antenna_basics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_cutoff_frequencies_converge_at_second_order(results):
    _, found = results
    assert float(found["numbers"]["cutoff-order"]) == pytest.approx(2.0, abs=0.05)
    for _, exact, computed in found["tables"]["cutoffs"]["rows"]:
        assert float(computed) == pytest.approx(float(exact), rel=5e-4)
    names = [row[0] for row in found["tables"]["cutoffs"]["rows"]]
    assert names[0] == "TE10"


def test_the_fdtd_guide_follows_its_dispersion_relation(results):
    _, found = results
    rows = found["tables"]["transmission"]["rows"]
    assert {row[1] for row in rows} == {"alpha", "beta"}
    for row in rows:
        assert float(row[2]) == pytest.approx(float(row[3]), rel=5e-3)
        assert float(row[4]) < 1e-3
        # The cut-off that the measurement implies is the TE10 cut-off.
        assert float(row[5]) == pytest.approx(6.557, rel=3e-3)


def test_the_superposed_wires_have_the_dipole_patterns(results):
    _, found = results
    half, short = found["tables"]["patterns"]["rows"]
    assert float(half[2]) < 1e-5
    assert float(short[2]) < 1e-2
    assert float(half[3]) == pytest.approx(float(half[4]), abs=1e-4)
    assert float(half[3]) == pytest.approx(1.641, abs=1e-3)
    assert float(short[4]) == pytest.approx(1.5, abs=1e-4)
    assert float(found["numbers"]["half-wave-resistance"]) == pytest.approx(
        float(found["numbers"]["closed-resistance"]), abs=0.01
    )


def test_two_elements_are_the_element_pattern_times_the_array_factor(results):
    _, found = results
    assert found["numbers"]["multiplication-gap"] == "below 1e-12"
