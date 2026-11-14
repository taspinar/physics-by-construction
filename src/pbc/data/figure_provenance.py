"""The provenance of a measured figure, off its chart area (F172, Issue #524).

A figure that opts in declares its provenance in the lesson's experiment
(``Experiment.figure(label, draw, provenance=FigureProvenance(...))``); the
declaration and the dataset card are the one source of everything that says
what the figure is and whose data it shows:

- the PNG: ``pbc.experiment.encode`` writes the text chunks of ``metadata``
  (status, figure identity, dataset, licence, attribution, processing),
  deterministically and without a date, a software version, an author, or
  a copyright field, and paints one short line under the axes: the
  visualization credit, combined with the card's short credit where
  ``rights.figure_credit.visible`` is ``required``;
- the page: the post-render step ``site/figure-credits.py`` reads that
  metadata from the page's PNG, requires the caption's status and dataset to
  equal it, the painted line to be the one the card gives, and adds the
  combined statuses, the short credit, and the full provenance in a closed
  ``<details>`` (``caption_html``), from the card.

The status is no longer painted into a declared figure (``label_status``),
nor the long credit (``add_credit``): ``pbc.data.plotting.check_figure``
with ``declared=`` requires their absence, ``check_roles`` replaces the
status words of the legend entries by a role on each drawn artist, and
``check_png`` compares the PNG's metadata with the declaration and the card.
A figure that declares nothing is drawn and encoded exactly as before.

The visualization credit is the owner's choice of 2026-11-14 on Issue #524,
"with subtle branding": every declared figure shows the small line
"Visualization: Physics by Construction" under the figure, outside the plot
area, so that a downloaded or shared image still shows where the
visualization comes from; where the card's terms require a visible dataset
credit the two form one line ("Visualization: Physics by Construction ·
Data: ..."). No box, no logo; the type size and grey of the figure credits.
No wording may claim ownership of external data (``ownership_problems``).

Run as a program it writes the pilot's examples into a directory::

    uv run python -m pbc.data.figure_provenance examples out
"""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pbc.data import REGISTRY_DIR
from pbc.data.card import load_card
from pbc.data.status import (
    FIGURE_STATUSES,
    MEASURED_STATUSES,
    allowed_statuses,
    needs_artifact,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure

SCHEMA = "pbc-figure-provenance/1"
# The owner's choice on Issue #524 (2026-11-14): with subtle branding.
VISUALIZATION_CREDIT = True
VISUALIZATION_PREFIX = "Visualization: Physics by Construction"
CREDIT_PREFIX = "Data: "
SHORT_CREDIT_LIMIT = 100
VISIBILITY = ("required", "not-required")
CREDIT_GID = "pbc-portable-credit"
# A role of a drawn artist besides the figure statuses: a residual combines
# the measurement and a model.
RESIDUAL = "residual"
_ROLE = "_pbc_role"
# Fields an image tool reads as ownership; never written.
FORBIDDEN_KEYS = ("Author", "Copyright", "Creation Time", "Software")
_OWNERSHIP = re.compile(
    r"©|\(c\)\s"
    r"|\bcopyright\s+(?:\(c\)\s+)?(?:\d{4}\s+)?(?:by\s+)?physics by construction"
    r"|\b(?:our|owned by|property of)\b",
    re.IGNORECASE,
)
_PROJECT = "Physics by Construction"
_STATEMENT = {
    "measured": "measurement",
    "calibrated": "calibrated measurement",
    "processed": "processed measurement",
}


def _flat(text: object) -> str:
    return " ".join(str(text).split())


@dataclass(frozen=True)
class FigureProvenance:
    """What a measured figure shows: its status, its dataset, the statuses of
    what it draws beside the measurement, and what the lesson's code did.

    ``status`` is the status of the measurement (``fig-status`` of the
    cell); ``combines`` the statuses of the models drawn with it, for
    example ``("simulated",)`` for fitted curves; ``artifact`` the artifact
    type (``fig-artifact``) where the card needs one; ``processing`` what
    the lesson's code computed from the record, which is not part of it.
    """

    status: str
    dataset: str
    processing: str
    combines: tuple[str, ...] = ()
    artifact: str | None = None

    def __post_init__(self) -> None:
        if self.status not in MEASURED_STATUSES:
            raise ValueError(
                f"a declared figure shows a measurement: {self.status!r} is not"
                f" one of {MEASURED_STATUSES}"
            )
        for other in self.combines:
            if other not in FIGURE_STATUSES or other in (self.status, "conceptual"):
                raise ValueError(f"cannot combine {other!r} with {self.status!r}")
        if len(set(self.combines)) != len(self.combines):
            raise ValueError("a combined status is named twice")
        if not _flat(self.processing):
            raise ValueError("the processing note is empty")

    def roles(self) -> set[str]:
        """The statuses the drawn artists of the figure carry."""
        return {self.status, *self.combines}

    def statement(self) -> str:
        """The status in words, with what the figure combines."""
        words = _STATEMENT[self.status]
        if self.combines:
            words += " with " + " and ".join(f"{c} models" for c in self.combines)
        return words


def card_of(dataset: str, registry: Path = REGISTRY_DIR) -> dict:
    """The card of ``dataset``."""
    return load_card(registry / f"{dataset}.yaml")


def ownership_problems(text: str) -> list[str]:
    """Wording that claims ownership of external data, or names the project
    other than in the visualization credit."""
    out = []
    if _OWNERSHIP.search(text):
        out.append(f"ownership wording in {text!r}")
    rest = text.replace(VISUALIZATION_PREFIX, "")
    if _PROJECT.lower() in rest.lower():
        out.append(f"names {_PROJECT} other than as the visualization: {text!r}")
    return out


def credit_problems(card: dict) -> list[str]:
    """The per-card rights check of the figure credit, ``rights.figure_credit``.

    The short credit is one line that starts with "Data: ", within the
    limit, and claims no ownership; ``visible`` says whether the card's terms
    require it painted on a portable figure, and ``source`` why. A CC BY
    licence requires the credit visible, and names the licence in it; the
    card must permit the publication of figures and modification with
    attribution.
    """
    rights = card.get("rights") or {}
    credit = rights.get("figure_credit")
    if not isinstance(credit, dict):
        return ["rights.figure_credit: missing"]
    out: list[str] = []
    short = credit.get("short")
    if not isinstance(short, str) or not short.strip():
        return ["rights.figure_credit.short: missing or empty"]
    if short != _flat(short):
        out.append("rights.figure_credit.short: one line, single spaces")
    if not short.startswith(CREDIT_PREFIX):
        out.append(f"rights.figure_credit.short: starts with {CREDIT_PREFIX!r}")
    if len(short) > SHORT_CREDIT_LIMIT:
        out.append(
            f"rights.figure_credit.short: {len(short)} characters, at most"
            f" {SHORT_CREDIT_LIMIT}"
        )
    out.extend(f"rights.figure_credit.short: {p}" for p in ownership_problems(short))
    visible = credit.get("visible")
    if visible not in VISIBILITY:
        out.append(f"rights.figure_credit.visible: one of {', '.join(VISIBILITY)}")
    if not _flat(credit.get("source") or ""):
        out.append("rights.figure_credit.source: why the credit is or is not visible")
    licence = str(rights.get("licence", ""))
    if licence.upper().startswith("CC-BY"):
        if visible != "required":
            out.append(
                "rights.figure_credit.visible: a CC BY licence requires the"
                " attribution with the figure: 'required'"
            )
        if "CC BY" not in short:
            out.append("rights.figure_credit.short: a CC BY credit names the licence")
    for question in ("publication_of_figures", "modification_and_attribution"):
        if (rights.get(question) or {}).get("answer") != "permitted":
            out.append(f"rights.{question}: a portable figure needs 'permitted'")
    attribution = _flat(rights.get("attribution") or "")
    if not attribution:
        out.append("rights.attribution: the full attribution the figure carries")
    return out


def declaration_problems(provenance: FigureProvenance, card: dict) -> list[str]:
    """Whether ``card`` allows the declared figure: a go, the status, the
    artifact, and a valid figure credit."""
    out = []
    ident = card.get("id")
    if ident != provenance.dataset:
        out.append(
            f"the card is {ident!r}, the declaration names {provenance.dataset!r}"
        )
    if (card.get("decision") or {}).get("value") != "go":
        out.append(f"{provenance.dataset}: a figure needs a card with a go")
    if provenance.artifact is None and needs_artifact(card):
        out.append(f"{provenance.dataset}: the declaration names no artifact")
    allowed = allowed_statuses(card, provenance.artifact)
    if provenance.status not in allowed:
        out.append(
            f"{provenance.dataset}: status {provenance.status!r}; the card allows"
            f" {', '.join(sorted(allowed))}"
        )
    out.extend(f"{provenance.dataset}: {p}" for p in credit_problems(card))
    return out


def visible_credit(
    card: dict, *, visualization: bool = VISUALIZATION_CREDIT
) -> str | None:
    """The one line painted under a portable figure, or None.

    With the visualization credit (the default, the owner's choice), the
    line "Visualization: Physics by Construction", followed by " · " and
    the card's short credit where its terms require that credit visible.
    Without it, the card's short credit where its terms require it, or
    nothing.
    """
    credit = card["rights"]["figure_credit"]
    data = credit["short"] if credit["visible"] == "required" else None
    if visualization:
        return (
            VISUALIZATION_PREFIX if data is None else f"{VISUALIZATION_PREFIX} · {data}"
        )
    return data


def source_link(card: dict) -> str:
    """The DOI of the dataset as a URL, or its source URL."""
    source = card["source"]
    doi = source.get("doi")
    return f"https://doi.org/{doi}" if doi else str(source["url"])


def metadata(
    provenance: FigureProvenance,
    card: dict,
    identity: str,
    *,
    visualization: bool = VISUALIZATION_CREDIT,
) -> dict[str, str]:
    """The text chunks of the PNG of a declared figure, in a fixed order.

    ``identity`` is ``<experiment module>:<cell label>``. The standard keys
    ``Title``, ``Description``, and ``Source`` are for image tools; the keys
    ``pbc:...`` are the record a check reads back. Every value is a
    function of the declaration and the card only.
    """
    problems = declaration_problems(provenance, card)
    if problems:
        raise ValueError("; ".join(problems))
    rights = card["rights"]
    short = rights["figure_credit"]["short"]
    painted = visible_credit(card, visualization=visualization)
    return {
        "Title": f"{identity} ({card['title']})",
        "Description": f"Status: {provenance.statement()}. {short}.",
        "Source": source_link(card),
        "pbc:schema": SCHEMA,
        "pbc:figure": identity,
        "pbc:status": provenance.status,
        "pbc:combines": " ".join(provenance.combines),
        "pbc:dataset": provenance.dataset,
        "pbc:artifact": provenance.artifact or "",
        "pbc:licence": str(rights["licence"]),
        "pbc:credit": short,
        "pbc:visible-credit": painted or "",
        "pbc:attribution": _flat(rights["attribution"]),
        "pbc:processing": _flat(provenance.processing),
    }


def paint_credit(fig: Figure, text: str) -> None:
    """One line of credit under the figure, outside the chart area.

    It sits below the figure's lower edge, so the axes keep their place and
    the tight bounding box of ``encode`` takes it in.
    """
    fig.text(
        0.0,
        0.0,
        text,
        ha="left",
        va="top",
        fontsize=7,
        color="0.25",
        gid=CREDIT_GID,
    )


def read_metadata(png: bytes) -> dict[str, str]:
    """The text chunks (tEXt, zTXt, iTXt) of the PNG ``png``, in order."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    out: dict[str, str] = {}
    at = 8
    while at < len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        kind = png[at + 4 : at + 8]
        data = png[at + 8 : at + 8 + length]
        at += 12 + length
        if kind == b"tEXt":
            key, _, value = data.partition(b"\0")
            out[key.decode("latin-1")] = value.decode("latin-1")
        elif kind == b"zTXt":
            key, _, rest = data.partition(b"\0")
            out[key.decode("latin-1")] = zlib.decompress(rest[1:]).decode("latin-1")
        elif kind == b"iTXt":
            key, _, rest = data.partition(b"\0")
            compressed, rest = rest[0], rest[2:]
            _, _, rest = rest.partition(b"\0")  # language tag
            _, _, text = rest.partition(b"\0")  # translated keyword
            out[key.decode("latin-1")] = (
                zlib.decompress(text) if compressed else text
            ).decode("utf-8")
        elif kind == b"IEND":
            break
    return out


def check_png(
    png: bytes,
    provenance: FigureProvenance,
    card: dict,
    identity: str,
    *,
    visualization: bool = VISUALIZATION_CREDIT,
) -> list[str]:
    """Problems of the metadata of a declared figure's PNG; empty if none.

    The metadata must be exactly what the declaration and the card give,
    hold no field an image tool reads as ownership, and no ownership
    wording.
    """
    found = read_metadata(png)
    expected = metadata(provenance, card, identity, visualization=visualization)
    out = [
        f"metadata {key!r} is {found.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if found.get(key) != value
    ]
    out.extend(
        f"metadata {key!r} is not written by the declaration"
        for key in found
        if key not in expected
    )
    out.extend(f"metadata holds {key!r}" for key in FORBIDDEN_KEYS if key in found)
    for key, value in found.items():
        out.extend(f"metadata {key!r}: {p}" for p in ownership_problems(value))
    return out


def role(artist: Any, status: str) -> Any:
    """Mark a drawn artist (a line, a band, an errorbar container) with the
    status of what it shows, or ``RESIDUAL``; return it."""
    if status not in (*FIGURE_STATUSES, RESIDUAL):
        raise ValueError(f"unknown role {status!r}")
    setattr(artist, _ROLE, status)
    return artist


def role_of(artist: Any) -> str | None:
    """The role ``role`` gave ``artist``, or None."""
    return getattr(artist, _ROLE, None)


def _linestyle(handle: Any) -> str | None:
    lines = getattr(handle, "lines", None)
    if lines is not None:  # an errorbar container: its data line
        handle = lines[0]
    get = getattr(handle, "get_linestyle", None)
    if get is None:
        return None
    style = get()
    return style if isinstance(style, str) else None


def check_roles(fig: Figure, provenance: FigureProvenance) -> list[str]:
    """The legend semantics of a declared figure; an empty list means none.

    Every legend entry is an artist with a role, every role is one the
    declaration names (a residual only where a measurement meets a model),
    every declared role is drawn, every entry of a panel is in its legend,
    a model is never a solid line and a measurement never a dashed or
    dotted one.
    """
    out: list[str] = []
    seen: set[str] = set()
    allowed = provenance.roles() | ({RESIDUAL} if provenance.combines else set())
    for k, ax in enumerate(fig.axes):
        handles, labels = ax.get_legend_handles_labels()
        legend = ax.get_legend()
        shown = [] if legend is None else [t.get_text() for t in legend.get_texts()]
        if shown != labels:
            out.append(f"panel {k + 1}: the legend shows {shown}, the panel {labels}")
        for handle, label in zip(handles, labels, strict=True):
            kind = role_of(handle)
            if kind is None:
                out.append(f"panel {k + 1}: legend entry {label!r} has no role")
                continue
            if kind not in allowed:
                out.append(
                    f"panel {k + 1}: {label!r} is {kind!r}; the figure declares"
                    f" {', '.join(sorted(allowed))}"
                )
            seen.add(kind)
            style = _linestyle(handle)
            if kind == "simulated" and style in ("-", "solid"):
                out.append(f"panel {k + 1}: the model {label!r} is a solid line")
            # Beside a model, a measurement is never dashed or dotted; a
            # figure of the measurement alone may tell its parts apart so.
            if (
                provenance.combines
                and kind in MEASURED_STATUSES
                and style in ("--", ":", "-.", "dashed", "dotted")
            ):
                out.append(
                    f"panel {k + 1}: the measurement {label!r} is drawn as a model"
                )
    missing = provenance.roles() - seen
    if missing:
        out.append(f"no legend entry of the declared {', '.join(sorted(missing))}")
    return out


def caption_html(meta: dict[str, str], card: dict) -> tuple[str, str]:
    """The HTML the page adds to the caption of a declared figure: what goes
    after its status label, and what closes the caption.

    Both come from the card and the metadata of the PNG; the post-render
    step checks that the metadata is what the card gives before it calls
    this.
    """
    combines = meta.get("pbc:combines", "").split()
    after = ""
    if combines:
        words = " and ".join(f"{escape(c)} models" for c in combines)
        kinds = escape(" ".join(combines), quote=True)
        after = (
            f' <span class="figure-combines" data-combines="{kinds}">'
            f"with {words}</span>"
        )
    rights = card["rights"]
    link = source_link(card)
    items = [
        ("Attribution", escape(_flat(rights["attribution"]))),
        ("Licence", escape(str(rights["licence"]))),
        ("Source", f'<a href="{escape(link, quote=True)}">{escape(link)}</a>'),
        ("Processing", escape(meta["pbc:processing"])),
        (
            "This figure",
            f"<code>{escape(meta['pbc:figure'])}</code>, status"
            f" {escape(meta['pbc:status'])}; the PNG carries this record as"
            " metadata.",
        ),
    ]
    painted = meta.get("pbc:visible-credit", "")
    if painted:
        items.insert(4, ("On the image", escape(painted)))
    rows = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items)
    short = escape(rights["figure_credit"]["short"])
    end = (
        f' <span class="figure-credit">{short}</span>'
        '<details class="figure-provenance"><summary>Full provenance</summary>'
        f"<dl>{rows}</dl></details>"
    )
    return after, end


def examples(directory: Path, experiments=None) -> list[Path]:
    """Write every declared figure of ``experiments`` (the three of the
    pilot when None) as the page shows it, with the visualization credit,
    and without it into ``directory``, the evidence of the owner's choice;
    return the files."""
    from pbc.experiment import encode

    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for experiment in _pilot_experiments() if experiments is None else experiments:
        for label, provenance in experiment.provenance.items():
            card = card_of(provenance.dataset)
            draw = experiment.figures[label]
            identity = experiment.identity(label)
            for visualization in (True, False):
                png = encode(
                    draw,
                    metadata=metadata(
                        provenance, card, identity, visualization=visualization
                    ),
                    credit=visible_credit(card, visualization=visualization),
                )
                suffix = "" if visualization else "-without-visualization-credit"
                path = directory / f"{label}{suffix}.png"
                path.write_bytes(png)
                written.append(path)
    return written


def _pilot_experiments():
    from pbc.astrophysics.experiments import exoplanet_light_curves
    from pbc.electromagnetism.experiments import rlc_circuit_measurements
    from pbc.materials.experiments import stress_strain_measurements

    for module in (
        exoplanet_light_curves,
        stress_strain_measurements,
        rlc_circuit_measurements,
    ):
        yield module.run()


def main(argv: list[str] | None = None) -> None:
    import argparse

    import matplotlib

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["examples"])
    parser.add_argument("directory", type=Path)
    arguments = parser.parse_args(argv)
    matplotlib.use("agg", force=True)
    for path in examples(arguments.directory):
        print(path)


if __name__ == "__main__":
    main()
