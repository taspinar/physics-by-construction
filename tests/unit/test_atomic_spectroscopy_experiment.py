"""The experiment of "Atomic spectroscopy lab" (quantum 8): what the page
claims is what the committed sample gives, the Rydberg constant is the
dossier's, the stated uncertainties' assumptions are checked on the data, and
the figures follow the conventions of a measured-data lab."""

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import (
    assert_the_page_and_the_results_agree,
    page_of,
    run_entry_point,
)

from pbc.authoring.tables import is_numeric_console_block
from pbc.data.adapters import sdss_flux_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import sdss_balmer
from pbc.experiment import encode
from pbc.quantum.experiments import atomic_spectroscopy as lab

MODULE = "pbc.quantum.experiments.atomic_spectroscopy"
PAGE = "quantum/08-atomic-spectroscopy"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("atomic_spectroscopy")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def spectrum():
    return lab.load_spectrum()


@pytest.fixture(scope="module")
def analysis(spectrum):
    return sdss_balmer.analyse(spectrum)


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name].replace(",", ""))


def _column(found: dict, table: str, column: int) -> list[str]:
    return [row[column] for row in found["tables"][table]["rows"]]


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_no_section_id_equals_a_cell_label():
    # Both become id="..." on the page (pitfall 8 of the labs).
    page = page_of(PAGE)
    sections = set(re.findall(r"\{#([a-z0-9-]+)\}", page))
    labels = set(re.findall(r"^#\|\s*label:\s*([a-z0-9-]+)\s*$", page, re.MULTILINE))
    assert labels and sections
    assert not sections & labels


def test_the_series_carries_the_status_of_the_card(spectrum):
    series = sdss_flux_series(spectrum)
    assert series.artifact == "calibrated-observation"
    assert series.status == "calibrated"
    assert series.x_unit == "Angstrom"
    assert series.sigma is not None and np.all(np.isfinite(series.sigma))
    assert series.sigma == pytest.approx(1 / np.sqrt(spectrum.ivar))
    assert np.all(np.diff(series.x) > 0)


def test_the_record_is_what_the_observational_claim_says(results):
    _, found = results
    assert found["numbers"]["pixels"] == "3,843"
    assert found["numbers"]["good"] == "3,816"
    assert _number(found, "masked") == 27
    assert (_number(found, "lowest"), _number(found, "highest")) == (3803, 9211)
    assert _number(found, "snr") == 39
    assert _number(found, "pixel-kms") == 69.0


def test_the_grid_levels_are_the_model(results, experiment):
    _, found = results
    check = lab.level_check(lab.Experiment())
    assert check["worst-coarse"] < 2e-4
    assert 3.99 < check["ratio"] <= check["ratio-high"] < 4.01
    assert found["numbers"]["level-bound"] == "1e-7"
    assert check["worst-extrapolated"] < 1e-7
    assert check["degeneracy"] < 1e-7  # l = 1 has the energy of l = 0
    assert check["worst-term"] < 1e-7  # the Balmer terms 1/4 - 1/n^2
    rows = found["tables"]["level-check"]["rows"]
    assert [row[0] for row in rows] == ["1", "2", "3", "4", "5", "6"]
    assert rows[0][4] == ""


def test_the_rydberg_constant_is_the_dossiers(results, analysis):
    _, found = results
    ryd = analysis.rydberg
    # The dossier: R = 10,968,065 +- 41 1/m, chi-square 0.74 for 3.
    assert found["numbers"]["r"] == "10,968,065"
    assert _number(found, "r-err") == 41
    assert _number(found, "r-chi2") == 0.74 and _number(found, "r-dof") == 3
    assert _number(found, "r") == pytest.approx(ryd.r, abs=0.5)
    per_line = [float(v.replace(",", "")) for v in _column(found, "rydberg", 4)]
    assert per_line == pytest.approx([10968088, 10968054, 10968091, 10968100], abs=0.5)
    # Every line lies below the R_H formula by about the same velocity.
    offsets = [float(v) for v in _column(found, "rydberg", 6)]
    assert all(-10 < v < -7 for v in offsets)
    assert _number(found, "flat-chi2") == 29.6
    # The single z (the dossier): R = 10,968,138 +- 85, calibration 153.8 for 8.
    assert (_number(found, "flat-r"), _number(found, "flat-r-err")) == (10968138, 85)
    assert (_number(found, "flat-cal-chi2"), _number(found, "flat-cal-dof")) == (154, 8)


def test_the_comparisons_with_the_laboratory_constants(results):
    _, found = results
    assert _number(found, "rel-h") == 2.80
    assert _number(found, "rel-h-sigma") == 7.4
    assert _number(found, "rel-fine") == 1.12
    assert _number(found, "rel-lab") == 1.67
    assert _number(found, "rel-lab-kms") == 5.0
    assert _number(found, "rel-lab-sigma") == 4.4
    # The recoil: R below R_inf by about m_e/m_p, resolved > 100 times.
    assert _number(found, "rel-inf") == 5.16
    assert _number(found, "recoil") == 5.45
    assert _number(found, "rel-inf-sigma") > 100
    # "About two fifths of it the fine structure."
    assert _number(found, "rel-fine") / _number(found, "rel-h") == pytest.approx(
        0.4, abs=0.02
    )


def test_the_calibration_and_its_extra_scatter(results, analysis):
    _, found = results
    assert found["numbers"]["z0"] == "0.0149937"
    assert found["numbers"]["z0-err"] == "0.0000030"
    assert (_number(found, "slope"), _number(found, "slope-err")) == (4.2, 1.0)
    assert (_number(found, "cal-chi2"), _number(found, "cal-dof")) == (40.4, 7)
    assert _number(found, "cal-birge") == 2.4
    # The calibration uses no hydrogen line.
    assert not set(analysis.rydberg.calibration.z) & set(sdss_balmer.BALMER.values())
    # "[Ne III] lies furthest from the calibration" (the caption).
    offsets = dict(
        zip(
            _column(found, "calibration", 0),
            [abs(float(v)) for v in _column(found, "calibration", 4)],
            strict=True,
        )
    )
    assert max(offsets, key=offsets.get) == "[Ne III] 3870"
    assert _number(found, "pipeline-offset") == -1.0


def test_the_lines_and_their_widths(results):
    _, found = results
    names = _column(found, "lines", 0)
    assert len(names) == 13 and names[:4] == ["H alpha", "H beta", "H gamma", "H delta"]
    gas = dict(zip(names, [float(v) for v in _column(found, "lines", 5)], strict=True))
    balmer = [gas[n] for n in names[:4]]
    forbidden = [gas[n] for n in names[4:]]
    # About the same for hydrogen as for the heavier ions, and far above the
    # thermal width of hydrogen at 1e4 K.
    assert abs(np.mean(balmer) - np.mean(forbidden)) < 10
    assert min(balmer + forbidden) > 2.5 * _number(found, "thermal-h")
    assert _number(found, "thermal-h") == 9
    assert (_number(found, "ha-raw-error"), _number(found, "ha-error")) == (
        0.007,
        0.028,
    )
    assert _number(found, "ha-chi2") == 16.7
    chi2 = dict(zip(names, [float(v) for v in _column(found, "lines", 6)], strict=True))
    for faint in ("[S II] 6718", "[Ne III] 3870", "[Ar III] 7138", "H beta"):
        assert chi2[faint] < 1.5


def test_the_stated_errors_rest_on_assumptions_that_were_checked(results):
    _, found = results
    rows = found["tables"]["independence"]["rows"]
    near_one = [r for r in rows if float(r[2]) < 1.5]
    assert all(r[5] == "yes" for r in near_one)
    assert _number(found, "near-one-inside") == _number(found, "near-one") == 5
    outside = {r[0] for r in rows if r[5] == "no"}
    assert outside == {"H delta", "[O I] 6302"}
    for r in rows:
        if r[0] in outside:
            assert float(r[2]) > 1.5  # misfit, scaled: the page's "also exceed"
            assert float(r[3]) > 0  # residuals in runs
    # The choices move R by less than one standard error.
    error = _number(found, "r-err")
    assert _number(found, "window-shift") < error / 4
    assert _number(found, "neiii-shift") < error


def test_the_exercises(experiment):
    proton = experiment.output("proton-exercise")
    implied = int(re.search(r"m_p/m_e from R: (\d+)", proton).group(1))
    assert implied > 1.03 * 1836  # "several per cent too large"
    assert "0.7%" in proton  # "under one per cent" from the statistics
    deuterium = experiment.output("deuterium-exercise")
    shift = float(re.search(r"as a velocity: (\d+) km/s", deuterium).group(1))
    assert 50 < shift < 150  # about a line width


def test_the_errors_of_the_balmer_series_are_hidden_by_its_markers(analysis):
    # The caption of fig-rydberg-law: the errors of the left panel's points
    # (the error column of the rydberg table, each below 1e-4 of its
    # wavenumber) are far smaller than the markers, so they are not drawn
    # there (Issue #500).
    ryd = analysis.rydberg
    figure = lab.draw_rydberg_law(analysis)
    try:
        ax = figure.axes[0]
        (points,) = [line for line in ax.lines if line.get_marker() == "o"]
        radius = points.get_markersize() / 2 * figure.dpi / 72  # in pixels
        for n in ryd.levels:
            term = 0.25 - 1.0 / n**2
            value = ryd.per_line[n] * term / 1e6
            error = ryd.per_line_err[n] * term / 1e6
            assert ryd.per_line_err[n] / ryd.per_line[n] < 1e-4
            low, high = ax.transData.transform([(term, value), (term, value + error)])
            assert high[1] - low[1] < radius / 10, n
    finally:
        plt.close(figure)


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_the_same_bytes_on_every_draw(experiment, label):
    # The page's figure must be regenerated byte for byte (straight model
    # lines are drawn from their two ends).
    drawings = {encode(experiment.figures[label]) for _ in range(12)}
    assert len(drawings) == 1


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        expected = "calibrated" if label == "fig-spectrum" else "processed"
        assert figure_status(figure) == expected
        residuals = label != "fig-spectrum"
        assert check_figure(figure, residuals=residuals) == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if "measured" in text or "fitted centres" in text:
                    assert f"[{expected}]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The labs keep their figures under 0.75 MB; the Linux build in CI came
    # out up to 16.6 % larger than the local one (W7), so the local total is
    # kept at most 70 % of that bound. Locally these are about 0.44 MB.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 525_000, total
