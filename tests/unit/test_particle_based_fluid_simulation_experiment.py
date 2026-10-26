"""The experiment of "Particle-based fluid simulation" (fluids 07)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.fluids.experiments.particle_based_fluid_simulation"
PAGE = "fluids/07-particle-based-fluid-simulation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("particle_based_fluid_simulation")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_particles_converge_on_a_lattice_and_not_when_disordered(results):
    _, found = results
    assert found["numbers"]["kernel-integral"] == "1.000000"
    rows = found["tables"]["gradient-run"]["rows"]
    central, lattice, plain, difference = (
        [float(row[k]) for row in rows] for k in (1, 2, 3, 4)
    )
    assert central == sorted(central, reverse=True)
    assert lattice == sorted(lattice, reverse=True)
    assert plain == sorted(plain)
    assert difference[-1] > 5 * lattice[-1]
    assert 1.8 < float(found["numbers"]["lattice-order"]) < 2.2


def test_the_drop_follows_the_exact_ellipse(results):
    _, found = results
    for row in found["tables"]["drop-run"]["rows"]:
        assert abs(float(row[3])) < 1.0 and abs(float(row[5])) < 1.0
    exact_a, exact_b = (
        float(found["numbers"]["exact-a"]),
        float(found["numbers"]["exact-b"]),
    )
    assert exact_a * exact_b == pytest.approx(1.0, abs=2e-4)


def test_conservation(results):
    _, found = results
    rows = found["tables"]["conservation-run"]["rows"]
    assert all(row[1] == "below 1e-12" for row in rows)
    angular = [float(row[2]) for row in rows]
    energies = [float(row[3]) for row in rows]
    assert angular == sorted(angular, reverse=True)
    assert energies == sorted(energies, reverse=True)
    assert float(found["numbers"]["angular-order"]) > 1.8
    assert float(found["numbers"]["energy-order"]) > 1.8
    assert len({row[4] for row in rows}) == 1


def test_the_exercises(results):
    _, found = results
    numbers = found["numbers"]
    assert 1.7 < float(numbers["mean-power"]) < 2.3
    assert 0.8 < float(numbers["noise-power"]) < 1.4
    start, end = found["tables"]["long-run"]["rows"]
    assert abs(float(end[2])) > 3 * abs(float(start[2]))
    assert float(end[3]) < float(start[3])
