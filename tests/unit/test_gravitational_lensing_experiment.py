"""The experiment of "Gravitational lensing" (astrophysics 03)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.gravitational_lensing"
PAGE = "astrophysics/03-gravitational-lensing"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("gravitational_lensing")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_deflection_approaches_the_weak_field_formula(results):
    _, found = results

    rows = found["tables"]["deflection"]["rows"]
    excess = [float(row[4]) for row in rows]
    assert excess == sorted(excess, reverse=True)
    assert all(value > 0 for value in excess)
    assert excess[-1] < 1e-4
    # The remainder approaches the second-order coefficient from above.
    coefficients = [float(row[5]) for row in rows]
    assert coefficients == sorted(coefficients, reverse=True)
    assert coefficients[-1] == pytest.approx(15 * np.pi / 4, rel=1e-4)
    # The Newtonian turn is half the weak-field one far from the mass.
    assert float(rows[-1][3]) == pytest.approx(float(rows[-1][2]) / 2, rel=1e-6)


def test_ray_shooting_agrees_with_the_disk_average(results):
    _, found = results

    for row in found["tables"]["images"]["rows"]:
        assert float(row[1]) == pytest.approx(float(row[2]), rel=5e-3)
        assert float(row[2]) >= float(row[3]) - 1e-3


def test_the_three_lenses_share_the_einstein_time_and_the_curve(results):
    _, found = results

    rows = found["tables"]["degeneracy"]["rows"]
    assert {row[-1] for row in rows} == {"30.0"}
    assert len({row[0] for row in rows}) == 3
    assert found["numbers"]["curve-spread"] == "below 1e-12"


def test_the_solar_limb_deflection(results):
    _, found = results

    weak = float(found["numbers"]["limb-weak"])
    assert weak == pytest.approx(1.75, abs=0.01)
    assert float(found["numbers"]["limb-newtonian"]) == pytest.approx(
        weak / 2, abs=1e-3
    )
