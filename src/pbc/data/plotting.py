"""Science-first plotting helpers and the figure conventions they enforce.

The conventions come from the requirements and ADR 007: a figure states its
status, every axis has a unit, a figure with more than one series has a legend,
a measured-versus-model figure has a residual panel, a colour scale that holds
both signs is centred on zero and does not hide the sign, a false-colour image
says so, and a smoothed series is never drawn as raw. ``check_figure`` returns
the violations of a finished figure as plain messages.
"""

import re
import textwrap
from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from pbc.data.series import Series
from pbc.data.status import FIGURE_STATUSES

# Okabe-Ito: distinguishable with the common kinds of colour-vision deficiency.
COLOURS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9")
STATUS_GID = "pbc-status"
CREDIT_GID = "pbc-credit"
_UNIT = re.compile(r"\[[^\]]+\]")


def _reserve(fig: Figure, *, top: float = 0.0, bottom: float = 0.0) -> None:
    """Keep ``top`` and ``bottom`` (fractions of the height) free of panels."""
    engine = fig.get_layout_engine()
    if engine is not None and hasattr(engine, "set"):
        engine.set(rect=(0, bottom, 1, 1 - top - bottom))
        fig._pbc_margins = (top, bottom)


def _margins(fig: Figure) -> tuple[float, float]:
    return getattr(fig, "_pbc_margins", (0.0, 0.0))


def label_status(fig: Figure, status: str) -> None:
    """Print the figure status in the upper left corner of the figure."""
    if status not in FIGURE_STATUSES:
        raise ValueError(f"status {status!r} is not one of {FIGURE_STATUSES}")
    for old in [t for t in fig.texts if t.get_gid() == STATUS_GID]:
        old.remove()
    _reserve(fig, top=0.5 / fig.get_figheight(), bottom=_margins(fig)[1])
    text = fig.text(
        0.005,
        0.995,
        f"status: {status}",
        ha="left",
        va="top",
        fontsize=9,
        fontweight="bold",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "0.3"},
    )
    text.set_gid(STATUS_GID)


def figure_status(fig: Figure) -> str | None:
    """The status printed on ``fig`` by ``label_status``, or None."""
    for text in fig.texts:
        if text.get_gid() == STATUS_GID:
            return text.get_text().removeprefix("status: ")
    return None


def add_credit(fig: Figure, text: str) -> None:
    """Print the attribution (and acknowledgement) text under the figure."""
    lines = textwrap.wrap(text, width=int(fig.get_figwidth() * 17))
    for old in [t for t in fig.texts if t.get_gid() == CREDIT_GID]:
        old.remove()
    height = (len(lines) * 0.13 + 0.1) / fig.get_figheight()
    _reserve(fig, top=_margins(fig)[0], bottom=height)
    fig.text(0.01, 0.005, "\n".join(lines), fontsize=7, va="bottom", gid=CREDIT_GID)


def _unit_label(name: str, unit: str) -> str:
    return f"{name} [{unit}]"


def plot_series(ax, series: Series, label: str, *, colour: str, **kwargs):
    """Draw ``series`` and its uncertainty band; a processed series says so.

    The legend entry names the steps taken, so that a smoothed or interpolated
    curve cannot pass for the recording. A modelled series is drawn dashed.
    """
    steps = f" ({series.disclosure()})" if series.steps else ""
    style = "--" if series.status == "simulated" else "-"
    if series.sigma is not None:
        ax.fill_between(
            series.x,
            series.y - series.sigma,
            series.y + series.sigma,
            color=colour,
            alpha=0.3,
            lw=0,
            label=f"{label}: 1 sigma",
        )
    (line,) = ax.plot(
        series.x,
        series.y,
        color=colour,
        linestyle=kwargs.pop("linestyle", style),
        lw=kwargs.pop("lw", 1.2),
        label=f"{label} [{series.status}]{steps}",
        **kwargs,
    )
    return line


def series_with_band(
    series: Series, label: str, *, figsize=(7, 3.5)
) -> tuple[Figure, plt.Axes]:
    """One time series with its uncertainty band and the status label."""
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    plot_series(ax, series, label, colour=COLOURS[0])
    ax.set_xlabel(_unit_label(series.x_name, series.x_unit))
    ax.set_ylabel(_unit_label(series.y_name, series.y_unit))
    ax.legend(fontsize=8)
    label_status(fig, series.status)
    return fig, ax


def residual(measured: Series, model: Series) -> np.ndarray:
    """Model minus measurement on the measurement's grid (model interpolated)."""
    return model.interpolate_to(measured.x).y - measured.y


def measured_vs_model(
    measured: Series,
    models: Mapping[str, Series],
    *,
    window: tuple[float, float] | None = None,
    figsize=(8, 6),
) -> tuple[Figure, tuple[plt.Axes, plt.Axes]]:
    """Measurement with its band, the models apart from it, and the residuals.

    The upper panel draws the measurement as a solid line with its uncertainty
    band and every model dashed; the lower panel is model minus measurement on
    the measurement's grid. The model is interpolated for that; the panel title
    says so. The status label is the measurement's.
    """
    for name, model in models.items():
        if model.status != "simulated":
            raise ValueError(f"model {name!r} is {model.status}, not simulated")
    if measured.status == "simulated":
        raise ValueError("the measurement is a simulation")
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=figsize, sharex=True, constrained_layout=True
    )
    plot_series(top, measured, "measurement", colour=COLOURS[0], lw=1.6)
    bottom.axhline(0, color="0.5", lw=0.8)
    for k, (name, model) in enumerate(models.items(), start=1):
        colour = COLOURS[k % len(COLOURS)]
        plot_series(top, model, name, colour=colour)
        r = residual(measured, model)
        inside = np.ones(r.shape, bool)
        if window is not None:
            inside = (measured.x >= window[0]) & (measured.x <= window[1])
        rms = np.sqrt(np.nanmean(r[inside] ** 2))
        bottom.plot(
            measured.x,
            r,
            color=colour,
            lw=1,
            label=f"{name}: RMS {rms:.3g} {measured.y_unit} in window",
        )
    if window is not None:
        for axis in (top, bottom):
            axis.axvspan(*window, color="0.5", alpha=0.12, lw=0)
    top.set_ylabel(_unit_label(measured.y_name, measured.y_unit))
    top.set_title("Measurement (solid) and modelled references (dashed)")
    top.legend(fontsize=8)
    bottom.set_xlabel(_unit_label(measured.x_name, measured.x_unit))
    bottom.set_ylabel(_unit_label("residual", measured.y_unit))
    bottom.set_title("Residual: model minus measurement, model interpolated")
    bottom.legend(fontsize=8)
    label_status(fig, measured.status)
    return fig, (top, bottom)


def signed_norm(field: np.ndarray, percentile: float = 99.0) -> Normalize:
    """A colour normalisation centred on zero, symmetric about it.

    The limits are the ``percentile`` of the absolute value, so one outlier does
    not wash out the field, and positive and negative values get the same
    colour range.
    """
    limit = float(np.nanpercentile(np.abs(field), percentile))
    if limit == 0.0:
        limit = 1.0
    return Normalize(vmin=-limit, vmax=limit)


def signed_image(ax, field: np.ndarray, *, label: str, unit: str, **kwargs):
    """Image of a field with both signs: diverging colours centred on zero.

    Masked samples (NaN) are drawn grey, not as a value. The colour bar says
    that the colours are an encoding, not the colour of the object.
    """
    cmap = plt.get_cmap("PuOr").with_extremes(bad="0.85")
    image = ax.imshow(
        np.ma.masked_invalid(field),
        cmap=cmap,
        norm=signed_norm(field),
        origin="lower",
        **kwargs,
    )
    bar = ax.figure.colorbar(image, ax=ax)
    bar.set_label(f"{label} [{unit}] (false colour, zero at the centre)")
    return image


def sequential_image(ax, field: np.ndarray, *, label: str, unit: str, **kwargs):
    """Image of a field of one sign; the colour bar says it is false colour."""
    cmap = plt.get_cmap("viridis").with_extremes(bad="0.85")
    image = ax.imshow(np.ma.masked_invalid(field), cmap=cmap, origin="lower", **kwargs)
    bar = ax.figure.colorbar(image, ax=ax)
    bar.set_label(f"{label} [{unit}] (false colour)")
    return image


def _lines_with_label(ax) -> int:
    return sum(
        1
        for line in ax.get_lines()
        if line.get_label() and not line.get_label().startswith("_")
    ) + sum(
        1
        for patch in ax.collections
        if patch.get_label() and not patch.get_label().startswith("_")
    )


def check_figure(
    fig: Figure, *, residuals: bool = False, declared: str | None = None
) -> list[str]:
    """Violations of the figure conventions; an empty list means none.

    Checks the status label, a unit in square brackets on every axis label, a
    title on every panel, a legend where a panel draws more than one named
    series, and, when ``residuals`` is true, a residual panel.

    ``declared`` is the status of a figure that declares its provenance
    (``pbc.data.figure_provenance``, Issue #524): it carries one status, at
    the caption and in its PNG's metadata, so a painted status label or a
    painted credit paragraph is a violation, and the declared status must
    be one of the five.
    """
    out: list[str] = []
    status = figure_status(fig)
    if declared is not None:
        if declared not in FIGURE_STATUSES:
            out.append(f"unknown declared status {declared!r}")
        if status is not None:
            out.append(
                "a status label is painted on a figure that declares its"
                " status: one status, at the caption"
            )
        if any(t.get_gid() == CREDIT_GID for t in fig.texts):
            out.append(
                "a credit is painted on a figure that declares its dataset:"
                " the caption and the metadata carry it"
            )
    elif status is None:
        out.append("no status label (use label_status)")
    elif status not in FIGURE_STATUSES:
        out.append(f"unknown status {status!r}")
    panels = [a for a in fig.axes if a.axison and a.get_label() != "<colorbar>"]
    if not panels:
        out.append("no panel")
    for k, ax in enumerate(panels):
        where = f"panel {k + 1}"
        if not ax.get_title():
            out.append(f"{where}: no title")
        # Panels that share an x axis carry its label on the lowest one.
        shares_x = len(ax.get_shared_x_axes().get_siblings(ax)) > 1
        below = shares_x and not ax.get_subplotspec().is_last_row()
        labels = [("y", ax.get_ylabel())] + ([] if below else [("x", ax.get_xlabel())])
        for name, axis in labels:
            if not _UNIT.search(axis):
                out.append(f"{where}: {name} label {axis!r} has no unit in [...]")
        if _lines_with_label(ax) > 1 and ax.get_legend() is None:
            out.append(f"{where}: several series and no legend")
    if residuals and not any("residual" in a.get_ylabel().lower() for a in panels):
        out.append("no residual panel")
    for ax in fig.axes:
        if ax.get_label() == "<colorbar>" and "false colour" not in (
            ax.get_ylabel() + ax.get_xlabel()
        ):
            out.append("a colour bar that does not say 'false colour'")
    return out
