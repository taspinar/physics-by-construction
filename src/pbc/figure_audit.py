"""The audit of a lesson figure at desktop and phone widths (F170).

The figure-language pilot measures its sample figures before and after the
style, with the same code, so that the comparison is a measurement and not an
impression. ``measure(draw)`` draws a figure as the page does
(``pbc.experiment.encode``) and reports what a reader meets: the size of the
file, the width the page shows it at on a desktop and on a phone, the
smallest text at both widths in CSS pixels (the status label and the
credit left out: they are F172's), the legend entries, the line
widths, the markers drawn, the colour maps, and the least contrast of a data
line against the white plate. Run it as a program to print the audit of the
pilot's samples:

    uv run --locked python -m pbc.figure_audit

The audit is a tool of the pilot; no lesson imports it.
"""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import matplotlib
from matplotlib.collections import QuadMesh
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.text import Text

from pbc.authoring.design import PAGE, contrast_ratio
from pbc.data.plotting import CREDIT_GID, STATUS_GID
from pbc.experiment import FIGURE_SETTINGS, PIXEL_RATIO, encode, png_size

# CSS pixels per point of a figure shown at its natural size: the page shows
# a figure at its dpi (FIGURE_SETTINGS) over the 72 points of an inch.
PIXELS_PER_POINT = FIGURE_SETTINGS["figure.dpi"] / 72
# The width a figure image has on a phone of 375 CSS px: the content column
# measured on a built lesson page (324 px), less the plate's padding (two
# times --pbc-space-2) and its rule (two times 1 px).
PHONE_WIDTH = 324 - 2 * 8 - 2 * 1
# Wider than any figure: on a desktop the page shows a figure at its
# natural size (measured: half its pixel width, at 1280 CSS px).
DESKTOP_WIDTH = 760

# The pilot's samples: the class of figure, the experiment module, and the
# figure's label (docs/authoring.md, "Figure language").
SAMPLES = (
    ("trajectory", "pbc.mechanics.experiments.kepler_orbit", "fig-orbit-four-methods"),
    (
        "multi-series numerical comparison",
        "pbc.mechanics.experiments.kepler_orbit",
        "fig-orbit-thousand",
    ),
    (
        "phase space",
        "pbc.mechanics.experiments.hamiltonian_mechanics",
        "fig-phase-blob",
    ),
    (
        "convergence, log-log",
        "pbc.thermodynamics.experiments.heat_conduction_and_diffusion",
        "fig-heat-convergence",
    ),
    (
        "field",
        "pbc.thermodynamics.experiments.heat_conduction_and_diffusion",
        "fig-plate-temperature",
    ),
    (
        "measured against model, residuals",
        "pbc.electromagnetism.experiments.rlc_circuit_measurements",
        "fig-impedance-fit",
    ),
)


@dataclass(frozen=True)
class Audit:
    """What a reader meets in one figure."""

    bytes: int
    natural_width: int  # CSS px
    desktop_scale: float
    phone_scale: float
    smallest_text: float  # pt
    largest_text: float  # pt
    legend_entries: int
    titles: int
    line_widths: tuple[float, ...]
    markers: int
    colour_maps: tuple[str, ...]
    least_line_contrast: float | None  # None: the figure draws no line

    def text_px(self, points: float, scale: float) -> float:
        return points * PIXELS_PER_POINT * scale

    @property
    def smallest_desktop_px(self) -> float:
        return self.text_px(self.smallest_text, self.desktop_scale)

    @property
    def smallest_phone_px(self) -> float:
        return self.text_px(self.smallest_text, self.phone_scale)


def _texts(fig: Figure) -> list[Text]:
    return [
        t
        for t in fig.findobj(Text)
        if t.get_visible()
        and t.get_text().strip()
        and t.get_figure() is not None
        # The status label and the credit are F172's, not the language's.
        and t.get_gid() not in (STATUS_GID, CREDIT_GID)
    ]


def _inspect(fig: Figure) -> dict:
    fig.canvas.draw()  # creates the tick labels the page shows
    sizes = [t.get_fontsize() for t in _texts(fig)]
    legends = [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]
    legends += [x for x in fig.legends]
    lines = [
        line
        for ax in fig.axes
        for line in ax.get_lines()
        if line.get_visible() and len(line.get_xdata()) > 0
    ]
    widths = sorted(
        {
            round(line.get_linewidth(), 2)
            for line in lines
            if line.get_linestyle() != "None"
        }
    )
    markers = sum(
        len(line.get_xdata())
        for line in lines
        if line.get_marker() not in (None, "None", "", " ")
    )
    maps = sorted(
        {
            image.get_cmap().name
            for ax in fig.axes
            for image in [*ax.images, *ax.collections]
            if isinstance(image, AxesImage | QuadMesh)
        }
    )
    plate = PAGE["plate"]
    contrasts = [
        contrast_ratio(to_hex(line.get_color()), plate)
        for line in lines
        if isinstance(line, Line2D)
    ]
    return {
        "smallest_text": min(sizes),
        "largest_text": max(sizes),
        "legend_entries": sum(len(legend.get_texts()) for legend in legends),
        "titles": sum(1 for ax in fig.axes if ax.get_title()),
        "line_widths": tuple(widths),
        "markers": markers,
        "colour_maps": tuple(maps),
        "least_line_contrast": min(contrasts) if contrasts else None,
    }


def measure(draw: Callable[[], Figure]) -> Audit:
    """The audit of the figure ``draw`` returns, drawn as the page draws it."""
    import matplotlib.pyplot as plt

    png = encode(draw)
    width, _ = png_size(png)
    natural = width // PIXEL_RATIO
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        matplotlib.rcParams.update(FIGURE_SETTINGS)
        fig = draw()
        try:
            found = _inspect(fig)
        finally:
            plt.close(fig)
    return Audit(
        bytes=len(png),
        natural_width=natural,
        desktop_scale=min(1.0, DESKTOP_WIDTH / natural),
        phone_scale=min(1.0, PHONE_WIDTH / natural),
        **found,
    )


def sample_figures() -> list[tuple[str, str, Callable[[], Figure]]]:
    """The class, the label, and the drawing of every sample figure."""
    runs: dict = {}
    out = []
    for kind, module, label in SAMPLES:
        if module not in runs:
            runs[module] = importlib.import_module(module).run()
        out.append((kind, label, runs[module].figures[label]))
    return out


def _contrast(value: float | None) -> str:
    return "no line" if value is None else f"{value:.2f}"


def table(rows: list[tuple[str, str, Audit]]) -> str:
    """The audit as a Markdown table."""
    lines = [
        "| Class | Figure | Bytes | Width (px) | Text (pt) | Smallest text, "
        "desktop / phone (CSS px) | Legend entries | Titles | Line widths | "
        "Markers | Colour maps | Least line contrast |",
        "|---|---|--:|--:|---|---|--:|--:|---|--:|---|--:|",
    ]
    for kind, label, a in rows:
        lines.append(
            f"| {kind} | `{label}` | {a.bytes} | {a.natural_width} | "
            f"{a.smallest_text:g} to {a.largest_text:g} | "
            f"{a.smallest_desktop_px:.1f} / {a.smallest_phone_px:.1f} | "
            f"{a.legend_entries} | {a.titles} | "
            f"{', '.join(f'{w:g}' for w in a.line_widths)} | {a.markers} | "
            f"{', '.join(a.colour_maps) or 'none'} | "
            f"{_contrast(a.least_line_contrast)} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--write", metavar="DIRECTORY", help="also write every sample as <label>.png"
    )
    args = parser.parse_args(argv)
    figures = sample_figures()
    if args.write:
        directory = Path(args.write)
        directory.mkdir(parents=True, exist_ok=True)
        for _, label, draw in figures:
            (directory / f"{label}.png").write_bytes(encode(draw))
    rows = [(kind, label, measure(draw)) for kind, label, draw in figures]
    print(table(rows))
    total = sum(a.bytes for _, _, a in rows)
    print(f"\nTotal bytes of the samples: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
