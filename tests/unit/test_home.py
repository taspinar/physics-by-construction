"""The generated parts of the home page: Part A and Part B from the curriculum
file and the lessons, the capstone projects from the map manifest, and the
examples the page links (F25, F62, F124)."""

import re
from dataclasses import replace

from support.paths import SITE_SOURCE

from pbc.authoring import COURSES, HomeContent, LearningPath
from pbc.authoring.atlas import CAPSTONE, AtlasManifest
from pbc.authoring.home import (
    ARTWORK_LABEL,
    CONSTRUCT_EXAMPLE,
    FEATURED_CAPSTONE,
    FEATURED_COURSES,
    FEATURED_HEADING,
    INVESTIGATE_EXAMPLE,
    OPENING_LESSON,
    OPENING_SOURCE,
    VERIFY_EXAMPLE,
)
from pbc.authoring.home_artwork import ALT, WAVEFRONT
from pbc.authoring.repository import BuildCommit

PATH = LearningPath.read(SITE_SOURCE)
MANIFEST = AtlasManifest.read(SITE_SOURCE, PATH.curriculum)
HOME = HomeContent(PATH, MANIFEST)
LINK = re.compile(r"\[[^\]]*\]\(([^)]*)\)")


def _lessons(number: int) -> str:
    return f"{number} lesson{'' if number == 1 else 's'} published"


def _item(lines: list[str], title: str) -> str:
    (line,) = [line for line in lines if line.startswith("- ") and title in line]
    return line


def _featured_blocks(text: str) -> dict[str, str]:
    return dict(
        re.findall(
            r"::: \{\.home-course data-course=([\w-]+)\}\n(.*?)\n:::", text, re.S
        )
    )


def test_part_a_names_every_course_of_the_file_with_real_counts():
    text = HOME.part_a()
    featured = _featured_blocks(text)
    compact = [line for line in text.splitlines() if line.startswith("- ")]
    assert len(COURSES) == 8
    # Three featured with their illustrations, the other five in the row.
    assert list(featured) == list(FEATURED_COURSES)
    assert len(compact) == len(COURSES) - len(FEATURED_COURSES)
    assert f"The site publishes {len(PATH.lessons)} lessons." in text
    for course in COURSES:
        if course.id in featured:
            item = featured[course.id]
        else:
            item = _item(compact, course.title)
        assert 'class="atlas-illustration home-illustration"' in item
        assert 'aria-hidden="true"' in item
        published = PATH.in_course(course)
        planned = len(PATH.planned_in_course(course))
        if published:
            assert f"[{course.title}](path/index.html#course-{course.id})" in item
            assert _lessons(len(published)) in item
            assert "{.home-planned}" not in item
        else:
            assert "path/index.html" not in item
            assert "[planned]{.home-planned}" in item
            assert "no lesson published" in item
        if planned:
            assert f"{planned} planned" in item


def test_a_featured_course_starts_with_its_first_published_lesson():
    featured = _featured_blocks(HOME.part_a())
    for course_id in FEATURED_COURSES:
        course = next(course for course in COURSES if course.id == course_id)
        first = PATH.in_course(course)[0]
        assert f"Starts with {HOME.example(first.id)}." in featured[course_id]


def test_part_b_names_every_method_path_with_real_counts():
    lines = HOME.part_b().splitlines()
    assert "::: {.home-structure .home-paths}" in lines
    assert len(PATH.paths) == 4
    assert sum(line.startswith("- ") for line in lines) == len(PATH.paths)
    for method_path in PATH.paths:
        (line,) = [
            line
            for line in lines
            if line.startswith((f"- {method_path.title} ", f"- [{method_path.title}]("))
        ]
        published = len(PATH.in_path(method_path))
        if published:
            assert f"](path/index.html#path-{method_path.id})" in line
            assert _lessons(published) in line
        else:
            assert "](" not in line and "[planned]{.home-planned}" in line
        assert f"{len(PATH.planned_in_path(method_path))} planned" in line


def test_a_planned_lesson_is_never_part_of_a_published_count():
    published = {lesson.slot for lesson in PATH.lessons if lesson.slot}
    planned = {slot.label for slot in PATH.curriculum.slots} - published
    assert len(PATH.curriculum.slots) == len(published) + len(planned)
    for course in COURSES:
        unfilled = {slot.label for slot in PATH.planned_in_course(course)}
        assert unfilled <= planned
        assert not unfilled & {lesson.slot for lesson in PATH.in_course(course)}


def _capstone_blocks(text: str) -> dict[str, str]:
    return dict(
        re.findall(r"::: \{\.home-capstone data-slot=(\w+)\}\n(.*?)\n:::", text, re.S)
    )


def _feature(text: str) -> tuple[str, str]:
    """The featured capstone's slot and its text (heading, name, and
    description), without the artwork."""
    ((slot, block),) = re.findall(
        r"::: \{\.home-capstone \.home-capstone-feature data-slot=(\w+)\}\n"
        r"::: \{\.home-capstone-text\}\n(.*?)\n:::",
        text,
        re.S,
    )
    return slot, block


def _name(slot) -> str:
    course = next(course for course in COURSES if course.id == slot.course)
    return (
        f"[{course.title}, capstone project [planned]{{.home-planned}}]"
        "{.home-capstone-name}"
    )


def _without_published_capstones() -> HomeContent:
    """The home of the path without the lessons that fill a capstone slot,
    so that every capstone is planned."""
    labels = {slot.label for slot in PATH.curriculum.slots if slot.kind == CAPSTONE}
    lessons = tuple(lesson for lesson in PATH.lessons if lesson.slot not in labels)
    return HomeContent(replace(PATH, lessons=lessons), MANIFEST)


def test_the_capstones_show_only_the_manifest_explanation_and_are_planned():
    text = _without_published_capstones().capstones()
    slots = [slot for slot in PATH.curriculum.slots if slot.kind == CAPSTONE]
    assert {slot.label for slot in slots} == {"T11", "EM9", "FL10"}
    blocks = _capstone_blocks(text)
    featured, feature = _feature(text)
    assert featured == FEATURED_CAPSTONE
    assert set(blocks) | {featured} == {slot.label for slot in slots}
    for slot in slots:
        explanation = MANIFEST.capstone(slot.label).explanation
        description = f"[{explanation}]{{.capstone-description}}"
        if slot.label == featured:
            # The editorial heading, then the name line and the manifest's
            # explanation, as in the smaller boxes.
            heading, blank, name, blank2, found = feature.split("\n")
            assert heading.startswith(f"### {FEATURED_HEADING} ")
            assert blank == blank2 == ""
            block = feature
        else:
            # The name line names the course and the state; the one
            # description is the manifest's explanation, in full and alone.
            block = blocks[slot.label]
            name, blank, found = block.split("\n")
            assert blank == ""
        assert name == _name(slot)
        assert found == description
        assert "](" not in block
        # The curriculum file's title is not a second description.
        assert slot.title not in block
    assert "hypothetical" in MANIFEST.capstone("T11").explanation
    assert "hypothetical" in blocks["T11"]


def test_the_featured_capstone_has_the_conceptual_artwork_and_its_label():
    text = HOME.capstones()
    assert f'<img src="assets/{WAVEFRONT}" alt="{ALT}"' in text
    assert f"[{ARTWORK_LABEL}]{{.home-artwork-label}}" in text
    assert "Conceptual artwork for a planned capstone" in ARTWORK_LABEL
    # The artwork comes after the featured capstone's text and before the
    # smaller boxes.
    assert text.index(FEATURED_HEADING) < text.index(WAVEFRONT)
    assert text.index(WAVEFRONT) < text.index("::: {.home-capstones}")


def test_the_published_em9_capstone_links_to_its_lesson():
    block = _capstone_blocks(HOME.capstones())["EM9"]
    lesson = next(lesson for lesson in PATH.lessons if lesson.slot == "EM9")
    assert "[published]{.home-published}" in block
    assert LINK.findall(block) == [lesson.page.removesuffix(".qmd") + ".html"]


def test_a_published_capstone_links_to_its_lesson():
    lesson = PATH.lessons[0]
    published = replace(lesson, slot="EM9")
    path = replace(
        PATH, lessons=tuple(published if x is lesson else x for x in PATH.lessons)
    )
    text = HomeContent(path, MANIFEST).capstones()
    block = _capstone_blocks(text)["EM9"]
    assert "[published]{.home-published}" in block
    assert LINK.findall(block) == [lesson.page.removesuffix(".qmd") + ".html"]
    assert "One of them is published." in text


def test_the_page_has_no_numbered_teaching_formula():
    source = (SITE_SOURCE / "index.qmd").read_text(encoding="utf-8")
    assert "From a question to a working model" not in source
    assert "One result, constructed and proved" not in source
    headings = re.findall(r"^#+ .*$", source, re.M)
    assert not [h for h in headings if re.match(r"#+ (\d|Step\b)", h)]
    for heading in ("Construct", "Investigate", "Verify"):
        assert f"# {heading}" not in source


def test_the_examples_are_published_lessons_of_the_three_activities():
    for lesson_id in (CONSTRUCT_EXAMPLE, INVESTIGATE_EXAMPLE, VERIFY_EXAMPLE):
        assert PATH.lesson(lesson_id).title in HOME.example(lesson_id)
    assert "simulation" in PATH.lesson(CONSTRUCT_EXAMPLE).methods
    assert "llm-agents" in PATH.lesson(INVESTIGATE_EXAMPLE).methods
    assert "lean" in PATH.lesson(VERIFY_EXAMPLE).methods


def test_the_invitation_links_the_atlas_and_the_first_lesson():
    first = PATH.in_course(PATH.courses[0])[0]
    for text in (HOME.begin(), HOME.actions()):
        assert LINK.findall(text) == [
            "path/index.html#atlas",
            first.page.removesuffix(".qmd") + ".html",
        ]


def test_the_opening_note_names_the_module_the_commit_and_the_lesson():
    sha = "0123456789abcdef0123456789abcdef01234567"
    home = HomeContent(
        PATH, MANIFEST, BuildCommit(sha, dirty=False), "https://example.org/r"
    )
    numbers = {
        "angle": "2",
        "step": "0.002",
        "duration": "10",
        "energy-change": "8e-08",
        "half-step-gap": "2e-05",
    }
    note = home.opening_note(numbers)
    assert f"https://example.org/r/blob/{sha}/{OPENING_SOURCE}" in note
    assert f"https://example.org/r/commit/{sha}" in note
    assert "uncommitted" not in note
    assert "8\u00a0\u00d7\u00a010^\u22128^" in note
    assert PATH.lesson(OPENING_LESSON).title in note
    dirty = HomeContent(PATH, MANIFEST, BuildCommit(sha, dirty=True), "https://x")
    assert "uncommitted changes" in dirty.provenance()
    assert "no commit is named" in HOME.provenance()
