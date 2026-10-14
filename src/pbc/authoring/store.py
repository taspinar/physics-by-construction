"""The execution store of a site build (ADR 014 decisions 3, 6 and 9).

Quarto keeps the executed results of every page in ``site/_freeze/`` when the
build runs with the ``store`` profile (``site/_quarto-store.yml``). A page that
has an entry there is not executed again; a page without one is. The build
therefore decides what is executed by what it leaves in the store:

* a build without a base removes the store, so every page executes;
* a build with a base removes it and restores the entries of the lessons the
  selection says are unchanged (``pbc.authoring.selection``). Every changed
  lesson and every page that is not a lesson executes, and the store the build
  writes is the store of this run, to be uploaded as the next base.

The contents of a base are data. Nothing in it is executed, and nothing in it
is read as configuration: a restored entry is copied only if it is a plain
file below the directory of a lesson the selection names, and the build
reads it as it would read its own result.
"""

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

from pbc.authoring import selection as selecting
from pbc.authoring import shards as sharding
from pbc.authoring.digest import LESSONS, render
from pbc.authoring.repository import REPOSITORY_ROOT

STORE = "_freeze"
DIGESTS = "_digests.json"
TIMINGS = "_timings.json"
PROFILE = "store"
# The budget of one executed lesson page (docs/architecture.md, time budget).
LESSON_SECONDS = 30.0
_PROGRESS = re.compile(r"^(?:\x1b\[[0-9;]*m|\s)*\[\s*(\d+)/(\d+)\]\s+(\S+\.qmd)")


class InvalidStore(Exception):
    """An entry of a base that must not be restored."""


def _relative(lesson: str) -> Path:
    """The directory of a lesson relative to the site, from its repository path."""
    path = Path(lesson)
    if not lesson.startswith(f"{LESSONS}/") or ".." in path.parts:
        raise InvalidStore(f"{lesson!r} is not a lesson directory")
    return path.relative_to("site")


def restore(site: Path, base: Path, lessons: list[str]) -> list[str]:
    """Copy the store entries of ``lessons`` from the base into ``site``.

    Raises InvalidStore, before anything is copied, if an entry is not one that
    ``entry_problem`` accepts.
    """
    plan = []
    for lesson in lessons:
        relative = _relative(lesson)
        source = base / selecting.STORE / relative
        problem = selecting.entry_problem(source)
        if problem is not None:
            raise InvalidStore(f"{lesson}: {problem}")
        plan.append((source, site / STORE / relative))
    for source, target in plan:
        shutil.copytree(source, target, symlinks=False)
    return sorted(lessons)


def prepare(site: Path, selection: dict | None, shard: dict | None = None) -> list[str]:
    """Leave in ``site`` the store a build starts from: the entries of the
    unchanged lessons of a selective run, and nothing else. A lesson shard
    restores only the entries of its own share (ADR 014 decision 11)."""
    shutil.rmtree(site / STORE, ignore_errors=True)
    if selection is None or selection.get("mode") != "selective":
        return []
    directory = selection.get("base_directory")
    if not isinstance(directory, str):
        raise InvalidStore("the selection names no base directory")
    reuse = list(selection["reuse"])
    if shard is not None:
        mine = set(shard["lessons"])
        reuse = [lesson for lesson in reuse if lesson in mine]
    return restore(site, Path(directory), reuse)


def shards_executed(selection: dict, shard: dict | None) -> list[str]:
    """The lessons of the selection that this run executes."""
    chosen = sharding.executed(shard, selection)
    return list(selection["execute"]) if chosen is None else chosen


def _read_selection(path: Path | None) -> dict | None:
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    ok = isinstance(data, dict) and data.get("format") == selecting.SELECTION_FORMAT
    return data if ok else None


def write_digests(root: Path, out: Path) -> None:
    """Write the input digests of every lesson of the tree at ``root``."""
    out.write_text(render(root), encoding="utf-8")


def timings(lines: list[tuple[float, str]]) -> list[dict]:
    """The seconds each page took, from the progress lines of a Quarto render.

    A page is from its progress line to the next one (or to the end of the
    log). That includes the render after the execution, so it is an upper bound
    of the time the budget of one lesson page is about.
    """
    pages = []
    for time_, line in lines:
        found = _PROGRESS.match(line)
        if found:
            pages.append([time_, found.group(3)])
    end = lines[-1][0] if lines else 0.0
    result = []
    for index, (start, page) in enumerate(pages):
        stop = pages[index + 1][0] if index + 1 < len(pages) else end
        result.append({"page": page, "seconds": round(stop - start, 1)})
    return result


def _stamp(out: Path) -> int:
    """Copy standard input to standard output and write the page times."""
    lines = []
    for line in sys.stdin:
        sys.stdout.write(line)
        sys.stdout.flush()
        lines.append((time.monotonic(), line))
    pages = timings(lines)
    out.write_text(json.dumps(pages, indent=2) + "\n", encoding="utf-8")
    for late in over_budget(pages):
        print(
            f"Note: over the {LESSON_SECONDS:.0f} s page budget, {late}",
            file=sys.stderr,
        )
    return 0


def over_budget(pages: list[dict]) -> list[str]:
    """The lesson pages that took longer than the budget of one page."""
    return [
        f"{item['page']}: {item['seconds']} s"
        for item in pages
        if item["page"].startswith("lessons/") and item["seconds"] > LESSON_SECONDS
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The execution store of a build.")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="leave the store a build starts from")
    prep.add_argument("--site", type=Path, required=True)
    prep.add_argument(
        "--selection",
        type=Path,
        help="the selection file; without it the store starts empty",
    )
    prep.add_argument(
        "--shard-file",
        type=Path,
        help="the lesson shard of the run: only its share is restored",
    )
    digests = sub.add_parser("digests", help="write the digests of every lesson")
    digests.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    digests.add_argument("--out", type=Path, required=True)
    stamp = sub.add_parser("timings", help="time the pages of a Quarto render log")
    stamp.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.command == "prepare":
        selection = _read_selection(arguments.selection)
        shard = sharding.read(arguments.shard_file) if arguments.shard_file else None
        if arguments.shard_file and shard is None:
            print(
                f"Error: {arguments.shard_file} is not a shard file.", file=sys.stderr
            )
            return 1
        try:
            restored = prepare(arguments.site, selection, shard)
        except InvalidStore as error:
            print(
                f"Error: the base cannot be restored: {error}. Run"
                " ./scripts/verify.sh without --base, or remove"
                " .agents/verification/selection.json, to build every page.",
                file=sys.stderr,
            )
            return 1
        if selection is None or selection["mode"] != "selective":
            print("Store: empty; every page executes.")
        else:
            executing = len(shards_executed(selection, shard))
            print(
                f"Store: {len(restored)} lesson(s) restored from the base, "
                f"{executing} execute."
            )
        return 0
    if arguments.command == "digests":
        write_digests(arguments.root.resolve(), arguments.out)
        return 0
    return _stamp(arguments.out)


if __name__ == "__main__":
    sys.exit(main())
