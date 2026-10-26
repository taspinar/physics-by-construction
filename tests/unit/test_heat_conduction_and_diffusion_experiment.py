"""The experiment of "Heat conduction and diffusion" (thermodynamics 07)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.thermodynamics.experiments.heat_conduction_and_diffusion"
PAGE = "thermodynamics/07-heat-conduction-and-diffusion"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("heat_conduction_and_diffusion")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_lumped_model_holds_at_small_biot_and_fails_at_large(results):
    _, found = results
    rows = found["tables"]["lumped-against-slab"]["rows"]
    gaps = [float(row[3]) for row in rows]
    assert gaps[0] < 0.01 < 0.1 < gaps[-1]
    assert gaps == sorted(gaps)
    # The scheme itself agrees with the exact series at every Biot number.
    assert all(float(row[4]) < 0.005 for row in rows)


def test_the_scheme_conserves_energy_to_round_off(results):
    _, found = results
    lost, out = map(float, found["tables"]["energy-balance"]["rows"][0])
    assert lost == pytest.approx(out, rel=1e-9)
    assert found["numbers"]["energy-gap"] == "below 1e-12"


def test_the_measured_stability_limits_are_those_of_the_grid(results):
    _, found = results
    for row in found["tables"]["stability"]["rows"]:
        dimension, measured, grid, fine = int(row[0]), *map(float, row[1:4])
        assert measured == pytest.approx(grid, abs=1e-5)
        assert fine == 1 / (2 * dimension)
        assert fine < measured < 1.02 * fine
        assert row[4] == "below 1e-06"


def test_the_scheme_is_second_order_in_space_and_first_in_time(results):
    _, found = results
    assert float(found["numbers"]["grid-order"]) == pytest.approx(2.0, abs=0.05)
    assert float(found["numbers"]["time-order"]) == pytest.approx(1.0, abs=0.05)


def test_the_transient_plate_settles_on_the_steady_solve(results):
    _, found = results
    assert found["numbers"]["plate-gap"] == "below 1e-09"


def test_the_thin_sheet_cools_as_one_body(results):
    _, found = results
    biot, _, lumped, exact = map(float, found["tables"]["cooling-time"]["rows"][0])
    assert biot < 0.1
    assert lumped == pytest.approx(exact, rel=1e-3)
