"""What the cards decide: the reference modules and the generated dataset lists.

Every list that a new dataset used to extend by hand is derived here from the
cards of ``data/registry/`` (Issue #456): the dictionary of reference modules
of ``python -m pbc.data.reference``, the cases of the tests that cover every
``go`` dataset, and the tables and conversion lists of ``docs/datasets/README.md``
and ``tools/datasets/README.md``. A new dataset adds its card and its own
files; it edits no shared list.

The generated parts of the two READMEs sit between the markers
``<!-- generated: <name> -->`` and ``<!-- end generated: <name> -->``, in
alphabetical order of the card id, so that two additions touch the same line
only when their ids are neighbours; such a conflict is resolved by running
the generator again::

    uv run python -m pbc.data.registry readme          # show what differs
    uv run python -m pbc.data.registry readme --write  # write the regions

``check_readmes`` is part of the dataset check (``python -m pbc.data.check``),
which fails when a region differs from what the cards give, and
``check_reference_modules`` fails it when a ``go`` card names no module that
imports and has ``make_figure``.
"""

import difflib
import importlib
import re
import sys
from pathlib import Path
from types import ModuleType

from pbc.data import REGISTRY_DIR, REPO_ROOT
from pbc.data.card import load_cards

REFERENCE_PACKAGE = "pbc.data.reference"
DOCS_README = Path("docs/datasets/README.md")
TOOLS_README = Path("tools/datasets/README.md")

# The 25 datasets of the survey of 2026-10-09 (Appendix A of
# docs/changes/physics-next-phase.md). A closed historical set: the survey
# is over, so no dataset is ever added here; a card that was surveyed and
# later passed its gate keeps its place in the survey table of the README.
SURVEYED = frozenset(
    (
        "aalborg-submerged-bar",
        "alma-dsharp-disks",
        "alma-hltau-verification",
        "cms-2012c-25-event-display",
        "cms-higgs-four-lepton-candidates",
        "electron-diffraction-crystals",
        "endgame-shocktube-schlieren",
        "euclid-q1-cutouts",
        "fraunhofer-microstructure-diffraction",
        "gaia-dr3-astrometry",
        "gw150914-strain",
        "haidinger-interference-rings",
        "lenslesspicam-measured-psf",
        "nist-experimental-ir-spectra",
        "npl-onwafer-sparameters",
        "onchip-ir-interferograms",
        "openpiv-sample-image-pairs",
        "piv-cylinder-wake",
        "rostock-piv-fluorescence",
        "sandia-qubit-gate-set-tomography",
        "sdo-aia-solar-uv",
        "sdo-hmi-magnetograms",
        "sheffield-piv-flume",
        "tess-exoplanet-light-curves",
        "ukaea-fair-mast-tokamak",
    )
)

_WRITE = "python -m pbc.data.registry readme --write"
_REGION = "<!-- generated: {name} -->"
_END = "<!-- end generated: {name} -->"


# The reference modules.


def decision_of(card: dict) -> str | None:
    return (card.get("decision") or {}).get("value")


def go_cards(registry: Path = REGISTRY_DIR) -> dict[str, dict]:
    """The cards with a ``go``, by id, in alphabetical order."""
    return {
        name: card
        for name, card in sorted(load_cards(registry).items())
        if decision_of(card) == "go"
    }


def reference_modules(cards: dict[str, dict] | None = None) -> dict[str, str]:
    """Dataset id to the name of its module under ``pbc.data.reference``.

    Only a ``go`` card with a text ``reference_module`` is listed; whether
    every ``go`` card has one is ``validate_card``'s finding.
    """
    cards = go_cards() if cards is None else cards
    return {
        name: card["reference_module"]
        for name, card in sorted(cards.items())
        if decision_of(card) == "go" and isinstance(card.get("reference_module"), str)
    }


def import_reference_module(card: dict) -> ModuleType:
    """The reference module a card names; raises what the import raises."""
    return importlib.import_module(f"{REFERENCE_PACKAGE}.{card['reference_module']}")


def check_reference_modules(cards: dict[str, dict]) -> list[str]:
    """Every ``go`` card whose module does not import or has no ``make_figure``.

    A ``go`` card without a text ``reference_module`` is reported by
    ``validate_card``, which the dataset check runs first; nothing is skipped.
    """
    out: list[str] = []
    for name, module in reference_modules(cards).items():
        qualified = f"{REFERENCE_PACKAGE}.{module}"
        try:
            imported = importlib.import_module(qualified)
        except Exception as error:  # any failure of the import counts
            out.append(
                f"{name}: reference module {qualified} does not import: "
                f"{type(error).__name__}: {error}"
            )
            continue
        if not callable(getattr(imported, "make_figure", None)):
            out.append(f"{name}: reference module {qualified} has no make_figure()")
    return out


# The generated regions of the READMEs.


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _decision_cell(card: dict) -> str:
    decision = card["decision"]
    inside = str(decision.get("date", ""))
    note = (card.get("listing") or {}).get("note")
    if note:
        inside = f"{inside}; {note}" if inside else note
    value = f"**{decision['value']}**"
    return f"{value} ({_cell(inside)})" if inside else value


def _dossier_cell(card: dict) -> str:
    dossier = card.get("dossier")
    if not dossier:
        return f"the card `data/registry/{card['id']}.yaml`"
    path = Path(dossier)
    if path.parent != DOCS_README.parent:
        return f"`{dossier}`"
    return f"[{path.stem}]({path.name})"


def _row(card: dict) -> str:
    listing = card.get("listing") or {}
    name = listing.get("name") or card.get("title", card["id"])
    kind = listing.get("kind", "")
    cells = (_cell(name), _cell(kind), _decision_cell(card), _dossier_cell(card))
    return "| " + " | ".join(cells) + " |"


_TABLE_HEAD = "| Dataset | Kind | Decision | Dossier |\n|---|---|---|---|"


def survey_table(cards: dict[str, dict]) -> str:
    """The surveyed datasets that were inspected, then the others as a count."""
    surveyed = [card for name, card in sorted(cards.items()) if name in SURVEYED]
    rows = [_row(card) for card in surveyed if decision_of(card) != "survey-only"]
    others = sum(decision_of(card) == "survey-only" for card in surveyed)
    rows.append(f"| {others} others | | survey-only | the cards in `data/registry/` |")
    return "\n".join([_TABLE_HEAD, *rows])


def later_table(cards: dict[str, dict]) -> str:
    """The cards added after the survey, in alphabetical order of the id."""
    rows = [_row(card) for name, card in sorted(cards.items()) if name not in SURVEYED]
    return "\n".join([_TABLE_HEAD, *rows])


def conversion_list(cards: dict[str, dict]) -> str:
    """One line per ``go`` dataset: its conversion scripts, or no conversion."""
    lines = []
    for name, card in sorted(cards.items()):
        if decision_of(card) != "go":
            continue
        label = (card.get("listing") or {}).get("name", name)
        scripts = [c["script"] for _, c in _conversions({name: card})]
        if scripts:
            what = "converted once by " + ", ".join(f"`{s}`" for s in scripts)
        else:
            what = f"no conversion; {card.get('format', '')}"
        lines.append(f"- {_cell(label)}: {_cell(what)}")
    return "\n".join(lines)


def _conversions(cards: dict[str, dict]) -> list[tuple[str, dict]]:
    return [
        (name, conversion)
        for name, card in sorted(cards.items())
        for conversion in sorted(
            (c for c in card.get("conversions") or [] if isinstance(c, dict)),
            key=lambda c: str(c.get("script")),
        )
    ]


def conversion_table(cards: dict[str, dict]) -> str:
    """The table of the tools README: one row per conversion, by dataset id."""
    head = "| Script | Dataset | Input (sha256) | Output (sha256) |\n|---|---|---|---|"
    rows = [
        f"| `{Path(c['script']).name}` | `{name}` | "
        f"{_cell(c['input'])} | {_cell(c['output'])} |"
        for name, c in _conversions(cards)
    ]
    return "\n".join([head, *rows])


def conversion_commands(cards: dict[str, dict]) -> str:
    """The command block of every conversion, with its note, by dataset id."""
    parts = []
    for name, c in _conversions(cards):
        lines = [f"**`{name}`, `{Path(c['script']).name}`.**"]
        if c.get("note"):
            lines[0] += " " + " ".join(str(c["note"]).split())
        lines += ["", "```", str(c["command"]).rstrip("\n"), "```"]
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def regions(cards: dict[str, dict]) -> dict[Path, dict[str, str]]:
    """The generated regions of each README, by relative path and region name."""
    return {
        DOCS_README: {
            "survey-table": survey_table(cards),
            "later-table": later_table(cards),
            "conversions": conversion_list(cards),
        },
        TOOLS_README: {
            "conversion-table": conversion_table(cards),
            "conversion-commands": conversion_commands(cards),
        },
    }


def _pattern(name: str) -> re.Pattern:
    start, end = re.escape(_REGION.format(name=name)), re.escape(_END.format(name=name))
    return re.compile(rf"^{start}\n(.*?)^{end}$", re.DOTALL | re.MULTILINE)


def region_text(text: str, name: str) -> str | None:
    """The body of the region ``name`` in ``text``, or None when it has no markers."""
    match = _pattern(name).search(text)
    return match.group(1).rstrip("\n") if match else None


def with_region(text: str, name: str, body: str) -> str:
    """``text`` with the region ``name`` replaced by ``body``; appended if absent."""
    block = f"{_REGION.format(name=name)}\n{body}\n{_END.format(name=name)}"
    if _pattern(name).search(text):
        return _pattern(name).sub(lambda _: block, text, count=1)
    return text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"


def check_readmes(root: Path = REPO_ROOT) -> list[str]:
    """Every region of the two READMEs that differs from what the cards give."""
    root = Path(root)
    out: list[str] = []
    for relative, bodies in regions(load_cards(root / "data" / "registry")).items():
        path = root / relative
        if not path.is_file():
            out.append(f"{relative}: missing; run {_WRITE}")
            continue
        text = path.read_text(encoding="utf-8")
        for name, body in bodies.items():
            current = region_text(text, name)
            if current is None:
                out.append(f"{relative}: no generated region {name!r}")
            elif current != body:
                diff = difflib.unified_diff(
                    current.splitlines(),
                    body.splitlines(),
                    "README",
                    "cards",
                    lineterm="",
                    n=0,
                )
                out.append(
                    f"{relative}: region {name!r} differs from the cards "
                    f"(run {_WRITE}):\n" + "\n".join(diff)
                )
    return out


def write_readmes(root: Path = REPO_ROOT) -> list[Path]:
    """Write the generated regions of the two READMEs; returns the files changed."""
    root = Path(root)
    changed = []
    for relative, bodies in regions(load_cards(root / "data" / "registry")).items():
        path = root / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        new = text
        for name, body in bodies.items():
            new = with_region(new, name, body)
        if new != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="utf-8")
            changed.append(path)
    return changed


def main(argv: list[str]) -> int:
    if argv[:1] != ["readme"] or argv[1:] not in ([], ["--write"]):
        print("usage: python -m pbc.data.registry readme [--write]", file=sys.stderr)
        return 2
    if argv[1:] == ["--write"]:
        for path in write_readmes():
            print(f"wrote {path.relative_to(REPO_ROOT)}")
        return 0
    problems = check_readmes()
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
