"""The plotting helpers enforce the figure conventions, and the reference
figures of the go datasets are made with them and keep their dossiers'
status labels.
"""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pbc.data import SAMPLES_DIR
from pbc.data.plotting import (
    add_credit,
    check_figure,
    figure_status,
    label_status,
    measured_vs_model,
    series_with_band,
    signed_image,
    signed_norm,
)
from pbc.data.reference import aalborg_flume, bayreuth_rlc, gw150914, npl_sparameters
from pbc.data.series import Series

AAL = SAMPLES_DIR / "aalborg-submerged-bar"
GW = SAMPLES_DIR / "gw150914-strain"
NPL = SAMPLES_DIR / "npl-onwafer-sparameters"
RLC = SAMPLES_DIR / "bayreuth-rlc-impedance"


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def series(artifact, steps=(), shift=0.0):
    x = np.linspace(0, 10, 101)
    return Series(
        x=x,
        y=np.sin(x) + shift,
        sigma=np.full(x.shape, 0.05) if artifact != "modelled-reference" else None,
        artifact=artifact,
        x_name="time",
        x_unit="s",
        y_name="elevation",
        y_unit="m",
        steps=steps,
    )


def test_a_figure_without_a_status_a_unit_a_title_or_a_legend_is_reported():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="a")
    ax.plot([0, 1], [1, 0], label="b")
    ax.set_xlabel("time")
    problems = check_figure(fig)
    assert any("no status label" in p for p in problems)
    assert any("no title" in p for p in problems)
    assert any("x label 'time' has no unit" in p for p in problems)
    assert any("y label '' has no unit" in p for p in problems)
    assert any("no legend" in p for p in problems)
    assert check_figure(fig, residuals=True)[-1:] != []


def test_a_figure_that_follows_the_conventions_passes():
    fig, ax = series_with_band(series("processed-measured"), "gauge")
    ax.set_title("Elevation at the gauge")
    assert figure_status(fig) == "processed"
    assert check_figure(fig) == []


def test_the_status_label_is_one_of_the_five_and_is_replaced_not_stacked():
    fig = plt.figure()
    with pytest.raises(ValueError):
        label_status(fig, "natural")
    label_status(fig, "measured")
    label_status(fig, "processed")
    assert figure_status(fig) == "processed"
    assert len([t for t in fig.texts if "status:" in t.get_text()]) == 1


def test_the_measured_versus_model_figure_has_residuals_and_the_measurement_status():
    measured = series("processed-measured")
    model = series("modelled-reference", shift=0.1)
    fig, (top, bottom) = measured_vs_model(measured, {"model": model})
    top.set_title("t")
    assert figure_status(fig) == "processed"
    assert "residual" in bottom.get_ylabel()
    np.testing.assert_allclose(bottom.lines[-1].get_ydata(), 0.1, atol=1e-12)
    assert check_figure(fig, residuals=True) == []
    legend = " ".join(t.get_text() for t in top.get_legend().get_texts())
    assert "[processed]" in legend and "[simulated]" in legend
    assert top.lines[-1].get_linestyle() == "--", "the model is drawn apart"


def test_a_model_cannot_be_drawn_as_a_measurement_and_the_reverse():
    with pytest.raises(ValueError, match="not simulated"):
        measured_vs_model(series("raw-measured"), {"m": series("raw-measured")})
    with pytest.raises(ValueError, match="simulation"):
        measured_vs_model(series("modelled-reference"), {})


def test_a_smoothed_series_is_named_as_smoothed_in_the_legend_and_not_called_raw():
    smoothed = series("raw-measured").smooth(5)
    fig, ax = series_with_band(smoothed, "recording")
    text = " ".join(t.get_text() for t in ax.get_legend().get_texts())
    assert "smoothed by a moving average of 5 samples" in text
    assert "[processed]" in text and "[measured]" not in text
    assert figure_status(fig) == "processed"


def test_a_signed_colour_scale_is_centred_on_zero_and_marks_masks_and_false_colour():
    field = np.array([[-3.0, 1.0], [np.nan, 2.0]])
    norm = signed_norm(field, percentile=100)
    assert (norm.vmin, norm.vmax) == (-3.0, 3.0)
    assert signed_norm(np.zeros((2, 2))).vmax == 1.0
    fig, ax = plt.subplots()
    image = signed_image(ax, field, label="velocity", unit="m/s")
    assert np.ma.getmaskarray(image.get_array())[1, 0]
    bar = next(a for a in fig.axes if a.get_label() == "<colorbar>")
    assert "false colour" in bar.get_ylabel() and "[m/s]" in bar.get_ylabel()
    ax.set_title("x")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    label_status(fig, "processed")
    assert check_figure(fig) == []


def test_a_colour_bar_that_is_not_called_false_colour_is_reported():
    fig, ax = plt.subplots()
    fig.colorbar(ax.imshow(np.eye(2)), ax=ax, label="amplitude [V]")
    assert any("false colour" in p for p in check_figure(fig))


def test_the_credit_line_is_wrapped_and_kept_inside_the_figure():
    fig, ax = plt.subplots(constrained_layout=True)
    add_credit(fig, "Data: someone, somewhere. " * 12)
    credit = next(t for t in fig.texts if t.get_gid() == "pbc-credit")
    assert credit.get_text().count("\n") >= 1
    fig.canvas.draw()
    box = credit.get_window_extent().transformed(fig.transFigure.inverted())
    assert box.y0 >= 0 and ax.get_position().y0 > box.y1 - 1e-9


@pytest.mark.parametrize(
    ("module", "path", "status", "residuals"),
    [
        (gw150914, GW, "processed", False),
        (npl_sparameters, NPL, "calibrated", False),
        (aalborg_flume, AAL, "processed", True),
        (bayreuth_rlc, RLC, "processed", True),
    ],
)
def test_each_reference_figure_is_made_with_the_helpers_and_has_its_dossiers_status(
    module, path, status, residuals
):
    fig = module.make_figure(path)
    assert figure_status(fig) == status
    assert check_figure(fig, residuals=residuals) == []


def test_the_dossiers_state_the_status_of_their_figure():
    root = SAMPLES_DIR.parents[1] / "docs/datasets"
    for name, status in (
        ("gw150914-strain", "processed"),
        ("npl-onwafer-sparameters", "calibrated"),
        ("aalborg-submerged-bar", "processed"),
        ("bayreuth-rlc-impedance", "processed"),
    ):
        text = (root / f"{name}.md").read_text().replace("**", "")
        assert f"Status label: {status}" in text, name
