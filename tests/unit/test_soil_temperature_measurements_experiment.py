"""The experiment of "Soil temperature measurements lab" (thermodynamics 10):
what the page claims is what the committed sample gives, the diffusivities
are the dossier's, the stated uncertainties' assumptions hold on the data,
and the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import soil_temperature_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import dwd_soil
from pbc.experiment import encode
from pbc.thermodynamics.experiments import soil_temperature_measurements as lab

MODULE = "pbc.thermodynamics.experiments.soil_temperature_measurements"
PAGE = "thermodynamics/10-soil-temperature-measurements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("soil_temperature_measurements")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def readings():
    return lab.load_readings()


@pytest.fixture(scope="module")
def waves(readings):
    annual, hourly = readings
    return dwd_soil.annual_wave(annual), dwd_soil.diurnal_wave(hourly)


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def _column(found: dict, table: str, column: int) -> list[float]:
    return [float(row[column]) for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_series_carries_the_status_of_the_card(readings):
    annual, _ = readings
    series = soil_temperature_series(annual, 0)
    assert series.artifact == "processed-measured"
    assert series.status == "processed"
    assert series.y_unit == "degC" and series.x_unit == "d"
    assert series.sigma is None  # the record gives no sensor accuracy
    # Four readings a day; the one gap is the two absent rows of 2023-09-05.
    steps = np.diff(series.x)
    assert np.all(steps[steps != 0.25] == 0.75) and np.sum(steps != 0.25) == 1
    assert np.isnan(series.y).sum() == 1  # 2023-09-04 12 h at 5 cm


def test_the_diffusivities_are_the_dossiers(waves):
    # Two implementations, the lab's lines through fit_curve and the
    # reference module's np.polyfit, give the same numbers.
    for wave in waves:
        ours = lab.diffusivity(wave)
        theirs = dwd_soil.estimate(wave)
        assert (ours["amplitude"]["alpha"], ours["phase"]["alpha"]) == pytest.approx(
            theirs.kappa, rel=1e-6
        )
        assert (ours["amplitude"]["sem"], ours["phase"]["sem"]) == pytest.approx(
            theirs.standard_error, rel=1e-6
        )
        np.testing.assert_allclose(
            np.column_stack([ours["amplitude"]["single"], ours["phase"]["single"]]),
            theirs.per_period,
            rtol=1e-6,
        )
        for (_, a, p), (*_, ra, rp) in zip(
            lab.pairs(wave), dwd_soil.pairwise(wave), strict=True
        ):
            assert (a, p) == pytest.approx((ra, rp), rel=1e-12)
    # (fit_curve converges to the least-squares line to about 1e-8.)


def test_the_record_is_what_the_observational_claim_says(results):
    _, found = results
    assert found["numbers"]["annual-rows"] == "14,610"
    assert found["numbers"]["hourly-rows"] == "11,040"
    # The dossier: 2023-09-04 12 h misses 5, 10, 20 cm; 2023-08-24 14-16 h
    # misses 5 and 10 cm.
    assert _number(found, "missing-annual") == 3
    assert _number(found, "missing-hourly") == 6
    assert _number(found, "shallow-min") == -10.0
    lowest = _column(found, "record", 3)
    highest = _column(found, "record", 4)
    means = _column(found, "record", 2)
    # Smaller swings with depth, about the same mean.
    assert lowest == sorted(lowest) and highest == sorted(highest, reverse=True)
    assert max(means) - min(means) < 0.5
    assert _number(found, "shallow-max") == highest[0]
    assert _number(found, "deep-min") == lowest[-1]


def test_the_scheme_settles_into_the_damped_wave(results):
    _, found = results
    assert _number(found, "check-amplitude-error") < 0.1  # per cent
    assert _number(found, "check-lag-error") < 1e-3  # rad
    rows = found["tables"]["scheme-check"]["rows"]
    for _, exact_a, scheme_a, exact_lag, scheme_lag in rows:
        assert float(scheme_a) == pytest.approx(float(exact_a), abs=2e-4)
        assert float(scheme_lag) == pytest.approx(float(exact_lag), abs=1e-3)


def test_the_waves_decay_and_lag_as_the_claim_says(results, waves):
    _, found = results
    annual, diurnal = waves
    assert np.all(np.diff(annual.amplitude.mean(0)) < 0)
    assert np.all(np.diff(annual.lag.mean(0)) > 0)
    assert np.all(np.diff(diurnal.amplitude.mean(0)) < 0)
    assert np.all(np.diff(diurnal.lag.mean(0)) > 0)
    assert _number(found, "annual-a5") == pytest.approx(12.5, abs=0.05)
    assert _number(found, "annual-a100") == pytest.approx(9.3, abs=0.05)
    assert _number(found, "annual-lag100") == 16
    assert _number(found, "daily-a5") == pytest.approx(6.4, abs=0.05)
    assert _number(found, "daily-a50") == pytest.approx(0.46, abs=0.005)
    assert _number(found, "daily-lag50") == pytest.approx(9.8, abs=0.05)
    # Below the 0.1 K of the readings at 100 cm, as the page says.
    assert _number(found, "daily-a100") < 0.05


def test_the_four_diffusivities_and_their_errors(results):
    _, found = results
    # The dossier: 1.015 +- 0.025, 1.147 +- 0.009, 1.084 +- 0.013,
    # 1.119 +- 0.009 (1e-6 m^2/s).
    alpha = _column(found, "diffusivity", 1)
    sem = _column(found, "diffusivity", 2)
    line = _column(found, "diffusivity", 4)
    assert alpha == pytest.approx([1.015, 1.147, 1.084, 1.119], abs=0.0005)
    assert sem == pytest.approx([0.025, 0.009, 0.013, 0.009], abs=0.0005)
    # The line through the mean wave has more error than the mean in every
    # row: the departures persist from year to year (the page).
    assert all(a > b for a, b in zip(line, sem, strict=True))
    assert _number(found, "year-depth") == pytest.approx(3.2, abs=0.05)
    assert _number(found, "day-depth") == pytest.approx(17.3, abs=0.05)
    # The damping depths scale with the root of the period to a few per cent.
    model = _number(found, "depth-ratio-model")
    for name in ("depth-ratio-amp", "depth-ratio-phase"):
        assert _number(found, name) == pytest.approx(model, rel=0.05)


def test_the_daily_lag_leaves_its_line_by_more_than_its_error(waves):
    # The caption of fig-depth-profiles: residuals of a few hundredths, for
    # the daily lag larger than the scatter between summers.
    _, diurnal = waves
    line = lab.diffusivity(diurnal)["lines"]["phase"]
    error = diurnal.lag.std(0, ddof=1) / np.sqrt(len(diurnal.periods))
    worst = int(np.argmax(np.abs(line.residuals)))
    assert np.abs(line.residuals).max() < 0.05
    assert abs(line.residuals[worst]) > 3 * error[worst]


def test_the_stated_errors_rest_on_assumptions_that_hold(results):
    _, found = results
    # Within a year the residuals persist for days, and the error that
    # assumes independent readings falls far short of the scatter between
    # years, at both depths of the table.
    for _, error, scatter, rho_day, rho_ten in found["tables"]["independence"]["rows"]:
        assert float(scatter) > 3 * float(error)
        assert float(rho_day) > 0.5 and float(rho_ten) > 0.3
    # Between years and summers no positive correlation outside the band
    # of independent values.
    for prefix, band in (("year", "band-years"), ("day", "band-summers")):
        for method in ("amp", "phase"):
            assert abs(_number(found, f"{prefix}-{method}-rho1")) < _number(found, band)
    assert _number(found, "year-amp-rho1") < 0 and _number(found, "year-phase-rho1") < 0


def test_where_the_uniform_soil_fails(results):
    _, found = results
    assert _number(found, "year-gap") == pytest.approx(5.0, abs=0.05)
    assert _number(found, "day-gap") > 2
    assert _number(found, "four-low") == 1.01 and _number(found, "four-high") == 1.15
    assert _number(found, "four-half-range") == 6
    assert _number(found, "pair-shallow-amp") == pytest.approx(2.49, abs=0.005)
    assert _number(found, "pair-shallow-drop") == 1
    low, high = _number(found, "pairs-low"), _number(found, "pairs-rest-high")
    assert (low, high) == pytest.approx((0.88, 1.53), abs=0.005)
    # "Still spread over more than half of their mean value."
    assert high - low > 0.5 * _number(found, "four-mean")
    # The spread of the four is larger than any standard error.
    spread = _number(found, "four-high") - _number(found, "four-low")
    assert spread > 2 * max(_column(found, "diffusivity", 2))


def test_the_shown_day_follows_its_rule(readings):
    _, hourly = readings
    day = lab.typical_day(hourly, lab.SHOWN_SUMMER)
    assert str(day).startswith(f"{lab.SHOWN_SUMMER}-0")
    start = day.astype("datetime64[h]")
    inside = (hourly.time >= start) & (hourly.time < start + np.timedelta64(24, "h"))
    assert inside.sum() == 24


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte (straight model
    # lines are drawn from their two ends, as in MAT6).
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        residuals = label in ("fig-harmonic-fits", "fig-depth-profiles")
        assert check_figure(figure, residuals=residuals) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if "measured" in text or "cm [" in text:
                    assert "[processed]" in text, (label, text)
                if "exp(-z/d)" in text or "lag z/d" in text:
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the labs keep their figures under 0.75 MB.
    # Locally these are about 0.55 MB. The Linux build in CI is larger: on
    # a3263c1 it measured 669,684 bytes against 580,399 locally, about
    # 15 % more, so the local total is kept below 0.56 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 650_000, total
