import json
import subprocess
from pathlib import Path

import pytest

from pbc.authoring import BuildCommit, Excerpt, build_commit, excerpt, reproduce_this
from pbc.authoring.excerpt import select
from pbc.authoring.repository import REPOSITORY_ROOT, repository_url
from pbc.mechanics import dynamics, kinematics
from pbc.mechanics.kinematics import State, euler_step


def git(directory: Path, *arguments: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.org",
            *arguments,
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A Git repository with one commit."""
    root = tmp_path / "checkout"
    root.mkdir()
    git(root, "init", "--quiet")
    (root / ".gitignore").write_text("_site/\n")
    (root / "page.qmd").write_text("A page.\n")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "--message", "First")
    return root


# --- excerpt ------------------------------------------------------------------


def test_excerpt_is_the_text_of_the_source_file():
    shown = excerpt(euler_step)

    lines = (REPOSITORY_ROOT / shown.path).read_text().splitlines(keepends=True)
    assert shown.path == "src/pbc/mechanics/kinematics.py"
    assert shown.source == "".join(lines[shown.first_line - 1 : shown.last_line])
    assert shown.source.startswith("def euler_step(")
    assert shown.name == "pbc.mechanics.kinematics:euler_step"


def test_excerpt_of_a_class_starts_at_its_decorator():
    assert excerpt(State).source.startswith("@dataclass(frozen=True)\nclass State:")


@pytest.mark.parametrize(
    "outside",
    [json.dumps, subprocess.CompletedProcess],
    ids=["function", "class"],
)
def test_excerpt_rejects_code_from_outside_the_package(outside: object):
    with pytest.raises(ValueError, match="not part of pbc"):
        excerpt(outside)


def test_excerpt_rejects_what_is_not_defined_at_the_top_level_of_a_module():
    with pytest.raises(ValueError, match="top level"):
        excerpt(Excerpt._repr_markdown_)


@pytest.mark.parametrize("value", [3.0, kinematics], ids=["number", "module"])
def test_excerpt_rejects_what_is_not_a_function_or_class(value: object):
    with pytest.raises(TypeError):
        excerpt(value)


def _excerpt_of(source: str, commit: BuildCommit) -> Excerpt:
    return Excerpt(
        name="pbc.example:function",
        source=source,
        path="src/pbc/example.py",
        first_line=3,
        last_line=5,
        commit=commit,
        repository="https://example.org/repository",
    )


def test_listing_survives_a_code_fence_inside_the_source():
    # A docstring with a fenced example must not end the listing early.
    source = (
        'def function():\n    """Example:\n\n'
        '    ```\n    function()\n    ```\n    """\n'
    )

    markdown = _excerpt_of(source, BuildCommit("abc", dirty=False))._repr_markdown_()

    opening = markdown.splitlines()[1]
    fence = opening[: len(opening) - len(opening.lstrip("`"))]
    assert len(fence) > 3
    assert markdown.count("\n" + fence + "\n") == 1  # only the closing fence
    assert source.rstrip() in markdown


def test_excerpt_links_to_its_lines_at_the_built_commit():
    markdown = _excerpt_of("x = 1\n", BuildCommit("abc123", False))._repr_markdown_()

    assert (
        "https://example.org/repository/blob/abc123/src/pbc/example.py#L3-L5"
        in markdown
    )


def test_excerpt_without_a_known_commit_has_no_link():
    markdown = _excerpt_of("x = 1\n", BuildCommit(None, False))._repr_markdown_()

    assert "https://" not in markdown
    assert "src/pbc/example.py" in markdown


# --- annotated excerpts -------------------------------------------------------

STEP = "pbc.mechanics.dynamics:euler_step"


def test_lines_show_part_of_the_object_with_the_file_lines_of_that_part():
    shown = excerpt(dynamics.euler_step, lines=(13, 17))

    file = (REPOSITORY_ROOT / shown.path).read_text().splitlines(keepends=True)
    assert shown.source == "".join(file[shown.first_line - 1 : shown.last_line])
    assert shown.source.startswith("    return State(")
    assert shown.lines == (13, 17)


def test_region_shows_the_text_between_its_markers():
    object_lines = [
        "def f():\n",
        "    # region: update\n",
        "    a = 1\n",
        "    # endregion: update\n",
        "    return a\n",
    ]

    assert select(object_lines, None, "update") == (2, ["    a = 1\n"])


@pytest.mark.parametrize(
    "lines, region",
    [((1, 99), None), ((3, 2), None), (None, "missing"), ((1, 2), "update")],
    ids=["past-the-end", "reversed", "missing-region", "both"],
)
def test_a_part_that_does_not_exist_fails_the_build(lines, region):
    with pytest.raises(ValueError):
        excerpt(dynamics.euler_step, lines=lines, region=region)


def test_a_note_marks_its_line_and_is_plain_text_in_the_page():
    shown = excerpt(
        dynamics.euler_step,
        lines=(13, 17),
        notes={"x=state.x + state.v * dt,": "The old velocity moves the particle."},
    )

    markdown = shown._repr_markdown_()
    assert [note.line for note in shown.notes] == [shown.first_line + 2]
    marked = shown.first_line + 2
    assert f'class="line marked" data-line="{marked}"' in markdown
    assert f"Line {marked}" in markdown
    assert "The old velocity moves the particle." in markdown.split("</pre>")[1]


def test_a_note_on_a_line_that_is_not_shown_fails_the_build():
    # The source changed, or the note names a line that lines= hides.
    with pytest.raises(ValueError, match="exactly one"):
        excerpt(
            dynamics.euler_step, lines=(13, 17), notes={"def euler_step(": "Hidden."}
        )


def test_a_note_cannot_contain_a_number_the_build_did_not_compute():
    with pytest.raises(ValueError, match="contains a number"):
        excerpt(
            dynamics.euler_step,
            lines=(13, 17),
            notes={"t=state.t + dt,": "Time advances by 0.1 s."},
        )


def test_a_note_shows_the_numbers_it_was_given():
    shown = excerpt(
        dynamics.euler_step,
        lines=(13, 17),
        notes={"t=state.t + dt,": "Time advances by {dt:.2f} s."},
        values={"dt": 0.1},
    )

    assert shown.notes[0].text == "Time advances by 0.10 s."


@pytest.mark.parametrize(
    "notes, values, error",
    [
        ({"t=state.t + dt,": "By {dt} s."}, {"dt": "0.1"}, TypeError),
        ({"t=state.t + dt,": "By {step} s."}, {"dt": 0.1}, ValueError),
    ],
    ids=["not-a-number", "unknown-placeholder"],
)
def test_values_must_be_numbers_that_the_notes_use(notes, values, error):
    with pytest.raises(error):
        excerpt(dynamics.euler_step, lines=(13, 17), notes=notes, values=values)


def test_interface_lists_inputs_output_and_the_units_of_the_docstring():
    shown = excerpt(dynamics.euler_step, interface=True)

    rows = {row.name: row for row in shown.interface}
    assert list(rows) == ["state", "acceleration", "dt", "return"]
    assert rows["dt"].unit == "s"
    assert rows["state"].type == "State"
    assert rows["return"].kind == "output"
    assert "| `dt` | input |" in shown._repr_markdown_()


# --- build commit -------------------------------------------------------------


def test_clean_checkout_reports_its_commit(checkout: Path):
    commit = build_commit(checkout)

    assert commit == BuildCommit(sha=git(checkout, "rev-parse", "HEAD"), dirty=False)
    assert commit.exact


@pytest.mark.parametrize("file", ["page.qmd", "new-lesson.qmd"])
def test_changed_or_new_file_makes_the_checkout_dirty(checkout: Path, file: str):
    (checkout / file).write_text("Changed.\n")

    commit = build_commit(checkout)

    assert commit.sha == git(checkout, "rev-parse", "HEAD")
    assert commit.dirty and not commit.exact


def test_ignored_build_output_does_not_make_the_checkout_dirty(checkout: Path):
    (checkout / "_site").mkdir()
    (checkout / "_site" / "page.html").write_text("<p>A page.</p>\n")

    assert not build_commit(checkout).dirty


def test_directory_outside_a_checkout_has_no_commit(tmp_path: Path):
    assert build_commit(tmp_path) == BuildCommit(sha=None, dirty=False)


def test_directory_inside_another_checkout_has_no_commit(checkout: Path):
    # A package installed below some other repository must not report that
    # repository's commit as its own.
    inner = checkout / "inner"
    inner.mkdir()

    assert build_commit(inner).sha is None


# --- reproduce this -----------------------------------------------------------


@pytest.fixture
def lesson_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The directory of a lesson page in a website project; cells run there."""
    directory = tmp_path / "site" / "lessons" / "mechanics" / "02-sample"
    directory.mkdir(parents=True)
    (tmp_path / "site" / "_quarto.yml").write_text("project:\n  type: website\n")
    (directory / "index.qmd").write_text("A lesson.\n")
    monkeypatch.chdir(directory)
    return directory


CODE = "src/pbc/mechanics/kinematics.py"
TESTS = "tests/unit/test_kinematics.py"


def test_reproduction_names_the_page_it_is_called_from(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])

    assert reproduction.page == "site/lessons/mechanics/02-sample/index.qmd"
    assert reproduction.output == "site/_site/lessons/mechanics/02-sample/index.html"
    assert reproduction.commands[-2:] == (
        f"uv run --locked pytest {TESTS}",
        "uv run --locked quarto render site/lessons/mechanics/02-sample/index.qmd",
    )


def test_commands_check_out_the_built_commit(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE])
    sha = build_commit().sha

    assert reproduction.commands[:4] == (
        f"git clone {repository_url()}.git",
        "cd physics-by-construction",
        f"git checkout {sha}",
        "uv sync --locked",
    )
    assert f"/tree/{sha}" in reproduction._repr_markdown_()


def test_the_summary_is_short_and_the_full_listing_is_in_a_closed_details(
    lesson_directory: Path,
):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    text = reproduction._repr_markdown_()
    summary, details = text.split('<details class="reproduce-details">')

    assert "<details open" not in text
    # First view: the commit and one command; the files and the other
    # commands are only in the listing.
    assert build_commit().sha in summary
    assert reproduction.commands[-1] in summary
    assert "git clone" not in summary and CODE not in summary
    for command in reproduction.commands:
        assert command in details
    assert CODE in details and TESTS in details


def test_a_page_that_shows_lean_proofs_runs_the_lean_check_before_rendering(
    lesson_directory: Path,
):
    lean_file = "lean/PhysicsByConstruction/Mechanics/Kinematics.lean"

    with_lean = reproduce_this(code=[lean_file, CODE])
    without = reproduce_this(code=[CODE])

    commands = with_lean.commands
    assert commands.index("uv sync --locked") < commands.index(
        "./scripts/check-lean.sh"
    )
    assert commands.index("./scripts/check-lean.sh") < len(commands) - 1
    assert commands[-1].startswith("uv run --locked quarto render ")
    assert "./scripts/check-lean.sh" not in without.commands
    assert "a Lean file the page shows" in with_lean._repr_markdown_()
    assert "check-lean.sh" not in without._repr_markdown_()


def test_uncommitted_changes_are_stated_on_the_page(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE])
    clean = BuildCommit(sha="abc123", dirty=False)
    dirty = BuildCommit(sha="abc123", dirty=True)

    def text(commit: BuildCommit) -> str:
        return type(reproduction)(
            page=reproduction.page,
            code=reproduction.code,
            tests=reproduction.tests,
            commit=commit,
            repository=reproduction.repository,
        )._repr_markdown_()

    assert "uncommitted changes" in text(dirty)
    assert "uncommitted changes" not in text(clean)


@pytest.mark.parametrize(
    "arguments",
    [
        {"code": ["src/pbc/mechanics/no_such_module.py"]},
        {"code": [CODE], "tests": ["tests/unit/test_no_such_test.py"]},
        {"code": [str(REPOSITORY_ROOT / CODE)]},
    ],
    ids=["code", "tests", "absolute"],
)
def test_reproduction_rejects_a_file_that_is_not_in_the_repository(
    lesson_directory: Path, arguments: dict[str, list[str]]
):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        reproduce_this(**arguments)


def test_reproduction_outside_a_website_project_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "index.qmd").write_text("A page.\n")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="website project"):
        reproduce_this(code=[CODE])
