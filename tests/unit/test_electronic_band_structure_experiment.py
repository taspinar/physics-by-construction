"""The experiment of "Electronic band structure" (materials 02)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.materials.experiments.electronic_band_structure"
PAGE = "materials/02-electronic-band-structure"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("electronic_band_structure")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_ring_has_the_closed_form_bands(results):
    _, found = results

    one, two = found["tables"]["bands"]["rows"]
    assert one[2] == "24" and two[2] == "48"
    assert one[3].startswith("below") and two[3].startswith("below")


def test_the_count_and_the_effective_mass(results):
    _, found = results

    for _, miscount, mass, closed, _ in found["tables"]["one-band"]["rows"]:
        assert float(miscount) <= 1.0
        assert float(closed) == pytest.approx(0.5)
        assert float(mass) > float(closed)
    assert float(found["numbers"]["mass-order"]) == pytest.approx(2.0, abs=0.05)


def test_the_half_filled_band_is_a_metal_and_the_filled_band_an_insulator(results):
    _, found = results

    for _, metal, closed, scaled, insulator in found["tables"]["filling"]["rows"]:
        assert float(metal) == pytest.approx(float(closed), abs=1e-5)
        assert float(scaled) == pytest.approx(4 * np.pi, rel=1e-2)
        assert float(insulator) == pytest.approx(1.0, abs=1e-5)  # 2 Delta
    assert float(found["numbers"]["fill-order"]) == pytest.approx(1.0, abs=0.05)


def test_the_packet_oscillates_with_the_bloch_period(results):
    _, found = results

    for force, _, period, swing, closed, edge, gap, back in found["tables"]["bloch"][
        "rows"
    ]:
        assert float(period) == pytest.approx(2 * np.pi / float(force), abs=1e-2)
        assert float(swing) == pytest.approx(float(closed), abs=1e-4)
        assert float(swing) < float(edge)
        assert gap.startswith("below") and back.startswith("below")
    narrow = found["tables"]["bloch"]["rows"][-1]
    assert float(narrow[3]) < 0.97 * float(narrow[5])


def test_the_gap_is_two_delta_and_the_bands_are_mirror_images(results):
    _, found = results

    for delta, gap, twice in found["tables"]["gap-closes"]["rows"]:
        assert float(gap) == pytest.approx(2 * float(delta), abs=1e-6)
        assert float(twice) == pytest.approx(2 * float(delta))
    numbers = found["numbers"]
    assert numbers["width-lower"] == numbers["width-upper"] == numbers["width-closed"]
