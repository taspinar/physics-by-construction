"""The generated home page (F134, ADR 021 decision 4; F158, requirements
decision 43 and the amendment of decision 4): the hero, then the four
sections of the Home copy file in the order identity, educational
philosophy, curriculum, and integrity.

The hero's copy is the owner's, held in the data file ``site/hero.yaml``
beside the curriculum file and validated here: one fixed headline and one
fixed subtext (round 2 of Issue #462, 2026-11-10; the subtext of Issue
#481, 2026-11-11), written into the HTML by
the build and never changed by a script, so the page shows the same text
with and without scripts and after a reload. The file keeps the three
headlines and eight subtexts of F134 under ``variants`` as an editorial
reference: validated as plain text, never written on a page or used by a
script. No copy of the hero is written on the page by hand.

The hero image is one of a small set of Part A illustrations (interface
artwork of ADR 021 decision 1), held in the same data file: each a WebP file
under ``site/assets/hero/`` named by its identifier and registered in the
provenance register, with the course whose atlas master it is derived from
and its alternative text. The default image stands in the HTML inside
``<noscript>``, so that it is what a page without scripts shows and what a
reader of the HTML sees, and is not requested when the script runs: the
script creates the one image it picks, at random, or the one the
``hero-image`` parameter names. Exactly one hero image is requested per
load.

The sections after the hero come from ``site/home.yaml``, the owner's
fixed copy (Issue #481, 2026-11-11): prose and references under the rules
of the learning journey, with a form of "discover" only in a question or
after a negation. The curriculum section holds Part A, Part B, and the
transition between them, each with its own heading and text; the longer
text of the learning journey (``site/journey.yaml``) stays on the Course
Atlas and About. After Part A the page names the course subjects, from the
curriculum (``COURSES``, which the curriculum file is validated against), a
course without a published lesson marked as planned. Home shows no example
lesson: lesson discovery belongs to the Course Atlas. The introduction does
not repeat the canonical attribution of ``pbc.authoring.identity``, which
About and the footer carry; it ends with the one link to it. Every link is
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
from pbc.authoring.identity import ABOUT_ANCHOR
from pbc.authoring.introductions import sequence_ids
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
)
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
# The parameter that forces an image, for tests and screenshots. (The `hero`
# parameter of F134 that forced a headline pair is gone with the pairs: the
# hero text is fixed.)
HERO_IMAGE_PARAMETER = "hero-image"

# The sections of the Home copy file in the order of the page, with the
# anchor of each (the identity keeps the anchor of F134's "What this site
# is").
SECTIONS = (
    ("identity", "about-the-site"),
    ("philosophy", "how-physics-is-learned"),
    ("curriculum", "what-you-can-learn"),
    ("integrity", "integrity"),
)
# The parts of the curriculum section in the order of the page, each a
# heading and its text in the copy file, with the anchor of its heading:
# Part A, Part B, and the transition between them.
PARTS = (
    ("part-a", "part-a"),
    ("part-b", "part-b"),
    ("relation", "part-a-to-part-b"),
)
# The accessible name of the list of the course subjects after Part A.
SUBJECTS_LABEL = "The courses of Part A"
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


# --- The hero's copy -------------------------------------------------------


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
    headline: str
    subtext: str
    images: tuple[HeroImage, ...] = ()
    default_image: str = ""
    # The editorial reference: the headlines of F134, each with its
    # subtexts, as (headline, (subtext, ...)); nothing shows them.
    variants: tuple[tuple[str, tuple[str, ...]], ...] = ()

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
            _words(data["headline"]),
            _words(data["subtext"]),
            tuple(
                HeroImage(item["id"], item["sequence"], _words(item["alt"]))
                for item in data["images"]["set"]
            ),
            data["images"]["default"],
            tuple(
                (
                    _words(headline["text"]),
                    tuple(_words(s["text"]) for s in headline["subtexts"]),
                )
                for headline in data.get("variants") or []
            ),
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
    """Every rule of the hero's data file that ``data`` breaks: a plain,
    non-empty ``headline`` and ``subtext``; the images (``image_problems``);
    no field beyond those and the optional ``variants``; and the variants,
    the editorial reference, each a headline with ``id``, ``text``, and
    ``subtexts`` of ``id`` and ``text``, plain text, each id once."""
    if not isinstance(data, dict):
        return [
            f"{HERO_FILE} is not a mapping with 'headline', 'subtext', and 'images'"
        ]
    found = _fields(
        HERO_FILE, data, {"headline", "subtext", "images"} | set(data) & {"variants"}
    )
    found += _text_problems("the headline", data.get("headline"))
    found += _text_problems("the subtext", data.get("subtext"))
    found += image_problems(data.get("images"))
    if "variants" in data:
        found += _variant_problems(data["variants"])
    return found


def _variant_problems(headlines: object) -> list[str]:
    """Every rule of the editorial reference ``variants`` that it breaks: a
    list of headlines, each with exactly ``id``, ``text``, and a list of
    ``subtexts`` with exactly ``id`` and ``text``; plain, non-empty text;
    each headline id and each pair (headline id and subtext id) once."""
    if not isinstance(headlines, list):
        return ["'variants' is not a list"]
    found: list[str] = []
    identifiers: list[str] = []
    headline_ids: list[str] = []
    for number, headline in enumerate(headlines, start=1):
        where = f"variant headline {number}"
        found += _fields(where, headline, {"id", "text", "subtexts"})
        if not isinstance(headline, dict):
            continue
        headline_id = str(headline.get("id", ""))
        headline_ids.append(headline_id)
        found += _text_problems(
            f"variant headline {headline_id or number}", headline.get("text")
        )
        subtexts = headline.get("subtexts")
        if not isinstance(subtexts, list):
            found.append(
                f"variant headline {headline_id or number} has no list of subtexts"
            )
            continue
        for subtext in subtexts:
            found += _fields(
                f"a subtext of variant headline {headline_id}", subtext, {"id", "text"}
            )
            if not isinstance(subtext, dict):
                continue
            pair = f"{headline_id}{subtext.get('id', '')}"
            identifiers.append(pair)
            found += _text_problems(f"variant subtext {pair}", subtext.get("text"))
    for headline_id in sorted({h for h in headline_ids if headline_ids.count(h) > 1}):
        found.append(f"the variant headline id {headline_id!r} appears more than once")
    for pair in sorted({p for p in identifiers if identifiers.count(p) > 1}):
        found.append(f"the variant pair {pair} appears more than once")
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
    terms: Collection[str] = (),
) -> list[str]:
    """Every rule of the Home copy file that ``data`` breaks: a mapping of
    exactly the four sections; each a mapping of a ``heading`` (plain,
    non-empty text) and, except the curriculum, ``text``, a non-empty list
    of paragraphs under the text rules of the learning journey (inline
    Markdown, references that resolve, no count, no lesson named outside a
    reference), with a form of "discover" only in a question or after a
    negation in its sentence; the curriculum's ``part-a``, ``part-b``, and
    ``relation``, each a mapping of a ``heading`` and ``text`` under the
    same rules."""
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
        if key not in data:
            continue
        if key == "curriculum":
            found += _section_problems(
                key, data[key], {"heading", *(part for part, _ in PARTS)}
            )
            section = data[key]
            if not isinstance(section, dict):
                continue
            for part, _ in PARTS:
                if part in section:
                    found += _section_problems(
                        f"{key} {part}",
                        section[part],
                        {"heading", "text"},
                        curriculum,
                        sequences,
                        terms,
                    )
            continue
        found += _section_problems(
            key, data[key], {"heading", "text"}, curriculum, sequences, terms
        )
    return found


def _section_problems(
    name: str,
    section: object,
    fields: set[str],
    curriculum: Curriculum | None = None,
    sequences: Collection[str] = (),
    terms: Collection[str] = (),
) -> list[str]:
    """The rules of one section of the copy file, or of one part of the
    curriculum section: exactly ``fields``, a plain heading, and, when
    ``fields`` holds ``text``, a non-empty list of paragraphs under the text
    rules."""
    where = HOME_FILE
    if not isinstance(section, dict):
        return [f"{where}: {name} is not a mapping"]
    found = []
    if unknown := set(section) - fields:
        found.append(
            f"{where}: {name} has unknown fields: "
            + ", ".join(sorted(map(str, unknown)))
        )
    for field in sorted(fields - set(section)):
        found.append(f"{where}: {name} lacks {field}")
    if "heading" in section:
        found += _text_problems(f"the heading of {name}", section["heading"])
    if "text" not in fields or "text" not in section:
        return found
    texts = section["text"]
    if not isinstance(texts, list) or not texts:
        return [*found, f"{where}: {name} has no non-empty list 'text'"]
    assert curriculum is not None
    for number, text in enumerate(texts, start=1):
        found += _journey_text_problems(
            f"{where}: {name} {number}",
            text,
            curriculum,
            sequences,
            terms,
            framed_discovery=True,
        )
    return found


@dataclass(frozen=True)
class HomeCopy:
    """The validated copy of Home: the heading and paragraphs of each
    section, and of each part of the curriculum section (the curriculum
    section's own paragraphs are empty)."""

    headings: dict[str, str]
    texts: dict[str, tuple[str, ...]]
    # "part-a" -> (its heading, its paragraphs)
    parts: dict[str, tuple[str, tuple[str, ...]]]

    @classmethod
    def parse(
        cls,
        data: object,
        curriculum: Curriculum,
        terms: Collection[str] = (),
    ) -> HomeCopy:
        found = home_problems(data, curriculum, terms)
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
            {
                part: (
                    _words(data["curriculum"][part]["heading"]),
                    tuple(_words(text) for text in data["curriculum"][part]["text"]),
                )
                for part, _ in PARTS
            },
        )

    @classmethod
    def read(
        cls,
        site: Path,
        curriculum: Curriculum,
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
        return cls.parse(data, curriculum, terms)


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
        """The hero as one raw HTML block: the fixed headline and subtext,
        the figure with the default image for a page without scripts, the
        images as data, the script, and the two actions."""
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
                # The one fixed text of the hero: static content that no
                # script touches.
                '<div class="hero-copy" id="hero-copy">',
                '<h1 class="hero-headline" id="hero-headline">'
                f"{html.escape(_typographic(self.hero_copy.headline))}</h1>",
                '<p class="hero-subtext">'
                f"{html.escape(_typographic(self.hero_copy.subtext))}</p>",
                "</div>",
                self.hero_figure(),
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
        """The copy's paragraphs and the one link to the creator and JIDAI.
        The canonical attribution is not repeated here: About and the
        footer carry it (Issue #481)."""
        return "\n\n".join(
            [
                self._heading("identity"),
                self._paragraphs("identity"),
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

    def subjects(self) -> str:
        """The course subjects of Part A as one list, in the order of the
        curriculum; a course without a published lesson is marked as
        planned. Plain names: the Course Atlas leads to the lessons."""
        items = "".join(
            f"<li>{html.escape(course.title)}"
            + ("" if self.path.in_course(course) else " (planned)")
            + "</li>"
            for course in COURSES
        )
        return (
            "```{=html}\n"
            f'<ul class="home-subjects" aria-label="{SUBJECTS_LABEL}">{items}</ul>\n'
            "```"
        )

    def _part(self, part: str, anchor: str) -> list[str]:
        heading, texts = self.copy.parts[part]
        return [
            f"::: {{.home-part .home-{part}}}",
            "",
            f"### {heading} {{#{anchor}}}",
            "",
            "\n\n".join(self.journey.inline(text) for text in texts),
            "",
            *([self.subjects(), ""] if part == "part-a" else []),
            ":::",
            "",
        ]

    def curriculum(self) -> str:
        """From computational physics to artificial intelligence: Part A
        with the course subjects, Part B, and the transition between them,
        from the copy file; no example lesson."""
        lines = [self._heading("curriculum"), "", "::: {.home-curriculum}", ""]
        for part, anchor in PARTS:
            lines += self._part(part, anchor)
        lines.append(":::")
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

    def markdown(self) -> str:
        """The whole page: the hero, then identity, educational philosophy,
        curriculum, and integrity."""
        return "\n\n".join(
            [
                self.hero(),
                self.identity(),
                self.philosophy(),
                self.curriculum(),
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
        HomeCopy.read(site, curriculum, terms),
        repository_url(),
    )
