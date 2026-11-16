"""The figure language (F170, revised by F171): one style for a lesson figure.

A figure opts in inside its ``draw_`` function: it draws in a ``with
figure_style():`` block, under ``RC`` on top of the settings of
``pbc.experiment.encode`` (``FIGURE_SETTINGS``), and returns
``finish(fig)``, which sets the grid and gives a field its frame. No
decorator: a lesson shows its ``draw_`` functions with ``excerpt``, which
must find each one, and its lines, in the lesson's own module.
Nothing changes for a figure that does not opt in: ``FIGURE_SETTINGS`` stays
as it is. F171 revised the sizes (the owner's decision on Issue #544) and
opted in the figures that ``docs/authoring.md`` ("Figure language") lists.

The values come from the design tokens of ``pbc.authoring.design`` (the ink,
the muted grey, the rule, the white plate, the figure colours); the module
adds sizes, line weights, and the rules below, and no colour of its own.
``docs/authoring.md`` ("Figure language") describes the language and when
each part applies.

- **Dimensions.** One width, ``WIDTH``, for every figure; heights from
  ``ASPECTS``; two panels stacked, never side by side. On a phone the page
  scales a figure down to about 306 CSS px (375 px phone) or 251 CSS px
  (320 px phone), so the width and the type are chosen together: the
  smallest text is 9 CSS px or more at 320 px (F171).
- **Typography.** DejaVu Sans, the face Matplotlib ships: the site's STIX Two
  Text exists only as web-font subsets, and the STIXGeneral Matplotlib ships
  shares its name with system copies (macOS), so the face a machine picks,
  and the bytes, would depend on the machine. Sizes from ``TEXT``; nothing
  smaller than ``MIN_TEXT`` points; at most ``TICKS`` ticks on an axis
  Matplotlib places.
- **Legends.** At most three entries inside the axes, where they cover no
  data; otherwise the series are named beside the curves (``direct_label``)
  or the legend goes under the plot in one column.
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
  An isoline on a field is white or ink by its level (``isoline_colours``)
  and carries a thin casing of the other (``cased``), so that it keeps
  3:1 where it meets a boundary of another colour than its level's.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

import matplotlib
import numpy as np
from matplotlib import cycler, patheffects
from matplotlib.ticker import AutoLocator, MaxNLocator

from pbc.authoring.design import CONTROL_CONTRAST, FIGURE_COLOURS, PAGE, contrast_ratio

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

# The width of every figure, in inches: 394 CSS px on a desktop, scaled to
# 0.78 on a 375 px phone and 0.64 on a 320 px phone (F171, the revised
# language: one PNG serves every width, so the text-to-width ratio sets the
# size a phone shows).
WIDTH = 4.1
# Height over width, by the kind of figure. Two panels are stacked, never
# side by side: side by side, each would have half the width on a phone.
ASPECTS = {
    "line": 0.78,  # one panel of lines
    "pair": 1.3,  # two panels, one above the other
    "square": 1.0,  # a trajectory or an orbit with equal axes
    "stacked": 1.3,  # two panels, one above the other
    "measured": 1.6,  # three stacked panels of measured data and residuals
}
# Type sizes in points. At WIDTH, a point is 1.33 CSS px on a desktop,
# 0.78 CSS px on a 375 px phone (306 CSS px, PHONE_WIDTH of
# pbc.figure_audit) and 0.64 CSS px on a 320 px phone (251 CSS px), so
# MIN_TEXT is 14.7, 11.4 and 9.3 CSS px; the tight crop of a saved figure
# widens it by up to 2.5 %, so a 320 px phone shows at least 9.0 CSS px
# (the tests' bound).
TEXT = {"tick": 11.0, "label": 12.0, "title": 12.0, "legend": 11.0, "note": 11.0}
MIN_TEXT = 11.0
# The height one entry of a legend under the plot takes, in inches (an
# 11 pt line and its spacing): ``figsize`` adds it per entry, so that the
# plot keeps its height when the legend moves under it.
LEGEND_ROW = 0.24
# At most this many major ticks on a linear axis whose ticks Matplotlib
# places itself (``finish``); a figure's own tick set is kept.
TICKS = 5
# Line widths in points: the hierarchy of a figure.
LINE = {"data": 1.8, "model": 1.4, "guide": 1.0, "axis": 0.8, "grid": 0.6}
# The casing of an isoline, in points on each side of its stroke.
CASING = 0.6
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


def figsize(kind: str, *, legend: int = 0) -> tuple[float, float]:
    """The size of a figure of the kind ``kind`` (a key of ``ASPECTS``), with
    room for ``legend`` entries of a legend under the plot."""
    return (WIDTH, round(WIDTH * ASPECTS[kind] + legend * LEGEND_ROW, 2))


def line_colours(palette: Sequence[str]) -> tuple[str, ...]:
    """The colours of ``palette`` that a line may take: at least 3:1 against
    the plate."""
    return tuple(c for c in palette if contrast_ratio(c, PLATE) >= CONTROL_CONTRAST)


def isoline_colours(
    levels: Sequence[float], vmin: float, vmax: float, cmap: str = SEQUENTIAL
) -> list[str]:
    """The colour of each isoline of ``levels`` on a field drawn with ``cmap``
    from ``vmin`` to ``vmax``: the plate's white or the ink, whichever has the
    more contrast with the map's colour at the level, the colour the field
    has under the line."""
    from matplotlib.colors import to_hex

    colour_map = matplotlib.colormaps[cmap]
    colours = []
    for level in levels:
        under = to_hex(colour_map((level - vmin) / (vmax - vmin)))
        colours.append(
            max((PLATE, INK), key=lambda colour: contrast_ratio(colour, under))
        )
    return colours


def cased(colour: str, width: float = LINE["guide"]) -> list:
    """The path effects of an isoline of ``colour`` (white or ink) and
    ``width``: a casing of the other colour beneath it, ``CASING`` points on
    each side. Where the field under the line is close to the line's own
    colour (a boundary of another temperature than the level's), the casing
    gives it its edge; the line stays where the field puts it."""
    other = (
        INK if contrast_ratio(colour, PLATE) < contrast_ratio(colour, INK) else PLATE
    )
    return [patheffects.withStroke(linewidth=width + 2 * CASING, foreground=other)]


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
    it; a field keeps its frame and never has a grid. A linear axis whose
    ticks Matplotlib places itself gets at most ``TICKS`` major ticks; an
    axis with a tick set of its own, or a log axis, keeps its ticks."""
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
        for axis, scale in ((ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())):
            if scale == "linear" and type(axis.get_major_locator()) is AutoLocator:
                axis.set_major_locator(MaxNLocator(TICKS, steps=[1, 2, 2.5, 5, 10]))
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
