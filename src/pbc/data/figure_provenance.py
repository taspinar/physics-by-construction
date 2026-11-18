"""The provenance of a figure of a dataset, off its chart area (F172, Issue
#524; rolled out by F173, Issue #531).

A figure that opts in declares its provenance in the lesson's experiment
(``Experiment.figure(label, draw, provenance=FigureProvenance(...))``); the
declaration and the dataset card are the one source of everything that says
what the figure is and whose data it shows:

- the PNG: ``pbc.experiment.encode`` writes the text chunks of ``metadata``
  (status, figure identity, dataset, licence, attribution, processing),
  deterministically and without a date, a software version, an author, or
  a copyright field, and paints one short line under the axes (broken
  within the figure's width where it is wider, Issue #546): the
  visualization credit, combined with the card's short credit where
  ``rights.figure_credit.visible`` is ``required`` (the terms ask for it)
  or ``chosen`` (the project shows it for clear attribution);
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
"with subtle branding", first for the three figures of the pilot (AST8,
MAT6, the RLC lab) and, by the owner's rollout decision of the same day,
for every figure F173 (Issue #531) declares: every figure of a dataset but
AI6's model-input picture, and every reference figure. Each shows the
small line
"Visualization: Physics by Construction" under the figure, outside the plot
area, so that a downloaded or shared image still shows where the
visualization comes from. It is not a per-figure choice: it goes with the
declaration, and a figure that declares nothing shows no line. Where the
card shows a dataset credit (``visible`` ``required`` or ``chosen``) the two
form one line ("Visualization: Physics by Construction · Data: ..."). No
box, no logo; the type size and grey of the figure credits. No wording may
claim ownership of external data (``ownership_problems``).

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
    from collections.abc import Callable

    from matplotlib.contour import ContourSet
    from matplotlib.figure import Figure

SCHEMA = "pbc-figure-provenance/1"
# The owner's choice on Issue #524 (2026-11-14): with subtle branding. It
# applies to the declared figures only, which since the rollout (F173,
# Issue #531) are every figure of a dataset but AI6's model input; an
# undeclared figure is encoded without it. A constant, not a setting.
VISUALIZATION_CREDIT = True
VISUALIZATION_PREFIX = "Visualization: Physics by Construction"
CREDIT_PREFIX = "Data: "
SHORT_CREDIT_LIMIT = 100
# required: the card's terms ask for the credit on the figure; chosen: the
# terms do not, and the project shows it for clear attribution (the owner's
# review of 2026-11-14 on Issue #524, for TESS); not-required: not painted.
VISIBILITY = ("required", "chosen", "not-required")
PAINTED = ("required", "chosen")
CREDIT_GID = "pbc-portable-credit"
# A role of a drawn artist besides the figure statuses: a residual combines
# the measurement and a model.
RESIDUAL = "residual"
# A fixed or published value drawn for comparison (a bound, a limit, a
# certified or published value, the moment a rule stops): neither the
# measurement nor a model, so no line style is required of it (Issue #531).
REFERENCE = "reference"
# The keys that hold a provider's attribution as its card gives it.
_NOTICES = ("pbc:attribution", "pbc:also-attribution")
_ROLE = "_pbc_role"
# Fields an image tool reads as ownership; never written.
FORBIDDEN_KEYS = ("Author", "Copyright", "Creation Time", "Software")
_MARK = re.compile(r"©|\(c\)\s")
_OWNERSHIP = re.compile(
    r"\bcopyright\s+(?:\(c\)\s+)?(?:\d{4}\s+)?(?:by\s+)?physics by construction"
    r"|\b(?:our|owned by|property of)\b",
    re.IGNORECASE,
)
_PROJECT = "Physics by Construction"
_STATEMENT = {
    "measured": "measurement",
    "calibrated": "calibrated measurement",
    "processed": "processed measurement",
    "simulated": "simulation",
}
# What a figure draws beside its own status, in words: the models of a
# measurement, or a further stage of it (a spectrum processed from a
# calibrated record, Issue #531).
_COMBINED = {
    "simulated": "simulated models",
    "processed": "processed data",
    "calibrated": "calibrated data",
    "measured": "measured data",
}


def _flat(text: object) -> str:
    return " ".join(str(text).split())


@dataclass(frozen=True)
class FigureProvenance:
    """What a figure of a dataset shows: its status, its dataset, the
    statuses of what it draws beside it, and what the lesson's code did.

    ``status`` is the status of the figure (``fig-status`` of the cell): a
    measurement's, or ``simulated`` for a modelled artifact of the card
    (``fig-artifact: modelled-reference``) or for a model of the dataset
    (``model_of``, the cell's ``fig-model-of``, Issue #531); ``combines``
    the statuses of the models drawn with it, for example
    ``("simulated",)`` for fitted curves; ``artifact`` the artifact type
    (``fig-artifact``) where the card needs one; ``processing`` what the
    lesson's code computed from the record, which is not part of it;
    ``also`` the further datasets whose data the figure draws (FL9's
    Strouhal figure, Issue #531), whose credits it carries as well.
    """

    status: str
    dataset: str
    processing: str
    combines: tuple[str, ...] = ()
    artifact: str | None = None
    model_of: bool = False
    also: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in (*MEASURED_STATUSES, "simulated"):
            raise ValueError(
                f"a declared figure shows a measurement or a simulation of a"
                f" dataset: {self.status!r} is neither"
            )
        if self.model_of and (self.status != "simulated" or self.artifact):
            raise ValueError("a model of a dataset is simulated and names no artifact")
        if self.status == "simulated" and not (self.model_of or self.artifact):
            raise ValueError(
                "a simulated figure of a dataset shows its modelled artifact"
                " (artifact=) or is a model of it (model_of=True)"
            )
        for other in self.combines:
            if other not in FIGURE_STATUSES or other in (self.status, "conceptual"):
                raise ValueError(f"cannot combine {other!r} with {self.status!r}")
        if len(set(self.combines)) != len(self.combines):
            raise ValueError("a combined status is named twice")
        if not _flat(self.processing):
            raise ValueError("the processing note is empty")
        if self.dataset in self.also or len(set(self.also)) != len(self.also):
            raise ValueError("a further dataset is named twice")

    def roles(self) -> set[str]:
        """The statuses the drawn artists of the figure carry."""
        return {self.status, *self.combines}

    def statement(self) -> str:
        """The status in words, with what the figure combines."""
        words = _STATEMENT[self.status]
        if self.model_of:
            words += " modelled on the dataset"
        if self.combines:
            words += " with " + " and ".join(_COMBINED[c] for c in self.combines)
        return words


def card_of(dataset: str, registry: Path = REGISTRY_DIR) -> dict:
    """The card of ``dataset``."""
    return load_card(registry / f"{dataset}.yaml")


def ownership_problems(text: str, *, notice: bool = False) -> list[str]:
    """Wording that claims ownership of external data, or names the project
    other than in the visualization credit.

    A copyright mark is ownership wording, except in ``notice``: the
    provider's own attribution, copied from its card, which keeps the
    provider's copyright notice as its licence asks (trackpy's CC BY 3.0
    sample, Issue #531); a claim for the project is refused there too.
    """
    out = []
    if _OWNERSHIP.search(text) or (not notice and _MARK.search(text)):
        out.append(f"ownership wording in {text!r}")
    rest = text.replace(VISUALIZATION_PREFIX, "")
    if _PROJECT.lower() in rest.lower():
        out.append(f"names {_PROJECT} other than as the visualization: {text!r}")
    return out


def credit_problems(card: dict) -> list[str]:
    """The per-card rights check of the figure credit, ``rights.figure_credit``.

    The short credit is one line that starts with "Data: ", within the
    limit, and claims no ownership; ``visible`` says whether it is painted
    on a portable figure because the card's terms require it (``required``),
    by the project's choice for clear attribution (``chosen``), or not at
    all (``not-required``), and ``source`` why. A CC BY
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
    for other in provenance.also:
        try:
            further = card_of(other)
        except (OSError, ValueError) as error:
            out.append(f"{other}: no card ({error})")
            continue
        if (further.get("decision") or {}).get("value") != "go":
            out.append(f"{other}: a figure needs a card with a go")
        out.extend(f"{other}: {p}" for p in credit_problems(further))
    if provenance.model_of:
        # A model of the dataset (fig-model-of): simulated, of no artifact.
        out.extend(f"{provenance.dataset}: {p}" for p in credit_problems(card))
        return out
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


def _painted_short(card: dict) -> str | None:
    credit = card["rights"]["figure_credit"]
    return credit["short"] if credit["visible"] in PAINTED else None


def visible_credit(
    card: dict,
    *,
    visualization: bool = VISUALIZATION_CREDIT,
    also: tuple[dict, ...] = (),
) -> str | None:
    """The line painted under a portable figure, or None.

    With the visualization credit (the default, the owner's choice), the
    line "Visualization: Physics by Construction", followed by " · " and
    the card's short credit where the card shows it (``visible``
    ``required`` or ``chosen``). Without it, that short credit, or nothing.
    The shown credits of the further cards ``also`` (``FigureProvenance.
    also``) follow on a second line, so the first keeps its width.
    """
    data = _painted_short(card)
    if visualization:
        line = (
            VISUALIZATION_PREFIX if data is None else f"{VISUALIZATION_PREFIX} · {data}"
        )
    else:
        line = data
    further = [short for c in also if (short := _painted_short(c)) is not None]
    if further:
        rest = " · ".join(further)
        return rest if line is None else f"{line}\n{rest}"
    return line


def also_cards(record_or_provenance: Any) -> tuple[dict, ...]:
    """The cards of the further datasets of a declaration or a PNG record."""
    if isinstance(record_or_provenance, FigureProvenance):
        names = record_or_provenance.also
    else:
        names = tuple(record_or_provenance.get("pbc:also", "").split())
    return tuple(card_of(name) for name in names)


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
    further = also_cards(provenance)
    painted = visible_credit(card, visualization=visualization, also=further)
    # A model of the dataset names it as such, not as its dataset: the
    # caption's fig-model-of (Issue #531); every other record is the pilot's.
    dataset = (
        {"pbc:dataset": "", "pbc:model-of": provenance.dataset}
        if provenance.model_of
        else {"pbc:dataset": provenance.dataset}
    )
    return {
        "Title": f"{identity} ({card['title']})",
        "Description": " ".join(
            [
                f"Status: {provenance.statement()}. {short}.",
                *(f"{c['rights']['figure_credit']['short']}." for c in further),
            ]
        ),
        "Source": source_link(card),
        "pbc:schema": SCHEMA,
        "pbc:figure": identity,
        "pbc:status": provenance.status,
        "pbc:combines": " ".join(provenance.combines),
        **dataset,
        "pbc:artifact": provenance.artifact or "",
        "pbc:licence": str(rights["licence"]),
        "pbc:credit": short,
        "pbc:visible-credit": painted or "",
        "pbc:attribution": _flat(rights["attribution"]),
        "pbc:processing": _flat(provenance.processing),
        # Only a figure of further datasets has these keys (Issue #531).
        **(
            {
                "pbc:also": " ".join(provenance.also),
                "pbc:also-credit": " | ".join(
                    c["rights"]["figure_credit"]["short"] for c in further
                ),
                "pbc:also-licence": " | ".join(
                    str(c["rights"]["licence"]) for c in further
                ),
                "pbc:also-attribution": " | ".join(
                    _flat(c["rights"]["attribution"]) for c in further
                ),
            }
            if further
            else {}
        ),
    }


def paint_credit(fig: Figure, text: str, *, dpi: float | None = None) -> None:
    """The credit under the figure, outside the chart area, within the
    figure's width (Issue #546).

    It sits below the figure's lower edge, so the axes keep their place and
    the tight bounding box of ``encode`` takes it in. It starts at the left
    edge of what the figure draws and breaks between words, or inside a
    word longer than a line, onto further lines wherever it would reach past
    the right edge: the tight bounding box keeps the width of the figure
    without the credit, so the page does not scale the chart and its labels
    down for it. ``dpi`` is the resolution the figure is saved at (text
    widths depend on it slightly); the figure's own when None. The text is
    ``text`` with line breaks added, nothing else.
    """
    original = fig.dpi
    if dpi is not None:
        fig.set_dpi(dpi)
    try:
        # Lays the figure out (a layout engine places the axes on draw) and
        # measures what it draws, in display units.
        renderer = fig.canvas.get_renderer()
        fig.draw_without_rendering()
        drawn = fig.get_tightbbox(renderer).transformed(fig.dpi_scale_trans)
        left = drawn.x0 / fig.bbox.width
        credit = fig.text(
            left,
            0.0,
            text,
            ha="left",
            va="top",
            fontsize=7,
            color="0.25",
            gid=CREDIT_GID,
        )

        def fits(line: str) -> bool:
            credit.set_text(line)
            return drawn.x0 + credit.get_window_extent(renderer).width <= drawn.x1

        credit.set_text(
            "\n".join(
                wrapped for line in text.split("\n") for wrapped in _wrap(line, fits)
            )
        )
    finally:
        fig.set_dpi(original)


def _wrap(line: str, fits: Callable[[str], bool]) -> list[str]:
    """``line`` broken greedily into lines that ``fits`` accepts: between
    words, and inside a word no line can hold."""
    out: list[str] = []
    current = ""
    for word in line.split(" "):
        candidate = f"{current} {word}" if current else word
        if fits(candidate):
            current = candidate
            continue
        if current:
            out.append(current)
        current = ""
        while word and not fits(word):
            # The longest head of the word that fits, at least one character.
            cut = max((k for k in range(1, len(word) + 1) if fits(word[:k])), default=1)
            out.append(word[:cut])
            word = word[cut:]
        current = word
    if current or not out:
        out.append(current)
    return out


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
        notice = key in _NOTICES and value == expected.get(key)
        out.extend(
            f"metadata {key!r}: {p}" for p in ownership_problems(value, notice=notice)
        )
    return out


def role(artist: Any, status: str) -> Any:
    """Mark a drawn artist (a line, a band, an errorbar container) with the
    status of what it shows, ``RESIDUAL``, or ``REFERENCE``; return it."""
    if status not in (*FIGURE_STATUSES, RESIDUAL, REFERENCE):
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


def _contour_style(
    k: int, contours: ContourSet, kind: str, measured: bool, modelled: bool
) -> list[str]:
    """The style rules of ``check_roles`` for the lines of a contour set."""
    styles = contours.get_linestyle()
    solid = [dashes is None or not any(dashes) for _, dashes in styles]
    if measured and kind == "simulated" and any(solid):
        return [f"panel {k + 1}: a model contour set has solid lines"]
    if modelled and kind in MEASURED_STATUSES and not all(solid):
        return [f"panel {k + 1}: a measured contour set is drawn as a model"]
    return []


def _drawn(ax: Any) -> list[Any]:
    """The artists a panel draws that can carry a role."""
    return [
        *ax.lines,
        *ax.collections,
        *ax.images,
        *ax.patches,
        *ax.containers,
    ]


def check_roles(fig: Figure, provenance: FigureProvenance) -> list[str]:
    """The legend semantics of a declared figure; an empty list means none.

    Every legend entry is an artist with a role, every role is one the
    declaration names (a residual only in a figure of a measurement),
    every declared role is drawn (by a legend entry or, in a panel without
    one, such as an image, by a drawn artist with the role, Issue #531),
    every entry of a panel is in its legend; in a panel that holds a
    measurement a model is never a solid line, and in a panel that holds a
    model a measurement is never a dashed or dotted one. A ``REFERENCE``
    (a bound, a limit, a published value) may be drawn in any figure and
    style. A contour set, which has no legend entry, always carries a role,
    and its lines follow the same style rules (review 02 M1).
    """
    from matplotlib.contour import ContourSet

    out: list[str] = []
    seen: set[str] = set()
    # A residual compares a measurement with a model: allowed beside the
    # model, or in a figure of the measurement that draws only the misfit
    # (EM9's wideband figure, PR #540).
    allowed = (
        provenance.roles()
        | (
            {RESIDUAL}
            if provenance.combines or provenance.status in MEASURED_STATUSES
            else set()
        )
        | {REFERENCE}
    )
    for k, ax in enumerate(fig.axes):
        # The style rules hold within a panel: a model beside a measurement
        # it is drawn with (Issue #531; the pilot's figures pass either way).
        here = {role_of(a) for a in _drawn(ax)}
        here |= {role_of(h) for h in ax.get_legend_handles_labels()[0]}
        measured = bool(here & set(MEASURED_STATUSES))
        modelled = "simulated" in here
        for artist in _drawn(ax):
            kind = role_of(artist)
            if kind is None:
                # A contour set draws data (a field, a model's levels), never
                # decoration: it carries a role (review 02 M1, Issue #531).
                if isinstance(artist, ContourSet):
                    out.append(f"panel {k + 1}: a contour set has no role")
                continue
            if isinstance(artist, ContourSet) and not artist.filled:
                # Contour lines have no legend entry: the style rules hold
                # for the lines drawn (review 02 M1).
                out.extend(_contour_style(k, artist, kind, measured, modelled))
            if kind not in allowed:
                out.append(
                    f"panel {k + 1}: an artist is {kind!r}; the figure declares"
                    f" {', '.join(sorted(allowed))}"
                )
            elif ax.get_legend() is None and kind != REFERENCE:
                # A panel without a legend (an image, one series) shows its
                # roles by its drawn artists; one with a legend by its entries.
                seen.add(kind)
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
            if kind != REFERENCE:
                seen.add(kind)
            style = _linestyle(handle)
            if measured and kind == "simulated" and style in ("-", "solid"):
                out.append(f"panel {k + 1}: the model {label!r} is a solid line")
            # Beside a model, a measurement is never dashed or dotted; a
            # figure of the measurement alone may tell its parts apart so.
            if (
                modelled
                and kind in MEASURED_STATUSES
                and style in ("--", ":", "-.", "dashed", "dotted")
            ):
                out.append(
                    f"panel {k + 1}: the measurement {label!r} is drawn as a model"
                )
    missing = provenance.roles() - seen
    if missing:
        out.append(
            "no legend entry (or, in a panel without a legend, drawn artist)"
            f" of the declared {', '.join(sorted(missing))}"
        )
    return out


def dataset_of(record: dict[str, str]) -> str:
    """The card a PNG's record names: its dataset, or what it models."""
    return record.get("pbc:model-of") or record.get("pbc:dataset", "")


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
        words = " and ".join(escape(_COMBINED.get(c, c)) for c in combines)
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
        items.insert(4, ("On the image", escape(_flat(painted))))
    further = also_cards(meta)
    for k, other in enumerate(further):
        # The further datasets the figure draws (Issue #531), after the
        # processing, each with its own attribution, licence, and source.
        link = source_link(other)
        items.insert(
            4 + k,
            (
                "Also from",
                f"{escape(_flat(other['rights']['attribution']))}"
                f" Licence: {escape(str(other['rights']['licence']))}."
                f' <a href="{escape(link, quote=True)}">{escape(link)}</a>',
            ),
        )
    rows = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items)
    short = escape(rights["figure_credit"]["short"])
    shorts = "".join(
        f' <span class="figure-credit-also">'
        f"{escape(other['rights']['figure_credit']['short'])}</span>"
        for other in further
    )
    end = (
        f' <span class="figure-credit">{short}</span>{shorts}'
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
