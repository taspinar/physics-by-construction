"""The dataset card: schema, loading, and validation (ADR 007, decision 2).

A card is ``data/registry/<id>.yaml``. ``validate_card`` returns every problem
it finds as a message; an empty list means the card is valid. It never opens a
network connection.

``python -m pbc.data.card downloads <id>`` prints the downloads of a card as
tab-separated ``url algorithm digest filename`` lines, for
``scripts/fetch-data.sh``.
"""

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from pbc.data import REGISTRY_DIR

ARTIFACT_TYPES = (
    "raw-measured",
    "processed-measured",
    "calibrated-observation",
    "modelled-reference",
    "synthetic-test",
)
DECISIONS = ("go", "defer", "reject", "survey-only")
ANSWERS = ("permitted", "restricted", "unclear", "not-assessed")
RIGHTS_QUESTIONS = (
    "local_download",
    "redistribution_of_subsets",
    "publication_of_figures",
    "modification_and_attribution",
)
# Licences under which a sample may be committed, besides a recorded
# equivalent permission (ADR 007, decision 4).
COMMITTABLE_LICENCES = ("CC0-1.0", "CC-BY-4.0", "equivalent-permission")
CHECKSUM_ALGORITHMS = ("md5", "sha256")
# Required of a card whose dataset was inspected (anything but survey-only).
INSPECTED_FIELDS = (
    "calibration",
    "schema",
    "units",
    "cadence",
    "coordinates",
    "masks",
    "uncertainty",
    "estimates",
    "dossier",
)
_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_TEST = re.compile(r"^(?P<file>tests/[\w/.-]+\.py)::(?P<name>\w+)$")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _as_date(value: Any) -> bool:
    return isinstance(value, date)


def load_card(path: Path) -> dict:
    """Load a card; a file that is not a mapping is an error."""
    card = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(card, dict):
        raise ValueError(f"{path}: a card is a mapping")
    return card


def load_cards(registry: Path = REGISTRY_DIR) -> dict[str, dict]:
    return {p.stem: load_card(p) for p in sorted(Path(registry).glob("*.yaml"))}


def _require_text(card: dict, where: str, keys: tuple[str, ...], out: list[str]):
    section = card
    for part in where.split(".") if where else []:
        section = section.get(part) if isinstance(section, dict) else None
    if not isinstance(section, dict):
        out.append(f"{where or 'card'}: missing")
        return
    for key in keys:
        if not _text(section.get(key)):
            out.append(f"{where + '.' if where else ''}{key}: missing or empty")


def validate_card(card: dict, name: str | None = None) -> list[str]:
    """Problems of one card; ``name`` is the file stem that ``id`` must equal."""
    out: list[str] = []
    ident = card.get("id")
    if not (isinstance(ident, str) and _ID.match(ident)):
        out.append("id: lowercase words joined by '-'")
    elif name is not None and ident != name:
        out.append(f"id: {ident!r} differs from the file name {name!r}")
    for key in ("title", "format", "reader"):
        if not _text(card.get(key)):
            out.append(f"{key}: missing or empty")
    _require_text(card, "source", ("url", "creator", "version"), out)
    if not _as_date((card.get("source") or {}).get("accessed")):
        out.append("source.accessed: a date (YYYY-MM-DD)")
    _require_text(card, "size", ("description",), out)

    rights = card.get("rights")
    if not isinstance(rights, dict) or not _text(rights.get("licence")):
        out.append("rights.licence: missing or empty")
    else:
        for question in RIGHTS_QUESTIONS:
            answer = rights.get(question)
            if not isinstance(answer, dict):
                out.append(f"rights.{question}: missing")
                continue
            if answer.get("answer") not in ANSWERS:
                out.append(f"rights.{question}.answer: one of {', '.join(ANSWERS)}")
            if not _text(answer.get("source")):
                out.append(f"rights.{question}.source: where the answer was read")

    artifacts = card.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        out.append("artifacts: at least one")
    else:
        for k, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict) or not _text(artifact.get("name")):
                out.append(f"artifacts[{k}].name: missing")
            elif artifact.get("type") not in ARTIFACT_TYPES:
                out.append(f"artifacts[{k}].type: one of {', '.join(ARTIFACT_TYPES)}")
            elif not _text(artifact.get("description")):
                out.append(f"artifacts[{k}].description: missing")

    decision = card.get("decision")
    if not isinstance(decision, dict) or decision.get("value") not in DECISIONS:
        out.append(f"decision.value: one of {', '.join(DECISIONS)}")
        return out
    if not _as_date(decision.get("date")):
        out.append("decision.date: a date (YYYY-MM-DD)")
    reasons = decision.get("reasons")
    if not (isinstance(reasons, list) and reasons and all(map(_text, reasons))):
        out.append("decision.reasons: a list of reasons")
    value = decision["value"]
    if value == "survey-only":
        if not _text(decision.get("gate")):
            out.append("decision.gate: the gate this dataset would have to pass")
    else:
        for key in INSPECTED_FIELDS:
            if not card.get(key):
                out.append(f"{key}: required once the dataset was inspected")
        out.extend(_validate_checksums(card))
    out.extend(_validate_samples(card))
    return out


def _validate_checksums(card: dict) -> list[str]:
    out = []
    for k, entry in enumerate(card.get("downloads") or []):
        where = f"downloads[{k}]"
        if not isinstance(entry, dict):
            out.append(f"{where}: a mapping")
            continue
        if not _text(entry.get("url")) or not _text(entry.get("filename")):
            out.append(f"{where}: url and filename")
        if entry.get("algorithm") not in CHECKSUM_ALGORITHMS:
            out.append(f"{where}.algorithm: one of {', '.join(CHECKSUM_ALGORITHMS)}")
        if not re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{64}", str(entry.get("digest"))):
            out.append(f"{where}.digest: a hex digest")
        if not _text(entry.get("digest_source")):
            out.append(f"{where}.digest_source: who computed or published it")
    return out


def _validate_samples(card: dict) -> list[str]:
    out = []
    for k, sample in enumerate(card.get("samples") or []):
        where = f"samples[{k}]"
        if not isinstance(sample, dict):
            out.append(f"{where}: a mapping")
            continue
        if not _text(sample.get("path")):
            out.append(f"{where}.path: missing")
        if not re.fullmatch(r"[0-9a-f]{64}", str(sample.get("sha256"))):
            out.append(f"{where}.sha256: a sha256 hex digest")
        if not isinstance(sample.get("bytes"), int):
            out.append(f"{where}.bytes: an integer")
        if not _text(sample.get("derivation")):
            out.append(f"{where}.derivation: how the file derives from the source")
        if not _TEST.match(str(sample.get("test"))):
            out.append(f"{where}.test: 'tests/<file>.py::<test name>'")
    return out


def downloads(card: dict) -> list[tuple[str, str, str, str]]:
    return [
        (d["url"], d["algorithm"], d["digest"], d["filename"])
        for d in card.get("downloads") or []
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] != "downloads":
        print("usage: python -m pbc.data.card downloads <dataset>", file=sys.stderr)
        return 2
    registry = Path(os.environ.get("PBC_REGISTRY", REGISTRY_DIR))
    path = registry / f"{argv[1]}.yaml"
    if not path.is_file():
        print(f"no card for dataset {argv[1]!r} in {registry}", file=sys.stderr)
        return 1
    card = load_card(path)
    problems = validate_card(card, path.stem)
    if problems:
        print(f"card {path.name} is invalid: {problems[0]}", file=sys.stderr)
        return 1
    rows = downloads(card)
    if not rows:
        print(f"card {path.name} lists no download", file=sys.stderr)
        return 1
    for row in rows:
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
