"""The data of the waveform comparator: the page embeds what the lab computed."""

import json

import numpy as np
import pytest

from pbc.authoring.widgets import widget_asset
from pbc.data import SAMPLES_DIR, gwstrain
from pbc.data.comparison import DECIMALS, SCHEMA, named_comparison, waveform_comparison
from pbc.data.gwosc import FILES, read_strain
from pbc.data.gwstrain import (
    cut_segment,
    fit_chirp,
    make_whitener,
    models_at_masses,
    noise_sigma,
)

BAND = (35.0, 350.0)
WINDOW = (-0.2, 0.0)
LAG = -0.00732


@pytest.fixture(scope="module")
def lab():
    strains = {
        n: read_strain(SAMPLES_DIR / "gw150914-strain" / f) for n, f in FILES.items()
    }
    seg = {n: cut_segment(s, 0.75) for n, s in strains.items()}
    white = {n: make_whitener(strains[n], seg[n], BAND) for n in strains}
    data = {n: white[n](seg[n].strain) for n in strains}
    time = seg["H1"].time
    sigma = noise_sigma(data["H1"], time, (0.3, 0.65))
    delays = {"H1": 0.0, "L1": LAG}
    fit = fit_chirp(
        time, data, white, delays, window=WINDOW, sigma=sigma,
        mc_grid=np.arange(22.0, 50.0, 2.0),
    )  # fmt: skip
    return time, data, white, delays, sigma, fit


def test_the_model_at_the_fitted_mass_reproduces_the_fit(lab):
    time, data, white, delays, sigma, fit = lab
    [at_best] = models_at_masses(
        time, data, white, delays, np.array([fit.mc]), window=WINDOW, sigma=sigma,
        mc_start=fit.mc, t_c_start=fit.t_c,
    )  # fmt: skip
    assert at_best.t_c == pytest.approx(fit.t_c, abs=2e-4)
    assert at_best.chi2 == pytest.approx(fit.fit.chi2, rel=2e-3)
    assert at_best.reduced_chi2 == pytest.approx(fit.reduced_chi2, rel=5e-2)
    for name in white:
        assert at_best.model[name] == pytest.approx(fit.models[name], abs=5e-2)


@pytest.mark.parametrize("fault", ["not converged", "not finite"])
def test_a_failed_search_leaves_the_grid_point_standing(lab, monkeypatch, fault):
    time, data, white, delays, sigma, fit = lab

    def at(mass):
        [model] = models_at_masses(
            time, data, white, delays, np.array([mass]), window=WINDOW, sigma=sigma,
            mc_start=fit.mc, t_c_start=fit.t_c,
        )  # fmt: skip
        return model

    search = gwstrain.optimize.minimize_scalar

    def fails(function, **options):
        result = search(function, **options)
        # A result that looks better than the grid point, far from it, and
        # that may not be used.
        result.x = options["bounds"][0] - 0.05
        if fault == "not converged":
            result.success = False
            result.fun = -1.0
        else:
            result.fun = float("-inf")
        return result

    monkeypatch.setattr(gwstrain.optimize, "minimize_scalar", fails)
    failed = at(fit.mc)
    monkeypatch.undo()
    searched = at(fit.mc)

    # The time is a point of the fine grid, which is a tenth of a millisecond
    # apart, and the chi-square is the one of that point, not of the search.
    assert failed.t_c == pytest.approx(searched.t_c, abs=1.5e-4)
    assert np.isfinite(failed.chi2) and failed.chi2 > 0
    assert failed.chi2 >= searched.chi2 - 1e-9


def test_the_metrics_rank_the_masses_as_the_profile_does(lab):
    time, data, white, delays, sigma, fit = lab
    masses = np.array([26.0, fit.mc, 44.0])
    models = models_at_masses(
        time, data, white, delays, masses, window=WINDOW, sigma=sigma,
        mc_start=fit.mc, t_c_start=fit.t_c,
    )  # fmt: skip
    assert min(models, key=lambda m: m.chi2).mc == pytest.approx(fit.mc)
    assert min(models, key=lambda m: m.rms_residual).mc == pytest.approx(fit.mc)
    assert max(models, key=lambda m: m.correlation).mc == pytest.approx(fit.mc)
    assert all(-1.0 <= m.correlation <= 1.0 for m in models)


def test_the_embedded_measured_series_is_the_data_to_the_stated_rounding(lab):
    time, data, white, delays, sigma, fit = lab
    models = models_at_masses(
        time, data, white, delays, np.array([fit.mc]), window=WINDOW, sigma=sigma,
        mc_start=fit.mc, t_c_start=fit.t_c,
    )  # fmt: skip
    payload = waveform_comparison(
        time, data["H1"], models, "H1", sigma=sigma, window=WINDOW,
        show=(-0.25, 0.05), quantity="whitened strain", unit="1", best=fit.mc,
    )  # fmt: skip
    assert payload["schema"] == SCHEMA
    shown = (time >= -0.25) & (time <= 0.05)
    # Nothing is smoothed or resampled: every sample is there, rounded only.
    assert np.array(payload["measured"]) == pytest.approx(
        data["H1"][shown], abs=0.5 * 10.0**-DECIMALS + 1e-12
    )
    assert np.array(payload["time"]) == pytest.approx(time[shown], abs=1e-5)
    assert np.array(payload["models"][0]["values"]) == pytest.approx(
        models[0].model["H1"][shown], abs=0.5 * 10.0**-DECIMALS + 1e-12
    )
    # The residual is the measurement minus the model, as plotted.
    assert np.array(payload["models"][0]["residual"]) == pytest.approx(
        (data["H1"] - models[0].model["H1"])[shown], abs=0.5 * 10.0**-DECIMALS + 1e-12
    )
    json.dumps(payload, allow_nan=False)


def test_the_chirp_family_carries_the_words_the_component_showed_before(lab):
    # The text of the gravitational-wave lab's component moved into its data;
    # what the reader sees is the same.
    time, data, white, delays, sigma, fit = lab
    models = models_at_masses(
        time, data, white, delays, np.array([fit.mc]), window=WINDOW, sigma=sigma,
        mc_start=fit.mc, t_c_start=fit.t_c,
    )  # fmt: skip
    payload = waveform_comparison(
        time, data["H1"], models, "H1", sigma=sigma, window=WINDOW,
        show=(-0.25, 0.05), quantity="whitened strain", unit="1", best=fit.mc,
    )  # fmt: skip
    labels = payload["labels"]
    assert labels["measured"] == "measured, whitened"
    assert labels["model"] == "model, chirp mass, detector frame "
    assert labels["title"] == "whitened strain of detector H1, measured and model"
    assert labels["notes"] == [f"noise standard deviation: {payload['sigma']!r}"]
    assert [m[2] for m in payload["metrics"]] == [1, 3, 4, 4]
    assert payload["details"][0][0] == "coalescence_time"


def test_a_named_family_holds_the_measurement_each_model_and_its_metrics():
    time = np.linspace(0.0, 3.0, 301)
    measured = 0.01 * np.sin(2 * np.pi * time)
    models = {
        "exact": measured.copy(),
        "shifted": 0.01 * np.sin(2 * np.pi * (time - 0.25)),
    }
    payload = named_comparison(
        time, measured, models, window=(1.0, 2.0), quantity="elevation",
        unit="mm", measured_label="measured", title="elevation", scale=1000.0,
    )  # fmt: skip
    assert payload["schema"] == SCHEMA
    assert payload["best_parameter"] is None
    assert [m["parameter"] for m in payload["models"]] == ["exact", "shifted"]
    assert np.array(payload["measured"]) == pytest.approx(1000 * measured, abs=1e-5)
    exact, shifted = payload["models"]
    assert exact["metrics"]["rms_residual"] == 0.0
    assert exact["metrics"]["correlation"] == 1.0
    # A quarter period out of phase: the residual of two sines of 10 mm.
    assert shifted["metrics"]["rms_residual"] == pytest.approx(10.0, abs=0.05)
    assert shifted["metrics"]["correlation"] == pytest.approx(0.0, abs=0.01)
    # The residual is the model minus the measurement, as the static figure.
    assert np.array(shifted["residual"]) == pytest.approx(
        np.array(shifted["values"]) - np.array(payload["measured"]), abs=2e-5
    )
    assert payload["labels"]["notes"][0] == "residual: model minus measured"
    json.dumps(payload, allow_nan=False)


def test_an_on_demand_file_is_written_beside_the_page(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = widget_asset("example-data", {"a": [1.5, 2.0]})
    assert url == "index_files/figure-html/example-data.json"
    assert json.loads((tmp_path / url).read_text()) == {"a": [1.5, 2.0]}


@pytest.mark.parametrize("name", ["Upper", "a/b", "a b", "../x", ""])
def test_an_on_demand_file_name_is_a_plain_lower_case_word(tmp_path, monkeypatch, name):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        widget_asset(name, {})


def test_an_on_demand_file_refuses_data_that_json_cannot_hold(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        widget_asset("bad", {"x": float("nan")})
