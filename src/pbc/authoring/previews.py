"""The small preview of every lesson (F63).

A preview is what the learning path shows beside a lesson: one small picture
that is never committed, copied, or fetched. It comes from one of two places.

- A lesson whose front matter names a figure cell in ``lesson.preview`` gets
  that figure, as the executed cell drew it, scaled to a fixed size. The cell
  is the figure of the lesson, so the preview carries its status and cannot
  drift from it.
- A lesson without ``preview`` gets a conceptual SVG that this module draws
  from the course and the methods of the lesson. It claims no result.

``write_previews`` runs after the site is rendered (``site/lesson-previews.py``)
and writes one file per lesson to ``previews/`` of the built site; the path
export names the file and its alt text. The alt text starts with the status of
the figure. The same input gives the same bytes: the scaling and the
encoding have no state, and the drawing is a string.

A figure preview is lossless WebP: every pixel of the scaled figure is kept,
in about half the bytes of a PNG (Issue #319), so the learning path page with
every preview stays within its payload budget.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

import yaml
from PIL import Image

from pbc.authoring.design import FIGURE_COLOURS, FIGURE_STATUSES, PAGE, STATUS_LABELS
from pbc.authoring.path import COURSES, LearningPath, Lesson

PREVIEW_DIRECTORY = "previews"
# The size of every preview in pixels, whatever the figure it comes from.
WIDTH = 320
HEIGHT = 200
# The effort of the lossless WebP encoder: within 2 percent of its smallest
# output for the figures of the site, at a fraction of the encoding time.
_WEBP = {"lossless": True, "quality": 80, "method": 6}
# Where Quarto writes the figure of an executed cell, beside the page.
_FIGURES = "index_files/figure-html"

# How Quarto recognises a cell fence and an option line (see
# tests/support/lesson_checks.py, which reads the same cells with Pandoc).
_CELL_START = re.compile(r"^(\s*)(```+)\s*\{python\}\s*$")
_OPTION = re.compile(r"\s*#\s*\| ?(.*)")


@dataclass(frozen=True)
class FigureCell:
    """A cell of a lesson that draws a figure."""

    label: str
    status: str  # "" when the cell declares none
    alt: str  # "" when the cell declares none


@dataclass(frozen=True)
class Preview:
    """The preview of one lesson."""

    lesson: str  # the lesson id
    file: str  # relative to the root of the built site
    alt: str
    source: str  # the label of the figure cell, or "" for the fallback
    status: str

    @property
    def fallback(self) -> bool:
        return not self.source


def figure_cells(text: str) -> list[FigureCell]:
    """The cells of a lesson page that draw a figure (a ``fig-`` label), in
    page order, with the status and the alt text they declare."""
    cells = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        start = _CELL_START.match(lines[index])
        index += 1
        if start is None:
            continue
        options = []
        while index < len(lines) and (option := _OPTION.match(lines[index])):
            options.append(option.group(1))
            index += 1
        while index < len(lines) and not lines[index].strip().startswith(
            start.group(2)
        ):
            index += 1
        try:
            declared = yaml.safe_load("\n".join(options)) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(declared, dict):
            continue
        label = str(declared.get("label", ""))
        if label.startswith("fig-"):
            cells.append(
                FigureCell(
                    label,
                    str(declared.get("fig-status") or ""),
                    str(declared.get("fig-alt") or "").strip(),
                )
            )
    return cells


def problems(preview: str, text: str) -> list[str]:
    """What is wrong with the ``preview`` label of the lesson page ``text``: it
    names no figure cell of the page, or a cell without a status of the
    vocabulary or without alt text."""
    if not preview:
        return []
    named = [cell for cell in figure_cells(text) if cell.label == preview]
    if not named:
        return [
            f"'lesson.preview' names {preview!r}, which is not the label"
            " of a figure cell of the page"
        ]
    cell = named[0]
    found = []
    if cell.status not in FIGURE_STATUSES:
        found.append(
            f"the preview cell {cell.label!r} has no 'fig-status' of"
            f" {', '.join(FIGURE_STATUSES)}"
        )
    if not cell.alt:
        found.append(f"the preview cell {cell.label!r} has no 'fig-alt'")
    return found


def preview_of(lesson: Lesson, site: Path) -> Preview:
    """The preview of ``lesson`` in the website project ``site``. Raises
    ``ValueError`` when ``lesson.preview`` is not a valid figure cell."""
    found = problems(lesson.preview, (site / lesson.page).read_text(encoding="utf-8"))
    if found:
        raise ValueError(f"{lesson.page}: {found[0]}")
    if not lesson.preview:
        course = next(item for item in COURSES if item.id == lesson.course)
        alt = (
            f"Preview, conceptual: a card for a lesson of {course.title},"
            f" using {', '.join(lesson.methods)}."
        )
        return Preview(
            lesson.id, f"{PREVIEW_DIRECTORY}/{lesson.id}.svg", alt, "", "conceptual"
        )
    cell = next(
        item
        for item in figure_cells((site / lesson.page).read_text(encoding="utf-8"))
        if item.label == lesson.preview
    )
    alt = f"Preview, {cell.status}: {cell.alt}"
    return Preview(
        lesson.id, f"{PREVIEW_DIRECTORY}/{lesson.id}.webp", alt, cell.label, cell.status
    )


def scale(figure: bytes) -> bytes:
    """``figure`` (a PNG) scaled to fit ``WIDTH`` by ``HEIGHT`` and centred
    on a white canvas of exactly that size, as a lossless WebP without
    metadata."""
    with Image.open(io.BytesIO(figure)) as opened:
        picture = opened.convert("RGBA")
    ratio = min(WIDTH / picture.width, HEIGHT / picture.height)
    size = (max(1, round(picture.width * ratio)), max(1, round(picture.height * ratio)))
    picture = picture.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "white")
    canvas.paste(picture, ((WIDTH - size[0]) // 2, (HEIGHT - size[1]) // 2), picture)
    out = io.BytesIO()
    canvas.save(out, format="WEBP", **_WEBP)
    return out.getvalue()


def _wrap(title: str, width: int = 26) -> list[str]:
    lines: list[str] = []
    for word in title.split():
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += f" {word}"
        else:
            lines.append(word)
    return lines


def fallback(lesson: Lesson) -> str:
    """The conceptual preview of ``lesson``: a card in the colours of the
    site with the title of its course and one marker per method, drawn from
    the course and the methods alone."""
    courses = [course.id for course in COURSES]
    accent = FIGURE_COLOURS[courses.index(lesson.course) % len(FIGURE_COLOURS)]
    course = next(item for item in COURSES if item.id == lesson.course)
    label = STATUS_LABELS["conceptual"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}"'
        f' viewBox="0 0 {WIDTH} {HEIGHT}" role="img">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{PAGE["surface"]}"/>',
        f'<rect width="12" height="{HEIGHT}" fill="{accent}"/>',
    ]
    for number, line in enumerate(_wrap(course.title)):
        parts.append(
            f'<text x="32" y="{70 + 24 * number}" font-family="sans-serif"'
            f' font-size="18" fill="{PAGE["text"]}">{escape(line)}</text>'
        )
    for number, method in enumerate(lesson.methods):
        x = 40 + 28 * number
        parts.append(f'<circle cx="{x}" cy="150" r="8" fill="{accent}"/>')
        parts.append(
            f'<text x="{x}" y="176" font-family="sans-serif" font-size="9"'
            f' text-anchor="middle" fill="{PAGE["muted"]}">{escape(method[:6])}</text>'
        )
    parts.append(
        f'<rect x="{WIDTH - 108}" y="14" width="96" height="22" rx="4"'
        f' fill="{label.background}"/>'
        f'<text x="{WIDTH - 60}" y="29" font-family="sans-serif" font-size="12"'
        f' text-anchor="middle" fill="{label.foreground}">conceptual</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def figure_file(site_output: Path, lesson: Lesson, label: str) -> Path:
    """The figure that the executed cell ``label`` of ``lesson`` wrote into
    the built site ``site_output``."""
    directory = site_output / Path(lesson.page).parent / _FIGURES
    found = sorted(directory.glob(f"{label}-output-*.png"))
    if not found:
        raise FileNotFoundError(
            f"{lesson.page}: the build has no figure of the cell {label!r}"
            f" in {directory}; 'lesson.preview' must name a cell that draws one"
        )
    return found[0]


def write_previews(
    path: LearningPath, site: Path, output: Path, complete: bool = True
) -> list[Preview]:
    """Write the preview of every lesson into ``output / previews`` (the
    built site of the project ``site``) and return them in path order.

    A render of one page leaves the figures of the other lessons unbuilt;
    with ``complete`` false a lesson whose figure is not in the build is
    skipped instead of failing, and the next full render writes it."""
    (output / PREVIEW_DIRECTORY).mkdir(parents=True, exist_ok=True)
    written = []
    for lesson in path.lessons:
        preview = preview_of(lesson, site)
        target = output / preview.file
        if preview.fallback:
            target.write_text(fallback(lesson), encoding="utf-8")
        else:
            try:
                figure = figure_file(output, lesson, preview.source)
            except FileNotFoundError:
                if complete:
                    raise
                continue
            target.write_bytes(scale(figure.read_bytes()))
        written.append(preview)
    return written
