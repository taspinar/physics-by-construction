"""The experiment of "Inverse optics" (waves 07)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.waves.experiments.inverse_optics"
PAGE = "waves/07-inverse-optics"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("inverse_optics")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_slits_are_recovered_within_four_standard_errors(results):
    _, found = results
    for row in found["tables"]["fit-run"]["rows"]:
        assert abs(float(row[4])) < 4.0


def test_a_wrong_wavelength_fits_equally_well(results):
    _, found = results
    rows = found["tables"]["degeneracy-run"]["rows"]

    assert len({row[3] for row in rows}) == 1
    assert len({row[4] for row in rows}) == 1
    assert len({row[2] for row in rows}) == 3
