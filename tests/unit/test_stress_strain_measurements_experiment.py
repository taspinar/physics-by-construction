"""The experiment of "Stress-strain measurements lab" (materials 05): what
the page claims is what the committed sample gives, the fit, the yield and
the loop are the dossier's, and the figures follow the conventions of a
measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.authoring.tables import is_numeric_console_block
from pbc.data import SAMPLES_DIR
from pbc.data.adapters import stress_strain_series
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import nist_numisheet
from pbc.materials.experiments import stress_strain_measurements as lab

MODULE = "pbc.materials.experiments.stress_strain_measurements"
PAGE = "materials/05-stress-strain-measurements"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("stress_strain_measurements")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def test_r01():
    return lab.load_test()


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name])


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_series_carries_the_status_of_the_card(test_r01):
    series = stress_strain_series(test_r01)
    assert series.artifact == "processed-measured"
    assert series.status == "processed"
    assert series.x_unit == "mm/mm" and series.y_unit == "MPa"
    assert series.sigma is None  # the record gives no uncertainty per point


def test_the_fit_yield_and_loop_are_the_dossiers(test_r01):
    # Two implementations, the lab's through pbc.materials.stress_strain
    # and the reference figure's of the dossier, give the same numbers.
    theirs = nist_numisheet.load(SAMPLES_DIR / lab.DATASET)
    ours_fit = lab.fit_modulus(test_r01)
    their_fit = nist_numisheet.elastic_fit(theirs)
    np.testing.assert_allclose(ours_fit.params, their_fit.params, rtol=1e-9)
    np.testing.assert_allclose(ours_fit.stderr, their_fit.stderr, rtol=1e-6)
    assert lab.offset_yields(test_r01, ours_fit)[-1] == pytest.approx(
        nist_numisheet.offset_yield(theirs, their_fit), rel=1e-12
    )
    cycle = lab.loop(test_r01)
    reference = nist_numisheet.loop(theirs)
    assert (cycle["start"], cycle["end"]) == (reference.start, reference.end)
    assert cycle["work"] == pytest.approx(reference.work, rel=1e-12)
    assert cycle["closing"] == pytest.approx(reference.closing, rel=1e-12)
    assert lab.WINDOWS == nist_numisheet.WINDOWS


def test_the_landmarks_are_those_of_the_observational_claim(results):
    _, found = results
    # The dossier: 991.3 MPa at e = 0.0575, hold end 970.3 MPa, -1006.6 MPa,
    # necking at 981.2 MPa and e = 0.0910, fracture at e = 0.1771.
    assert found["numbers"]["peak-stress"] == "991"
    assert found["numbers"]["peak-strain"] == "5.75"
    assert found["numbers"]["hold-stress"] == "970"
    assert found["numbers"]["min-stress"] == "-1007"
    assert found["numbers"]["neck-stress"] == "981"
    assert found["numbers"]["neck-strain"] == "9.1"
    assert found["numbers"]["fracture-strain"] == "17.7"
    assert found["numbers"]["rows"] == "1607"
    assert _number(found, "strain-noise") == pytest.approx(25, abs=1)


def test_the_modulus_and_its_comparison_with_the_model_are_those_of_the_claims(
    results,
):
    _, found = results
    assert _number(found, "e-fit") == pytest.approx(196.3, abs=0.05)
    assert _number(found, "e-err") == pytest.approx(1.1, abs=0.05)
    assert _number(found, "s0") == pytest.approx(7.4, abs=0.05)
    assert found["numbers"]["fit-warnings"] == "none"
    # The scatter in the window is the strain noise times E, to 15 %, as
    # the page says.
    assert _number(found, "rms") == pytest.approx(
        _number(found, "noise-times-e"), rel=0.15
    )
    # The model's 200 GPa: above the fit by a few standard errors, a larger
    # rms in the window than the fitted line.
    assert _number(found, "model-e") == 200
    assert 2 < _number(found, "model-sigmas") < 5
    assert _number(found, "model-rms") > _number(found, "rms")


def test_the_sensitivity_table_brackets_the_model_as_the_page_says(results):
    _, found = results
    rows = found["tables"]["modulus-sensitivity"]["rows"]
    windows = [float(row[2]) for row in rows[:-1]]
    origin = float(rows[-1][2])
    standard_errors = [float(row[3]) for row in rows]
    model = _number(found, "model-e")
    # Inside the range of all the choices, outside the window fits alone.
    assert min(windows) < model < origin
    assert max(windows) < model
    # The spread is several times the standard error of any one fit.
    assert (origin - min(windows)) > 3 * max(standard_errors)
    # Higher windows give lower moduli.
    assert windows[-1] == min(windows)


def test_the_curve_leaves_the_line_gradually(results, test_r01):
    _, found = results
    rows = found["tables"]["offsets"]["rows"]
    stresses = [float(row[2]) for row in rows]
    assert stresses == sorted(stresses) and len(set(stresses)) == len(stresses)
    assert _number(found, "yield") == pytest.approx(775, abs=1)
    assert _number(found, "yield-small") == pytest.approx(542, abs=1)
    # The smallest offset is several times the strain noise.
    assert float(rows[0][1]) > 5
    # Above the window the residuals leave the noise (the page: the line
    # holds at least to the top of the window, about half the yield).
    result = lab.fit_modulus(test_r01)
    e, s = lab.first_loading(test_r01)
    residual = s - result.value("E") * 1e3 * e - result.value("S0")
    band = (s > 500) & (s < 650)
    assert np.mean(residual[band]) < -5 * _number(found, "rms")
    assert lab.WINDOW[1] / _number(found, "yield") == pytest.approx(0.5, abs=0.05)


def test_the_unloading_is_not_elastic(results):
    _, found = results
    assert _number(found, "recovered") == pytest.approx(6.82, abs=0.01)
    assert _number(found, "predicted") == pytest.approx(4.94, abs=0.01)
    assert _number(found, "recovered-ratio") > 1.3
    assert _number(found, "chord") == pytest.approx(142, abs=1)
    # Reverse yield barely past zero stress: far less compressive than the
    # tensile yield and than the most compressive stress.
    reverse = _number(found, "reverse-yield")
    assert -100 < reverse < 0
    assert abs(reverse) < 0.1 * _number(found, "yield")
    assert _number(found, "reverse-drop") == pytest.approx(
        _number(found, "hold-stress") - reverse, abs=1
    )


def test_the_loop_and_the_ellipse_check(results, test_r01):
    _, found = results
    assert _number(found, "loop-work") == pytest.approx(75.8, abs=0.05)
    assert _number(found, "loop-closing") == pytest.approx(-0.1, abs=0.05)
    cycle = lab.loop(test_r01)
    # Clockwise and simple: the integral is the shoelace area.
    assert cycle["work"] == pytest.approx(cycle["shoelace"], rel=1e-9)
    assert _number(found, "ellipse-ratio") == pytest.approx(4.0, abs=0.05)


def test_the_true_stress_at_the_neck_is_nists_column(test_r01):
    neck = nist_numisheet.reload_maximum(test_r01)
    true_e, true_s = lab.neck_true_stress(test_r01)
    assert true_e == pytest.approx(test_r01.true_strain[neck], abs=1e-12)
    assert true_s == pytest.approx(test_r01.true_stress[neck], rel=1e-9)


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_is_processed_measurement_and_follows_the_conventions(
    experiment, label
):
    figure = experiment.figures[label]()
    try:
        assert figure_status(figure) == "processed"
        assert check_figure(figure, residuals=label == "fig-elastic-regime") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if text.startswith("measured ["):
                    assert "[processed]" in text, (label, text)
                if "Hooke" in text or "elastic unloading," in text or "shifted" in text:
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the other labs keep their figures under
    # 0.75 MB, and so does this one.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
