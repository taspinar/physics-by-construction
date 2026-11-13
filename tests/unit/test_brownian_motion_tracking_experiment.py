"""The experiment of "Brownian motion tracking lab" (thermodynamics 11): what
the page claims is what the committed tracks give, D and the drift are the
dossier's, the stated uncertainties' assumptions are checked on the data, and
the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data import tracking
from pbc.data.adapters import track_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import trackpy_bulk_water
from pbc.experiment import encode
from pbc.thermodynamics.experiments import brownian_motion_tracking as lab

MODULE = "pbc.thermodynamics.experiments.brownian_motion_tracking"
PAGE = "thermodynamics/11-brownian-motion-tracking"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("brownian_motion_tracking")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def tracks():
    return lab.load_tracks()


@pytest.fixture(scope="module")
def analysis(tracks):
    return trackpy_bulk_water.analyse(tracks)


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def _column(found: dict, table: str, column: int) -> list[str]:
    return [row[column] for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_a_track_carries_the_status_of_the_card(tracks):
    number = int(np.argmax(np.bincount(tracks.particle)))
    series = track_series(tracks, number, 0)
    assert series.artifact == "processed-measured"
    assert series.status == "processed"
    assert series.x_unit == "frame" and series.y_unit == "px"
    assert series.sigma is None  # the record gives no localisation error
    assert np.all(np.diff(series.x) == 1)  # a track occupies consecutive frames
    rows = tracks.particle == number
    assert np.array_equal(
        np.sort(track_series(tracks, number, 1).y), np.sort(tracks.xy[rows, 1])
    )


def test_the_lab_selects_and_corrects_as_the_reference_module(tracks, analysis):
    # The lab's own selection and drift subtraction give the reference
    # module's MSD exactly, so the regions and the increases analyse the
    # same tracks.
    frame, particle, xy = lab.corrected_positions(tracks)
    sums, counts, numbers = tracking.msd_sums(frame, particle, xy, lab.LAGS)
    np.testing.assert_allclose(sums.sum(0) / counts.sum(0), analysis.msd, rtol=1e-12)
    assert len(numbers) == analysis.tracks == 596
    assert frame.size == analysis.features == 21_200
    local, _ = lab.local_diffusion(tracks)
    np.testing.assert_allclose(
        local, np.diff(analysis.msd) / (4 * lab.FRAME_TIME), rtol=1e-12
    )


def test_the_record_is_what_the_observational_claim_says(results):
    _, found = results
    # The dossier: 582 to 603 features per frame, 1,268 tracks, 596 of at
    # least 15 frames with 21,200 features, 23,685 rows.
    assert _number(found, "features-low") == 582
    assert _number(found, "features-high") == 603
    assert found["numbers"]["tracks"] == "1,268"
    assert _number(found, "long-tracks") == 596
    assert found["numbers"]["long-features"] == "21,200"
    assert _column(found, "record", 1)[:2] == ["40", "23,685"]


def test_the_camera_formula_holds_for_the_simulated_walks(results):
    _, found = results
    assert _number(found, "check-z") < 3  # standard errors, every lag and camera
    assert _number(found, "check-d") < 1.5  # per cent
    assert _number(found, "check-rho") < 0.01
    # The line through the origin falls short under blur, as the formula says:
    # 4 D tau_e / 3 of intercept over the lags 1-10 is about 5 per cent of D.
    assert _number(found, "check-origin") < 0.39
    for row in found["tables"]["camera-check"]["rows"]:
        assert float(row[3]) == pytest.approx(float(row[4]), abs=1.5e-3)


def test_the_drift_is_the_dossiers(results, analysis):
    _, found = results
    assert analysis.drift[-1] == pytest.approx([0.848, 0.262], abs=5e-4)
    assert _number(found, "drift-speed") == 0.55
    assert _number(found, "duration") == pytest.approx(39 / 24, abs=0.005)


def test_d_and_the_line_are_the_dossiers(results):
    _, found = results
    # The dossier: D = 0.403 +- 0.010 µm^2/s, c = -0.036 +- 0.003 µm^2.
    assert _number(found, "d") == 0.403
    assert _number(found, "d-err") == 0.010
    assert _number(found, "intercept") == pytest.approx(-0.035, abs=0.0015)
    assert _number(found, "intercept-err") == 0.003
    # The estimator of the random-walks lesson, through the origin, is lower.
    assert _number(found, "d-origin") == 0.373


def test_the_residuals_bend_and_the_increases_climb(results, analysis):
    _, found = results
    residual = analysis.msd - (
        4 * analysis.diffusion * analysis.tau + analysis.intercept
    )
    # Positive, negative, positive: a bend, not scatter.
    assert residual[0] > 0 and residual[4] < 0 and residual[-1] > 0
    first = _number(found, "local-first")
    error = _number(found, "local-first-err")
    late = _number(found, "local-late")
    assert first == pytest.approx(0.334, abs=0.001)
    assert late - first > 10 * error  # the climb is far outside the error
    assert late == pytest.approx(0.418, abs=0.002)


def test_stokes_einstein_and_what_it_needs(results):
    _, found = results
    assert _number(found, "se-20") == 0.429 and _number(found, "se-25") == 0.491
    assert _number(found, "below-20") == 6 and _number(found, "below-25") == 18
    assert _number(found, "radius-20") == 0.53 and _number(found, "radius-25") == 0.61
    assert _number(found, "eta-per-kelvin") == pytest.approx(2.4, abs=0.05)


def test_the_processing_range_is_the_dossiers(results):
    _, found = results
    assert _number(found, "variants-low") == 0.377
    assert _number(found, "variants-high") == 0.411
    assert _number(found, "no-drift") == 0.438
    assert _number(found, "no-drift-rel") == 9
    # "Its half-width is ... times the bootstrap error", larger than it.
    assert 1 < _number(found, "range-ratio") < 2


def test_the_stated_errors_rest_on_assumptions_that_were_checked(results, tracks):
    _, found = results
    # The least-squares error that treats the MSD points as independent is
    # far smaller than the bootstrap over tracks.
    assert _number(found, "ols") < _number(found, "d-err") / 2
    # The tracks: few long tracks could continue another.
    assert _number(found, "continuations") <= 0.02 * _number(found, "long-tracks")
    # Across the field: no significant difference, but not ruled out (the
    # page says the test is weak and the top-bottom gap is about two errors).
    assert 0.05 < _number(found, "chi2-p") < 0.5
    assert 1.5 < _number(found, "top-bottom-sigmas") < 3
    assert (
        _number(found, "quarters-low")
        < _number(found, "d")
        < _number(found, "quarters-high")
    )
    regions = lab.region_diffusion(tracks)
    assert set(regions) >= {"top left", "top right", "bottom left", "bottom right"}


def test_the_camera_model_does_not_explain_the_short_lags(results, analysis):
    _, found = results
    # The intercept is below what blur over a whole frame can make it.
    assert _number(found, "intercept") < _number(found, "blur-floor")
    # Through the camera formula it predicts a step correlation far above
    # the measured one.
    assert _number(found, "rho-predicted") > 2 * _number(found, "rho-measured")
    assert _number(found, "rho-measured") == pytest.approx(
        analysis.step_correlation, abs=0.005
    )
    # The steps are not Gaussian and the tracks are not alike.
    assert _number(found, "kurtosis") == pytest.approx(3.2, abs=0.05)
    assert _number(found, "spread") > 1.5 * _number(found, "spread-expected")


def test_the_exercises_use_the_labs_numbers(results, analysis):
    _, found = results
    # The statements give D = 0.403 µm^2/s and c = -0.0355 µm^2.
    assert round(analysis.diffusion, 3) == 0.403
    assert round(analysis.intercept, 4) == -0.0355
    output = found["outputs"]["exposure-exercise"]
    exposure = float(output.split("alone: ")[1].split(" ms")[0])
    assert exposure > 1e3 / 24  # longer than a frame, as the solution says


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_follows_the_conventions_of_its_status(experiment, label):
    figure = experiment.figures[label]()
    try:
        expected = "measured" if label == "fig-frame" else "processed"
        assert figure_status(figure) == expected
        assert check_figure(figure, residuals=label == "fig-msd") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if "MSD," in text or "track" in text or "steps," in text:
                    assert "[processed]" in text, (label, text)
                if text.startswith("Stokes-Einstein"):
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The labs keep their figures under 0.65 MB. The Linux build in CI came
    # out up to 15 % larger than the local one (T7: 669,684 bytes against
    # 580,399), so the local total is kept at least 15 % below the bound:
    # about 0.43 MB here.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 650_000 * 0.85, total
