"""Display Lean proofs by reference, and state what compiled them.

A lesson in the formal proofs strand shows its theorems with ``lean_excerpt``
and states the build evidence with ``lean_evidence``. Both read the files of
``lean/`` when the page is built, so the page shows the proofs that
``lake build`` compiled (ADR 002).

``scripts/check-lean.sh`` compiles every module, audits it for ``sorry`` and
axioms, and then writes the build record read here. A page is not built from a
proof that was changed after that: the checksums of the record must match the
files.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from pbc.authoring.repository import (
    REPOSITORY_ROOT,
    BuildCommit,
    build_commit,
    repository_url,
)

LEAN_DIRECTORY = "lean"
LEAN_PROJECT = REPOSITORY_ROOT / LEAN_DIRECTORY

# Where scripts/check-lean.sh leaves the record of a passed check.
BUILD_RECORD = Path(".lake") / "pbc-build-record.json"

# The public Lean web editor. It loads a file from the address after "#url=".
WEB_EDITOR = "https://live.lean-lang.org/"
RAW_FILES = "https://raw.githubusercontent.com/"

_MODULE = re.compile(r"PhysicsByConstruction(\.[A-Z][A-Za-z0-9_]*)+")
_ANCHOR = re.compile(r"^\s*--\s*ANCHOR(_END)?:\s*(\S+)\s*$")


def module_path(module: str) -> str:
    """Return the file of a Lean module, relative to the repository root."""
    if not _MODULE.fullmatch(module):
        raise ValueError(
            f"{module!r} is not a module of the project; expected a name such as"
            " PhysicsByConstruction.Mechanics.Kinematics"
        )
    return f"{LEAN_DIRECTORY}/{module.replace('.', '/')}.lean"


def anchored_lines(text: str, anchor: str) -> tuple[list[str], int]:
    """Return the lines between ``-- ANCHOR: <anchor>`` and
    ``-- ANCHOR_END: <anchor>``, and the number of the first of them.

    The marker lines are comments of the Lean file and are not part of the
    result. Each marker must occur exactly once, start before end.
    """
    lines = text.splitlines()
    starts = []
    ends = []
    for number, line in enumerate(lines, start=1):
        marker = _ANCHOR.match(line)
        if marker and marker.group(2) == anchor:
            (ends if marker.group(1) else starts).append(number)
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError(
            f"expected one '-- ANCHOR: {anchor}' followed by one"
            f" '-- ANCHOR_END: {anchor}', found {len(starts)} and {len(ends)}"
        )
    return lines[starts[0] : ends[0] - 1], starts[0] + 1


def _record(project: Path) -> dict:
    file = project / BUILD_RECORD
    if not file.is_file():
        raise FileNotFoundError(
            f"{file} does not exist; run ./scripts/check-lean.sh, which compiles"
            " the Lean proofs and records the result, before building a page"
            " that shows them"
        )
    return json.loads(file.read_text(encoding="utf-8"))


def _checksum(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def compiled_record(module: str, project: Path = LEAN_PROJECT) -> dict:
    """Return the build record after checking that the file of ``module`` is
    the one that was compiled."""
    record = _record(project)
    relative = Path(module_path(module)).relative_to(LEAN_DIRECTORY)
    expected = record.get("modules", {}).get(module)
    if expected is None:
        raise LookupError(f"the build record lists no module {module}")
    if _checksum(project / relative) != expected:
        raise RuntimeError(
            f"{relative} changed after it was compiled; run"
            " ./scripts/check-lean.sh again before building a page that shows it"
        )
    return record


def editor_link(path: str, commit: BuildCommit, repository: str) -> str | None:
    """Return the address that opens the file ``path`` at ``commit`` in the
    Lean web editor, or None when the commit is unknown."""
    if commit.sha is None:
        return None
    prefix = "https://github.com/"
    if not repository.startswith(prefix):
        return None
    raw = f"{RAW_FILES}{repository[len(prefix) :]}/{commit.sha}/{path}"
    return f"{WEB_EDITOR}#url={quote(raw, safe='')}"


@dataclass(frozen=True)
class LeanExcerpt:
    """The text of one anchored region of a Lean file, with where it was read.

    As the result of a code cell it renders as a highlighted listing followed
    by the file and lines it came from.
    """

    name: str  # "<module>:<anchor>"
    source: str  # the text, exactly as in the file
    path: str  # file, relative to the repository root
    first_line: int
    last_line: int
    commit: BuildCommit
    repository: str

    def _repr_markdown_(self) -> str:
        longest_run = max(
            (len(run) for run in re.findall(r"`+", self.source)), default=0
        )
        fence = "`" * max(3, longest_run + 1)
        location = f"`{self.path}`, lines {self.first_line} to {self.last_line}"
        if self.commit.sha is not None:
            location = (
                f"[{location}]({self.repository}/blob/{self.commit.sha}/{self.path}"
                f"#L{self.first_line}-L{self.last_line})"
            )
        return (
            "::: {.excerpt .lean-excerpt}\n"
            f'{fence}{{.lean source="{self.name}"}}\n'
            f"{self.source.rstrip()}\n"
            f"{fence}\n\n"
            "::: {.excerpt-source}\n"
            f"{location}, read from the repository when this page was built.\n"
            ":::\n"
            ":::\n"
        )


def lean_excerpt(module: str, anchor: str, project: Path = LEAN_PROJECT) -> LeanExcerpt:
    """Return the region ``anchor`` of the Lean ``module`` for display.

    The region lies between ``-- ANCHOR: <anchor>`` and
    ``-- ANCHOR_END: <anchor>`` in the file. The module must be one that
    ``scripts/check-lean.sh`` compiled in its present form.
    """
    compiled_record(module, project)
    path = module_path(module)
    file = project / Path(path).relative_to(LEAN_DIRECTORY)
    region, first_line = anchored_lines(file.read_text(encoding="utf-8"), anchor)
    if not region:
        raise ValueError(f"the region {anchor!r} of {module} is empty")
    return LeanExcerpt(
        name=f"{module}:{anchor}",
        source="\n".join(region),
        path=path,
        first_line=first_line,
        last_line=first_line + len(region) - 1,
        commit=build_commit(),
        repository=repository_url(),
    )


@dataclass(frozen=True)
class LeanEvidence:
    """What compiled the proofs of a lesson, and where to read them.

    As the result of a code cell it renders as a short list: the commit, the
    versions, and for each module a link to the repository and one to the Lean
    web editor.
    """

    modules: tuple[str, ...]
    lean: str  # for example "4.34.1"
    mathlib: str  # the Mathlib tag
    mathlib_revision: str
    commit: BuildCommit
    repository: str

    def _links(self, module: str) -> str:
        path = module_path(module)
        sha = self.commit.sha
        if sha is None:
            return f"`{path}`"
        repository_link = f"[`{path}`]({self.repository}/blob/{sha}/{path})"
        editor = editor_link(path, self.commit, self.repository)
        if editor is None:
            return repository_link
        return f"{repository_link}, or [open it in the Lean web editor]({editor})"

    def _repr_markdown_(self) -> str:
        sha = self.commit.sha
        if sha is None:
            built_from = (
                "The commit is unknown: this page was not built from a Git checkout."
            )
        else:
            built_from = (
                f"Commit [`{sha}`]({self.repository}/tree/{sha}) of the"
                f" [repository]({self.repository})."
            )
            if self.commit.dirty:
                built_from += (
                    " **The checkout had uncommitted changes, so that commit"
                    " does not hold exactly the files this page was built"
                    " from.**"
                )
        lines = [
            "::: {.lean-evidence}",
            f"**Compiled with** Lean {self.lean} and Mathlib {self.mathlib}:"
            " `./scripts/check-lean.sh` found no `sorry` and no axiom declared"
            " by the project before this page was built.",
            "",
            f"{built_from}",
            "",
            '<details class="lean-evidence-details">',
            "<summary>What was checked, and where to read the proofs</summary>",
            "",
            "`./scripts/check-lean.sh` ran `lake build` on every module of the"
            " project and found no `sorry` and no axiom declared by the project"
            " before this page was built. CI runs the same check on every pull"
            " request and on `main`.",
            "",
            f"- Lean {self.lean}, from the toolchain pinned in `lean/lean-toolchain`.",
            f"- Mathlib {self.mathlib}, revision `{self.mathlib_revision}`.",
            *(f"- {self._links(module)}" for module in self.modules),
            "",
            "The file in the repository at that commit and the result of the CI"
            " run are authoritative. The Lean web editor is a convenience: it"
            " runs its own version of Mathlib, which can differ from the one"
            " above, so a proof that compiled here may report an error there.",
            "",
            "</details>",
            ":::",
            "",
        ]
        return "\n".join(lines)


def lean_evidence(*modules: str, project: Path = LEAN_PROJECT) -> LeanEvidence:
    """Return the build evidence for the Lean ``modules`` the page shows."""
    if not modules:
        raise ValueError("name at least one Lean module")
    record = None
    for module in modules:
        record = compiled_record(module, project)
    assert record is not None
    return LeanEvidence(
        modules=tuple(modules),
        lean=record["lean"]["version"],
        mathlib=record["mathlib"]["tag"],
        mathlib_revision=record["mathlib"]["rev"][:10],
        commit=build_commit(),
        repository=repository_url(),
    )
