"""The experiment of "Modified gravity" (astrophysics 02)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.modified_gravity"
PAGE = "astrophysics/02-modified-gravity"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("modified_gravity")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_only_the_modified_law_turns_and_both_conserve(results):
    _, found = results

    newton, modified = found["tables"]["diagnostics"]["rows"]
    assert newton[2].startswith("below")
    assert float(modified[2]) > 0.1
    for row in (newton, modified):
        assert row[3].startswith("below") and row[4].startswith("below")


def test_the_turn_follows_the_first_order_prediction_to_second_order(results):
    _, found = results

    rows = found["tables"]["power-law"]["rows"]
    for delta, measured, predicted, gap, _ in rows:
        closed_form = 2 * np.pi * float(delta) * (1 - np.sqrt(0.75)) / 0.25
        assert float(predicted) == pytest.approx(closed_form, abs=1e-6)
        assert float(measured) == pytest.approx(closed_form, rel=float(delta))
        assert abs(float(gap)) < float(delta)
    assert float(found["numbers"]["gap-order"]) == pytest.approx(2.0, abs=0.1)


def test_the_yukawa_turn_matches_and_peaks_near_the_orbit(results):
    _, found = results

    rows = found["tables"]["yukawa"]["rows"]
    for _, _, _, small, large in rows:
        assert abs(float(small)) < 7e-3
        assert abs(float(large)) < 7e-2
    # The peak lies near the periapsis distance a (1 - e) = 0.5.
    assert 0.3 < float(found["numbers"]["yukawa-peak"]) < 0.6


def test_the_near_circular_turn_is_exact_beyond_first_order(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["circle-measured"]) == pytest.approx(
        float(numbers["circle-formula"]), abs=2e-3
    )
    assert float(numbers["circle-first-order"]) < 0.8 * float(
        numbers["circle-measured"]
    )
