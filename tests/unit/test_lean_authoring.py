"""The Lean display form: excerpts by reference and the build evidence."""

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest

from pbc.authoring import BuildCommit, lean_evidence, lean_excerpt
from pbc.authoring.lean import (
    BUILD_RECORD,
    anchored_lines,
    editor_link,
    module_path,
)
from pbc.authoring.repository import REPOSITORY_ROOT

MODULE = "PhysicsByConstruction.Mechanics.Sample"
SOURCE = """\
import Mathlib.Basic.Real.Basic

-- ANCHOR: first
theorem first : (1 : Nat) = 1 := rfl
-- ANCHOR_END: first

-- ANCHOR: second
/-- Two lines,
with a doc comment. -/
theorem second : (2 : Nat) = 2 := rfl
-- ANCHOR_END: second
"""


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A Lean project of one module that was compiled, with its record."""
    file = tmp_path / "PhysicsByConstruction" / "Mechanics" / "Sample.lean"
    file.parent.mkdir(parents=True)
    file.write_text(SOURCE)
    (tmp_path / BUILD_RECORD).parent.mkdir()
    (tmp_path / BUILD_RECORD).write_text(
        json.dumps(
            {
                "toolchain": "leanprover/lean4:v4.99.0",
                "lean": {"version": "4.99.0", "commit": "f" * 40},
                "mathlib": {
                    "tag": "v4.99.0",
                    "rev": "0123456789abcdef" * 2 + "01234567",
                },
                "modules": {MODULE: checksum(SOURCE)},
            }
        )
    )
    return tmp_path


# --- anchors ------------------------------------------------------------------


def test_region_is_the_text_between_the_anchors_without_them():
    lines, first = anchored_lines(SOURCE, "second")

    assert lines[0] == "/-- Two lines,"
    assert lines[-1] == "theorem second : (2 : Nat) = 2 := rfl"
    assert SOURCE.splitlines()[first - 1] == lines[0]
    assert all("ANCHOR" not in line for line in lines)


@pytest.mark.parametrize(
    "text",
    [
        "theorem a : True := trivial\n",
        "-- ANCHOR: a\ntheorem a : True := trivial\n",
        "-- ANCHOR_END: a\n-- ANCHOR: a\n",
        "-- ANCHOR: a\n-- ANCHOR: a\n-- ANCHOR_END: a\n",
    ],
    ids=["none", "no-end", "end-first", "twice"],
)
def test_region_needs_exactly_one_start_before_one_end(text: str):
    with pytest.raises(ValueError, match="ANCHOR"):
        anchored_lines(text, "a")


def test_the_proofs_of_the_repository_have_the_anchors_the_lesson_names():
    # The real files, not a fixture: every anchor is a theorem or definition.
    for module, anchor in [
        ("Kinematics", "velocity_sq_of_constant_acceleration"),
        ("EulerOscillator", "euler_energy_step"),
    ]:
        text = (
            REPOSITORY_ROOT / f"lean/PhysicsByConstruction/Mechanics/{module}.lean"
        ).read_text()
        lines, _ = anchored_lines(text, anchor)
        assert any(
            line.startswith(("theorem ", "noncomputable def ")) for line in lines
        )


# --- modules ------------------------------------------------------------------


def test_module_names_map_to_files_of_the_lean_project():
    assert module_path(MODULE) == "lean/PhysicsByConstruction/Mechanics/Sample.lean"


@pytest.mark.parametrize(
    "module", ["Mathlib.Data.Real.Basic", "PhysicsByConstruction", "../x", ""]
)
def test_other_names_are_not_modules_of_the_project(module: str):
    with pytest.raises(ValueError, match="not a module of the project"):
        module_path(module)


# --- excerpts -----------------------------------------------------------------


def test_excerpt_is_the_region_of_the_file_as_it_is(project: Path):
    shown = lean_excerpt(MODULE, "second", project)

    assert shown.source == (
        "/-- Two lines,\nwith a doc comment. -/\ntheorem second : (2 : Nat) = 2 := rfl"
    )
    assert shown.name == f"{MODULE}:second"
    assert (shown.first_line, shown.last_line) == (8, 10)
    assert shown.path == "lean/PhysicsByConstruction/Mechanics/Sample.lean"


def test_excerpt_renders_a_lean_listing_that_names_its_source(project: Path):
    text = lean_excerpt(MODULE, "first", project)._repr_markdown_()

    assert f'```{{.lean source="{MODULE}:first"}}' in text
    assert "theorem first : (1 : Nat) = 1 := rfl" in text
    assert "lines 4 to 4" in text


def test_excerpt_of_a_file_changed_after_compiling_is_refused(project: Path):
    file = project / "PhysicsByConstruction" / "Mechanics" / "Sample.lean"
    file.write_text(SOURCE.replace("(1 : Nat) = 1", "(1 : Nat) = 2"))

    with pytest.raises(RuntimeError, match="changed after it was compiled"):
        lean_excerpt(MODULE, "first", project)


def test_excerpt_without_a_build_record_is_refused(project: Path):
    (project / BUILD_RECORD).unlink()

    with pytest.raises(FileNotFoundError, match=r"check-lean\.sh"):
        lean_excerpt(MODULE, "first", project)


def test_excerpt_of_a_module_the_build_did_not_compile_is_refused(project: Path):
    other = project / "PhysicsByConstruction" / "Mechanics" / "Other.lean"
    other.write_text(SOURCE)

    with pytest.raises(LookupError, match="lists no module"):
        lean_excerpt("PhysicsByConstruction.Mechanics.Other", "first", project)


# --- links --------------------------------------------------------------------

COMMIT = BuildCommit(sha="a" * 40, dirty=False)
REPOSITORY = "https://github.com/example/repository"


def test_editor_link_loads_the_file_at_the_built_commit():
    path = "lean/PhysicsByConstruction/Mechanics/Sample.lean"

    link = editor_link(path, COMMIT, REPOSITORY)

    assert link is not None and link.startswith("https://live.lean-lang.org/#url=")
    loaded = unquote(urlparse(link).fragment.removeprefix("url="))
    assert loaded == (
        f"https://raw.githubusercontent.com/example/repository/{COMMIT.sha}/{path}"
    )
    assert not parse_qs(urlparse(link).query)


def test_no_editor_link_without_a_commit_or_a_github_repository():
    path = "lean/X.lean"

    assert editor_link(path, BuildCommit(sha=None, dirty=False), REPOSITORY) is None
    assert editor_link(path, COMMIT, "https://example.org/repository") is None


# --- evidence -----------------------------------------------------------------


def test_evidence_states_commit_versions_and_links(project: Path):
    evidence = lean_evidence(MODULE, project=project)
    text = type(evidence)(
        modules=evidence.modules,
        lean=evidence.lean,
        mathlib=evidence.mathlib,
        mathlib_revision=evidence.mathlib_revision,
        commit=COMMIT,
        repository=REPOSITORY,
    )._repr_markdown_()

    assert "Lean 4.99.0" in text
    assert "Mathlib v4.99.0" in text and evidence.mathlib_revision in text
    assert f"{REPOSITORY}/tree/{COMMIT.sha}" in text
    assert f"{REPOSITORY}/blob/{COMMIT.sha}/lean/PhysicsByConstruction" in text
    assert "https://live.lean-lang.org/#url=" in text
    assert "uncommitted changes" not in text


def test_evidence_of_a_dirty_checkout_says_so(project: Path):
    evidence = lean_evidence(MODULE, project=project)
    dirty = type(evidence)(
        modules=evidence.modules,
        lean=evidence.lean,
        mathlib=evidence.mathlib,
        mathlib_revision=evidence.mathlib_revision,
        commit=BuildCommit(sha="b" * 40, dirty=True),
        repository=REPOSITORY,
    )

    assert "uncommitted changes" in dirty._repr_markdown_()


def test_evidence_needs_a_module(project: Path):
    with pytest.raises(ValueError, match="at least one"):
        lean_evidence(project=project)
