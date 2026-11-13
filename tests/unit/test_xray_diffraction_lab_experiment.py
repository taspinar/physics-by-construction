"""The experiment of "X-ray diffraction lab" (materials 06): what the page
claims is what the committed samples give, the lattice parameters are the
dossier's, and the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import diffraction_pattern_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import srm660c
from pbc.experiment import encode
from pbc.materials.experiments import xray_diffraction_lab as lab

MODULE = "pbc.materials.experiments.xray_diffraction_lab"
PAGE = "materials/06-xray-diffraction-lab"
FIGURES = ("fig-extrapolation", "fig-pattern", "fig-peaks", "fig-specimens")
# The other labs keep their figures under 0.75 MB; the Linux build in CI has
# come out up to 17 % larger than a local one, so this lab keeps its local
# figures under 70 % of that bound.
FIGURE_BOUND = 750_000
LOCAL_SHARE = 0.70


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("xray_diffraction_lab")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def analyses():
    return lab.analyse_all(lab.load_patterns())


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_figures_are_those_the_tests_draw(experiment):
    assert tuple(sorted(experiment.figures)) == FIGURES


def test_the_series_carries_the_status_of_the_card():
    pattern = lab.load_patterns()[lab.SHOWN]
    series = diffraction_pattern_series(pattern)
    assert series.artifact == "processed-measured"
    assert series.status == "processed"
    assert series.x_unit == "degrees"
    assert series.y_unit == "counts per counting time"
    # The Poisson uncertainty of the record's weights, sigma = 1/sqrt(w).
    np.testing.assert_allclose(series.sigma, 1 / np.sqrt(pattern.weight))


def test_the_lattice_parameters_are_the_dossiers(analyses):
    # Two implementations, the lab's through pbc.materials.diffraction and
    # fit_curve and the reference figure's of the dossier, give the same a
    # per reflection and the same intercept for every specimen.
    measured, model = analyses
    for analyses_of in (measured, model):
        for specimen in srm660c.SPECIMENS:
            analysis = analyses_of[specimen]
            for peak in analysis.peaks:
                assert lab.peak_lattice_parameter(peak) == pytest.approx(
                    peak.a, rel=1e-13
                )
            line = lab.extrapolate(analysis.peaks)
            assert line.a0 == pytest.approx(analysis.a0, abs=1e-10)
            assert line.slope == pytest.approx(analysis.slope, rel=1e-7)
    assert lab.LOWEST == srm660c.NR_MIN
    assert lab.EXTRAPOLATIONS[0] == ("Nelson-Riley", lab.LOWEST, False)


def test_the_method_is_unbiased_on_its_own_profile(results):
    _, found = results
    # Counting noise alone: about one ppm. A pure displacement of -0.1 mm:
    # the Nelson-Riley line misses by several ppm, the displacement function
    # does not, and its slope is the first-order a s / R.
    assert abs(_number(found, "synthetic-plain")) < 2
    assert -12 < _number(found, "synthetic-nr") < -6
    assert abs(_number(found, "synthetic-disp")) < 2
    rows = found["tables"]["method-check"]["rows"]
    displaced = [row for row in rows if row[0] == "-0.1" and row[1] == "displacement"]
    (row,) = displaced
    assert float(row[3]) == pytest.approx(float(row[4]), rel=0.01)


def test_one_lattice_parameter_indexes_the_pattern(results):
    _, found = results
    # The dossier: every fitted position within 0.07 degrees of Table 1, the
    # offset growing with the angle.
    assert _number(found, "max-offset") < 0.07
    assert _number(found, "low-offset") < 0.01 < _number(found, "high-offset")
    rows = found["tables"]["reflections"]["rows"]
    assert len(rows) == 24
    assert [row[0] for row in rows] == ["".join(map(str, h)) for h in srm660c.HKL]
    # Every reflection's a lies within 0.01 of a percent of the certified a.
    for row in rows:
        assert float(row[6]) == pytest.approx(srm660c.CERTIFIED_A, rel=1e-3)


def test_the_symmetric_fit_misses_the_instruments_profile(results):
    _, found = results
    assert _number(found, "chi2-lowest") > 10
    assert 1 < _number(found, "chi2-high-max") < 8
    # The dossier's wavelength and height ratios of the two lines.
    assert _number(found, "ratio") == pytest.approx(1.00248, abs=0.00001)
    assert _number(found, "share") == pytest.approx(0.515, abs=0.01)


def test_the_extrapolated_a_and_its_spread_are_the_dossiers(results):
    _, found = results
    # The dossier: 4.156485 angstrom, SD 0.000014, range 4.156453 to
    # 4.156508; NIST's model by the same method 4.156480; NIST's a 4.156789.
    assert found["numbers"]["a-mean"] == "4.156485"
    assert found["numbers"]["a-sd"] == "0.000014"
    assert found["numbers"]["a-min"] == "4.156453"
    assert found["numbers"]["a-max"] == "4.156508"
    assert found["numbers"]["model-mean"] == "4.156480"
    assert found["numbers"]["nist"] == "4.156789"
    assert _number(found, "a-sem-ppm") == pytest.approx(0.7, abs=0.05)
    assert found["numbers"]["shown-warnings"] == "none"
    assert _number(found, "used") == 18
    # The drift over the reflections is far larger than the spread.
    assert abs(_number(found, "a-drift-ppm")) > 50 * _number(found, "a-sd-ppm")


def test_the_scatter_about_the_line_is_not_counting_noise(results):
    _, found = results
    band = _number(found, "rho-band")
    assert band == pytest.approx(2 / np.sqrt(18), abs=0.005)
    # Correlated residuals for the measurement and for the noise-free model.
    assert _number(found, "rho-measured") > 0.3
    assert _number(found, "rho-model") > 0.3
    assert _number(found, "above-measured") >= 10
    assert _number(found, "above-model") >= 10
    # The model's standard error is of the size of the measurement's.
    assert 0.5 < _number(found, "stderr-model") / _number(found, "stderr-measured") < 1
    # Measured minus model spreads by about a ppm, much less than the
    # specimens.
    assert _number(found, "count-sd") == pytest.approx(1.1, abs=0.1)
    assert _number(found, "count-sd") < _number(found, "a-sd-ppm") / 2
    rows = found["tables"]["error-check"]["rows"]
    assert [row[0] for row in rows] == [
        "measured",
        "NIST's model, same method",
        "measured minus model",
    ]
    assert rows[2][3] == ""


def test_the_two_specimens_of_a_bottle_are_checked_for_a_common_error(results):
    _, found = results
    rows = found["tables"]["bottle-check"]["rows"]
    assert [row[0] for row in rows] == ["extrapolated a", "measured minus model"]
    # The dossier's specimens pair up by bottle: 100a, 100b, ..., 1000b.
    assert srm660c.SPECIMENS[:4] == ("100a", "100b", "200a", "200b")
    # No common error shows within a bottle: F near 1, no significance, a
    # weak correlation of the a and b specimens.
    for name in ("a", "difference"):
        assert _number(found, f"bottle-p-{name}") > 0.05
        assert abs(_number(found, f"bottle-correlation-{name}")) < 0.5
    # The bottle means give a standard error close to the 20 specimens'.
    assert _number(found, "sem-bottles-a") == pytest.approx(
        _number(found, "a-sem-ppm"), rel=0.2
    )
    # The comparisons use the larger of the two.
    assert _number(found, "sem-used") >= _number(found, "a-sem-ppm") - 0.05
    assert _number(found, "sem-used") >= _number(found, "sem-bottles-a") - 0.05
    assert (
        _number(found, "difference-sem")
        >= _number(found, "sem-bottles-difference") - 0.005
    )


def test_the_bottle_check_finds_a_common_error_when_there_is_one():
    from pbc.experiment import Experiment

    rng = np.random.default_rng(0)
    shared = np.repeat(rng.normal(size=10) * 5, 2)
    independent = rng.normal(size=20)
    found = lab.bottle_check(
        Experiment(),
        {
            "shared": ("shared", shared + 0.1 * independent),
            "independent": ("independent", independent),
        },
    )
    assert found["shared"]["p"] < 0.001
    assert found["shared"]["correlation"] > 0.9
    # With a shared error the bottle means give the honest, larger error.
    assert found["shared"]["sem-bottles"] > 1.3 * found["shared"]["sem"]
    assert found["independent"]["p"] > 0.01


def test_the_slope_follows_the_displacement(results):
    _, found = results
    assert _number(found, "slope-correlation") > 0.999
    assert _number(found, "slope-predicted") == pytest.approx(
        srm660c.CERTIFIED_A / 217.5, rel=1e-3
    )
    assert 1.1 < _number(found, "slope-ratio") < 1.4
    assert _number(found, "nr-correlation") > 0.5


def test_the_bias_the_difference_and_the_comparison(results):
    _, found = results
    # The dossier: -74 ppm bias, +1.1 ppm measured minus model, -82 ppm
    # from the certified value, 4.3 U.
    assert _number(found, "bias") == pytest.approx(-74.4, abs=0.1)
    assert _number(found, "difference") == pytest.approx(1.1, abs=0.1)
    assert _number(found, "gap") == pytest.approx(-82.1, abs=0.1)
    assert _number(found, "gap-u") == pytest.approx(4.3, abs=0.05)
    assert _number(found, "nist-gap") == pytest.approx(-8.9, abs=0.1)
    assert _number(found, "difference-sigmas") >= 3
    assert _number(found, "gap-sem") > 50
    # Corrected for the bias, inside the expanded uncertainty.
    assert abs(_number(found, "corrected-gap")) < _number(found, "certified-u-ppm")
    # The budget: the three parts add up to the comparison.
    rows = {row[0]: float(row[2]) for row in found["tables"]["budget"]["rows"]}
    parts = [
        "measured minus NIST's model, same method (mean of 20)",
        "the method's bias, measured on NIST's model",
        "NIST's refined a in the CIFs (20.85 °C) minus the certified (22.5 °C)",
    ]
    assert sum(rows[p] for p in parts) == pytest.approx(
        rows["measured minus certified"], abs=0.15
    )
    assert rows["certificate: expanded uncertainty U (k = 2)"] == pytest.approx(
        19.2, abs=0.05
    )
    # The bias dominates: larger than every other part.
    others = [v for k, v in rows.items() if k != "measured minus certified"]
    assert max(abs(v) for v in others) == abs(rows[parts[1]])


def test_no_extrapolation_brings_the_simple_analysis_near_the_certificate(results):
    _, found = results
    rows = found["tables"]["extrapolations"]["rows"]
    assert len(rows) == len(lab.EXTRAPOLATIONS) == 6
    gaps = [float(row[8]) for row in rows]
    biases = [float(row[6]) for row in rows]
    differences = [float(row[7]) for row in rows]
    assert max(gaps) < -3 * _number(found, "certified-u-ppm")
    assert min(biases) < -60 and max(biases) < -60
    assert max(abs(d) for d in differences) < 10
    assert _number(found, "gap-spread") == pytest.approx(max(gaps) - min(gaps), abs=0.1)
    # The lab's own extrapolation is the first row.
    assert rows[0][4] == found["numbers"]["a-mean"]


def test_the_exercises(experiment):
    bragg = experiment.outputs["bragg-exercise"]
    assert "(100) spacing d: 4.1568 A" in bragg
    assert "(100) K-alpha-1 peak at 2theta: 21.359 deg" in bragg
    assert "(510) K-alpha-2 peak above it by: 0.829 deg" in bragg
    shift = experiment.outputs["displacement-exercise"]
    assert "low-angle peak, error of a: -2396 ppm" in shift
    assert "high-angle peak, error of a: -52 ppm" in shift


@pytest.mark.parametrize("label", FIGURES)
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte; twelve draws
    # find a figure that comes out in one of two rasters (MAT6, W7).
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", FIGURES)
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=label == "fig-peaks") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if text.startswith("measured"):
                    assert "[processed]" in text, (label, text)
                if any(
                    word in text
                    for word in ("model", "fit [", "Bragg", "line [", "first order")
                ) and not text.startswith("measured"):
                    assert "[simulated]" in text or text.startswith(
                        ("NIST's refined", "certified")
                    ), (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < LOCAL_SHARE * FIGURE_BOUND, total


def test_the_extrapolation_panel_shows_every_fitted_reflection(experiment, analyses):
    figure = experiment.figures["fig-extrapolation"]()
    try:
        (ax,) = figure.axes
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        for analysis in (analyses[0][lab.SHOWN], analyses[1][lab.SHOWN]):
            for peak in analysis.peaks:
                if peak.two_theta > lab.LOWEST:
                    assert x0 <= lab.nelson_riley(peak.theta) <= x1
                    assert y0 <= lab.peak_lattice_parameter(peak) <= y1
        assert y0 < srm660c.CERTIFIED_A < y1
    finally:
        plt.close(figure)
