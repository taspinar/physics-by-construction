"""The experiment of "Cosmic expansion and redshift" (astrophysics 06)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.cosmic_expansion"
PAGE = "astrophysics/06-cosmic-expansion"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("cosmic_expansion")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_expansion_matches_the_analytic_histories_and_ages(results):
    _, found = results

    rows = found["tables"]["expansion"]["rows"]
    for _, _, measured, analytic, _, gap in rows:
        assert measured == analytic
        assert gap.startswith("below")
    eds, milne, de_sitter, toy = rows
    assert float(eds[3]) == pytest.approx(2 / 3, abs=1e-6)
    assert float(milne[3]) == pytest.approx(1.0, abs=1e-6)
    assert de_sitter[2] == ""  # no beginning
    assert float(eds[1]) == 0.5 and float(de_sitter[1]) == -1.0
    assert float(eds[4]) < float(toy[4]) < float(milne[4])


def test_the_distance_redshift_relation_matches_the_analytic_cases(results):
    _, found = results

    rows = found["tables"]["distance-checks"]["rows"]
    for _, analytic, ray in rows[:3]:
        assert analytic.startswith("below")
        assert ray.startswith("below")
    assert rows[3][2].startswith("below")
    for z, comoving, luminosity, angular, _ in found["tables"]["distances"]["rows"]:
        z = float(z)
        assert float(luminosity) == pytest.approx((1 + z) * float(comoving), rel=1e-3)
        assert float(angular) == pytest.approx(float(comoving) / (1 + z), rel=1e-3)


def test_the_hubble_law_is_the_first_order(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["first-order"]) == pytest.approx(1.0, abs=0.1)
    assert float(numbers["second-order"]) == pytest.approx(2.0, abs=0.15)
    assert float(numbers["toy-q0"]) == pytest.approx(0.15 - 0.7)
    for z, _, first, second in found["tables"]["hubble-law"]["rows"]:
        assert float(second) < float(first) < float(z)


def test_the_angular_diameter_distance_turns_over_and_the_exercises(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["eds-peak"]) == pytest.approx(1.25, abs=1e-4)
    assert float(numbers["toy-peak"]) > 1.25
    assert numbers["turn-z"] == numbers["turn-z-closed"]
    assert float(numbers["turn-z"]) == pytest.approx(
        np.cbrt(2 * 0.7 / 0.3) - 1, abs=1e-4
    )
    assert float(numbers["fainter-eds"]) > float(numbers["fainter-milne"]) > 0
