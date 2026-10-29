"""The experiment of "Special relativity and spacetime" (astrophysics 04)."""

from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.astrophysics.experiments.special_relativity"
PAGE = "astrophysics/04-special-relativity"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("special_relativity")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_every_boost_keeps_the_interval_and_the_metric(results):
    _, found = results

    for row in found["tables"]["invariants"]["rows"]:
        speed = np.linalg.norm([float(c) for c in row[0].strip("()").split(",")])
        assert float(row[1]) == pytest.approx(speed, rel=1e-3)
        assert float(row[2]) == pytest.approx(1 / np.sqrt(1 - speed**2), abs=1e-4)
        assert all(cell.startswith("below") for cell in row[3:])


def test_dilation_and_contraction_follow_from_the_transformed_events(results):
    _, found = results

    for speed, gamma, tick, distance, own, length in found["tables"]["dilation"][
        "rows"
    ]:
        beta = float(speed)
        assert float(tick) == pytest.approx(float(gamma), abs=1e-4)
        assert float(distance) == pytest.approx(beta * float(gamma), abs=1e-4)
        assert float(own) == pytest.approx(1.0, abs=1e-6)
        assert float(length) == pytest.approx(np.sqrt(1 - beta**2), abs=1e-6)


def test_the_four_momentum_is_conserved_in_every_frame_and_newtons_is_not(results):
    _, found = results

    rows = found["tables"]["collision"]["rows"]
    masses = {row[1] for row in rows}
    assert len(masses) == 1  # the invariant mass of the pair, in every frame
    for _, _, _, change, before, after in rows:
        assert change.startswith("below")
        assert abs(float(after) - float(before)) > 0.05


def test_newtons_mechanics_is_recovered_at_second_order(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["limit-order"]) == pytest.approx(2.0, abs=0.01)
    assert float(numbers["ke-coefficient"]) == pytest.approx(0.75, abs=1e-3)
    for beta, *gaps in found["tables"]["limit"]["rows"]:
        assert all(0 < float(gap) < 2 * float(beta) ** 2 for gap in gaps)


def test_the_exercises(results):
    _, found = results

    numbers = found["numbers"]
    assert float(numbers["twin-away"]) == pytest.approx(6.0)
    assert float(numbers["muon-survive"]) > 0.05 > float(numbers["muon-survive-naive"])
    ratios = [float(row[3]) for row in found["tables"]["sticking"]["rows"]]
    assert ratios[0] == pytest.approx(1.0, abs=1e-3)  # Newton's limit
    assert ratios == sorted(ratios) and ratios[-1] > 1
