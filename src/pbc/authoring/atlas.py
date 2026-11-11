"""The course atlas: its manifest, what the build derives from it, and the
navigation page of inline expanding courses (ADR 018 decision 3, ADR 021
decision 3 as amended on 2026-11-11; F125, F133, Issue #483).

The atlas has one source of truth (docs/architecture.md, I31): courses,
paths, and slots come from the curriculum file, publication, titles,
difficulty, prerequisites, and addresses from the front matter of the
lessons, and the manifest (``site/atlas.yaml``) adds only what neither
holds: one entry per sequence (each course and each method path) with its
one-line description and its illustration, concept identifiers with a short
explanation, the slots each concept covers, and the curated conceptual
connections with their rationale. Everything else is derived here when the
path page is built: the lessons of a sequence and their state, the counts,
the three figures of the opening, and capstone membership from the slots a
concept names.

The page opens with the owner's two paragraphs and the three figures, then
holds twelve native disclosures of one exclusive group, one per sequence,
and a smaller one for the Lean lessons beyond the curriculum: the
``<summary>`` is the row (illustration, title, counts, progress), the
content expands inline beneath it with the description, the link to the
introduction, and the lesson rows. None is open at load; without a script
every lesson is one click away. The relationships (conceptual connections
and capstone membership) are shown on the lesson pages (``connections``).
The same inputs give the same page, byte for byte.
"""

import posixpath
import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from functools import cached_property
from html import escape
from pathlib import Path, PurePosixPath

import yaml

from pbc.authoring.path import (
    _COURSE,
    _DIFFICULTY,
    _FRONT_MATTER_FIELDS,
    APPLIED_CAPSTONE,
    CAPSTONES,
    COURSES,
    PATH_PAGE,
    Curriculum,
    LearningPath,
    Lesson,
    Slot,
    _page_being_built,
)
from pbc.authoring.website import introduced, introduction_page, page_href

# Where the manifest sits in the website project, beside the curriculum file.
ATLAS_FILE = "atlas.yaml"
# The provenance register of the site's assets, and the directory it names
# files relative to (ADR 021 decision 2).
ASSETS = "assets"
ASSET_REGISTER = f"{ASSETS}/provenance.yaml"

# The capstone of a course; a method path's is a product capstone, and both
# are capstones wherever the atlas marks one (``CAPSTONES``, ADR 022).
CAPSTONE = APPLIED_CAPSTONE
LAB = "measured-data lab"

_ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_SEQUENCE_KEYS = {"id", "description", "illustration"}
_CONCEPT_KEYS = {"id", "area", "slots", "explanation"}
_CONNECTION_KEYS = {"concepts", "type", "rationale"}
# What the curriculum file or a lesson's front matter holds, and what the
# generator derives: never in the manifest. A sequence entry holds its
# description and its illustration, a concept neither.
_NOT_HERE = {
    *_FRONT_MATTER_FIELDS,
    "title",
    "label",
    "kind",
    "course",
    "path",
    "strand",
    "lesson",
    "lessons",
    "state",
    "status",
    "published",
    "planned",
    "count",
    "counts",
    "requires",
    "required-by",
    "capstone",
    "members",
    "position",
    "illustration",
    "image",
    "icon",
}
_SEQUENCE_NOT_HERE = _NOT_HERE - {"description", "illustration"}
_PREREQUISITE_TYPES = {"prerequisite", "prerequisites", "requires", "capstone"}

# The curated kinds of conceptual connection, and how a sentence states one.
# "limit" and "application" read in the order of the two concepts.
CONNECTION_TYPES = {
    "same-mathematics": "{a} and {b} share their mathematics",
    "limit": "{a} is a limit of {b}",
    "same-method": "{a} and {b} use the same method",
    "application": "{a} applies {b}",
}
_CONNECTION_WORDS = {
    "same-mathematics": "same mathematics",
    "limit": "a limit",
    "same-method": "same method",
    "application": "an application",
}

PUBLISHED = "published"
PARTLY = "partly published"
PLANNED = "planned"

# The illustration of a sequence: four WebP files under site/assets/, the
# card (the 76 px slot at 2x and 3x, shown on the atlas) and the panel (the
# 200 px slot at 2x and 4x, shown on the introduction pages), all 4:3 (ADR
# 021 decision 2).
CARD_SLOT = 76
PANEL_SLOT = 200
ILLUSTRATION_WIDTHS = {"card": (152, 228), "panel": (400, 800)}

# The address module: the hash follows the open sequence (F133).
ATLAS_SCRIPT = "learner/atlas.js"
LEAN_ANCHOR = "lean"


def illustration_files(stem: str) -> tuple[str, ...]:
    """The files of an illustration, relative to site/assets/."""
    return tuple(
        f"{stem}-{kind}-{width}.webp"
        for kind, widths in ILLUSTRATION_WIDTHS.items()
        for width in widths
    )


@dataclass(frozen=True)
class SequenceEntry:
    """What the manifest says of a sequence: a course or a method path."""

    id: str
    description: str
    illustration: str  # the stem of its files under site/assets/


@dataclass(frozen=True)
class Concept:
    """A concept of the atlas, as the manifest declares it."""

    id: str
    area: str  # a course id or a path id of the curriculum file
    slots: tuple[str, ...]
    explanation: str

    @property
    def name(self) -> str:
        """The identifier in words: the manifest writes no title."""
        words = self.id.replace("-", " ")
        return words[:1].upper() + words[1:]


@dataclass(frozen=True)
class Connection:
    """A curated conceptual connection between two concepts."""

    concepts: tuple[str, str]
    type: str
    rationale: str


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _field_problems(
    item: dict, name: str, what: str, keys: set[str], not_here: set[str]
) -> list[str]:
    found = []
    for key in item:
        if key in keys:
            continue
        if key in not_here:
            found.append(
                f"{what} {name}: {key!r} is held by the curriculum file or the"
                " front matter, or derived by the build, not written in the"
                " manifest"
            )
        else:
            found.append(f"{what} {name}: {key!r} is not a field of a {what}")
    return found


def _sequence_problems(
    sequences: object, curriculum: Curriculum, registered: Collection[str]
) -> list[str]:
    if not isinstance(sequences, list):
        return ["'sequences' must be a list"]
    found: list[str] = []
    # A site without a curriculum file has no sequence to describe.
    wanted = (
        [course.id for course in COURSES] + [path.id for path in curriculum.paths]
        if curriculum.slots
        else []
    )
    seen: list[str] = []
    for item in sequences:
        if not isinstance(item, dict):
            found.append(f"sequence entry {item!r} must be a mapping")
            continue
        name = repr(item.get("id"))
        found += _field_problems(
            item, name, "sequence", _SEQUENCE_KEYS, _SEQUENCE_NOT_HERE
        )
        sequence_id = item.get("id")
        if sequence_id not in wanted:
            found.append(
                f"sequence {name}: 'id' is not a course or a path of the"
                " curriculum file"
            )
        elif sequence_id in seen:
            found.append(f"sequence {name}: the id is used twice")
        else:
            seen.append(str(sequence_id))
        if not _is_text(item.get("description")):
            found.append(f"sequence {name}: 'description' must be a text")
        stem = item.get("illustration")
        if not _is_text(stem):
            found.append(
                f"sequence {name}: 'illustration' must name the stem of its"
                " files under site/assets/, such as atlas/mechanics"
            )
            continue
        missing = [file for file in illustration_files(stem) if file not in registered]
        if missing:
            found.append(
                f"sequence {name}: the illustration {stem!r} needs its files"
                f" registered in {ASSET_REGISTER}; missing: {', '.join(missing)}"
            )
    for sequence_id in wanted:
        if sequence_id not in seen:
            found.append(f"the sequence {sequence_id!r} has no entry in 'sequences'")
    return found


def atlas_problems(
    data: object, curriculum: Curriculum, registered: Collection[str] = ()
) -> list[str]:
    """Return every way the contents of the manifest break its rules (ADR 018
    decision 3, ADR 021 decision 3): an unknown field, a field the curriculum
    file or the front matter holds, a sequence missing, unknown, or twice, a
    sequence without its description or with an illustration the register
    ``registered`` (its keys) does not name, a prerequisite, a reference that
    does not resolve, a concept without a slot or with a slot outside its
    area, and a capstone slot that is not represented by exactly one
    concept."""
    if not isinstance(data, dict) or set(data) != {
        "sequences",
        "concepts",
        "connections",
    }:
        return [
            "the file holds the lists 'sequences', 'concepts', and 'connections',"
            " and nothing else"
        ]
    found = _sequence_problems(data["sequences"], curriculum, registered)
    courses = {course.id for course in COURSES}
    paths = {path.id for path in curriculum.paths}
    slots = {slot.label: slot for slot in curriculum.slots}
    capstones = [slot.label for slot in curriculum.slots if slot.is_capstone]

    concepts = data["concepts"]
    if not isinstance(concepts, list):
        found.append("'concepts' must be a list")
        concepts = []
    ids: set[str] = set()
    represented: dict[str, list[str]] = {label: [] for label in capstones}
    for item in concepts:
        if not isinstance(item, dict):
            found.append(f"concept entry {item!r} must be a mapping")
            continue
        name = repr(item.get("id"))
        found += _field_problems(item, name, "concept", _CONCEPT_KEYS, _NOT_HERE)
        concept_id = item.get("id")
        if not (isinstance(concept_id, str) and _ID.fullmatch(concept_id)):
            found.append(
                f"concept {name}: 'id' must be a lower-case identifier such as"
                " harmonic-motion"
            )
        elif concept_id in ids:
            found.append(f"concept {name}: the id is used twice")
        else:
            ids.add(concept_id)
        if not _is_text(item.get("explanation")):
            found.append(f"concept {name}: 'explanation' must be a text")
        area = item.get("area")
        if not (isinstance(area, str) and (area in courses or area in paths)):
            found.append(
                f"concept {name}: 'area' {area!r} is not a course or a path of"
                " the curriculum file"
            )
        labels = item.get("slots")
        if not (
            isinstance(labels, list)
            and labels
            and all(isinstance(label, str) for label in labels)
        ):
            found.append(f"concept {name} must name at least one slot in 'slots'")
            continue
        own = []
        for label in labels:
            slot = slots.get(label) if isinstance(label, str) else None
            if slot is None:
                found.append(
                    f"concept {name}: {label!r} is not a slot of the curriculum"
                )
            elif slot.is_capstone:
                continue
            else:
                own.append(label)
                if (slot.course or slot.path) != area:
                    found.append(
                        f"concept {name}: slot {label} belongs to"
                        f" {slot.course or slot.path or slot.strand!r}, not to"
                        f" the area {area!r}"
                    )
        if len(labels) != len(set(labels)):
            found.append(f"concept {name} names a slot twice")
        named = [label for label in labels if label in represented]
        if named and not own and len(labels) == len(named):
            if len(named) > 1:
                found.append(
                    f"concept {name} names only capstone slots: a concept that"
                    " represents a capstone names exactly one slot"
                )
            else:
                represented[named[0]].append(str(concept_id))
                home = slots[named[0]].course or slots[named[0]].path
                if home != area:
                    found.append(
                        f"concept {name} represents {named[0]}, which belongs to"
                        f" {home!r}, not to the area {area!r}"
                    )
    for label, concept_ids in represented.items():
        if len(concept_ids) != 1:
            found.append(
                f"capstone slot {label} must be represented by exactly one concept"
                f" (a concept whose only slot it is); found {len(concept_ids)}"
            )

    connections = data["connections"]
    if not isinstance(connections, list):
        return [*found, "'connections' must be a list"]
    pairs: set[frozenset[str]] = set()
    for item in connections:
        if not isinstance(item, dict):
            found.append(f"connection entry {item!r} must be a mapping")
            continue
        name = repr(item.get("concepts"))
        found += _field_problems(item, name, "connection", _CONNECTION_KEYS, _NOT_HERE)
        kind = item.get("type")
        if not isinstance(kind, str):
            found.append(
                f"connection {name}: 'type' must be one of"
                f" {', '.join(CONNECTION_TYPES)}"
            )
        elif kind in _PREREQUISITE_TYPES:
            found.append(
                f"connection {name}: {kind!r} is not curated: prerequisites come"
                " from the front matter and capstone membership from the slots"
                " of a concept"
            )
        elif kind not in CONNECTION_TYPES:
            found.append(
                f"connection {name}: 'type' must be one of"
                f" {', '.join(CONNECTION_TYPES)}"
            )
        if not _is_text(item.get("rationale")):
            found.append(f"connection {name}: 'rationale' must be a text")
        ends = item.get("concepts")
        if not (
            isinstance(ends, list)
            and len(ends) == 2
            and all(isinstance(end, str) for end in ends)
        ):
            found.append(f"connection {name}: 'concepts' must name two concepts")
            continue
        for end in ends:
            if end not in ids:
                found.append(f"connection {name}: {end!r} is not a concept")
        if ends[0] == ends[1]:
            found.append(f"connection {name} joins a concept to itself")
        pair = frozenset(str(end) for end in ends)
        if pair in pairs:
            found.append(f"connection {name}: the two concepts are connected twice")
        pairs.add(pair)
    return found


def registered_assets(site: Path) -> frozenset[str]:
    """The paths, relative to site/assets/, that the provenance register of
    the website project ``site`` names; empty without a register."""
    file = site / ASSET_REGISTER
    if not file.is_file():
        return frozenset()
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    entries = data.get("assets") if isinstance(data, dict) else None
    return (
        frozenset(str(name) for name in entries)
        if isinstance(entries, dict)
        else frozenset()
    )


def _words(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True)
class AtlasManifest:
    """The manifest, validated against the curriculum file."""

    sequences: tuple[SequenceEntry, ...] = ()
    concepts: tuple[Concept, ...] = ()
    connections: tuple[Connection, ...] = ()

    @classmethod
    def read(cls, site: Path, curriculum: Curriculum) -> AtlasManifest:
        """Read ``atlas.yaml`` of the website project ``site``, with the
        register of its assets; a site without the file has an empty
        manifest, which fails. Raises ``ValueError`` when the file breaks a
        rule; the message lists every problem."""
        file = site / ATLAS_FILE
        data: object = {"sequences": [], "concepts": [], "connections": []}
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{ATLAS_FILE} is not valid YAML: {error}") from None
        return cls.parse(data, curriculum, registered_assets(site))

    @classmethod
    def parse(
        cls, data: object, curriculum: Curriculum, registered: Collection[str] = ()
    ) -> AtlasManifest:
        found = atlas_problems(data, curriculum, registered)
        if found:
            raise ValueError(
                f"{ATLAS_FILE} breaks the rules of the manifest:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            tuple(
                SequenceEntry(
                    id=item["id"],
                    description=_words(item["description"]),
                    illustration=item["illustration"],
                )
                for item in data["sequences"]
            ),
            tuple(
                Concept(
                    id=item["id"],
                    area=item["area"],
                    slots=tuple(item["slots"]),
                    explanation=_words(item["explanation"]),
                )
                for item in data["concepts"]
            ),
            tuple(
                Connection(
                    concepts=(item["concepts"][0], item["concepts"][1]),
                    type=item["type"],
                    rationale=_words(item["rationale"]),
                )
                for item in data["connections"]
            ),
        )

    def sequence(self, sequence_id: str) -> SequenceEntry:
        """The entry of a course or a path; an empty one in a site without a
        curriculum file, which needs none."""
        return next(
            (entry for entry in self.sequences if entry.id == sequence_id),
            SequenceEntry(sequence_id, "", ""),
        )

    def concept(self, concept_id: str) -> Concept:
        return next(concept for concept in self.concepts if concept.id == concept_id)

    def capstone(self, label: str) -> Concept:
        """The concept that represents the capstone slot ``label``: its
        explanation is the capstone's planned description."""
        return next(concept for concept in self.concepts if concept.slots == (label,))


# --- What the build derives ---------------------------------------------------


@dataclass(frozen=True)
class Membership:
    """Concept ``member`` is integrated by the capstone that ``capstone``
    (a concept) represents."""

    member: str
    capstone: str


@dataclass(frozen=True)
class Row:
    """One row of a sequence: a slot of the curriculum, filled by a published
    lesson or planned, or a published lesson without a slot."""

    label: str  # the slot's label; "" for a lesson without a slot
    title: str  # the lesson's title, or the slot's working title
    kind: str  # the slot's kind; "lesson" without a slot
    lesson: Lesson | None  # None: planned, no page, never counted
    description: str = ""  # a planned capstone's description, from the manifest
    extension: bool = False  # an extension slot of a method path (ADR 022)

    @property
    def is_capstone(self) -> bool:
        return self.kind in CAPSTONES


@dataclass(frozen=True)
class AtlasSequence:
    """A course, a method path, or the Lean lessons beyond the curriculum,
    with its rows in teaching order: the slots in the order of the
    curriculum file, a course's lessons without a slot after them, and a
    course's capstone last; a method path's capstone ends its core rows, and
    its extension rows follow them. The counts are those of the core rows;
    the extension rows are counted apart (ADR 022 decision 2)."""

    id: str
    anchor: str  # its id on the page: course-<id>, path-<id>, or lean
    title: str
    part: str  # "A", "B", or "" for the Lean entry
    number: int  # its place in its part, from 1; 0 for the Lean entry
    description: str
    illustration: str  # "" for the Lean entry
    rows: tuple[Row, ...]
    aliases: tuple[str, ...] = ()  # anchors of the previous page it opens on

    @property
    def core(self) -> tuple[Row, ...]:
        return tuple(row for row in self.rows if not row.extension)

    @property
    def extensions(self) -> tuple[Row, ...]:
        return tuple(row for row in self.rows if row.extension)

    @property
    def published(self) -> int:
        return sum(1 for row in self.core if row.lesson is not None)

    @property
    def planned(self) -> int:
        return len(self.core) - self.published

    @property
    def extension_published(self) -> int:
        return sum(1 for row in self.extensions if row.lesson is not None)

    @property
    def extension_planned(self) -> int:
        return len(self.extensions) - self.extension_published


@dataclass(frozen=True)
class Atlas:
    """The atlas of a learning path: the manifest with everything the build
    derives from the curriculum file and the front matter."""

    path: LearningPath
    manifest: AtlasManifest

    @classmethod
    def read(cls, site: Path) -> Atlas:
        path = LearningPath.read(site)
        return cls(path, AtlasManifest.read(site, path.curriculum))

    @property
    def areas(self) -> list[str]:
        return [course.id for course in COURSES] + [
            path.id for path in self.path.curriculum.paths
        ]

    def area_title(self, area: str) -> str:
        if area in _COURSE:
            return _COURSE[area].title
        return self.path.curriculum.path(area).title

    @cached_property
    def concepts(self) -> tuple[Concept, ...]:
        """The concepts area by area (the courses, then the paths), in the
        order of the manifest within an area."""
        areas = self.areas
        return tuple(sorted(self.manifest.concepts, key=lambda c: areas.index(c.area)))

    def in_area(self, area: str) -> tuple[Concept, ...]:
        return tuple(concept for concept in self.concepts if concept.area == area)

    def capstone_of(self, concept: Concept) -> Slot | None:
        """The capstone slot the concept represents, or ``None``."""
        if len(concept.slots) != 1:
            return None
        slot = self.path.curriculum.slot(concept.slots[0])
        return slot if slot is not None and slot.is_capstone else None

    def own_slots(self, concept: Concept) -> tuple[Slot, ...]:
        """The slots whose lessons the concept teaches: all its slots for a
        capstone's concept, and else its slots that are not capstones."""
        slots = [self.path.curriculum.slot(label) for label in concept.slots]
        if self.capstone_of(concept) is not None:
            return tuple(slot for slot in slots if slot is not None)
        return tuple(
            slot for slot in slots if slot is not None and not slot.is_capstone
        )

    @cached_property
    def _filled(self) -> dict[str, Lesson]:
        return {lesson.slot: lesson for lesson in self.path.lessons if lesson.slot}

    def lesson_of(self, slot: Slot) -> Lesson | None:
        return self._filled.get(slot.label)

    def lessons_of(self, concept: Concept) -> tuple[Lesson, ...]:
        """The published lessons that fill the concept's own slots, in the
        order of the curriculum file: never inferred from a title."""
        lessons = [self.lesson_of(slot) for slot in self.own_slots(concept)]
        return self.path.taught(tuple(lesson for lesson in lessons if lesson))

    def planned_of(self, concept: Concept) -> tuple[Slot, ...]:
        return tuple(
            slot for slot in self.own_slots(concept) if self.lesson_of(slot) is None
        )

    def state(self, concept: Concept) -> str:
        if not self.lessons_of(concept):
            return PLANNED
        return PARTLY if self.planned_of(concept) else PUBLISHED

    def concepts_of(self, lesson: Lesson) -> tuple[Concept, ...]:
        """The concepts whose own slots the lesson fills."""
        if not lesson.slot:
            return ()
        return tuple(
            concept
            for concept in self.concepts
            if lesson.slot in {slot.label for slot in self.own_slots(concept)}
        )

    def memberships(self) -> tuple[Membership, ...]:
        """The concepts that name a capstone slot beside their own slots."""
        found = []
        for concept in self.concepts:
            if self.capstone_of(concept) is not None:
                continue
            for label in concept.slots:
                slot = self.path.curriculum.slot(label)
                if slot is not None and slot.is_capstone:
                    found.append(
                        Membership(concept.id, self.manifest.capstone(label).id)
                    )
        return tuple(found)

    # --- The sequences ----------------------------------------------------------

    def _row(self, slot: Slot) -> Row:
        lesson = self.lesson_of(slot)
        description = ""
        if lesson is None and slot.is_capstone:
            description = self.manifest.capstone(slot.label).explanation
        return Row(
            slot.label,
            lesson.title if lesson else slot.title,
            slot.kind,
            lesson,
            description,
            slot.extension,
        )

    @cached_property
    def _beyond(self) -> tuple[Lesson, ...]:
        """The published lessons without a slot: a Lean lesson joins the Lean
        entry, any other the end of its course."""
        return tuple(lesson for lesson in self.path.lessons if not lesson.slot)

    @staticmethod
    def _is_lean(lesson: Lesson) -> bool:
        return "lean" in lesson.methods

    def sequences(self) -> tuple[AtlasSequence, ...]:
        """The eight courses, the four method paths, and the Lean entry, in
        that order: every published lesson is a row of exactly one."""
        return self._sequences

    @cached_property
    def _sequences(self) -> tuple[AtlasSequence, ...]:
        curriculum = self.path.curriculum
        found = []
        for number, course in enumerate(COURSES, start=1):
            slots = curriculum.in_course(course)
            rows = [self._row(slot) for slot in slots if not slot.is_capstone]
            rows += [
                Row("", lesson.title, "lesson", lesson)
                for lesson in self._beyond
                if lesson.course == course.id and not self._is_lean(lesson)
            ]
            # The capstone integrates the course: its row comes last.
            rows += [self._row(slot) for slot in slots if slot.is_capstone]
            entry = self.manifest.sequence(course.id)
            aliases = (
                f"course-{course.id}-lessons",
                *(f"concept-{concept.id}" for concept in self.in_area(course.id)),
            )
            found.append(
                AtlasSequence(
                    course.id,
                    f"course-{course.id}",
                    course.title,
                    "A",
                    number,
                    entry.description,
                    entry.illustration,
                    tuple(rows),
                    aliases,
                )
            )
        for number, method_path in enumerate(curriculum.paths, start=1):
            entry = self.manifest.sequence(method_path.id)
            core = curriculum.core_in_path(method_path)
            # The capstone integrates the path: the last of its core rows,
            # and the optional extensions after the core.
            path_rows = (
                *(self._row(slot) for slot in core if not slot.is_capstone),
                *(self._row(slot) for slot in core if slot.is_capstone),
                *(self._row(s) for s in curriculum.extensions_in_path(method_path)),
            )
            found.append(
                AtlasSequence(
                    method_path.id,
                    f"path-{method_path.id}",
                    method_path.title,
                    "B",
                    number,
                    entry.description,
                    entry.illustration,
                    path_rows,
                    tuple(
                        f"concept-{concept.id}"
                        for concept in self.in_area(method_path.id)
                    ),
                )
            )
        strand = [slot for slot in curriculum.slots if not (slot.course or slot.path)]
        rows = [self._row(slot) for slot in strand]
        rows += [
            Row("", lesson.title, "lesson", lesson)
            for lesson in self._beyond
            if self._is_lean(lesson)
        ]
        found.append(
            AtlasSequence(
                LEAN_ANCHOR,
                LEAN_ANCHOR,
                "Beyond the curriculum: proofs in Lean",
                "",
                0,
                "Lessons that take a result of a course and prove it in Lean,"
                " checked by the machine.",
                "",
                tuple(rows),
            )
        )
        return tuple(found)


# --- The page -------------------------------------------------------------------


def _join(items: Sequence[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


_PART_NAMES = {"A": "Physics by construction", "B": "Physics and AI"}
_PART_KINDS = {"A": "Course", "B": "Method path"}

# The owner's text that opens the atlas under its subtitle (Issue #483,
# 2026-11-11): what Part A and Part B teach, in two paragraphs. The longer
# account of the learning journey stays on About and in the introductions.
ATLAS_INTRODUCTION = (
    "Part A teaches you to understand physical systems through models,"
    " simulations, and experiments. Part B builds on that foundation to"
    " explore how artificial intelligence can support scientific research.",
    "Both follow the same principle: scientific conclusions must be supported"
    " by evidence.",
)
# The link from an open sequence to its introduction (F156), by part.
_INTRODUCTION_LINKS = {
    "A": "Read the course introduction",
    "B": "Read the method path introduction",
}


@dataclass(frozen=True)
class AtlasSection:
    """The atlas of the path page: the owner's two paragraphs and the three
    figures of the curriculum, then one native disclosure per course and
    method path and one for the Lean lessons, in one exclusive group, none
    open at load, each expanding inline beneath its own row; the textual
    equivalent; and the address module. Print it from a cell with
    ``output: asis``."""

    atlas: Atlas
    page: str = PATH_PAGE
    # The sequences that have an introduction (F156): their content links to it.
    introductions: frozenset[str] = frozenset()

    def __str__(self) -> str:
        sequences = self.atlas.sequences()
        items: list[str] = []
        for sequence in sequences:
            if sequence.part and sequence.number == 1:
                items.append(self._part_label(sequence.part))
            items.append(self._sequence(sequence))
        lines = [
            "```{=html}",
            self._opening(),
            '<section class="atlas-sequences" id="atlas"'
            ' aria-label="The courses and method paths">',
            '<div class="atlas" id="choose">',
            *items,
            "</div></section>",
            self._text(),
            f'<script type="module" src="{"../" * self.page.count("/")}'
            f'{escape(ATLAS_SCRIPT)}"></script>',
            "```",
            "",
        ]
        return "\n".join(lines)

    # --- The opening ----------------------------------------------------------

    def figures(self) -> tuple[tuple[int, str], ...]:
        """The three numbers of the opening, each with the singular of its
        label: the physics courses, the AI method paths, and the published
        lessons (every published lesson of the learning path, which is a row
        of exactly one sequence; the extension and Lean lessons among them).
        Derived from the curriculum file and the front matter, never
        written."""
        sequences = self.atlas.sequences()
        return (
            (sum(1 for s in sequences if s.part == "A"), "physics course"),
            (sum(1 for s in sequences if s.part == "B"), "AI method path"),
            (len(self.atlas.path.lessons), "published lesson"),
        )

    def _opening(self) -> str:
        paragraphs = "".join(f"<p>{escape(text)}</p>" for text in ATLAS_INTRODUCTION)
        figures = "".join(
            f'<li><span class="atlas-figure-number">{count}</span> '
            f'<span class="atlas-figure-label">{escape(word)}'
            f"{'' if count == 1 else 's'}</span></li>"
            for count, word in self.figures()
        )
        return (
            f'<div class="atlas-opening">{paragraphs}</div>'
            '<ul class="atlas-figures" aria-label="The curriculum in numbers">'
            f"{figures}</ul>"
        )

    # --- Pieces -------------------------------------------------------------

    def _href(self, to_page: str) -> str:
        return escape(page_href(self.page, to_page))

    def _asset(self, file: str) -> str:
        """A relative link from the page to a file under site/assets/."""
        parent = PurePosixPath(self.page).parent.as_posix()
        return escape(posixpath.relpath(f"{ASSETS}/{file}", parent))

    def _image(
        self, sequence: AtlasSequence, kind: str = "card", eager: bool = True
    ) -> str:
        """The illustration of a sequence at the card size (the atlas's rows)
        or the panel size (the introduction pages), with the densities the
        register names. Its alternative text names it; a Part B
        illustration's says that it shows a toy model."""
        widths = ILLUSTRATION_WIDTHS[kind]
        slot = CARD_SLOT if kind == "card" else PANEL_SLOT
        files = [f"{sequence.illustration}-{kind}-{width}.webp" for width in widths]
        srcset = ", ".join(
            f"{self._asset(file)} {width}w"
            for file, width in zip(files, widths, strict=True)
        )
        alt = f"Illustration of {sequence.title}"
        if sequence.part == "B":
            alt += ": a toy-model example, no agent was run"
        loading = "eager" if eager else "lazy"
        return (
            f'<img class="atlas-{kind}-image" src="{self._asset(files[0])}"'
            f' srcset="{srcset}" sizes="{slot}px" width="{slot}"'
            f' height="{slot * 3 // 4}" alt="{escape(alt)}" loading="{loading}"'
            ' decoding="async">'
        )

    def _part_label(self, part: str) -> str:
        anchor = "courses" if part == "A" else "paths"
        return (
            f'<p class="atlas-part atlas-part-{part.lower()}" id="{anchor}">'
            f'<span class="atlas-part-name">Part {part}</span>'
            f" {escape(_PART_NAMES[part])}</p>"
        )

    def _sequence(self, sequence: AtlasSequence) -> str:
        part = f"atlas-part-{sequence.part.lower()}" if sequence.part else "atlas-lean"
        aliases = (
            f' data-aliases="{" ".join(sequence.aliases)}"' if sequence.aliases else ""
        )
        counts = f"{sequence.published} published"
        if sequence.planned:
            counts += f" · {sequence.planned} planned"
        # One segment per published lesson of the core, which progress.js
        # marks; the stylesheet shows the hairline once a segment is marked.
        ticks = "".join(
            f'<i class="path-link" data-lesson-id="{escape(row.lesson.id)}"></i>'
            for row in sequence.core
            if row.lesson is not None
        )
        card = (
            '<summary class="atlas-card">'
            + (self._image(sequence) if sequence.illustration else "")
            + '<span class="atlas-card-text">'
            f'<span class="atlas-card-title">{escape(sequence.title)}</span>'
            f'<span class="atlas-card-count">{counts}</span>'
            f'<span class="atlas-progress" aria-hidden="true">{ticks}</span>'
            "</span>"
            '<span class="atlas-card-mark" aria-hidden="true"></span>'
            "</summary>"
        )
        head = (
            '<div class="atlas-panel-head">'
            f'<h2 class="atlas-panel-title">{escape(sequence.title)}</h2>'
            f'<p class="atlas-description">{escape(sequence.description)}</p>'
            f"{self._introduction(sequence)}</div>"
        )
        rows = "".join(self._row(row) for row in sequence.core)
        return (
            f'<details class="atlas-sequence {part}" name="atlas"'
            f' id="{sequence.anchor}"{aliases}>'
            f"{card}"
            f'<div class="atlas-panel">{head}'
            f'<ol class="atlas-rows">{rows}</ol>'
            f"{self._extensions(sequence)}</div></details>"
        )

    def _introduction(self, sequence: AtlasSequence) -> str:
        """The link from the open sequence to its introduction, before its
        lessons; nothing for a sequence without one."""
        if sequence.id not in self.introductions or not sequence.part:
            return ""
        href = escape(page_href(self.page, introduction_page(sequence.id)))
        return (
            f'<p class="atlas-introduction"><a href="{href}">'
            f"{_INTRODUCTION_LINKS[sequence.part]}</a></p>"
        )

    def _extensions(self, sequence: AtlasSequence) -> str:
        """The optional extensions of a method path after its core rows: set
        apart by their place and their own heading and counts, never by a
        mark of the row (ADR 022 decision 2). Empty without any."""
        if not sequence.extensions:
            return ""
        counts = f"{sequence.extension_published} published"
        if sequence.extension_planned:
            counts += f", {sequence.extension_planned} planned"
        rows = "".join(self._row(row) for row in sequence.extensions)
        heading = f"{sequence.anchor}-extensions"
        return (
            f'<section class="atlas-extensions" aria-labelledby="{heading}">'
            f'<h3 class="atlas-extensions-title" id="{heading}">Optional'
            " extensions</h3>"
            '<p class="atlas-extensions-note">Depth beside the path, not part'
            f" of its {_plural(len(sequence.core), 'lesson')}: {escape(counts)}.</p>"
            f'<ol class="atlas-rows atlas-rows-extension">{rows}</ol></section>'
        )

    def _row(self, row: Row) -> str:
        """One lesson row: the slot's label, the title (a link only when
        published), the difficulty of the front matter, and the marks in
        words: Lab, Capstone, Lean, planned. A planned row is no link."""
        marks = []
        classes = ["atlas-row"]
        if row.kind == LAB:
            classes.append("atlas-row-lab")
            marks.append('<span class="atlas-mark atlas-mark-lab">Lab</span>')
        if row.is_capstone:
            classes.append("atlas-row-capstone")
            marks.append('<span class="atlas-mark atlas-mark-capstone">Capstone</span>')
        if row.lesson is not None and Atlas._is_lean(row.lesson):
            marks.append('<span class="atlas-mark atlas-mark-lean">Lean</span>')
        label = f'<span class="atlas-label">{escape(row.label)}</span>'
        if row.lesson is None:
            classes.append("planned-slot")
            marks.append('<span class="atlas-mark atlas-mark-planned">planned</span>')
            title = f'<span class="atlas-planned-title">{escape(row.title)}</span>'
            description = (
                f'<p class="capstone-description">{escape(row.description)}</p>'
                if row.description
                else ""
            )
            return (
                f'<li class="{" ".join(classes)}" data-state="planned">{label}'
                f'<span class="atlas-title">{title}{description}</span>'
                f'<span class="atlas-marks">{"".join(marks)}</span></li>'
            )
        classes.insert(0, "path-card")
        level = (
            f'<span class="atlas-level">'
            f"{escape(_DIFFICULTY[row.lesson.difficulty].title)}</span>"
        )
        return (
            f'<li class="{" ".join(classes)}" data-state="published"'
            f' data-lesson-id="{escape(row.lesson.id)}">{label}'
            f'<span class="atlas-title"><a class="lesson-link"'
            f' href="{self._href(row.lesson.page)}">{escape(row.title)}</a></span>'
            f'<span class="atlas-marks">{level}{"".join(marks)}</span></li>'
        )

    def sentences(self) -> list[str]:
        """The atlas in words: every sequence with every lesson and its
        state, a planned capstone with its description."""
        found = []
        for sequence in self.atlas.sequences():
            rows = []
            for row in sequence.rows:
                name = f"{row.label} {row.title}" if row.label else row.title
                kind = f", {row.kind}" if row.kind != "lesson" else ""
                if row.extension:
                    kind += ", optional extension"
                state = "published" if row.lesson is not None else "planned"
                text = f"{name} ({state}{kind})"
                if row.description:
                    text += f", planned description: {row.description}"
                rows.append(text)
            where = (
                f"Part {sequence.part}, {_PART_KINDS[sequence.part].lower()}"
                f" {sequence.number}"
                if sequence.part
                else "beyond the curriculum"
            )
            extensions = (
                f" Optional extensions after the core:"
                f" {sequence.extension_published} published,"
                f" {sequence.extension_planned} planned."
                if sequence.extensions
                else ""
            )
            found.append(
                f"{sequence.title} ({where}): {sequence.published} published,"
                f" {sequence.planned} planned.{extensions} {'; '.join(rows)}."
            )
        return found

    def _text(self) -> str:
        items = "".join(f"<li>{escape(text)}</li>" for text in self.sentences())
        return (
            '<section class="visually-hidden" aria-labelledby="atlas-text-title">'
            '<h2 id="atlas-text-title">The atlas in words</h2>'
            f'<ol class="atlas-text">{items}</ol></section>'
        )


def course_atlas() -> AtlasSection:
    """Return the atlas section of the path page being built."""
    site, page = _page_being_built()
    return AtlasSection(Atlas.read(site), page, introduced(site))


# --- The relationships on a lesson page ----------------------------------------


def connections(atlas: Atlas, lesson: Lesson, page: str) -> list[str]:
    """The relationships of a published lesson's concepts as Markdown items
    for its header (ADR 021 decision 3): each curated conceptual connection
    with its rationale and a link to the other concept's sequence, each
    capstone the concept is a member of, and for a capstone the concepts it
    integrates. Empty for a lesson without a slot or without any."""
    manifest = atlas.manifest
    items: list[str] = []

    def sequence_link(concept: Concept) -> str:
        kind = "course" if concept.area in _COURSE else "path"
        return (
            f"[{atlas.area_title(concept.area)}]"
            f"({page_href(page, PATH_PAGE, f'{kind}-{concept.area}')})"
        )

    def capstone_name(capstone: Concept) -> str:
        slot = atlas.capstone_of(capstone)
        assert slot is not None
        published = atlas.lesson_of(slot)
        if published is not None and published.id != lesson.id:
            return (
                f"{slot.label} [{published.title}]({page_href(page, published.page)})"
            )
        if published is not None:
            return f"{slot.label} {published.title}"
        return f"{slot.label} {slot.title} (planned)"

    for concept in atlas.concepts_of(lesson):
        for connection in manifest.connections:
            if concept.id not in connection.concepts:
                continue
            a, b = (manifest.concept(end) for end in connection.concepts)
            other = b if a == concept else a
            sentence = CONNECTION_TYPES[connection.type].format(
                a=f"*{a.name}*", b=f"*{b.name}*"
            )
            items.append(
                f"{sentence} ({_CONNECTION_WORDS[connection.type]}; see"
                f" {sequence_link(other)}): {connection.rationale}"
            )
        for membership in atlas.memberships():
            if membership.member == concept.id:
                capstone = manifest.concept(membership.capstone)
                items.append(
                    f"*{concept.name}* is part of the capstone project"
                    f" {capstone_name(capstone)}."
                )
        if atlas.capstone_of(concept) is not None:
            members = [
                f"*{manifest.concept(m.member).name}*"
                for m in atlas.memberships()
                if m.capstone == concept.id
            ]
            if members:
                items.append(f"This capstone project integrates {_join(members)}.")
    return items
