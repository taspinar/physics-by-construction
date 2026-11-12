"""The experiment of "Exoplanet light curves lab" (astrophysics 09): what
the page claims is what the committed sample gives, the geometry is the
dossier's with its uncertainties propagated through the correlations, and
the figures follow the conventions of a measured-data lab."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.astrophysics.experiments import exoplanet_light_curves as lab
from pbc.authoring.tables import is_numeric_console_block
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import tess_wasp18

MODULE = "pbc.astrophysics.experiments.exoplanet_light_curves"
PAGE = "astrophysics/09-exoplanet-light-curves"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("exoplanet_light_curves")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def experiment():
    return lab.run()


@pytest.fixture(scope="module")
def light_curve():
    return lab.load_light_curve()


@pytest.fixture(scope="module")
def analysis(light_curve):
    return tess_wasp18.analyse(light_curve)


def _number(found: dict, name: str) -> float:
    return float(found["numbers"][name].replace(",", ""))


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_ring_model_is_the_transit_lessons_model(results):
    _, found = results
    # The claim: below 1e-12 for a uniform star, and small gaps for the
    # limb-darkened depth and grid, far below the data's errors.
    assert found["numbers"]["ast7-uniform-gap"] == "below 1e-12"
    assert _number(found, "ast7-depth-gap") < 1e-5
    assert _number(found, "ast7-grid-gap") < 3e-6


def test_the_cleaning_counts_are_the_files(results):
    _, found = results
    assert _number(found, "cadences") == 18864
    assert _number(found, "no-time") == 681
    assert _number(found, "no-flux") == 4503
    assert _number(found, "flagged") == 4506
    assert _number(found, "flagged-with-flux") == 3
    assert _number(found, "good") == 14358
    rows = {row[0].strip(): row[1] for row in found["tables"]["cleaning"]["rows"]}
    # Every cadence without a flux is flagged, so the claim "all but three
    # of those have no flux either" covers every missing flux.
    assert rows["without a flux but not flagged"] == "0"
    assert _number(found, "dips") == _number(found, "transits") == 21
    assert _number(found, "fitted-cadences") == 4819


def test_the_kept_cadences_are_the_flags_and_values_of_the_file(light_curve):
    good = tess_wasp18.good(light_curve)
    assert np.all(light_curve.quality[good] == 0)
    assert np.all(np.isfinite(light_curve.flux[good]))
    # Dropping only the missing values would keep the three flagged
    # cadences with a flux: the quality flag is a second rule.
    finite = np.isfinite(light_curve.flux) & np.isfinite(light_curve.time)
    assert finite.sum() - good.sum() == 3


def test_one_transit_is_normalised_as_the_analysis_does(light_curve, analysis):
    epoch = analysis.folded.epochs[0]
    window = lab.one_transit(light_curve, analysis, epoch)
    mine = analysis.folded.epoch == epoch
    np.testing.assert_allclose(window["time"], analysis.folded.time[mine])
    np.testing.assert_allclose(window["normalised"], analysis.folded.flux[mine])
    # The straight line sits above the parabola at mid-transit: the
    # baseline curves downward towards the transit.
    above = np.polyval(window["line"], 0.0) - np.polyval(window["parabola"], 0.0)
    assert above > 0


def test_the_baseline_varies_over_the_orbit(results):
    _, found = results
    quarter = _number(found, "phase-quarter")
    for key in ("transit", "half"):
        low, error = _number(found, f"phase-{key}"), _number(found, f"phase-{key}-err")
        combined = np.hypot(error, _number(found, "phase-quarter-err"))
        # Lower near the transit and half an orbit later than near the
        # quarter phases, by more than five combined standard errors.
        assert quarter - low > 5 * combined, key
    assert _number(found, "phase-orbits") >= 18


def test_the_fit_is_the_dossiers(results):
    _, found = results
    rows = {row[0]: row for row in found["tables"]["fit"]["rows"]}
    expected = {
        "p": (0.09795, 0.00039),
        "a/R*": (3.437, 0.035),
        "b": (0.400, 0.027),
        "u1": (0.237, 0.047),
        "u2": (0.266, 0.088),
    }
    for name, (value, error) in expected.items():
        assert float(rows[name][1]) == pytest.approx(value, abs=error / 10), name
        assert float(rows[name][2]) == pytest.approx(error, rel=0.05), name
    assert _number(found, "reduced-chi2") == pytest.approx(1.16, abs=0.01)
    assert found["numbers"]["fit-warnings"] == "none"
    assert _number(found, "corr-a-b") == pytest.approx(-0.98, abs=0.01)


def test_the_uniform_star_is_worse(analysis):
    uniform = lab.fit_uniform_star(analysis)
    # The claim: a far larger chi-square for two fewer parameters, and a
    # larger planet crossing farther from the centre.
    assert uniform.chi2 - analysis.shape.chi2 > 500
    assert uniform.reduced_chi2 > analysis.shape.reduced_chi2 + 0.1
    assert uniform.value("p") > analysis.shape.value("p")
    assert uniform.value("b") > analysis.shape.value("b") + 5 * analysis.shape.stderr[2]


def test_the_geometry_and_its_errors_are_those_of_the_claim(results):
    _, found = results
    assert _number(found, "depth") == pytest.approx(10696, abs=5)
    assert _number(found, "depth-err") == pytest.approx(29, abs=2)
    assert _number(found, "t14") == pytest.approx(2.1878, abs=2e-4)
    assert _number(found, "t14-err") == pytest.approx(0.0050, abs=3e-4)
    assert _number(found, "t23") == pytest.approx(1.720, abs=1e-3)
    assert _number(found, "inclination") == pytest.approx(83.3, abs=0.05)
    assert _number(found, "density") == pytest.approx(867, abs=1)
    # Correlations matter: the depth and T14 errors as if independent are
    # several times larger, as the page says.
    assert _number(found, "depth-err-independent") > 5 * _number(found, "depth-err")
    assert _number(found, "t14-err-independent") > 5 * _number(found, "t14-err")
    # The depth exceeds p^2, as limb darkening and b < 1 - p imply.
    assert _number(found, "depth") > _number(found, "p-squared")


def test_the_correlated_propagation_agrees_with_a_monte_carlo_draw(analysis):
    shape, period = analysis.shape, analysis.ephemeris.period
    values, errors, _ = lab.propagate_correlated(
        lambda x: lab.derived(x, period), shape.params, shape.covariance
    )
    rng = np.random.default_rng(420)
    draws = rng.multivariate_normal(shape.params, shape.covariance, size=4000)
    sampled = np.array([lab.derived(x, period) for x in draws])
    # Linear propagation against the spread of 4,000 draws: within 6 %
    # (the sampling error of a standard deviation from 4,000 draws is
    # about 1 %; the rest is the curvature of the functions).
    np.testing.assert_allclose(sampled.std(axis=0), errors, rtol=0.06)
    np.testing.assert_allclose(sampled.mean(axis=0), values, rtol=1e-2)


def test_the_mid_times_scatter_more_than_their_errors(results):
    _, found = results
    assert _number(found, "period") == pytest.approx(0.9414504, abs=2e-7)
    assert _number(found, "period-err") == pytest.approx(0.38, abs=0.01)
    assert _number(found, "timing-chi2") == pytest.approx(41.8, abs=0.1)
    assert _number(found, "timing-dof") == 19
    assert _number(found, "timing-scale") == pytest.approx(1.5, abs=0.05)
    assert _number(found, "period-err-scaled") == pytest.approx(0.57, abs=0.01)


def test_the_sensitivity_table_is_the_dossiers(results):
    _, found = results
    rows = found["tables"]["sensitivity"]["rows"]
    got = [(float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in rows]
    expected = [
        (0.09795, 3.437, 0.400, 10696),
        (0.09769, 3.448, 0.394, 10647),
        (0.09818, 3.427, 0.405, 10739),
        (0.09905, 3.387, 0.426, 10892),
    ]
    for (p, a, b, depth), (ep, ea, eb, edepth) in zip(got, expected, strict=True):
        assert p == pytest.approx(ep, abs=2e-5)
        assert a == pytest.approx(ea, abs=1.5e-3)
        assert b == pytest.approx(eb, abs=1.5e-3)
        assert depth == pytest.approx(edepth, abs=2)
    # The claim: the window moves p by about one standard error.
    spread = _number(found, "window-p-range")
    assert 0.8 < spread / _number(found, "p-err") < 1.6
    assert _number(found, "line-deeper") == pytest.approx(196, abs=2)


def test_the_density_disagrees_with_the_catalogue(results):
    _, found = results
    assert _number(found, "tic-density") == pytest.approx(693, abs=1)
    assert _number(found, "density-difference") == pytest.approx(20, abs=0.5)
    assert _number(found, "density-sigmas") >= 5


def test_the_exercises_print_what_their_solutions_say(experiment):
    radius = experiment.output("radius-exercise")
    # "somewhat larger than Jupiter"
    assert "in Jupiter radii: 1.28" in radius
    period = experiment.output("period-exercise")
    # "It matches the weighted fit's error"
    assert "standard error of the period: 0.38 s" in period


@pytest.mark.parametrize("label", sorted(lab.run().figures))
def test_every_figure_has_its_status_and_follows_the_conventions(experiment, label):
    figure = experiment.figures[label]()
    try:
        expected = "calibrated" if label == "fig-light-curve" else "processed"
        assert figure_status(figure) == expected
        assert check_figure(figure, residuals=label == "fig-transit-fit") == []
        for ax in figure.axes:
            legend = ax.get_legend()
            for t in [] if legend is None else legend.get_texts():
                text = t.get_text()
                if text.startswith(("measured", "PDCSAP")):
                    assert f"[{expected}]" in text or "[calibrated]" in text, (
                        label,
                        text,
                    )
                if text.startswith(("model", "baseline model")):
                    assert "[simulated]" in text, (label, text)
    finally:
        plt.close(figure)


def test_no_printed_output_is_a_block_of_numbers(experiment):
    for name, text in experiment.outputs.items():
        assert not is_numeric_console_block(text), name


def test_the_figures_leave_room_in_the_payload_budget_of_the_page(results):
    # The page budget is 3 MB; the earlier labs keep their figures under
    # 0.75 MB, and so does this one with four figures.
    directory, _ = results
    total = sum(p.stat().st_size for p in directory.glob("fig-*.png"))
    assert total < 750_000, total
