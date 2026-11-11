"""The generated home page (F134, F158; ADR 021 decision 4 as amended): the
hero's data file and its rules (one fixed headline and subtext, the variants
of F134 as an unused reference), the hero images and their registration, the
hero's markup, the Home copy file and its rules (the owner's fixed copy of
Issue #481), the course subjects of Part A from the curriculum, the two
actions of the first step, and the order of the page, all generated from
data. Home shows no example lesson and does not repeat the canonical
attribution."""

import copy
import hashlib
import json
import re
from dataclasses import replace

import pytest
import yaml
from PIL import Image
from support.paths import SITE_SOURCE

from pbc.authoring.atlas import Atlas
from pbc.authoring.glossary import Glossary
from pbc.authoring.home import (
    ATLAS_ACTION,
    FIRST_LESSON_ACTION,
    HERO_FILE,
    HERO_IMAGE_HEIGHT,
    HERO_IMAGE_WIDTH,
    HOME_FILE,
    PARTS,
    SECTIONS,
    SUBJECTS_LABEL,
    HeroCopy,
    HomeContent,
    HomeCopy,
    hero_problems,
    home_problems,
    image_file_problems,
)
from pbc.authoring.identity import description
from pbc.authoring.journey import Journey, JourneyContent
from pbc.authoring.path import COURSES, LearningPath
from pbc.authoring.website import introduced

ATLAS = Atlas.read(SITE_SOURCE)
PATH = ATLAS.path
CURRICULUM = PATH.curriculum
GLOSSARY = Glossary.read(SITE_SOURCE)
TERMS = tuple(entry.term for entry in GLOSSARY.entries)
JOURNEY = Journey.read(SITE_SOURCE, CURRICULUM, GLOSSARY)
DATA = yaml.safe_load((SITE_SOURCE / HERO_FILE).read_text(encoding="utf-8"))
HERO = HeroCopy.parse(DATA)
COPY_DATA = yaml.safe_load((SITE_SOURCE / HOME_FILE).read_text(encoding="utf-8"))
COPY = HomeCopy.parse(COPY_DATA, CURRICULUM, TERMS)
REGISTER = yaml.safe_load(
    (SITE_SOURCE / "assets" / "provenance.yaml").read_text(encoding="utf-8")
)["assets"]


def _content(page: str = "index.qmd") -> JourneyContent:
    return JourneyContent(ATLAS, GLOSSARY, JOURNEY, introduced(SITE_SOURCE), page)


HOME = HomeContent(_content(), HERO, COPY, "https://example.org/repo")
APOSTROPHE = chr(0x2019)  # as the build sets an apostrophe
LINK = re.compile(r"\]\(([^)]*)\)")
HREF = re.compile(r'\bhref="([^"]*)"')
# The owner's set and choices on Issue #462 (2026-11-09).
OWNER_IMAGES = {
    "double-pendulum": "mechanics",
    "vortex-street": "fluids",
    "hot-cold-gas": "thermodynamics",
    "exoplanet-transit": "astrophysics",
}


def _data():
    return copy.deepcopy(DATA)


def _copy_data():
    return copy.deepcopy(COPY_DATA)


def _home_problems(data) -> list[str]:
    return home_problems(data, CURRICULUM, TERMS)


# --- The hero's data file: the fixed text --------------------------------------


def test_the_data_file_holds_the_owner_s_fixed_headline_and_subtext():
    assert hero_problems(DATA) == []
    # The owner's words, kept exactly: the headline of round 2 of Issue #462
    # (2026-11-10), the subtext of Issue #481 (2026-11-11).
    assert HERO.headline == (
        "The universe has no obligation to fit the limits of human intelligence."
    )
    assert HERO.subtext == (
        "Explore physics by building simulations, working with experimental"
        " data, and investigating how AI could help us understand the physical"
        " world."
    )


def test_the_variants_are_the_eight_pairs_of_f134_kept_as_a_reference():
    # Three headlines with eight subtexts, the first headline the fixed one;
    # nothing but the validation reads them.
    assert len(HERO.variants) == 3
    assert sum(len(subtexts) for _, subtexts in HERO.variants) == 8
    assert HERO.variants[0][0] == HERO.headline
    assert HERO.variants[2][1][1].startswith(
        "We do not know what physics will look like in a hundred years."
    )


def test_without_variants_the_file_is_valid():
    data = _data()
    del data["variants"]
    assert hero_problems(data) == []
    assert HeroCopy.parse(data).variants == ()


def test_a_missing_empty_or_marked_up_headline_or_subtext_fails():
    data = _data()
    data["headline"] = " "
    data["subtext"] = "Physics <b>and</b> AI."
    found = hero_problems(data)
    assert any("the headline has no text" in p for p in found)
    assert any("the subtext holds markup" in p for p in found)
    data = _data()
    del data["subtext"]
    assert any("lacks subtext" in p for p in hero_problems(data))
    with pytest.raises(ValueError, match="rules of the hero"):
        HeroCopy.parse(data)


def test_an_unknown_field_fails_at_every_level():
    for where in ("top", "variant headline", "variant subtext", "images", "image"):
        data = _data()
        target = {
            "top": data,
            "variant headline": data["variants"][0],
            "variant subtext": data["variants"][0]["subtexts"][0],
            "images": data["images"],
            "image": data["images"]["set"][0],
        }[where]
        target["weight"] = 2
        assert any("unknown fields: weight" in p for p in hero_problems(data)), where


def test_a_broken_variant_fails():
    data = _data()
    data["variants"][1]["id"] = "1"
    data["variants"][0]["subtexts"].append(dict(data["variants"][0]["subtexts"][0]))
    data["variants"][2]["subtexts"][0]["text"] = "Physics <b>and</b> AI."
    found = hero_problems(data)
    assert any("variant headline id '1' appears more than once" in p for p in found)
    assert any("variant pair 1a appears more than once" in p for p in found)
    assert any("variant subtext 3a holds markup" in p for p in found)
    data = _data()
    data["variants"][0]["subtexts"] = "none"
    assert any("has no list of subtexts" in p for p in hero_problems(data))
    data["variants"] = {"a": 1}
    assert "'variants' is not a list" in hero_problems(data)


def test_a_site_without_the_data_file_fails(tmp_path):
    with pytest.raises(ValueError):
        HeroCopy.read(tmp_path)


# --- The hero's data file: the images ----------------------------------------


def test_the_data_file_holds_the_owner_s_four_images_with_the_pendulum_default():
    assert {image.id: image.sequence for image in HERO.images} == OWNER_IMAGES
    assert [image.id for image in HERO.images] == list(OWNER_IMAGES)
    assert HERO.default_image == "double-pendulum"


@pytest.mark.parametrize("image_id", list(OWNER_IMAGES))
def test_each_hero_image_has_its_file_its_register_entry_and_its_alt_text(
    image_id: str,
):
    """Each image's own test: a WebP file at hero size under site/assets/hero,
    and a complete register entry whose master, hash, and origin are those of
    the atlas panel of its course (the masters the owner supplied and the
    Issue matched by SHA-256), so no hero file comes from an atlas file and
    no origin is claimed that the atlas entry does not record."""
    image = HERO.image(image_id)
    file = SITE_SOURCE / image.file
    with Image.open(file) as opened:
        assert opened.format == "WEBP"
        assert opened.size == (HERO_IMAGE_WIDTH, HERO_IMAGE_HEIGHT)
    entry = REGISTER[image.file.removeprefix("assets/")]
    atlas = REGISTER[f"atlas/{image.sequence}-panel-800.webp"]
    for field in ("master", "sha256", "author", "licence", "date"):
        assert entry[field] == atlas[field], field
    assert entry.get("script") == atlas.get("script")
    assert "model" not in entry
    assert "derive_assets.py --hero" in entry["source"]
    # Never the atlas file itself, which is smaller and would be upscaled.
    atlas_file = SITE_SOURCE / "assets" / "atlas" / f"{image.sequence}-panel-800.webp"
    assert hashlib.sha256(file.read_bytes()).digest() != (
        hashlib.sha256(atlas_file.read_bytes()).digest()
    )
    # Its alternative text names what it is and claims no result.
    assert image.alt.startswith("Illustration: ")
    assert not re.search(r"\b(verified|result|measured|simulat\w*)\b", image.alt)


def test_the_exoplanet_transit_names_its_author_and_no_script():
    entry = REGISTER["hero/exoplanet-transit.webp"]
    assert entry["author"] and "script" not in entry


def test_an_image_rule_broken_fails():
    cases = {
        "id": ("id", "Double_Pendulum", "lower-case words joined by hyphens"),
        "sequence": ("sequence", "law-discovery", "no course of Part A"),
        "alt": ("alt", "An <em>image</em>", "holds markup"),
        "empty alt": ("alt", " ", "has no text"),
    }
    for name, (field, value, message) in cases.items():
        data = _data()
        data["images"]["set"][1][field] = value
        assert any(message in p for p in hero_problems(data)), name


def test_a_duplicate_image_a_bad_default_or_no_images_fails():
    data = _data()
    data["images"]["set"].append(dict(data["images"]["set"][0]))
    assert any(
        "double-pendulum appears more than once" in p for p in hero_problems(data)
    )
    data = _data()
    data["images"]["default"] = "ising"
    assert any("default image 'ising'" in p for p in hero_problems(data))
    data = _data()
    data["images"]["set"] = []
    assert any("no list 'set'" in p for p in hero_problems(data))
    data = _data()
    del data["images"]
    assert any("lacks images" in p for p in hero_problems(data))


def test_an_image_without_its_file_or_its_register_entry_fails(tmp_path):
    (tmp_path / "assets" / "hero").mkdir(parents=True)
    (tmp_path / "assets" / "provenance.yaml").write_text(
        "assets:\n  hero/double-pendulum.webp: {}\n", encoding="utf-8"
    )
    (tmp_path / "assets" / "hero" / "vortex-street.webp").write_bytes(b"")
    found = image_file_problems(HERO, tmp_path)
    assert (
        "the hero image double-pendulum has no file assets/hero/double-pendulum.webp"
        in found
    )
    assert "the hero image vortex-street is not in the provenance register" in found
    assert image_file_problems(HERO, SITE_SOURCE) == []


# --- The hero's markup -------------------------------------------------------


def _data_of(hero: str, element: str) -> list[dict]:
    (found,) = re.findall(
        rf'<script type="application/json" id="{element}">(.*?)</script>', hero
    )
    return json.loads(found)


def test_the_hero_carries_one_h1_with_the_fixed_text_and_no_other_copy():
    hero = HOME.hero()
    assert hero.count("<h1") == 1
    (h1,) = re.findall(r"<h1[^>]*>(.*?)</h1>", hero)
    assert h1 == HERO.headline.replace("'", APOSTROPHE)
    (subtext,) = re.findall(r'<p class="hero-subtext">(.*?)</p>', hero)
    assert subtext == HERO.subtext.replace("'", APOSTROPHE)
    # No pairs: no data for a script to swap the text, no hidden copies, no
    # marker of a chosen pair.
    assert "hero-pairs" not in hero and "data-hero=" not in hero
    assert "hero-pair" not in hero and "hero-ghost" not in hero
    # The variants are only a reference: none of their texts is on the page
    # (the first headline is the fixed one).
    for headline, subtexts in HERO.variants:
        if headline != HERO.headline:
            assert headline.replace("'", APOSTROPHE) not in hero
        for text in subtexts:
            assert text.replace("'", APOSTROPHE) not in hero


def test_the_default_image_is_in_the_html_inside_noscript_and_the_set_is_data():
    hero = HOME.hero()
    default = HERO.image(HERO.default_image)
    # The one image of the HTML is the default, inside <noscript>: without
    # scripts it is shown, with scripts it is not requested.
    images = re.findall(r"<img [^>]*>", hero)
    assert len(images) == 1
    (inside,) = re.findall(r"<noscript>(.*?)</noscript>", hero)
    assert inside == images[0]
    assert 'src="assets/hero/double-pendulum.webp"' in inside
    assert f'alt="{default.alt}"' in inside
    assert f'width="{HERO_IMAGE_WIDTH}" height="{HERO_IMAGE_HEIGHT}"' in inside
    assert 'data-hero-image="double-pendulum"' in hero
    # Every image of the set as data for the script, with its alt text.
    data = _data_of(hero, "hero-images")
    assert [item["id"] for item in data] == list(OWNER_IMAGES)
    for item in data:
        image = HERO.image(item["id"])
        assert item["src"] == f"assets/hero/{image.id}.webp"
        assert item["alt"] == image.alt.replace("'", APOSTROPHE)
        assert (item["width"], item["height"]) == (HERO_IMAGE_WIDTH, HERO_IMAGE_HEIGHT)
    # No constellation, no inline SVG, no link inside the image.
    assert "<svg" not in hero and "hero-node" not in hero


def test_the_script_follows_the_figure_and_the_data():
    hero = HOME.hero()
    order = [
        hero.index('class="hero-copy"'),
        hero.index('id="hero-figure"'),
        hero.index('id="hero-images"'),
        hero.index('<script src="learner/hero.js"></script>'),
        hero.index('class="home-actions"'),
    ]
    assert order == sorted(order)


def test_the_embedded_data_cannot_close_its_script_element():
    data = _data()
    data["images"]["set"][0]["alt"] = "Illustration: plain & simple."
    home = replace(HOME, hero_copy=HeroCopy.parse(data))
    hero = home.hero()
    assert "\\u0026" in hero
    assert _data_of(hero, "hero-images")[0]["alt"] == "Illustration: plain & simple."


def test_the_page_source_holds_no_copy_but_the_data_files():
    source = (SITE_SOURCE / "index.qmd").read_text(encoding="utf-8")
    assert HERO.headline not in source and HERO.subtext not in source
    for headline, subtexts in HERO.variants:
        assert headline not in source
        assert all(text not in source for text in subtexts)
    for texts in COPY.texts.values():
        for text in texts:
            assert text[:40] not in source
    # The page writes no link and no heading of its own.
    assert not LINK.search(source)
    markdown = re.sub(r"```\{python\}.*?```", "", source, flags=re.S)
    assert not re.search(r"^#+ ", markdown, re.M)


# --- The first step -----------------------------------------------------------


def _header_targets() -> dict[str, str]:
    """The pages of the header's Course Atlas link and Start learning
    button, as the built site addresses them."""
    navbar = yaml.safe_load((SITE_SOURCE / "_quarto.yml").read_text())["website"][
        "navbar"
    ]
    items = navbar["left"] + navbar["right"]
    target = {item["text"]: item["href"] for item in items}
    return {
        "atlas": target["Course Atlas"].removesuffix(".qmd") + ".html",
        "start": target["[Start learning]{.pbc-start}"].removesuffix(".qmd") + ".html",
    }


def test_the_two_actions_lead_where_the_header_leads_the_atlas_first():
    actions = HOME.actions()
    header = _header_targets()
    assert HREF.findall(actions) == [header["atlas"], header["start"]]
    assert re.findall(r'<a class="([^"]+)"', actions) == [
        "home-action-primary",
        "home-action",
    ]
    assert re.findall(r">([^<]+)</a>", actions) == [ATLAS_ACTION, FIRST_LESSON_ACTION]
    # The first lesson of Part A, the start of the first course.
    first = PATH.in_course(PATH.courses[0])[0]
    assert header["start"] == first.page.removesuffix(".qmd") + ".html"
    # The hero holds the actions and no other link.
    assert HREF.findall(HOME.hero()) == [header["atlas"], header["start"]]


# --- The Home copy file -----------------------------------------------------

# The owner's copy of Issue #481 (2026-11-11), kept exactly: each section's
# heading and paragraphs, and each part's.
OWNER_HEADINGS = {
    "identity": "What is Physics by Construction?",
    "philosophy": "Build. Experiment. Understand.",
    "curriculum": "From computational physics to artificial intelligence",
    "integrity": "How we verify what we teach",
}
OWNER_PARTS = {
    "part-a": "Part A \u2014 Computational and experimental physics",
    "part-b": "Part B \u2014 Can AI help us discover new physics?",
    "relation": "First understand the physics. Then challenge the AI.",
}
OWNER_TEXT = {
    "identity": (
        "Physics by Construction is a free, open-source online physics project"
        " built around simulations, experiments, and scientific reasoning.",
        "Many lessons begin with a physical question. How does a pendulum move?"
        " How do waves propagate? What causes a fluid to form vortices? You"
        " explore these questions by building models in Python, running"
        " simulations, changing conditions, and comparing the results with"
        " established theory or recorded experimental measurements. The goal is"
        " not just to learn the equations, but to understand what they predict,"
        " why they work, and where their limitations lie.",
        "Beyond learning established physics, the project also explores how"
        " artificial intelligence might support scientific research, and how we"
        " can determine whether its conclusions are reliable.",
    ),
    "philosophy": (
        "Learning physics is more than memorising equations. It means"
        " understanding how the physical world behaves and learning how to"
        " investigate it.",
        "Physics by Construction follows the scientific process: ask a"
        " question, develop a model, make predictions, investigate the results,"
        " and examine where the model succeeds or fails. Through experimentation,"
        " mathematical theory becomes something you can explore, question, and"
        " understand.",
    ),
    "part-a": (
        "Learn physics by building and exploring computational models. Through"
        " Python simulations and numerical experiments, you investigate how"
        " physical systems behave and how mathematical theories describe them.",
        "Some lessons also use recorded experimental measurements, allowing you"
        " to compare theoretical predictions with observations. Throughout the"
        " courses, you learn how to test your models, understand their"
        " limitations, and evaluate the reliability of their results.",
        "The result is a deeper understanding of physics through experimentation.",
    ),
    "part-b": (
        "Artificial intelligence is transforming how we analyse information,"
        " write software, and solve complex problems. But could it also help"
        " scientists design experiments, analyse complex data, or uncover"
        " relationships in physical systems?",
        "In Part B, you explore how AI agents can conduct computational"
        " experiments, search for mathematical relationships, and reason about"
        " physical systems. You examine what happens when these systems are"
        " given scientific problems and investigate whether their conclusions"
        " can be trusted.",
        "The aim is not to assume that AI can make scientific discoveries, but"
        " to explore what it would take for AI to become a reliable partner in"
        " scientific research.",
    ),
    "relation": (
        "Before asking AI to investigate a physical system, you need to"
        " understand what a trustworthy result looks like. Part A provides that"
        " foundation through simulations, theory, and experiments. Part B"
        " builds on it by evaluating what AI can contribute to the scientific"
        " process.",
    ),
    "integrity": (
        "Scientific results should be reproducible, transparent, and open to scrutiny.",
        "The code used in our lessons is tested automatically, and results are"
        " checked against established theory, independent calculations, or"
        " experimental measurements where appropriate. Some lessons also"
        " include computer-verified mathematical proofs.",
        "We explain the assumptions and limitations behind the results so you"
        " can understand not only what a model shows, but also how much"
        " confidence to place in it.",
    ),
}


def test_the_copy_file_holds_the_four_sections_in_order():
    assert home_problems(COPY_DATA, CURRICULUM, TERMS) == []
    assert list(COPY_DATA) == [key for key, _ in SECTIONS]
    assert set(COPY.headings) == {key for key, _ in SECTIONS}
    assert list(COPY_DATA["curriculum"]) == ["heading", *(p for p, _ in PARTS)]


def test_the_copy_is_the_owner_s_exactly():
    assert COPY.headings == OWNER_HEADINGS
    assert {part: heading for part, (heading, _) in COPY.parts.items()} == (OWNER_PARTS)
    for key in ("identity", "philosophy", "integrity"):
        assert COPY.texts[key] == OWNER_TEXT[key], key
    for part in OWNER_PARTS:
        assert COPY.parts[part][1] == OWNER_TEXT[part], part


def test_an_unknown_or_missing_section_or_field_fails():
    data = _copy_data()
    data["testimonials"] = {"heading": "x", "text": ["y"]}
    assert any("unknown fields: testimonials" in p for p in _home_problems(data))
    data = _copy_data()
    del data["integrity"]
    assert any("lacks integrity" in p for p in _home_problems(data))
    data = _copy_data()
    data["philosophy"]["lessons"] = ["M1"]
    assert any(
        "philosophy has unknown fields: lessons" in p for p in _home_problems(data)
    )
    data = _copy_data()
    data["curriculum"]["text"] = ["A list of the courses."]
    assert any("curriculum has unknown fields: text" in p for p in _home_problems(data))
    # The examples of F158 are gone: naming one fails.
    data = _copy_data()
    data["curriculum"]["examples"] = {"part-a": "M1"}
    assert any(
        "curriculum has unknown fields: examples" in p for p in _home_problems(data)
    )
    data = _copy_data()
    del data["curriculum"]["relation"]
    assert any("curriculum lacks relation" in p for p in _home_problems(data))
    data = _copy_data()
    data["curriculum"]["part-b"]["lessons"] = ["SA5"]
    assert any(
        "curriculum part-b has unknown fields: lessons" in p
        for p in _home_problems(data)
    )
    data = _copy_data()
    del data["curriculum"]["part-a"]["heading"]
    assert any("curriculum part-a lacks heading" in p for p in _home_problems(data))
    data = _copy_data()
    data["curriculum"]["part-a"]["text"] = []
    assert any(
        "curriculum part-a has no non-empty list" in p for p in _home_problems(data)
    )
    data = _copy_data()
    del data["identity"]["heading"]
    assert any("identity lacks heading" in p for p in _home_problems(data))
    data = _copy_data()
    data["identity"]["text"] = []
    assert any("identity has no non-empty list" in p for p in _home_problems(data))
    assert _home_problems(None)
    with pytest.raises(ValueError, match="rules of the Home copy"):
        HomeCopy.parse(data, CURRICULUM, TERMS)


def test_the_text_rules_of_the_journey_hold_for_the_copy():
    cases = {
        "heading markup": ("identity", "heading", "What <b>this</b> is", "markup"),
        "a link by hand": (
            "integrity",
            "text",
            ["See [the page](verify.html)."],
            "more than inline Markdown",
        ),
        "a count": (
            "philosophy",
            "text",
            ["There are 94 lessons in eight courses."],
            "count",
        ),
        "an unresolved reference": (
            "philosophy",
            "text",
            ["Begin with {slot:Z99}."],
            "not in the curriculum file",
        ),
        "a lesson named by hand": (
            "identity",
            "text",
            ["Read M1 first."],
            "names lessons outside a reference",
        ),
    }
    for name, (section, field, value, message) in cases.items():
        data = _copy_data()
        data[section][field] = value
        assert any(message in p for p in _home_problems(data)), name


def test_home_has_no_rule_about_the_word_discover():
    # The home page is not part of the curriculum (owner's decision, Issue #481).
    data = _copy_data()
    data["integrity"]["text"] = ["Agents discover new laws here."]
    data["curriculum"]["part-b"]["text"] = ["Can AI help us discover new physics?"]
    assert [p for p in _home_problems(data) if "'discover'" in p] == []


def test_the_journey_itself_keeps_the_strict_rule():
    from pbc.authoring.journey import journey_problems

    data = yaml.safe_load((SITE_SOURCE / "journey.yaml").read_text(encoding="utf-8"))
    key = next(k for k, v in data.items() if isinstance(v, list))
    data[key] = ["Can AI help us discover new physics?"]
    assert any("'discover'" in p for p in journey_problems(data, CURRICULUM, TERMS))


def test_a_reference_in_the_copy_resolves_to_a_link():
    data = _copy_data()
    data["philosophy"]["text"] = ["If unsure, begin with {slot:M1}."]
    home = replace(HOME, copy=HomeCopy.parse(data, CURRICULUM, TERMS))
    first = PATH.in_course(PATH.courses[0])[0]
    assert f"[{first.title}]({first.page.removesuffix('.qmd')}.html)" in (
        home.philosophy()
    )


# --- The course subjects of Part A ------------------------------------------


def _subjects(section: str) -> list[str]:
    (listing,) = re.findall(r'<ul class="home-subjects"[^>]*>(.*?)</ul>', section)
    return re.findall(r"<li>(.*?)</li>", listing)


def test_the_subjects_are_the_eight_courses_of_the_curriculum_file_in_order():
    curriculum_file = yaml.safe_load(
        (SITE_SOURCE / "curriculum.yaml").read_text(encoding="utf-8")
    )
    titles = [course["title"] for course in curriculum_file["courses"]]
    assert len(titles) == 8
    section = HOME.curriculum()
    # Every course has a published lesson today: no mark.
    assert _subjects(section) == titles
    assert [course.title for course in COURSES] == titles
    assert f'aria-label="{SUBJECTS_LABEL}"' in section
    # Plain names: no link in the list.
    (listing,) = re.findall(r'<ul class="home-subjects".*?</ul>', section)
    assert "<a " not in listing and "](" not in listing


def test_a_course_without_a_published_lesson_is_marked_planned():
    lessons = tuple(lesson for lesson in PATH.lessons if lesson.course != "quantum")
    path = LearningPath(lessons, PATH.curriculum)
    journey = replace(_content(), atlas=replace(ATLAS, path=path))
    home = replace(HOME, journey=journey)
    subjects = _subjects(home.curriculum())
    assert "Quantum physics (planned)" in subjects
    assert sum("(planned)" in subject for subject in subjects) == 1


def test_the_subjects_follow_part_a_and_nothing_else_names_a_course():
    section = HOME.curriculum()
    order = [
        section.index("### " + OWNER_PARTS["part-a"]),
        section.index('class="home-subjects"'),
        section.index("### " + OWNER_PARTS["part-b"]),
        section.index("### " + OWNER_PARTS["relation"]),
    ]
    assert order == sorted(order)
    assert section.count('class="home-subjects"') == 1


# --- The page -----------------------------------------------------------------


def test_the_page_follows_identity_philosophy_curriculum_and_integrity_last():
    page = HOME.markdown()
    headings = re.findall(r"^## (.*?) \{#([\w-]+)\}", page, re.M)
    assert headings == [(COPY.headings[key], anchor) for key, anchor in SECTIONS]
    assert page.index('class="home-hero"') < page.index("## ")
    # Integrity is last: nothing after its links but the end of the page.
    assert page.rstrip().endswith(":::")
    assert "## Begin" not in page
    assert "From a question to a working model" not in page
    assert "lessons published" not in page


def test_identity_holds_the_owner_s_text_and_its_one_link_not_the_attribution():
    identity = HOME.identity()
    paragraphs = identity.split("\n\n")
    assert paragraphs[1] == COPY.texts["identity"][0]
    for text in COPY.texts["identity"]:
        assert text in identity
    # The canonical attribution is on About and in the footer, not here.
    assert description() not in HOME.markdown()
    assert "by JIDAI, created by Ahmet Taspinar" not in HOME.markdown()
    assert LINK.findall(identity) == ["about.html#creator-and-jidai"]


def test_integrity_links_the_account_of_the_evidence_and_the_source():
    integrity = HOME.integrity()
    for text in COPY.texts["integrity"]:
        assert text in integrity
    assert LINK.findall(integrity)[-2:] == ["verify.html", "https://example.org/repo"]
    assert "The source on GitHub" not in replace(HOME, repository="").integrity()


def test_the_curriculum_section_is_the_copy_file_s_parts_without_examples():
    section = HOME.curriculum()
    for part, anchor in PARTS:
        heading, texts = COPY.parts[part]
        assert f"### {heading} {{#{anchor}}}" in section
        for text in texts:
            assert text in section, part
    # No example lesson, no preview, and no link at all in the section.
    assert "home-example" not in section and "previews/" not in section
    assert "<img" not in section and not LINK.search(section)
    # Home does not take the parts from the journey file: the atlas's and
    # About's longer text is not repeated here.
    for key in ("part-a", "part-b", "relation"):
        for text in JOURNEY.sections[key]:
            assert _content().inline(text) not in section, key
