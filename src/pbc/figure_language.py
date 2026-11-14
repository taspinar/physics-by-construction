"""The figure language of the pilot (F170): one style for a lesson figure.

A figure opts in inside its ``draw_`` function: it draws in a ``with
figure_style():`` block, under ``RC`` on top of the settings of
``pbc.experiment.encode`` (``FIGURE_SETTINGS``), and returns
``finish(fig)``, which sets the grid and gives a field its frame. No
decorator: a lesson shows its ``draw_`` functions with ``excerpt``, which
must find each one, and its lines, in the lesson's own module.
Nothing changes for a figure that does not opt in: ``FIGURE_SETTINGS`` stays
as it is (a global change is F171, after the owner's decision).

The values come from the design tokens of ``pbc.authoring.design`` (the ink,
the muted grey, the rule, the white plate, the figure colours); the module
adds sizes, line weights, and the rules below, and no colour of its own.
``docs/authoring.md`` ("Figure language") describes the language and when
each part applies.

- **Dimensions.** One width, ``WIDTH``, for every figure; heights from
  ``ASPECTS``. On a phone the page scales a figure down to about 306 CSS px,
  so a figure narrower than the old default keeps its text legible there.
- **Typography.** DejaVu Sans, the face Matplotlib ships: the site's STIX Two
  Text exists only as web-font subsets, and the STIXGeneral Matplotlib ships
  shares its name with system copies (macOS), so the face a machine picks,
  and the bytes, would depend on the machine. Sizes from ``TEXT``; nothing
  smaller than ``MIN_TEXT`` points.
- **Hierarchy.** Labels and titles in ink, tick labels in the muted grey,
  axes and ticks in the rule's grey, no top or right spine on a line plot;
  data lines ``LINE["data"]``, models ``LINE["model"]``, reference lines and
  guides ``LINE["guide"]``, a light grid only where reading values off the
  plot is the point (``finish(fig, grid=True)``).
- **Colour.** A lesson figure takes its series colours from
  ``FIGURE_COLOURS``; a figure of measured data drawn with
  ``pbc.data.plotting`` keeps the Okabe-Ito ``COLOURS`` for its measurement
  and its models. ``line_colours`` leaves out the colours of a palette that
  have less than 3:1 against the plate, so a line is never fainter than that.
- **Colour maps by data semantics.** ``SEQUENTIAL`` for a magnitude that
  does not change sign (a temperature, a density, an intensity),
  ``DIVERGING`` centred on zero for a signed quantity
  (``pbc.data.plotting.signed_norm``); the colour bar says "false colour".
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

import matplotlib
import numpy as np
from matplotlib import cycler

from pbc.authoring.design import CONTROL_CONTRAST, FIGURE_COLOURS, PAGE, contrast_ratio

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

# The width of every figure, in inches: 538 CSS px on a desktop, scaled to
# 0.57 on a phone.
WIDTH = 5.6
# Height over width, by the kind of figure.
ASPECTS = {
    "line": 0.62,  # one panel of lines
    "pair": 0.5,  # two panels side by side
    "square": 0.9,  # a trajectory or an orbit with equal axes
    "stacked": 0.95,  # two panels, one above the other
    "measured": 1.15,  # three stacked panels of measured data and residuals
}
# Type sizes in points. At WIDTH, a point is 1.33 CSS px on a desktop and
# 0.76 CSS px on a phone, so MIN_TEXT is 12.7 and 7.2 CSS px.
TEXT = {"tick": 10.0, "label": 11.0, "title": 11.0, "legend": 10.0, "note": 9.5}
MIN_TEXT = 9.5
# Line widths in points: the hierarchy of a figure.
LINE = {"data": 1.8, "model": 1.4, "guide": 1.0, "axis": 0.8, "grid": 0.6}
MARKER = 4.5

INK = PAGE["text"]
MUTED = PAGE["muted"]
RULE = PAGE["rule"]
PLATE = PAGE["plate"]
GRID_ALPHA = 0.35

SEQUENTIAL = "viridis"
DIVERGING = "PuOr"

RC = {
    "font.family": "DejaVu Sans",
    "font.size": TEXT["tick"],
    "text.color": INK,
    "axes.labelsize": TEXT["label"],
    "axes.labelcolor": INK,
    "axes.titlesize": TEXT["title"],
    "axes.titlecolor": INK,
    "axes.titlepad": 6.0,
    "axes.edgecolor": RULE,
    "axes.linewidth": LINE["axis"],
    "axes.facecolor": PLATE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.prop_cycle": cycler(color=FIGURE_COLOURS),
    "xtick.labelsize": TEXT["tick"],
    "ytick.labelsize": TEXT["tick"],
    "xtick.color": RULE,
    "ytick.color": RULE,
    "xtick.labelcolor": MUTED,
    "ytick.labelcolor": MUTED,
    "grid.color": RULE,
    "grid.alpha": GRID_ALPHA,
    "grid.linewidth": LINE["grid"],
    "lines.linewidth": LINE["data"],
    "lines.markersize": MARKER,
    "legend.fontsize": TEXT["legend"],
    "legend.frameon": False,
    "legend.handlelength": 2.6,
    "image.cmap": SEQUENTIAL,
    "figure.facecolor": PLATE,
    "figure.constrained_layout.use": True,
}


def figsize(kind: str) -> tuple[float, float]:
    """The size of a figure of the kind ``kind`` (a key of ``ASPECTS``)."""
    return (WIDTH, round(WIDTH * ASPECTS[kind], 2))


def line_colours(palette: Sequence[str]) -> tuple[str, ...]:
    """The colours of ``palette`` that a line may take: at least 3:1 against
    the plate."""
    return tuple(c for c in palette if contrast_ratio(c, PLATE) >= CONTROL_CONTRAST)


@contextmanager
def figure_style() -> Iterator[None]:
    """Draw under the figure language's settings."""
    with matplotlib.rc_context(RC):
        yield


def _has_image(ax: Axes) -> bool:
    return bool(ax.images) or any(
        type(c).__name__ in ("QuadMesh", "QuadContourSet") for c in ax.collections
    )


def finish(fig: Figure, *, grid: bool = False) -> Figure:
    """Set the grid of every axes of ``fig``, only where ``grid`` asks for
    it; a field keeps its frame and never has a grid."""
    for ax in fig.axes:
        image = _has_image(ax)
        if image:
            for spine in ax.spines.values():
                spine.set_visible(True)
        if grid and not image:
            ax.grid(
                True,
                which="major",
                color=RULE,
                alpha=GRID_ALPHA,
                linewidth=LINE["grid"],
            )
        else:
            ax.grid(False)
    return fig


def direct_label(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    colour: str,
    *,
    offset: tuple[float, float] = (4.0, 0.0),
    ha: str = "left",
    va: str = "center",
) -> None:
    """Name a series beside the point (x, y) of it, in its colour, instead of
    in a legend."""
    ax.annotate(
        text,
        (x, y),
        xytext=offset,
        textcoords="offset points",
        color=colour,
        fontsize=TEXT["note"],
        ha=ha,
        va=va,
    )


def reference_slope(
    ax: Axes, h: Iterable[float], anchor: float, order: int, *, below: float = 0.5
) -> None:
    """The reference line of slope ``order`` on log-log axes through
    ``below * anchor`` at the first ``h``, in the guide's style, labelled
    "slope <order>" below its middle: a comparison, never a fit."""
    h = np.asarray(list(h), dtype=float)
    reference = below * anchor * (h / h[0]) ** order
    ax.loglog(h, reference, color=MUTED, linestyle=":", linewidth=LINE["guide"])
    # Below and right of the middle of the line, away from the data above it.
    middle = int(np.argsort(h)[len(h) // 2])
    direct_label(
        ax,
        h[middle],
        reference[middle],
        f"slope {order}",
        MUTED,
        offset=(6.0, -6.0),
        ha="left",
        va="top",
    )
