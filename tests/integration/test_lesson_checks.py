"""The lesson source checks report a lesson that violates them.

Each test writes a small repository with one lesson and one violation and
runs the check that tests/lessons runs on this repository. The unchanged
lesson passes every check, so a reported violation comes from the violation
and not from the test setup.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from support import lesson_checks
from support.checks import output, run_check
from support.site_checks import Violation

LESSON = "site/lessons/mechanics/01-sample"

_VALID = """\
---
title: "Sample lesson"
description: "A lesson that follows the format."
lesson:
  id: sample
  strand: mechanics
  order: 1
  difficulty: 1
  prerequisites:
    lessons: []
    outside:
      - "Calculus"
---

```{python}
#| echo: false
lesson_header()
```

Introduction.

## Assumptions

1. A point particle.

## Explanation

The position changes at the rate $v$.

## Code

```{python}
position = 1.0 + 2.0 * 0.5
```

## Worked examples

```{python}
#| label: fig-line
#| fig-cap: "A line."
#| fig-alt: "A straight line that rises from the origin."
import matplotlib.pyplot as plt

plt.plot([0.0, 1.0], [0.0, position])
plt.show()
```

## Exercises

::: {.exercise}
Where is the particle after one second?

::: {.solution}
At `{python} position` m.
:::
:::

## Reproduce this

```{python}
#| echo: false
reproduce_this(code=[])
```
"""

Repository = Callable[..., Path]


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.org",
            *arguments,
        ],
        cwd=repository,
        capture_output=True,
        check=True,
    )


@pytest.fixture
def make_repository(tmp_path: Path) -> Repository:
    """Write a repository with one lesson.

    ``change`` maps text of the valid lesson to its replacement, ``lesson``
    is the directory of the lesson, and ``files`` are further files.
    """

    def make(
        change: dict[str, str] | None = None,
        lesson: str = LESSON,
        files: dict[str, str] | None = None,
        config: str = "project:\n  type: website\n",
    ) -> Path:
        text = _VALID
        for old, new in (change or {}).items():
            assert old in text, f"the valid lesson does not contain {old!r}"
            text = text.replace(old, new)
        repository = tmp_path / "repository"
        for name, content in {
            "site/_quarto.yml": config,
            f"{lesson}/index.qmd": text,
            **(files or {}),
        }.items():
            (repository / name).parent.mkdir(parents=True, exist_ok=True)
            (repository / name).write_text(content)
        git(repository, "init", "--quiet")
        return repository

    return make


def rules(violations: list[Violation]) -> set[str]:
    return {violation.rule for violation in violations}


def details(violations: list[Violation]) -> str:
    return "\n".join(violation.detail for violation in violations)


def all_checks(repository: Path) -> list[Violation]:
    return [
        *lesson_checks.check_metadata(repository),
        *lesson_checks.check_sections(repository),
        *lesson_checks.check_path(repository),
        *lesson_checks.check_displayed_code(repository),
        *lesson_checks.check_figures(repository),
        *lesson_checks.check_committed_files(repository),
    ]


def test_a_lesson_that_follows_the_format_passes_every_check(
    make_repository: Repository,
):
    assert all_checks(make_repository()) == []


# --- Front matter -------------------------------------------------------------


@pytest.mark.parametrize(
    "line, field",
    [
        ('title: "Sample lesson"\n', "title"),
        ("  id: sample\n", "lesson.id"),
        ("  strand: mechanics\n", "lesson.strand"),
        ("  order: 1\n", "lesson.order"),
        ("  difficulty: 1\n", "lesson.difficulty"),
        (
            '  prerequisites:\n    lessons: []\n    outside:\n      - "Calculus"\n',
            "lesson.prerequisites",
        ),
    ],
)
def test_missing_metadata_field_is_reported(
    make_repository: Repository, line: str, field: str
):
    violations = lesson_checks.check_metadata(make_repository({line: ""}))

    assert rules(violations) == {"metadata"}
    assert f"'{field}'" in details(violations)


@pytest.mark.parametrize(
    "old, new",
    [
        ("  id: sample\n", "  id: Sample Lesson\n"),
        ("  strand: mechanics\n", "  strand: optics\n"),
        # A valid strand, but not the one of the directory the lesson is in.
        ("  strand: mechanics\n", "  strand: lean\n"),
        ("  order: 1\n", "  order: 2\n"),
        ("  order: 1\n", '  order: "1"\n'),
        ("  difficulty: 1\n", "  difficulty: 4\n"),
        ("    lessons: []\n", "    lessons: [sample]\n"),
        ("    lessons: []\n", "    lessons: kinematics\n"),
        ('    outside:\n      - "Calculus"\n', ""),
        ("  difficulty: 1\n", "  difficulty: 1\n  lean-modules: [kinematics]\n"),
        # Keys outside the format, such as a misspelt one or a Quarto option
        # that changes how the page is executed.
        ("  difficulty: 1\n", "  difficulty: 1\n  prerequisite: []\n"),
        ("lesson:\n", "freeze: true\nlesson:\n"),
    ],
    ids=[
        "id",
        "unknown-strand",
        "other-strand",
        "order-differs-from-directory",
        "order-text",
        "difficulty-out-of-range",
        "own-prerequisite",
        "prerequisites-not-a-list",
        "no-outside-prerequisites",
        "lean-module-name",
        "unknown-lesson-key",
        "unknown-key",
    ],
)
def test_invalid_metadata_is_reported(make_repository: Repository, old: str, new: str):
    violations = lesson_checks.check_metadata(make_repository({old: new}))

    assert rules(violations) == {"metadata"}


def test_page_without_front_matter_is_reported(make_repository: Repository):
    repository = make_repository()
    (repository / LESSON / "index.qmd").write_text("## Assumptions\n\nNone.\n")

    assert rules(lesson_checks.check_metadata(repository)) == {"metadata"}


def test_lean_modules_of_the_project_are_accepted(make_repository: Repository):
    repository = make_repository(
        {
            "  difficulty: 1\n": "  difficulty: 1\n"
            "  lean-modules: [PhysicsByConstruction.Mechanics.Kinematics]\n"
        }
    )

    assert lesson_checks.check_metadata(repository) == []


# --- Sections -----------------------------------------------------------------


@pytest.mark.parametrize(
    "heading, identifier",
    [
        ("## Assumptions\n", "assumptions"),
        ("## Explanation\n", "explanation"),
        ("## Code\n", "code"),
        ("## Worked examples\n", "worked-examples"),
        ("## Exercises\n", "exercises"),
        ("## Reproduce this\n", "reproduce-this"),
    ],
)
def test_missing_required_section_is_reported(
    make_repository: Repository, heading: str, identifier: str
):
    violations = lesson_checks.check_sections(make_repository({heading: ""}))

    assert rules(violations) == {"sections"}
    assert f"'{identifier}'" in details(violations)


def test_section_may_have_a_title_of_its_own(make_repository: Repository):
    repository = make_repository({"## Code\n": "## The program {#code}\n"})

    assert lesson_checks.check_sections(repository) == []


def test_section_at_another_heading_level_does_not_count(
    make_repository: Repository,
):
    repository = make_repository({"## Assumptions\n": "### Assumptions\n"})

    assert "'assumptions'" in details(lesson_checks.check_sections(repository))


def test_empty_section_is_reported(make_repository: Repository):
    repository = make_repository({"1. A point particle.\n": ""})

    violations = lesson_checks.check_sections(repository)

    assert rules(violations) == {"sections"}
    assert "'assumptions' is empty" in details(violations)


def test_interactive_visualization_may_replace_the_exercises(
    make_repository: Repository,
):
    repository = make_repository(
        {"## Exercises\n": "## Interactive visualization\n\nA figure.\n\n### More\n"}
    )

    assert lesson_checks.check_sections(repository) == []


@pytest.mark.parametrize(
    "old, new",
    [
        ("::: {.solution}\nAt `{python} position` m.\n:::\n", ""),
        ("::: {.exercise}\n", "::: {.task}\n"),
        (
            "Introduction.\n",
            "Introduction.\n\n::: {.solution}\nA stray solution.\n:::\n",
        ),
    ],
    ids=["exercise-without-solution", "no-exercise", "solution-outside-exercise"],
)
def test_exercise_without_on_page_solution_is_reported(
    make_repository: Repository, old: str, new: str
):
    violations = lesson_checks.check_sections(make_repository({old: new}))

    assert rules(violations) == {"sections"}


_HEADER = "```{python}\n#| echo: false\nlesson_header()\n```\n"


@pytest.mark.parametrize(
    "change",
    [
        {_HEADER: ""},
        {_HEADER: "", "## Assumptions\n": "## Assumptions\n\n" + _HEADER},
        {_HEADER: "```{python}\n#| eval: false\nlesson_header()\n```\n"},
    ],
    ids=["no-header-cell", "header-after-the-first-heading", "header-not-executed"],
)
def test_lesson_without_a_generated_header_is_reported(
    make_repository: Repository, change: dict[str, str]
):
    violations = lesson_checks.check_sections(make_repository(change))

    assert rules(violations) == {"sections"}
    assert "lesson_header()" in details(violations)


def test_hand_written_reproduce_section_is_reported(make_repository: Repository):
    repository = make_repository(
        {
            "```{python}\n#| echo: false\nreproduce_this(code=[])\n```\n": (
                "Clone the repository and run the page.\n"
            )
        }
    )

    violations = lesson_checks.check_sections(repository)

    assert rules(violations) == {"sections"}
    assert "reproduce_this()" in details(violations)


# --- The learning path --------------------------------------------------------


def second_lesson(
    id: str = "second",
    order: int = 2,
    strand: str = "mechanics",
    prerequisites: str = "[sample]",
    difficulty: int = 1,
) -> dict[str, str]:
    """A second lesson that follows the format, as ``files`` for the fixture."""
    text = _VALID
    for old, new in {
        "  id: sample\n": f"  id: {id}\n",
        "  strand: mechanics\n": f"  strand: {strand}\n",
        "  order: 1\n": f"  order: {order}\n",
        "  difficulty: 1\n": f"  difficulty: {difficulty}\n",
        "    lessons: []\n": f"    lessons: {prerequisites}\n",
    }.items():
        assert old in text
        text = text.replace(old, new)
    return {f"site/lessons/{strand}/{order:02d}-{id}/index.qmd": text}


def test_two_lessons_that_form_a_path_pass(make_repository: Repository):
    assert all_checks(make_repository(files=second_lesson())) == []


@pytest.mark.parametrize(
    "change, files, expected",
    [
        ({}, second_lesson(id="sample", prerequisites="[]"), "already used"),
        ({}, second_lesson(prerequisites="[gravity]"), "not the id of any lesson"),
        ({"    lessons: []\n": "    lessons: [second]\n"}, second_lesson(), "cycle"),
        (
            {"    lessons: []\n": "    lessons: [second]\n"},
            second_lesson(prerequisites="[]"),
            "does not come earlier",
        ),
        ({}, second_lesson(order=3), "no lesson with order 2"),
        ({}, second_lesson(order=1), "'lesson.order' 1 is already used"),
    ],
    ids=[
        "duplicate-id",
        "unknown-prerequisite",
        "cycle",
        "prerequisite-later-in-the-path",
        "gap-in-the-order",
        "duplicate-order",
    ],
)
def test_lessons_that_do_not_form_a_path_are_reported(
    make_repository: Repository,
    change: dict[str, str],
    files: dict[str, str],
    expected: str,
):
    violations = lesson_checks.check_path(make_repository(change, files=files))

    assert rules(violations) == {"path"}
    assert expected in details(violations)


def test_lesson_outside_the_schema_is_left_out_of_the_path(
    make_repository: Repository,
):
    # The metadata check reports the lesson; the path is checked without it,
    # so one mistake is reported once.
    repository = make_repository(files=second_lesson(difficulty=4))

    assert rules(lesson_checks.check_metadata(repository)) == {"metadata"}
    assert lesson_checks.check_path(repository) == []


# --- Displayed code -----------------------------------------------------------

_CELL = "```{python}\nposition = 1.0 + 2.0 * 0.5\n```\n"
_NOT_EXECUTED = {
    "python-block": "```python\nposition = 3.0\n```\n",
    "python-class": "```{.python}\nposition = 3.0\n```\n",
    "tilde-fence": "~~~python\nposition = 3.0\n~~~\n",
    "no-language": "```\nposition = 3.0\n```\n",
    "indented": "    position = 3.0\n",
    "shell": "```bash\npython simulate.py\n```\n",
    "pasted-output": "```text\nposition: 3.0 m\n```\n",
    "raw-html": "<pre>position = 3.0</pre>\n",
    "eval-false": "```{python}\n#| eval: false\nposition = 3.0\n```\n",
    # Quarto also reads '# |' as an option line.
    "eval-false-spaced": "```{python}\n# | eval: false\nposition = 3.0\n```\n",
}


@pytest.mark.parametrize("block", _NOT_EXECUTED.values(), ids=_NOT_EXECUTED.keys())
def test_code_that_is_not_executed_needs_the_not_verified_marker(
    make_repository: Repository, block: str
):
    repository = make_repository({_CELL: _CELL + "\n" + block})

    assert rules(lesson_checks.check_displayed_code(repository)) == {"unverified-code"}


@pytest.mark.parametrize("block", _NOT_EXECUTED.values(), ids=_NOT_EXECUTED.keys())
def test_code_marked_not_verified_is_accepted(make_repository: Repository, block: str):
    marked = "::: {.not-verified}\n" + block + ":::\n"
    repository = make_repository({_CELL: _CELL + "\n" + marked})

    assert lesson_checks.check_displayed_code(repository) == []


def test_marker_on_another_block_does_not_cover_the_code(
    make_repository: Repository,
):
    repository = make_repository(
        {
            _CELL: _CELL + "\n::: {.not-verified}\nA remark.\n:::\n\n"
            "```python\nposition = 3.0\n```\n"
        }
    )

    assert rules(lesson_checks.check_displayed_code(repository)) == {"unverified-code"}


@pytest.mark.parametrize(
    "block",
    [
        "```{r}\nposition <- 3\n```\n",
        "```{python echo=FALSE}\nposition = 3.0\n```\n",
        # A cell belongs at the top level of the page, in a div, or in a list.
        "Text.[^note]\n\n[^note]: A note.\n\n    ```{python}\n    position = 3.0\n"
        "    ```\n",
    ],
    ids=["other-engine", "options-in-the-fence", "inside-a-footnote"],
)
def test_cell_the_build_would_not_execute_as_written_is_reported(
    make_repository: Repository, block: str
):
    repository = make_repository({_CELL: _CELL + "\n" + block})

    assert rules(lesson_checks.check_displayed_code(repository)) == {"cell-form"}


@pytest.mark.parametrize("shortcode", ["include _part.qmd", "embed notebook.ipynb#x"])
def test_content_from_another_file_is_reported(
    make_repository: Repository, shortcode: str
):
    repository = make_repository({_CELL: _CELL + "\n{{< " + shortcode + " >}}\n"})

    assert rules(lesson_checks.check_displayed_code(repository)) == {"unverified-code"}


@pytest.mark.parametrize(
    "execute", ["eval: false", "enabled: false", "freeze: auto", "cache: true"]
)
def test_site_configuration_that_does_not_execute_pages_is_reported(
    make_repository: Repository, execute: str
):
    repository = make_repository(
        config=f"project:\n  type: website\nexecute:\n  {execute}\n"
    )

    assert rules(lesson_checks.check_displayed_code(repository)) == {
        "execution-disabled"
    }


# --- Figures ------------------------------------------------------------------

_ALT = '#| fig-alt: "A straight line that rises from the origin."\n'


@pytest.mark.parametrize(
    "old, new",
    [
        (_ALT, ""),
        (_ALT, '#| fig-alt: ""\n'),
        # Declared by its caption alone.
        (
            "#| label: fig-line\n" + '#| fig-cap: "A line."\n' + _ALT,
            '#| fig-cap: "A line."\n',
        ),
    ],
    ids=["no-alt", "empty-alt", "caption-only"],
)
def test_figure_without_alt_text_is_reported(
    make_repository: Repository, old: str, new: str
):
    violations = lesson_checks.check_figures(make_repository({old: new}))

    assert rules(violations) == {"figure-alt"}


@pytest.mark.parametrize(
    "image",
    [
        "![A straight line.](line.png)\n",
        '<img src="line.png" alt="A straight line." width="10" height="10">\n',
    ],
    ids=["markdown", "raw-html"],
)
def test_image_file_in_a_lesson_is_reported(make_repository: Repository, image: str):
    repository = make_repository({"Introduction.\n": "Introduction.\n\n" + image})

    assert rules(lesson_checks.check_figures(repository)) == {"figure-source"}


# --- Committed files ----------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        f"{LESSON}/index_files/figure-html/fig-line-output-1.png",
        f"{LESSON}/line.png",
        f"{LESSON}/line.svg",
        f"{LESSON}/index.html",
        f"{LESSON}/index.ipynb",
        f"{LESSON}/results.json",
        f"{LESSON}/results.npy",
        "site/_site/index.html",
        "site/_freeze/lessons/execute-results/html.json",
        "site/.quarto/idx/index.qmd.json",
        "site/assets/trajectory.png",
        "src/pbc/mechanics/trajectory.csv",
    ],
)
def test_generated_artifact_is_reported(make_repository: Repository, path: str):
    repository = make_repository(files={path: "generated"})

    violations = lesson_checks.check_committed_files(repository)

    assert [(violation.rule, violation.page) for violation in violations] == [
        ("committed-artifact", path)
    ]


def test_committed_generated_figure_is_reported(make_repository: Repository):
    repository = make_repository(files={f"{LESSON}/line.png": "generated"})
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "--message", "Lesson with its figure")

    assert rules(lesson_checks.check_committed_files(repository)) == {
        "committed-artifact"
    }


def test_build_output_that_git_ignores_is_not_reported(make_repository: Repository):
    repository = make_repository(
        files={
            ".gitignore": "site/_site/\nsite/**/*_files/\n",
            "site/_site/index.html": "generated",
            f"{LESSON}/index_files/figure-html/fig-line-output-1.png": "generated",
        }
    )

    assert lesson_checks.check_committed_files(repository) == []


def test_file_at_the_replay_fixture_location_is_accepted(make_repository: Repository):
    repository = make_repository(files={f"{LESSON}/replay.json": '{"messages": []}'})
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "--message", "Lesson with a replay fixture")

    assert lesson_checks.check_committed_files(repository) == []


@pytest.mark.parametrize(
    "path",
    [
        f"{LESSON}/replay/replay.json",
        f"{LESSON}/replay-2.json",
        "site/lessons/mechanics/replay.json",
        "site/lessons/replay.json",
        "site/replay.json",
    ],
)
def test_recording_anywhere_else_is_reported(make_repository: Repository, path: str):
    repository = make_repository(files={path: '{"messages": []}'})

    assert rules(lesson_checks.check_committed_files(repository)) == {
        "committed-artifact"
    }


@pytest.mark.parametrize(
    "path",
    [
        f"{LESSON}/notes.md",
        f"{LESSON}/_part.qmd",
        "site/lessons/mechanics/kinematics/index.qmd",
        "site/lessons/optics/01-lenses/index.qmd",
        "site/lessons/mechanics/index.qmd",
    ],
)
def test_file_that_is_not_part_of_a_lesson_is_reported(
    make_repository: Repository, path: str
):
    repository = make_repository(files={path: "text"})

    violations = lesson_checks.check_committed_files(repository)

    assert [(violation.rule, violation.page) for violation in violations] == [
        ("lesson-layout", path)
    ]


# --- The check as verification runs it ------------------------------------------


def test_verification_passes_a_lesson_that_follows_the_format(
    make_repository: Repository,
):
    repository = make_repository(files={f"{LESSON}/replay.json": '{"messages": []}'})

    result = run_check("lesson-checks", "--repository", repository)

    assert result.returncode == 0, output(result)


@pytest.mark.parametrize(
    "change, files, rule",
    [
        ({"  difficulty: 1\n": ""}, {}, "metadata"),
        ({"## Assumptions\n": ""}, {}, "sections"),
        ({_CELL: _CELL + "\n```python\nposition = 3.0\n```\n"}, {}, "unverified-code"),
        (
            {_CELL: _CELL + "\n" + _NOT_EXECUTED["eval-false-spaced"]},
            {},
            "unverified-code",
        ),
        ({_ALT: ""}, {}, "figure-alt"),
        ({}, {f"{LESSON}/line.png": "generated"}, "committed-artifact"),
        ({_HEADER: ""}, {}, "sections"),
        ({}, second_lesson(id="sample", prerequisites="[]"), "path"),
        ({}, second_lesson(prerequisites="[gravity]"), "path"),
        ({"    lessons: []\n": "    lessons: [second]\n"}, second_lesson(), "path"),
        (
            {"    lessons: []\n": "    lessons: [second]\n"},
            second_lesson(prerequisites="[]"),
            "path",
        ),
    ],
    ids=[
        "missing-metadata-field",
        "missing-required-section",
        "python-block-without-marker",
        "skipped-cell-without-marker",
        "figure-without-alt-text",
        "committed-generated-figure",
        "lesson-without-generated-header",
        "duplicate-lesson-id",
        "unknown-prerequisite",
        "prerequisite-cycle",
        "prerequisite-later-in-the-path",
    ],
)
def test_verification_fails_on_a_violating_lesson(
    make_repository: Repository,
    change: dict[str, str],
    files: dict[str, str],
    rule: str,
):
    repository = make_repository(change, files=files)

    result = run_check("lesson-checks", "--repository", repository)

    # Exit status 1 is pytest's "tests failed", not a usage or collection
    # error; the rule tells this violation from the others.
    assert result.returncode == 1, output(result)
    assert f"[{rule}]" in output(result)


def test_verification_fails_when_there_is_no_lesson(tmp_path: Path):
    (tmp_path / "site").mkdir()
    git(tmp_path, "init", "--quiet")

    result = run_check("lesson-checks", "--repository", tmp_path)

    assert result.returncode == 1, output(result)
