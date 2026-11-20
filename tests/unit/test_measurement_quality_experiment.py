"""The experiment of "Measurement quality and multimodal observations"
(electromagnetism 11, slot SA4, Issue #570): every claim of the page is
asserted here, the video exercise is compared with its ground truth, and the
clips are checked against the rules of generated clips (acceptance criteria
3 and 4)."""

import base64
import json
import math
from pathlib import Path

import numpy as np
import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

from pbc.electromagnetism import needle as compass
from pbc.electromagnetism.experiments import measurement_quality as lab
from pbc.electromagnetism.measurement import alias
from pbc.electromagnetism.observations import (
    CONFIRMED,
    CONTRADICTED,
    INFERRED,
    READ,
    UNCERTAIN,
)

MODULE = "pbc.electromagnetism.experiments.measurement_quality"
PAGE = "electromagnetism/11-measurement-quality"
# The on-demand budget of a page is 3 MB with the initial payload under 5 MB
# (docs/authoring.md, "On-demand data"); the clips stay far below it.
CLIP_FILE_LIMIT = 300_000


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("measurement-quality")
    return directory, run_entry_point(MODULE, directory)


def rows(results, name):
    return results[1]["tables"][name]["rows"]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_first_capture_is_flagged_and_its_peak_is_the_rail(results):
    numbers = results[1]["numbers"]
    assert numbers["quality-flags"] == "clipped, samples missing, not calibrated"
    assert numbers["quality-usable"] == "not usable"
    assert float(numbers["peak-reading"]) == pytest.approx(lab.CHAIN.full_scale_v)
    assert float(numbers["exact-amplitude"]) > lab.CHAIN.full_scale_v


def test_the_calibration_finds_the_chain_and_corrects_the_amplitude(results):
    """Claim: uncorrected the amplitude is off by the gain; corrected it agrees
    with the closed form to the millivolt."""
    found = lab.calibration()
    assert found["gain"] == pytest.approx(lab.CHAIN.gain, abs=1e-3)
    assert found["offset"] == pytest.approx(lab.CHAIN.offset_v, abs=1e-3)
    assert abs(found["corrected"] - found["exact"]) < 1e-3
    assert found["raw"] / found["exact"] == pytest.approx(lab.CHAIN.gain, abs=2e-3)
    table = dict(rows(results, "amplitudes"))
    assert table["fit, corrected with the calibration"] == table["closed form"]
    assert table["fit, uncorrected"] != table["closed form"]


def test_below_the_nyquist_rate_the_record_shows_the_alias():
    """Claim: above the Nyquist rate the record shows the drive; below it the
    strongest component is the predicted alias, and nothing in the record
    says so: a sinusoid at the alias fits the record down to its noise."""
    for rate, per_period, found, predicted in lab.sampling():
        assert predicted == alias(lab.FREQUENCY_HZ, rate)
        assert abs(found - predicted) < 0.01 * lab.FREQUENCY_HZ
        if per_period > 2:
            assert abs(found - lab.FREQUENCY_HZ) < 0.01 * lab.FREQUENCY_HZ
        else:
            assert abs(found - lab.FREQUENCY_HZ) > 0.5 * lab.FREQUENCY_HZ
            bench = lab.SimulatedRLCBench(seed=lab.SEED)
            bench.set_output(lab.AMPLITUDE_V, lab.FREQUENCY_HZ)
            record = bench.capture(rate, round(lab.SAMPLING_DURATION * rate) + 1)
            v, phase = record.channels["response"], 2 * np.pi * predicted * record.t
            basis = np.column_stack([np.sin(phase), np.cos(phase), np.ones_like(phase)])
            coefficients = np.linalg.lstsq(basis, v, rcond=None)[0]
            assert np.std(v - basis @ coefficients) < 1.5 * bench.noise_v


def test_the_spread_falls_as_the_square_root_and_the_fit_reports_it(results):
    """Claim: the spread of the amplitude falls as one over the square root of
    N, close to sigma sqrt(2 / N), and the reported standard error agrees."""
    noise = lab.noise_and_length()
    n = np.array([r[0] for r in noise], dtype=float)
    spread = np.array([r[1] for r in noise])
    slope = np.polyfit(np.log(n), np.log(spread), 1)[0]
    assert slope == pytest.approx(-0.5, abs=0.12)
    for _, s, error, expected in noise:
        # 24 repeats estimate a standard deviation to about 15 % (one sigma).
        assert s / expected == pytest.approx(1.0, abs=0.45)
        assert error / expected == pytest.approx(1.0, abs=0.06)


def test_the_fit_inside_the_rails_recovers_the_clipped_amplitude():
    """Claim: the fit to the samples inside the rails agrees with the closed
    form to the millivolt; the peak and the fit to every sample fall short."""
    exact = lab.exact_capacitor_amplitude()
    peak, everything, inside = lab.clipping()
    assert abs(inside[1] - exact) < 1e-3
    assert inside[2] < everything[2]
    assert peak[1] == pytest.approx(lab.CLIPPING.full_scale_v)
    assert everything[1] < exact - 0.1 and peak[1] < exact - 0.1


def test_lost_samples_left_out_cost_nothing_and_zeros_bias_low():
    """Claim: with the lost samples left out the fit recovers the amplitude;
    with them set to zero it reads too low."""
    exact = lab.exact_capacitor_amplitude()
    masked, zeros = lab.missing_samples()
    assert abs(masked[1] - exact) < 1e-3
    assert zeros[1] < exact - 0.1
    assert 0.2 < 1 - masked[2] / zeros[2] < 0.45  # about a third lost


def test_the_readings_of_the_diagram_are_typed_and_checked(results):
    """Acceptance criterion 4: the affordances (read and inferred) and the
    counterfactuals, each with its status; the wrong inference contradicted,
    the uncertain one confirmed for this circuit and still uncertain."""
    checks = lab.check_readings()
    statuses = [c.interpretation.status for c in checks]
    outcomes = [c.outcome for c in checks]
    assert statuses == [READ, READ, INFERRED, INFERRED, INFERRED, UNCERTAIN]
    assert outcomes == [
        CONFIRMED, CONFIRMED, CONFIRMED, CONTRADICTED, CONFIRMED, CONFIRMED
    ]  # fmt: skip
    assert "resistor" in checks[4].interpretation.statement
    assert "R doubled" in checks[5].interpretation.statement
    assert checks[5].interpretation.settled_by
    assert [r[2] for r in rows(results, "readings")] == outcomes


def test_the_resistor_probe_peaks_at_the_natural_frequency_for_two_resistances():
    """Review 02, MIN1: the counterfactual's check tests what it states,
    the peak, its gain and phase, for R and for R doubled; and channel 2's
    check tells the capacitor from the inductor by the phase."""
    step = 0.25 * lab.F0_HZ / 50
    circuit = lab.BENCH_CIRCUIT
    doubled = lab.SeriesRLC(
        2 * circuit.resistance, circuit.inductance, circuit.capacitance
    )
    for c in (circuit, doubled):
        peak_f, gain = lab._sweep_peak(lab.ResistorProbeBench, c)
        assert abs(peak_f - lab.F0_HZ) <= step / 2
        assert abs(gain - 1) < 1e-3
        assert abs(lab._at(lab.ResistorProbeBench, lab.F0_HZ, c)[1]) < 0.1
    evidence = lab.check_readings()[4].evidence
    assert "R = 100 ohm: peak at 5033 Hz, gain 1.000" in evidence
    assert "R = 200 ohm: peak at 5033 Hz, gain 1.000" in evidence
    assert "phase -90.00 deg" in lab.check_readings()[1].evidence


def test_the_capacitor_peaks_below_the_natural_frequency():
    """The independent reason the fourth reading is contradicted: the
    capacitor voltage of a series circuit peaks at f0 sqrt(1 - 1 / (2 Q^2))."""
    q = lab.BENCH_CIRCUIT.quality_factor
    peak, _ = lab._sweep_peak(lab.SimulatedRLCBench, lab.BENCH_CIRCUIT)
    expected = lab.F0_HZ * math.sqrt(1 - 1 / (2 * q * q))
    step = (1.1 - 0.85) * lab.F0_HZ / 50
    assert abs(peak - expected) <= step


# -- the clips: acceptance criterion 3 -----------------------------------------------


@pytest.fixture(scope="module")
def filmed():
    return lab.clips()


def test_the_tracking_is_deterministic_and_matches_the_ground_truth(filmed):
    """Claim: the angle found in every frame lies within the stated bound of
    the simulated angle; two runs give the same track."""
    first, second = lab.tracks(filmed), lab.tracks(lab.clips())
    for name, clip in filmed.items():
        np.testing.assert_array_equal(first[name], second[name])
        assert np.max(np.abs(first[name] - clip.theta)) < math.radians(0.05)


def test_the_frame_rate_decides_the_field_read(results):
    """Claim: above twice the needle's frequency the clip gives the field
    within two per cent; below it the alias, and a field many times too
    small: more than three times, as (alias / frequency)^2 predicts."""
    needle = compass.Needle()
    for rate, _, found, predicted, field_mt in lab.frame_rates():
        assert predicted == alias(needle.frequency, rate)
        assert abs(found - predicted) < 0.02
        ratio = field_mt / (1e3 * needle.field)
        if rate > 2 * needle.frequency:
            assert abs(ratio - 1) < 0.02
            assert abs(ratio - 1) < 0.005  # "a few parts in a thousand"
        else:
            assert ratio < 0.3  # "many times too small"
            assert ratio == pytest.approx((predicted / needle.frequency) ** 2, rel=0.03)


def test_the_slow_clip_reading_is_uncertain_and_contradicted(results):
    table = rows(results, "clip-readings")
    assert [(r[1], r[2]) for r in table] == [
        (UNCERTAIN, CONTRADICTED),
        (INFERRED, CONFIRMED),
    ]
    # Review 02, MIN1 (its class): the confirmed reading says "about half a
    # millitesla", and its evidence gives the field read, near 0.5 mT.
    read_mt = float(table[1][3].split("read ")[1].split(" mT")[0])
    assert abs(read_mt / 0.5 - 1) < 0.1


def test_the_clip_file_holds_every_frame_as_generated(results, filmed):
    """The on-demand file: labelled generated, every frame a PNG whose pixels
    are the rendered frame, its time the clip's, and the whole far within
    the on-demand budget."""
    directory, _ = results
    path = directory / "needle-clips.json"
    assert path.stat().st_size < CLIP_FILE_LIMIT
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "clip-frames-1"
    assert "Generated" in data["label"] and "not filmed" in data["label"]
    from io import BytesIO

    from PIL import Image

    for entry, clip in zip(data["clips"], filmed.values(), strict=True):
        assert entry["frame_rate"] == clip.frame_rate
        assert len(entry["frames"]) == len(clip.frames)
        for frame, t, pixels in zip(entry["frames"], clip.t, clip.frames, strict=True):
            assert frame["t"] == pytest.approx(t, abs=1e-6)
            prefix = "data:image/png;base64,"
            assert frame["src"].startswith(prefix)
            image = Image.open(BytesIO(base64.b64decode(frame["src"][len(prefix) :])))
            np.testing.assert_array_equal(np.asarray(image), pixels)


def test_the_page_loads_the_clips_only_on_demand_and_names_them_generated():
    page = page_of(PAGE)
    assert 'data-ondemand="index_files/figure-html/needle-clips.json"' in page
    assert 'data-widget="clip-viewer"' in page
    assert "generated" in page
    assert "never plays them" in page


def test_the_affordance_exercise_does_not_rely_on_the_ai6_lesson():
    """Acceptance criterion 4: the exercise is complete on this page; the AI6
    lesson is only linked as depth, in the header, and said to be optional."""
    page = page_of(PAGE)
    exercise = page[page.index("**Read the set-up.**") : page.index("**A frame rate")]
    assert "multimodal-physics-reasoning" not in exercise
    assert "Reading physics from pictures" not in exercise
    assert "related: [multimodal-physics-reasoning, discovery-under-noise]" in page
    assert "neither is needed" in " ".join(page.split())
