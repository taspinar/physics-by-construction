"""Lesson shards: the division of a full run over same-machine jobs (ADR 014
decision 11).

A *lesson shard* is a share of the lessons that one ``build`` job executes,
second-executes and reproduces on its own machine. The verification script
derives the shares from the lesson count and reads them from no file: ``S``,
the most lessons of one shard, is declared in ``scripts/verify.conf``, ``N`` is
the ceiling of the lesson count over ``S``, and lesson ``i`` of the sorted list
goes to shard ``i mod N + 1``. The shares are therefore stable for a lesson
list, differ in size by at most one lesson, never exceed ``S``, and none is
empty. This is not the division of the tests of the built site in
``tests/e2e/shards.json``; "shard" alone means a lesson shard here.

``./scripts/verify.sh --shard k/N`` writes the share it runs to ``SHARD_FILE``,
which the build, the second build and the reproduction read.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from pbc.authoring import selection as selecting
from pbc.authoring.digest import LESSONS, PAGE
from pbc.authoring.repository import REPOSITORY_ROOT

SHARD_FILE = ".agents/verification/shard.json"
SHARD_FORMAT = 1
CONFIG = "scripts/verify.conf"
SIZE_ENTRY = "shard-size"
_SIZE = re.compile(rf"^{SIZE_ENTRY}:[ \t]*(\d+)[ \t]*$", re.M)
_SPEC = re.compile(r"^(\d+)/(\d+)$")


class ShardError(Exception):
    """A division that does not exist."""


def size(root: Path = REPOSITORY_ROOT) -> int:
    """``S``, as ``scripts/verify.conf`` declares it."""
    try:
        text = (root / CONFIG).read_text(encoding="utf-8")
    except OSError as error:
        raise ShardError(f"cannot read {CONFIG}: {error}") from error
    found = _SIZE.findall(text)
    if len(found) != 1 or int(found[0]) < 1:
        raise ShardError(f"{CONFIG} must declare '{SIZE_ENTRY}: <lessons>' once")
    return int(found[0])


def lessons(root: Path = REPOSITORY_ROOT) -> list[str]:
    """The lessons of the tree, by repository path, in sorted order."""
    base = root / LESSONS
    return sorted(
        p.parent.relative_to(root).as_posix() for p in base.glob(f"*/*/{PAGE}")
    )


def count(lesson_count: int, limit: int) -> int:
    """``N``: the ceiling of the lesson count over ``S``."""
    if limit < 1:
        raise ShardError("the shard size must be at least one lesson")
    return -(-lesson_count // limit)


def shares(names: list[str], limit: int) -> list[list[str]]:
    """The lessons of every shard, in shard order, for the sorted ``names``."""
    ordered = sorted(names)
    total = count(len(ordered), limit)
    return [ordered[index::total] for index in range(total)]


def parse(spec: str, total: int) -> int:
    """The number ``k`` of ``k/N``, which must name the derived ``N``."""
    found = _SPEC.match(spec)
    if found is None:
        raise ShardError(f"expected <k>/<N>, got {spec!r}")
    number, of = int(found.group(1)), int(found.group(2))
    if of != total:
        raise ShardError(
            f"the lessons have {total} shard(s) at this size, not {of}: N is derived"
            " from the lesson count, never given"
        )
    if not 1 <= number <= of:
        raise ShardError(f"the shard {number} is not one of 1..{of}")
    return number


def share(root: Path, spec: str) -> tuple[int, int, list[str]]:
    """``(k, N, lessons)`` of the shard ``spec`` of the tree at ``root``."""
    division = shares(lessons(root), size(root))
    number = parse(spec, len(division))
    return number, len(division), division[number - 1]


def matrix(root: Path = REPOSITORY_ROOT) -> list[int]:
    """The shard numbers of the tree: what the workflow's matrix is made of."""
    return list(range(1, count(len(lessons(root)), size(root)) + 1))


def write(root: Path, spec: str) -> dict:
    number, total, names = share(root, spec)
    data = {
        "format": SHARD_FORMAT,
        "shard": number,
        "of": total,
        "lessons": names,
    }
    target = root / SHARD_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", "utf-8")
    return data


def read(path: Path | None = None, root: Path = REPOSITORY_ROOT) -> dict | None:
    """The shard file of a run, or None when the run is not a shard."""
    try:
        data = json.loads((path or root / SHARD_FILE).read_text("utf-8"))
    except OSError, ValueError:
        return None
    ok = isinstance(data, dict) and data.get("format") == SHARD_FORMAT
    return data if ok else None


def executed(shard: dict | None, selection: dict | None) -> list[str] | None:
    """The lessons a run executes: the share of the shard that the selection
    does not restore from a base. None means every lesson (a run without a
    shard and without a selective selection)."""
    chosen = None
    if selection is not None and selection.get("mode") == "selective":
        chosen = list(selection["execute"])
    if shard is None:
        return chosen
    mine = list(shard["lessons"])
    if chosen is None:
        return mine
    return [lesson for lesson in mine if lesson in set(chosen)]


def pages(names: list[str]) -> list[str]:
    """The pages of ``names`` relative to the site (``lessons/s/01/index.qmd``)."""
    return [f"{Path(name).relative_to('site').as_posix()}/{PAGE}" for name in names]


def render_list(site: Path, selection_file: Path | None, shard_file: Path) -> list[str]:
    """The pages a shard build renders, relative to ``site``."""
    shard = read(shard_file)
    if shard is None:
        raise ShardError(f"{shard_file} is not a shard file")
    chosen = _selection(selection_file) if selection_file else None
    return pages(executed(shard, chosen) or [])


def _selection(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text("utf-8"))
    except OSError, ValueError:
        return None
    ok = isinstance(data, dict) and data.get("format") == selecting.SELECTION_FORMAT
    return data if ok else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lesson shards of a full run.")
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("matrix", help="the shard numbers, as a JSON list")
    sub.add_parser("count", help="N, the number of shards")
    write_parser = sub.add_parser("write", help="write the shard file of k/N")
    write_parser.add_argument("spec")
    listing = sub.add_parser("render-list", help="the pages a shard build renders")
    listing.add_argument("--site", type=Path, required=True)
    listing.add_argument("--shard-file", type=Path, required=True)
    listing.add_argument("--selection", type=Path)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    try:
        if arguments.command == "matrix":
            print(json.dumps(matrix(root)))
        elif arguments.command == "count":
            print(count(len(lessons(root)), size(root)))
        elif arguments.command == "write":
            data = write(root, arguments.spec)
            print(
                f"Lesson shard {data['shard']} of {data['of']}: "
                f"{len(data['lessons'])} lesson(s)."
            )
        else:
            for page in render_list(
                arguments.site, arguments.selection, arguments.shard_file
            ):
                print(page)
    except ShardError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
