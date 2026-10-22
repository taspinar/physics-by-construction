"""The interface artwork of the home page's featured capstone: wavefronts that
spread from a line in open water towards a coastline (F124).

Conceptual artwork for a planned capstone (ADR 018 decision 2): drawn by
code, the same bytes on every build, with no axis, scale, legend, number,
or measurement label, and computed from no model. The fronts are the curves
at equal distances from a straight line, the shape of a front from a long
source in water of one depth; the coastline is a sum of three sines. Neither
is data of a real place or event. The post-render script
``site/home-artwork.py`` writes the file into the built site, and the
provenance register ``site/assets/provenance.yaml`` names this module as
its source.
"""

import math
from pathlib import Path

from pbc.authoring.design import PAGE

WAVEFRONT = "home-wavefront.svg"
ASSETS = "assets"
WIDTH, HEIGHT = 640, 400
ALT = (
    "Conceptual artwork: wavefronts spreading from a line in open water"
    " towards a coastline."
)

# The source line, and the distance between two fronts.
SOURCE = ((505.0, 110.0), (565.0, 270.0))
SPACING = 30.0
FRONTS = 16


def _number(value: float) -> str:
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _point(x: float, y: float) -> str:
    return f"{_number(x)},{_number(y)}"


def _coast_x(y: float) -> float:
    return (
        150
        + 30 * math.sin(2 * math.pi * y / 330 + 0.6)
        + 9 * math.sin(2 * math.pi * y / 113 + 1.3)
        + 4 * math.sin(2 * math.pi * y / 41)
    )


def _coastline() -> list[tuple[float, float]]:
    return [(_coast_x(y), float(y)) for y in range(0, HEIGHT + 1, 5)]


def _front(distance: float) -> str:
    """The closed curve at ``distance`` from the source line: two straight
    sides and a half circle about each end."""
    (ax, ay), (bx, by) = SOURCE
    length = math.hypot(bx - ax, by - ay)
    nx, ny = (by - ay) / length, -(bx - ax) / length
    d = distance
    return (
        f"M{_point(ax + d * nx, ay + d * ny)}"
        f" L{_point(bx + d * nx, by + d * ny)}"
        f" A{_number(d)},{_number(d)} 0 0 1 {_point(bx - d * nx, by - d * ny)}"
        f" L{_point(ax - d * nx, ay - d * ny)}"
        f" A{_number(d)},{_number(d)} 0 0 1 {_point(ax + d * nx, ay + d * ny)} Z"
    )


def wavefront() -> str:
    """The artwork as an SVG document."""
    coast = _coastline()
    shore = " ".join(_point(x, y) for x, y in coast)
    sea = f"{shore} {WIDTH},{HEIGHT} {WIDTH},0"
    fronts = []
    for index in range(1, FRONTS + 1):
        # Fainter and thinner the farther a front has travelled.
        fade = 1 - (index - 1) / FRONTS
        fronts.append(
            f'<path d="{_front(index * SPACING)}"'
            f' stroke-width="{_number(0.8 + 1.4 * fade)}"'
            f' stroke-opacity="{fade * 0.85 + 0.15:.2f}"/>'
        )
    (ax, ay), (bx, by) = SOURCE
    return "".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg"'
            f' viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}"'
            ' role="img">',
            f"<title>{ALT}</title>",
            '<defs><clipPath id="sea">',
            f'<polygon points="{sea}"/>',
            "</clipPath></defs>",
            f'<g clip-path="url(#sea)" fill="none" stroke="{PAGE["night-line"]}">',
            *fronts,
            "</g>",
            f'<polyline points="{shore}" fill="none"'
            f' stroke="{PAGE["night-muted"]}" stroke-width="1.5"/>',
            f'<path d="M{_point(ax, ay)} L{_point(bx, by)}"'
            f' stroke="{PAGE["night-text"]}" stroke-width="3"'
            ' stroke-linecap="round"/>',
            "</svg>\n",
        ]
    )


def write(output: Path) -> Path:
    """Write the artwork into the built site ``output``; return its path."""
    path = output / ASSETS / WAVEFRONT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(wavefront(), encoding="utf-8")
    return path
