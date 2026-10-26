"""The experiment of "Diffraction and imaging" (waves 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.waves.experiments.diffraction_and_imaging"
PAGE = "waves/06-diffraction-and-imaging"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("diffraction_and_imaging")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_fringe_spacing_and_airy_zero_match_the_closed_forms(results):
    _, found = results
    numbers = found["numbers"]

    assert float(numbers["spacing"]) == pytest.approx(
        float(numbers["paraxial"]), rel=1e-3
    )
    assert numbers["airy-zero"] == numbers["airy-closed"]
    assert numbers["fresnel-slope"] == "2.00"


def test_the_doublet_is_resolved_only_by_the_larger_grating(results):
    _, found = results
    resolved = [row[3] for row in found["tables"]["doublet-run"]["rows"]]

    assert resolved == ["no", "yes", "yes"]
