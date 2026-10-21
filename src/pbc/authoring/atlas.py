"""The course atlas: the map manifest, what the build derives from it, and
the map as inline SVG with its textual equivalent (ADR 018 decision 3).

The atlas has one source of truth (docs/architecture.md, I31): courses,
paths, and slots come from the curriculum file, publication, titles,
prerequisites, and addresses from the front matter of the lessons, and the
map manifest (``site/atlas.yaml``) adds only what neither holds: concept
identifiers with a short explanation, their placement on the map, the slots
each concept belongs to, and the curated conceptual connections with their
rationale. Everything else is derived here when the path page is built:
the state and the count of a concept from the lessons that fill its slots,
the prerequisite edges between concepts from the lessons' prerequisites,
and capstone membership from the slots a concept names.

The drawing is laid out in plain Python, as the prerequisite graph is, with
no script in the browser and the same output for the same inputs, byte for
byte. Its course illustrations are interface artwork drawn by code (ADR 018
decision 2): one small drawing per course, mapped here from the course, and
referenced nowhere in the manifest.
"""

import heapq
import itertools
import math
import re
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import cached_property
from html import escape
from pathlib import Path

import yaml

from pbc.authoring.path import (
    _COURSE,
    _FRONT_MATTER_FIELDS,
    _METHOD,
    COURSES,
    METHODS,
    PATH_PAGE,
    Curriculum,
    LearningPath,
    Lesson,
    Slot,
    _page_being_built,
)
from pbc.authoring.website import page_href

# Where the manifest sits in the website project, beside the curriculum file.
ATLAS_FILE = "atlas.yaml"

CAPSTONE = "applied capstone"

# The grid of an area of the map: a concept's position is a column and a row.
AREA_COLUMNS = 2
AREA_ROWS = 4

_ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")
_CONCEPT_KEYS = {"id", "area", "position", "slots", "explanation"}
_CONNECTION_KEYS = {"concepts", "type", "rationale"}
# What the curriculum file or a lesson's front matter holds, what the
# generator derives, and what the generator draws: never in the manifest.
_NOT_HERE = {
    *_FRONT_MATTER_FIELDS,
    "title",
    "label",
    "kind",
    "course",
    "path",
    "strand",
    "lesson",
    "state",
    "status",
    "published",
    "count",
    "counts",
    "requires",
    "required-by",
    "capstone",
    "members",
    "illustration",
    "image",
    "icon",
}
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


@dataclass(frozen=True)
class Concept:
    """A concept of the map, as the manifest declares it."""

    id: str
    area: str  # a course id or a path id of the curriculum file
    position: tuple[int, int]  # column, row in the grid of the area
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


def atlas_problems(data: object, curriculum: Curriculum) -> list[str]:
    """Return every way the contents of the map manifest break its rules
    (ADR 018 decision 3): an unknown field, a field the curriculum file or
    the front matter holds, a prerequisite, a reference that does not
    resolve, a concept without a slot or with a slot outside its area, and a
    capstone slot that is not represented by exactly one concept."""
    if not isinstance(data, dict) or set(data) != {"concepts", "connections"}:
        return [
            "the file holds the lists 'concepts' and 'connections', and nothing else"
        ]
    found: list[str] = []
    courses = {course.id for course in COURSES}
    paths = {path.id for path in curriculum.paths}
    slots = {slot.label: slot for slot in curriculum.slots}
    capstones = [slot.label for slot in curriculum.slots if slot.kind == CAPSTONE]

    concepts = data["concepts"]
    if not isinstance(concepts, list):
        found.append("'concepts' must be a list")
        concepts = []
    ids: set[str] = set()
    places: set[tuple[str, int, int]] = set()
    represented: dict[str, list[str]] = {label: [] for label in capstones}
    for item in concepts:
        if not isinstance(item, dict):
            found.append(f"concept entry {item!r} must be a mapping")
            continue
        name = repr(item.get("id"))
        for key in item:
            if key in _CONCEPT_KEYS:
                continue
            if key in _NOT_HERE:
                found.append(
                    f"concept {name}: {key!r} is held by the curriculum file or"
                    " the front matter, or derived by the build, not written in"
                    " the map manifest"
                )
            else:
                found.append(f"concept {name}: {key!r} is not a field of a concept")
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
        if area not in courses and area not in paths:
            found.append(
                f"concept {name}: 'area' {area!r} is not a course or a path of"
                " the curriculum file"
            )
        position = item.get("position")
        if (
            isinstance(position, list)
            and len(position) == 2
            and all(isinstance(number, int) for number in position)
            and 1 <= position[0] <= AREA_COLUMNS
            and 1 <= position[1] <= AREA_ROWS
        ):
            place = (str(area), position[0], position[1])
            if place in places:
                found.append(
                    f"concept {name}: another concept of {area!r} has the"
                    f" position {position}"
                )
            places.add(place)
        else:
            found.append(
                f"concept {name}: 'position' must be [column, row], a column"
                f" from 1 to {AREA_COLUMNS} and a row from 1 to {AREA_ROWS}"
            )
        labels = item.get("slots")
        if not (isinstance(labels, list) and labels):
            found.append(f"concept {name} must name at least one slot in 'slots'")
            continue
        own = []
        for label in labels:
            slot = slots.get(label) if isinstance(label, str) else None
            if slot is None:
                found.append(
                    f"concept {name}: {label!r} is not a slot of the curriculum"
                )
            elif slot.kind == CAPSTONE:
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
                if slots[named[0]].course != area:
                    found.append(
                        f"concept {name} represents {named[0]}, which belongs to"
                        f" {slots[named[0]].course!r}, not to the area {area!r}"
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
        for key in item:
            if key in _CONNECTION_KEYS:
                continue
            if key in _NOT_HERE:
                found.append(
                    f"connection {name}: {key!r} is held by the curriculum file"
                    " or the front matter, or derived by the build, not written"
                    " in the map manifest"
                )
            else:
                found.append(
                    f"connection {name}: {key!r} is not a field of a connection"
                )
        kind = item.get("type")
        if kind in _PREREQUISITE_TYPES:
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
        if not (isinstance(ends, list) and len(ends) == 2):
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


@dataclass(frozen=True)
class AtlasManifest:
    """The map manifest, validated against the curriculum file."""

    concepts: tuple[Concept, ...] = ()
    connections: tuple[Connection, ...] = ()

    @classmethod
    def read(cls, site: Path, curriculum: Curriculum) -> AtlasManifest:
        """Read ``atlas.yaml`` of the website project ``site``; a site without
        the file has an empty manifest, which fails as soon as the
        curriculum has a capstone. Raises ``ValueError`` when the file
        breaks a rule; the message lists every problem."""
        file = site / ATLAS_FILE
        data: object = {"concepts": [], "connections": []}
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{ATLAS_FILE} is not valid YAML: {error}") from None
        return cls.parse(data, curriculum)

    @classmethod
    def parse(cls, data: object, curriculum: Curriculum) -> AtlasManifest:
        found = atlas_problems(data, curriculum)
        if found:
            raise ValueError(
                f"{ATLAS_FILE} breaks the rules of the map manifest:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            tuple(
                Concept(
                    id=item["id"],
                    area=item["area"],
                    position=(item["position"][0], item["position"][1]),
                    slots=tuple(item["slots"]),
                    explanation=" ".join(item["explanation"].split()),
                )
                for item in data["concepts"]
            ),
            tuple(
                Connection(
                    concepts=(item["concepts"][0], item["concepts"][1]),
                    type=item["type"],
                    rationale=" ".join(item["rationale"].split()),
                )
                for item in data["connections"]
            ),
        )

    def concept(self, concept_id: str) -> Concept:
        return next(concept for concept in self.concepts if concept.id == concept_id)

    def capstone(self, label: str) -> Concept:
        """The concept that represents the capstone slot ``label``: its
        explanation is the capstone's planned description."""
        return next(concept for concept in self.concepts if concept.slots == (label,))


# --- What the build derives ---------------------------------------------------


@dataclass(frozen=True)
class PrerequisiteEdge:
    """Concept ``source`` is required by concept ``target``: a lesson of the
    target requires a lesson of the source. ``pairs`` are those lessons, as
    (required lesson id, requiring lesson id)."""

    source: str
    target: str
    pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Membership:
    """Concept ``member`` is integrated by the capstone that ``capstone``
    (a concept) represents."""

    member: str
    capstone: str


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

    @cached_property
    def concepts(self) -> tuple[Concept, ...]:
        """The concepts in the order of the map: area by area (the courses,
        then the paths), and in an area row by row."""
        areas = self.areas
        return tuple(
            sorted(
                self.manifest.concepts,
                key=lambda concept: (
                    areas.index(concept.area),
                    concept.position[1],
                    concept.position[0],
                ),
            )
        )

    @property
    def areas(self) -> list[str]:
        return [course.id for course in COURSES] + [
            path.id for path in self.path.curriculum.paths
        ]

    def area_title(self, area: str) -> str:
        if area in _COURSE:
            return _COURSE[area].title
        return self.path.curriculum.path(area).title

    def in_area(self, area: str) -> tuple[Concept, ...]:
        return tuple(concept for concept in self.concepts if concept.area == area)

    def capstone_of(self, concept: Concept) -> Slot | None:
        """The capstone slot the concept represents, or ``None``."""
        if len(concept.slots) != 1:
            return None
        slot = self.path.curriculum.slot(concept.slots[0])
        return slot if slot is not None and slot.kind == CAPSTONE else None

    def own_slots(self, concept: Concept) -> tuple[Slot, ...]:
        """The slots whose lessons the concept teaches: all its slots for a
        capstone's concept, and else its slots that are not capstones."""
        slots = [self.path.curriculum.slot(label) for label in concept.slots]
        if self.capstone_of(concept) is not None:
            return tuple(slot for slot in slots if slot is not None)
        return tuple(
            slot for slot in slots if slot is not None and slot.kind != CAPSTONE
        )

    @cached_property
    def _filled(self) -> dict[str, Lesson]:
        return {lesson.slot: lesson for lesson in self.path.lessons if lesson.slot}

    def lesson_of(self, slot: Slot) -> Lesson | None:
        return self._filled.get(slot.label)

    @cached_property
    def _lessons(self) -> dict[str, tuple[Lesson, ...]]:
        found = {}
        for concept in self.manifest.concepts:
            lessons = [self.lesson_of(slot) for slot in self.own_slots(concept)]
            found[concept.id] = self.path.taught(
                tuple(lesson for lesson in lessons if lesson)
            )
        return found

    def lessons_of(self, concept: Concept) -> tuple[Lesson, ...]:
        """The published lessons that fill the concept's own slots, in the
        order of the curriculum file: never inferred from a title."""
        return self._lessons[concept.id]

    def planned_of(self, concept: Concept) -> tuple[Slot, ...]:
        return tuple(
            slot for slot in self.own_slots(concept) if self.lesson_of(slot) is None
        )

    def state(self, concept: Concept) -> str:
        if not self.lessons_of(concept):
            return PLANNED
        return PARTLY if self.planned_of(concept) else PUBLISHED

    def state_words(self, concept: Concept) -> str:
        """The state as the node and the panel say it: counts of lessons, the
        planned slots, never a planned slot counted as published."""
        lessons, planned = len(self.lessons_of(concept)), len(self.planned_of(concept))
        if self.capstone_of(concept) is not None:
            return "capstone, " + ("published" if lessons else "planned")
        if not lessons:
            return "planned"
        words = f"{lessons} lesson{'s' if lessons != 1 else ''}"
        return words + (f", {planned} planned" if planned else "")

    def area_counts(self, area: str) -> tuple[int, int]:
        """The published lessons that fill a slot of the area, and its slots."""
        home = [
            slot
            for slot in self.path.curriculum.slots
            if (slot.course or slot.path) == area
        ]
        return sum(1 for slot in home if self.lesson_of(slot)), len(home)

    def concept_of_lesson(self, lesson: Lesson) -> tuple[Concept, ...]:
        return tuple(
            concept for concept in self.concepts if lesson in self.lessons_of(concept)
        )

    @cached_property
    def _prerequisite_edges(self) -> tuple[PrerequisiteEdge, ...]:
        """An edge from concept B to concept A when a lesson of A requires a
        lesson of B; a planned slot has no lesson, so it has no edge."""
        order = {concept.id: number for number, concept in enumerate(self.concepts)}
        found: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for lesson in self.path.lessons:
            for target in self.concept_of_lesson(lesson):
                for required in lesson.prerequisites:
                    for source in self.concept_of_lesson(self.path.lesson(required)):
                        if source.id != target.id:
                            key = (source.id, target.id)
                            found.setdefault(key, []).append((required, lesson.id))
        return tuple(
            PrerequisiteEdge(source, target, tuple(pairs))
            for (source, target), pairs in sorted(
                found.items(),
                key=lambda item: (order[item[0][1]], order[item[0][0]]),
            )
        )

    def prerequisite_edges(self) -> tuple[PrerequisiteEdge, ...]:
        return self._prerequisite_edges

    def memberships(self) -> tuple[Membership, ...]:
        """The concepts that name a capstone slot beside their own slots."""
        found = []
        for concept in self.concepts:
            if self.capstone_of(concept) is not None:
                continue
            for label in concept.slots:
                slot = self.path.curriculum.slot(label)
                if slot is not None and slot.kind == CAPSTONE:
                    found.append(
                        Membership(concept.id, self.manifest.capstone(label).id)
                    )
        return tuple(found)

    def views(self) -> tuple[tuple[str, tuple[Lesson, ...]], ...]:
        """The Lean and method views: every published lesson by its method
        tags from the front matter, the lessons without a slot included;
        Lean first, then the other methods in the order of ``METHODS``."""
        methods = sorted(METHODS, key=lambda method: method.id != "lean")
        return tuple(
            (method.id, self.path.using(method))
            for method in methods
            if self.path.using(method)
        )


# --- The drawing ----------------------------------------------------------------

WIDTH = 1120
MARGIN = 12
AREA_GAP = 28
AREA_WIDTH = (WIDTH - 2 * MARGIN - 3 * AREA_GAP) // 4  # 253
AREA_PAD = 8
AREA_HEADER = 64
NODE_GAP_X = 17
NODE_WIDTH = (AREA_WIDTH - 2 * AREA_PAD - NODE_GAP_X) // 2  # 110
NODE_HEIGHT = 76
NODE_GAP_Y = 30
BAND_GAP = 36  # between the two rows of course areas
HEADING = 40  # the space a layer's heading takes
HEADING_LINE = 20  # a second line of a heading
LAYER_GAP = 28
RAIL = 18  # the rail that joins the four path lanes sits this far above them
VIEW_LABEL = 132  # the column of a view's name
CHIP_WIDTH = 186
CHIP_HEIGHT = 24
CHIP_GAP = 6
NAME_WIDTH = 15  # characters of a concept's name on one line of a node
NAME_LINES = 3
CHIP_CHARACTERS = 28
ILLUSTRATION = 44
# The routing of the edges along the gutters between the nodes.
TRACK = 4  # between two edges side by side in a gutter
PORT = 12  # between two edges at the same side of a node
BEND = 40  # the cost of a turn, in units of length
CROWD = 12  # the cost of a gutter's stretch for each edge already on it
FULL = 400  # the cost of a stretch with no free track left

TITLE_ID = "atlas-title"
DESCRIPTION_ID = "atlas-description"
PREREQUISITE_MARKER = "atlas-arrow-prerequisite"
CONCEPTUAL_MARKER = "atlas-end-conceptual"
CAPSTONE_MARKER = "atlas-end-capstone"


def _number(value: float) -> str:
    """A coordinate, written the same way on every build."""
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _wrap(text: str, width: int, lines: int) -> tuple[list[str], bool]:
    """The lines of a label, and whether it was cut short."""
    found = textwrap.wrap(text, width, break_long_words=False) or [text]
    if len(found) <= lines:
        return found, False
    kept = found[:lines]
    kept[-1] = kept[-1].rstrip(".,;:") + "…"
    return kept, True


def _short(text: str, characters: int) -> tuple[str, bool]:
    if len(text) <= characters:
        return text, False
    cut = text[: characters - 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return cut + "…", True


def _straighten(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """A polyline without repeated points and without points in the middle
    of a straight stretch."""
    kept: list[tuple[float, float]] = []
    for point in points:
        if kept and point == kept[-1]:
            continue
        if len(kept) >= 2:
            (ax, ay), (bx, by) = kept[-2], kept[-1]
            if (bx - ax) * (point[1] - by) == (by - ay) * (point[0] - bx):
                kept[-1] = point
                continue
        kept.append(point)
    return kept


# The course illustrations: interface artwork, one drawing per course of the
# curriculum file, in a box of ILLUSTRATION units. Each shows a system the
# course studies, with its geometry right, and carries no number and no
# caption (ADR 018 decision 2).


def _pendulum() -> str:
    # A pendulum of length 30 at 25 degrees from the vertical, its bob on the
    # arc of its swing, which is centred on the pivot.
    return (
        '<path class="ill-rule" d="M13,5 L31,5"/>'
        '<path class="ill-faint" d="M9.3,32.2 A30,30 0 0 0 34.7,32.2"/>'
        '<path class="ill-line" d="M22,5 L34.7,32.2"/>'
        '<circle class="ill-fill" cx="34.7" cy="32.2" r="4"/>'
    )


def _random_walk() -> str:
    # A walk on a lattice of step 6: every step has the same length and goes
    # along one axis.
    steps = "RURRULURRDRUU"
    x, y = 6.0, 38.0
    points = [f"{_number(x)},{_number(y)}"]
    move = {"R": (6, 0), "L": (-6, 0), "U": (0, -6), "D": (0, 6)}
    for step in steps:
        x, y = x + move[step][0], y + move[step][1]
        points.append(f"{_number(x)},{_number(y)}")
    return (
        f'<polyline class="ill-line" points="{" ".join(points)}"/>'
        '<circle class="ill-fill" cx="6" cy="38" r="2.5"/>'
        f'<circle class="ill-fill" cx="{_number(x)}" cy="{_number(y)}" r="2.5"/>'
    )


def _wave() -> str:
    # A sine wave of wavelength 20 and amplitude 9 about the middle line.
    points = " ".join(
        f"{_number(x)},{_number(22 - 9 * math.sin(2 * math.pi * (x - 4) / 20))}"
        for x in [4 + 0.5 * step for step in range(73)]
    )
    return (
        '<path class="ill-faint" d="M3,22 L41,22"/>'
        f'<polyline class="ill-line" points="{points}"/>'
    )


def _dipole() -> str:
    # The field lines of a pair of opposite charges: symmetric about the axis
    # and about the plane between the charges, from + to -.
    return (
        '<path class="ill-faint" d="M12,22 L32,22"/>'
        '<path class="ill-faint" d="M12,22 Q22,10 32,22"/>'
        '<path class="ill-faint" d="M12,22 Q22,34 32,22"/>'
        '<path class="ill-faint" d="M12,22 Q22,-2 32,22"/>'
        '<path class="ill-faint" d="M12,22 Q22,46 32,22"/>'
        '<circle class="ill-plate" cx="12" cy="22" r="5"/>'
        '<path class="ill-line" d="M9.5,22 L14.5,22 M12,19.5 L12,24.5"/>'
        '<circle class="ill-plate" cx="32" cy="22" r="5"/>'
        '<path class="ill-line" d="M29.5,22 L34.5,22"/>'
    )


def _streamlines() -> str:
    # Streamlines of a steady flow past a cylinder: straight far from it, and
    # bending around it symmetrically upstream and downstream.
    return (
        '<path class="ill-faint" d="M2,6 L42,6 M2,38 L42,38"/>'
        '<path class="ill-faint"'
        ' d="M2,14 C13,14 15,9.5 22,9.5 C29,9.5 31,14 42,14"/>'
        '<path class="ill-faint"'
        ' d="M2,30 C13,30 15,34.5 22,34.5 C29,34.5 31,30 42,30"/>'
        '<path class="ill-faint" d="M2,22 L13,22 M31,22 L42,22"/>'
        '<circle class="ill-line" cx="22" cy="22" r="7"/>'
    )


def _oscillator_levels() -> str:
    # A parabolic potential (a quadratic curve whose control point puts its
    # vertex at y = 38) and the first four levels of the quantum harmonic
    # oscillator: equally spaced, the lowest half a spacing above the bottom,
    # each drawn between the walls of the potential.
    levels = []
    for y in (34, 26, 18, 10):
        half = (8 * (38 - y)) ** 0.5
        levels.append(f"M{_number(22 - half)},{y} L{_number(22 + half)},{y}")
    return (
        '<path class="ill-line" d="M6,6 Q22,70 38,6"/>'
        f'<path class="ill-faint" d="{" ".join(levels)}"/>'
    )


def _orbit() -> str:
    # An ellipse of semi-axes 16 and 10 with the star at a focus, a distance
    # sqrt(16^2 - 10^2) from the centre, and the planet at aphelion.
    return (
        '<ellipse class="ill-faint" cx="22" cy="22" rx="16" ry="10"/>'
        '<circle class="ill-fill" cx="9.5" cy="22" r="3.5"/>'
        '<circle class="ill-line" cx="38" cy="22" r="2.5"/>'
    )


def _lattice() -> str:
    # A square lattice: atoms at the nodes, bonds to the nearest neighbours.
    coordinates = [7 + 10 * step for step in range(4)]
    bonds = " ".join(
        f"M{coordinates[0]},{c} L{coordinates[-1]},{c}"
        f" M{c},{coordinates[0]} L{c},{coordinates[-1]}"
        for c in coordinates
    )
    atoms = "".join(
        f'<circle class="ill-fill" cx="{x}" cy="{y}" r="2.5"/>'
        for y in coordinates
        for x in coordinates
    )
    return f'<path class="ill-faint" d="{bonds}"/>{atoms}'


ILLUSTRATIONS: dict[str, Callable[[], str]] = {
    "mechanics": _pendulum,
    "thermodynamics": _random_walk,
    "waves": _wave,
    "electromagnetism": _dipole,
    "fluids": _streamlines,
    "quantum": _oscillator_levels,
    "astrophysics": _orbit,
    "materials": _lattice,
}


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int

    @property
    def centre(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2


@dataclass(frozen=True)
class Channel:
    """A gutter between the nodes that edges run along: the line at ``at``
    (an x when vertical, a y otherwise) from ``low`` to ``high``, with
    ``room`` units on either side of it for edges side by side."""

    vertical: bool
    at: float
    low: float
    high: float
    room: float


Point = tuple[float, float]

# The sides of a node, and whether an edge leaves each one horizontally.
SIDES = {"left": True, "right": True, "top": False, "bottom": False}
REACH = 40  # the farthest a gutter can be from the side of a node it serves


@dataclass(frozen=True)
class Route:
    """An edge as the gutters it runs along: the side of the node it leaves,
    its runs (a gutter and the grid points it passes there), and the side of
    the node it enters."""

    kind: str
    source: str
    target: str
    detail: str
    start: str
    end: str
    runs: tuple[tuple[int, tuple[Point, ...]], ...]


@dataclass(frozen=True)
class AtlasMap:
    """The layout of the atlas: the course areas, the path lanes, the concept
    nodes, the gutters between them, and the view layer, in SVG user units
    (CSS pixels)."""

    atlas: Atlas
    areas: dict[str, Box]
    nodes: dict[str, Box]
    channels: tuple[Channel, ...]
    rail: tuple[int, int, int]  # y, x from, x to
    headings: tuple[tuple[str, int], ...]  # text, baseline
    views: tuple[tuple[str, Box, tuple[tuple[Lesson, Box], ...]], ...]
    height: int

    @classmethod
    def layout(cls, atlas: Atlas) -> AtlasMap:
        areas: dict[str, Box] = {}
        nodes: dict[str, Box] = {}
        channels: list[Channel] = []
        headings = []
        top = MARGIN
        # The vertical gutters beside and between the areas of a row; their
        # edges keep clear of the areas' rules.
        lines = [
            (MARGIN / 2, MARGIN / 2 - 2),
            *(
                (MARGIN + n * (AREA_WIDTH + AREA_GAP) - AREA_GAP / 2, AREA_GAP / 2 - 2)
                for n in range(1, 4)
            ),
            (WIDTH - MARGIN / 2, MARGIN / 2 - 2),
        ]

        def rows_of(group: Sequence[str]) -> int:
            used = [concept.position[1] for a in group for concept in atlas.in_area(a)]
            return max(used, default=1)

        def place(group: Sequence[str], y: int, below: int) -> int:
            """Place a row of areas at ``y`` with ``below`` units free under
            it, and the gutters between its nodes and under it."""
            rows = rows_of(group)
            grid = y + AREA_HEADER
            height = AREA_HEADER + rows * (NODE_HEIGHT + NODE_GAP_Y) - NODE_GAP_Y
            height += AREA_PAD
            under = y + height + below / 2
            for number, area in enumerate(group):
                x = MARGIN + number * (AREA_WIDTH + AREA_GAP)
                areas[area] = Box(x, y, AREA_WIDTH, height)
                for concept in atlas.in_area(area):
                    column, row = concept.position
                    nodes[concept.id] = Box(
                        x + AREA_PAD + (column - 1) * (NODE_WIDTH + NODE_GAP_X),
                        grid + (row - 1) * (NODE_HEIGHT + NODE_GAP_Y),
                        NODE_WIDTH,
                        NODE_HEIGHT,
                    )
                middle = x + AREA_PAD + NODE_WIDTH + NODE_GAP_X / 2
                channels.append(Channel(True, middle, grid, under, NODE_GAP_X / 2 - 3))
            left, right = lines[0][0], lines[-1][0]
            for row in range(1, rows):
                at = grid + row * (NODE_HEIGHT + NODE_GAP_Y) - NODE_GAP_Y / 2
                channels.append(Channel(False, at, left, right, NODE_GAP_Y / 2 - 5))
            channels.append(Channel(False, under, left, right, below / 2 - 2))
            return y + height

        courses = [course.id for course in COURSES]
        headings.append(("Part A: the eight physics courses", top + 22))
        top += HEADING
        first_row = top
        top = place(courses[:4], top, BAND_GAP) + BAND_GAP
        top = place(courses[4:], top, LAYER_GAP) + LAYER_GAP

        # The heading takes two lines, so that the gutters between the
        # areas pass beside it on their way to the paths.
        paths = [path.id for path in atlas.path.curriculum.paths]
        headings.append(("Part B: physics and AI,", top + 22))
        headings.append(("the four method paths", top + 22 + HEADING_LINE))
        top += HEADING + HEADING_LINE + RAIL
        lanes_top = top
        if paths:
            top = place(paths, top, LAYER_GAP) + LAYER_GAP
        last_gutter = max(c.at for c in channels if not c.vertical)
        channels += [
            Channel(True, at, first_row, last_gutter, room) for at, room in lines
        ]
        first, last = MARGIN + AREA_WIDTH // 2, MARGIN + AREA_WIDTH // 2
        if paths:
            last = MARGIN + (len(paths) - 1) * (AREA_WIDTH + AREA_GAP) + AREA_WIDTH // 2
        rail = (lanes_top - RAIL, first, last)

        views_heading = (
            "The Lean and method views: every published lesson by its methods"
        )
        headings.append((views_heading, top + 22))
        top += HEADING
        per_row = (WIDTH - 2 * MARGIN - VIEW_LABEL) // (CHIP_WIDTH + CHIP_GAP)
        views = []
        for method, lessons in atlas.views():
            rows = max(1, -(-len(lessons) // per_row))
            title_lines, _ = _wrap(_METHOD[method].title, 14, 2)
            height = max(
                rows * (CHIP_HEIGHT + CHIP_GAP) - CHIP_GAP,
                22 + 18 * len(title_lines),
            )
            height += 2 * AREA_PAD
            band = Box(MARGIN, top, WIDTH - 2 * MARGIN, height)
            chips = tuple(
                (
                    lesson,
                    Box(
                        MARGIN
                        + VIEW_LABEL
                        + (number % per_row) * (CHIP_WIDTH + CHIP_GAP),
                        top + AREA_PAD + (number // per_row) * (CHIP_HEIGHT + CHIP_GAP),
                        CHIP_WIDTH,
                        CHIP_HEIGHT,
                    ),
                )
                for number, lesson in enumerate(lessons)
            )
            views.append((method, band, chips))
            top += height + CHIP_GAP
        return cls(
            atlas,
            areas,
            nodes,
            tuple(channels),
            rail,
            tuple(headings),
            tuple(views),
            top - CHIP_GAP + MARGIN,
        )

    # --- Edges --------------------------------------------------------------
    #
    # An edge never crosses a node: it leaves its node at a side, runs along
    # the gutters between the nodes and the areas at right angles, and enters
    # the other node at a side. Each edge has its own track in a gutter it
    # shares and its own point on a side it shares, so two edges never lie
    # on one another. The route is the shortest by length, turns, and the
    # edges already in a gutter, found on the grid of the gutters.

    def _edges(self) -> list[tuple[str, str, str, str]]:
        """Every edge to draw as (kind, source, target, description), with
        the prerequisite edges first, then the connections, then capstone
        membership."""
        atlas = self.atlas
        edges = [
            ("prerequisite", edge.source, edge.target, "")
            for edge in atlas.prerequisite_edges()
        ]
        edges += [
            ("conceptual", *connection.concepts, connection.type)
            for connection in atlas.manifest.connections
        ]
        edges += [
            ("capstone", membership.member, membership.capstone, "")
            for membership in atlas.memberships()
        ]
        return edges

    @cached_property
    def _ports(self) -> dict[tuple[str, str], tuple[int, Point, float]]:
        """For each side of each node that a gutter serves: the gutter, the
        point where an edge leaving that side meets it, and the length of
        that stretch."""
        ports = {}
        for concept, box in self.nodes.items():
            cx, cy = box.centre
            for side, horizontal in SIDES.items():
                best = None
                for index, channel in enumerate(self.channels):
                    if channel.vertical != horizontal:
                        continue
                    along = cy if horizontal else cx
                    if not channel.low <= along <= channel.high:
                        continue
                    distance = {
                        "left": box.x - channel.at,
                        "right": channel.at - box.x - box.width,
                        "top": box.y - channel.at,
                        "bottom": channel.at - box.y - box.height,
                    }[side]
                    if 0 < distance <= REACH and (best is None or distance < best[0]):
                        best = (distance, index)
                if best is not None:
                    distance, index = best
                    at = self.channels[index].at
                    point = (at, cy) if horizontal else (cx, at)
                    ports[(concept, side)] = (index, point, distance)
        return ports

    @cached_property
    def _grid(self) -> dict[Point, list[tuple[Point, int, float]]]:
        """The grid of the gutters: from each point, the next points along
        the gutters through it, with the gutter and the distance."""
        stops: dict[int, set[float]] = {i: set() for i in range(len(self.channels))}
        for i, a in enumerate(self.channels):
            for j, b in enumerate(self.channels):
                if (
                    a.vertical
                    and not b.vertical
                    and b.low <= a.at <= b.high
                    and a.low <= b.at <= a.high
                ):
                    stops[i].add(b.at)
                    stops[j].add(a.at)
        for index, point, _ in self._ports.values():
            stops[index].add(point[1] if self.channels[index].vertical else point[0])
        grid: dict[Point, list[tuple[Point, int, float]]] = {}
        for index, channel in enumerate(self.channels):
            line = sorted(stops[index])
            points = [
                (channel.at, along) if channel.vertical else (along, channel.at)
                for along in line
            ]
            for a, b, la, lb in zip(points, points[1:], line, line[1:], strict=False):
                grid.setdefault(a, []).append((b, index, lb - la))
                grid.setdefault(b, []).append((a, index, lb - la))
        return grid

    def _route(
        self,
        kind: str,
        source: str,
        target: str,
        detail: str,
        load: dict[frozenset[Point], int],
    ) -> Route:
        """The cheapest route of one edge on the grid of the gutters."""
        # A state is a point of the grid and the way the route arrived
        # there (vertical, horizontal, or None at the start).
        heap: list[tuple[float, int, Point, bool | None]] = []
        best: dict[tuple[Point, bool | None], float] = {}
        back: dict[tuple[Point, bool | None], tuple[Point, bool | None, int] | None]
        back = {}
        start_side: dict[Point, str] = {}
        ends: dict[Point, list[tuple[str, float]]] = {}
        for (concept, side), (_, point, distance) in self._ports.items():
            if concept == target:
                ends.setdefault(point, []).append((side, distance))
        order = 0
        for (concept, side), (_, point, distance) in self._ports.items():
            if concept != source:
                continue
            state = (point, None)
            if distance < best.get(state, math.inf):
                best[state] = distance
                back[state] = None
                start_side[point] = side
                heapq.heappush(heap, (distance, order, point, None))
                order += 1
        found = None
        while heap:
            cost, _, point, direction = heapq.heappop(heap)
            if cost > best[(point, direction)]:
                continue
            if found is not None and cost >= found[0]:
                break
            for side, distance in ends.get(point, []):
                turn = BEND if direction is not None and direction != SIDES[side] else 0
                total = cost + distance + turn
                if found is None or total < found[0]:
                    found = (total, point, direction, side)
            for following, index, length in self._grid.get(point, []):
                way = self.channels[index].vertical
                used = load.get(frozenset((point, following)), 0)
                step = length + CROWD * used
                if used >= self.channels[index].room * 2 // TRACK + 1:
                    step += FULL
                if direction is not None and way != direction:
                    step += BEND
                state = (following, way)
                if cost + step < best.get(state, math.inf):
                    best[state] = cost + step
                    back[state] = (point, direction, index)
                    heapq.heappush(heap, (cost + step, order, following, way))
                    order += 1
        if found is None:
            raise ValueError(f"no route on the map from {source} to {target}")
        _, point, direction, end = found
        steps: list[tuple[Point, int]] = []
        state: tuple[Point, bool | None] = (point, direction)
        while back[state] is not None:
            previous, way, index = back[state]
            steps.append((state[0], index))
            state = (previous, way)
        steps.reverse()
        first = state[0]
        for (a, _), (b, _) in zip([(first, 0), *steps], steps, strict=False):
            load[frozenset((a, b))] = load.get(frozenset((a, b)), 0) + 1
        start = start_side[first]
        runs: list[tuple[int, list[Point]]] = []
        if not steps:
            runs.append((self._ports[(source, start)][0], [first]))
        for point, index in steps:
            if runs and runs[-1][0] == index:
                runs[-1][1].append(point)
            else:
                origin = runs[-1][1][-1] if runs else first
                runs.append((index, [origin, point]))
        return Route(
            kind,
            source,
            target,
            detail,
            start,
            end,
            tuple((index, tuple(points)) for index, points in runs),
        )

    @cached_property
    def routes(self) -> tuple[tuple[Route, tuple[Point, ...]], ...]:
        """Every edge with the points of its drawn line: from a side of one
        node, along its own tracks in the gutters, to a side of the other."""
        load: dict[frozenset[Point], int] = {}
        routes = [self._route(*edge, load) for edge in self._edges()]

        # The point of each edge on a node's side, in the order the edges
        # head off, so that they leave it side by side without crossing. Two
        # sides that face each other across a gutter share their points.
        at_side: dict[Point, list[tuple[float, int, int]]] = {}
        facing: dict[Point, tuple[str, str]] = {}
        for number, route in enumerate(routes):
            for end, (concept, side, run) in enumerate(
                (
                    (route.source, route.start, route.runs[0]),
                    (route.target, route.end, route.runs[-1]),
                )
            ):
                far = run[1][-1] if end == 0 else run[1][0]
                axis = 1 if SIDES[side] else 0
                heading = far[axis]
                if heading == self._ports[(concept, side)][1][axis]:
                    other = route.target if end == 0 else route.source
                    heading = self.nodes[other].centre[axis]
                meeting = self._ports[(concept, side)][1]
                at_side.setdefault(meeting, []).append((heading, number, end))
                facing.setdefault(meeting, (concept, side))
        port: dict[tuple[int, int], float] = {}
        for meeting, items in at_side.items():
            concept, side = facing[meeting]
            box = self.nodes[concept]
            axis = 1 if SIDES[side] else 0
            length = box.height if SIDES[side] else box.width
            centre = box.centre[axis]
            spacing = min(PORT, (length - 20) / max(len(items) - 1, 1))
            for rank, (_, number, end) in enumerate(sorted(items)):
                port[(number, end)] = centre + (rank - (len(items) - 1) / 2) * spacing

        # The track of each run in its gutter: runs that overlap get their
        # own tracks, spread about the middle of the gutter.
        spans: dict[int, list[tuple[float, float, int, int]]] = {}
        for number, route in enumerate(routes):
            for order, (index, points) in enumerate(route.runs):
                axis = 1 if self.channels[index].vertical else 0
                along = [p[axis] for p in points]
                if order == 0:
                    along.append(port[(number, 0)])
                if order == len(route.runs) - 1:
                    along.append(port[(number, 1)])
                spans.setdefault(index, []).append(
                    (min(along), max(along), number, order)
                )
        offset: dict[tuple[int, int], float] = {}
        for index, items in spans.items():
            tracks: list[float] = []
            chosen = []
            for low, high, number, order in sorted(items):
                for track, end in enumerate(tracks):
                    if end + PORT / 2 < low:
                        tracks[track] = high
                        break
                else:
                    track = len(tracks)
                    tracks.append(high)
                chosen.append((number, order, track))
            room = self.channels[index].room
            spacing = min(TRACK, 2 * room / max(len(tracks) - 1, 1))
            for number, order, track in chosen:
                offset[(number, order)] = (track - (len(tracks) - 1) / 2) * spacing

        drawn = []
        for number, route in enumerate(routes):
            lines = []
            for order, (index, _) in enumerate(route.runs):
                channel = self.channels[index]
                lines.append((channel.vertical, channel.at + offset[(number, order)]))
            points = [self._on_side(route.source, route.start, port[(number, 0)])]
            vertical, at = lines[0]
            points.append(
                (at, port[(number, 0)]) if vertical else (port[(number, 0)], at)
            )
            for (vertical, at), (_, following) in itertools.pairwise(lines):
                points.append((at, following) if vertical else (following, at))
            vertical, at = lines[-1]
            points.append(
                (at, port[(number, 1)]) if vertical else (port[(number, 1)], at)
            )
            points.append(self._on_side(route.target, route.end, port[(number, 1)]))
            drawn.append((route, _straighten(points)))
        return tuple(drawn)

    def _on_side(self, concept: str, side: str, along: float) -> Point:
        box = self.nodes[concept]
        return {
            "left": (box.x, along),
            "right": (box.x + box.width, along),
            "top": (along, box.y),
            "bottom": (along, box.y + box.height),
        }[side]

    # --- SVG ----------------------------------------------------------------

    def svg(self, href: Callable[[Lesson], str], summary: str) -> str:
        atlas = self.atlas
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" class="atlas-svg"'
            f' viewBox="0 0 {WIDTH} {self.height}"'
            f' width="{WIDTH}" height="{self.height}"'
            f' aria-labelledby="{TITLE_ID} {DESCRIPTION_ID}">',
            f'<title id="{TITLE_ID}">Course atlas: the concepts of the curriculum'
            " and how they connect</title>",
            f'<desc id="{DESCRIPTION_ID}">{escape(summary)}</desc>',
            "<defs>",
            f'<marker id="{PREREQUISITE_MARKER}" viewBox="0 0 10 10" refX="9"'
            ' refY="5" markerWidth="8" markerHeight="8" orient="auto">'
            '<path class="atlas-arrowhead" d="M0,0 L10,5 L0,10 z"/></marker>',
            f'<marker id="{CONCEPTUAL_MARKER}" viewBox="0 0 10 10" refX="5"'
            ' refY="5" markerWidth="7" markerHeight="7" orient="auto">'
            '<circle class="atlas-open-end" cx="5" cy="5" r="3.5"/></marker>',
            f'<marker id="{CAPSTONE_MARKER}" viewBox="0 0 12 12" refX="11"'
            ' refY="6" markerWidth="10" markerHeight="10" orient="auto">'
            '<path class="atlas-open-end" d="M1,6 L6,1.5 L11,6 L6,10.5 z"/>'
            "</marker>",
            "</defs>",
        ]
        for text, baseline in self.headings:
            parts.append(
                f'<text class="atlas-heading" x="{MARGIN}" y="{baseline}">'
                f"{escape(text)}</text>"
            )

        # The areas: a course or a path, its title, its count, its drawing.
        for area, box in self.areas.items():
            published, slots = atlas.area_counts(area)
            title_lines, _ = _wrap(atlas.area_title(area), 24, 2)
            kind = "course" if area in _COURSE else "path"
            parts.append(
                f'<g class="atlas-area atlas-{kind}" data-area="{escape(area)}">'
                f'<rect class="atlas-area-box" x="{box.x}" y="{box.y}"'
                f' width="{box.width}" height="{box.height}"/>'
                f'<text class="atlas-area-title" x="{box.x + AREA_PAD}"'
                f' y="{box.y + 22}">'
                + "".join(
                    f'<tspan x="{box.x + AREA_PAD}" dy="{0 if n == 0 else 18}">'
                    f"{escape(line)}</tspan>"
                    for n, line in enumerate(title_lines)
                )
                + "</text>"
                f'<text class="atlas-area-count" x="{box.x + AREA_PAD}"'
                f' y="{box.y + AREA_HEADER - 10}">'
                f"{published} of {slots} slots published</text>"
            )
            if area in ILLUSTRATIONS:
                left = box.x + box.width - AREA_PAD - ILLUSTRATION
                parts.append(
                    f'<g class="atlas-illustration" aria-hidden="true"'
                    f' transform="translate({left},{box.y + 8})">'
                    f"{ILLUSTRATIONS[area]()}</g>"
                )
            parts.append("</g>")

        # The rail that joins the method paths into one layer.
        y, x1, x2 = self.rail
        if len(atlas.path.curriculum.paths) > 1:
            ticks = "".join(
                f" M{box.x + box.width // 2},{y} L{box.x + box.width // 2},{box.y}"
                for area, box in self.areas.items()
                if area not in _COURSE
            )
            parts.append(
                f'<path class="atlas-rail" aria-hidden="true"'
                f' d="M{x1},{y} L{x2},{y}{ticks}"/>'
            )

        # The edges, under the nodes.
        markers = {
            "prerequisite": f'marker-end="url(#{PREREQUISITE_MARKER})"',
            "conceptual": f'marker-start="url(#{CONCEPTUAL_MARKER})"'
            f' marker-end="url(#{CONCEPTUAL_MARKER})"',
            "capstone": f'marker-end="url(#{CAPSTONE_MARKER})"',
        }
        parts.append('<g class="atlas-edges" aria-hidden="true">')
        for route, points in self.routes:
            kind = route.kind
            extra = f' data-type="{escape(route.detail)}"' if route.detail else ""
            line = " L".join(f"{_number(x)},{_number(y)}" for x, y in points)
            parts.append(
                f'<path class="atlas-edge atlas-edge-{kind}" data-kind="{kind}"'
                f' data-from="{route.source}" data-to="{route.target}"{extra}'
                f' d="M{line}" {markers[kind]}/>'
            )
        parts.append("</g>")

        # The concept nodes: each a link to its panel, never to a lesson.
        parts.append('<g class="atlas-nodes">')
        for concept in atlas.concepts:
            box = self.nodes[concept.id]
            state = atlas.state(concept)
            capstone = atlas.capstone_of(concept) is not None
            lines, _ = _wrap(concept.name, NAME_WIDTH, NAME_LINES)
            words = atlas.state_words(concept)
            label = f"{concept.name}, {words}"
            classes = f"atlas-node atlas-{state.replace(' ', '-')}"
            if capstone:
                classes += " atlas-capstone"
            outline = (
                f'<rect class="atlas-node-box" x="{box.x}" y="{box.y}"'
                f' width="{box.width}" height="{box.height}"/>'
            )
            if capstone:
                outline += (
                    f'<rect class="atlas-node-inner" x="{box.x + 3}" y="{box.y + 3}"'
                    f' width="{box.width - 6}" height="{box.height - 6}"/>'
                )
            text_top = box.y + 20
            parts.append(
                f'<a href="#concept-{concept.id}" class="{classes}"'
                f' data-concept="{concept.id}" data-concept-state="{state}"'
                f' aria-label="{escape(label)}">'
                + outline
                + f'<text class="atlas-node-name" x="{box.x + 8}" y="{text_top}">'
                + "".join(
                    f'<tspan x="{box.x + 8}" dy="{0 if n == 0 else 15}">'
                    f"{escape(line)}</tspan>"
                    for n, line in enumerate(lines)
                )
                + "</text>"
                f'<text class="atlas-node-state" x="{box.x + 8}"'
                f' y="{box.y + box.height - 9}">{escape(words)}</text>' + "</a>"
            )
        parts.append("</g>")

        # The Lean and method views: every published lesson, by its methods.
        parts.append('<g class="atlas-views">')
        for method, band, chips in self.views:
            title_lines, _ = _wrap(_METHOD[method].title, 14, 2)
            parts.append(
                f'<g class="atlas-view" data-method="{escape(method)}">'
                f'<rect class="atlas-view-box" x="{band.x}" y="{band.y}"'
                f' width="{band.width}" height="{band.height}"/>'
                f'<text class="atlas-view-title" x="{band.x + AREA_PAD}"'
                f' y="{band.y + AREA_PAD + 16}">'
                + "".join(
                    f'<tspan x="{band.x + AREA_PAD}" dy="{0 if n == 0 else 18}">'
                    f"{escape(line)}</tspan>"
                    for n, line in enumerate(title_lines)
                )
                + "</text>"
                f'<text class="atlas-area-count" x="{band.x + AREA_PAD}"'
                f' y="{band.y + AREA_PAD + 16 + 18 * len(title_lines)}">{len(chips)}'
                f" lesson{'s' if len(chips) != 1 else ''}</text>"
            )
            for lesson, chip in chips:
                text, cut = _short(lesson.title, CHIP_CHARACTERS)
                label = f' aria-label="{escape(lesson.title)}"' if cut else ""
                parts.append(
                    f'<a href="{escape(href(lesson))}" class="atlas-lesson"'
                    f' data-lesson="{lesson.id}"{label}>'
                    f'<rect class="atlas-lesson-box" x="{chip.x}" y="{chip.y}"'
                    f' width="{chip.width}" height="{chip.height}"/>'
                    f'<text x="{chip.x + 8}" y="{chip.y + 16}">{escape(text)}</text>'
                    "</a>"
                )
            parts.append("</g>")
        parts.append("</g></svg>")
        return "\n".join(parts)


# --- The page -------------------------------------------------------------------


def _join(items: Sequence[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


@dataclass(frozen=True)
class AtlasSection:
    """The atlas section of the path page: the breadcrumb, the switch, the
    map with its legend, the capstone projects, a panel per concept, and the
    textual equivalent. Print it from a cell with ``output: asis`` before
    the course index."""

    atlas: Atlas
    page: str = PATH_PAGE

    def __str__(self) -> str:
        atlas = self.atlas
        layout = AtlasMap.layout(atlas)
        published = sum(len(atlas.lessons_of(c)) for c in atlas.concepts)
        planned = sum(
            len(atlas.planned_of(c))
            for c in atlas.concepts
            if atlas.capstone_of(c) is None
        )
        summary = (
            f"{len(atlas.concepts)} concepts in the eight courses and the four"
            f" method paths, with {len(atlas.prerequisite_edges())} prerequisite"
            f" links, {len(atlas.manifest.connections)} conceptual connections,"
            f" and {len(atlas.memberships())} capstone memberships, and the"
            " published lessons by their methods. The atlas is described in"
            " words after the drawing, and each concept has a panel below it."
        )
        lines = [
            "```{=html}",
            '<nav class="pbc-breadcrumb" aria-label="Breadcrumb"><ol>'
            f'<li><a href="{escape(page_href(self.page, "index.qmd"))}">Home</a></li>'
            '<li><span aria-current="page">Learning path</span></li></ol></nav>',
            "```",
            "",
            "## Course atlas {#atlas}",
            "",
            "```{=html}",
            '<nav class="atlas-switch" aria-label="Map or course index"><ul>'
            '<li><a href="#atlas-map">Map</a></li>'
            '<li><a href="#choose">Course index</a></li>'
            '<li><a href="#atlas-concepts">Concepts</a></li></ul></nav>',
            "```",
            "",
            "A map of the reference curriculum: the eight physics courses of"
            " Part A, the four method paths of Part B, and the methods that cut"
            " across them. Each box is a concept and opens its panel, with its"
            f" explanation and its lessons. Today {published} lessons fill a"
            f" slot of a concept, and {planned} slots are planned. On a narrow"
            " screen the map scrolls sideways in its box, and the course index"
            " is the quicker route.",
            "",
            "```{=html}",
            self._legend(),
            "```",
            "",
            "::: {.column-page}",
            "```{=html}",
            '<div class="atlas-map" id="atlas-map" tabindex="0" role="region"'
            ' aria-label="Course atlas, scrolls in its box">'
            + layout.svg(lambda lesson: page_href(self.page, lesson.page), summary)
            + "</div>",
            "```",
            ":::",
            "",
            "```{=html}",
            self._capstones(),
            self._panels(),
            self._text(),
            "```",
            "",
        ]
        return "\n".join(lines)

    # --- Pieces -------------------------------------------------------------

    def _lesson_link(self, lesson: Lesson) -> str:
        return (
            f'<a href="{escape(page_href(self.page, lesson.page))}">'
            f"{escape(lesson.title)}</a>"
        )

    def _concept_link(self, concept: Concept) -> str:
        return f'<a href="#concept-{concept.id}">{escape(concept.name)}</a>'

    def _legend(self) -> str:
        def sample(path: str) -> str:
            return (
                '<svg aria-hidden="true" width="64" height="16" viewBox="0 0 64 16">'
                f"{path}</svg>"
            )

        items = [
            (
                sample(
                    '<path class="atlas-edge atlas-edge-prerequisite" d="M2,8 L54,8"/>'
                    '<path class="atlas-arrowhead" d="M52,3 L62,8 L52,13 z"/>'
                ),
                "<strong>Prerequisite</strong>: a solid line with a filled"
                " arrowhead, from a concept to one whose lessons require its"
                " lessons; generated from the lessons.",
            ),
            (
                sample(
                    '<path class="atlas-edge atlas-edge-conceptual" d="M8,8 L56,8"/>'
                    '<circle class="atlas-open-end" cx="6" cy="8" r="3.5"/>'
                    '<circle class="atlas-open-end" cx="58" cy="8" r="3.5"/>'
                ),
                "<strong>Conceptual connection</strong>: a dashed line with an"
                " open circle at each end, a scientific relationship with its"
                " reason in the panels.",
            ),
            (
                sample(
                    '<path class="atlas-edge atlas-edge-capstone" d="M2,8 L50,8"/>'
                    '<path class="atlas-open-end" d="M50,8 L56,3 L62,8 L56,13 z"/>'
                ),
                "<strong>Capstone membership</strong>: a dotted line with an"
                " open diamond, from a concept to the capstone project that"
                " integrates it.",
            ),
            (
                sample(
                    '<rect class="atlas-legend-planned" x="2" y="2" width="60"'
                    ' height="12"/>'
                ),
                "<strong>Planned</strong>: a dashed box, the name in italics,"
                " and the word planned; no lesson yet, nothing counted.",
            ),
        ]
        return (
            '<ul class="atlas-legend">'
            + "".join(f"<li>{svg} {text}</li>" for svg, text in items)
            + "</ul>"
        )

    def _capstones(self) -> str:
        atlas = self.atlas
        items = []
        for concept in atlas.concepts:
            slot = atlas.capstone_of(concept)
            if slot is None:
                continue
            lesson = atlas.lesson_of(slot)
            if lesson is not None:
                name = self._lesson_link(lesson)
                state = "Published."
            else:
                name = escape(slot.title)
                state = "Planned, not published."
            items.append(
                f'<li class="atlas-capstone-item" data-slot="{slot.label}">'
                f'<p class="atlas-capstone-name"><span class="atlas-label">'
                f"{slot.label}</span> {name}"
                f' <span class="atlas-capstone-state">{state}</span></p>'
                f'<p class="capstone-description">{escape(concept.explanation)}</p>'
                f'<p class="atlas-capstone-more">On the map: '
                f"{self._concept_link(concept)}.</p></li>"
            )
        if not items:
            return ""
        return (
            '<section class="atlas-capstones" aria-labelledby="atlas-capstones">'
            '<h3 id="atlas-capstones">Capstone projects</h3>'
            '<ul class="atlas-capstone-list">' + "".join(items) + "</ul></section>"
        )

    def _slot_item(self, slot: Slot) -> str:
        lesson = self.atlas.lesson_of(slot)
        if lesson is not None:
            return (
                f'<li data-slot-state="published"><span class="atlas-label">'
                f"{slot.label}</span> {self._lesson_link(lesson)}</li>"
            )
        return (
            f'<li data-slot-state="planned"><span class="atlas-label">'
            f"{slot.label}</span> {escape(slot.title)}"
            ' <span class="atlas-planned-word">(planned, not published)</span></li>'
        )

    def _panel(self, concept: Concept) -> str:
        atlas = self.atlas
        manifest = atlas.manifest
        facts = [
            ("Area", escape(atlas.area_title(concept.area))),
            (
                "Slots",
                '<ul class="atlas-slots">'
                + "".join(self._slot_item(slot) for slot in atlas.own_slots(concept))
                + "</ul>",
            ),
        ]
        connections = []
        for connection in manifest.connections:
            if concept.id not in connection.concepts:
                continue
            a, b = (manifest.concept(end) for end in connection.concepts)
            sentence = CONNECTION_TYPES[connection.type].format(
                a=self._concept_link(a) if a != concept else escape(a.name),
                b=self._concept_link(b) if b != concept else escape(b.name),
            )
            connections.append(
                f"<li>{sentence} ({_CONNECTION_WORDS[connection.type]}):"
                f" {escape(connection.rationale)}</li>"
            )
        if connections:
            facts.append(("Connections", f"<ul>{''.join(connections)}</ul>"))
        requires, required_by = [], []
        for edge in atlas.prerequisite_edges():
            if edge.target == concept.id:
                requires.append(self._concept_link(manifest.concept(edge.source)))
            elif edge.source == concept.id:
                required_by.append(self._concept_link(manifest.concept(edge.target)))
        if requires:
            facts.append(("Builds on", _join(requires)))
        if required_by:
            facts.append(("Needed by", _join(required_by)))
        members = [m for m in atlas.memberships() if m.member == concept.id]
        if members:
            facts.append(
                (
                    "Capstone",
                    _join(
                        [
                            self._concept_link(manifest.concept(m.capstone))
                            for m in members
                        ]
                    ),
                )
            )
        if atlas.capstone_of(concept) is not None:
            integrated = [
                self._concept_link(manifest.concept(m.member))
                for m in atlas.memberships()
                if m.capstone == concept.id
            ]
            if integrated:
                facts.append(("Integrates", _join(integrated)))
        state = atlas.state(concept)
        description = (
            '<p class="capstone-description">'
            if atlas.capstone_of(concept) is not None
            else "<p>"
        )
        return (
            f'<details class="concept-panel" id="concept-{concept.id}"'
            f' data-concept-state="{state}">'
            f'<summary><span class="concept-name">{escape(concept.name)}</span>'
            f' <span class="concept-state">{escape(atlas.state_words(concept))}'
            "</span></summary>"
            f'<div class="concept-body">{description}'
            f"{escape(concept.explanation)}</p><dl>"
            + "".join(f"<dt>{term}</dt><dd>{value}</dd>" for term, value in facts)
            + "</dl></div></details>"
        )

    def _panels(self) -> str:
        atlas = self.atlas
        groups = []
        for area in atlas.areas:
            concepts = atlas.in_area(area)
            if not concepts:
                continue
            groups.append(
                f'<div class="atlas-panel-group" data-area="{escape(area)}">'
                f"<h4>{escape(atlas.area_title(area))}</h4>"
                + "".join(self._panel(concept) for concept in concepts)
                + "</div>"
            )
        return (
            '<section class="atlas-concepts" id="atlas-concepts"'
            ' aria-labelledby="atlas-concepts-title">'
            '<h3 id="atlas-concepts-title">Concepts</h3>'
            "<p>Each concept of the map, by course and path. Open one for its"
            " explanation, its slots and lessons, and its connections.</p>"
            f'<div class="atlas-panels">{"".join(groups)}</div></section>'
        )

    def sentences(self) -> list[str]:
        """The atlas in words: every concept with its area, its slots and
        their state, every edge, and every lesson of the views."""
        atlas = self.atlas
        manifest = atlas.manifest
        found = []
        for concept in atlas.concepts:
            slots = []
            for slot in atlas.own_slots(concept):
                lesson = atlas.lesson_of(slot)
                slots.append(
                    f"{slot.label} {lesson.title} (published)"
                    if lesson
                    else f"{slot.label} {slot.title} (planned)"
                )
            capstone = atlas.capstone_of(concept)
            if capstone is not None:
                state = "published" if atlas.lesson_of(capstone) else "planned"
                found.append(
                    f"Concept {concept.name}, in {atlas.area_title(concept.area)}:"
                    f" the capstone project {capstone.label}, {state}. Planned"
                    f" description: {concept.explanation}"
                )
                continue
            found.append(
                f"Concept {concept.name}, in {atlas.area_title(concept.area)},"
                f" {atlas.state(concept)} ({atlas.state_words(concept)}):"
                f" {concept.explanation} Slots: {'; '.join(slots)}."
            )
        for edge in atlas.prerequisite_edges():
            source = manifest.concept(edge.source)
            target = manifest.concept(edge.target)
            because = "; ".join(
                f"{atlas.path.lesson(b).title} requires {atlas.path.lesson(a).title}"
                for a, b in edge.pairs
            )
            found.append(
                f"Prerequisite: {target.name} requires {source.name}, because"
                f" {because}."
            )
        for connection in manifest.connections:
            a, b = (manifest.concept(end) for end in connection.concepts)
            found.append(
                f"Conceptual connection, {_CONNECTION_WORDS[connection.type]}: "
                + CONNECTION_TYPES[connection.type].format(a=a.name, b=b.name)
                + f". {connection.rationale}"
            )
        for membership in atlas.memberships():
            member = manifest.concept(membership.member)
            capstone = manifest.concept(membership.capstone)
            slot = atlas.capstone_of(capstone)
            assert slot is not None
            state = "published" if atlas.lesson_of(slot) else "planned"
            found.append(
                f"Capstone membership: {member.name} is part of the capstone"
                f" project {capstone.name} ({slot.label}, {state})."
            )
        for method, lessons in atlas.views():
            titles = [lesson.title for lesson in lessons]
            found.append(
                f"The view {_METHOD[method].title} lists {len(titles)}"
                f" lesson{'s' if len(titles) != 1 else ''}: {_join(titles)}."
            )
        return found

    def _text(self) -> str:
        items = "".join(f"<li>{escape(text)}</li>" for text in self.sentences())
        return (
            '<section class="visually-hidden" aria-labelledby="atlas-text-title">'
            '<h3 id="atlas-text-title">The atlas in words</h3>'
            f'<ol class="atlas-text">{items}</ol></section>'
        )


def course_atlas() -> AtlasSection:
    """Return the atlas section of the path page being built."""
    site, page = _page_being_built()
    return AtlasSection(Atlas.read(site), page)
