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

_GLOSSARY = """\
entries:
  - term: Calculus
    definition: The derivative is a rate of change. The integral accumulates it.
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
            "site/glossary.yaml": _GLOSSARY,
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
        *lesson_checks.check_experiments(repository),
        *lesson_checks.check_figures(repository),
        *lesson_checks.check_committed_files(repository),
        *lesson_checks.check_atlas(repository),
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
        ("  difficulty: 1\n", "  difficulty: 1\n  experiment: [a, b]\n"),
        # The one page class the format admits, and only it.
        ("lesson:\n", "body-classes: wide\nlesson:\n"),
        ("lesson:\n", "body-classes: pbc-reading-column wide\nlesson:\n"),
        ("lesson:\n", "body-classes: [pbc-reading-column]\nlesson:\n"),
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
        "experiment-not-text",
        "other-body-class",
        "body-class-and-another",
        "body-classes-not-text",
    ],
)
def test_invalid_metadata_is_reported(make_repository: Repository, old: str, new: str):
    violations = lesson_checks.check_metadata(make_repository({old: new}))

    assert rules(violations) == {"metadata"}


def test_the_reading_column_opt_in_is_accepted(make_repository: Repository):
    repository = make_repository(
        {"lesson:\n": "body-classes: pbc-reading-column\nlesson:\n"}
    )

    assert lesson_checks.check_metadata(repository) == []


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


# --- Experiments --------------------------------------------------------------

_MODULE = "pbc.mechanics.experiments.sample"
_DECLARED = {
    "  difficulty: 1\n": f"  difficulty: 1\n  experiment: {_MODULE}\n",
    "## Reproduce this\n": "## Run this experiment {#reproduce-this}\n",
    "```{python}\n#| echo: false\nlesson_header()\n": "```{python}\n#| echo: false\n"
    "from pbc.mechanics.experiments import sample as experiment\n\n"
    "lesson_header()\n",
}
_EXPERIMENT_FILES = {
    "src/pbc/mechanics/experiments/sample.py": "def run(): ...\n",
    "tests/unit/test_sample_experiment.py": "def test_run(): ...\n",
}


def test_a_declared_experiment_that_follows_the_contract_passes(
    make_repository: Repository,
):
    repository = make_repository(_DECLARED, files=_EXPERIMENT_FILES)

    assert all_checks(repository) == []


@pytest.mark.parametrize(
    "heading",
    [
        "## Reproduce this {#reproduce-this}\n",
        "## Check this proof {#reproduce-this}\n",
    ],
    ids=["superseded", "another-kind"],
)
def test_the_last_section_is_headed_by_the_activity_of_the_lesson(
    make_repository: Repository, heading: str
):
    declared = {**_DECLARED, "## Reproduce this\n": heading}
    repository = make_repository(declared, files=_EXPERIMENT_FILES)

    violations = lesson_checks.check_experiments(repository)

    assert rules(violations) == {"experiment"}
    assert "a lesson of this kind is headed 'Run this experiment'" in details(
        violations
    )


def test_a_lesson_without_an_experiment_fails_only_once_it_is_required(
    make_repository: Repository,
):
    repository = make_repository()

    assert lesson_checks.check_experiments(repository) == []
    violations = lesson_checks.check_experiments(repository, required=True)
    assert rules(violations) == {"experiment"}
    assert "declares no 'lesson.experiment'" in details(violations)


@pytest.mark.parametrize(
    "change, files, message",
    [
        (
            {f"experiment: {_MODULE}": "experiment: pbc.mechanics.sample"},
            _EXPERIMENT_FILES,
            "this lesson's module is pbc.mechanics.experiments.sample",
        ),
        (
            {},
            {"tests/unit/test_sample_experiment.py": "def test_run(): ...\n"},
            "has no file src/pbc/mechanics/experiments/sample.py",
        ),
        (
            {},
            {"src/pbc/mechanics/experiments/sample.py": "def run(): ...\n"},
            "has no unit test tests/unit/test_sample_experiment.py",
        ),
        (
            {"from pbc.mechanics.experiments import sample as experiment\n": ""},
            _EXPERIMENT_FILES,
            "no executed cell of the page imports its experiment",
        ),
        (
            {f"experiment: {_MODULE}": "experiment: ./scripts/check-lean.sh"},
            _EXPERIMENT_FILES,
            "only a lesson whose methods are [lean] may declare",
        ),
    ],
    ids=["other-module", "no-module", "no-test", "not-imported", "lean-elsewhere"],
)
def test_an_experiment_outside_the_contract_is_reported(
    make_repository: Repository, change: dict, files: dict, message: str
):
    declared = {**_DECLARED}
    for old, new in change.items():
        for key, value in declared.items():
            declared[key] = value.replace(old, new)
    repository = make_repository(declared, files=files)

    violations = lesson_checks.check_experiments(repository)

    assert rules(violations) == {"experiment"}
    assert message in details(violations)


_LEAN_ONLY = {
    "  methods: [simulation]\n": "  methods: [lean]\n"
    "  experiment: ./scripts/check-lean.sh\n",
    "## Reproduce this\n": "## Check this proof {#reproduce-this}\n",
}
_FIGURE_CELL = """```{python}
#| label: fig-line
#| fig-cap: "A line."
#| fig-alt: "A straight line that rises from the origin."
import matplotlib.pyplot as plt

plt.plot([0.0, 1.0], [0.0, position])
plt.show()
```
"""


def test_a_lean_only_lesson_without_a_figure_may_declare_the_proof_check(
    make_repository: Repository,
):
    repository = make_repository({**_LEAN_ONLY, _FIGURE_CELL: ""})

    assert lesson_checks.check_experiments(repository, required=True) == []


def test_a_lean_only_lesson_that_draws_a_figure_declares_its_module(
    make_repository: Repository,
):
    violations = lesson_checks.check_experiments(make_repository(_LEAN_ONLY))

    assert rules(violations) == {"experiment"}
    assert "declares its experiment module" in details(violations)


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


_STATEMENT = "Where is the particle after one second?\n\n"
_SOLUTION = "::: {.solution}\nAt `{python} position` m.\n:::\n"


def _hinted(*hints: str, after: bool = False) -> dict[str, str]:
    block = "".join(f"::: {{.hint}}\n{hint}\n:::\n\n" for hint in hints)
    if after:
        return {_SOLUTION: _SOLUTION + "\n" + block.rstrip("\n") + "\n"}
    return {_STATEMENT: _STATEMENT + block}


def test_hints_before_the_solution_pass(make_repository: Repository):
    repository = make_repository(
        _hinted("Use the rate.", "Multiply the rate by the time.")
    )

    assert lesson_checks.check_sections(repository) == []


def test_a_hint_may_repeat_a_number_of_the_statement(make_repository: Repository):
    repository = make_repository(
        {
            _STATEMENT: "Where is the particle after 1 s?\n\n"
            "::: {.hint}\nWhat is the rate over 1 s?\n:::\n\n"
        }
    )

    assert lesson_checks.check_sections(repository) == []


@pytest.mark.parametrize(
    "hints, after, text",
    [
        (("Use the rate.",), True, "after the '.solution'"),
        (("a", "b", "c", "d"), False, "at most 3"),
        (("It is 2.0 m.",), False, "number"),
        (("It is `2.0` m.",), False, "number"),
        (("It is `{2.0}` m.",), False, "number"),
        (("```{python}\nprint(1)\n```",), False, "holds code"),
        (("Compute `{python} position` first.",), False, "holds code"),
        (('::: {.go-deeper ref="x"}\nRead.\n:::',), False, "go-deeper"),
    ],
    ids=[
        "after-solution",
        "four-hints",
        "number",
        "code-span",
        "brace-code-span",
        "cell",
        "inline",
        "go-deeper",
    ],
)
def test_a_misplaced_or_leaking_hint_is_reported(
    make_repository: Repository, hints: tuple[str, ...], after: bool, text: str
):
    violations = lesson_checks.check_sections(
        make_repository(_hinted(*hints, after=after))
    )

    assert rules(violations) == {"sections"}
    assert text in details(violations)


def test_a_hint_outside_an_exercise_is_reported(make_repository: Repository):
    violations = lesson_checks.check_sections(
        make_repository(
            {"Introduction.\n": "Introduction.\n\n::: {.hint}\nA stray hint.\n:::\n"}
        )
    )

    assert "outside an '.exercise'" in details(violations)


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


def test_named_replay_fixtures_of_a_lesson_are_accepted(make_repository: Repository):
    repository = make_repository(
        files={
            f"{LESSON}/replay-false.json": '{"steps": []}',
            f"{LESSON}/replay-open.json": '{"steps": []}',
        }
    )
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "--message", "Lesson with two recordings")

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


# --- Interface artwork under site/assets (ADR 018 decision 2) -----------------

_MARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"/>\n'
_AUTHORED = (
    "  {name}:\n"
    "    author: A. Author\n"
    "    licence: CC-BY-4.0\n"
    "    source: drawn for the project\n"
)


def register(*entries: str) -> dict[str, str]:
    """The provenance register of site/assets with the given entries."""
    return {lesson_checks.ASSET_REGISTER: "assets:\n" + "".join(entries)}


def authored(name: str) -> str:
    return _AUTHORED.format(name=name)


def test_registered_svg_under_site_assets_is_accepted(make_repository: Repository):
    repository = make_repository(
        files={"site/assets/mark.svg": _MARK, **register(authored("mark.svg"))}
    )
    git(repository, "add", "--all")
    git(repository, "commit", "--quiet", "--message", "The mark and its entry")

    assert lesson_checks.check_committed_files(repository) == []
    assert lesson_checks.check_asset_sources(repository) == []


def test_unregistered_svg_under_site_assets_is_reported(make_repository: Repository):
    repository = make_repository(files={"site/assets/mark.svg": _MARK})

    violations = lesson_checks.check_committed_files(repository)

    assert [(violation.rule, violation.page) for violation in violations] == [
        ("committed-artifact", "site/assets/mark.svg")
    ]
    assert rules(lesson_checks.check_asset_sources(repository)) == {"asset-source"}


@pytest.mark.parametrize(
    "entry",
    [
        "  mark.svg:\n    author: A. Author\n    source: drawn\n",
        "  mark.svg:\n    licence: CC-BY-4.0\n    source: drawn\n",
        '  mark.svg:\n    author: ""\n    licence: CC-BY-4.0\n',
        "  mark.svg:\n    module: pbc.authoring.design\n",
    ],
    ids=["no-licence", "no-author", "empty-author", "generated"],
)
def test_svg_registered_without_author_and_licence_is_reported(
    make_repository: Repository, entry: str
):
    repository = make_repository(
        files={"site/assets/mark.svg": _MARK, **register(entry)}
    )

    assert rules(lesson_checks.check_committed_files(repository)) == {
        "committed-artifact"
    }


@pytest.mark.parametrize(
    "path", ["site/assets/mark.png", "site/assets/mark.webp", "site/assets/mark.gif"]
)
def test_raster_under_site_assets_is_reported_even_when_registered(
    make_repository: Repository, path: str
):
    name = path.removeprefix("site/assets/")
    repository = make_repository(files={path: "raster", **register(authored(name))})

    violations = lesson_checks.check_committed_files(repository)

    assert [(violation.rule, violation.page) for violation in violations] == [
        ("committed-artifact", path)
    ]
    assert "not an SVG" in details(lesson_checks.check_asset_sources(repository))


@pytest.mark.parametrize("path", ["site/mark.svg", "src/pbc/mark.svg"])
def test_svg_outside_site_assets_is_reported_even_when_registered(
    make_repository: Repository, path: str
):
    repository = make_repository(
        files={
            "site/assets/mark.svg": _MARK,
            path: _MARK,
            **register(authored("mark.svg")),
        }
    )

    violations = lesson_checks.check_committed_files(repository)

    assert [(violation.rule, violation.page) for violation in violations] == [
        ("committed-artifact", path)
    ]


def test_register_entry_that_leaves_site_assets_is_reported(
    make_repository: Repository,
):
    repository = make_repository(
        files={"site/mark.svg": _MARK, **register(authored("../mark.svg"))}
    )

    assert rules(lesson_checks.check_committed_files(repository)) == {
        "committed-artifact"
    }
    assert rules(lesson_checks.check_asset_sources(repository)) == {"asset-source"}


def test_no_register_and_no_svg_passes_the_asset_source_rule(
    make_repository: Repository,
):
    assert lesson_checks.check_asset_sources(make_repository()) == []


def test_generated_svg_entry_naming_a_module_that_imports_is_accepted(
    make_repository: Repository,
):
    repository = make_repository(
        files=register("  plot.svg:\n    module: pbc.authoring.design\n")
    )

    assert lesson_checks.check_asset_sources(repository) == []


@pytest.mark.parametrize(
    "files, problem",
    [
        (register(authored("mark.svg")), "no file"),
        (
            {
                "site/assets/mark.svg": _MARK,
                **register(authored("mark.svg") + "    year: 2026\n"),
            },
            "'year'",
        ),
        (register("  plot.svg:\n    module: pbc.no_such_module\n"), "import"),
        (
            {
                "site/assets/mark.svg": _MARK,
                **register(
                    "  mark.svg:\n    module: pbc.authoring.design\n"
                    "    author: A. Author\n    licence: CC-BY-4.0\n"
                ),
            },
            "either",
        ),
        ({lesson_checks.ASSET_REGISTER: "- mark.svg\n"}, "mapping"),
        ({lesson_checks.ASSET_REGISTER: "assets: [mark.svg\n"}, "YAML"),
    ],
    ids=[
        "entry-without-file",
        "unknown-field",
        "module-not-importable",
        "authored-and-generated",
        "not-a-mapping",
        "not-yaml",
    ],
)
def test_register_that_breaks_its_format_is_reported(
    make_repository: Repository, files: dict[str, str], problem: str
):
    violations = lesson_checks.check_asset_sources(make_repository(files=files))

    assert rules(violations) == {"asset-source"}
    assert problem in details(violations)


# --- The map manifest ------------------------------------------------------------


def test_a_map_manifest_that_breaks_a_rule_is_reported(make_repository: Repository):
    manifest = (
        "concepts:\n"
        "  - {id: motion, area: mechanics, position: [1, 1], slots: [M1],\n"
        "     explanation: Motion., title: Motion}\n"
        "connections: []\n"
    )
    violations = lesson_checks.check_atlas(
        make_repository(files={"site/atlas.yaml": manifest})
    )

    assert rules(violations) == {"atlas"}
    assert "'title' is held by the curriculum file" in details(violations)
    assert "'M1' is not a slot of the curriculum" in details(violations)


# --- The check as verification runs it ------------------------------------------


def test_verification_passes_a_lesson_that_follows_the_format(
    make_repository: Repository,
):
    repository = make_repository(
        _DECLARED,
        files={**_EXPERIMENT_FILES, f"{LESSON}/replay.json": '{"messages": []}'},
    )

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


_CHOICES = (
    "::: {.choices}\n"
    "::: {.choice}\nBecause of friction.\n\n::: {.feedback}\nNo.\n:::\n:::\n\n"
    '::: {.choice correct="true"}\nBecause of the coordinate.\n\n'
    "::: {.feedback}\nYes.\n:::\n:::\n"
    ":::\n\n"
)


def with_choices(markup: str) -> dict[str, str]:
    return {"Why one dimension?\n\n": "Why one dimension?\n\n" + markup}


def test_a_self_check_with_choices_that_follow_the_rules_passes(
    make_format_2: Repository,
):
    assert format_2_checks(make_format_2(with_choices(_CHOICES))) == []


@pytest.mark.parametrize(
    "markup, text",
    [
        (_CHOICES.replace(' correct="true"', ""), "0 correct choices"),
        (
            _CHOICES.replace("::: {.choice}", '::: {.choice correct="true"}'),
            "2 correct",
        ),
        (_CHOICES.replace("::: {.feedback}\nNo.\n:::\n", ""), "no '.feedback'"),
        (
            _CHOICES.replace(
                "::: {.choice}\nBecause of friction.", "Stray.\n\n::: {.choice}\nF."
            ),
            "nothing else",
        ),
        (_CHOICES.split("::: {.choice correct")[0] + ":::\n\n", "two or more"),
        ('correct="maybe"'.join(_CHOICES.split('correct="true"')), "'true' or 'false'"),
    ],
)
def test_a_self_check_with_malformed_choices_is_reported(
    make_format_2: Repository, markup: str, text: str
):
    violations = lesson_checks.check_sections(make_format_2(with_choices(markup)))

    assert text in details(violations)


def test_choices_outside_a_self_check_are_reported(make_format_2: Repository):
    limits = "## Limits\n\nThe model has one dimension.\n"
    change = {limits: limits + "\n" + _CHOICES}

    assert "outside a '.self-check'" in details(
        lesson_checks.check_sections(make_format_2(change))
    )


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
            {
                "#| fig-status: simulated\n": "#| fig-status: simulated\n"
                "#| fig-dataset: gw150914-strain\n"
            },
            "figure-dataset",
            "cannot be 'simulated'",
        ),
        (
            {
                "#| fig-status: simulated\n": "#| fig-status: processed\n"
                "#| fig-dataset: no-such-dataset\n"
            },
            "figure-dataset",
            "no card",
        ),
        (
            {
                "plt.plot([0.0, 1.0], [0.0, position])\n": (
                    "from pbc.data.touchstone import read_touchstone\n"
                    'plt.plot(read_touchstone("x.s2p").frequency)\n'
                )
            },
            "figure-dataset",
            "names none",
        ),
        (
            {
                "#| fig-status: simulated\n": "#| fig-status: processed\n"
                "#| fig-model-of: gw150914-strain\n"
            },
            "figure-dataset",
            "is 'simulated', not 'processed'",
        ),
        (
            {
                "#| fig-status: simulated\n": "#| fig-status: simulated\n"
                "#| fig-model-of: no-such-dataset\n"
            },
            "figure-dataset",
            "no card",
        ),
        (
            {
                "#| fig-status: simulated\n": "#| fig-status: processed\n"
                "#| fig-dataset: gw150914-strain\n"
                "#| fig-model-of: gw150914-strain\n"
            },
            "figure-dataset",
            "both 'fig-dataset' and 'fig-model-of'",
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


def test_a_figure_of_a_dataset_with_a_status_its_card_allows_passes(
    make_format_2: Repository,
):
    repository = make_format_2(
        {
            "#| fig-status: simulated\n": "#| fig-status: processed\n"
            "#| fig-dataset: gw150914-strain\n"
        }
    )

    assert "figure-dataset" not in rules(format_2_checks(repository))


# The figure cell of the lesson plots 'position' and is labelled 'simulated',
# without 'fig-dataset'. Each of these cells, put before it, makes 'position'
# a measurement of a registered dataset; none of them is named in the figure
# cell itself.
_READS_A_SAMPLE = (
    "from pbc.data import SAMPLES_DIR\n"
    "from pbc.data.gwosc import read_strain\n"
    "\n"
    'strain = read_strain(SAMPLES_DIR / "gw150914-strain" / "H1.hdf5")\n'
)
_DATA_BEFORE_THE_FIGURE = {
    "a name bound in an earlier cell": _READS_A_SAMPLE
    + "position = float(strain.strain[0])\n",
    "a module under another name": (
        "import pbc.data.gwosc as g\n"
        "from pbc import data as d\n"
        "\n"
        'position = g.read_strain(d.SAMPLES_DIR / "x.hdf5").strain[0]\n'
    ),
    "a function of the lesson": _READS_A_SAMPLE
    + "def first():\n    return float(strain.strain[0])\n\nposition = first()\n",
    "a loop and a container": _READS_A_SAMPLE
    + "values = []\nfor sample in strain.strain:\n    values.append(sample)\n"
    "position = values[0]\n",
    "a path written out": (
        "import numpy as np\n"
        "\n"
        'position = np.loadtxt("../../data/samples/aalborg-submerged-bar/a.csv")[0]\n'
    ),
    "a star import of the package": (
        "import numpy as np\n"
        "from pbc.data import *\n"
        "\n"
        'position = np.loadtxt(SAMPLES_DIR / "aalborg-submerged-bar" / "a.csv")[0]\n'
    ),
    "a reference loader": (
        "from pbc.data import DOWNLOADS_DIR\n"
        "from pbc.data.reference import gw150914\n"
        "\n"
        'position = gw150914.load(DOWNLOADS_DIR)["H1"].strain[0]\n'
    ),
}


@pytest.mark.parametrize(
    "cell", _DATA_BEFORE_THE_FIGURE.values(), ids=list(_DATA_BEFORE_THE_FIGURE)
)
def test_a_simulated_figure_made_from_a_measured_dataset_is_refused(
    make_format_2: Repository, cell: str
):
    repository = make_format_2({"position = 1.0 + 2.0 * 0.5\n": cell})

    violations = format_2_checks(repository)

    assert "figure-dataset" in rules(violations), details(violations)
    assert "'fig-line' is made from a dataset" in details(violations)


def test_a_figure_drawn_on_axes_that_received_data_is_refused(
    make_format_2: Repository,
):
    repository = make_format_2(
        {
            "position = 1.0 + 2.0 * 0.5\n": _READS_A_SAMPLE
            + "import matplotlib.pyplot as plt\n\nposition = 2.0\n"
            "fig, ax = plt.subplots()\nax.plot(strain.strain)\n",
            "plt.plot([0.0, 1.0], [0.0, position])\nplt.show()\n": "fig\n",
        }
    )

    assert "figure-dataset" in rules(format_2_checks(repository))


def test_naming_the_dataset_of_such_a_figure_brings_the_card_rule(
    make_format_2: Repository,
):
    cell = _DATA_BEFORE_THE_FIGURE["a name bound in an earlier cell"]
    named = make_format_2(
        {
            "position = 1.0 + 2.0 * 0.5\n": cell,
            "#| fig-status: simulated\n": "#| fig-status: simulated\n"
            "#| fig-dataset: gw150914-strain\n",
        }
    )

    assert "cannot be 'simulated'" in details(format_2_checks(named))


_EXPERIMENT_OF_DATA = """\
from functools import partial

from pbc.data import SAMPLES_DIR
from pbc.data.gwosc import read_strain
from pbc.experiment import Experiment


def draw_line(values):
    return values


def draw_model(level):
    return level


def model(experiment: Experiment):
    return 1.0


def run():
    experiment = Experiment()
    strain = read_strain(SAMPLES_DIR / "gw150914-strain" / "H1.hdf5")
    # The record receives data; what a function given the record returns is
    # not data because of it.
    experiment.number("first", strain.strain[0])
    level = model(experiment)
    experiment.figure("fig-line", partial(draw_line, strain.strain))
    experiment.figure("fig-model", partial(draw_model, level))
    return experiment
"""


def _shows(label: str) -> dict[str, str]:
    """A lesson whose figure cell shows ``label`` of its experiment, which
    reads a sample for one figure and draws the other from nothing."""
    return {
        **_DECLARED,
        "from pbc.mechanics.experiments import sample as experiment\n\n": (
            "from pbc.mechanics.experiments import sample as experiment\n\n"
            "result = experiment.run()\n"
        ),
        "import matplotlib.pyplot as plt\n\n"
        "plt.plot([0.0, 1.0], [0.0, position])\nplt.show()\n": (
            f'result.show("{label}")\n'
        ),
    }


def _experiment_files() -> dict[str, str]:
    return {
        **_EXPERIMENT_FILES,
        "src/pbc/mechanics/experiments/sample.py": _EXPERIMENT_OF_DATA,
    }


def test_a_figure_its_experiment_draws_from_a_dataset_must_name_it(
    make_format_2: Repository,
):
    repository = make_format_2(_shows("fig-line"), files=_experiment_files())

    violations = format_2_checks(repository)

    assert "'fig-line' is made from a dataset" in details(violations)


def test_a_figure_its_experiment_draws_without_data_needs_no_dataset(
    make_format_2: Repository,
):
    # The experiment reads a sample for another figure; this one is simulated.
    repository = make_format_2(_shows("fig-model"), files=_experiment_files())

    assert "figure-dataset" not in rules(format_2_checks(repository))


def test_a_figure_its_experiment_does_not_record_is_reported(
    make_format_2: Repository,
):
    repository = make_format_2(_shows("fig-missing"), files=_experiment_files())

    assert "which its experiment does not record" in details(
        format_2_checks(repository)
    )


def _figure_of_the_flume(status: str, artifact: str | None) -> dict[str, str]:
    """The figure names the dataset that holds measurements and a model."""
    options = f"#| fig-status: {status}\n#| fig-dataset: aalborg-submerged-bar\n"
    if artifact is not None:
        options += f"#| fig-artifact: {artifact}\n"
    return {"#| fig-status: simulated\n": options}


@pytest.mark.parametrize(
    ("status", "artifact", "text"),
    [
        ("simulated", "processed-measured", "cannot be 'simulated'"),
        ("processed", "modelled-reference", "cannot be 'processed'"),
        ("simulated", None, "say which one"),
        ("processed", None, "say which one"),
        ("simulated", "raw-measured", "'fig-artifact' names 'raw-measured'"),
    ],
)
def test_the_measurements_of_a_card_with_a_model_cannot_pass_as_simulated(
    make_format_2: Repository, status: str, artifact: str | None, text: str
):
    violations = format_2_checks(make_format_2(_figure_of_the_flume(status, artifact)))

    assert "figure-dataset" in rules(violations), details(violations)
    assert text in details(violations)


@pytest.mark.parametrize(
    ("status", "artifact"),
    [("processed", "processed-measured"), ("simulated", "modelled-reference")],
)
def test_a_figure_of_one_artifact_of_such_a_card_passes(
    make_format_2: Repository, status: str, artifact: str
):
    repository = make_format_2(_figure_of_the_flume(status, artifact))

    assert "figure-dataset" not in rules(format_2_checks(repository))


def test_an_artifact_without_a_dataset_is_reported(make_format_2: Repository):
    repository = make_format_2(
        {
            "#| fig-status: simulated\n": "#| fig-status: simulated\n"
            "#| fig-artifact: modelled-reference\n"
        }
    )

    assert "'fig-artifact' without 'fig-dataset'" in details(
        format_2_checks(repository)
    )


def test_a_figure_of_a_model_fitted_to_a_dataset_declares_it(
    make_format_2: Repository,
):
    cell = _DATA_BEFORE_THE_FIGURE["a name bound in an earlier cell"]
    repository = make_format_2(
        {
            "position = 1.0 + 2.0 * 0.5\n": cell,
            "#| fig-status: simulated\n": "#| fig-status: simulated\n"
            "#| fig-model-of: gw150914-strain\n",
        }
    )

    assert "figure-dataset" not in rules(format_2_checks(repository))


def test_the_tools_of_the_data_package_do_not_make_a_figure_a_data_figure(
    make_format_2: Repository,
):
    repository = make_format_2(
        {
            "position = 1.0 + 2.0 * 0.5\n": (
                "import numpy as np\n"
                "from pbc.data.plotting import series_with_band\n"
                "from pbc.data.series import Series\n"
                "\n"
                'series = Series(np.arange(3.0), np.arange(3.0), "simulation")\n'
                "position = float(series.y[1])\n"
            )
        }
    )

    assert "figure-dataset" not in rules(format_2_checks(repository))


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


# --- The glossary -------------------------------------------------------------


def _glossary_repository(
    make_repository: Repository,
    outside: str = '"Calculus: derivatives"',
    glossary: str = _GLOSSARY,
) -> Path:
    return make_repository(
        {'      - "Calculus"\n': f"      - {outside}\n"},
        files={"site/glossary.yaml": glossary},
    )


def test_outside_prerequisites_that_name_entries_pass_the_glossary_check(
    make_repository: Repository,
):
    assert lesson_checks.check_glossary(_glossary_repository(make_repository)) == []


def test_an_outside_prerequisite_without_an_entry_is_reported(
    make_repository: Repository,
):
    repository = _glossary_repository(make_repository, '"Topology: open sets"')

    messages = [v.detail for v in lesson_checks.check_glossary(repository)]

    assert any("'Topology: open sets' names no glossary entry" in m for m in messages)
    # The entry that no lesson assumes is reported too: nothing links it.
    assert any("'Calculus' is assumed by no lesson" in m for m in messages)


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        ("Derivatives.", None),
        ("One. Two. Three. Four.", "4 sentences"),
        ("No sentence end", "0 sentences"),
    ],
)
def test_an_entry_is_one_to_three_sentences(
    make_repository: Repository, definition: str, expected: str | None
):
    glossary = f"entries:\n  - term: Calculus\n    definition: {definition}\n"
    repository = _glossary_repository(make_repository, glossary=glossary)

    messages = [v.detail for v in lesson_checks.check_glossary(repository)]

    if expected is None:
        assert messages == []
    else:
        assert any(expected in m for m in messages)


def test_an_entry_that_sees_a_missing_lesson_is_reported(make_repository: Repository):
    glossary = _GLOSSARY + "    see: nowhere\n"
    repository = _glossary_repository(make_repository, glossary=glossary)

    messages = [v.detail for v in lesson_checks.check_glossary(repository)]

    assert any("'see' 'nowhere' is not the id of any lesson" in m for m in messages)


def test_a_missing_glossary_is_reported(make_repository: Repository):
    repository = make_repository()
    (repository / "site/glossary.yaml").unlink()

    violations = lesson_checks.check_glossary(repository)

    assert [v.rule for v in violations] == ["glossary"]


# --- The evidence map ---------------------------------------------------------

_CLAIM = '{.claim type="numerically-verified" evidence="fig-line"}'
_THEOREM_FILE = (
    "theorem velocity_after_step (v a t : Real) : v + a * t = v + a * t := rfl\n"
)
_REPLAY = "{}\n"


def evidence_files() -> dict[str, str]:
    return {
        "lean/PhysicsByConstruction/Mechanics/Step.lean": _THEOREM_FILE,
        "data/registry/sample-card.yaml": "id: sample-card\n",
        f"{LESSON}/replay-agent.json": _REPLAY,
    }


def test_claims_with_existing_evidence_pass_the_evidence_check(
    make_format_2: Repository,
):
    repository = make_format_2(
        {
            'evidence="fig-line"': (
                'evidence="fig-line euler-error, velocity_after_step'
                ' sample-card replay-agent"'
            )
        },
        files=evidence_files(),
    )

    assert lesson_checks.check_evidence(repository) == []


@pytest.mark.parametrize(
    "change, text",
    [
        (
            {
                '{.claim type="numerically-verified" evidence="fig-line"}': (
                    '{.claim type="numerically-verified"}'
                )
            },
            "has no 'evidence'",
        ),
        ({'evidence="fig-line"': 'evidence=""'}, "has no 'evidence'"),
        ({'evidence="fig-line"': 'evidence="the table above"'}, "'the', 'table'"),
        ({'evidence="fig-line"': 'evidence="fig-nowhere"'}, "'fig-nowhere'"),
        ({'evidence="fig-line"': 'evidence="no_such_theorem"'}, "'no_such_theorem'"),
        ({'evidence="fig-line"': 'evidence="replay"'}, "'replay'"),
        ({'type="numerically-verified"': 'type="plausible"'}, "no valid type"),
        # A cell that does not run is no evidence.
        (
            {"#| label: fig-line\n": "#| label: fig-line\n#| eval: false\n"},
            "'fig-line'",
        ),
    ],
)
def test_a_claim_without_existing_evidence_is_reported(
    make_format_2: Repository, change: dict[str, str], text: str
):
    violations = lesson_checks.check_evidence(
        make_format_2(change, files=evidence_files())
    )

    assert rules(violations) == {"evidence"}, details(violations)
    assert text in details(violations)


def test_evidence_of_another_lesson_is_not_a_cell_of_this_one(
    make_format_2: Repository,
):
    other = _VALID.replace("id: sample", "id: other").replace("fig-line", "fig-other")
    repository = make_format_2(
        {'evidence="fig-line"': 'evidence="fig-other"'},
        files={**evidence_files(), "site/lessons/mechanics/02-other/index.qmd": other},
    )

    assert "'fig-other'" in details(lesson_checks.check_evidence(repository))


def test_a_claim_in_a_div_is_checked_too(make_format_2: Repository):
    repository = make_format_2(
        {
            "[The position changes at the rate $v$.]"
            '{.claim type="numerically-verified" evidence="fig-line"}\n': (
                '::: {.claim type="numerically-verified"}\n'
                "The position changes at the rate $v$.\n:::\n"
            )
        }
    )

    assert "has no 'evidence'" in details(lesson_checks.check_evidence(repository))
