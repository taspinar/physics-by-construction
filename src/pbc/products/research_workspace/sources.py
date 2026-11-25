"""Source evidence: a published value, the register key of its source, the
words a person checked, and the place in the paper.

A published value enters the workspace only with a quotation that stands in
the register entry's checked ``statement`` (``site/references.yaml``); a
value whose words are not there is refused. The register's rule is a
person's check: the entry says who read the paper and when, and for the
reproduction track the owner confirms the quoted values on the Issue
before the part merges.
"""

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.data import REPO_ROOT

REGISTER = REPO_ROOT / "site" / "references.yaml"


@dataclass(frozen=True)
class Source:
    """One published value: its id, the quantity, the value with its
    uncertainty and unit as published, the confidence it is given at, the
    register key, the place in the paper, and the quoted words it rests on."""

    id: str
    quantity: str
    value: float | None
    uncertainty: float | None
    unit: str
    confidence: str
    register: str
    place: str
    quote: str


def _flat(text: str) -> str:
    return " ".join(str(text).split())


def load(path: Path) -> tuple[Source, ...]:
    """The sources of a project's ``sources.toml``."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        Source(
            id=key,
            quantity=entry["quantity"],
            value=entry.get("value"),
            uncertainty=entry.get("uncertainty"),
            unit=entry.get("unit", ""),
            confidence=entry.get("confidence", ""),
            register=entry["register"],
            place=entry["place"],
            quote=entry["quote"],
        )
        for key, entry in data["source"].items()
    )


def register_entries(path: Path = REGISTER) -> dict[str, Mapping]:
    entries = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["references"]
    return {entry["key"]: entry for entry in entries}


def problems(sources: Iterable[Source], register: Mapping[str, Mapping]) -> list[str]:
    """Every source whose register key is missing or whose quoted words are
    not in the entry's checked statement."""
    found = []
    for source in sources:
        entry = register.get(source.register)
        if entry is None:
            found.append(f"{source.id}: no register entry {source.register!r}")
            continue
        if not source.quote.strip():
            found.append(f"{source.id}: no quoted words")
        elif _flat(source.quote) not in _flat(entry["statement"]):
            found.append(
                f"{source.id}: the words {source.quote!r} are not in the checked"
                f" statement of {source.register}"
            )
        if not source.place.strip():
            found.append(f"{source.id}: the place in the paper is not named")
    return found


def by_id(sources: Iterable[Source]) -> dict[str, Source]:
    return {source.id: source for source in sources}
