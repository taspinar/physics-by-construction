"""The experiment of "Exoplanet transit simulation" (astrophysics 05)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.exoplanet_transit"
PAGE = "astrophysics/05-exoplanet-transit"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("exoplanet_transit")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_depth_and_the_durations_of_one_transit(results):
    _, found = results

    depth, t14, t23 = found["tables"]["one-transit"]["rows"]
    assert float(depth[1]) == pytest.approx(0.01, rel=1e-3)
    for row in (t14, t23):
        assert row[1] == row[2]
        assert row[3] == "below 1e-09"
    assert float(found["numbers"]["flux-gap"]) < 1e-3


def test_the_impact_parameter_shortens_the_transit(results):
    _, found = results

    rows = found["tables"]["impacts"]["rows"]
    for row in rows:
        assert row[1] == row[2] and row[3] == row[4]
    totals = [float(row[1]) for row in rows]
    assert totals == sorted(totals, reverse=True)
    *full, grazing = rows
    assert all(float(row[5]) == pytest.approx(1.0, abs=1e-3) for row in full)
    assert grazing[3] == "none" and float(grazing[5]) < 0.9


def test_limb_darkening_deepens_a_central_transit(results):
    _, found = results

    rows = found["tables"]["limb"]["rows"]
    gaps = [abs(float(row[3])) for row in rows]
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[-1] < 1e-3
    assert float(rows[-1][2]) > 0.01


def test_the_earth_transit(results):
    _, found = results

    assert float(found["numbers"]["earth-depth"]) == pytest.approx(84, abs=1)
    assert float(found["numbers"]["earth-hours"]) == pytest.approx(13, abs=0.5)
