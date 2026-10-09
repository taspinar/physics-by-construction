"""The lesson source checks report a lesson that violates them.

Each test writes a small repository with one lesson and one violation and
runs the check that tests/lessons runs on this repository. The unchanged
lesson passes every check, so a reported violation comes from the violation
and not from the test setup.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from support import lesson_checks
from support.checks import output, run_check
from support.site_checks import Violation

LESSON = "site/lessons/mechanics/01-sample"

_OUTCOMES = (
    "  outcomes:\n    - Step a position forward in time\n"
    "    - Check the step against the exact solution\n"
)

_VALID = """\
---
title: "Sample lesson"
description: "A lesson that follows the format."
lesson:
  id: sample
  strand: mechanics
  order: 1
  difficulty: 1
  course: mechanics
  methods: [simulation]
  outcomes:
    - Step a position forward in time
    - Check the step against the exact solution
  related: []
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
            "site/references.yaml": "references: []\n",
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
        *lesson_checks.check_lean_modules(repository),
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
        ("  course: mechanics\n", "lesson.course"),
        ("  methods: [simulation]\n", "lesson.methods"),
        (_OUTCOMES, "lesson.outcomes"),
        ("  related: []\n", "lesson.related"),
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
        ("  methods: [simulation]\n", "  methods: simulation\n"),
        ("  course: mechanics\n", "  course: [mechanics]\n"),
        ("  related: []\n", "  related: [Not An Id]\n"),
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
        "methods-not-a-list",
        "course-not-text",
        "related-not-an-id",
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


def test_lean_modules_match_the_modules_the_page_shows(make_repository: Repository):
    module = "PhysicsByConstruction.Mechanics.Kinematics"
    front = f"  difficulty: 1\n  lean-modules: [{module}]\n"
    shown = 'Introduction.\n\n`lean_excerpt("' + module + '", "x")`\n'
    files = {"lean/PhysicsByConstruction/Mechanics/Kinematics.lean": "-- lean\n"}
    change = {"  difficulty: 1\n": front, "Introduction.\n": shown}

    assert lesson_checks.check_lean_modules(make_repository(change, files=files)) == []

    # Listed, but the page shows nothing of it.
    only_listed = make_repository({"  difficulty: 1\n": front}, files=files)
    assert "does not show" in details(lesson_checks.check_lean_modules(only_listed))


def test_lean_module_that_is_shown_but_not_listed_is_reported(
    make_repository: Repository,
):
    shown = "Introduction.\n\n`PhysicsByConstruction.Mechanics.Kinematics`\n"
    repository = make_repository({"Introduction.\n": shown})

    violations = lesson_checks.check_lean_modules(repository)

    assert rules(violations) == {"lean-module"}
    assert "does not list" in details(violations)


def test_lean_module_without_a_file_is_reported(make_repository: Repository):
    module = "PhysicsByConstruction.Mechanics.Missing"
    repository = make_repository(
        {
            "  difficulty: 1\n": f"  difficulty: 1\n  lean-modules: [{module}]\n",
            "Introduction.\n": f"Introduction.\n\n`{module}`\n",
        }
    )

    violations = lesson_checks.check_lean_modules(repository)

    assert rules(violations) == {"lean-module"}
    assert "does not exist" in details(violations)


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


@pytest.mark.parametrize(
    "old, new, expected",
    [
        ("  course: mechanics\n", "  course: optics\n", "not a course"),
        ("  methods: [simulation]\n", "  methods: []\n", "names no method"),
        ("  methods: [simulation]\n", "  methods: [magic]\n", "not a method"),
        (
            "  methods: [simulation]\n",
            "  methods: [simulation, simulation]\n",
            "twice",
        ),
        (_OUTCOMES, "  outcomes:\n    - One only\n", "has 1 outcomes"),
        (
            _OUTCOMES,
            "  outcomes:\n" + "".join(f"    - Outcome {n}\n" for n in range(6)),
            "has 6 outcomes",
        ),
        ("  related: []\n", "  related: [gravity]\n", "not the id of any lesson"),
        ("  related: []\n", "  related: [sample]\n", "lists itself"),
    ],
    ids=[
        "unknown-course",
        "no-method",
        "unknown-method",
        "method-twice",
        "one-outcome",
        "six-outcomes",
        "related-does-not-exist",
        "related-is-itself",
    ],
)
def test_facets_outside_the_rules_are_reported_with_the_path(
    make_repository: Repository, old: str, new: str, expected: str
):
    repository = make_repository({old: new})

    assert lesson_checks.check_metadata(repository) == []
    violations = lesson_checks.check_path(repository)
    assert rules(violations) == {"path"}
    assert expected in details(violations)


def test_related_lesson_that_is_a_prerequisite_is_reported(
    make_repository: Repository,
):
    files = second_lesson(prerequisites="[sample]")
    (path,) = files
    files[path] = files[path].replace("  related: []\n", "  related: [sample]\n")

    violations = lesson_checks.check_path(make_repository(files=files))

    assert rules(violations) == {"path"}
    assert "already a prerequisite" in details(violations)


def test_related_lesson_that_exists_and_is_not_a_prerequisite_passes(
    make_repository: Repository,
):
    # Related links run from the prerequisite side: sample links its extension.
    repository = make_repository(
        {"  related: []\n": "  related: [second]\n"}, files=second_lesson()
    )

    assert lesson_checks.check_path(repository) == []


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


# --- Format 2 -----------------------------------------------------------------

_REGISTER = """\
references:
  - key: euler-error
    concept: Error of explicit Euler
    url: https://example.org/euler
    title: Euler error
    author: A. Author
    section: Section 2
    role: derivation
    statement: The global error is first order.
    alternatives: Another page was compared and adds nothing.
    lessons: [sample]
    last-checked: 2026-10-09
    licence: None stated.
"""

# The valid lesson turned into a lesson of format 2.
_FORMAT_2 = {
    "  related: []\n": "  related: []\n  format: 2\n",
    "Introduction.\n": "Introduction.\n",
    "#| label: fig-line\n": "#| label: fig-line\n#| fig-status: simulated\n",
    "The position changes at the rate $v$.\n": (
        "[The position changes at the rate $v$.]"
        '{.claim type="numerically-verified" evidence="fig-line"}\n'
        "\n"
        '::: {.go-deeper ref="euler-error"}\n'
        "It derives the error step by step.\n"
        ":::\n"
    ),
    "## Exercises\n": (
        "## Limits\n\nThe model has one dimension.\n\n"
        "::: {.exercise .self-check}\nWhy one dimension?\n\n"
        "::: {.solution}\nBecause the particle has one coordinate.\n:::\n:::\n\n"
        "## Exercises\n"
    ),
}


@pytest.fixture
def make_format_2(make_repository: Repository) -> Repository:
    def make(change: dict[str, str] | None = None, **keywords: Any) -> Path:
        merged = dict(_FORMAT_2)
        for old, new in (change or {}).items():
            for key in merged:
                if old in merged[key]:
                    merged[key] = merged[key].replace(old, new)
                    break
            else:
                merged[old] = new
        files = {"site/references.yaml": _REGISTER, **keywords.pop("files", {})}
        return make_repository(merged, files=files, **keywords)

    return make


def format_2_checks(repository: Path) -> list[Violation]:
    return [
        *lesson_checks.check_format_2(repository),
        *lesson_checks.check_references(repository),
        *lesson_checks.check_figures(repository),
        *lesson_checks.check_sections(repository),
        *lesson_checks.check_metadata(repository),
    ]


def test_a_lesson_of_format_2_that_follows_the_format_passes(
    make_format_2: Repository,
):
    assert format_2_checks(make_format_2()) == []


def test_a_lesson_of_format_1_needs_none_of_format_2(make_repository: Repository):
    repository = make_repository()

    assert lesson_checks.check_format_2(repository) == []
    assert lesson_checks.check_references(repository) == []


def test_an_unknown_format_is_reported(make_repository: Repository):
    violations = lesson_checks.check_metadata(
        make_repository({"  related: []\n": "  related: []\n  format: 3\n"})
    )

    assert "lesson.format" in details(violations)


@pytest.mark.parametrize(
    "change, rule, text",
    [
        ({"## Limits\n\nThe model has one dimension.\n\n": ""}, "limits", "limits"),
        (
            {"## Limits\n\nThe model has one dimension.\n": "## Limits\n"},
            "limits",
            "limits",
        ),
        (
            {
                "## Exercises\n": "::: {.exercise .self-check}\nAgain?\n\n"
                "::: {.solution}\nYes.\n:::\n:::\n\n## Exercises\n"
            },
            "self-check",
            "2 self-checks",
        ),
        ({".exercise .self-check": ".self-check"}, "self-check", "'.exercise'"),
        (
            {'type="numerically-verified"': 'type="plausible"'},
            "claim-type",
            "plausible",
        ),
        ({'ref="euler-error"': 'ref="unknown-key"'}, "reference-key", "unknown-key"),
        ({"#| fig-status: simulated\n": ""}, "figure-status", "fig-status"),
        (
            {"#| fig-status: simulated\n": "#| fig-status: nice\n"},
            "figure-status",
            "fig-status",
        ),
        (
            {"A straight line that rises": "A line with slope 0.5 that rises"},
            "typed-number",
            "0.5",
        ),
        (
            {"Because the particle has one coordinate.": "The error is 0.05 m."},
            "typed-number",
            "0.05",
        ),
        (
            {"Introduction.\n": "See https://example.org/page for more.\n"},
            "raw-url",
            "https://",
        ),
    ],
)
def test_a_violation_of_format_2_is_reported(
    make_format_2: Repository, change: dict[str, str], rule: str, text: str
):
    violations = format_2_checks(make_format_2(change))

    assert rule in rules(violations), details(violations)
    assert text in details(violations)


def test_given_values_and_math_are_not_hand_typed_numbers(make_format_2: Repository):
    repository = make_format_2(
        {
            "Introduction.\n": "The start is [2 m]{.given} and $x_0 = 1$.\n\n"
            "::: {.exercise}\nA ball falls for 3 s.\n\n"
            "::: {.solution}\nIt falls.\n:::\n:::\n"
        }
    )

    assert "typed-number" not in rules(format_2_checks(repository))


@pytest.mark.parametrize(
    "sentence, reported",
    [
        ("The error is 0.05 m.\n", True),
        ("The error is `{python} position` m.\n", False),
    ],
)
def test_a_computed_value_in_prose_is_reported_an_inline_expression_is_not(
    make_format_2: Repository, sentence: str, reported: bool
):
    repository = make_format_2({"Introduction.\n": sentence})

    violations = lesson_checks.check_format_2(repository)

    assert ("typed-number" in rules(violations)) is reported


@pytest.mark.parametrize(
    "change, text",
    [
        ({"    lessons: [sample]\n": ""}, "no field 'lessons'"),
        ({"    licence: None stated.\n": ""}, "no field 'licence'"),
        ({"    role: derivation\n": "    role: blog\n"}, "'role'"),
        ({"https://example.org": "http://example.org"}, "https://"),
        ({"    lessons: [sample]\n": "    lessons: []\n"}, "'lessons' is []"),
        ({"2026-10-09": "yesterday"}, "'last-checked'"),
        ({"    section: Section 2\n": "    section: ''\n"}, "'section'"),
    ],
)
def test_a_register_entry_that_breaks_the_schema_is_reported(
    make_format_2: Repository, change: dict[str, str], text: str
):
    register = _REGISTER
    for old, new in change.items():
        assert old in register
        register = register.replace(old, new)

    violations = lesson_checks.check_references(
        make_format_2(files={"site/references.yaml": register})
    )

    assert text in details(violations), details(violations)


def test_an_entry_that_no_lesson_uses_is_reported_unless_it_is_reserved(
    make_format_2: Repository,
):
    unused = _REGISTER + _REGISTER.replace("euler-error", "other").split("\n", 1)[1]
    # The second entry names the lesson, but the lesson does not use it.
    reserved = unused + "    reserved: For the lesson on integrators.\n"

    reported = lesson_checks.check_references(
        make_format_2(files={"site/references.yaml": unused})
    )
    accepted = lesson_checks.check_references(
        make_format_2(files={"site/references.yaml": reserved})
    )

    assert "'other' is used by no lesson" in details(reported)
    assert "used by no lesson" not in details(accepted)


def test_a_reserved_entry_that_lists_lessons_is_reported(make_format_2: Repository):
    unused = _REGISTER + _REGISTER.replace("euler-error", "other").split("\n", 1)[1]
    reserved = unused + "    reserved: For the lesson on integrators.\n"

    violations = lesson_checks.check_references(
        make_format_2(files={"site/references.yaml": reserved})
    )

    assert "'other' is reserved, so its 'lessons' must be empty" in details(violations)


def test_a_missing_register_is_reported(make_format_2: Repository):
    repository = make_format_2()
    (repository / "site/references.yaml").unlink()

    violations = lesson_checks.check_references(repository)

    assert "the register is missing" in details(violations)


def test_a_block_of_printed_numbers_in_a_built_page_is_reported(
    make_format_2: Repository, tmp_path: Path
):
    repository = make_format_2()
    page = tmp_path / "built" / "lessons/mechanics/01-sample/index.html"
    page.parent.mkdir(parents=True)

    def build(printed: str) -> list[Violation]:
        page.write_text(
            '<div class="cell-output cell-output-stdout"><pre><code>'
            f"{printed}</code></pre></div>"
        )
        return lesson_checks.check_console_blocks(repository, tmp_path / "built")

    assert build("0.1 2.5\n0.2 5.0\n0.3 7.5\n") != []
    assert build("largest time step: 12.3 microseconds\n") == []
