"""The generated parts of the home page (F134, ADR 021 decision 4): the hero,
what the site is, three example lessons and one capstone, and the invitation.

The hero's copy is the owner's, held in the data file ``site/hero.yaml``
beside the curriculum file and validated here: exactly the eight pairs 1a,
1b, 1c, 2a, 2b, 2c, 3a, and 3b, each a headline and one of its subtexts. The
page carries the default pair in its HTML, and the pairs as data for
``site/learner/hero.js``, which shows one at random per visit, or the one
the ``hero`` parameter names, before the first paint. No copy of the hero is
written on the page.

The hero image is interface artwork (ADR 021 decision 1): two constellations,
the eight courses and the four method paths, each node the card illustration
the atlas manifest names for its sequence (a file of the provenance
register), its name as SVG text from the curriculum. Its lines are
decorative and imply no prerequisite.

The examples are chosen by code from the front matter, never by hand: a
simulation, a measured-data lab, and an AI experiment, each from a different
course and none from the first course, which the start link leads into; and
the first published capstone of a course none of them has. A capstone's one
line is the explanation of its concept in the atlas manifest. Every link is
built here from the lessons and the page addresses.
"""

from __future__ import annotations

import html
import json
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.atlas import CAPSTONE, AtlasManifest
from pbc.authoring.identity import ABOUT_ANCHOR, description
from pbc.authoring.path import (
    COURSES,
    LearningPath,
    Lesson,
    _href,
    _level,
)
from pbc.authoring.previews import HEIGHT as PREVIEW_HEIGHT
from pbc.authoring.previews import WIDTH as PREVIEW_WIDTH
from pbc.authoring.previews import Preview, preview_of
from pbc.authoring.repository import repository_url
from pbc.authoring.website import PAGE_FILE, page_href, project_root

HOME_PAGE = PAGE_FILE
PATH_PAGE = "path/index.qmd"
VERIFY_PAGE = "verify.qmd"
ABOUT_PAGE = "about.qmd"
HERO_FILE = "hero.yaml"
HERO_SCRIPT = "learner/hero.js"

# The eight pairs of the owner's copy: the headline's id and the subtext's
# letter (Issue #339, 2026-10-30).
HERO_PAIRS = ("1a", "1b", "1c", "2a", "2b", "2c", "3a", "3b")

# The methods that make the three kinds of example, in the order shown.
SIMULATION = "simulation"
MEASURED = "measured-data"
AGENT = "llm-agents"

# Markup that plain text of the hero must not hold: it is set as text, so it
# would show as typed.
_MARKUP = re.compile(r"[<>*_`#\[\]{}\\|$]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


# --- The hero's copy -------------------------------------------------------


@dataclass(frozen=True)
class HeroPair:
    id: str  # "1a"
    headline: str
    subtext: str


@dataclass(frozen=True)
class HeroCopy:
    pairs: tuple[HeroPair, ...]
    default: str

    def pair(self, pair_id: str) -> HeroPair:
        return next(pair for pair in self.pairs if pair.id == pair_id)

    @classmethod
    def parse(cls, data: object) -> HeroCopy:
        found = hero_problems(data)
        if found:
            raise ValueError(
                f"{HERO_FILE} breaks the rules of the hero:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            tuple(
                HeroPair(
                    f"{headline['id']}{subtext['id']}",
                    _words(headline["text"]),
                    _words(subtext["text"]),
                )
                for headline in data["headlines"]
                for subtext in headline["subtexts"]
            ),
            data["default"],
        )

    @classmethod
    def read(cls, site: Path) -> HeroCopy:
        """Read ``hero.yaml`` of the website project ``site``. Raises
        ``ValueError`` when it breaks a rule; a missing file breaks them."""
        file = site / HERO_FILE
        data: object = None
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{HERO_FILE} is not valid YAML: {error}") from None
        return cls.parse(data)


def _words(text: str) -> str:
    return " ".join(text.split())


def _text_problems(where: str, value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{where} has no text"]
    if _MARKUP.search(value):
        return [f"{where} holds markup; the copy is plain text"]
    return []


def _fields(where: str, item: object, fields: set[str]) -> list[str]:
    if not isinstance(item, dict):
        return [f"{where} is not a mapping"]
    found = []
    if unknown := set(item) - fields:
        found.append(
            f"{where} has unknown fields: {', '.join(sorted(map(str, unknown)))}"
        )
    if missing := fields - set(item):
        found.append(f"{where} lacks {', '.join(sorted(missing))}")
    return found


def hero_problems(data: object) -> list[str]:
    """Every rule of the hero's data file that ``data`` breaks: exactly the
    pairs of ``HERO_PAIRS``, each once; plain, non-empty text; no field
    beyond ``default``, ``headlines``, ``id``, ``text``, and ``subtexts``;
    a default that names one of the pairs."""
    if not isinstance(data, dict):
        return [f"{HERO_FILE} is not a mapping with 'default' and 'headlines'"]
    found = _fields(HERO_FILE, data, {"default", "headlines"})
    headlines = data.get("headlines")
    if not isinstance(headlines, list):
        return [*found, "'headlines' is not a list"]
    identifiers: list[str] = []
    headline_ids: list[str] = []
    for number, headline in enumerate(headlines, start=1):
        where = f"headline {number}"
        found += _fields(where, headline, {"id", "text", "subtexts"})
        if not isinstance(headline, dict):
            continue
        headline_id = str(headline.get("id", ""))
        headline_ids.append(headline_id)
        found += _text_problems(
            f"headline {headline_id or number}", headline.get("text")
        )
        subtexts = headline.get("subtexts")
        if not isinstance(subtexts, list):
            found.append(f"headline {headline_id or number} has no list of subtexts")
            continue
        for subtext in subtexts:
            found += _fields(
                f"a subtext of headline {headline_id}", subtext, {"id", "text"}
            )
            if not isinstance(subtext, dict):
                continue
            pair = f"{headline_id}{subtext.get('id', '')}"
            identifiers.append(pair)
            found += _text_problems(f"subtext {pair}", subtext.get("text"))
    for headline_id in sorted({h for h in headline_ids if headline_ids.count(h) > 1}):
        found.append(f"the headline id {headline_id!r} appears more than once")
    for pair in sorted({p for p in identifiers if identifiers.count(p) > 1}):
        found.append(f"the pair {pair} appears more than once")
    if missing := [pair for pair in HERO_PAIRS if pair not in identifiers]:
        found.append(f"the pairs {', '.join(missing)} are missing")
    if extra := sorted(set(identifiers) - set(HERO_PAIRS)):
        found.append(f"the pairs {', '.join(extra)} are not the owner's eight")
    if data.get("default") not in HERO_PAIRS:
        found.append(f"the default {data.get('default')!r} is none of the eight pairs")
    return found


def _typographic(text: str) -> str:
    """The text with typographic apostrophes, as the build sets the
    Markdown of the other pages."""
    return text.replace("'", "\u2019")


# --- The hero image --------------------------------------------------------

# The two constellations in a box of WIDTH by HEIGHT units: the centre of
# each node, in the order of the curriculum file. Decorative positions; the
# lines between them say nothing about the order of study.
WIDTH, HEIGHT = 640, 520
NODE_WIDTH, NODE_HEIGHT = 96, 72
COURSE_NODES = (
    (86, 62),
    (240, 44),
    (392, 92),
    (322, 236),
    (170, 208),
    (74, 352),
    (226, 396),
    (382, 418),
)
PATH_NODES = ((556, 64), (532, 196), (568, 322), (534, 448))
# Below 40em the image is drawn about 360 CSS px wide, too narrow for four
# columns of labels that a reader can read: the nodes move to two columns,
# PHONE_SCALE times larger, in a box of WIDTH by PHONE_HEIGHT units, and the
# labels grow (site/assets/site.css, .hero-label).
PHONE_HEIGHT = 1280
PHONE_SCALE = 1.25
PHONE_COURSE_NODES = (
    (170, 80),
    (470, 120),
    (170, 280),
    (470, 320),
    (170, 480),
    (470, 520),
    (170, 680),
    (470, 720),
)
PHONE_PATH_NODES = ((170, 920), (470, 960), (170, 1120), (470, 1160))
# The card illustration of a node, the larger of the atlas's two card sizes.
CARD = "{stem}-card-228.webp"
_LABEL_LINE = 19  # characters on one line of a node's label


def _wrap(title: str) -> list[str]:
    """A node's label on at most two lines."""
    lines: list[str] = []
    for word in title.split():
        if lines and len(lines[-1]) + 1 + len(word) <= _LABEL_LINE:
            lines[-1] += f" {word}"
        elif len(lines) < 2:
            lines.append(word)
        else:
            lines[-1] += f" {word}"
    return lines


def _path_line(points: tuple[tuple[int, int], ...]) -> str:
    return "M" + " L".join(f"{x},{y}" for x, y in points)


# --- The page ----------------------------------------------------------------


@dataclass(frozen=True)
class HomeContent:
    path: LearningPath
    manifest: AtlasManifest
    hero_copy: HeroCopy
    repository: str = ""  # the public address of the repository, or ""
    page: str = HOME_PAGE

    def _to(self, page: str, fragment: str = "") -> str:
        return page_href(self.page, page, fragment)

    def first_lesson(self) -> Lesson:
        """The first lesson of the first course in teaching order: the start
        link of the header goes there too."""
        return self.path.in_course(self.path.courses[0])[0]

    def _actions(self) -> str:
        first = self.first_lesson()
        return (
            '<p class="home-actions">'
            f'<a class="home-action-primary" href="{_href(self.page, first.page)}">'
            "Start learning</a> "
            f'<a class="home-action" href="{self._to(PATH_PAGE, "atlas")}">'
            "Open the Course Atlas</a></p>"
        )

    # The hero.

    def hero(self) -> str:
        """The hero as one raw HTML block: the default pair, the two ways in,
        the pairs as data, the script, and the image."""
        default = self.hero_copy.pair(self.hero_copy.default)
        pairs = json.dumps(
            [
                {
                    "id": pair.id,
                    "headline": _typographic(pair.headline),
                    "subtext": _typographic(pair.subtext),
                }
                for pair in self.hero_copy.pairs
            ],
            ensure_ascii=False,
        )
        # Safe inside a script element: no "</script>" can close it early.
        pairs = (
            pairs.replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
        )
        script = posixpath_relative(self.page, HERO_SCRIPT)
        return "\n".join(
            [
                "```{=html}",
                # An empty title block: without one, Quarto moves the first
                # <h1> of a page without a title into a title block of its
                # own, out of the hero.
                '<header class="quarto-title-block"></header>',
                '<section class="home-hero" aria-labelledby="hero-headline">',
                '<div class="hero-text">',
                # A declared enhancement (invariant I4): the default pair is
                # its static content, which the script may replace.
                '<div class="hero-copy" id="hero-copy" data-enhancement'
                f' data-hero="{default.id}">',
                '<div class="hero-pair">',
                '<h1 class="hero-headline" id="hero-headline">'
                f"{html.escape(_typographic(default.headline))}</h1>",
                '<p class="hero-subtext">'
                f"{html.escape(_typographic(default.subtext))}</p>",
                "</div>",
                "</div>",
                f'<script type="application/json" id="hero-pairs">{pairs}</script>',
                f'<script src="{script}"></script>',
                self._actions(),
                "</div>",
                self.hero_image(),
                "</section>",
                "```",
            ]
        )

    def _sequences(
        self,
    ) -> list[tuple[str, str, tuple[int, int], tuple[int, int], str]]:
        """The nodes of the image: the sequence id, its title, its centre,
        its centre on a phone, and the part it belongs to."""
        courses = [
            (course.id, course.title, centre, phone, "a")
            for course, centre, phone in zip(
                COURSES, COURSE_NODES, PHONE_COURSE_NODES, strict=True
            )
        ]
        paths = [
            (item.id, item.title, centre, phone, "b")
            for item, centre, phone in zip(
                self.path.paths, PATH_NODES, PHONE_PATH_NODES, strict=True
            )
        ]
        return courses + paths

    def hero_alt(self) -> str:
        courses = ", ".join(course.title for course in COURSES)
        paths = ", ".join(item.title for item in self.path.paths)
        return (
            "Illustration: two constellations of the atlas's illustrations,"
            f" the {len(COURSES)} physics courses ({courses}) and the"
            f" {len(self.path.paths)} method paths of physics and AI ({paths}),"
            " joined by decorative lines that imply no order of study."
        )

    def hero_image(self) -> str:
        """The two constellations as one inline SVG."""
        nodes = self._sequences()
        courses = tuple(centre for _, _, centre, _, part in nodes if part == "a")
        paths = tuple(centre for _, _, centre, _, part in nodes if part == "b")
        bridge = (courses[3], paths[1])
        # On a phone the last course meets the second path: the bridge of the
        # wide layout would pass behind two nodes of the right column.
        phone_bridge = (PHONE_COURSE_NODES[-1], PHONE_PATH_NODES[1])
        # The phone layout keeps the viewBox: its box is taller, and the
        # drawing is aligned to the top, so the units below HEIGHT show.
        parts = [
            f'<svg class="hero-image" viewBox="0 0 {WIDTH} {HEIGHT}"'
            ' preserveAspectRatio="xMidYMin meet"'
            f' style="--hero-phone-ratio: {WIDTH} / {PHONE_HEIGHT}" role="img"'
            ' aria-labelledby="hero-image-title" focusable="false">',
            f'<title id="hero-image-title">{html.escape(self.hero_alt())}</title>',
            "<defs>"
            '<clipPath id="hero-frame" clipPathUnits="objectBoundingBox">'
            '<rect width="1" height="1" rx="0.06" ry="0.08"/></clipPath>'
            "</defs>",
            f'<path class="hero-bridge hero-wide" d="{_path_line(bridge)}"/>',
            '<path class="hero-line hero-line-a hero-wide"'
            f' d="{_path_line(courses)}"/>',
            f'<path class="hero-line hero-line-b hero-wide" d="{_path_line(paths)}"/>',
            f'<path class="hero-bridge hero-phone" d="{_path_line(phone_bridge)}"/>',
            '<path class="hero-line hero-line-a hero-phone"'
            f' d="{_path_line(PHONE_COURSE_NODES)}"/>',
            '<path class="hero-line hero-line-b hero-phone"'
            f' d="{_path_line(PHONE_PATH_NODES)}"/>',
        ]
        for sequence_id, title, (x, y), (phone_x, phone_y), part in nodes:
            stem = self.manifest.sequence(sequence_id).illustration
            left, top = x - NODE_WIDTH // 2, y - NODE_HEIGHT // 2
            source = posixpath_relative(self.page, "assets/" + CARD.format(stem=stem))
            # In em, so that the lines keep their spacing when the labels grow.
            label = "".join(
                f'<tspan x="{x}" dy="{"1.15em" if index else "1.25em"}">'
                f"{html.escape(line)}</tspan>"
                for index, line in enumerate(_wrap(title))
            )
            # The node's place on a phone, which the style sheet applies below
            # 40em: scaled about its centre and moved to its phone centre.
            phone = (
                f"translate({phone_x}px, {phone_y}px) scale({PHONE_SCALE})"
                f" translate({-x}px, {-y}px)"
            )
            parts += [
                f'<g class="hero-node hero-node-{part}" data-sequence="{sequence_id}"'
                f' style="--hero-phone: {phone}">',
                f'<rect class="hero-plate" x="{left}" y="{top}" width="{NODE_WIDTH}"'
                f' height="{NODE_HEIGHT}" rx="6"/>',
                f'<image href="{source}" x="{left}" y="{top}" width="{NODE_WIDTH}"'
                f' height="{NODE_HEIGHT}" preserveAspectRatio="xMidYMid slice"'
                ' clip-path="url(#hero-frame)"/>',
                f'<rect class="hero-frame" x="{left}" y="{top}" width="{NODE_WIDTH}"'
                f' height="{NODE_HEIGHT}" rx="6"/>',
                f'<text class="hero-label" x="{x}" y="{top + NODE_HEIGHT}">'
                f"{label}</text>",
                "</g>",
            ]
        parts.append("</svg>")
        return "".join(parts)

    # What the site is.

    def about(self) -> str:
        """Three sentences, the canonical one first, and the links that
        follow them: the one attribution link, this page's account of the
        evidence, and the source."""
        return "\n\n".join(
            [
                f"{description()} A model becomes a short program that you can"
                " run, and each lesson tests it: against theory in"
                " simulations, against real measurements in the labs, or with"
                " a proof that a computer checks. A lesson whose code fails or"
                " whose proof does not compile cannot be published.",
                "::: {.home-more}\n"
                f"[About the creator and JIDAI]({self._about()})"
                f" [How we verify the science]({self._to(VERIFY_PAGE)})"
                + (
                    f" [The source on GitHub]({self.repository})"
                    if self.repository
                    else ""
                )
                + "\n"
                ":::",
            ]
        )

    def _about(self) -> str:
        return self._to(ABOUT_PAGE, ABOUT_ANCHOR.partition("#")[2])

    # The examples.

    def examples(self) -> tuple[Lesson, ...]:
        """A simulation, a measured-data lab, and an AI experiment, in that
        order, each the first published lesson of its kind in path order
        whose course is neither the first course nor the course of an
        earlier example. A kind without such a lesson is left out."""
        first = self.path.courses[0].id
        kinds = (
            lambda lesson: lesson.methods == (SIMULATION,) and lesson.difficulty == 1,
            lambda lesson: MEASURED in lesson.methods,
            lambda lesson: AGENT in lesson.methods,
        )
        chosen: list[Lesson] = []
        for kind in kinds:
            used = {first, *(lesson.course for lesson in chosen)}
            found = next(
                (
                    lesson
                    for lesson in self.path.lessons
                    if lesson.course not in used and kind(lesson)
                ),
                None,
            )
            if found is not None:
                chosen.append(found)
        return tuple(chosen)

    def capstone(self) -> Lesson | None:
        """The first published capstone in the order of the curriculum file
        whose course none of the examples has, else the first published one
        that is not itself an example; None when there is no such one."""
        published = {lesson.slot: lesson for lesson in self.path.lessons if lesson.slot}
        capstones = [
            published[slot.label]
            for slot in self.path.curriculum.slots
            if slot.kind == CAPSTONE and slot.label in published
        ]
        examples = self.examples()
        used = {lesson.course for lesson in examples}
        shown = {lesson.id for lesson in examples}
        return next(
            (lesson for lesson in capstones if lesson.course not in used),
            next((lesson for lesson in capstones if lesson.id not in shown), None),
        )

    def _course_title(self, lesson: Lesson) -> str:
        return next(course.title for course in COURSES if course.id == lesson.course)

    def _card(
        self, lesson: Lesson, line: str, note: str, preview: Preview
    ) -> list[str]:
        image = posixpath_relative(self.page, preview.file)
        return [
            f"::: {{.home-example data-lesson-id={lesson.id}}}",
            f'`<img class="home-preview" src="{image}"'
            f' alt="{html.escape(preview.alt, quote=True)}"'
            f' width="{PREVIEW_WIDTH}" height="{PREVIEW_HEIGHT}"'
            ' loading="lazy">`{=html}',
            "",
            f"### [{lesson.title}]({_href(self.page, lesson.page)})"
            f" {{#example-{lesson.id} .unnumbered .unlisted}}",
            "",
            line,
            "",
            f"[{note}]{{.home-meta}}",
            ":::",
            "",
        ]

    def examples_section(self, site: Path | None = None) -> str:
        """The three examples and the capstone: each with its preview, its
        title as a link, one line, and its level and course."""
        site = site or project_root(Path.cwd().resolve())
        lines = ["::: {.home-examples}", ""]
        for lesson in self.examples():
            line = (
                _SENTENCE_END.split(lesson.description)[0] if lesson.description else ""
            )
            note = f"{_level(lesson)}, in {self._course_title(lesson)}"
            lines += self._card(lesson, line, note, preview_of(lesson, site))
        capstone = self.capstone()
        if capstone is not None:
            explanation = self.manifest.capstone(capstone.slot).explanation
            note = (
                f"{_level(capstone)}, the capstone project of"
                f" {self._course_title(capstone)}"
            )
            lines += self._card(capstone, explanation, note, preview_of(capstone, site))
        lines.append(":::")
        return "\n".join(lines)

    # The invitation.

    def begin(self) -> str:
        """The start link and the atlas, nothing else."""
        first = self.first_lesson()
        return (
            f"[Start learning]({_href(self.page, first.page)}){{.home-action-primary}}"
            f" [Open the Course Atlas]({self._to(PATH_PAGE, 'atlas')}){{.home-action}}"
        )

    def markdown(self, site: Path | None = None) -> str:
        """The whole page, in the order of the plan: the hero, what the site
        is, the examples, and the invitation."""
        return "\n\n".join(
            [
                self.hero(),
                "## What this site is {#about-the-site}",
                self.about(),
                "## What you can learn {#examples}",
                self.examples_section(site),
                "## Begin {#begin}",
                f"::: {{.home-begin}}\n{self.begin()}\n:::",
            ]
        )


def posixpath_relative(from_page: str, target: str) -> str:
    """A relative address of the file ``target`` of the built site, from the
    built ``from_page``."""
    return posixpath.relpath(target, posixpath.dirname(from_page) or ".")


def home_content() -> HomeContent:
    """Return the generated parts of the home page being built."""
    site = project_root(Path.cwd().resolve())
    path = LearningPath.read(site)
    return HomeContent(
        path,
        AtlasManifest.read(site, path.curriculum),
        HeroCopy.read(site),
        repository_url(),
    )
