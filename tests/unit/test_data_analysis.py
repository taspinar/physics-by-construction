"""The analysis core of ``pbc.data``: status, series, uncertainty, calibration,
and curve fitting, on synthetic data whose truth is known and on the samples.
"""

import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.adapters import (
    impedance_series,
    measured_elevation,
    modelled_elevation,
    strain_series,
    transmission_series,
)
from pbc.data.calibration import apply_gain_offset, mask_to_nan, valid_fraction
from pbc.data.fit import fit_curve
from pbc.data.flume import read_elevation
from pbc.data.gwosc import read_strain
from pbc.data.series import Series
from pbc.data.status import (
    FIGURE_STATUSES,
    allowed_statuses,
    needs_artifact,
    status_of,
)
from pbc.data.touchstone import read_touchstone
from pbc.data.uncertainty import (
    K95,
    normalised_difference,
    propagate,
    quadrature,
    robust_sigma,
    standard_error,
    standard_from_expanded,
)

AAL = SAMPLES_DIR / "aalborg-submerged-bar"
GW = SAMPLES_DIR / "gw150914-strain"
NPL = SAMPLES_DIR / "npl-onwafer-sparameters"


# --- status -----------------------------------------------------------------


def test_the_status_follows_from_the_artifact_type():
    assert status_of("raw-measured") == "measured"
    assert status_of("processed-measured") == "processed"
    assert status_of("calibrated-observation") == "calibrated"
    assert status_of("modelled-reference") == "simulated"
    assert status_of("synthetic-test") == "simulated"
    assert set(map(status_of, ("raw-measured", "modelled-reference"))) <= set(
        FIGURE_STATUSES
    )
    with pytest.raises(ValueError):
        status_of("beautiful")


def test_a_step_makes_a_measurement_processed_but_never_a_model_measured():
    assert status_of("raw-measured", ("smoothed",)) == "processed"
    assert status_of("calibrated-observation", ("selected",)) == "processed"
    assert status_of("modelled-reference", ("smoothed",)) == "simulated"


def test_a_card_allows_the_statuses_of_its_artifacts_and_no_others():
    cards = {
        "gw": {"artifacts": [{"type": "calibrated-observation"}]},
        "flume": {
            "artifacts": [
                {"type": "processed-measured"},
                {"type": "modelled-reference"},
            ]
        },
    }
    assert allowed_statuses(cards["gw"]) == {"calibrated", "processed"}
    assert allowed_statuses(cards["flume"]) == {"processed", "simulated"}
    assert "simulated" not in allowed_statuses(cards["gw"])
    assert "conceptual" not in allowed_statuses(cards["flume"])


# --- series -----------------------------------------------------------------


def make_series(artifact="raw-measured", n=11):
    x = np.arange(n, dtype=float)
    return Series(x=x, y=x**2, artifact=artifact, sigma=np.full(n, 0.5))


def test_an_untouched_series_is_raw_and_a_smoothed_one_is_not():
    raw = make_series()
    assert raw.is_raw and raw.status == "measured" and raw.disclosure() == ""
    smooth = raw.smooth(3)
    assert not smooth.is_raw and smooth.status == "processed"
    assert "moving average of 3" in smooth.disclosure()
    assert smooth.sigma is None, "a smoothed series does not keep per-sample sigma"
    assert raw.status == "measured", "the original is not changed"
    assert smooth.y[1] == pytest.approx((0 + 1 + 4) / 3)
    assert smooth.y[2] == pytest.approx((1 + 4 + 9) / 3)
    assert np.isnan(smooth.y[0]) and np.isnan(smooth.y[-1])


def test_selection_interpolation_and_masks_are_disclosed():
    s = make_series()
    picked = s.select(2, 5)
    assert picked.x.tolist() == [2, 3, 4, 5] and "selected 2 to 5 s" in picked.steps[0]
    assert picked.sigma.shape == picked.y.shape
    onto = s.interpolate_to(np.array([0.5, 1.5, 20.0]))
    assert onto.y[:2].tolist() == [0.5, 2.5] and np.isnan(onto.y[2])
    assert onto.status == "processed"
    holes = Series(np.arange(4.0), np.array([1, np.nan, 3, 4]), "raw-measured")
    clean = holes.drop_masked()
    assert clean.x.tolist() == [0, 2, 3] and "removed 1 masked" in clean.steps[0]
    assert make_series().drop_masked().is_raw, "nothing removed, nothing to disclose"


def test_interpolation_propagates_the_uncertainty_of_both_samples():
    s = Series(
        np.array([0.0, 1.0, 3.0]),
        np.array([0.0, 2.0, 2.0]),
        "raw-measured",
        sigma=np.array([0.3, 0.4, 1.2]),
    )

    onto = s.interpolate_to(np.array([0.0, 0.5, 1.0, 1.5, 3.0, 4.0]))

    # At a sample the uncertainty is the sample's own.
    assert onto.sigma[[0, 2, 4]] == pytest.approx([0.3, 0.4, 1.2])
    # Half way between independent samples: sqrt(0.5^2 s0^2 + 0.5^2 s1^2),
    # not the mean of the two.
    assert onto.sigma[1] == pytest.approx(0.25)
    assert onto.sigma[1] < (0.3 + 0.4) / 2
    # A quarter of the way: weights 0.75 and 0.25.
    assert onto.sigma[3] == pytest.approx(np.hypot(0.75 * 0.4, 0.25 * 1.2))
    assert np.isnan(onto.sigma[5]) and np.isnan(onto.y[5])


def test_interpolation_skips_a_masked_sample_also_in_the_uncertainty():
    s = Series(
        np.array([0.0, 1.0, 2.0]),
        np.array([0.0, np.nan, 4.0]),
        "raw-measured",
        sigma=np.array([0.6, 9.0, 0.8]),
    )

    onto = s.interpolate_to(np.array([1.0]))

    assert onto.y[0] == pytest.approx(2.0)
    assert onto.sigma[0] == pytest.approx(0.5)


def test_the_statuses_of_a_card_follow_the_artifact_that_is_shown():
    card = {
        "artifacts": [
            {"type": "processed-measured"},
            {"type": "modelled-reference"},
        ]
    }

    assert needs_artifact(card)
    assert not needs_artifact({"artifacts": [{"type": "raw-measured"}]})
    assert not needs_artifact({"artifacts": [{"type": "synthetic-test"}]})
    assert allowed_statuses(card, "processed-measured") == {"processed"}
    assert allowed_statuses(card, "modelled-reference") == {"simulated"}
    assert allowed_statuses(card, "raw-measured") == set()
    assert allowed_statuses({"artifacts": [{"type": "raw-measured"}]}) == {
        "measured",
        "processed",
    }


def test_a_series_refuses_inconsistent_shapes_and_an_even_window():
    with pytest.raises(ValueError):
        Series(np.arange(3.0), np.arange(4.0), "raw-measured")
    with pytest.raises(ValueError):
        make_series().smooth(4)


def test_the_samples_become_series_with_the_status_of_their_card():
    h1 = strain_series(read_strain(GW / "H-H1_GWOSC_4KHZ_R1-1126259447-32.txt.gz"))
    assert (h1.status, h1.y_unit) == ("calibrated", "1")
    s21 = transmission_series(
        read_touchstone(NPL / "coaxial_3dB_attenuator_0601_CORR.s2p")
    )
    assert (s21.status, s21.x_unit, s21.y_unit) == ("calibrated", "GHz", "dB")
    assert -4.5 < s21.y.mean() < -3.5
    experiment = read_elevation(AAL / "Exp_WC1_gauge05_surfaceElevation.csv")
    measured = measured_elevation(experiment, 5)
    model = modelled_elevation(
        read_elevation(AAL / "Msigma_WC1_gauge05_surfaceElevation_A.csv")
    )
    assert (measured.status, model.status) == ("processed", "simulated")
    expanded = experiment.column(5, "expanded unc")
    np.testing.assert_allclose(measured.sigma * K95, expanded)


def test_the_impedance_spectrum_becomes_processed_series_in_rising_frequency():
    from pbc.data.reference import bayreuth_rlc

    spectrum = bayreuth_rlc.load(SAMPLES_DIR / "bayreuth-rlc-impedance")
    modulus = impedance_series(spectrum, "modulus")
    phase = impedance_series(spectrum, "phase")
    for series in (modulus, phase):
        assert series.status == "processed" and series.sigma is None
        assert series.x_unit == "Hz" and np.all(np.diff(series.x) > 0)
    assert (modulus.y_unit, phase.y_unit) == ("ohm", "deg")
    # The file runs from high to low frequency; the series from low to high.
    assert modulus.y[0] == pytest.approx(abs(spectrum.impedance[-1]))
    assert phase.y[-1] == pytest.approx(np.degrees(np.angle(spectrum.impedance[0])))
    with pytest.raises(ValueError):
        impedance_series(spectrum, "real")


# --- uncertainty ------------------------------------------------------------


def test_the_robust_noise_level_recovers_sigma_in_the_presence_of_a_signal():
    rng = np.random.default_rng(1)
    noise = rng.normal(0.0, 2.0, 100_000)
    noise[:200] += 50.0  # a short, strong signal does not move the estimate
    assert robust_sigma(noise) == pytest.approx(2.0, rel=0.02)
    assert robust_sigma(np.array([np.nan, 1.0, -1.0, 1.0, -1.0])) > 0


def test_the_standard_error_of_repetitions_is_the_scatter_over_root_n():
    rng = np.random.default_rng(2)
    reps = rng.normal(0.0, 3.0, (5, 50_000))
    # The sample variance is unbiased, the sample standard deviation is not.
    rms = np.sqrt(np.mean(standard_error(reps) ** 2))
    assert rms == pytest.approx(3.0 / np.sqrt(5), rel=0.02)
    with pytest.raises(ValueError):
        standard_error(reps[:1])


def test_the_aalborg_mean_has_the_standard_error_of_its_repetitions():
    experiment = read_elevation(AAL / "Exp_WC1_gauge05_surfaceElevation.csv")
    reps = np.stack([experiment.column(5, f"rep {k}") for k in range(1, 6)], axis=1)
    ours = standard_error(reps, axis=1)
    theirs = standard_from_expanded(experiment.column(5, "expanded unc"))
    # The file's expanded uncertainty uses a coverage factor and may include
    # other components; the two agree in order of magnitude.
    ratio = np.median(theirs[ours > 0] / ours[ours > 0])
    assert 0.5 < ratio < 5


def test_propagation_matches_the_closed_form_for_a_product_and_a_quotient():
    a, sa, b, sb = 3.0, 0.1, 4.0, 0.2
    value, sigma = propagate(lambda x, y: x * y, [a, b], [sa, sb])
    assert value == pytest.approx(12.0)
    assert sigma == pytest.approx(np.hypot(b * sa, a * sb), rel=1e-6)
    value, sigma = propagate(lambda x, y: x / y, [a, b], [sa, sb])
    assert sigma == pytest.approx(np.hypot(sa / b, a * sb / b**2), rel=1e-6)
    assert quadrature(3.0, 4.0) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        propagate(lambda x: x, [1.0], [0.1, 0.2])


def test_propagation_agrees_with_a_monte_carlo_of_the_same_inputs():
    rng = np.random.default_rng(3)
    gain, s_gain, off, s_off = 2.0, 0.05, 1.0, 0.1
    counts = np.array([10.0, 100.0])
    value, sigma = apply_gain_offset(counts, gain, off, s_gain, s_off, 0.5)
    draws = rng.normal(gain, s_gain, (100_000, 1)) * rng.normal(
        counts, 0.5, (100_000, 2)
    ) + rng.normal(off, s_off, (100_000, 1))
    np.testing.assert_allclose(sigma, draws.std(axis=0), rtol=0.02)
    np.testing.assert_allclose(value, gain * counts + off)


def test_two_values_agree_within_the_uncertainty_when_the_difference_is_small():
    z = normalised_difference(10.0, 0.3, 10.5, 0.4)
    assert abs(z) == pytest.approx(1.0)


# --- calibration and masks --------------------------------------------------


def test_masks_become_nan_whatever_the_source_wrote():
    values = np.array([[0.0, 1.5], [2.5, 0.0]])
    out = mask_to_nan(values, sentinel=0.0)
    assert np.isnan(out).tolist() == [[True, False], [False, True]]
    flags = np.array([[False, True], [False, False]])
    both = mask_to_nan(values, sentinel=0.0, invalid=flags)
    assert valid_fraction(both) == pytest.approx(0.25)
    assert values[0, 0] == 0.0, "the input is not changed"
    with pytest.raises(ValueError):
        mask_to_nan(values, invalid=np.array([True]))


def test_the_modelled_flume_runs_report_their_masks():
    d_sph = read_elevation(AAL / "DSPH_WC1_gauge05_surfaceElevation_A.csv")
    assert 0.0 < 1 - valid_fraction(d_sph.values) < 1e-2


# --- fitting ----------------------------------------------------------------


def damped(t, amplitude, rate, omega, phase):
    return amplitude * np.exp(-rate * t) * np.cos(omega * t + phase)


TRUTH = (2.0, 0.4, 5.0, 0.3)


def synthetic(seed, sigma=0.05):
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, 8.0, 400)
    return t, damped(t, *TRUTH) + rng.normal(0.0, sigma, t.size)


def test_the_fit_recovers_known_parameters_within_their_reported_uncertainty():
    t, y = synthetic(4)
    result = fit_curve(
        damped,
        t,
        y,
        p0=(1.5, 0.3, 4.9, 0.0),
        sigma=0.05,
        names=("amplitude", "rate", "omega", "phase"),
    )
    assert result.ok and result.warnings == ()
    for name, truth in zip(result.names, TRUTH, strict=True):
        error = abs(result.value(name) - truth)
        assert error < 4 * result.stderr[result.names.index(name)], name
    # A stated tolerance, independent of the reported uncertainty.
    np.testing.assert_allclose(result.params, TRUTH, rtol=0.03, atol=0.02)
    assert result.reduced_chi2 == pytest.approx(1.0, abs=0.25)
    assert result.dof == 396
    low, high = result.interval("rate")
    assert low < TRUTH[1] < high


def test_the_reported_uncertainty_covers_the_truth_about_as_often_as_it_says():
    covered = 0
    runs = 150
    for seed in range(runs):
        t, y = synthetic(100 + seed)
        fit = fit_curve(damped, t, y, p0=(1.5, 0.3, 4.9, 0.0), sigma=0.05)
        low, high = fit.interval("p1")
        covered += low < TRUTH[1] < high
    assert 0.90 < covered / runs < 0.99


def test_without_sigma_the_scatter_of_the_residuals_sets_the_uncertainty():
    t, y = synthetic(5, sigma=0.2)
    free = fit_curve(damped, t, y, p0=(1.5, 0.3, 4.9, 0.0))
    told = fit_curve(damped, t, y, p0=(1.5, 0.3, 4.9, 0.0), sigma=0.2)
    assert not free.absolute_sigma and told.absolute_sigma
    np.testing.assert_allclose(free.stderr, told.stderr, rtol=0.15)
    assert free.residuals.std() == pytest.approx(0.2, rel=0.1)


def test_a_wrong_uncertainty_is_reported_through_the_reduced_chi_square():
    t, y = synthetic(6, sigma=0.2)
    fit = fit_curve(damped, t, y, p0=(1.5, 0.3, 4.9, 0.0), sigma=0.05)
    assert fit.reduced_chi2 > 3
    assert any("reduced chi-square" in w for w in fit.warnings) and not fit.ok


def test_parameters_that_only_appear_as_a_product_are_reported_as_not_identified():
    x = np.linspace(0, 1, 50)
    y = 6.0 * x
    fit = fit_curve(lambda x, a, b: a * b * x, x, y, p0=(2.0, 2.5), sigma=0.1)
    assert fit.identifiable == (False, False)
    assert np.isinf(fit.stderr).all()
    assert any("do not determine a, b" in w for w in fit.warnings) or any(
        "do not determine p0, p1" in w for w in fit.warnings
    )
    assert fit.singular_ratio < 1e-6
    # The product itself is determined.
    assert fit.params[0] * fit.params[1] == pytest.approx(6.0, rel=1e-6)


def test_two_nearly_equal_rates_are_flagged_and_two_distinct_ones_are_not():
    t = np.linspace(0, 4, 60)

    def two_exponentials(t, a, k1, b, k2):
        return a * np.exp(-k1 * t) + b * np.exp(-k2 * t)

    rng = np.random.default_rng(7)
    near = two_exponentials(t, 1.0, 1.0, 1.0, 1.001) + rng.normal(0, 1e-3, t.size)
    far = two_exponentials(t, 1.0, 0.5, 1.0, 3.0) + rng.normal(0, 1e-3, t.size)
    bad = fit_curve(two_exponentials, t, near, (1.0, 0.9, 1.0, 1.1), sigma=1e-3)
    good = fit_curve(two_exponentials, t, far, (1.2, 0.6, 0.8, 2.5), sigma=1e-3)
    assert not all(bad.identifiable)
    assert all(good.identifiable) and good.ok


def test_the_fit_ignores_masked_samples_and_refuses_too_few_samples():
    t, y = synthetic(8)
    y[10:20] = np.nan
    fit = fit_curve(damped, t, y, p0=(1.5, 0.3, 4.9, 0.0), sigma=0.05)
    assert fit.dof == 400 - 10 - 4
    with pytest.raises(ValueError):
        fit_curve(damped, t[:3], y[20:23], p0=(1, 1, 1, 1))
    with pytest.raises(ValueError):
        fit_curve(damped, t, y, p0=(1, 1, 1, 1), names=("a",))


def test_the_fit_of_the_measured_wave_finds_its_period():
    experiment = read_elevation(AAL / "Exp_WC1_gauge05_surfaceElevation.csv")
    measured = measured_elevation(experiment, 5).select(6.0, 14.0)

    def wave(t, amplitude, omega, phase, offset):
        return amplitude * np.cos(omega * t + phase) + offset

    from pbc.data.reference import aalborg_flume

    period = aalborg_flume.dominant_period(measured.x, measured.y, 6, 14)
    fit = fit_curve(
        wave,
        measured.x,
        measured.y,
        p0=(0.012, 2 * np.pi / period, 0.0, 0.0),
        names=("amplitude", "omega", "phase", "offset"),
    )
    # The spectral line of an 8 s window is only known to one bin, 1/8 Hz; the
    # fit is finer and must lie within that bin.
    assert abs(fit.value("omega") / (2 * np.pi) - 1 / period) < 1 / 8
    low, high = fit.interval("omega")
    assert high - low < 0.1 * fit.value("omega"), "the frequency is well determined"
    assert fit.identifiable == (True,) * 4
