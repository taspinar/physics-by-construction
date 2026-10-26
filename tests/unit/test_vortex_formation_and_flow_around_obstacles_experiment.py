"""The experiment of "Vortex formation and flow around obstacles" (fluids 06)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.fluids.experiments.vortex_formation_and_flow_around_obstacles"
PAGE = "fluids/06-vortex-formation-and-flow-around-obstacles"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("vortex_formation_and_flow_around_obstacles")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_shear_layers_keep_their_circulation_and_converge(results):
    _, found = results
    rows = found["tables"]["shear-layer-run"]["rows"]
    assert all(row[1] == "below 1e-12" for row in rows)
    mismatches = [float(row[3]) for row in rows]
    assert mismatches == sorted(mismatches, reverse=True) and mismatches[-1] < 1e-4
    assert 1.4 < float(found["numbers"]["shear-order"]) < 2.5


def test_the_wake_settles_at_forty_and_sheds_at_one_hundred(results):
    _, found = results
    shedding, steady = found["tables"]["wake-run"]["rows"]
    assert float(steady[0]) == 40 and float(shedding[0]) == 100
    assert float(shedding[2]) == pytest.approx(float(shedding[1]), rel=0.05)
    assert float(shedding[2]) > 0.5
    assert float(steady[2]) < 0.5 * float(steady[1]) and steady[3] == ""


def test_the_strouhal_number_against_roshko(results):
    _, found = results
    numbers = found["numbers"]
    computed, roshko = float(numbers["strouhal"]), float(numbers["roshko"])
    assert roshko == pytest.approx(0.212 * (1 - 21.2 / 100), abs=5e-4)
    assert float(numbers["range-low"]) < computed < float(numbers["range-high"])
    # Within ten per cent of the fit, and above it, as blockage predicts.
    assert 1.0 < computed / roshko < 1.1
    assert float(numbers["narrow-strouhal"]) > computed


def test_the_singing_wire(results):
    _, found = results
    numbers = found["numbers"]
    assert numbers["wire-re"] == "100"
    assert float(numbers["wire-roshko"]) == pytest.approx(0.1671 * 1500, abs=1)
