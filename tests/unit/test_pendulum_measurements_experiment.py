"""The experiment of "Pendulum measurements lab" (mechanics 20): what the
page claims is what the committed sample gives, the periods are the
dossier's, and the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import pendulum_angle_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import xu_pendulum
from pbc.experiment import encode
from pbc.mechanics.experiments import pendulum_measurements as lab

MODULE = "pbc.mechanics.experiments.pendulum_measurements"
PAGE = "mechanics/20-pendulum-measurements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("pendulum_measurements")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def sample():
    return lab.load_sample()


@pytest.fixture(scope="module")
def traces(sample):
    return lab.load_traces(sample)


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def _column(found: dict, table: str, column: int) -> list[float]:
    return [float(row[column]) for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_angle_series_carries_the_status_of_the_card(sample):
    run = sample.runs["len1_cond1_1"]
    series = pendulum_angle_series(run)
    assert series.artifact == "raw-measured"
    assert series.status == "measured"
    assert series.select(0.0, 20.0).status == "processed"
    assert series.x_unit == "s" and series.y_unit == "rad"
    assert series.sigma is None  # the record gives no uncertainty


def test_the_lab_uses_eighteen_runs_over_the_creators_window(sample, traces):
    assert len(traces) == 18
    assert {name for name in traces if "_cond3_" in name} == {
        "len1_cond3_1",
        "len1_cond3_2",
        "len1_cond3_3",
    }
    for trace in traces.values():
        assert trace.time.size == 6000
        assert trace.time[0] == pytest.approx(0.0, abs=1e-9)
    # A first trial read from its raw file is the creators' cleaned file.
    cleaned = sample.cleaned
    first = traces["len1_cond1_1"]
    np.testing.assert_allclose(first.time, cleaned.time, atol=1e-9)
    np.testing.assert_allclose(first.angle, cleaned.angle, atol=1e-12)


def test_the_periods_are_those_of_the_reference_module_within_the_window(
    sample, traces
):
    # The dossier's periods are over the whole record after the release;
    # over the creators' window the cycles differ a little, the periods by
    # well below the spread of the trials.
    for name, run in sample.runs.items():
        ours = lab.period_of(traces[name]).t0
        theirs = xu_pendulum.period(run).t0
        assert abs(ours - theirs) < 3e-4, name
    # The same cycle analysis: identical on the same rows.
    whole = sample.runs["len2_cond1_1"]
    trace = lab.Trace(whole.name, whole.length, whole.time, whole.angle)
    np.testing.assert_array_equal(
        lab.cycles_of(trace).period, xu_pendulum.cycles(whole).period
    )


def test_the_simulated_check_recovers_the_model(results):
    _, found = results
    rows = found["tables"]["simulation-check"]["rows"]
    set_values = [float(row[2]) for row in rows]
    recovered = [float(row[3]) for row in rows]
    assert set_values == [lab.SIMULATED_T0, lab.SIMULATED_GAMMA, lab.SIMULATED_KAPPA]
    assert _number(found, "sim-t0-error") < 30  # microseconds
    assert recovered[0] == pytest.approx(lab.SIMULATED_T0, abs=3e-5)
    # The envelope's rates within ten per cent: the bias of averaging a
    # swing of this size as a cosine, which the page states.
    assert _number(found, "sim-gamma-off") <= 10
    assert _number(found, "sim-kappa-off") <= 10
    # The encoder alone scatters a cycle's corrected period by about 0.2 ms;
    # the measured cycles scatter about three times more (the page).
    assert 0.15 < _number(found, "sim-scatter") < 0.3
    ratio = _number(found, "short-scatter") / _number(found, "sim-scatter")
    assert 2.5 < ratio < 3.5
    # The two laws are told apart on the simulated decay.
    assert _number(found, "sim-rms-linear") > 4 * _number(found, "sim-rms-both")
    # No amplitude dependence is left by the analysis itself, far below the
    # measured remainder (the page).
    assert abs(_number(found, "sim-slope")) < 0.01
    assert _number(found, "slope-after-low") > 5 * abs(_number(found, "sim-slope"))


def test_the_record_facts_of_the_observational_claim(results):
    _, found = results
    # The dossier: 6,896 rows, the release 3.06 s after the start, the
    # largest |angle| of the file.
    assert found["numbers"]["rows"] == "6896"
    assert found["numbers"]["release-time"] == "3.06"
    assert found["numbers"]["release-angle"] == "46"
    assert found["numbers"]["window-cycles"] == "57"
    assert found["numbers"]["first-amplitude"] == "43"
    assert found["numbers"]["last-amplitude"] == "26"
    assert found["numbers"]["runs"] == "18"


def test_the_correction_removes_nearly_all_the_amplitude_dependence(results):
    _, found = results
    before = _column(found, "amplitude-correction", 3)
    after = _column(found, "amplitude-correction", 4)
    assert all(1.4 < b < 1.9 for b in before)
    assert all(0 < a < 0.12 for a in after)
    # "A few per cent of the slope".
    assert max(a / b for a, b in zip(after, before, strict=True)) < 0.08
    assert _number(found, "short-scatter") == pytest.approx(0.7, abs=0.05)


def test_the_trials_disagree_by_more_than_one_runs_standard_error(results):
    _, found = results
    assert _number(found, "trial-sd-low") == pytest.approx(0.19, abs=0.01)
    assert _number(found, "trial-sd-high") == pytest.approx(0.86, abs=0.01)
    assert _number(found, "run-stderr-high") == pytest.approx(0.23, abs=0.01)
    # Against the standard errors of their own runs, the trials' spreads
    # give a chi-square far above its degrees of freedom: chi-square with 10
    # degrees of freedom exceeds 40 with a probability below 1e-5.
    assert found["numbers"]["trial-dof"] == "10"
    assert _number(found, "trial-chi2") > 40


def test_the_length_models_and_the_effective_length(results):
    _, found = results
    assert _number(found, "excess-low") == pytest.approx(4.2, abs=0.05)
    assert _number(found, "excess-high") == pytest.approx(9.9, abs=0.05)
    assert _number(found, "short-above") == pytest.approx(2.1, abs=0.05)
    # No model within the spread of the trials.
    assert _number(found, "simple-chi2") > 1000
    assert 20 < _number(found, "line-chi2") < 40
    assert 20 < _number(found, "physical-chi2") < 50
    # Residuals of the fitted models about a millimetre, the precision of
    # the stated lengths, several times the error bars.
    assert 0.5 < _number(found, "physical-residual-mm") < 1.0
    assert 1.0 < _number(found, "line-residual-mm") < 2.0
    assert _number(found, "sigma-mm-high") < 0.5
    assert _number(found, "physical-residual-mm") > 2 * _number(found, "sigma-mm-high")
    # The line's g is far from the stated one: not a measurement of g.
    g_line, g_err = _number(found, "g-line"), _number(found, "g-err")
    assert g_line == pytest.approx(9.99, abs=0.01)
    assert (g_line - lab.G) > 5 * g_err


def test_the_scaled_errors_take_the_misfit_into_account(traces):
    points = lab.length_points(traces)
    experiment = lab.Experiment()
    models = lab.length_models(experiment, points)
    line = models["line"]
    a = line.value("a")
    plain = 4 * np.pi**2 / a * float(line.stderr[0]) / a
    assert models["g-err"] == pytest.approx(plain * np.sqrt(line.reduced_chi2))


def test_the_damping_holdout_asks_for_the_quadratic_part(results):
    _, found = results
    rows = found["tables"]["damping-holdout"]["rows"]
    for setting in ("air", "large baffle"):
        mine = [r for r in rows if r[0] == setting]
        fitted = [r for r in mine if r[2] == "fitted"]
        held = [r for r in mine if r[2] == "held out"]
        assert len(fitted) == 1 and len(held) == 2
        # The held-out trials were released higher than the fitted one.
        assert all(float(r[3]) > float(fitted[0][3]) + 5 for r in held)
        # Both parts fit better than the exponential, in the fit and on
        # the held-out trials, where they cut its misfit by a third to a half.
        assert float(fitted[0][5]) < float(fitted[0][4])
        for r in held:
            ratio = float(r[5]) / float(r[4])
            assert 0.4 < ratio < 0.7, (setting, ratio)
            # Two to five times the residual of the fitted trial.
            assert 2 < float(r[5]) / float(fitted[0][5]) < 5
    assert _number(found, "air-quality") == pytest.approx(376, abs=2)


def test_the_rates_differ_between_trials_by_more_than_their_fit_errors(results):
    _, found = results
    for tag in ("air", "baffle"):
        assert _number(found, tag + "-kappa-sd") > 2 * _number(
            found, tag + "-kappa-err"
        )
        # Neighbouring cycles' residuals are positively correlated.
        assert _number(found, tag + "-rho-both") > 0.5
    assert _number(found, "baffle-kappa-mean") > 2 * _number(found, "air-kappa-mean")
    # The baffle lengthens the period by more than the spread of the trials.
    assert _number(found, "baffle-t0-longer") > 2 * _number(found, "trial-sd-low")


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte; the straight
    # lines are drawn from their two ends.
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=label != "fig-record") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                model = ("law", "fitted straight", "fitted physical", "exact period")
                if any(m in text for m in model) and "[" in text:
                    assert "[simulated]" in text, (label, text)
                if text.startswith(("trial", "T of", "T0,", "recorded", "mean of")):
                    assert "[processed]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the earlier labs keep their figures under
    # 0.75 MB, and so does this one with four figures (about 0.63 MB here;
    # CI's build has come out larger than the local one before).
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
