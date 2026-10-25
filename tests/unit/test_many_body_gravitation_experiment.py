"""The experiment of "Many-body gravitation" (mechanics 17)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.mechanics.experiments.many_body_gravitation"
PAGE = "mechanics/17-many-body-gravitation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("many-body-gravitation")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_two_bodies_converge_to_the_kepler_motion_with_order_two(results):
    _, found = results

    assert float(found["numbers"]["two-body-order"]) == pytest.approx(2.0, abs=0.05)
    assert float(found["numbers"]["two-body-error"]) < 1e-2


def test_the_drift_is_reported_per_integrator_and_follows_the_method(results):
    _, found = results
    rows = {row[0]: row for row in found["tables"]["drift-per-integrator"]["rows"]}

    assert set(rows) == {
        "explicit Euler",
        "symplectic Euler",
        "velocity Verlet",
        "Runge-Kutta 4",
    }
    # The symplectic methods: a band that does not grow, and the angular
    # momentum to round-off.
    for name in ("symplectic Euler", "velocity Verlet"):
        early, late = float(rows[name][2]), float(rows[name][3])
        assert late < 1.5 * early
        assert rows[name][4] == "below 1e-12"
    # The others: an energy that drifts, and an angular momentum that moves.
    for name in ("explicit Euler", "Runge-Kutta 4"):
        assert float(rows[name][3]) > 1.4 * float(rows[name][2])
        assert float(rows[name][4]) > 1e-10


def test_the_figure_eight_closes_and_permutes_its_bodies(results):
    _, found = results

    assert float(found["numbers"]["period"]) == pytest.approx(6.3259, abs=1e-3)
    assert float(found["numbers"]["closure"]) < 1e-6
    assert float(found["numbers"]["permuted"]) < 1e-6


def test_the_energy_band_of_verlet_falls_towards_a_quarter_with_half_the_step(results):
    _, found = results

    halved = float(found["numbers"]["halved-ratio"])
    quartered = float(found["numbers"]["quartered-ratio"])
    assert abs(quartered - 4.0) < abs(halved - 4.0) < 1.0


def test_jupiter_moves_the_eccentricity_of_saturn(results):
    _, found = results

    assert float(found["numbers"]["saturn-with-jupiter"]) > 10 * float(
        found["numbers"]["saturn-alone"]
    )
