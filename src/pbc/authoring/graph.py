"""The prerequisite graph of the learning path, as one inline SVG.

The graph is computed when the learning path page is built, from the same
lessons as the rest of the page (docs/architecture.md, "Lesson model"): a
layered layout of the prerequisite DAG in plain Python, no script in the
browser, and the same output for the same lessons, byte for byte. A node is
a lesson and links to it. An arrow points from a prerequisite to the lesson
that requires it (solid), and from a lesson to a related lesson it
recommends (dashed). The text list of the same edges is the accessible
alternative to the drawing.
"""

import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pbc.authoring.path import Course, Lesson

REQUIRES = "requires"
RELATED = "related"

# Geometry, in SVG user units, which are CSS pixels at the natural size.
NODE_WIDTH = 176
NODE_HEIGHT = 64
COLUMN_GAP = 72
ROW_GAP = 20
BAND_GAP = 24
BAND_LABEL = 28
MARGIN = 12
# Offset that separates a related edge from a required edge between the same
# two lessons.
PAIR_OFFSET = 7
LINE_WIDTH = 20  # characters of a title on one line of a node
LINES = 3
SWEEPS = 4

TITLE_ID = "prerequisite-graph-title"
DESCRIPTION_ID = "prerequisite-graph-description"
REQUIRES_MARKER = "prerequisite-graph-requires"
RELATED_MARKER = "prerequisite-graph-related"


@dataclass(frozen=True)
class Edge:
    """An arrow of the graph, from ``source`` to ``target`` (lesson ids)."""

    source: str
    target: str
    kind: str  # REQUIRES or RELATED


@dataclass(frozen=True)
class Node:
    lesson: Lesson
    layer: int  # column
    x: int
    y: int


@dataclass(frozen=True)
class Band:
    """The strip of one course."""

    course: Course
    y: int
    height: int


def edges_of(lessons: Sequence[Lesson]) -> tuple[Edge, ...]:
    """The edges the front matter of ``lessons``, given in path order, states:
    each prerequisite is an arrow into the lesson that requires it, each
    related lesson an arrow out of the lesson that lists it. Ordered by the
    lesson the sentence of the text list is about."""
    known = {lesson.id for lesson in lessons}
    edges = []
    for lesson in lessons:
        edges += [
            Edge(prerequisite, lesson.id, REQUIRES)
            for prerequisite in lesson.prerequisites
            if prerequisite in known
        ]
        edges += [
            Edge(lesson.id, related, RELATED)
            for related in lesson.related
            if related in known
        ]
    return tuple(edges)


def _layers(lessons: Sequence[Lesson]) -> dict[str, int]:
    """A lesson stands one column right of its furthest prerequisite. The
    lessons are in path order, so prerequisites are laid out first."""
    layer: dict[str, int] = {}
    for lesson in lessons:
        before = [layer[item] for item in lesson.prerequisites if item in layer]
        layer[lesson.id] = 1 + max(before) if before else 0
    return layer


@dataclass(frozen=True)
class PrerequisiteGraph:
    """The layout of the lessons, in path order, as columns and course bands."""

    nodes: tuple[Node, ...]
    bands: tuple[Band, ...]
    edges: tuple[Edge, ...]
    width: int
    height: int

    @classmethod
    def layout(
        cls, lessons: Sequence[Lesson], courses: Sequence[Course]
    ) -> PrerequisiteGraph:
        """Lay out ``lessons`` (in path order) in the bands of ``courses``.

        Columns follow the prerequisites; rows within a column are ordered
        by a few barycentre sweeps, so that edges cross little, and every
        tie is broken by the path order, so that the result is
        deterministic.
        """
        edges = edges_of(lessons)
        layer = _layers(lessons)
        index = {lesson.id: number for number, lesson in enumerate(lessons)}
        course_index = {course.id: number for number, course in enumerate(courses)}
        near: dict[str, list[str]] = {lesson.id: [] for lesson in lessons}
        for edge in edges:
            near[edge.source].append(edge.target)
            near[edge.target].append(edge.source)

        columns = max(layer.values(), default=-1) + 1
        column: list[list[str]] = [[] for _ in range(columns)]
        for lesson in lessons:
            column[layer[lesson.id]].append(lesson.id)
        by_id = {lesson.id: lesson for lesson in lessons}

        def course_of(lesson_id: str) -> int:
            return course_index.get(by_id[lesson_id].course, len(courses))

        row = {item: number for ids in column for number, item in enumerate(ids)}

        def place(ids: list[str], key: Callable[[str], tuple]) -> None:
            ids.sort(key=key)
            for number, item in enumerate(ids):
                row[item] = number

        def barycentre(number: int, forward: bool) -> Callable[[str], tuple]:
            def key(item: str) -> tuple[int, float, int]:
                others = [
                    row[other]
                    for other in near[item]
                    if (layer[other] < number) == forward and layer[other] != number
                ]
                centre = sum(others) / len(others) if others else float(row[item])
                return (course_of(item), centre, index[item])

            return key

        for ids in column:
            place(ids, lambda item: (course_of(item), 0.0, index[item]))
        for step in range(SWEEPS):
            forward = step % 2 == 0
            for number in range(columns) if forward else reversed(range(columns)):
                place(column[number], barycentre(number, forward))

        # A band is as high as its fullest column; a column is centred in it.
        pitch = NODE_HEIGHT + ROW_GAP
        bands = []
        top = MARGIN
        height_of: dict[str, tuple[int, int]] = {}
        used = sorted({course_of(item) for ids in column for item in ids})
        for position in used:
            course = courses[position] if position < len(courses) else None
            if course is None:
                continue
            rows = max(
                (
                    sum(1 for item in ids if course_of(item) == position)
                    for ids in column
                ),
                default=0,
            )
            if rows == 0:
                continue
            band_height = BAND_LABEL + rows * pitch - ROW_GAP + 2 * MARGIN
            bands.append(Band(course, top, band_height))
            height_of[course.id] = (top, rows)
            top += band_height + BAND_GAP

        nodes = []
        for number, ids in enumerate(column):
            seen: dict[int, int] = {}
            for item in ids:
                position = course_of(item)
                course = by_id[item].course
                band_top, rows = height_of[course]
                count = sum(1 for other in ids if course_of(other) == position)
                slot = seen.get(position, 0)
                seen[position] = slot + 1
                offset = (rows - count) * pitch // 2
                nodes.append(
                    Node(
                        by_id[item],
                        number,
                        MARGIN + number * (NODE_WIDTH + COLUMN_GAP),
                        band_top + BAND_LABEL + MARGIN + offset + slot * pitch,
                    )
                )
        nodes.sort(key=lambda node: index[node.lesson.id])
        width = 2 * MARGIN + columns * NODE_WIDTH + max(columns - 1, 0) * COLUMN_GAP
        height = (top - BAND_GAP + MARGIN) if bands else 2 * MARGIN
        return cls(tuple(nodes), tuple(bands), edges, width, height)

    # --- Text ---------------------------------------------------------------

    def sentences(self) -> list[str]:
        """The edges as sentences, the accessible alternative to the
        drawing: "Newton's laws requires Kinematics as a program"."""
        title = {node.lesson.id: node.lesson.title for node in self.nodes}
        found = []
        for edge in self._ordered():
            if edge.kind == REQUIRES:
                found.append(f"{title[edge.target]} requires {title[edge.source]}")
            else:
                found.append(
                    f"{title[edge.source]} has the related lesson"
                    f" {title[edge.target]} (recommended, not required)"
                )
        return found

    def _ordered(self) -> list[Edge]:
        rank = {node.lesson.id: number for number, node in enumerate(self.nodes)}

        def key(edge: Edge) -> tuple[int, int, int, int]:
            about = edge.target if edge.kind == REQUIRES else edge.source
            other = edge.source if edge.kind == REQUIRES else edge.target
            return (rank[about], edge.kind != REQUIRES, rank[other], 0)

        return sorted(self.edges, key=key)

    # --- Drawing ------------------------------------------------------------

    def _path(self, edge: Edge, doubled: bool) -> str:
        nodes = {node.lesson.id: node for node in self.nodes}
        source, target = nodes[edge.source], nodes[edge.target]
        shift = 0
        if doubled:
            shift = -PAIR_OFFSET if edge.kind == REQUIRES else PAIR_OFFSET
        y1 = source.y + NODE_HEIGHT // 2 + shift
        y2 = target.y + NODE_HEIGHT // 2 + shift
        if target.layer > source.layer:
            x1, x2 = source.x + NODE_WIDTH, target.x
            middle = (x1 + x2) // 2
            return f"M{x1},{y1} C{middle},{y1} {middle},{y2} {x2},{y2}"
        if target.layer < source.layer:
            x1, x2 = source.x, target.x + NODE_WIDTH
            middle = (x1 + x2) // 2
            return f"M{x1},{y1} C{middle},{y1} {middle},{y2} {x2},{y2}"
        x1 = source.x + NODE_WIDTH
        out = x1 + COLUMN_GAP // 2
        return f"M{x1},{y1} C{out},{y1} {out},{y2} {x1},{y2}"

    def svg(self, href: Callable[[Lesson], str], summary: str) -> str:
        """The graph as inline SVG; ``href`` gives the link of a lesson from
        the page the graph is on, ``summary`` is its description."""
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" class="prerequisite-graph-svg"'
            f' viewBox="0 0 {self.width} {self.height}"'
            f' width="{self.width}" height="{self.height}"'
            f' aria-labelledby="{TITLE_ID} {DESCRIPTION_ID}">',
            f'<title id="{TITLE_ID}">Prerequisite graph of the lessons</title>',
            f'<desc id="{DESCRIPTION_ID}">{escape(summary)}</desc>',
            "<defs>",
            f'<marker id="{REQUIRES_MARKER}" viewBox="0 0 10 10" refX="9" refY="5"'
            ' markerWidth="9" markerHeight="9" orient="auto">'
            '<path class="arrow-requires" d="M0,0 L10,5 L0,10 z"/></marker>',
            f'<marker id="{RELATED_MARKER}" viewBox="0 0 10 10" refX="9" refY="5"'
            ' markerWidth="9" markerHeight="9" orient="auto">'
            '<path class="arrow-related" d="M1,1 L9,5 L1,9"/></marker>',
            "</defs>",
        ]
        for band in self.bands:
            band_id = f"prerequisite-graph-course-{band.course.id}"
            parts += [
                f'<g role="group" aria-labelledby="{band_id}">',
                f'<rect class="band" x="0" y="{band.y}" width="{self.width}"'
                f' height="{band.height}" rx="4"/>',
                f'<text id="{band_id}" class="band-label" x="{MARGIN}"'
                f' y="{band.y + 20}">{escape(band.course.title)}</text>',
                "</g>",
            ]
        parts.append('<g class="edges">')
        for edge in self._ordered():
            doubled = self._both(edge)
            marker = REQUIRES_MARKER if edge.kind == REQUIRES else RELATED_MARKER
            parts.append(
                f'<path class="edge-{edge.kind}" data-from="{edge.source}"'
                f' data-to="{edge.target}" data-kind="{edge.kind}"'
                f' d="{self._path(edge, doubled)}" marker-end="url(#{marker})"/>'
            )
        parts.append("</g>")
        parts.append('<g class="nodes">')
        for node in self.nodes:
            lesson = node.lesson
            lines, cut = _wrap(lesson.title)
            label = f' aria-label="{escape(lesson.title)}"' if cut else ""
            parts.append(
                f'<a href="{escape(href(lesson))}" data-lesson="{lesson.id}"{label}>'
                f'<rect class="node" x="{node.x}" y="{node.y}"'
                f' width="{NODE_WIDTH}" height="{NODE_HEIGHT}" rx="4"/>'
                f'<text x="{node.x + 10}" y="{node.y + 28 - 8 * (len(lines) - 1)}">'
                + "".join(
                    f'<tspan x="{node.x + 10}" dy="{0 if number == 0 else 17}">'
                    f"{escape(line)}</tspan>"
                    for number, line in enumerate(lines)
                )
                + "</text></a>"
            )
        parts.append("</g></svg>")
        return "\n".join(parts)

    def _both(self, edge: Edge) -> bool:
        """Whether the same two lessons are joined by a required and a
        related edge in the same direction."""
        kinds = {
            other.kind
            for other in self.edges
            if (other.source, other.target) == (edge.source, edge.target)
        }
        return kinds == {REQUIRES, RELATED}


def _wrap(title: str) -> tuple[list[str], bool]:
    """The lines of a node label, and whether the title was cut short."""
    lines = textwrap.wrap(title, LINE_WIDTH, break_long_words=False) or [title]
    if len(lines) <= LINES:
        return lines, False
    kept = lines[:LINES]
    kept[-1] = kept[-1].rstrip(".,;:") + "…"
    return kept, True
