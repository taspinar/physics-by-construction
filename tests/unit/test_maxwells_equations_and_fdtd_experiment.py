"""The experiment of "Maxwell's equations and FDTD" (electromagnetism 04)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.electromagnetism.experiments.maxwells_equations_and_fdtd"
PAGE = "electromagnetism/04-maxwells-equations-and-fdtd"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("maxwells_equations_and_fdtd")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_pulse_travels_at_the_group_velocity_of_the_grid(results):
    _, found = results
    for row in found["tables"]["wave-speed"]["rows"]:
        measured, grid, gap = float(row[2]), float(row[3]), float(row[4])
        assert measured < 1.0
        assert gap < 2e-4
        assert gap < 0.01 * (1.0 - grid)


def test_the_gap_to_the_speed_of_light_is_second_order(results):
    _, found = results
    for n in (1, 2):
        assert float(found["numbers"][f"speed-order-{n}"]) == pytest.approx(
            2.0, abs=0.05
        )


def test_the_interface_meets_the_fresnel_coefficients(results):
    _, found = results
    rows = found["tables"]["interface"]["rows"]
    *runs, fresnel = rows
    r, t = float(fresnel[1]), float(fresnel[2])
    assert (r, t) == pytest.approx((-1 / 3, 2 / 3), abs=1e-5)
    gaps = [max(abs(float(row[1]) - r), abs(float(row[2]) - t)) for row in runs]
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[-1] < 5e-4
    for row in runs:
        assert float(row[3]) + float(row[4]) == pytest.approx(1.0, abs=1e-6)
    assert float(found["numbers"]["conductor-reflection"]) == pytest.approx(
        -1.0, abs=1e-4
    )


def test_the_scheme_is_stable_below_its_limit_and_grows_above_it(results):
    _, found = results
    for row in found["tables"]["stability"]["rows"]:
        limit, courant, peak = float(row[1]), float(row[2]), float(row[3])
        measured, predicted = float(row[4]), float(row[5])
        if courant < limit:
            assert peak < 3.0
            assert predicted == 1.0
        else:
            assert peak > 1e40
            assert measured == pytest.approx(predicted, rel=1e-3)


def test_the_divergence_of_h_stays_at_round_off(results):
    _, found = results
    assert found["numbers"]["divergence-h"] == "below 1e-12"
