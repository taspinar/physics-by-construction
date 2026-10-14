"""The parts of the lesson shards and their assembly (ADR 014 decision 11).

A lesson shard of a full run (``pbc.authoring.shards``) executes its share of the
lessons on its own machine, makes every comparison of bytes there, and hands
over a *part*: a directory with

* ``part.json``: the shard, its share of the lessons, the lessons it executed,
  the commit, and what the selection of the run was;
* ``digests.json``: the input digests of the tree the shard built;
* ``freeze/``: the store entries of the share (what it executed, and what it
  restored from the base for a lesson that was unchanged);
* ``site/``: the files of the lessons it executed, as it rendered and
  reproduced them (the page and its figures);
* ``files.sha256``: the checksum of every other file of the part.

The assembly retrieves the parts and treats them as data: it requires the parts
to be exactly the ones the lesson count derives, every file to be the recorded
one, every part to describe the tree it assembles, and the shares to cover every
lesson exactly once. It then builds the *union*, a directory shaped like a base
(``digests.json`` and ``freeze/``), and the selection of the run against it,
which must execute no lesson: the site is rendered from the store, and no
scientific cell of any lesson runs. After that render, ``compare`` requires every
file of a lesson the shards executed to be, in the assembled site, the file that
shard rendered and reproduced.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from pbc.authoring import selection as selecting
from pbc.authoring import shards as sharding
from pbc.authoring.digest import render
from pbc.authoring.repository import REPOSITORY_ROOT, build_commit

PART_FORMAT = 1
PART_FILE = "part.json"
LIST_FILE = "files.sha256"
DIGESTS = "digests.json"
STORE = "freeze"
SITE = "site"
PART_PREFIX = "lesson-shard-"
PART_DIRECTORY = ".agents/verification/part"
BUILT_SITE = "site/_site"
_LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")


class InvalidParts(Exception):
    """Parts that must not be assembled, or an assembly that is not the shards'."""


def part_name(number: int) -> str:
    return f"{PART_PREFIX}{number}"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(directory: Path) -> dict[str, Path]:
    """Every file below ``directory`` by relative path. A link, or anything
    that is neither a file nor a directory, is refused."""
    found = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise InvalidParts(f"{path.relative_to(directory)} is a symbolic link")
        if path.is_file():
            found[path.relative_to(directory).as_posix()] = path
        elif not path.is_dir():
            raise InvalidParts(f"{path.relative_to(directory)} is not a plain file")
    return found


def _lesson_key(path: Path, base: Path) -> str:
    """``site/lessons/s/01-one`` of ``base / lessons / s / 01-one``."""
    return "site/" + path.relative_to(base).as_posix()


def _lesson_dirs(base: Path) -> dict[str, Path]:
    lessons = base / "lessons"
    if not lessons.is_dir():
        return {}
    return {
        _lesson_key(path, base): path
        for path in sorted(lessons.glob("*/*"))
        if path.is_dir()
    }


def _relative(lesson: str) -> str:
    return Path(lesson).relative_to("site").as_posix()


# -- writing a part ------------------------------------------------------------


def write_part(root: Path, out: Path) -> dict:
    """Write the part of the lesson shard this run was (``shard.json``)."""
    shard = sharding.read(root=root)
    if shard is None:
        raise InvalidParts("this run is not a lesson shard: no shard file")
    selection = selecting.read(root)
    executed = sorted(sharding.executed(shard, selection) or [])
    site = root / "site"
    built = root / BUILT_SITE
    digests = site / "_digests.json"
    if not digests.is_file():
        raise InvalidParts(f"{digests} is missing: the shard did not build")
    if out.exists() and (
        not out.is_dir() or (any(out.iterdir()) and not (out / PART_FILE).is_file())
    ):
        raise InvalidParts(f"{out} exists and is not the part of an earlier run")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    shutil.copy2(digests, out / DIGESTS)
    for lesson in shard["lessons"]:
        source = site / "_freeze" / _relative(lesson)
        problem = selecting.entry_problem(source)
        if problem is not None:
            raise InvalidParts(f"{lesson}: the store holds no usable entry ({problem})")
        shutil.copytree(source, out / STORE / _relative(lesson), symlinks=False)
    for lesson in executed:
        source = built / _relative(lesson)
        files = _files(source) if source.is_dir() else {}
        if "index.html" not in files:
            raise InvalidParts(f"{lesson}: the shard rendered no page")
        shutil.copytree(source, out / SITE / _relative(lesson), symlinks=False)
    selected = None if selection is None else selection.get("mode")
    base = None if selection is None else selection.get("base")
    data = {
        "format": PART_FORMAT,
        "shard": shard["shard"],
        "of": shard["of"],
        "lessons": list(shard["lessons"]),
        "executed": executed,
        "commit": build_commit(root).sha,
        "selection": selected or "full",
        "base": None if base is None else base.get("id"),
    }
    (out / PART_FILE).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", "utf-8"
    )
    listing = [f"{_sha(path)}  {name}" for name, path in sorted(_files(out).items())]
    (out / LIST_FILE).write_text("\n".join(listing) + "\n", "utf-8")
    return data


# -- verifying the parts -------------------------------------------------------


def _recorded(directory: Path) -> dict[str, str]:
    path = directory / LIST_FILE
    if not path.is_file():
        raise InvalidParts(f"{directory.name}: {LIST_FILE} is missing")
    recorded: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        found = _LINE.match(line)
        if found is None:
            raise InvalidParts(f"{directory.name}: a malformed line in {LIST_FILE}")
        name = found.group(2)
        parts = Path(name).parts
        if Path(name).is_absolute() or ".." in parts or name in recorded:
            raise InvalidParts(f"{directory.name}: {name!r} is not a valid entry")
        recorded[name] = found.group(1)
    return recorded


def _check_files(directory: Path) -> None:
    """Every file is the recorded one: none missing, none extra, none changed."""
    recorded = _recorded(directory)
    found = _files(directory)
    found.pop(LIST_FILE, None)
    missing = sorted(set(recorded) - set(found))
    extra = sorted(set(found) - set(recorded))
    if missing:
        raise InvalidParts(
            f"{directory.name}: missing {missing[0]} (and {len(missing) - 1} more)"
        )
    if extra:
        raise InvalidParts(
            f"{directory.name}: unexpected {extra[0]} (and {len(extra) - 1} more)"
        )
    for name, path in found.items():
        if _sha(path) != recorded[name]:
            raise InvalidParts(
                f"{directory.name}: {name} is not the file that was recorded"
            )


def _read_part(directory: Path) -> dict:
    try:
        data = json.loads((directory / PART_FILE).read_text("utf-8"))
    except OSError, ValueError:
        raise InvalidParts(f"{directory.name}: {PART_FILE} is not readable") from None
    keys = {
        "format",
        "shard",
        "of",
        "lessons",
        "executed",
        "commit",
        "selection",
        "base",
    }
    if not isinstance(data, dict) or set(data) != keys or data["format"] != PART_FORMAT:
        raise InvalidParts(
            f"{directory.name}: {PART_FILE} is not a part of this format"
        )
    for key in ("lessons", "executed"):
        value = data[key]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise InvalidParts(f"{directory.name}: {key} is not a list of lessons")
    return data


def verify_parts(root: Path, parts: Path, *, sources: bool = True) -> list[dict]:
    """The parts in ``parts``, in shard order, after every requirement.

    ``sources`` also requires every part to be made from the sources of ``root``
    as they are now (the comparison after the render leaves it out: the render
    has run since, and only the integrity of the parts matters then).

    Raises InvalidParts naming the first thing that is wrong."""
    division = sharding.shares(sharding.lessons(root), sharding.size(root))
    expected = {part_name(number): number for number in range(1, len(division) + 1)}
    if not parts.is_dir() or parts.is_symlink():
        raise InvalidParts(f"{parts} is not a directory of parts")
    present = {path.name for path in parts.iterdir()}
    for name in sorted(present - set(expected)):
        raise InvalidParts(
            f"unexpected {name}: the lessons have {len(division)} shard(s)"
        )
    for name in sorted(set(expected) - present):
        raise InvalidParts(f"missing the part {name}: every shard hands over one")
    current = render(root) if sources else None
    commit = build_commit(root).sha
    result: list[dict] = []
    for name, number in expected.items():
        directory = parts / name
        if directory.is_symlink() or not directory.is_dir():
            raise InvalidParts(f"{name} is not a directory")
        _check_files(directory)
        data = _read_part(directory)
        share = division[number - 1]
        if (data["shard"], data["of"]) != (number, len(division)):
            raise InvalidParts(
                f"{name} is the part of the shard {data['shard']}/{data['of']}"
            )
        if data["lessons"] != share:
            raise InvalidParts(
                f"{name} holds another share of the lessons than the tree derives"
            )
        if not set(data["executed"]) <= set(share) or data["executed"] != sorted(
            set(data["executed"])
        ):
            raise InvalidParts(f"{name} executed lessons outside its share")
        if commit is not None and data["commit"] != commit:
            raise InvalidParts(
                f"{name} was made at the commit {data['commit']}, not {commit}"
            )
        if sources and (directory / DIGESTS).read_text("utf-8") != current:
            raise InvalidParts(
                f"{name} was made from other sources: its digests are not this tree's"
            )
        if data["selection"] == "full" and data["executed"] != share:
            raise InvalidParts(
                f"{name} made a full run but executed only part of its share"
            )
        found = _lesson_dirs(directory / STORE)
        if sorted(found) != share:
            raise InvalidParts(f"{name}: the store entries are not those of its share")
        for lesson, entry in found.items():
            problem = selecting.entry_problem(entry)
            if problem is not None:
                raise InvalidParts(f"{name}: {lesson}: {problem}")
        rendered = _lesson_dirs(directory / SITE)
        if sorted(rendered) != data["executed"]:
            raise InvalidParts(
                f"{name}: the rendered lessons are not the ones it executed"
            )
        for lesson, path in rendered.items():
            if not (path / "index.html").is_file():
                raise InvalidParts(f"{name}: {lesson} has no page")
        result.append(data)
    covered = [lesson for data in result for lesson in data["lessons"]]
    everything = sharding.lessons(root)
    if sorted(covered) != everything or len(set(covered)) != len(covered):
        raise InvalidParts("the parts do not cover every lesson exactly once")
    if len({(d["selection"], d["base"]) for d in result}) != 1:
        raise InvalidParts("the shards did not take the same base")
    return result


def build_union(root: Path, parts: Path, union: Path) -> dict:
    """Verify the parts and leave in ``union`` what a base holds: the digests
    and the store of every lesson. Writes the selection of the run against it,
    which must execute no lesson."""
    result = verify_parts(root, parts)
    shutil.rmtree(union, ignore_errors=True)
    union.mkdir(parents=True)
    shutil.copy2(parts / part_name(1) / DIGESTS, union / DIGESTS)
    for number in range(1, len(result) + 1):
        source = parts / part_name(number) / STORE
        for path in sorted(source.rglob("*")):
            target = union / STORE / path.relative_to(source)
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                if target.exists():
                    raise InvalidParts(f"{path.relative_to(source)} is in two parts")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    chosen = selecting.select(root, union)
    if chosen["mode"] != "selective" or chosen["execute"]:
        why = chosen["reason"] or f"{len(chosen['execute'])} lesson(s) would execute"
        raise InvalidParts(f"the assembly would execute a lesson: {why}")
    selecting.write(root, chosen)
    return chosen


# -- comparing the assembled site ------------------------------------------------


def compare(root: Path, parts: Path) -> int:
    """Require every file of every lesson the shards executed to be the same
    file in the assembled site. Returns the number of lessons compared."""
    result = verify_parts(root, parts, sources=False)
    built = root / BUILT_SITE
    problems = []
    count = 0
    for number, data in enumerate(result, start=1):
        for lesson in data["executed"]:
            count += 1
            shard_files = _files(parts / part_name(number) / SITE / _relative(lesson))
            directory = built / _relative(lesson)
            site_files = _files(directory) if directory.is_dir() else {}
            for name in sorted(set(shard_files) | set(site_files)):
                where = f"{_relative(lesson)}/{name}"
                if name not in site_files:
                    problems.append(f"{where}: the assembly did not render it")
                elif name not in shard_files:
                    problems.append(f"{where}: the shard did not render it")
                elif _sha(site_files[name]) != _sha(shard_files[name]):
                    problems.append(
                        f"{where}: differs from the file shard {number} rendered"
                    )
    if problems:
        raise InvalidParts(
            f"{len(problems)} file(s) of the assembled site are not the shards' "
            f"(first: {problems[0]})"
        )
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The parts of the lesson shards.")
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    part = sub.add_parser("part", help="write the part of this lesson shard")
    part.add_argument("--out", type=Path)
    verify = sub.add_parser("verify", help="verify the parts, build the union")
    verify.add_argument("--parts", type=Path, required=True)
    verify.add_argument("--union", type=Path, required=True)
    again = sub.add_parser("compare", help="compare the assembled site with the parts")
    again.add_argument("--parts", type=Path, required=True)
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    try:
        if arguments.command == "part":
            out = arguments.out or root / PART_DIRECTORY
            data = write_part(root, out)
            print(
                f"Part of the lesson shard {data['shard']}/{data['of']}: "
                f"{len(data['lessons'])} lesson(s) stored, "
                f"{len(data['executed'])} executed, in {out}."
            )
        elif arguments.command == "verify":
            chosen = build_union(root, arguments.parts, arguments.union)
            print(
                f"The parts cover {len(chosen['lessons'])} lesson(s) exactly once; "
                "the site is rendered from their store and executes no lesson."
            )
        else:
            count = compare(root, arguments.parts)
            print(
                f"{count} lesson(s): every file of the assembled site is the file "
                "its shard rendered and reproduced."
            )
    except (InvalidParts, sharding.ShardError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
