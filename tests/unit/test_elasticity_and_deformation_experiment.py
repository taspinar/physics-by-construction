"""The experiment of "Elasticity and deformation" (materials 03)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.materials.experiments.elasticity_and_deformation"
PAGE = "materials/03-elasticity-and-deformation"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("elasticity_and_deformation")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_bar_is_exact_at_the_nodes_and_its_stress_at_the_midpoints(results):
    _, found = results

    rows = found["tables"]["bar"]["rows"]
    assert [int(row[0]) for row in rows] == [1, 2, 4, 8, 16]
    for _, nodal, middle, ends, bound in rows:
        assert nodal.startswith("below") and middle.startswith("below")
        assert float(ends) == pytest.approx(float(bound), rel=1e-3)
    # q h / (2A) halves with h; q L / (2A) = 7850 * 9.81 * 100 / 2 Pa.
    assert float(rows[0][4]) == pytest.approx(7850 * 9.81 * 100 / 2 / 1e6, rel=1e-3)
    # u(L) = (F L + q L^2 / 2) / (E A), sigma(0) = (F + q L) / A.
    q = 7850 * 9.81 * 1e-4
    assert float(found["numbers"]["tip-mm"]) == pytest.approx(
        1e3 * (1000 * 100 + q * 100**2 / 2) / (200e9 * 1e-4), abs=1e-3
    )
    assert float(found["numbers"]["top-stress"]) == pytest.approx(
        (1000 + q * 100) / 1e-4 / 1e6, abs=0.01
    )


def test_uniform_tension_passes_the_patch_test_with_poissons_ratio(results):
    _, found = results

    for _, _, displacement, stress, ratio in found["tables"]["patch"]["rows"]:
        assert displacement.startswith("below") and stress.startswith("below")
        assert float(ratio) == pytest.approx(0.3, abs=1e-6)


def test_the_clamp_disturbs_the_plate_only_near_it(results):
    _, found = results

    rows = found["tables"]["clamped"]["rows"]
    peaks = [float(row[4]) for row in rows]
    assert peaks == sorted(peaks) and peaks[-1] > peaks[0] + 0.1
    for _, _, balance, end, _ in rows:
        assert balance.startswith("below")
        assert 0.99 < float(end) < 1.0  # the clamp stiffens the plate a little
    recovery = {
        float(row[0]): [float(v) for v in row[1:]]
        for row in found["tables"]["recovery"]["rows"]
    }
    assert all(v < 0.7 for v in recovery[0.125])
    assert all(abs(v - 1) < 2e-4 for v in recovery[2.0] + recovery[3.0])
    assert float(found["numbers"]["recovery-two"]) < 2e-4


def test_the_exercises_agree_with_their_closed_forms(results):
    _, found = results

    numbers = found["numbers"]
    # F (L1 / (E1 A) + L2 / (E2 A)) with F = 10 kN, A = 1 cm^2, L = 1 m each.
    assert float(numbers["series-closed-mm"]) == pytest.approx(
        1e3 * 1e4 * (1 / (200e9 * 1e-4) + 1 / (70e9 * 1e-4)), abs=1e-4
    )
    assert numbers["series-end-mm"] == numbers["series-closed-mm"]
    assert numbers["series-gap"].startswith("below")
    assert numbers["series-stress-spread"].startswith("below")
    assert numbers["no-contraction"].startswith("below")
