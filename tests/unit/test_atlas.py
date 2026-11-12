"""The manifest of the course atlas, what the build derives from it, the
opening and the sequences of the path page, and the relationships on the
lesson pages (ADR 018 decision 3, ADR 021 decision 3 as amended on
2026-11-11; F125, F133, Issue #483)."""

import re
from dataclasses import replace
from html import escape, unescape
from pathlib import Path

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring import COURSES, LearningPath
from pbc.authoring.atlas import (
    ATLAS_FILE,
    ATLAS_INTRODUCTION,
    CONNECTION_TYPES,
    LAB,
    Atlas,
    AtlasManifest,
    AtlasSection,
    atlas_problems,
    connections,
    illustration_files,
    registered_assets,
)
from pbc.authoring.path import DIFFICULTIES, Curriculum
from pbc.authoring.website import introduced, introduction_page

FILE = SITE_SOURCE / ATLAS_FILE
PATH = LearningPath.read(SITE_SOURCE)
CURRICULUM = PATH.curriculum
ATLAS = Atlas.read(SITE_SOURCE)
REGISTERED = registered_assets(SITE_SOURCE)
INTRODUCED = introduced(SITE_SOURCE)


def data() -> dict:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))


def broken(change) -> list[str]:
    content = data()
    change(content)
    return atlas_problems(content, CURRICULUM, REGISTERED)


def concept(content: dict, concept_id: str) -> dict:
    return next(item for item in content["concepts"] if item["id"] == concept_id)


# --- The rules of the manifest --------------------------------------------------


def sequence(content: dict, sequence_id: str) -> dict:
    return next(item for item in content["sequences"] if item["id"] == sequence_id)


def test_the_manifest_as_committed_breaks_no_rule():
    assert atlas_problems(data(), CURRICULUM, REGISTERED) == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (
            lambda d: d.update(courses=[]),
            "the file holds the lists 'sequences', 'concepts', and 'connections',"
            " and nothing else",
        ),
        (
            lambda d: d.pop("sequences"),
            "the file holds the lists 'sequences', 'concepts', and 'connections',"
            " and nothing else",
        ),
        (
            lambda d: d["sequences"].remove(sequence(d, "quantum")),
            "the sequence 'quantum' has no entry in 'sequences'",
        ),
        (
            lambda d: d["sequences"].remove(sequence(d, "benchmarking")),
            "the sequence 'benchmarking' has no entry in 'sequences'",
        ),
        (
            lambda d: d["sequences"].append(
                {**sequence(d, "waves"), "id": "chemistry"}
            ),
            "sequence 'chemistry': 'id' is not a course or a path of the curriculum",
        ),
        (
            lambda d: d["sequences"].append(sequence(d, "waves")),
            "sequence 'waves': the id is used twice",
        ),
        (
            lambda d: sequence(d, "waves").update(description=" "),
            "sequence 'waves': 'description' must be a text",
        ),
        (
            lambda d: sequence(d, "waves").pop("description"),
            "sequence 'waves': 'description' must be a text",
        ),
        (
            lambda d: sequence(d, "waves").pop("illustration"),
            "sequence 'waves': 'illustration' must name the stem of its files",
        ),
        (
            lambda d: sequence(d, "waves").update(illustration="atlas/optics"),
            "sequence 'waves': the illustration 'atlas/optics' needs its files"
            " registered in assets/provenance.yaml; missing:"
            " atlas/optics-card-152.webp",
        ),
        (
            lambda d: sequence(d, "waves").update(colour="blue"),
            "sequence 'waves': 'colour' is not a field of a sequence",
        ),
        (
            lambda d: sequence(d, "waves").update(title="Waves"),
            "sequence 'waves': 'title' is held by the curriculum file",
        ),
        (
            lambda d: sequence(d, "waves").update(lessons=["W1"]),
            "sequence 'waves': 'lessons' is held by the curriculum file",
        ),
        (
            lambda d: d["sequences"].append("waves"),
            "sequence entry 'waves' must be a mapping",
        ),
        (
            lambda d: d["concepts"][0].update(colour="blue"),
            "concept 'motion-as-a-program': 'colour' is not a field of a concept",
        ),
        (
            lambda d: d["connections"][0].update(weight=2),
            "'weight' is not a field of a connection",
        ),
        (
            lambda d: d["concepts"][0].update(area="chemistry"),
            "concept 'motion-as-a-program': 'area' 'chemistry' is not a course"
            " or a path of the curriculum file",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "ZZ9"]),
            "concept 'motion-as-a-program': 'ZZ9' is not a slot of the curriculum",
        ),
        (
            lambda d: d["concepts"][0].update(slots=[]),
            "concept 'motion-as-a-program' must name at least one slot in 'slots'",
        ),
        (
            lambda d: d["concepts"][0].pop("slots"),
            "concept 'motion-as-a-program' must name at least one slot in 'slots'",
        ),
        (
            lambda d: d["connections"][0].update(
                concepts=["oscillation-and-resonance", "no-such-concept"]
            ),
            "'no-such-concept' is not a concept",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "W1"]),
            "concept 'motion-as-a-program': slot W1 belongs to 'waves', not to"
            " the area 'mechanics'",
        ),
        (
            lambda d: d["concepts"][0].update(slots=["M1", "L1"]),
            "concept 'motion-as-a-program': slot L1 belongs to 'lean', not to"
            " the area 'mechanics'",
        ),
        (
            lambda d: d["concepts"][1].update(id="motion-as-a-program"),
            "concept 'motion-as-a-program': the id is used twice",
        ),
        (
            lambda d: d["concepts"][0].update(id="Motion"),
            "concept 'Motion': 'id' must be a lower-case identifier",
        ),
        (
            lambda d: d["concepts"][0].update(explanation=" "),
            "concept 'motion-as-a-program': 'explanation' must be a text",
        ),
        (
            lambda d: d["connections"][0].update(rationale=""),
            "'rationale' must be a text",
        ),
        (
            lambda d: d["connections"][0].update(type="looks-alike"),
            "'type' must be one of same-mathematics, limit, same-method, application",
        ),
        (
            lambda d: d["connections"][0].update(
                concepts=["oscillation-and-resonance", "oscillation-and-resonance"]
            ),
            "joins a concept to itself",
        ),
        (
            lambda d: d["connections"].append(
                {
                    "concepts": ["circuits-and-resonance", "oscillation-and-resonance"],
                    "type": "same-method",
                    "rationale": "Again.",
                }
            ),
            "the two concepts are connected twice",
        ),
    ],
)
def test_a_manifest_that_breaks_a_rule_is_rejected(change, expected):
    assert any(expected in message for message in broken(change)), broken(change)


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "description",
        "outcomes",
        "prerequisites",
        "state",
        "count",
        "lesson",
        "lessons",
        "illustration",
        "position",
    ],
)
def test_a_field_that_another_source_holds_is_rejected(field):
    problems = broken(lambda d: d["concepts"][0].update({field: "x"}))
    assert problems == [
        f"concept 'motion-as-a-program': {field!r} is held by the curriculum"
        " file or the front matter, or derived by the build, not written in the"
        " manifest"
    ]


@pytest.mark.parametrize("kind", ["prerequisite", "requires", "capstone"])
def test_a_prerequisite_or_a_capstone_link_cannot_be_written(kind):
    problems = broken(lambda d: d["connections"][0].update(type=kind))
    assert len(problems) == 1
    assert "is not curated: prerequisites come from the front matter" in problems[0]


def test_a_prerequisite_field_cannot_be_written_on_a_connection():
    problems = broken(lambda d: d["connections"][0].update(requires=["x"]))
    assert "'requires' is held by the curriculum file" in problems[0]


def test_a_capstone_without_its_concept_is_rejected():
    problems = broken(
        lambda d: d["concepts"].remove(concept(d, "tsunami-reconstruction"))
    )
    assert problems == [
        "capstone slot FL10 must be represented by exactly one concept (a"
        " concept whose only slot it is); found 0"
    ]


def test_a_capstone_with_two_concepts_is_rejected():
    def change(d: dict) -> None:
        d["concepts"].append(
            {**concept(d, "tsunami-reconstruction"), "id": "tsunami-again"}
        )

    assert any("capstone slot FL10" in m and "found 2" in m for m in broken(change))


def test_a_concept_of_two_capstones_alone_is_rejected():
    problems = broken(
        lambda d: concept(d, "tsunami-reconstruction").update(slots=["FL10", "T11"])
    )
    assert any("names only capstone slots" in message for message in problems)


def test_reading_a_broken_manifest_fails_with_every_problem(tmp_path: Path):
    content = data()
    content["concepts"][0]["title"] = "Motion"
    content["connections"][0]["type"] = "prerequisite"
    (tmp_path / ATLAS_FILE).write_text(yaml.safe_dump(content), encoding="utf-8")
    with pytest.raises(ValueError) as error:
        AtlasManifest.read(tmp_path, CURRICULUM)
    assert "'title' is held" in str(error.value)
    assert "is not curated" in str(error.value)


def test_a_site_without_the_manifest_fails_once_it_has_a_curriculum(tmp_path: Path):
    assert AtlasManifest.read(tmp_path, Curriculum()) == AtlasManifest()
    with pytest.raises(ValueError) as error:
        AtlasManifest.read(tmp_path, CURRICULUM)
    assert "the sequence 'mechanics' has no entry" in str(error.value)
    assert "capstone slot T11" in str(error.value)


def test_an_illustration_needs_the_register_of_the_site(tmp_path: Path):
    (tmp_path / ATLAS_FILE).write_text(FILE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="needs its files registered"):
        AtlasManifest.read(tmp_path, CURRICULUM)


def test_every_illustration_is_registered_and_committed():
    for entry in ATLAS.manifest.sequences:
        for file in illustration_files(entry.illustration):
            assert file in REGISTERED
            assert (SITE_SOURCE / "assets" / file).is_file(), file


# --- The curation -----------------------------------------------------------------


def test_every_course_and_path_slot_is_on_the_map_once():
    # The capstone slots are named again by the concepts they integrate;
    # every other slot of a course or a path belongs to exactly one concept,
    # so that every planned slot is labelled on the map.
    named: dict[str, list[str]] = {}
    for item in ATLAS.concepts:
        for label in item.slots:
            named.setdefault(label, []).append(item.id)
    for slot in CURRICULUM.slots:
        if slot.strand:
            assert slot.label not in named
        elif slot.is_capstone:
            assert ATLAS.manifest.capstone(slot.label).id in named[slot.label]
        else:
            assert len(named[slot.label]) == 1, slot.label


def test_every_course_and_path_has_concepts():
    for area in ATLAS.areas:
        assert ATLAS.in_area(area), area


def test_the_capstones_have_their_concepts_and_members():
    # Either kind: a course's applied capstone and a path's product capstone,
    # each represented by exactly one concept (ADR 022 decision 3).
    for label in ("T11", "EM9", "FL10", "SA9", "MD10", "AE7", "RR8"):
        capstone = ATLAS.manifest.capstone(label)
        assert ATLAS.capstone_of(capstone).label == label
        assert [m for m in ATLAS.memberships() if m.capstone == capstone.id]
    assert "hypothetical" in ATLAS.manifest.capstone("T11").explanation
    assert "not a model of any real chip" in ATLAS.manifest.capstone("T11").explanation


# --- What the build derives -----------------------------------------------------


def test_a_concepts_lessons_come_only_from_its_slots():
    for item in ATLAS.concepts:
        own = {slot.label for slot in ATLAS.own_slots(item)}
        assert all(lesson.slot in own for lesson in ATLAS.lessons_of(item))
        filled = {lesson.slot for lesson in ATLAS.lessons_of(item)}
        assert {slot.label for slot in ATLAS.planned_of(item)} == own - filled


def test_the_sequences_are_the_courses_the_paths_and_the_lean_entry():
    sequences = ATLAS.sequences()
    assert [s.anchor for s in sequences] == [
        *(f"course-{course.id}" for course in COURSES),
        *(f"path-{path.id}" for path in CURRICULUM.paths),
        "lean",
    ]
    assert [s.part for s in sequences] == ["A"] * 8 + ["B"] * 4 + [""]
    for entry in ATLAS.manifest.sequences:
        (found,) = [s for s in sequences if s.id == entry.id]
        assert found.description == entry.description
        assert found.illustration == entry.illustration


def test_every_published_lesson_is_a_row_of_exactly_one_sequence():
    rows = [
        row.lesson.id
        for sequence in ATLAS.sequences()
        for row in sequence.rows
        if row.lesson is not None
    ]
    assert sorted(rows) == sorted(lesson.id for lesson in PATH.lessons)


def test_every_slot_is_a_row_of_its_sequence_in_curriculum_order():
    for sequence in ATLAS.sequences():
        if sequence.part == "A":
            slots = [s for s in CURRICULUM.slots if s.course == sequence.id]
        elif sequence.part == "B":
            slots = [s for s in CURRICULUM.slots if s.path == sequence.id]
        else:
            slots = [s for s in CURRICULUM.slots if not (s.course or s.path)]
        # A path's extension rows follow its core (ADR 022 decision 2).
        extensions = [s.label for s in slots if s.extension]
        assert [row.label for row in sequence.extensions] == extensions
        slots = [s for s in slots if not s.extension]
        capstones = [s.label for s in slots if s.is_capstone]
        others = [s.label for s in slots if not s.is_capstone]
        rows = list(sequence.core)
        assert list(sequence.rows) == [*rows, *sequence.extensions]
        # The capstone integrates its course: its row is the last.
        if capstones:
            assert [row.label for row in rows[-len(capstones) :]] == capstones
            rows = rows[: -len(capstones)]
        assert [row.label for row in rows if row.label] == others, sequence.id
        # A lesson without a slot follows the slots, and is published.
        extra = rows[len(others) :]
        assert all(row.label == "" and row.lesson for row in extra)


def test_the_lean_entry_holds_the_lean_lessons_without_a_course_or_path_slot():
    lean = ATLAS.sequences()[-1]
    expected = {
        lesson.id
        for lesson in PATH.lessons
        if (not lesson.slot and "lean" in lesson.methods)
        or (lesson.slot and not (CURRICULUM.slot(lesson.slot).course
                                 or CURRICULUM.slot(lesson.slot).path))
    }  # fmt: skip
    assert {row.lesson.id for row in lean.rows if row.lesson} == expected
    assert expected


def test_the_counts_equal_the_rows_and_a_planned_slot_is_never_published():
    filled = {lesson.slot for lesson in PATH.lessons if lesson.slot}
    for sequence in ATLAS.sequences():
        # The counts are the core's; the extensions are counted apart.
        assert sequence.published + sequence.planned == len(sequence.core)
        assert sequence.extension_published + sequence.extension_planned == len(
            sequence.extensions
        )
        for row in sequence.rows:
            if row.label:
                assert (row.lesson is not None) == (row.label in filled)
            if row.lesson is None:
                assert row.label not in filled
    sequences = ATLAS.sequences()
    published = sum(s.published + s.extension_published for s in sequences)
    assert published == len(PATH.lessons)
    planned = sum(s.planned for s in sequences)
    assert planned == len(CURRICULUM.core) - len(
        filled & {s.label for s in CURRICULUM.core}
    )
    extensions = [s for s in CURRICULUM.slots if s.extension]
    assert sum(s.extension_published + s.extension_planned for s in sequences) == len(
        extensions
    )
    # The five published extension lessons and the two planned extensions.
    assert sum(s.extension_published for s in sequences) == 5
    assert sum(s.extension_planned for s in sequences) == 2


def test_the_aliases_open_the_sequence_of_every_concept_and_course_index():
    aliases = {
        alias: sequence.anchor
        for sequence in ATLAS.sequences()
        for alias in sequence.aliases
    }
    for item in ATLAS.concepts:
        kind = "course" if item.area in {c.id for c in COURSES} else "path"
        assert aliases[f"concept-{item.id}"] == f"{kind}-{item.area}"
    for course in COURSES:
        assert aliases[f"course-{course.id}-lessons"] == f"course-{course.id}"


# --- The page --------------------------------------------------------------------


@pytest.fixture(scope="module")
def page() -> str:
    return str(AtlasSection(ATLAS))


def _sequence_html(page: str, anchor: str) -> str:
    found = re.search(rf'<details [^>]*id="{anchor}"[^>]*>(.*?)</details>', page)
    assert found, anchor
    return found.group(0)


def _published(atlas: Atlas, label: str) -> Atlas:
    lesson = replace(PATH.lessons[0], id="tsunami", slot=label, page="lessons/x.qmd")
    path = replace(PATH, lessons=(*PATH.lessons, lesson))
    return Atlas(path, atlas.manifest)


def test_one_exclusive_disclosure_per_sequence_and_none_open(page: str):
    details = re.findall(r"<details [^>]*>", page)
    assert len(details) == len(ATLAS.sequences()) == 13
    assert all('name="atlas"' in tag for tag in details)
    assert not any(" open" in tag for tag in details)
    ids = re.findall(r' id="([^"]+)"', page)
    assert len(ids) == len(set(ids))
    for anchor in ("atlas", "choose", "courses", "paths", "lean"):
        assert anchor in ids


def test_the_opening_is_the_owners_paragraphs_and_the_derived_figures(page: str):
    """The two paragraphs are the owner's words (Issue #483); the three
    figures are derived: the courses and paths of the curriculum file and
    every published lesson of the front matter. No breadcrumb, no journey,
    no count written by hand."""
    section = AtlasSection(ATLAS)
    opening = page[: page.index('<section class="atlas-sequences"')]
    for text in ATLAS_INTRODUCTION:
        assert f"<p>{escape(text)}</p>" in opening
    assert section.figures() == (
        (len(COURSES), "physics course"),
        (len(CURRICULUM.paths), "AI method path"),
        (len(PATH.lessons), "published lesson"),
    )
    assert section.figures()[2][0] == sum(s.published for s in ATLAS.sequences()) + sum(
        s.extension_published for s in ATLAS.sequences()
    )
    items = re.findall(r"<li>(.*?)</li>", opening)
    assert items == [
        f'<span class="atlas-figure-number">{len(COURSES)}</span> '
        '<span class="atlas-figure-label">physics courses</span>',
        f'<span class="atlas-figure-number">{len(CURRICULUM.paths)}</span> '
        '<span class="atlas-figure-label">AI method paths</span>',
        f'<span class="atlas-figure-number">{len(PATH.lessons)}</span> '
        '<span class="atlas-figure-label">published lessons</span>',
    ]
    for absent in ("pbc-breadcrumb", "journey", "atlas-summary", "lessons published"):
        assert absent not in page
    # The opening stands before the first row.
    assert page.index('class="atlas-figures"') < page.index('class="atlas-sequence')


def test_the_introduction_link_stands_before_the_rows_where_one_exists():
    page = str(AtlasSection(ATLAS, introductions=INTRODUCED))
    for sequence in ATLAS.sequences():
        html = _sequence_html(page, sequence.anchor)
        if sequence.id in INTRODUCED and sequence.part:
            href = "../" + introduction_page(sequence.id).removesuffix(".qmd") + ".html"
            words = "course" if sequence.part == "A" else "method path"
            link = (
                f'<p class="atlas-introduction"><a href="{href}">Read the {words}'
                " introduction</a></p>"
            )
            assert link in html, sequence.id
            assert html.index(link) < html.index('<ol class="atlas-rows">')
            assert html.index('class="atlas-description"') < html.index(link)
        else:
            assert "atlas-introduction" not in html, sequence.id
    assert any(s.id in INTRODUCED for s in ATLAS.sequences())


def test_each_card_and_panel_show_the_counts_of_their_rows(page: str):
    for sequence in ATLAS.sequences():
        html = _sequence_html(page, sequence.anchor)
        card = re.search(r"<summary.*?</summary>", html).group(0)
        counts = f"{sequence.published} published"
        if sequence.planned:
            counts += f" · {sequence.planned} planned"
        assert f'<span class="atlas-card-count">{counts}</span>' in card
        assert "atlas-counts" not in html and "atlas-kicker" not in html
        assert html.count('<li class="') == len(sequence.rows)
        group = re.search(r'<section class="atlas-extensions".*?</section>', html)
        if sequence.extensions:
            group = group.group(0)
            extra = f"{sequence.extension_published} published"
            if sequence.extension_planned:
                extra += f", {sequence.extension_planned} planned"
            assert f"{extra}.</p>" in group
            assert group.count('<li class="') == len(sequence.extensions)
            core_html = html.replace(group, "")
        else:
            assert group is None
            core_html = html
        assert core_html.count('data-state="published"') == sequence.published
        assert core_html.count('data-state="planned"') == sequence.planned
        # The progress hairline: one segment per published lesson of the core.
        assert card.count('<i class="path-link" data-lesson-id=') == sequence.published


def test_a_paths_extensions_follow_its_core_under_their_own_heading(page: str):
    for sequence in ATLAS.sequences():
        html = _sequence_html(page, sequence.anchor)
        if not sequence.extensions:
            assert "atlas-extensions" not in html
            continue
        assert sequence.part == "B"
        group = re.search(r'<section class="atlas-extensions".*?</section>', html)
        text = group.group(0)
        # After the core list, under a heading of its own; the rows carry no
        # mark of their own (ADR 022 decision 2).
        core_end = html.index("</ol>")
        assert core_end < group.start()
        assert html[core_end : group.start()] == "</ol>"
        assert (
            f'<h3 class="atlas-extensions-title" id="{sequence.anchor}-extensions">'
            "Optional extensions</h3>" in text
        )
        assert f'aria-labelledby="{sequence.anchor}-extensions"' in text
        labels = re.findall(r'<span class="atlas-label">([A-Z]+[0-9]+)</span>', text)
        assert labels == [row.label for row in sequence.extensions]
        assert "atlas-mark-extension" not in text
    paths = [s for s in ATLAS.sequences() if s.extensions]
    assert [s.id for s in paths] == [
        "reasoning",
        "law-discovery",
        "autonomous-research",
    ]


def test_a_published_row_links_its_lesson_and_a_planned_row_links_nothing(page: str):
    for item in re.findall(r'<li class="[^"]*" data-state="planned">.*?</li>', page):
        assert "<a " not in item and "tabindex" not in item and "<button" not in item
        assert ">planned</span>" in item
        assert "atlas-planned-title" in item
        assert "atlas-level" not in item
    rows = re.findall(r'<li class="path-card[^"]*" data-state="published"[^>]*>', page)
    assert len(rows) == len(PATH.lessons)
    for lesson in PATH.lessons:
        href = "../" + lesson.page.removesuffix(".qmd") + ".html"
        assert page.count(f'href="{href}"') == 1, lesson.id
        assert f'data-lesson-id="{lesson.id}">' in page


def test_the_rows_carry_only_the_marks_lab_capstone_and_lean(page: str):
    marks = re.findall(r'<span class="atlas-mark atlas-mark-([a-z]+)"', page)
    assert set(marks) == {"lab", "capstone", "lean", "planned"}
    labs = sum(1 for s in CURRICULUM.slots if s.kind == LAB)
    assert marks.count("lab") == labs
    # Both kinds of capstone under the one capstone mark.
    assert marks.count("capstone") == sum(1 for s in CURRICULUM.slots if s.is_capstone)
    assert marks.count("capstone") == 7
    assert "★" not in page


def test_a_published_row_shows_the_difficulty_of_its_front_matter(page: str):
    titles = {difficulty.level: difficulty.title for difficulty in DIFFICULTIES}
    rows = re.findall(
        r'<li class="path-card[^"]*" data-state="published"'
        r' data-lesson-id="([^"]+)">.*?<span class="atlas-level">([^<]+)</span>',
        page,
    )
    assert len(rows) == len(PATH.lessons)
    for lesson_id, shown in rows:
        assert shown == titles[PATH.lesson(lesson_id).difficulty], lesson_id


def test_a_capstone_is_a_link_when_published_and_else_its_planned_description(
    page: str,
):
    for label in ("T11", "EM9", "FL10"):
        item = re.search(rf'<li class="[^"]*atlas-row-capstone[^"]*"[^>]*>'
                         rf'<span class="atlas-label">{label}</span>.*?</li>',
                         page).group(0)  # fmt: skip
        lesson = next((x for x in PATH.lessons if x.slot == label), None)
        description = ATLAS.manifest.capstone(label).explanation
        if lesson is None:
            assert "<a " not in item
            assert f'<p class="capstone-description">{escape(description)}</p>' in item
        else:
            href = "../" + lesson.page.removesuffix(".qmd") + ".html"
            assert f'href="{href}"' in item
            assert "capstone-description" not in item
    published = str(AtlasSection(_published(ATLAS, "FL10")))
    item = re.search(r'<span class="atlas-label">FL10</span>.*?</li>', published).group(
        0
    )
    assert 'href="../lessons/x.html"' in item
    assert "capstone-description" not in item


def test_the_planned_capstones_description_is_only_the_manifests_explanation(
    page: str,
):
    descriptions = re.findall(r'<p class="capstone-description">(.*?)</p>', page)
    planned = [
        s.label
        for s in (*(row for seq in ATLAS.sequences() for row in seq.rows if row.label),)
        if s.is_capstone and s.lesson is None
    ]
    assert [unescape(text) for text in descriptions] == [
        ATLAS.manifest.capstone(label).explanation for label in planned
    ]
    assert planned == ["FL10", "SA9", "MD10", "AE7", "RR8"]


def test_part_b_is_told_apart_in_words_and_its_illustrations_say_toy_model(page: str):
    for sequence in ATLAS.sequences():
        html = _sequence_html(page, sequence.anchor)
        if sequence.part == "A":
            assert "atlas-part-a" in html
            assert "toy-model" not in html
        elif sequence.part == "B":
            assert "atlas-part-b" in html
            assert "a toy-model example, no agent was run" in html
        if sequence.illustration:
            assert f'alt="Illustration of {escape(sequence.title)}' in html
            # The card files only; the panel files are for the introductions.
            for file in illustration_files(sequence.illustration):
                assert (f"../assets/{file}" in html) == ("-card-" in file), file
            assert 'sizes="76px"' in html and "200" not in html.split("<div")[0]
            assert html.count("<img ") == 1
    # The part's label stands before its sequences, in words.
    assert page.index('<p class="atlas-part atlas-part-a" id="courses">') < page.index(
        'id="course-mechanics"'
    )
    assert (
        page.index('id="course-materials"')
        < page.index('<p class="atlas-part atlas-part-b" id="paths">')
        < page.index('id="path-reasoning"')
    )


def test_the_textual_equivalent_names_every_sequence_and_lesson_with_its_state():
    sentences = AtlasSection(ATLAS).sentences()
    assert len(sentences) == len(ATLAS.sequences())
    for sequence, sentence in zip(ATLAS.sequences(), sentences, strict=True):
        assert sentence.startswith(sequence.title)
        for row in sequence.rows:
            name = f"{row.label} {row.title}" if row.label else row.title
            state = "published" if row.lesson else "planned"
            assert f"{name} ({state}" in sentence
            if row.extension:
                assert re.search(
                    rf"{re.escape(name)} \({state}[^)]*, optional extension\)", sentence
                )


def test_the_textual_equivalent_is_in_the_page_without_links(page: str):
    text = re.search(r'<section class="visually-hidden".*?</section>', page).group(0)
    assert "<a " not in text
    for sentence in AtlasSection(ATLAS).sentences():
        assert escape(sentence) in text


def test_the_section_is_the_same_on_every_build(page: str):
    assert str(AtlasSection(Atlas.read(SITE_SOURCE))) == page


def test_the_section_loads_only_the_address_module(page: str):
    assert re.findall(r'<script[^>]*src="([^"]+)"', page) == ["../learner/atlas.js"]
    assert not re.search(r'(?:src|href)="(?:https?:)?//', page)


# --- The relationships on a lesson page -----------------------------------------


def test_a_lesson_shows_the_connections_and_memberships_of_its_concept():
    for lesson in PATH.lessons:
        items = connections(ATLAS, lesson, lesson.page)
        concepts = ATLAS.concepts_of(lesson)
        expected = []
        for item in concepts:
            expected += [
                c.rationale for c in ATLAS.manifest.connections if item.id in c.concepts
            ]
        rationales = [text for text in expected if any(text in i for i in items)]
        assert rationales == expected, lesson.id
        members = [
            m for item in concepts for m in ATLAS.memberships() if m.member == item.id
        ]
        assert sum("is part of the capstone project" in i for i in items) == len(
            members
        )
        if not lesson.slot:
            assert items == []


def test_a_connection_names_its_type_and_links_the_other_concepts_sequence():
    lesson = PATH.lesson("harmonic-oscillator")
    items = connections(ATLAS, lesson, lesson.page)
    assert items
    for text in items:
        assert re.search(
            r"\(\.\./\.\./\.\./path/index\.html#(course|path)-[a-z-]+\)", text
        )
        assert any(
            words in text
            for words in (
                "same mathematics",
                "a limit",
                "same method",
                "an application",
            )
        )


def test_every_connection_and_membership_reaches_a_published_lesson_or_a_planned_one():
    shown = set()
    for lesson in PATH.lessons:
        for text in connections(ATLAS, lesson, lesson.page):
            shown.add(text)
    for connection in ATLAS.manifest.connections:
        ends = [ATLAS.manifest.concept(end) for end in connection.concepts]
        if any(ATLAS.lessons_of(end) for end in ends):
            assert any(connection.rationale in text for text in shown)
    assert CONNECTION_TYPES


# --- Malformed field types are reported, never raised (#245) --------------------


@pytest.mark.parametrize("wrong", [["mechanics"], {"a": 1}, 3, None])
def test_a_concept_area_of_the_wrong_type_is_a_problem(wrong):
    found = broken(lambda d: d["concepts"][0].update(area=wrong))

    assert any("'area'" in problem for problem in found)


@pytest.mark.parametrize("wrong", [[["x"]], [{"a": 1}], "slot", {"a": 1}, [None]])
def test_concept_slots_of_the_wrong_type_are_a_problem(wrong):
    found = broken(lambda d: d["concepts"][0].update(slots=wrong))

    assert any("'slots'" in problem or "slot" in problem for problem in found)


@pytest.mark.parametrize("wrong", [["related"], {"a": 1}, 3, None])
def test_a_connection_type_of_the_wrong_type_is_a_problem(wrong):
    found = broken(lambda d: d["connections"][0].update(type=wrong))

    assert any("'type' must be one of" in problem for problem in found)


@pytest.mark.parametrize("wrong", [[["a"], "b"], [{"a": 1}, "b"], ["a", ["b"]]])
def test_an_unhashable_connection_endpoint_is_a_problem(wrong):
    found = broken(lambda d: d["connections"][0].update(concepts=wrong))

    assert any("'concepts' must name two concepts" in problem for problem in found)
