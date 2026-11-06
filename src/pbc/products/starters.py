"""The starter checks of ADR 022 decision 5 (``docs/products.md``, "The
starter and its pin").

Every ``products/<product>/starter/`` is checked twice:

- **current tree**: its tests run with the repository's working tree first
  on the path, so that a change which breaks what the starter imports fails
  its pull request;
- **at its pin**: the pin is the ``rev`` of ``pbc`` in the starter's
  ``pyproject.toml``, the full hash of a commit. The check takes that
  commit's ``src/`` from the repository's own history (``git archive``; no
  fetch, so a commit that is not in the history fails), puts it first on the
  path, confirms that ``pbc`` is imported from it, and runs the starter's
  tests, so that what a learner installs is what was verified. The commit
  must be in the history of ``HEAD``. A pin that is ``pending`` (a new
  starter before its first pin bump) is skipped, and the skip is named in
  the output.

The pinned commit is run with the dependencies of the current environment;
a pin bump that also changes a dependency is checked by the learner's own
installation, which resolves the pinned commit's lock.

    uv run --locked python -m pbc.products.starters [--root DIR]

It never starts a product, contacts a model, an instrument, or the network.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

PENDING = "pending"
_HASH = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class Outcome:
    starter: str
    check: str  # current tree or at pin
    status: str  # passed, failed, skipped
    detail: str

    def __str__(self) -> str:
        return f"{self.starter}, {self.check}: {self.status}. {self.detail}"


def find_starters(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.glob("products/*/starter/pyproject.toml"))


def pin_of(starter: Path) -> str:
    """The pin: the ``rev`` of ``pbc`` under ``[tool.uv.sources]``."""
    data = tomllib.loads((starter / "pyproject.toml").read_text(encoding="utf-8"))
    source = data.get("tool", {}).get("uv", {}).get("sources", {}).get("pbc")
    if not isinstance(source, dict) or not isinstance(source.get("rev"), str):
        raise ValueError(
            f"{starter}/pyproject.toml declares no pin: [tool.uv.sources] pbc ="
            ' { git = "...", rev = "<commit>" }'
        )
    return source["rev"]


def _pytest(starter: Path, path: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(starter / "pyproject.toml"),
            "--rootdir",
            str(starter),
            "-p",
            "no:cacheprovider",
            "-q",
            str(starter / "tests"),
        ],
        cwd=starter,
        env=_environment(path),
        capture_output=True,
        text=True,
        check=False,
    )


def _environment(path: list[Path]) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(str(p) for p in path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _tail(result: subprocess.CompletedProcess) -> str:
    lines = (result.stdout + result.stderr).strip().splitlines()
    return " | ".join(lines[-3:]) if lines else "(no output)"


def check_current(root: Path, starter: Path) -> Outcome:
    name = starter.relative_to(root).as_posix()
    result = _pytest(starter, [root / "src", starter])
    status = "passed" if result.returncode == 0 else "failed"
    return Outcome(name, "current tree", status, _tail(result))


def _git(root: Path, *arguments: str, data: bool = False):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        check=False,
        text=not data,
    )


def check_pin(root: Path, starter: Path) -> Outcome:
    name = starter.relative_to(root).as_posix()

    def failed(detail: str) -> Outcome:
        return Outcome(name, "at pin", "failed", detail)

    try:
        pin = pin_of(starter)
    except ValueError as reason:
        return failed(str(reason))
    if pin == PENDING:
        return Outcome(
            name,
            "at pin",
            "skipped",
            "the pin is `pending` (a new starter, ADR 022 decision 5); the first"
            " pin bump after its feature merged sets it, and this check then runs",
        )
    if not _HASH.fullmatch(pin):
        return failed(f"the pin {pin!r} is not the full hash of a commit")
    if _git(root, "cat-file", "-e", f"{pin}^{{commit}}").returncode != 0:
        return failed(
            f"{pin} is not a commit in the repository's history (no fetch is made;"
            " CI checks out the full history)"
        )
    if _git(root, "merge-base", "--is-ancestor", pin, "HEAD").returncode != 0:
        return failed(f"{pin} is not in the history of HEAD")
    archive = _git(root, "archive", "--format=tar", pin, "src", data=True)
    if archive.returncode != 0:
        return failed(f"cannot take src/ from {pin}: {archive.stderr.decode()}")
    with tempfile.TemporaryDirectory(prefix="pbc-pin-") as directory:
        installed = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(installed, filter="data")
        source = installed / "src"
        if not (source / "pbc" / "__init__.py").is_file():
            return failed(f"{pin} has no package src/pbc")
        where = subprocess.run(
            [sys.executable, "-c", "import pbc; print(pbc.__file__)"],
            env=_environment([source, starter]),
            capture_output=True,
            text=True,
            check=False,
        )
        imported = Path(where.stdout.strip() or "?").resolve()
        if source.resolve() not in imported.parents:
            return failed(f"pbc was imported from {imported}, not from the pin")
        result = _pytest(starter, [source, starter])
    status = "passed" if result.returncode == 0 else "failed"
    return Outcome(name, "at pin", status, f"pbc at {pin}: {_tail(result)}")


def check_all(root: Path) -> list[Outcome]:
    outcomes = []
    for starter in find_starters(root):
        outcomes.append(check_current(root, starter))
        outcomes.append(check_pin(root, starter))
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pbc.products.starters")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    root = parser.parse_args(argv).root.resolve()
    outcomes = check_all(root)
    if not outcomes:
        print("no starter under products/*/starter/")
    for outcome in outcomes:
        print(outcome)
    return 1 if any(o.status == "failed" for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
