"""Which built pages differ from the base (ADR 014 decision 3).

A build records the checksum of every file of the site with the build commit
normalised: the commit is the one value every page that shows provenance
carries and that changes with every commit, so two builds of the same sources
at two commits would otherwise differ on every lesson page. A run with a base
compares its own record with the record of the base. The checks of one page
(accessibility, reading without scripts, widths, payload) run for the pages
whose normalised bytes differ, which includes every page of a lesson this run
executed. A page loads the files of the site that are not pages (the style
sheet, the scripts, the fonts, the images) without a checksum in its link, so a
difference in any of them, a file the base does not have, or a file the base
has and the site lacks, selects every page; it selects no lesson for execution,
which only the digests of the lessons decide (``pbc.authoring.selection``).

The checks of one page write what they ran for, and why, and the pages they
skipped, to ``CHECKED_FILE``: the record of the checked pages of the run, which
``summary`` turns into the lines the log of the run shows (#230, m3).

The record of a base is data; nothing in it is executed or read as
configuration, and a record that cannot be read selects every page.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from pbc.authoring import selection as selecting
from pbc.authoring.repository import REPOSITORY_ROOT, build_commit

PAGES = "pages.json"
BUILT_PAGES = "_pages.json"
FORMAT = 1
PLACEHOLDER = b"PBC-BUILD-COMMIT"
CHECKED_FILE = ".agents/verification/checked-pages.json"
CHECKED_FORMAT = 1
# Why a page is checked: its bytes differ from the base's, its lesson was
# executed, or only a file that is not a page differs.
DIFFERS = "differs"
EXECUTED = "executed"
ASSET = "asset"


def _checksum(data: bytes, commit: str | None) -> str:
    if commit:
        data = data.replace(commit.encode(), PLACEHOLDER)
    return hashlib.sha256(data).hexdigest()


def record(site_dir: Path, commit: str | None) -> dict:
    """The record of the built site in ``site_dir`` built from ``commit``."""
    files = {}
    for path in sorted(site_dir.rglob("*")):
        if path.is_file():
            files[path.relative_to(site_dir).as_posix()] = _checksum(
                path.read_bytes(), commit
            )
    return {"format": FORMAT, "files": files}


def read(path: Path) -> dict | None:
    """The record at ``path``, or None when it cannot be used."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        return None
    files = data.get("files")
    if not isinstance(files, dict):
        return None
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        return None
    return data


def pages(site_dir: Path) -> list[str]:
    """Every HTML page of the built site, relative to it."""
    return sorted(p.relative_to(site_dir).as_posix() for p in site_dir.rglob("*.html"))


def differing(site_dir: Path, base: dict, commit: str | None) -> list[str]:
    """The pages of ``site_dir`` that are not byte-identical to the page of the
    base, with the build commit normalised in both, and the pages the base does
    not have."""
    return _pages_differing(record(site_dir, commit)["files"], base["files"])


def differing_assets(site_dir: Path, base: dict, commit: str | None) -> list[str]:
    """The files of ``site_dir`` that are not pages and are not byte-identical
    to the file of the base, the ones the base does not have, and the ones the
    base has and ``site_dir`` lacks."""
    return _assets_differing(record(site_dir, commit)["files"], base["files"])


def _pages_differing(current: dict, known: dict) -> list[str]:
    return sorted(
        name
        for name in current
        if name.endswith(".html") and known.get(name) != current[name]
    )


def _assets_differing(current: dict, known: dict) -> list[str]:
    return sorted(
        name
        for name in set(current) | set(known)
        if not name.endswith(".html") and current.get(name) != known.get(name)
    )


def _lesson_page(lesson: str) -> str:
    """The built page of a lesson directory (``site/lessons/s/01-one``)."""
    return f"{Path(lesson).relative_to('site').as_posix()}/index.html"


def _every(site_dir: Path, reason: str) -> dict:
    return {
        "format": CHECKED_FORMAT,
        "mode": "every",
        "reason": reason,
        "assets": [],
        "pages": dict.fromkeys(pages(site_dir), "every"),
        "skipped": [],
    }


def checked(site_dir: Path, root: Path = REPOSITORY_ROOT) -> dict:
    """The pages the per-page checks run for, each with the reason.

    A run without a base, a full run, or a base without a usable record checks
    every page (mode ``every``). Otherwise (mode ``selective``) every page of
    a lesson this run executed, every page whose bytes differ from the base's,
    and, when a file that is not a page differs, every other page with the
    reason ``asset``. ``skipped`` lists the pages it does not check: those
    byte-identical to the page of the base, which the run that made the base
    checked.
    """
    selection = selecting.read(root)
    if selection is None:
        return _every(site_dir, "the run has no base")
    if selection.get("mode") != "selective":
        return _every(site_dir, f"a full run: {selection.get('reason', '')}")
    directory = selection.get("base_directory")
    if not isinstance(directory, str):
        return _every(site_dir, "the selection names no base directory")
    base = read(Path(directory) / PAGES)
    if base is None:
        return _every(site_dir, f"the base has no usable {PAGES}")
    current = record(site_dir, build_commit().sha)["files"]
    every = pages(site_dir)
    assets = _assets_differing(current, base["files"])
    executed = {_lesson_page(lesson) for lesson in selection["execute"]}
    chosen = dict.fromkeys(every if assets else [], ASSET)
    chosen |= dict.fromkeys(_pages_differing(current, base["files"]), DIFFERS)
    chosen |= dict.fromkeys(executed & set(every), EXECUTED)
    return {
        "format": CHECKED_FORMAT,
        "mode": "selective",
        "reason": "",
        "assets": assets,
        "pages": dict(sorted(chosen.items())),
        "skipped": [page for page in every if page not in chosen],
    }


def summary(data: dict) -> list[str]:
    """The lines that tell the log of a run which pages the checks of one page
    ran for, and why, and which they skipped, from a record of ``checked``."""
    checked_pages = data.get("pages", {})
    skipped = data.get("skipped", [])
    total = len(checked_pages) + len(skipped)
    if data.get("mode") == "every":
        lines = [
            f"Per-page checks: every page ({total}), {data.get('reason', '')}".rstrip()
        ]
    else:
        lines = [
            f"Per-page checks: {len(checked_pages)} of {total} pages checked,"
            f" {len(skipped)} skipped as byte-identical to the base"
        ]
        if data.get("assets"):
            lines.append(
                "A file that is not a page differs, which checks every page: "
                + ", ".join(data["assets"])
            )
    lines += [f"  checked ({why}): {page}" for page, why in checked_pages.items()]
    lines += [f"  skipped: {page}" for page in skipped]
    return lines


def selected(site_dir: Path, root: Path = REPOSITORY_ROOT) -> list[str] | None:
    """The pages the per-page checks run for, or None for every page."""
    data = checked(site_dir, root)
    return None if data["mode"] == "every" else list(data["pages"])


def write_checked(target: Path, data: dict) -> None:
    """Write the record of the checked pages to ``target``, whole or not at all."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.{os.getpid()}")
    partial.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    partial.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The record of a built site.")
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    data = record(arguments.site_dir, build_commit().sha)
    arguments.out.write_text(
        json.dumps(data, indent=0, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Recorded {len(data['files'])} files of the built site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
