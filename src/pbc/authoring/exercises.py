"""Lean exercises: stubs outside the checked library, solutions inside it.

A learner completes an exercise on their own machine: the stub in
``lean/Exercises/<Name>.lean`` states theorems whose proofs are ``sorry``. The
site never runs Lean for them (ADR 011). The checked solution of each stub is a
module of the library, ``PhysicsByConstruction.Exercises.<Name>``, which
``lake build`` compiles and the axiom audit of ``scripts/check-lean.sh`` finds
free of ``sorry``.

This module does two jobs:

* ``python -m pbc.authoring.exercises <lean project>`` is the pairing check that
  ``scripts/check-lean.sh`` runs: every stub has a solution module, both state
  the same theorems with the same statements, the stub still contains
  ``sorry``, and the solution contains none.
* ``lean_stub`` shows a stub on a page, marked "not verified", read from the
  file that the check compiled, with a Source link to its lines.
"""

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from pbc.authoring.context import current_page, marker
from pbc.authoring.excerpt import source_link_markdown
from pbc.authoring.lean import (
    LEAN_DIRECTORY,
    LEAN_PROJECT,
    anchored_lines,
    compiled_record,
)
from pbc.authoring.repository import BuildCommit

STUB_DIRECTORY = "Exercises"
SOLUTION_DIRECTORY = "PhysicsByConstruction/Exercises"
SOLUTION_PREFIX = "PhysicsByConstruction.Exercises"

_NAME = re.compile(r"[A-Z][A-Za-z0-9]*")
_THEOREM = re.compile(r"^theorem\s+([A-Za-z_][A-Za-z0-9_'.]*)", re.MULTILINE)
_SORRY = re.compile(r"\b(sorry|admit)\b")


def _without_comments(text: str) -> str:
    """Remove block comments (also doc comments) and line comments."""
    text = re.sub(r"/-.*?-/", " ", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", text)


def theorem_statements(text: str) -> dict[str, str]:
    """Return the statement of every top-level theorem of a Lean file.

    The statement is the text from the name to the ``:=`` that starts the
    proof, with comments removed and whitespace collapsed, so that two files
    agree when they state the same thing in differently laid out text.
    """
    code = _without_comments(text)
    matches = list(_THEOREM.finditer(code))
    statements: dict[str, str] = {}
    for match in matches:
        end = code.find(":=", match.end())
        if end < 0:
            raise ValueError(f"theorem {match.group(1)} has no ':='")
        statements[match.group(1)] = " ".join(code[match.start() : end].split())
    return statements


def uses_sorry(text: str) -> bool:
    """Whether the code of a Lean file contains ``sorry`` or ``admit``."""
    return bool(_SORRY.search(_without_comments(text)))


def stub_names(project: Path) -> list[str]:
    """The names of the exercise stubs of a Lean project, sorted."""
    directory = project / STUB_DIRECTORY
    if not directory.is_dir():
        return []
    return sorted(file.stem for file in directory.glob("*.lean"))


def check(project: Path) -> list[str]:
    """Return what is wrong with the exercises of a Lean project."""
    problems: list[str] = []
    names = stub_names(project)
    solutions = project / SOLUTION_DIRECTORY
    for directory in (project / STUB_DIRECTORY, solutions):
        if not directory.is_dir():
            continue
        for file in sorted(directory.rglob("*.lean")):
            if file.parent != directory:
                where = file.relative_to(project).as_posix()
                problems.append(
                    f"{where}: exercises live directly in {directory.name}, "
                    "not in subdirectories"
                )
    for name in names:
        stub_file = project / STUB_DIRECTORY / f"{name}.lean"
        where = f"{STUB_DIRECTORY}/{name}.lean"
        if not _NAME.fullmatch(name):
            problems.append(f"{where}: the file name is not a Lean module name")
            continue
        solution_file = solutions / f"{name}.lean"
        if not solution_file.is_file():
            expected = f"{SOLUTION_DIRECTORY}/{name}.lean"
            problems.append(f"{where}: no checked solution; expected {expected}")
            continue
        stub = stub_file.read_text(encoding="utf-8")
        solution = solution_file.read_text(encoding="utf-8")
        try:
            stub_statements = theorem_statements(stub)
            solution_statements = theorem_statements(solution)
        except ValueError as error:
            problems.append(f"{where}: {error}")
            continue
        if not stub_statements:
            problems.append(f"{where}: states no theorem")
        if not uses_sorry(stub):
            problems.append(f"{where}: contains no 'sorry', so it is not a stub")
        if uses_sorry(solution):
            problems.append(f"{SOLUTION_DIRECTORY}/{name}.lean: contains 'sorry'")
        for theorem, statement in stub_statements.items():
            other = solution_statements.get(theorem)
            if other is None:
                problems.append(f"{where}: the solution does not prove '{theorem}'")
            elif other != statement:
                problems.append(
                    f"{where}: the statement of '{theorem}' differs from the solution's"
                )
        for theorem in solution_statements.keys() - stub_statements.keys():
            problems.append(
                f"{SOLUTION_DIRECTORY}/{name}.lean: '{theorem}' has no stub in {where}"
            )
    for file in sorted(solutions.glob("*.lean")) if solutions.is_dir() else []:
        if file.stem not in names:
            solution = f"{SOLUTION_DIRECTORY}/{file.name}"
            problems.append(f"{solution}: no stub {STUB_DIRECTORY}/{file.name}")
    return problems


def stub_module(name: str) -> str:
    """The identifier of a stub in the build record."""
    return f"{STUB_DIRECTORY}.{name}"


def stub_path(name: str) -> str:
    """The file of a stub, relative to the repository root."""
    return f"{LEAN_DIRECTORY}/{STUB_DIRECTORY}/{name}.lean"


def solution_module(name: str) -> str:
    """The library module that holds the checked solution of a stub."""
    return f"{SOLUTION_PREFIX}.{name}"


@dataclass(frozen=True)
class LeanStub:
    """A theorem statement of an exercise stub, as shown on a page.

    As the result of a code cell it leaves a marker; the page the reader gets
    shows a listing in a "not verified" box, followed by the compact Source
    link to the lines of the stub at the commit of the run
    (``pbc.authoring.context``): the proof is ``sorry`` and nothing here has
    been proved.
    """

    name: str  # "<stub>:<anchor>"
    source: str
    path: str
    first_line: int
    last_line: int

    def payload(self) -> dict:
        """What the region is built from, apart from the commit."""
        return {
            "name": self.name,
            "source": self.source,
            "path": self.path,
            "first_line": self.first_line,
            "last_line": self.last_line,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> LeanStub:
        return cls(
            name=payload["name"],
            source=payload["source"],
            path=payload["path"],
            first_line=payload["first_line"],
            last_line=payload["last_line"],
        )

    def _repr_markdown_(self) -> str:
        return marker("lean-stub", current_page(), self.payload())

    def markdown(self, commit: BuildCommit, repository: str) -> str:
        """The content of the region, for the commit this was built with."""
        longest_run = max(
            (len(run) for run in re.findall(r"`+", self.source)), default=0
        )
        fence = "`" * max(3, longest_run + 1)
        link = source_link_markdown(
            self.name,
            self.path,
            (self.first_line, self.last_line),
            commit,
            repository,
        )
        return (
            # The region is built after the render, so it writes the label
            # that the page filter gives every "not verified" box.
            "::: {.not-verified .lean-stub role=note}\n"
            "::: {.not-verified-label}\n"
            "**Not verified.** The build of this site did not run or check the"
            " material in this box.\n"
            ":::\n\n"
            "::: {.excerpt}\n"
            f'{fence}{{.lean source="{self.name}"}}\n'
            f"{self.source.rstrip()}\n"
            f"{fence}\n\n"
            f"::: {{.excerpt-source}}\n{link}\n:::\n"
            ":::\n\n"
            f"The stub `{self.path}` contains `sorry`: it states the exercise and"
            " proves nothing. You complete it on your machine; the site does not"
            " run Lean for you.\n"
            ":::\n"
        )


def lean_stub(name: str, anchor: str, project: Path = LEAN_PROJECT) -> LeanStub:
    """Return the region ``anchor`` of the stub ``name`` for display.

    ``scripts/check-lean.sh`` must have compiled the stub in its present form.
    """
    record = compiled_record(solution_module(name), project)
    expected = record.get("exercises", {}).get(stub_module(name))
    file = project / STUB_DIRECTORY / f"{name}.lean"
    if expected is None:
        raise LookupError(f"the build record lists no exercise stub {name}")
    if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
        raise RuntimeError(
            f"{STUB_DIRECTORY}/{name}.lean changed after it was checked; run"
            " ./scripts/check-lean.sh again before building a page that shows it"
        )
    region, first_line = anchored_lines(file.read_text(encoding="utf-8"), anchor)
    if not region:
        raise ValueError(f"the region {anchor!r} of the stub {name} is empty")
    return LeanStub(
        name=f"{stub_module(name)}:{anchor}",
        source="\n".join(region),
        path=stub_path(name),
        first_line=first_line,
        last_line=first_line + len(region) - 1,
    )


def main(argv: list[str]) -> int:
    project = Path(argv[1]) if len(argv) > 1 else LEAN_PROJECT
    problems = check(project)
    for problem in problems:
        print(f"Error: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{len(stub_names(project))} exercise stub(s), each with a checked solution")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
