"""The experiment of "Turbulent boundary layer measurements lab" (fluids 8):
what the page claims is what the committed samples give, the fits and the
shape factors are the dossiers', the stated uncertainties' assumptions are
checked on the data, and the figures follow the conventions of a
measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import (
    boundary_layer_profile_series,
    hot_wire_intensity_series,
    hot_wire_profile_series,
)
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import grazing_flow_hwa, tudelft_boundary_layer
from pbc.experiment import encode
from pbc.fluids.experiments import turbulent_boundary_layer_measurements as lab

MODULE = "pbc.fluids.experiments.turbulent_boundary_layer_measurements"
PAGE = "fluids/08-turbulent-boundary-layer-measurements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("turbulent_boundary_layer_measurements")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def records():
    return lab.load_records()


@pytest.fixture(scope="module")
def stations():
    return lab.solid_stations()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def _column(found: dict, table: str, column: int) -> list[float]:
    return [float(row[column]) for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_series_carry_the_status_of_the_cards(records):
    tudelft, hot_wire = records
    piv, ptv = tudelft["U10"]
    for profile in (piv, ptv):
        series = boundary_layer_profile_series(profile)
        assert series.artifact == "processed-measured"
        assert series.status == "processed"
        assert series.sigma is None  # the record gives no uncertainty
        assert series.x_unit == "m" and series.y_unit == "m/s"
    # PTV y is read in millimetres: its points end near 2 mm, below the
    # PIV profile's 140 mm.
    assert boundary_layer_profile_series(ptv).x.max() < 2.2e-3
    s = hot_wire["D00V20"]
    series = hot_wire_profile_series(s)
    assert series.status == "processed"
    # The record's 95 % half-width becomes a standard uncertainty.
    np.testing.assert_allclose(series.sigma * 1.959964, s.U_uncertainty, rtol=1e-6)
    assert np.all(np.diff(series.x) > 0)
    # The TI bounds: the larger distance to either bound, as a standard one.
    intensity = hot_wire_intensity_series(s)
    assert intensity.status == "processed" and intensity.y_unit == "%"
    np.testing.assert_array_equal(intensity.y, s.TI)
    half = np.maximum(s.TI_upper - s.TI, s.TI - s.TI_lower)
    np.testing.assert_allclose(intensity.sigma * 1.959964, half, rtol=1e-6)
    assert np.all(s.TI_lower <= s.TI) and np.all(s.TI_upper >= s.TI)


def test_the_hot_wire_profiles_are_the_middle_station(records, stations):
    _, hot_wire = records
    for case, s in hot_wire.items():
        assert s.x_over_L == pytest.approx(0.0, abs=1e-9)
        assert s is not None and stations[case][lab.CENTRE].x_over_L == s.x_over_L
        assert len(stations[case]) == 5


def test_the_fits_and_shape_factors_are_the_dossiers(records, stations):
    # Two implementations: the lab's fit_curve and the reference modules'
    # np.polyfit give the same kappa and B, window by window.
    tudelft, _ = records
    for piv, ptv in tudelft.values():
        found = lab.tudelft_log_law(piv)
        kappa, b, n = tudelft_boundary_layer.log_fit(piv)
        assert (found["kappa"], found["B"]) == pytest.approx((kappa, b), rel=1e-6)
        assert found["points"] == n
        (k_lo, k_hi), (b_lo, b_hi) = tudelft_boundary_layer.log_fit_range(piv)
        assert found["kappa-range"] == pytest.approx((k_lo, k_hi), rel=1e-6)
        assert found["B-range"] == pytest.approx((b_lo, b_hi), rel=1e-6)
        y, u = tudelft_boundary_layer.spliced(piv, ptv)
        h = tudelft_boundary_layer.shape_factor(y, u, piv.delta)[2]
        assert lab.shape_factors({"x": (piv, ptv)}, {c: [] for c in lab.SOLID})[
            "recomputed"
        ][0] == pytest.approx(h, rel=1e-12)
    for case in lab.SOLID:
        for s in stations[case]:
            sel = lab.window(s.yplus, s.y_over_delta, lab.LOG_LOWER, lab.LOG_UPPER)
            fit = lab.log_fit(s.yplus[sel], s.Uplus[sel])
            kappa, b, _ = grazing_flow_hwa.log_fit(s)
            assert (fit.value("kappa"), fit.value("B")) == pytest.approx(
                (kappa, b), rel=1e-6
            )


def test_the_records_are_what_the_observational_claim_says(results):
    _, found = results
    # The dossier: Re_tau 1351 to 4647, Re_theta 3079 to 12020, u_tau within
    # 1.1 % of Coles-Fernholz.
    assert (
        _number(found, "re-tau-low") == 1351 and _number(found, "re-tau-high") == 4647
    )
    assert _number(found, "re-theta-low") == 3079
    assert _number(found, "re-theta-high") == 12020
    assert _number(found, "utau-deviation") == 1.1
    # The record's delta is about 1.3 delta_99; the hot wire's is delta_99.
    assert _number(found, "delta-record-low") == 1.24
    assert _number(found, "delta-record-high") == 1.30
    assert _number(found, "hw-delta-gap") < 1.0
    assert (_number(found, "hw-re-tau-low"), _number(found, "hw-re-tau-high")) == (
        1126,
        1790,
    )
    # "Their Re_theta lies between those of the two lowest TU Delft speeds."
    re_theta = _column(found, "records", 5)
    assert all(re_theta[0] < r < re_theta[1] for r in re_theta[4:])
    assert _number(found, "hw-points") == 43


def test_the_blasius_check(results):
    _, found = results
    assert _number(found, "blasius-worst") < 2.0  # parts per million
    for *_, gap in found["tables"]["blasius"]["rows"]:
        assert float(gap) < 2e-6
    assert _number(found, "blasius-h") == 2.591
    assert _number(found, "blasius-curvature") == 0.3321


def test_the_laminar_layer_is_far_from_the_measured_one(results):
    _, found = results
    assert (_number(found, "re-x-low"), _number(found, "re-x-high")) == (2.1, 8.3)
    assert (_number(found, "delta-ratio-low"), _number(found, "delta-ratio-high")) == (
        4,
        7,
    )
    assert (_number(found, "theta-ratio-low"), _number(found, "theta-ratio-high")) == (
        3,
        6,
    )
    assert (_number(found, "cf-ratio-low"), _number(found, "cf-ratio-high")) == (7, 11)
    # "The ratios grow with the speed": the rows are in increasing speed.
    rows = found["tables"]["laminar"]["rows"]
    for measured, laminar in ((3, 2), (5, 4), (7, 6)):
        ratio = [float(r[measured]) / float(r[laminar]) for r in rows]
        assert ratio == sorted(ratio), (measured, ratio)


def test_the_shape_factors(results):
    _, found = results
    assert (_number(found, "h-low"), _number(found, "h-high")) == (1.33, 1.37)
    assert _number(found, "h-tudelft-low") == 1.331
    assert _number(found, "h-tudelft-high") == 1.367
    assert _number(found, "h-hw-low") == 1.326
    assert _number(found, "h-hw-high") == 1.357
    assert _number(found, "h-recomputed-gap") < 1.5
    # About half the laminar value.
    assert 0.5 < _number(found, "h-high") / _number(found, "blasius-h") < 0.55


def test_the_log_law_and_its_window(results):
    _, found = results
    assert (_number(found, "kappa-low"), _number(found, "kappa-high")) == (0.40, 0.41)
    assert (_number(found, "b-low"), _number(found, "b-high")) == (4.8, 5.2)
    window = (_number(found, "kappa-window-low"), _number(found, "kappa-window-high"))
    assert window == (0.35, 0.43)
    assert (_number(found, "b-window-low"), _number(found, "b-window-high")) == (
        3.0,
        5.5,
    )
    assert _number(found, "kappa-round") == 0.4
    # "The spread over the windows is several times the spread between the
    # speeds."
    kappas = _column(found, "log-law", 2)
    assert window[1] - window[0] > 4 * (max(kappas) - min(kappas))


def test_the_errors_and_their_assumption(records, results):
    _, found = results
    tudelft, _ = records
    fits = [lab.tudelft_log_law(piv) for piv, _ in tudelft.values()]
    half = max((f["kappa-range"][1] - f["kappa-range"][0]) / 2 for f in fits)
    # The least-squares error is an order of magnitude below the half-range.
    assert max(f["kappa-error"] for f in fits) * 10 < half
    # The residuals are far from independent ...
    assert min(f["rho"] for f in fits) > 0.85
    assert max(f["effective"] for f in fits) < 3.5
    # ... and even inflated by it the error stays below the window's.
    inflated = max(
        f["kappa-error"] * np.sqrt(f["points"] / f["effective"]) for f in fits
    )
    assert inflated < half
    assert _number(found, "kappa-error-inflated") < _number(found, "kappa-window-half")
    # A one per cent error of u_tau moves kappa and B far less than the
    # window does.
    assert _number(found, "utau-kappa-shift") == 0.004
    assert _number(found, "utau-b-shift") == 0.08
    assert 5 * _number(found, "utau-kappa-shift") < _number(found, "kappa-window-half")
    # The caption of fig-wall-units: residuals within two tenths.
    assert max(np.abs(f["fit"].residuals).max() for f in fits) < 0.2
    _, hot_wire = records
    for station in hot_wire.values():
        sel = lab.window(
            station.yplus, station.y_over_delta, lab.LOG_LOWER, lab.LOG_UPPER
        )
        fit = lab.log_fit(station.yplus[sel], station.Uplus[sel])
        assert np.abs(fit.residuals).max() < 0.2
    # Check of the correlation itself on a known series: independent noise
    # gives a correlation near zero, a smooth arc one near one.
    rng = np.random.default_rng(441)
    assert abs(lab.neighbour_correlation(rng.normal(size=4000))) < 0.05
    assert lab.neighbour_correlation(np.sin(np.linspace(0, 3, 50))) > 0.9


def test_the_hot_wire_law_lies_inside_the_tudelft_windows(results):
    _, found = results
    assert (_number(found, "hw-kappa-low"), _number(found, "hw-kappa-high")) == (
        0.39,
        0.42,
    )
    assert (_number(found, "hw-b-low"), _number(found, "hw-b-high")) == (4.5, 5.4)
    assert _number(found, "hw-kappa-low") >= _number(found, "kappa-window-low")
    assert _number(found, "hw-kappa-high") <= _number(found, "kappa-window-high")
    assert _number(found, "hw-b-low") >= _number(found, "b-window-low")
    assert _number(found, "hw-b-high") <= _number(found, "b-window-high")
    assert (_number(found, "hw-points-low"), _number(found, "hw-points-high")) == (
        6,
        10,
    )


def test_the_turbulence_intensities(results, records):
    _, found = results
    tudelft, _ = records
    rows = found["tables"]["intensity"]["rows"]
    piv = np.array([[float(v) for v in r[1:4]] for r in rows[:4]])
    wire = np.array([[float(v) for v in r[1:4]] for r in rows[4:]])
    gaps = piv.mean(0) - wire.mean(0)
    # The PIV higher on average at every height, by a few tenths.
    assert np.all(gaps > 0.2) and np.all(gaps < 0.45)
    assert _number(found, "ti-gap-relative") <= 6
    # The hot wire's statistical 95 % TI bounds, as the dossier says at most
    # 0.001 percentage points from TI, far below the smallest gap.
    bound = _number(found, "hw-ti-bound")
    assert 0 < bound <= 0.001
    assert bound < gaps.min() / 100
    assert (_number(found, "ti-low"), _number(found, "ti-high")) == (5.4, 7.9)
    # The hot wire's inner peak, the PIV's rise at its first points.
    assert (_number(found, "hw-peak-low"), _number(found, "hw-peak-high")) == (2.6, 2.7)
    assert _number(found, "hw-peak-yplus") == 13
    assert (_number(found, "piv-peak-low"), _number(found, "piv-peak-high")) == (
        4.5,
        5.5,
    )
    for piv_profile, _ in tudelft.values():
        uplus = np.sqrt(piv_profile.uu) / piv_profile.Utau
        assert int(np.argmax(uplus)) <= 2  # at the first points
    ratio = _number(found, "piv-peak-high") / _number(found, "hw-peak-high")
    assert 1.6 < ratio < 2.2  # "about twice as much"
    # The Reynolds shear stress peaks below one.
    assert (_number(found, "stress-low"), _number(found, "stress-high")) == (0.91, 0.97)
    assert (_number(found, "ptv-piv-low"), _number(found, "ptv-piv-high")) == (0.3, 7.0)


def test_the_hot_wire_bounds_are_hidden_by_its_markers(results, experiment):
    # The caption of fig-turbulence-intensity: the hot wire's 95 % TI bounds
    # (hw-ti-bound in the text below it, under 1e-3 percentage points) are
    # far narrower than its markers and are not drawn (Issue #501).
    _, found = results
    bound = _number(found, "hw-ti-bound")
    assert bound < 1e-3
    figure = experiment.figures["fig-turbulence-intensity"]()
    try:
        ax = figure.axes[0]
        markers = [line for line in ax.lines if line.get_linestyle() == "None"]
        assert len(markers) == 3
        for line in markers:
            radius = line.get_markersize() / 2 * figure.dpi / 72  # in pixels
            x, y = line.get_xdata()[0], line.get_ydata()[0]
            low, high = ax.transData.transform([(x, y), (x, y + bound)])
            assert high[1] - low[1] < radius / 10
    finally:
        plt.close(figure)


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte (straight model
    # lines are drawn from their two ends, as in MAT6 and T7).
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=label == "fig-wall-units") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                measured = ", PIV [" in text or ", PTV" in text or "hot wire, " in text
                if measured and "[" in text:
                    assert "[processed]" in text, (label, text)
                if "Blasius" in text or "log law" in text or "sublayer" in text:
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The labs keep their figures under 0.75 MB of the page's 3 MB. The Linux
    # build in CI came out up to 16.6 % larger than the local one (W7), so
    # the local total is kept at most 0.70 of that bound.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
