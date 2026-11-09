"""The generated home page (F134, ADR 021 decision 4; F158, requirements
decision 43 and the amendment of decision 4): the hero, then the four
sections of the Home copy file in the order identity, educational
philosophy, curriculum, and integrity.

The hero's copy is the owner's, held in the data file ``site/hero.yaml``
beside the curriculum file and validated here: exactly the eight pairs 1a,
1b, 1c, 2a, 2b, 2c, 3a, and 3b, each a headline and one of its subtexts. The
page carries the default pair in its HTML, and the pairs as data for
``site/learner/hero.js``, which shows one at random per visit, or the one
the ``hero`` parameter names, before the first paint. No copy of the hero is
written on the page.

The hero image is one of a small set of Part A illustrations (interface
artwork of ADR 021 decision 1), held in the same data file: each a WebP file
under ``site/assets/hero/`` named by its identifier and registered in the
provenance register, with the course whose atlas master it is derived from
and its alternative text. The default image stands in the HTML inside
``<noscript>``, so that it is what a page without scripts shows and what a
reader of the HTML sees, and is not requested when the script runs: the
script creates the one image it picks, at random and independently of the
pair, or the one the ``hero-image`` parameter names. Exactly one hero image
is requested per load.

The sections after the hero come from ``site/home.yaml`` (prose and
references under the rules of the learning journey) and, for "What you can
learn", from the learning journey itself (``site/journey.yaml``, the one
source the Course Atlas and About share), with at most one representative
published lesson per part, chosen by the owner and named in the copy file by
its slot. No code chooses an example lesson or a capstone. Every link is
built here from the lessons and the page addresses.
"""

from __future__ import annotations

import html
import json
import posixpath
import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import yaml

from pbc.authoring.atlas import Atlas, registered_assets
from pbc.authoring.glossary import Glossary
from pbc.authoring.identity import ABOUT_ANCHOR, description
from pbc.authoring.introductions import sequence_ids
from pbc.authoring.journey import (
    SECTIONS as JOURNEY_SECTIONS,
)
from pbc.authoring.journey import (
    Journey,
    JourneyContent,
    _journey_text_problems,
)
from pbc.authoring.path import (
    COURSES,
    Curriculum,
    LearningPath,
    Lesson,
    _href,
    _level,
)
from pbc.authoring.previews import HEIGHT as PREVIEW_HEIGHT
from pbc.authoring.previews import WIDTH as PREVIEW_WIDTH
from pbc.authoring.previews import preview_of
from pbc.authoring.repository import repository_url
from pbc.authoring.website import PAGE_FILE, introduced, page_href, project_root

HOME_PAGE = PAGE_FILE
PATH_PAGE = "path/index.qmd"
VERIFY_PAGE = "verify.qmd"
ABOUT_PAGE = "about.qmd"
HERO_FILE = "hero.yaml"
HOME_FILE = "home.yaml"
HERO_SCRIPT = "learner/hero.js"
# The hero images: one WebP file per image, named by its identifier, at one
# size (tools/illustrations/derive_assets.py --hero), 4:3 like its master.
HERO_IMAGES = "assets/hero"
HERO_IMAGE_WIDTH, HERO_IMAGE_HEIGHT = 1200, 900
# The parameters that force a pair and an image, for tests and screenshots.
HERO_PARAMETER = "hero"
HERO_IMAGE_PARAMETER = "hero-image"

# The eight pairs of the owner's copy: the headline's id and the subtext's
# letter (Issue #339, 2026-10-30).
HERO_PAIRS = ("1a", "1b", "1c", "2a", "2b", "2c", "3a", "3b")

# The sections of the Home copy file in the order of the page, with the
# anchor of each (the identity keeps the anchor of F134's "What this site
# is").
SECTIONS = (
    ("identity", "about-the-site"),
    ("philosophy", "how-physics-is-learned"),
    ("curriculum", "what-you-can-learn"),
    ("integrity", "integrity"),
)
# The two parts of "What you can learn": the key of an example in the copy
# file, and the section of the learning journey that explains the part.
PARTS = (("part-a", "A"), ("part-b", "B"))
# The two actions of the first step (requirements decision 43): the Course
# Atlas, primary on Home, and the first lesson of Part A, secondary; the
# header's Course Atlas link and Start learning button lead to the same
# pages.
ATLAS_ACTION = "Open the Course Atlas"
FIRST_LESSON_ACTION = "Start with the first lesson"
_IMAGE_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

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
class HeroImage:
    id: str  # "double-pendulum": the name of its file
    sequence: str  # the course whose atlas master it is derived from
    alt: str

    @property
    def file(self) -> str:
        """The file of the built site, relative to its root."""
        return f"{HERO_IMAGES}/{self.id}.webp"


@dataclass(frozen=True)
class HeroCopy:
    pairs: tuple[HeroPair, ...]
    default: str
    images: tuple[HeroImage, ...] = ()
    default_image: str = ""

    def pair(self, pair_id: str) -> HeroPair:
        return next(pair for pair in self.pairs if pair.id == pair_id)

    def image(self, image_id: str) -> HeroImage:
        return next(image for image in self.images if image.id == image_id)

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
            tuple(
                HeroImage(item["id"], item["sequence"], _words(item["alt"]))
                for item in data["images"]["set"]
            ),
            data["images"]["default"],
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
    a default that names one of the pairs; and the images
    (``image_problems``)."""
    if not isinstance(data, dict):
        return [
            f"{HERO_FILE} is not a mapping with 'default', 'headlines', and 'images'"
        ]
    found = _fields(HERO_FILE, data, {"default", "headlines", "images"})
    found += image_problems(data.get("images"))
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


def image_problems(images: object) -> list[str]:
    """Every rule of the hero images that ``images`` breaks: a mapping of
    ``default`` and ``set``; the set a non-empty list of images, each with
    exactly ``id`` (lower-case words joined by hyphens, the name of its
    file, unique), ``sequence`` (a course of Part A, whose atlas master the
    file is derived from), and ``alt`` (plain, non-empty text); a default
    that names one of them."""
    where = "'images'"
    found = _fields(where, images, {"default", "set"})
    if not isinstance(images, dict):
        return found
    items = images.get("set")
    if not isinstance(items, list) or not items:
        return [*found, "'images' has no list 'set' of images"]
    identifiers: list[str] = []
    courses = {course.id for course in COURSES}
    for number, item in enumerate(items, start=1):
        found += _fields(f"image {number}", item, {"id", "sequence", "alt"})
        if not isinstance(item, dict):
            continue
        image_id = item.get("id")
        if not isinstance(image_id, str) or not _IMAGE_ID.fullmatch(image_id):
            found.append(
                f"image {number} has the id {image_id!r}; an id is lower-case"
                " words joined by hyphens, the name of its file"
            )
        else:
            identifiers.append(image_id)
        name = image_id if isinstance(image_id, str) else number
        if item.get("sequence") not in courses:
            found.append(
                f"image {name} names the sequence {item.get('sequence')!r}, which"
                " is no course of Part A"
            )
        found += _text_problems(f"the alt text of image {name}", item.get("alt"))
    for image_id in sorted({i for i in identifiers if identifiers.count(i) > 1}):
        found.append(f"the image {image_id} appears more than once")
    if images.get("default") not in identifiers:
        found.append(
            f"the default image {images.get('default')!r} is none of the images"
        )
    return found


def image_file_problems(hero: HeroCopy, site: Path) -> list[str]:
    """What the website project ``site`` lacks for the hero images: each
    file under ``site/assets/hero/`` and its entry in the provenance
    register."""
    registered = registered_assets(site)
    found = []
    for image in hero.images:
        if not (site / image.file).is_file():
            found.append(f"the hero image {image.id} has no file {image.file}")
        if image.file.removeprefix("assets/") not in registered:
            found.append(f"the hero image {image.id} is not in the provenance register")
    return found


def _typographic(text: str) -> str:
    """The text with typographic apostrophes, as the build sets the
    Markdown of the other pages."""
    return text.replace("'", "\u2019")


# --- The Home copy file ------------------------------------------------------


def home_problems(
    data: object,
    curriculum: Curriculum,
    published: Collection[str] = (),
    terms: Collection[str] = (),
) -> list[str]:
    """Every rule of the Home copy file that ``data`` breaks: a mapping of
    exactly the four sections; each a mapping of a ``heading`` (plain,
    non-empty text) and, except the curriculum, ``text``, a non-empty list
    of paragraphs under the text rules of the learning journey (inline
    Markdown, references that resolve, no count, no lesson named outside a
    reference, no "discover"); the curriculum's optional ``examples``, a
    mapping of ``part-a`` or ``part-b`` to the label of a slot of a course
    or of a method path respectively, which has a published lesson (its
    label in ``published``)."""
    where = HOME_FILE
    if not isinstance(data, dict):
        return [
            f"{where} is not a mapping of the sections"
            f" {', '.join(key for key, _ in SECTIONS)}"
        ]
    found = _fields(where, data, {key for key, _ in SECTIONS})
    try:
        sequences = sequence_ids(curriculum)
    except ValueError as error:
        return [*found, str(error)]
    for key, _ in SECTIONS:
        section = data.get(key)
        if key not in data:
            continue
        fields = {"heading", "examples"} if key == "curriculum" else {"heading", "text"}
        if not isinstance(section, dict):
            found.append(f"{where}: {key} is not a mapping")
            continue
        unknown = set(section) - fields
        if unknown:
            found.append(
                f"{where}: {key} has unknown fields: "
                + ", ".join(sorted(map(str, unknown)))
            )
        if "heading" not in section:
            found.append(f"{where}: {key} lacks heading")
        else:
            found += _text_problems(f"the heading of {key}", section["heading"])
        if key == "curriculum":
            found += _example_problems(
                section.get("examples", {}), curriculum, published
            )
            continue
        texts = section.get("text")
        if not isinstance(texts, list) or not texts:
            found.append(f"{where}: {key} has no non-empty list 'text'")
            continue
        for number, text in enumerate(texts, start=1):
            found += _journey_text_problems(
                f"{where}: {key} {number}", text, curriculum, sequences, terms
            )
    return found


def _example_problems(
    examples: object, curriculum: Curriculum, published: Collection[str]
) -> list[str]:
    where = f"{HOME_FILE}: curriculum examples"
    if examples is None:
        return []
    if not isinstance(examples, dict):
        return [f"{where} is not a mapping of part-a and part-b to a slot"]
    found = []
    if unknown := set(examples) - {key for key, _ in PARTS}:
        found.append(
            f"{where} name {', '.join(sorted(map(str, unknown)))}; only part-a and"
            " part-b, one lesson each"
        )
    for key, part in PARTS:
        if key not in examples:
            continue
        label = examples[key]
        slot = curriculum.slot(label) if isinstance(label, str) else None
        if slot is None:
            found.append(f"{where}: {key} names {label!r}, no slot of the curriculum")
            continue
        if part == "A" and not slot.course:
            found.append(f"{where}: {key} names {label}, which is no slot of a course")
        if part == "B" and not slot.path:
            found.append(
                f"{where}: {key} names {label}, which is no slot of a method path"
            )
        if label not in published:
            found.append(
                f"{where}: {key} names {label}, which has no published lesson;"
                " an example is a published lesson or none"
            )
    return found


@dataclass(frozen=True)
class HomeCopy:
    """The validated copy of Home: the heading and paragraphs of each
    section, and the slot of each part's example."""

    headings: dict[str, str]
    texts: dict[str, tuple[str, ...]]
    examples: dict[str, str]  # "part-a" -> a slot label

    @classmethod
    def parse(
        cls,
        data: object,
        curriculum: Curriculum,
        published: Collection[str] = (),
        terms: Collection[str] = (),
    ) -> HomeCopy:
        found = home_problems(data, curriculum, published, terms)
        if found:
            raise ValueError(
                f"{HOME_FILE} breaks the rules of the Home copy:\n"
                + "\n".join(f"  {message}" for message in found)
            )
        assert isinstance(data, dict)
        return cls(
            {key: _words(data[key]["heading"]) for key, _ in SECTIONS},
            {
                key: tuple(_words(text) for text in data[key]["text"])
                for key, _ in SECTIONS
                if key != "curriculum"
            },
            dict(data["curriculum"].get("examples") or {}),
        )

    @classmethod
    def read(
        cls,
        site: Path,
        curriculum: Curriculum,
        published: Collection[str] = (),
        terms: Collection[str] = (),
    ) -> HomeCopy:
        """Read ``home.yaml`` of the website project ``site``. Raises
        ``ValueError`` when it breaks a rule; a missing file breaks them."""
        file = site / HOME_FILE
        data: object = None
        if file.is_file():
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
            except yaml.YAMLError as error:
                raise ValueError(f"{HOME_FILE} is not valid YAML: {error}") from None
        return cls.parse(data, curriculum, published, terms)


# --- The page ----------------------------------------------------------------


def _script_data(value: object) -> str:
    """JSON that is safe inside a script element: no "</script>" can close
    it early."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


@dataclass(frozen=True)
class HomeContent:
    journey: JourneyContent  # the atlas, the glossary, and the journey
    hero_copy: HeroCopy
    copy: HomeCopy
    repository: str = ""  # the public address of the repository, or ""
    page: str = HOME_PAGE

    @property
    def path(self) -> LearningPath:
        return self.journey.atlas.path

    def _to(self, page: str, fragment: str = "") -> str:
        return page_href(self.page, page, fragment)

    def first_lesson(self) -> Lesson:
        """The first lesson of the first course in teaching order: the start
        link of the header goes there too."""
        return self.path.in_course(self.path.courses[0])[0]

    def actions(self) -> str:
        """The first step: the Course Atlas, the one filled control, and the
        first lesson of Part A, a text link; the same pages as the header's
        Course Atlas link and Start learning button."""
        first = self.first_lesson()
        return (
            '<p class="home-actions">'
            f'<a class="home-action-primary" href="{self._to(PATH_PAGE)}">'
            f"{ATLAS_ACTION}</a> "
            f'<a class="home-action" href="{_href(self.page, first.page)}">'
            f"{FIRST_LESSON_ACTION}</a></p>"
        )

    # The hero.

    def hero(self) -> str:
        """The hero as one raw HTML block: the default pair, the figure with
        the default image for a page without scripts, the pairs and the
        images as data, the script, and the two actions."""
        default = self.hero_copy.pair(self.hero_copy.default)
        pairs = _script_data(
            [
                {
                    "id": pair.id,
                    "headline": _typographic(pair.headline),
                    "subtext": _typographic(pair.subtext),
                }
                for pair in self.hero_copy.pairs
            ]
        )
        images = _script_data(
            [
                {
                    "id": image.id,
                    "src": posixpath_relative(self.page, image.file),
                    "alt": _typographic(image.alt),
                    "width": HERO_IMAGE_WIDTH,
                    "height": HERO_IMAGE_HEIGHT,
                }
                for image in self.hero_copy.images
            ]
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
                self.hero_figure(),
                f'<script type="application/json" id="hero-pairs">{pairs}</script>',
                f'<script type="application/json" id="hero-images">{images}</script>',
                f'<script src="{script}"></script>',
                self.actions(),
                "</section>",
                "```",
            ]
        )

    def hero_figure(self) -> str:
        """The figure of the hero image: the default inside ``<noscript>``
        (what a page without scripts shows; with scripts it is not
        requested), and the box the script's image fills."""
        image = self.hero_copy.image(self.hero_copy.default_image)
        source = posixpath_relative(self.page, image.file)
        return (
            '<div class="hero-figure" id="hero-figure" data-enhancement'
            f' data-hero-image="{image.id}"><noscript>'
            f'<img class="hero-image" src="{source}"'
            f' alt="{html.escape(_typographic(image.alt), quote=True)}"'
            f' width="{HERO_IMAGE_WIDTH}" height="{HERO_IMAGE_HEIGHT}">'
            "</noscript></div>"
        )

    # The sections of the copy file.

    def _paragraphs(self, key: str) -> str:
        return "\n\n".join(self.journey.inline(text) for text in self.copy.texts[key])

    def _heading(self, key: str) -> str:
        return f"## {self.copy.headings[key]} {{#{dict(SECTIONS)[key]}}}"

    def identity(self) -> str:
        """The canonical sentence, the copy's paragraphs, and the one
        attribution link."""
        return "\n\n".join(
            [
                self._heading("identity"),
                f"{description()} {self._paragraphs('identity')}",
                "::: {.home-more}\n"
                f"[About the creator and JIDAI]({self._about()})\n"
                ":::",
            ]
        )

    def _about(self) -> str:
        return self._to(ABOUT_PAGE, ABOUT_ANCHOR.partition("#")[2])

    def philosophy(self) -> str:
        return "\n\n".join(
            [self._heading("philosophy"), self._paragraphs("philosophy")]
        )

    def example(self, part: str) -> Lesson | None:
        """The owner's example of ``part`` ("part-a" or "part-b"), or None."""
        label = self.copy.examples.get(part)
        if label is None:
            return None
        return next(lesson for lesson in self.path.lessons if lesson.slot == label)

    def _course_title(self, lesson: Lesson) -> str:
        return next(course.title for course in COURSES if course.id == lesson.course)

    def _example_card(self, part: str, letter: str, site: Path) -> list[str]:
        lesson = self.example(part)
        if lesson is None:
            return []
        preview = preview_of(lesson, site)
        image = posixpath_relative(self.page, preview.file)
        line = _SENTENCE_END.split(lesson.description)[0] if lesson.description else ""
        slot = self.path.slot_of(lesson)
        home = (
            f"the method path {self.path.curriculum.path(slot.path).title}"
            if slot is not None and slot.path
            else self._course_title(lesson)
        )
        return [
            f"::: {{.home-example data-lesson-id={lesson.id}}}",
            f'`<img class="home-preview" src="{image}"'
            f' alt="{html.escape(preview.alt, quote=True)}"'
            f' width="{PREVIEW_WIDTH}" height="{PREVIEW_HEIGHT}"'
            ' loading="lazy">`{=html}',
            "",
            f"#### [{lesson.title}]({_href(self.page, lesson.page)})"
            f" {{#example-part-{letter.lower()} .unnumbered .unlisted}}",
            "",
            line,
            "",
            f"[A lesson of Part {letter}: {_level(lesson)}, in {home}]{{.home-meta}}",
            ":::",
            "",
        ]

    def curriculum(self, site: Path | None = None) -> str:
        """What you can learn: the learning journey's Part A, Part B, and
        their relation, each part with the owner's example lesson."""
        site = site or project_root(Path.cwd().resolve())
        headings = dict(JOURNEY_SECTIONS)
        lines = [self._heading("curriculum"), "", "::: {.home-curriculum}", ""]
        for part, letter in PARTS:
            lines += [
                f"::: {{.home-part .home-{part}}}",
                "",
                f"### {headings[part]} {{#{part}}}",
                "",
                self.journey._paragraphs(part),
                "",
                *self._example_card(part, letter, site),
                ":::",
                "",
            ]
        lines += [
            "::: {.home-part .home-relation}",
            "",
            f"### {headings['relation']} {{#part-a-to-part-b}}",
            "",
            self.journey._paragraphs("relation"),
            "",
            ":::",
            "",
            ":::",
        ]
        return "\n".join(lines)

    def integrity(self) -> str:
        """The copy's paragraphs, last, and the links to the account of the
        evidence and to the source."""
        return "\n\n".join(
            [
                self._heading("integrity"),
                self._paragraphs("integrity"),
                "::: {.home-more}\n"
                f"[How we verify the science]({self._to(VERIFY_PAGE)})"
                + (
                    f" [The source on GitHub]({self.repository})"
                    if self.repository
                    else ""
                )
                + "\n:::",
            ]
        )

    def markdown(self, site: Path | None = None) -> str:
        """The whole page: the hero, then identity, educational philosophy,
        curriculum, and integrity."""
        return "\n\n".join(
            [
                self.hero(),
                self.identity(),
                self.philosophy(),
                self.curriculum(site),
                self.integrity(),
            ]
        )


def posixpath_relative(from_page: str, target: str) -> str:
    """A relative address of the file ``target`` of the built site, from the
    built ``from_page``."""
    return posixpath.relpath(target, posixpath.dirname(from_page) or ".")


def home_content() -> HomeContent:
    """Return the generated parts of the home page being built. Raises
    ``ValueError`` when the hero's data file, its image files, or the Home
    copy file break a rule."""
    site = project_root(Path.cwd().resolve())
    atlas = Atlas.read(site)
    glossary = Glossary.read(site)
    terms = tuple(entry.term for entry in glossary.entries)
    curriculum = atlas.path.curriculum
    hero = HeroCopy.read(site)
    if found := image_file_problems(hero, site):
        raise ValueError(
            "the hero images break their rules:\n"
            + "\n".join(f"  {message}" for message in found)
        )
    published = {lesson.slot for lesson in atlas.path.lessons if lesson.slot}
    journey = JourneyContent(
        atlas,
        glossary,
        Journey.read(site, curriculum, glossary),
        introduced(site),
        HOME_PAGE,
    )
    return HomeContent(
        journey,
        hero,
        HomeCopy.read(site, curriculum, published, terms),
        repository_url(),
    )
