"""The learning path is derived from lesson front matter, validated, and
rendered with links that work from the page it is shown on."""

import json
import subprocess
from pathlib import Path

import pytest

from pbc.authoring import DIFFICULTIES, STRANDS, LearningPath, learning_path
from pbc.authoring.path import (
    PATH_PAGE,
    Lesson,
    LessonHeader,
    PathOverview,
    lesson_header,
    problems,
    read_lessons,
)


def lesson(
    id: str,
    strand: str = "mechanics",
    order: int = 1,
    prerequisites: tuple[str, ...] = (),
    difficulty: int = 1,
    outside: tuple[str, ...] = (),
) -> Lesson:
    return Lesson(
        page=f"lessons/{strand}/{order:02d}-{id}/index.qmd",
        id=id,
        title=id.capitalize(),
        description="",
        strand=strand,
        order=order,
        difficulty=difficulty,
        prerequisites=prerequisites,
        outside=outside,
    )


def messages(lessons: list[Lesson]) -> list[str]:
    return [f"{problem.page}: {problem.message}" for problem in problems(lessons)]


# Lessons in two strands, given out of path order.
KINEMATICS = lesson("kinematics")
NEWTON = lesson("newton", order=2, prerequisites=("kinematics",), difficulty=2)
ENERGY = lesson("energy", order=3, prerequisites=("newton",), difficulty=2)
PROOF = lesson("proof", strand="lean", order=1, prerequisites=("energy",), difficulty=3)
LESSONS = [PROOF, ENERGY, KINEMATICS, NEWTON]


def test_the_strands_and_the_scale_are_defined_once_in_order():
    assert [strand.id for strand in STRANDS] == [
        "mechanics",
        "agents-llm",
        "agents-abm",
        "lean",
    ]
    assert [difficulty.level for difficulty in DIFFICULTIES] == [1, 2, 3]
    assert all(
        difficulty.title and difficulty.description for difficulty in DIFFICULTIES
    )


# --- Order ---------------------------------------------------------------------


@pytest.fixture
def site(tmp_path: Path) -> Path:
    """A website project with the lessons above as pages."""
    site = tmp_path / "site"
    (site / "_quarto.yml").parent.mkdir()
    (site / "_quarto.yml").write_text("project:\n  type: website\n")
    for item in LESSONS:
        write_lesson(site, item)
    return site


def write_lesson(site: Path, item: Lesson, **front_matter: str) -> Path:
    page = site / item.page
    page.parent.mkdir(parents=True, exist_ok=True)
    lessons = ", ".join(item.prerequisites)
    outside = ", ".join(f'"{text}"' for text in item.outside)
    page.write_text(
        f'---\ntitle: "{item.title}"\n'
        + (f'description: "{item.description}"\n' if item.description else "")
        + f"lesson:\n  id: {item.id}\n  strand: {item.strand}\n"
        f"  order: {item.order}\n  difficulty: {item.difficulty}\n"
        f"  prerequisites:\n    lessons: [{lessons}]\n    outside: [{outside}]\n"
        + "".join(f"{key}: {value}\n" for key, value in front_matter.items())
        + "---\n\nIntroduction.\n"
    )
    return page


def test_path_is_read_from_the_front_matter_of_the_lesson_pages(site: Path):
    path = LearningPath.read(site)

    assert [item.id for item in path.lessons] == [
        "kinematics",
        "newton",
        "energy",
        "proof",
    ]
    assert path.lesson("newton") == NEWTON
    assert path.at_page(NEWTON.page) == NEWTON


def test_description_is_read_when_a_lesson_has_one(site: Path):
    item = lesson("drag", order=4, prerequisites=("energy",))
    write_lesson(site, item, description='"Motion with air drag."')

    assert LearningPath.read(site).lesson("drag").description == "Motion with air drag."


def test_previous_and_next_follow_the_path_across_strands(site: Path):
    path = LearningPath.read(site)

    assert path.previous(KINEMATICS) is None
    assert path.next(KINEMATICS) == NEWTON
    assert path.previous(PROOF) == ENERGY
    assert path.next(PROOF) is None


def test_only_strands_with_a_lesson_are_part_of_the_path(site: Path):
    path = LearningPath.read(site)

    assert [strand.id for strand in path.strands] == ["mechanics", "lean"]
    assert path.in_strand(path.strands[0]) == (KINEMATICS, NEWTON, ENERGY)


def test_a_site_without_lessons_has_an_empty_path(tmp_path: Path):
    (tmp_path / "_quarto.yml").write_text("project:\n  type: website\n")

    assert LearningPath.read(tmp_path).lessons == ()


@pytest.mark.parametrize(
    "text",
    [
        "No front matter.\n",
        "---\ntitle: Lesson\n---\n\nNo lesson mapping.\n",
        "---\ntitle: Lesson\nlesson:\n  id: x\n  strand: mechanics\n---\n",
        "---\ntitle: Lesson\nlesson: [not, a, mapping]\n---\n",
    ],
    ids=["no-front-matter", "no-lesson-key", "missing-fields", "not-a-mapping"],
)
def test_page_outside_the_lesson_format_is_rejected(site: Path, text: str):
    (site / "lessons/mechanics/04-broken").mkdir()
    (site / "lessons/mechanics/04-broken/index.qmd").write_text(text)

    with pytest.raises(ValueError, match="04-broken"):
        read_lessons(site)


@pytest.mark.parametrize(
    "item, expected",
    [
        (lesson("optics", strand="optics", order=1), "not a strand"),
        (lesson("hard", order=4, difficulty=4), "not on the scale"),
    ],
    ids=["unknown-strand", "difficulty-off-the-scale"],
)
def test_strand_and_difficulty_outside_the_definitions_are_rejected(
    site: Path, item: Lesson, expected: str
):
    write_lesson(site, item)

    with pytest.raises(ValueError, match=expected):
        read_lessons(site)


# --- Validation ----------------------------------------------------------------


def test_a_consistent_set_of_lessons_has_no_problem():
    assert problems(LESSONS) == []


def test_duplicate_id_is_reported_on_the_later_lesson():
    duplicate = lesson("kinematics", strand="lean", order=2, prerequisites=("proof",))

    assert messages([*LESSONS, duplicate]) == [
        f"{duplicate.page}: lesson id 'kinematics' is already used by {KINEMATICS.page}"
    ]


def test_unknown_prerequisite_is_reported():
    orphan = lesson("orbit", order=4, prerequisites=("gravity",))

    assert messages([*LESSONS, orphan]) == [
        f"{orphan.page}: prerequisite 'gravity' is not the id of any lesson"
    ]


def test_prerequisite_later_in_the_path_is_reported():
    # Nothing depends on the first lesson, so this is not a cycle.
    early = lesson("kinematics", prerequisites=("proof",))
    second = lesson("newton", order=2)

    assert messages([early, second, ENERGY, PROOF]) == [
        f"{early.page}: prerequisite 'proof' does not come earlier in the learning path"
    ]


def test_cycle_is_reported_once_with_its_members():
    first = lesson("kinematics", prerequisites=("energy",))
    found = messages([first, NEWTON, ENERGY, PROOF])

    assert (
        f"{first.page}: prerequisites form a cycle: kinematics -> energy -> newton"
        " -> kinematics"
    ) in found
    assert sum("cycle" in message for message in found) == 1


def test_gap_in_the_order_of_a_strand_is_reported():
    late = lesson("orbit", order=5, prerequisites=("energy",))

    assert messages([*LESSONS, late]) == [
        f"{late.page}: 'lesson.order' is 5, but strand 'mechanics' has no lesson"
        " with order 4"
    ]


def test_strand_that_does_not_start_at_one_is_reported():
    assert messages([NEWTON]) == [
        f"{NEWTON.page}: 'lesson.order' is 2, but strand 'mechanics' has no lesson"
        " with order 1",
        f"{NEWTON.page}: prerequisite 'kinematics' is not the id of any lesson",
    ]


def test_duplicate_order_in_a_strand_is_reported():
    twin = Lesson(**{**NEWTON.__dict__, "id": "forces", "page": "lessons/x/index.qmd"})

    assert messages([*LESSONS, twin]) == [
        f"{twin.page}: 'lesson.order' 2 is already used by {NEWTON.page}"
    ]


def test_reading_an_inconsistent_site_fails_with_every_problem(site: Path):
    write_lesson(site, lesson("orbit", order=5, prerequisites=("gravity",)))

    with pytest.raises(ValueError) as failure:
        LearningPath.read(site)

    assert "no lesson with order 4" in str(failure.value)
    assert "'gravity' is not the id" in str(failure.value)


# --- Rendering -----------------------------------------------------------------


@pytest.fixture
def path(site: Path) -> LearningPath:
    return LearningPath.read(site)


def test_header_shows_strand_position_difficulty_prerequisites_and_neighbours(
    path: LearningPath,
):
    shown = LessonHeader(path, NEWTON)._repr_markdown_()

    assert "[Mechanics](../../../path/index.html#mechanics), lesson 2 of 3" in shown
    assert "[Intermediate, level 2 of 3](../../../path/index.html#difficulty)" in shown
    assert "Prerequisites\n:   [Kinematics](../01-kinematics/index.html)" in shown
    assert "Previous\n:   [Kinematics](../01-kinematics/index.html)" in shown
    assert "Next\n:   [Energy](../03-energy/index.html)" in shown


def test_header_links_across_strands_and_states_the_ends_of_the_path(
    path: LearningPath,
):
    first = LessonHeader(path, KINEMATICS)._repr_markdown_()
    last = LessonHeader(path, PROOF)._repr_markdown_()

    assert "Previous\n:   none; this is the first lesson" in first
    assert "Next\n:   [Newton](../02-newton/index.html)" in first
    assert "Previous\n:   [Energy](../../mechanics/03-energy/index.html)" in last
    assert "Next\n:   none yet; this is the last lesson" in last
    assert "[Formal proofs](../../../path/index.html#lean), lesson 1 of 1" in last


def test_header_names_the_outside_prerequisites(path: LearningPath):
    item = lesson("drag", order=4, prerequisites=("newton",), outside=("Calculus",))
    path = LearningPath((*path.lessons, item))

    shown = LessonHeader(path, item)._repr_markdown_()

    assert "[Newton](../02-newton/index.html). Also assumed: Calculus." in shown


def test_overview_explains_the_scale_and_lists_strands_with_lessons_in_order(
    path: LearningPath,
):
    shown = str(PathOverview(path, PATH_PAGE))

    assert "## Difficulty {#difficulty}" in shown
    for difficulty in DIFFICULTIES:
        assert difficulty.description in shown
    headings = [line for line in shown.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Difficulty {#difficulty}",
        "## Mechanics {#mechanics}",
        "## Formal proofs {#lean}",
    ]
    assert "LLM agents" not in shown and "Agent-based" not in shown
    lessons = [
        line for line in shown.splitlines() if line[:1].isdigit() and ". [" in line
    ]
    assert lessons == [
        "1. [Kinematics](../lessons/mechanics/01-kinematics/index.html)",
        "2. [Newton](../lessons/mechanics/02-newton/index.html)",
        "3. [Energy](../lessons/mechanics/03-energy/index.html)",
        "1. [Proof](../lessons/lean/01-proof/index.html)",
    ]
    assert (
        "   Advanced, level 3 of 3. Prerequisites:"
        " [Energy](../lessons/mechanics/03-energy/index.html)." in shown
    )


def test_overview_of_a_site_without_lessons_says_so():
    shown = str(PathOverview(LearningPath(()), PATH_PAGE))

    assert "No lesson has been published yet." in shown
    assert "## Difficulty {#difficulty}" in shown


def pandoc_blocks(markdown: str) -> list[dict]:
    """The Pandoc document of ``markdown``, read by the Pandoc Quarto ships."""
    result = subprocess.run(
        ["quarto", "pandoc", "--from", "markdown", "--to", "json"],
        input=markdown,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)["blocks"]


def test_overview_keeps_the_facts_of_every_lesson_in_its_item_past_ten_lessons():
    # A two-digit marker is wider than a one-digit one; the paragraphs of an
    # item must be indented to the width of its marker, or Pandoc places them
    # outside the item and starts a new list after it.
    lessons = []
    for order in range(1, 12):
        earlier = ("l1",) if order > 1 else ()
        item = lesson(f"l{order}", order=order, prerequisites=earlier)
        description = f"About lesson {order},\nin two lines." if order % 2 else ""
        lessons.append(Lesson(**{**item.__dict__, "description": description}))
    path = LearningPath(tuple(lessons))

    blocks = pandoc_blocks(str(PathOverview(path, PATH_PAGE)))

    ordered_lists = [block for block in blocks if block["t"] == "OrderedList"]
    assert len(ordered_lists) == 1
    items = ordered_lists[0]["c"][1]
    assert len(items) == 11
    for order, item in enumerate(items, start=1):
        paragraphs = [block["t"] for block in item]
        assert paragraphs == ["Para"] * (3 if order % 2 else 2), order


# --- From the page being built --------------------------------------------------


def test_helpers_find_the_page_from_the_directory_the_cell_runs_in(
    site: Path, monkeypatch: pytest.MonkeyPatch
):
    (site / "path").mkdir()
    (site / PATH_PAGE).write_text("---\ntitle: Learning path\n---\n")

    monkeypatch.chdir(site / "lessons/mechanics/02-newton")
    header = lesson_header()
    assert header.lesson == NEWTON

    monkeypatch.chdir(site / "path")
    overview = learning_path()
    assert overview.page == PATH_PAGE
    assert "(../lessons/mechanics/02-newton/index.html)" in str(overview)


def test_header_outside_a_lesson_directory_is_an_error(
    site: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(site)

    with pytest.raises(LookupError, match="not a lesson"):
        lesson_header()


def test_helpers_outside_a_website_project_are_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="website project"):
        learning_path()
