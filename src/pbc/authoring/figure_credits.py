"""The caption of a figure that declares its provenance (Issue #524).

The post-render step ``site/figure-credits.py`` calls ``annotate`` on every
built page. A figure whose PNG carries the record of
``pbc.data.figure_provenance`` gets, from that record and its dataset card:
after the caption's status label, the statuses it combines ("with simulated
models"); at the end of the caption, the card's short credit and the full
provenance in a closed ``<details>``. The caption's status and dataset,
which the lesson filter renders from the cell's ``fig-status`` and
``fig-dataset``, must equal the record, and the record must equal the card:
anything else fails the build. A figure whose PNG carries no record, and a
page without one, are not changed.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from pbc.data import REGISTRY_DIR
from pbc.data.figure_provenance import (
    caption_html,
    card_of,
    read_metadata,
)

FIGURE = re.compile(r"<figure\b[^>]*>.*?</figure>", re.DOTALL)
IMAGE = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"')
STATUS = re.compile(r'<span class="figure-status"([^>]*)>[^<]*</span>')
ATTRIBUTE = re.compile(r'([\w-]+)="([^"]*)"')
CAPTION_END = "</figcaption>"
DONE = 'class="figure-credit"'


class InvalidFigure(ValueError):
    """A declared figure whose caption or card disagrees with its PNG."""


def record_of(figure: str, page_dir: Path) -> dict[str, str] | None:
    """The provenance record of the PNG of ``figure`` (the HTML of one
    ``<figure>`` of a page in ``page_dir``), or None."""
    image = IMAGE.search(figure)
    if image is None:
        return None
    source = unquote(image.group(1))
    if "://" in source or source.startswith("data:") or not source.endswith(".png"):
        return None
    path = page_dir / source
    if not path.is_file():
        return None
    record = read_metadata(path.read_bytes())
    return record if "pbc:schema" in record else None


def disagreements(figure: str, record: dict[str, str], card: dict) -> list[str]:
    """Where the caption of ``figure`` or the card ``card`` differs from the
    record of its PNG."""
    label = record["pbc:figure"]
    status = STATUS.search(figure)
    if status is None:
        return [f"{label}: the caption has no status label"]
    attributes = dict(ATTRIBUTE.findall(status.group(1)))
    out = []
    for attribute, key in (
        ("data-status", "pbc:status"),
        ("data-dataset", "pbc:dataset"),
        ("data-artifact", "pbc:artifact"),
    ):
        if attributes.get(attribute, "") != record.get(key, ""):
            out.append(
                f"{label}: the caption's {attribute} is"
                f" {attributes.get(attribute)!r}, the PNG declares"
                f" {record.get(key)!r}"
            )
    rights = card["rights"]
    for key, value in (
        ("pbc:credit", rights["figure_credit"]["short"]),
        ("pbc:attribution", " ".join(str(rights["attribution"]).split())),
        ("pbc:licence", str(rights["licence"])),
    ):
        if record.get(key) != value:
            out.append(f"{label}: the PNG's {key} is not the card's")
    if figure.count(CAPTION_END) != 1:
        out.append(f"{label}: the figure has no single caption")
    return out


def annotate(
    html: str, page_dir: Path, registry: Path = REGISTRY_DIR
) -> tuple[str, int]:
    """``html`` with the caption of every declared figure completed, and the
    number of figures completed. Idempotent."""
    count = 0

    def complete(match: re.Match) -> str:
        nonlocal count
        figure = match.group(0)
        record = record_of(figure, page_dir)
        if record is None or DONE in figure:
            return figure
        dataset = record.get("pbc:dataset", "")
        if not (registry / f"{dataset}.yaml").is_file():
            raise InvalidFigure(f"{record.get('pbc:figure')}: no card {dataset!r}")
        card = card_of(dataset, registry)
        problems = disagreements(figure, record, card)
        if problems:
            raise InvalidFigure("; ".join(problems))
        after, end = caption_html(record, card)
        status = STATUS.search(figure)
        figure = figure[: status.end()] + after + figure[status.end() :]
        figure = figure.replace(CAPTION_END, end + CAPTION_END)
        count += 1
        return figure

    return FIGURE.sub(complete, html), count
