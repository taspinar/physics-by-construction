"""The experiment of "Applied capstone: adaptive phased-array beam steering"
(electromagnetism 07)."""

from itertools import pairwise
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

MODULE = "pbc.electromagnetism.experiments.adaptive_phased_array_beam_steering"
PAGE = "electromagnetism/07-adaptive-phased-array-beam-steering"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("adaptive_phased_array_beam_steering")
    return directory, run_entry_point(MODULE, directory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_model_meets_its_closed_forms(results):
    _, found = results
    numbers = found["numbers"]
    for name in ("closed-form-gap", "mirror-gap", "translation-gap", "ideal-null"):
        assert numbers[name] == "below 1e-12"
    for name in ("steering-gap", "null-gap", "squint-gap"):
        assert numbers[name] == "below 1e-09"
    for commanded, peak in found["tables"]["steering"]["rows"]:
        assert float(peak) == pytest.approx(float(commanded), abs=1e-9)
    for _, closed, nulls in found["tables"]["nulls"]["rows"]:
        assert float(nulls) == pytest.approx(float(closed), abs=1e-6)


def test_the_grating_onset_is_the_closed_form_less_the_threshold_shift(results):
    _, found = results
    assert found["numbers"]["onset-residual"] == "below 1e-08"
    shift = float(found["numbers"]["onset-shift"])
    for _, closed, bisection, gap in found["tables"]["grating-onset"]["rows"]:
        assert float(gap) == pytest.approx(-shift, rel=1e-2)
        assert float(bisection) < float(closed)
    # The chosen spacing keeps grating lobes out over the band and the scan.
    assert float(found["numbers"]["spacing"]) < float(
        found["numbers"]["largest-spacing"]
    )


def test_the_taper_and_the_null_meet_their_closed_forms(results):
    _, found = results
    uniform, tapered = found["tables"]["taper"]["rows"]
    assert float(tapered[1]) == pytest.approx(-30.0, abs=1e-6)
    assert float(uniform[1]) == pytest.approx(-13.15, abs=0.01)
    assert float(tapered[2]) > float(uniform[2])
    assert found["numbers"]["null-cost-gap"] == "below 1e-12"
    rows = found["tables"]["null-cost"]["rows"]
    assert float(rows[0][2]) > 3.0  # inside the main lobe, the null is costly
    assert float(rows[-1][2]) < 0.1  # in the sidelobes it is almost free


def test_quantisation_and_noise_degrade_as_expected(results):
    _, found = results
    for _, loss, mean_loss, depth, mean_depth in found["tables"]["quantisation"][
        "rows"
    ]:
        assert float(mean_depth) == pytest.approx(float(depth), abs=0.3)
        assert float(mean_loss) == pytest.approx(float(loss), abs=0.1)
    depths = [float(row[3]) for row in found["tables"]["quantisation"]["rows"]]
    # About six decibels per bit once the step is small (from three bits).
    steps = [a - b for a, b in pairwise(depths[1:])]
    assert steps == pytest.approx([6.0] * len(steps), abs=0.2)
    for _, change, mean_change, depth, mean_depth in found["tables"]["channel-errors"][
        "rows"
    ]:
        assert float(mean_depth) == pytest.approx(float(depth), abs=0.3)
        assert float(mean_change) == pytest.approx(float(change), abs=0.01)
    assert float(found["numbers"]["rounding-lobe"]) > -20.0


def test_the_decision_meets_the_null_requirement(results):
    _, found = results
    bits = int(found["numbers"]["chosen-bits"])
    rows = {int(row[0]): row for row in found["tables"]["decision"]["rows"]}
    assert float(rows[bits][2]) <= -30.0
    assert float(rows[bits - 1][2]) > -30.0
    assert float(found["numbers"]["worst-null"]) <= -30.0
    assert (
        float(found["numbers"]["window-low"])
        < 20.0
        < float(found["numbers"]["window-high"])
    )


def test_phase_steering_squints_across_the_band(results):
    _, found = results
    for _, closed, peak, _, _ in found["tables"]["band"]["rows"]:
        assert float(peak) == pytest.approx(float(closed), abs=1e-4)
    assert float(found["numbers"]["squint"]) > 0.0
    # The ideal null of the design still meets the requirement at the band
    # edges, the claim of the page, and is only exact at the carrier.
    depths = [float(row[4]) for row in found["tables"]["band"]["rows"] if row[4]]
    assert len(depths) == 4
    assert max(depths) <= -30.0
    assert float(found["numbers"]["edge-null"]) == pytest.approx(max(depths), abs=0.05)
    assert float(found["numbers"]["edge-null-margin"]) > 0.0
