"""The Xu damped-pendulum sample parses into what its card says, and the
reference analysis gives the numbers of the dossier (ADR 007;
docs/datasets/xu-damped-pendulum.md).
"""

import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.reference import xu_pendulum

XU = SAMPLES_DIR / "xu-damped-pendulum"
ROWS = {
    "len1_cond1_1": 6896,
    "len2_cond1_1": 6584,
    "len3_cond1_1": 6767,
    "len4_cond1_1": 6767,
    "len5_cond1_1": 6749,
}
STATED = {"len1": 0.236, "len2": 0.330, "len3": 0.426, "len4": 0.518, "len5": 0.607}


@pytest.fixture(scope="module")
def sample():
    return xu_pendulum.load(XU)


@pytest.fixture(scope="module")
def analysis(sample):
    return xu_pendulum.analyse(sample)


# The sample.


def test_xu_pendulum_sample_parses(sample):
    # Field names: the PASCO export, UTF-8 with a byte-order mark, seven columns.
    for name in xu_pendulum.RUNS:
        raw = (XU / "raw_data" / f"{name}.csv").read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")
        header = raw[3:].decode("utf-8").splitlines()[0]
        assert tuple(h.strip('"') for h in header.split(",")) == xu_pendulum.RAW_FIELDS
    # The stated lengths, in metres, keyed len1 .. len5.
    assert sample.lengths == STATED
    for name, run in sample.runs.items():
        n = ROWS[name]
        assert run.length == STATED[name.split("_")[0]]
        # Shapes: every row of the file, one value per column.
        for column in (
            run.time,
            run.angle,
            run.angular_velocity,
            run.angular_acceleration,
            run.position,
            run.velocity,
            run.acceleration,
        ):
            assert column.shape == (n,)
        # Cadence: 0.01 s from 0, no gap, 66 to 69 s in all.
        assert run.time[0] == 0
        np.testing.assert_allclose(np.diff(run.time), xu_pendulum.STEP, atol=1e-9)
        assert 65 < run.time[-1] < 69
        # Masks: the angle and the position are complete; the derived columns
        # are empty only where a numerical derivative leaves the record.
        assert not np.isnan(run.angle).any() and not np.isnan(run.position).any()
        for first_derivative in (run.angular_velocity, run.velocity):
            assert list(np.flatnonzero(np.isnan(first_derivative))) == [0, n - 1]
        for second_derivative in (run.angular_acceleration, run.acceleration):
            assert list(np.flatnonzero(np.isnan(second_derivative))) == [
                0,
                1,
                n - 3,
                n - 2,
                n - 1,
            ]
        # Units: the angle in radians is a whole number of encoder steps of
        # 2 pi / 2000 (0.18 deg), written with 3 decimals.
        counts = np.round(run.angle / xu_pendulum.ENCODER_STEP)
        np.testing.assert_allclose(
            np.round(counts * xu_pendulum.ENCODER_STEP, 3), run.angle, atol=1e-12
        )
        # The angular velocity in rad/s is the software's derivative of the
        # angle, not a second measurement.
        computed = xu_pendulum.software_velocity(run.angle)
        np.testing.assert_allclose(
            computed[2:-2], run.angular_velocity[2:-2], atol=1e-9
        )
        # The position in metres is the angle times a radius of about 23.9 mm,
        # a pulley setting of the software, not a length of the pendulum.
        moving = np.abs(run.angle) > 0.1
        radius = np.median(run.position[moving] / run.angle[moving])
        assert radius == pytest.approx(0.0239, abs=0.0002)
    # The cleaned file: 6000 rows, the raw rows 5 s <= t < 65 s with the time
    # shifted to 0, no value changed; is_peak marks 115 extremes of |angle|.
    cleaned = sample.cleaned
    assert (XU / "cleaned_data/len1_cond1_1.csv").read_text().splitlines()[
        0
    ] == ",".join(xu_pendulum.CLEANED_FIELDS)
    raw = sample.runs[xu_pendulum.CLEANED]
    window = xu_pendulum.clean_window(raw)
    assert window.sum() == cleaned.time.size == 6000
    assert np.flatnonzero(window)[0] == 500
    np.testing.assert_allclose(cleaned.time, raw.time[window] - 5, atol=1e-9)
    # The raw file writes some zero angles as floating-point noise in
    # scientific notation (11 in this window, below 1e-15 rad); the cleaned
    # file writes them as 0.000.
    noise = (raw.angle[window] != 0) & (np.abs(raw.angle[window]) < 1e-12)
    assert noise.sum() == 11
    np.testing.assert_array_equal(cleaned.angle[noise], 0)
    np.testing.assert_array_equal(cleaned.angle[~noise], raw.angle[window][~noise])
    np.testing.assert_array_equal(
        cleaned.angular_velocity, raw.angular_velocity[window]
    )
    assert cleaned.is_peak.sum() == 115
    # The licence travels with the files (Apache-2.0, section 4(a)).
    licence = (XU / xu_pendulum.LICENSE).read_text()
    assert licence.split()[:4] == ["Apache", "License", "Version", "2.0,"]


ADDED = (
    *(f"len{k}_cond1_{t}" for k in range(1, 6) for t in (2, 3)),
    *(f"len1_cond3_{t}" for t in (1, 2, 3)),
)


def test_xu_pendulum_added_trials_parse():
    # The cleaned files added for the M15 lab (Issue #437, phase 2): the
    # other two air-only trials of every length and the three large-baffle
    # trials of the shortest one, each the creators' window of its raw run.
    assert len(ADDED) == 13
    for name in ADDED:
        path = XU / "cleaned_data" / f"{name}.csv"
        assert path.read_text().splitlines()[0] == ",".join(xu_pendulum.CLEANED_FIELDS)
        cleaned = xu_pendulum.read_cleaned(path)
        # Shapes and cadence: 6000 rows at 0.01 s from 0, 60 s of swinging.
        for column in (cleaned.time, cleaned.angle, cleaned.angular_velocity):
            assert column.shape == (6000,)
        assert cleaned.time[0] == 0
        np.testing.assert_allclose(np.diff(cleaned.time), xu_pendulum.STEP, atol=1e-9)
        # Masks: nothing is missing in the window.
        assert np.isfinite(cleaned.angle).all()
        assert np.isfinite(cleaned.angular_velocity).all()
        # Units: the angle in radians is a whole number of encoder steps,
        # written with 3 decimals; the pendulum swings by more than 0.1 rad.
        counts = np.round(cleaned.angle / xu_pendulum.ENCODER_STEP)
        np.testing.assert_allclose(
            np.round(counts * xu_pendulum.ENCODER_STEP, 3), cleaned.angle, atol=1e-12
        )
        assert 0.1 < np.abs(cleaned.angle).max() < 1.2
        # The angular velocity in rad/s is the software's derivative of the
        # angle inside the window, as in the raw files.
        computed = xu_pendulum.software_velocity(cleaned.angle)
        np.testing.assert_allclose(
            computed[2:-2], cleaned.angular_velocity[2:-2], atol=1e-9
        )
        # is_peak marks extremes of |angle| only.
        peaks = np.flatnonzero(cleaned.is_peak)
        assert peaks.size > 40
        inner = peaks[(peaks > 0) & (peaks < 5999)]
        magnitude = np.abs(cleaned.angle)
        assert (magnitude[inner] >= magnitude[inner - 1]).all()
        assert (magnitude[inner] >= magnitude[inner + 1]).all()


def test_a_file_with_another_header_is_refused(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text("time,angle\n0.0,0.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a raw export"):
        xu_pendulum.read_raw(path, 0.2)
    with pytest.raises(ValueError, match="not a cleaned file"):
        xu_pendulum.read_cleaned(path)


# The analysis.


def test_the_amplitude_correction_agrees_with_its_series():
    # T / T0 = 1 + A^2/16 + 11 A^4/3072 + 173 A^6/737280 + ... (rigid pendulum).
    for amplitude in (0.05, 0.2, 0.5, 0.8):
        series = (
            1
            + amplitude**2 / 16
            + 11 * amplitude**4 / 3072
            + 173 * amplitude**6 / 737280
        )
        t0 = xu_pendulum.corrected_period(np.array([series]), np.array([amplitude]))
        assert t0[0] == pytest.approx(1.0, abs=2 * amplitude**8 / 1000)


def test_the_release_the_centre_and_the_cycles(sample):
    expected = {  # release time [s], cycles used, first and last amplitude [deg]
        "len1_cond1_1": (3.06, 62, 43.7, 25.6),
        "len2_cond1_1": (2.90, 51, 16.5, 11.3),
        "len3_cond1_1": (2.67, 46, 24.1, 18.4),
        "len4_cond1_1": (2.42, 42, 38.8, 27.1),
        "len5_cond1_1": (2.55, 39, 22.9, 17.9),
    }
    for name, (released, used, first, last) in expected.items():
        run = sample.runs[name]
        assert run.time[xu_pendulum.release(run)] == pytest.approx(released)
        cycles = xu_pendulum.cycles(run)
        # The encoder's zero is the rest position at the start, within 0.01 rad
        # of the centre of the swing.
        assert abs(cycles.centre) < 0.01
        assert cycles.period.size == used
        assert np.degrees(cycles.amplitude[[0, -1]]) == pytest.approx(
            [first, last], abs=0.05
        )
        assert np.all(np.diff(cycles.amplitude) < 0.01)
        # The encoder step alone gives each period a lower bound of its
        # uncertainty, 0.27 ms (len1, 44 deg) to 1.4 ms (len2, 11 deg): one
        # per cycle, comparable to the cycles' scatter in the slowest runs.
        assert cycles.period_error.shape == cycles.period.shape
        assert cycles.period_error.min() > 0.00025
        assert cycles.period_error.max() < 0.0015


def test_the_periods_and_the_effective_lengths_are_the_dossiers(analysis):
    expected = {  # T0 [s], L_eff - L [mm]
        "len1_cond1_1": (0.99521, 9.8),
        "len2_cond1_1": (1.16662, 7.8),
        "len3_cond1_1": (1.31777, 5.0),
        "len4_cond1_1": (1.45284, 5.9),
        "len5_cond1_1": (1.56879, 3.9),
    }
    for period, l_eff in zip(
        analysis["periods"], analysis["effective_lengths"], strict=True
    ):
        t0, excess = expected[period.name]
        assert period.t0 == pytest.approx(t0, abs=2e-5)
        # The standard error of the mean over the cycles is 0.1 to 0.2 ms, the
        # scatter of one cycle 0.7 to 1.4 ms.
        assert 5e-5 < period.stderr < 2.5e-4
        assert 6e-4 < period.scatter < 1.5e-3
        assert 1000 * (l_eff - period.length) == pytest.approx(excess, abs=0.05)
    # The shortest pendulum: 2.1 % above 2 pi sqrt(L/g) of the stated length.
    first = analysis["periods"][0]
    assert xu_pendulum.simple_period(first.length) == pytest.approx(0.9751, abs=1e-4)
    assert first.t0 / xu_pendulum.simple_period(first.length) == pytest.approx(
        1.0206, abs=1e-4
    )


def test_the_line_through_the_five_lengths(analysis):
    fit = analysis["length_fit"]
    assert fit.ok
    # The slope means g = 9.95 +- 0.03 m/s^2, 1.5 % above the README's 9.799;
    # the intercept adds 13 mm to every stated length.
    g = analysis["g"]
    g_err = g * fit.stderr[0] / fit.value("a")
    assert g == pytest.approx(9.947, abs=0.001)
    assert g_err == pytest.approx(0.035, abs=0.001)
    assert (g - xu_pendulum.G_LOCAL) / g_err > 4
    assert 1000 * analysis["offset"] == pytest.approx(13.0, abs=0.05)
    # The points scatter about the line by up to 5.75e-3 s^2 in T0^2, far more
    # than the standard errors of the periods allow (2 T0 dT0 < 7e-4 s^2).
    assert np.abs(fit.residuals).max() == pytest.approx(5.75e-3, abs=1e-4)
    assert max(2 * p.t0 * p.stderr for p in analysis["periods"]) < 7e-4


def test_the_correction_removes_most_of_the_amplitude_dependence(sample):
    # In ms per degree: the raw slope, and the slope left after the correction.
    expected = {
        "len1_cond1_1": (1.441, 0.088),
        "len2_cond1_1": (0.524, -0.100),
        "len3_cond1_1": (0.908, -0.174),
        "len4_cond1_1": (1.936, 0.072),
        "len5_cond1_1": (1.645, 0.407),
    }
    per_degree = 1000 * np.pi / 180
    for name, (raw, left) in expected.items():
        slopes = xu_pendulum.amplitude_slopes(sample.runs[name])
        assert np.array(slopes) * per_degree == pytest.approx([raw, left], abs=0.001)
    # What is left has no common sign: no scale error of the angle explains it.
    left = [v for _, v in expected.values()]
    assert min(left) < 0 < max(left)


def test_the_damping_of_the_shortest_pendulum(sample):
    run = sample.runs["len1_cond1_1"]
    envelope, q = xu_pendulum.envelope_fit(run)
    assert envelope.value("tau") == pytest.approx(118.6, abs=0.1)
    assert envelope.stderr[1] == pytest.approx(0.61, abs=0.01)
    assert q == pytest.approx(374.5, abs=0.5)
    # The damping law is not determined in 60 s of air damping: the
    # exponential and the quadratic law fit within 0.5 mrad of each other,
    # near the encoder step of 3.1 mrad.
    rms = {name: 1000 * value for name, value in xu_pendulum.envelope_rms(run).items()}
    assert rms == pytest.approx(
        {"exponential": 3.49, "linear": 8.85, "quadratic": 3.96}, abs=0.01
    )


def test_the_damping_laws_of_the_other_lengths(sample):
    expected = {  # rms [mrad]: exponential, linear, quadratic
        "len2_cond1_1": (3.12, 2.22, 4.47),
        "len3_cond1_1": (3.81, 4.35, 3.91),
        "len4_cond1_1": (7.53, 9.16, 6.36),
        "len5_cond1_1": (3.16, 2.91, 3.49),
    }
    for name, values in expected.items():
        rms = xu_pendulum.envelope_rms(sample.runs[name])
        got = [1000 * rms[k] for k in ("exponential", "linear", "quadratic")]
        assert got == pytest.approx(list(values), abs=0.01), name
