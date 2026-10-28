"""The experiment of "The three-body problem" (astrophysics 01)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.three_body_problem"
PAGE = "astrophysics/01-the-three-body-problem"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("three_body_problem")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_triangle_is_reproduced_at_order_four(results):
    _, found = results

    rows = found["tables"]["triangle"]["rows"]
    errors = [float(row[2]) for row in rows]
    assert errors == sorted(errors, reverse=True)
    assert errors[-1] < 1e-8
    assert float(rows[-1][3]) == pytest.approx(4.0, abs=0.2)
    assert all(float(row[4]) < 1e-5 for row in rows)


def test_the_growth_rate_follows_routh_on_both_sides_of_the_threshold(results):
    _, found = results

    for _, _, k, measured, predicted in found["tables"]["stability"]["rows"]:
        if float(k) < 1:
            assert float(measured) == 0.0 == float(predicted)
        else:
            assert float(measured) == pytest.approx(float(predicted), rel=0.02)
    assert float(found["numbers"]["equal-rate"]) == pytest.approx(2**-0.5, rel=0.01)


def test_the_lightest_body_escapes_at_both_tolerances(results):
    _, found = results

    rows = found["tables"]["pythagorean"]["rows"]
    for row in rows[:2]:
        assert float(row[1]) < 1e-8
        assert row[3] == "1"
        assert float(row[4]) > 0 > float(row[5])
    assert found["numbers"]["escaper"] == "1"


def test_nearby_runs_part_while_the_energy_is_kept(results):
    _, found = results

    rows = found["tables"]["divergence"]["rows"]
    tolerance_times = [float(row[1]) for row in rows]
    assert tolerance_times == sorted(tolerance_times)
    assert float(found["numbers"]["moved-final"]) > 1
    assert float(found["numbers"]["pythagorean-energy"]) < 1e-8


def test_the_trojan_libration_and_the_critical_ratio(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["libration-measured"]) == pytest.approx(
        float(numbers["libration-predicted"]), rel=0.01
    )
    assert float(numbers["critical-mu"]) == pytest.approx(0.03852, abs=1e-5)
