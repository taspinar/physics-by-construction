"""The experiment of "Navier-Stokes fundamentals" (fluids 05)."""

import itertools
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.fluids.experiments.navier_stokes_fundamentals"
PAGE = "fluids/05-navier-stokes-fundamentals"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("navier_stokes_fundamentals")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_projection_removes_the_gradient_and_its_energy(results):
    _, found = results
    rows = found["tables"]["projection-run"]["rows"]
    assert rows[0][3] == rows[1][3] == "below 1e-12"
    before, after = float(rows[2][2]), float(rows[2][3])
    assert before - after == pytest.approx(
        float(found["numbers"]["removed-energy"]), abs=2e-4
    )
    # The Taylor-Green vortex on [0, 2 pi)^2 has the energy pi^2.
    assert after == pytest.approx(9.8696, abs=1e-4)


def test_the_solver_converges_at_second_order(results):
    _, found = results
    for name in ("order-vortex", "order-velocity", "order-pressure"):
        assert 1.9 < float(found["numbers"][name]) < 2.1
    rows = found["tables"]["convergence-run"]["rows"]
    for coarse, fine in itertools.pairwise(rows):
        for column in (2, 3, 4):
            assert float(coarse[column]) / float(fine[column]) == pytest.approx(
                4.0, rel=0.15
            )


def test_the_energy_budget_closes(results):
    _, found = results
    numbers = found["numbers"]
    assert 2.7 < float(numbers["inviscid-order"]) < 3.3
    assert float(numbers["budget-mismatch"]) < 1e-6
    assert numbers["budget-lost"] == numbers["budget-dissipated"]


def test_the_exercises(results):
    _, found = results
    reynolds = [float(row[4]) for row in found["tables"]["reynolds-run"]["rows"]]
    assert reynolds == sorted(reynolds) and reynolds[0] < 1 < 1e6 < reynolds[-1]
    rows = found["tables"]["unprojected-run"]["rows"]
    raw = [float(row[1]) for row in rows]
    assert raw[0] / raw[1] == pytest.approx(2.0, rel=1e-3)
    assert all(row[2] == "below 1e-12" for row in rows)
