"""The dataset check: cards, committed samples, caps, rights, checksums, tests.

``uv run python -m pbc.data.check`` is a required verification check. It reads
only the repository; it never contacts a portal (invariant I20).
"""

import hashlib
import sys
from pathlib import Path

from pbc.data import REPO_ROOT
from pbc.data.card import COMMITTABLE_LICENCES, load_card, validate_card

MAX_FILE = 2 * 1024 * 1024
MAX_DATASET = 8 * 1024 * 1024
MAX_ALL = 32 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _test_exists(root: Path, reference: str) -> bool:
    file, _, name = reference.partition("::")
    path = root / file
    return path.is_file() and f"def {name}(" in path.read_text(encoding="utf-8")


def check_sample_dir(root: Path, directory: Path, card: dict | None) -> list[str]:
    name = directory.name
    if card is None:
        return [f"data/samples/{name}: no card data/registry/{name}.yaml"]
    out = []
    rights = card.get("rights") or {}
    decision = (card.get("decision") or {}).get("value")
    if decision != "go":
        out.append(
            f"{name}: samples are committed only after a go (decision: {decision})"
        )
    if rights.get("licence") not in COMMITTABLE_LICENCES:
        out.append(
            f"{name}: licence {rights.get('licence')!r} does not permit committed "
            f"samples (allowed: {', '.join(COMMITTABLE_LICENCES)})"
        )
    redistribution = rights.get("redistribution_of_subsets") or {}
    if redistribution.get("answer") != "permitted":
        out.append(
            f"{name}: the card does not record redistribution of subsets as permitted"
        )
    declared = {
        s.get("path"): s for s in card.get("samples") or [] if isinstance(s, dict)
    }
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    total = 0
    for path in files:
        relative = path.relative_to(directory).as_posix()
        size = path.stat().st_size
        total += size
        if size > MAX_FILE:
            out.append(
                f"{name}/{relative}: {size} bytes exceeds the {MAX_FILE} cap per file"
            )
        sample = declared.get(relative)
        if sample is None:
            out.append(f"{name}/{relative}: not declared in the card's samples")
            continue
        if sha256(path) != sample.get("sha256"):
            out.append(f"{name}/{relative}: checksum differs from the card")
        if sample.get("bytes") != size:
            out.append(f"{name}/{relative}: size differs from the card")
        if not _test_exists(root, str(sample.get("test"))):
            out.append(
                f"{name}/{relative}: parsing test {sample.get('test')} not found"
            )
    for relative in sorted(
        set(declared) - {p.relative_to(directory).as_posix() for p in files}
    ):
        out.append(f"{name}/{relative}: declared in the card, not committed")
    if total > MAX_DATASET:
        out.append(f"{name}: {total} bytes exceeds the {MAX_DATASET} cap per dataset")
    return out


def check_repository(root: Path = REPO_ROOT) -> list[str]:
    """Every problem of the registry and the samples under ``root``."""
    root = Path(root)
    out: list[str] = []
    cards: dict[str, dict] = {}
    for path in sorted((root / "data" / "registry").glob("*.yaml")):
        try:
            card = load_card(path)
        except ValueError as error:
            out.append(str(error))
            continue
        cards[path.stem] = card
        out.extend(f"{path.name}: {p}" for p in validate_card(card, path.stem))
        dossier = card.get("dossier")
        if dossier and not (root / dossier).is_file():
            out.append(f"{path.name}: dossier {dossier} does not exist")
    total = 0
    samples = root / "data" / "samples"
    directories = (
        sorted(p for p in samples.iterdir() if p.is_dir()) if samples.is_dir() else []
    )
    for directory in directories:
        out.extend(check_sample_dir(root, directory, cards.get(directory.name)))
        total += sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
    for name, card in cards.items():
        if card.get("samples") and not (samples / name).is_dir():
            out.append(f"{name}: card declares samples, data/samples/{name} is missing")
    if total > MAX_ALL:
        out.append(
            f"data/samples: {total} bytes exceeds the {MAX_ALL} cap for all samples"
        )
    return out


def sample_total(root: Path = REPO_ROOT) -> int:
    samples = Path(root) / "data" / "samples"
    return sum(p.stat().st_size for p in samples.rglob("*") if p.is_file())


def main() -> int:
    problems = check_repository()
    for problem in problems:
        print(f"dataset check: {problem}", file=sys.stderr)
    if problems:
        return 1
    registry = REPO_ROOT / "data" / "registry"
    print(
        f"dataset check: {len(list(registry.glob('*.yaml')))} cards, "
        f"samples {sample_total()} bytes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
