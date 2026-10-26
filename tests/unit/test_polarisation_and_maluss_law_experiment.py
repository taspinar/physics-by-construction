"""The experiment of "Polarisation and Malus's law" (waves 05)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.waves.experiments.polarisation_and_maluss_law"
PAGE = "waves/05-polarisation-and-maluss-law"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("polarisation_and_maluss_law")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_transmitted_intensity_follows_malus(results):
    _, found = results
    for row in found["tables"]["malus-run"]["rows"]:
        assert row[1] == row[2] and row[3] == row[4]


def test_unpolarised_light_is_halved_and_more_polarisers_pass_more(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["ensemble-sigmas"]) < 4.0
    assert float(numbers["chain-sixty"]) > float(numbers["chain-two"])
