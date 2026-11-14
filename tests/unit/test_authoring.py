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

    markdown = _excerpt_of(source, BuildCommit("abc", dirty=False)).markdown()

    opening = markdown.splitlines()[1]
    fence = opening[: len(opening) - len(opening.lstrip("`"))]
    assert len(fence) > 3
    assert markdown.count("\n" + fence + "\n") == 1  # only the closing fence
    assert source.rstrip() in markdown


def test_excerpt_links_to_its_lines_at_the_built_commit():
    markdown = _excerpt_of("x = 1\n", BuildCommit("abc123", False)).markdown()

    assert (
        "https://example.org/repository/blob/abc123/src/pbc/example.py#L3-L5"
        in markdown
    )


def test_excerpt_without_a_known_commit_has_no_link():
    markdown = _excerpt_of("x = 1\n", BuildCommit(None, False)).markdown()

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


def test_a_region_of_a_module_shows_the_values_an_experiment_starts_from():
    from pbc.mechanics.experiments import kinematics as experiment

    shown = excerpt(experiment, region="setup")

    file = (REPOSITORY_ROOT / shown.path).read_text().splitlines(keepends=True)
    assert shown.name == "pbc.mechanics.experiments.kinematics:"
    assert shown.source == "".join(file[shown.first_line - 1 : shown.last_line])
    assert file[shown.first_line - 2].strip() == "# region: setup"
    assert "launch = State(" in shown.source


def test_a_module_is_shown_by_a_part_of_it_only():
    from pbc.mechanics.experiments import kinematics as experiment

    with pytest.raises(TypeError, match="region or lines"):
        excerpt(experiment)
    with pytest.raises(ValueError, match="interface"):
        excerpt(experiment, region="setup", interface=True)


def test_a_note_marks_its_line_and_is_plain_text_in_the_page():
    shown = excerpt(
        dynamics.euler_step,
        lines=(13, 17),
        notes={"x=state.x + state.v * dt,": "The old velocity moves the particle."},
    )

    markdown = shown.markdown()
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
    assert "| `dt` | input |" in shown.markdown()


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


_FRONT_MATTER = """\
---
title: "Sample"
lesson:
  id: sample
  methods: {methods}
  experiment: {experiment}
{extra}---

A lesson.
"""


def _write_lesson(directory: Path, methods: str, experiment: str, extra: str = ""):
    (directory / "index.qmd").write_text(
        _FRONT_MATTER.format(methods=methods, experiment=experiment, extra=extra)
    )


@pytest.fixture
def lesson_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The directory of a lesson page in a website project; cells run there."""
    directory = tmp_path / "site" / "lessons" / "mechanics" / "02-sample"
    directory.mkdir(parents=True)
    (tmp_path / "site" / "_quarto.yml").write_text("project:\n  type: website\n")
    _write_lesson(directory, "[simulation]", EXPERIMENT)
    monkeypatch.chdir(directory)
    return directory


CODE = "src/pbc/mechanics/kinematics.py"
TESTS = "tests/unit/test_kinematics.py"
EXPERIMENT = "pbc.mechanics.experiments.kinematics"
# What renders or previews the website; no footer names it (ADR 016).
SITE_BUILD = ("quarto", "render", "preview", "build-site.sh", "verify.sh")


def test_reproduction_names_the_page_and_ends_in_its_experiment(
    lesson_directory: Path,
):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])

    assert reproduction.page == "site/lessons/mechanics/02-sample/index.qmd"
    assert reproduction.heading == "Run this experiment"
    assert reproduction.commands[-2:] == (
        "uv sync --locked --no-dev",
        f"uv run --locked --no-dev python -m {EXPERIMENT} results",
    )


def test_commands_check_out_the_built_commit(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE])
    sha = build_commit().sha

    assert reproduction.commands[:3] == (
        f"git clone {repository_url()}.git",
        "cd physics-by-construction",
        f"git checkout {sha}",
    )
    assert f"/tree/{sha}" in reproduction.markdown()


@pytest.mark.parametrize(
    "methods, extra",
    [
        ("[simulation]", ""),
        ("[simulation, llm-agents]", ""),
        ("[lean]", "  lean-modules: [PhysicsByConstruction.Mechanics.Kinematics]\n"),
    ],
    ids=["run", "replay", "proof"],
)
def test_no_footer_renders_or_previews_the_website(
    lesson_directory: Path, methods: str, extra: str
):
    experiment = (
        "pbc.mechanics.experiments.agent_experiment"
        if "llm-agents" in methods
        else EXPERIMENT
    )
    _write_lesson(lesson_directory, methods, experiment, extra)

    text = reproduce_this(code=[CODE], tests=[TESTS]).markdown()

    for word in SITE_BUILD:
        assert word not in text
    assert "Reproduce this" not in text


def test_the_summary_is_short_and_the_full_listing_is_in_a_closed_details(
    lesson_directory: Path,
):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    text = reproduction.markdown()
    summary, details = text.split('<details class="reproduce-details">')

    assert "<details open" not in text
    # First view: one sentence with the commit and no command (F174); every
    # command, the files, and the tests are only in the listing, and no
    # command is shown twice.
    assert build_commit().sha in summary
    assert "```" not in summary
    sentence = summary.removeprefix("::: {.reproduce}\n").strip()
    assert "\n" not in sentence and sentence.count(". ") <= 1
    assert "run its experiment on your own machine" in sentence
    assert reproduction.experiment_command not in summary
    assert "git clone" not in summary and CODE not in summary
    for command in reproduction.commands:
        assert command in details
        assert text.count(command) == 1
    assert CODE in details and TESTS in details
    assert "results/results.json" in details
    assert "[the setup page](../../../reproduce.html)" in details


def test_a_proof_lesson_checks_its_modules_with_lake_and_needs_no_python_tools(
    lesson_directory: Path,
):
    modules = "[PhysicsByConstruction.Mechanics.Kinematics]"
    _write_lesson(
        lesson_directory, "[lean]", EXPERIMENT, f"  lean-modules: {modules}\n"
    )

    reproduction = reproduce_this(code=[CODE])
    text = reproduction.markdown()
    summary = text.split("<details")[0]

    assert reproduction.heading == "Check this proof"
    assert reproduction.commands[-3:] == (
        "cd lean",
        "lake exe cache get",
        "lake build PhysicsByConstruction.Mechanics.Kinematics",
    )
    # The figures of the page come from its experiment, before the proofs.
    assert reproduction.experiment_command in reproduction.commands
    # The summary says what can be checked; the command is in the listing,
    # once (F174).
    assert "check its proofs" in summary
    assert "lake build" not in summary
    assert text.count("lake build PhysicsByConstruction.Mechanics.Kinematics") == 1
    assert "check-lean.sh" not in text and "jq" not in text
    assert "elan" in text


def test_a_proof_lesson_that_computes_nothing_runs_no_python(lesson_directory: Path):
    modules = "  lean-modules: [PhysicsByConstruction.Mechanics.Kinematics]\n"
    _write_lesson(lesson_directory, "[lean]", "./scripts/check-lean.sh", modules)

    reproduction = reproduce_this(code=[])

    assert not any(command.startswith("uv ") for command in reproduction.commands)
    assert reproduction.commands[-1].startswith("lake build ")


def test_an_agent_lesson_replays_and_names_the_live_run_apart(lesson_directory: Path):
    _write_lesson(
        lesson_directory,
        "[simulation, llm-agents]",
        "pbc.mechanics.experiments.agent_experiment",
    )

    reproduction = reproduce_this(code=[CODE])
    text = reproduction.markdown()
    main, live = text.split("::: {.not-verified role=note}")

    assert reproduction.heading == "Replay this experiment"
    assert reproduction.live == "pbc.agents.projectile_lab"
    # The replay needs no model, no key, and no extra.
    assert "OPENAI_API_KEY" not in main and "--extra" not in main
    assert "no model" in main
    # The live run is labelled, optional, and names its credential and extra.
    assert "**Not verified.**" in live and "Optional" in live
    assert 'export OPENAI_API_KEY="..."' in live
    assert "uv sync --locked --no-dev --extra openai" in live
    assert "python -m pbc.agents.projectile_lab" in live


def test_the_marker_gives_back_the_same_section(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    page = "lessons/mechanics/02-sample/index.qmd"

    again = type(reproduction).from_payload(
        page, reproduction.payload(), reproduction.commit, reproduction.repository
    )

    assert again == reproduction


def test_uncommitted_changes_are_stated_on_the_page(lesson_directory: Path):
    from dataclasses import replace

    reproduction = reproduce_this(code=[CODE])
    clean = BuildCommit(sha="abc123", dirty=False)
    dirty = BuildCommit(sha="abc123", dirty=True)

    assert "uncommitted changes" in replace(reproduction, commit=dirty).markdown()
    assert "uncommitted changes" not in replace(reproduction, commit=clean).markdown()


def test_a_lesson_without_an_experiment_has_no_section(lesson_directory: Path):
    (lesson_directory / "index.qmd").write_text("A lesson.\n")

    with pytest.raises(ValueError, match=r"declares no 'lesson\.experiment'"):
        reproduce_this(code=[CODE])


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


def test_a_diagram_is_deterministic_and_draws_what_was_asked():
    from io import BytesIO

    import matplotlib.pyplot as plt

    from pbc.authoring import FIGURE_COLOURS, diagrams

    def draw() -> tuple[bytes, list[str]]:
        fig, ax = diagrams.canvas(3.0, 2.0, (0.0, 3.0), (0.0, 2.0))
        diagrams.state_box(ax, (1.0, 1.0), "state")
        diagrams.arrow(ax, (1.0, 1.0), (2.5, 1.0), colour=1, linestyle="--")
        diagrams.circle(ax, (2.0, 0.5), 0.2, filled=True)
        diagrams.line(ax, [(0.0, 0.0), (1.0, 0.5)], colour="#000000")
        labels = [t.get_text() for t in ax.texts]
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=80)
        plt.close(fig)
        return buffer.getvalue(), labels

    first, labels = draw()
    second, _ = draw()
    assert first == second
    assert "state" in labels
    assert diagrams._colour(1) == FIGURE_COLOURS[1]


def test_an_arrow_takes_the_colour_and_the_line_style_given():
    import matplotlib.colors
    import matplotlib.pyplot as plt

    from pbc.authoring import FIGURE_COLOURS, diagrams

    fig, ax = diagrams.canvas(3.0, 2.0, (0.0, 3.0), (0.0, 2.0))
    diagrams.arrow(ax, (0.5, 1.0), (2.5, 1.0), colour=2, linestyle=":")
    (patch,) = [p for p in ax.get_children() if hasattr(p, "arrow_patch")]
    plt.close(fig)
    assert patch.arrow_patch.get_linestyle() == ":"
    assert (
        matplotlib.colors.to_hex(patch.arrow_patch.get_edgecolor()) == FIGURE_COLOURS[2]
    )
