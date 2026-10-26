"""The experiment of "Refraction and Snell's law" (waves 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.waves.experiments.refraction_and_snells_law"
PAGE = "waves/04-refraction-and-snells-law"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("refraction_and_snells_law")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_least_time_paths_obey_snells_law(results):
    _, found = results
    for row in found["tables"]["least-time"]["rows"]:
        assert row[3] == row[4]


def test_the_grid_pulse_splits_by_the_fresnel_amplitudes(results):
    _, found = results
    numbers = found["numbers"]

    assert numbers["reflected"] == numbers["r-normal"] == "-0.2000"
    assert numbers["transmitted"] == numbers["t-normal"] == "0.8000"
    assert numbers["pulse-order"] == "2.00"
