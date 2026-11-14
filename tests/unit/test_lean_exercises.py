"""Lean exercises: the pairing of stubs with solutions, and the stub display."""

import hashlib
import json
from pathlib import Path

import pytest

from pbc.authoring.exercises import (
    LeanStub,
    check,
    lean_stub,
    stub_names,
    theorem_statements,
    uses_sorry,
)
from pbc.authoring.lean import BUILD_RECORD
from pbc.authoring.repository import REPOSITORY_ROOT, BuildCommit

COMMIT = BuildCommit(sha="a" * 40, dirty=False)
REPOSITORY = "https://github.com/example/physics-by-construction"
STUB = """\
import Init

/-- Doc comment. -/
-- ANCHOR: double
theorem double (x : Nat) :
    x + x = 2 * x := by
  sorry
-- ANCHOR_END: double
"""
SOLUTION = """\
import Init

-- ANCHOR: double
/-- A different doc comment. -/
theorem double (x : Nat) : x + x = 2 * x := by
  ring
-- ANCHOR_END: double
"""


def write(project: Path, relative: str, text: str) -> None:
    file = project / relative
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    write(tmp_path, "Exercises/Double.lean", STUB)
    write(tmp_path, "PhysicsByConstruction/Exercises/Double.lean", SOLUTION)
    return tmp_path


def test_statements_ignore_comments_and_layout():
    assert theorem_statements(STUB) == theorem_statements(SOLUTION)
    assert theorem_statements(STUB) == {
        "double": "theorem double (x : Nat) : x + x = 2 * x"
    }


def test_sorry_in_a_comment_is_not_sorry():
    assert uses_sorry("theorem a : True := by\n  sorry\n")
    assert not uses_sorry("-- sorry\n/- admit -/\ntheorem a : True := trivial\n")


def test_a_paired_stub_passes(project: Path):
    assert stub_names(project) == ["Double"]
    assert check(project) == []


def test_a_stub_without_a_solution_fails(project: Path):
    (project / "PhysicsByConstruction/Exercises/Double.lean").unlink()

    assert any("no checked solution" in problem for problem in check(project))


def test_a_changed_statement_fails(project: Path):
    write(
        project,
        "PhysicsByConstruction/Exercises/Double.lean",
        SOLUTION.replace("x + x = 2 * x", "x + x = x * 2"),
    )

    assert any("differs from the solution's" in problem for problem in check(project))


def test_a_solution_with_sorry_and_a_stub_without_it_fail(project: Path):
    write(project, "PhysicsByConstruction/Exercises/Double.lean", STUB)
    write(project, "Exercises/Double.lean", SOLUTION)

    problems = check(project)

    assert any("contains 'sorry'" in problem for problem in problems)
    assert any("not a stub" in problem for problem in problems)


def test_a_theorem_missing_on_either_side_fails(project: Path):
    write(
        project,
        "PhysicsByConstruction/Exercises/Double.lean",
        SOLUTION + "theorem extra : True := trivial\n",
    )
    assert any("'extra' has no stub" in problem for problem in check(project))

    write(project, "PhysicsByConstruction/Exercises/Double.lean", "-- empty\n")
    assert any("does not prove 'double'" in problem for problem in check(project))


def test_a_solution_without_a_stub_fails(project: Path):
    write(project, "PhysicsByConstruction/Exercises/Other.lean", SOLUTION)

    assert any("no stub" in problem for problem in check(project))


def test_a_nested_stub_fails(project: Path):
    write(project, "Exercises/Sub/Nested.lean", STUB)

    assert any("subdirectories" in problem for problem in check(project))


def test_a_solution_without_any_stub_fails(tmp_path: Path):
    write(tmp_path, "PhysicsByConstruction/Exercises/Lonely.lean", SOLUTION)

    assert any("no stub" in problem for problem in check(tmp_path))


def record(project: Path, stub_text: str = STUB) -> None:
    solution = (project / "PhysicsByConstruction/Exercises/Double.lean").read_bytes()
    write(
        project,
        str(BUILD_RECORD),
        json.dumps(
            {
                "modules": {
                    "PhysicsByConstruction.Exercises.Double": hashlib.sha256(
                        solution
                    ).hexdigest()
                },
                "exercises": {
                    "Exercises.Double": hashlib.sha256(stub_text.encode()).hexdigest()
                },
            }
        ),
    )


def test_a_stub_is_shown_as_not_verified(project: Path):
    record(project)

    shown = lean_stub("Double", "double", project)

    markdown = shown.markdown(COMMIT, REPOSITORY)
    assert markdown.startswith("::: {.not-verified .lean-stub role=note}")
    # Built after the render's filter: the region writes its label itself.
    assert "::: {.not-verified-label}\n**Not verified.**" in markdown
    assert "theorem double" in markdown and "sorry" in markdown
    assert "ANCHOR" not in markdown
    assert shown.path == "lean/Exercises/Double.lean"


def test_a_stub_links_to_its_lines_at_the_built_commit(project: Path):
    record(project)

    shown = lean_stub("Double", "double", project)

    # The region of the stub is lines 5 to 7 of the file, between its anchors.
    assert (shown.first_line, shown.last_line) == (5, 7)
    markdown = shown.markdown(COMMIT, REPOSITORY)
    link = f"{REPOSITORY}/blob/{COMMIT.sha}/lean/Exercises/Double.lean#L5-L7"
    assert f"]({link})" in markdown
    assert 'lines="5-7"' in markdown
    # The link sits with the listing, inside the "not verified" box.
    assert markdown.index(".excerpt-source") < markdown.index("contains `sorry`")
    assert LeanStub.from_payload(shown.payload()) == shown


def test_a_stub_leaves_a_marker_that_holds_no_commit(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    record(project)
    directory = tmp_path / "site" / "lessons" / "lean" / "04-sample"
    directory.mkdir(parents=True)
    (tmp_path / "site" / "_quarto.yml").write_text("project:\n  type: website\n")
    monkeypatch.chdir(directory)

    shown = lean_stub("Double", "double", project)._repr_markdown_()

    assert 'pbc-kind="lean-stub"' in shown
    assert "theorem" not in shown and COMMIT.sha not in shown


def test_a_stub_changed_after_the_check_is_refused(project: Path):
    record(project)
    write(project, "Exercises/Double.lean", STUB + "-- edited\n")

    with pytest.raises(RuntimeError, match="changed after it was checked"):
        lean_stub("Double", "double", project)


def test_a_stub_the_record_does_not_list_is_refused(project: Path):
    record(project)
    data = json.loads((project / BUILD_RECORD).read_text())
    data["exercises"] = {}
    (project / BUILD_RECORD).write_text(json.dumps(data))

    with pytest.raises(LookupError):
        lean_stub("Double", "double", project)


def test_the_repository_stubs_are_paired():
    assert stub_names(REPOSITORY_ROOT / "lean") != []
    assert check(REPOSITORY_ROOT / "lean") == []
