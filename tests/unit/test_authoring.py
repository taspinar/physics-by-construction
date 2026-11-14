import ast
import json
import re
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.authoring import BuildCommit, Excerpt, build_commit, excerpt, reproduce_this
from pbc.authoring.context import _quarto_code
from pbc.authoring.excerpt import (
    Part,
    _check_signature,
    docstring_lines,
    generated_signature,
    header_lines,
    number_lines,
    select,
    source_link,
)
from pbc.authoring.repository import REPOSITORY_ROOT, repository_url
from pbc.authoring.reproduce import (
    LOCAL_PREVIEW,
    MAIN_MAY_DIFFER,
    PAGE_VERSION,
    SKIP_PAGE_VERSION,
)
from pbc.materials import stress_strain
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
        path="src/pbc/example.py",
        parts=(Part((1, source.count("\n")), 3, source),),
        span=(3, 5),
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


def test_excerpt_ends_with_a_compact_source_link_that_holds_its_metadata():
    markdown = _excerpt_of("x = 1\n", BuildCommit("abc123", False)).markdown()

    source = markdown.split("::: {.excerpt-source}\n", 1)[1]
    # The link reads "Source"; a screen reader also hears the object and lines.
    assert source.startswith(
        "[Source [of `function`, lines 3 to 5]{.visually-hidden}]("
    )
    for attribute in (
        'path="src/pbc/example.py"',
        'lines="3-5"',
        'commit="abc123"',
        'source-name="pbc.example:function"',
    ):
        assert attribute in source
    # No sentence after every block (U1b).
    assert "read from the repository" not in markdown


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

    assert select(object_lines, None, "update") == [(3, 3)]


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
    assert f'marked="{marked}:1"' in markdown
    assert f"Line {marked}" in markdown
    listing_end = markdown.index(shown.source.rstrip("\n")) + len(shown.source)
    assert markdown.index("The old velocity moves the particle.") > listing_end


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


# --- exact selections, the docstring, the generated signature (ADR 023) -------


def _file_lines(shown: Excerpt) -> list[str]:
    return (REPOSITORY_ROOT / shown.path).read_text().splitlines(keepends=True)


def test_ranges_show_exact_parts_with_their_file_lines_and_a_marker_between():
    shown = excerpt(stress_strain.offset_crossing, lines=[(13, 15), (18, 21)])

    file = _file_lines(shown)
    assert [part.lines for part in shown.parts] == [(13, 15), (18, 21)]
    for part in shown.parts:
        assert part.source == "".join(file[part.first_line - 1 : part.last_line])
    assert shown.parts[0].source.lstrip().startswith("e = np.asarray(strain")
    assert shown.parts[1].source.lstrip().startswith("raise ValueError(")
    (omission,) = shown.omissions()
    assert (omission.first_line, omission.last_line) == (
        shown.parts[0].last_line + 1,
        shown.parts[1].first_line - 1,
    )
    markdown = shown.markdown()
    assert 'lines="13-15,18-21"' in markdown
    assert (
        f"Lines {omission.first_line} to {omission.last_line} are not shown."
        in markdown
    )
    for part in shown.parts:
        assert f'first-line="{part.first_line}"' in markdown


@pytest.mark.parametrize(
    "lines",
    [[(5, 8), (8, 10)], [(5, 8), (9, 10)], [(9, 10), (5, 6)], [(1, 2), (4, 99)]],
    ids=["overlapping", "touching", "out-of-order", "past-the-end"],
)
def test_ranges_that_could_hide_an_omission_fail_the_build(lines):
    with pytest.raises(ValueError):
        excerpt(stress_strain.offset_crossing, lines=lines)


def test_a_selection_is_labelled_and_the_whole_object_is_not():
    selected = excerpt(dynamics.euler_step, lines=(13, 17)).markdown()
    whole = excerpt(dynamics.euler_step).markdown()

    assert "Selected lines of `euler_step`, not the whole function" in selected
    assert ".excerpt-part" in selected
    assert "excerpt-label" not in whole
    assert "excerpt-part" not in whole


def test_the_source_link_of_a_selection_opens_the_whole_object():
    shown = excerpt(dynamics.euler_step, lines=(13, 17))

    file = _file_lines(shown)
    first, last = shown.span
    assert file[first - 1].startswith("def euler_step(")
    assert "".join(file[first - 1 : last]) == excerpt(dynamics.euler_step).source
    assert f'lines="{first}-{last}"' in shown.markdown()


def test_docstring_is_left_out_of_the_display_only_and_marked():
    shown = excerpt(stress_strain.offset_crossing, docstring=False)

    file = _file_lines(shown)
    whole = excerpt(stress_strain.offset_crossing)
    docstring = docstring_lines(whole.source)
    assert docstring is not None and shown.docstring == docstring
    first, last = (whole.first_line + n - 1 for n in docstring)
    assert file[first - 1].strip().startswith('"""')
    assert file[last - 1].rstrip().endswith('"""')
    assert '"""' not in shown.source
    assert len(shown.source.splitlines()) + last - first + 1 == len(
        whole.source.splitlines()
    )
    (omission,) = shown.omissions()
    assert omission.docstring and (omission.first_line, omission.last_line) == (
        first,
        last,
    )
    assert f"The docstring, lines {first} to {last}, is not shown." in (
        shown.markdown()
    )


def test_leaving_out_a_docstring_that_is_not_shown_fails_the_build():
    with pytest.raises(ValueError, match="no docstring"):
        excerpt(stress_strain.offset_crossing, lines=(13, 21), docstring=False)


def test_generated_signature_is_what_the_build_reads_from_the_function():
    import inspect

    shown = excerpt(stress_strain.offset_crossing, signature=True, lines=(13, 21))

    assert shown.signature == (
        "def offset_crossing(\n"
        "    strain,\n"
        "    stress,\n"
        "    modulus,\n"
        "    offset,\n"
        "    intercept=0.0,\n"
        "): ...\n"
    )
    stub = ast.parse(shown.signature).body[0]
    names = [a.arg for a in stub.args.args]
    parameters = inspect.signature(stress_strain.offset_crossing).parameters
    assert names == list(parameters)
    assert ast.literal_eval(stub.args.defaults[0]) == parameters["intercept"].default
    # It stands for the header as written, which the parts do not repeat.
    assert shown.signature_lines == header_lines(
        excerpt(stress_strain.offset_crossing).source
    )
    assert "def offset_crossing" not in shown.source
    markdown = shown.markdown()
    assert "Generated signature of `offset_crossing`, not the source text" in markdown
    assert 'replaces="1-7"' in markdown
    # The docstring between the header and line 13 is marked as left out.
    leading = shown.leading_omission()
    assert leading is not None and leading.docstring


def test_generated_signature_keeps_the_units_of_the_interface_table():
    shown = excerpt(dynamics.euler_step, signature=True, interface=True)

    units = {row.name: row.unit for row in shown.interface}
    assert "    dt,  # s\n" in (shown.signature or "")
    assert units["dt"] == "s"


def test_generated_signature_keeps_every_kind_of_parameter_and_default():
    text = "def f(a, /, b=1e-3, *args, c, d=(1, 2), **rest) -> int:\n    return 1\n"

    shown = generated_signature(text, {"b": "m"})

    assert shown == (
        "def f(\n    a,\n    /,\n    b=1e-3,  # m\n    *args,\n    c,\n"
        "    d=(1, 2),\n    **rest,\n): ...\n"
    )
    ast.parse(shown)


def test_a_signature_whose_default_differs_from_the_function_fails_the_build():
    def f(a, b=2):
        return a + b

    with pytest.raises(ValueError, match="default"):
        _check_signature(f, "def f(a, b=3):\n    return a + b\n", "f")
    with pytest.raises(ValueError, match="parameters"):
        _check_signature(f, "def f(a, c=2):\n    return a + c\n", "f")


def test_a_class_has_no_generated_signature():
    with pytest.raises(ValueError, match="function"):
        excerpt(State, signature=True)


def test_an_excerpt_round_trips_through_its_marker_payload():
    shown = excerpt(
        stress_strain.offset_crossing,
        lines=[(13, 15), (18, 21)],
        signature=True,
        notes={"k = int(below[0])": "The first sample below the line."},
    )

    again = Excerpt.from_payload(shown.payload(), shown.commit, shown.repository)

    assert again == shown


def test_figure_source_is_a_link_alone():
    shown = source_link(stress_strain.offset_crossing, figure=True)

    markdown = shown.markdown()
    assert markdown.startswith("::: {.excerpt-source .figure-source}\n")
    assert "Figure source [of `offset_crossing`" in markdown
    assert "```" not in markdown
    file = _file_lines(shown)
    assert file[shown.span[0] - 1].startswith("def offset_crossing(")


# Pandoc's HTML of a highlighted block, as `quarto pandoc` writes it.
_CONVERTED = (
    '<div class="sourceCode" id="ctx-cb1" data-marked="11:1" data-first-line="10"'
    ' tabindex="0"><pre class="sourceCode python excerpt-listing excerpt-part">'
    '<code class="sourceCode python"><span id="ctx-cb1-1"><a href="#ctx-cb1-1"'
    ' aria-hidden="true" tabindex="-1"></a>x <span class="op">=</span>'
    ' <span class="dv">1</span></span>\n<span id="ctx-cb1-2"><a href="#ctx-cb1-2"'
    ' aria-hidden="true" tabindex="-1"></a><span class="cf">return</span> x</span>'
    "</code></pre></div>"
)


def test_lines_are_numbered_and_marked_after_the_highlighting():
    numbered = number_lines(_CONVERTED)

    assert '<span class="line" data-line="10">x <span class="op">=</span>' in (numbered)
    assert (
        '<span class="line marked" data-line="11" data-note="1">'
        '<span class="cf">return</span>'
    ) in numbered
    # The tokens keep their highlighting, and the text stays the source.
    assert re.sub(r"<[^>]+>", "", numbered) == "x = 1\nreturn x"


def test_a_block_that_is_not_an_excerpt_listing_is_left_as_converted():
    plain = _CONVERTED.replace(" excerpt-listing excerpt-part", "")

    assert number_lines(plain) == plain


def test_a_part_of_a_selection_gets_no_copy_button_and_a_whole_listing_does():
    whole = _CONVERTED.replace(" excerpt-part", "")

    assert "code-copy-button" not in _quarto_code(_CONVERTED)
    assert "code-copy-button" in _quarto_code(whole)
    assert 'data-line="10"' in _quarto_code(whole)


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

    reproduction = reproduce_this(code=[CODE], tests=[TESTS])

    # Clean and with uncommitted changes; the owner's notice of a local build
    # ("Local preview: ...") names the reader's page, not a command.
    for dirty in (False, True):
        commit = BuildCommit(sha="abc123", dirty=dirty)
        text = replace(reproduction, commit=commit).markdown()
        text = text.replace(LOCAL_PREVIEW, "")
        for word in SITE_BUILD:
            assert word not in text
        assert "Reproduce this" not in text


def test_the_summary_is_one_sentence_and_the_full_listing_is_in_a_closed_details(
    lesson_directory: Path,
):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    clean = replace(reproduction, commit=BuildCommit(sha="abc123", dirty=False))
    text = clean.markdown()
    summary, details = text.split('<details class="reproduce-details">')

    assert "<details open" not in text
    # First view: one sentence, no commit, no command (the owner's decision
    # of 2026-11-14 on F174); every command, the files, and the tests are
    # only in the closed "Setup and commands", and no command is shown twice.
    assert summary == "::: {.reproduce}\nRun this experiment on your own computer.\n\n"
    assert "<summary>Setup and commands</summary>" in details
    for command in clean.commands:
        assert command in details
        assert text.count(command) == 1
    assert CODE in details and TESTS in details
    assert "results/results.json" in details
    assert "[the setup page](../../../reproduce.html)" in details


def test_main_is_the_default_route_and_the_page_version_is_the_extra_checkout(
    lesson_directory: Path,
):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    page = replace(reproduction, commit=BuildCommit(sha="abc123", dirty=False))
    details = page.markdown().split("<summary>")[1]
    clone, checkout, run = (
        details.index("git clone "),
        details.index("git checkout abc123"),
        details.index("uv sync --locked --no-dev"),
    )

    # The clone gives main, with its note; the version behind this page adds
    # one checkout, of the build commit, linked by a description, not by its
    # hash; the shared steps follow once.
    assert clone < details.index(MAIN_MAY_DIFFER) < checkout < run
    assert clone < details.index(PAGE_VERSION) < checkout
    # The checkout is labelled optional, and a reader who runs every block in
    # order is told before it that skipping it keeps the latest version (the
    # owner's review of 2026-11-14).
    assert PAGE_VERSION.startswith("Optional: ")
    assert details.index(PAGE_VERSION) < details.index(SKIP_PAGE_VERSION) < checkout
    assert f"[the commit this page was built from]({page.repository}/tree/abc123)" in (
        details
    )
    assert "[`abc123`]" not in details
    assert "in either version" in details
    # The links to the files point to the build commit.
    assert f"{page.repository}/blob/abc123/{CODE}" in details
    # An exact reproduction is promised for the version behind this page.
    assert "match this page to the digits shown" in details


def test_a_page_of_an_unknown_commit_offers_main_only(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE], tests=[TESTS])
    unknown = replace(reproduction, commit=BuildCommit(sha=None, dirty=False))
    text = unknown.markdown()

    assert "git checkout" not in text and PAGE_VERSION not in text
    assert SKIP_PAGE_VERSION not in text
    assert "the commit of its sources is unknown" in text
    assert MAIN_MAY_DIFFER in text and "in either version" not in text
    assert "match this page to the digits shown" not in text
    assert "/blob/" not in text


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
    # The sentence says what can be checked; the command is in the listing,
    # once (F174).
    assert "Check this proof and run its experiment on your own computer." in summary
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
    # The sentence names the recorded run; the live run, with its commands,
    # is inside the closed disclosure, after the replay (F174).
    assert "Replay this recorded agent run on your own computer." in main
    assert "<details" in main and "</details>" in live
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


def test_a_data_note_is_inside_the_disclosure_after_the_run(lesson_directory: Path):
    note = """
        The data card above gives the command that downloads a fresh copy of
        the file into `data/downloads/sample`; no model and no account are
        needed to read it.
    """
    reproduction = replace(
        reproduce_this(code=[CODE], tests=[TESTS], data=note),
        commit=BuildCommit(sha="abc123", dirty=False),
    )
    page = "lessons/mechanics/02-sample/index.qmd"
    visible, details = reproduction.markdown().split(
        '<details class="reproduce-details">'
    )
    paragraph = " ".join(note.split())

    # A measured-data lab's note on its download is part of the run
    # instructions, not of the first view, which stays one sentence (the
    # owner's review of 2026-11-14 on F174); it is one paragraph, after what
    # the run writes and before the files, and it survives the marker.
    assert visible == "::: {.reproduce}\nRun this experiment on your own computer.\n\n"
    assert f"\n\n{paragraph}\n\n" in details
    assert (
        details.index("results/results.json")
        < details.index(paragraph)
        < details.index("The files behind this page")
        < details.index("</details>")
    )
    again = type(reproduction).from_payload(
        page, reproduction.payload(), reproduction.commit, reproduction.repository
    )
    assert again == reproduction
    # Without a note, nothing is added.
    assert "data card" not in reproduce_this(code=[CODE]).markdown()


def test_uncommitted_changes_are_stated_on_the_page(lesson_directory: Path):
    reproduction = reproduce_this(code=[CODE])
    clean = replace(reproduction, commit=BuildCommit(sha="abc123", dirty=False))
    dirty = replace(reproduction, commit=BuildCommit(sha="abc123", dirty=True))
    visible, details = dirty.markdown().split('<details class="reproduce-details">')

    # A short notice is visible; the explanation is in the disclosure, and
    # no exact reproduction is promised.
    assert LOCAL_PREVIEW in visible
    assert "uncommitted changes" in details
    assert "does not contain those changes" in details
    assert "match this page to the digits shown" not in dirty.markdown()
    assert LOCAL_PREVIEW not in clean.markdown()
    assert "uncommitted changes" not in clean.markdown()


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
