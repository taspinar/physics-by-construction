"""The experiment of "From finite differences to finite elements"
(thermodynamics 08)."""

from itertools import pairwise
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.thermodynamics.experiments.from_finite_differences_to_finite_elements"
PAGE = "thermodynamics/08-from-finite-differences-to-finite-elements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("from_finite_differences_to_finite_elements")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_manufactured_errors_fall_at_the_orders_of_linear_elements(results):
    _, found = results
    assert float(found["numbers"]["l2-order"]) == pytest.approx(2.0, abs=0.05)
    assert float(found["numbers"]["h1-order"]) == pytest.approx(1.0, abs=0.05)
    rows = found["tables"]["manufactured"]["rows"]
    for coarse, fine in pairwise(rows):
        assert float(coarse[3]) / float(fine[3]) == pytest.approx(4.0, rel=0.05)
        assert float(coarse[4]) / float(fine[4]) == pytest.approx(2.0, rel=0.05)


def test_the_structured_elements_are_the_five_point_grid(results):
    _, found = results
    assert found["numbers"]["stencil-gap"] == "below 1e-12"
    rows = found["tables"]["fd-against-fem"]["rows"]
    for coarse, fine in pairwise(rows):
        for column in (1, 2, 3):
            ratio = float(coarse[column]) / float(fine[column])
            assert ratio == pytest.approx(4.0, rel=0.05)


def test_the_meshes_keep_their_quality_under_refinement(results):
    _, found = results
    rows = found["tables"]["mesh-quality"]["rows"]
    assert float(found["numbers"]["smallest-angle"]) > 40.0
    for row in rows:
        assert float(row[4]) > 40.0
        assert float(row[5]) > 0.8
        assert row[7] == "below 1e-12"
    sizes = [float(row[3]) for row in rows]
    assert sizes == sorted(sizes, reverse=True)


def test_the_pipe_balance_closes_and_its_heat_loss_converges(results):
    _, found = results
    assert found["numbers"]["balance-gap"] == "below 1e-10"
    exact = float(found["numbers"]["exact-heat-loss"])
    for row in found["tables"]["pipe"]["rows"]:
        heat_in, heat_out = float(row[2]), float(row[3])
        assert heat_in == pytest.approx(heat_out, rel=1e-9)
        assert row[4] == "below 1e-10"
        assert abs(heat_in - exact) / exact < 3e-3
    assert float(found["numbers"]["pipe-order"]) > 1.8
    assert float(found["numbers"]["gradient-order"]) == pytest.approx(1.0, abs=0.15)
    assert float(found["numbers"]["pipe-error"]) < 1e-5


def test_the_heat_loss_of_a_coated_wire_peaks_at_the_critical_radius(results):
    _, found = results
    rows = found["tables"]["critical-radius"]["rows"]
    exact = [float(row[1]) for row in rows]
    fem = [float(row[2]) for row in rows]
    peak = exact.index(max(exact))
    assert float(rows[peak][0]) == pytest.approx(20.0)  # k / h = 0.2 / 10 m
    assert fem.index(max(fem)) == peak
    for e, f in zip(exact, fem, strict=True):
        assert f == pytest.approx(e, rel=3e-3)
