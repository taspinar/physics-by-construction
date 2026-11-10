"""The generated home page (F134, F158; ADR 021 decision 4 as amended): the
hero's data file and its rules (one fixed headline and subtext, the variants
of F134 as an unused reference), the hero images and their registration, the
hero's markup, the Home copy file and its rules, the owner's example lessons
validated against the published lessons, the two actions of the first step,
and the order of the page, all generated from data."""

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
    SECTIONS,
    HeroCopy,
    HomeContent,
    HomeCopy,
    hero_problems,
    home_problems,
    image_file_problems,
)
from pbc.authoring.identity import description
from pbc.authoring.journey import Journey, JourneyContent
from pbc.authoring.previews import HEIGHT as PREVIEW_HEIGHT
from pbc.authoring.previews import WIDTH as PREVIEW_WIDTH
from pbc.authoring.website import introduced

ATLAS = Atlas.read(SITE_SOURCE)
PATH = ATLAS.path
CURRICULUM = PATH.curriculum
GLOSSARY = Glossary.read(SITE_SOURCE)
TERMS = tuple(entry.term for entry in GLOSSARY.entries)
PUBLISHED = frozenset(lesson.slot for lesson in PATH.lessons if lesson.slot)
JOURNEY = Journey.read(SITE_SOURCE, CURRICULUM, GLOSSARY)
DATA = yaml.safe_load((SITE_SOURCE / HERO_FILE).read_text(encoding="utf-8"))
HERO = HeroCopy.parse(DATA)
COPY_DATA = yaml.safe_load((SITE_SOURCE / HOME_FILE).read_text(encoding="utf-8"))
COPY = HomeCopy.parse(COPY_DATA, CURRICULUM, PUBLISHED, TERMS)
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
OWNER_EXAMPLES = {
    "part-a": "mechanics/01-kinematics-as-a-program",
    "part-b": "agents-llm/01-an-agent-runs-an-experiment",
}


def _data():
    return copy.deepcopy(DATA)


def _copy_data():
    return copy.deepcopy(COPY_DATA)


def _home_problems(data) -> list[str]:
    return home_problems(data, CURRICULUM, PUBLISHED, TERMS)


# --- The hero's data file: the fixed text --------------------------------------


def test_the_data_file_holds_the_owner_s_fixed_headline_and_subtext():
    assert hero_problems(DATA) == []
    # The owner's words (round 2 of Issue #462 and its correction,
    # 2026-11-10), kept exactly.
    assert HERO.headline == (
        "The universe has no obligation to fit the limits of human intelligence."
    )
    assert HERO.subtext == (
        "Explore physics by building models, testing predictions against real"
        " data, and discovering what AI might make possible."
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


def test_the_copy_file_holds_the_four_sections_in_order():
    assert home_problems(COPY_DATA, CURRICULUM, PUBLISHED, TERMS) == []
    assert list(COPY_DATA) == [key for key, _ in SECTIONS]
    assert set(COPY.headings) == {key for key, _ in SECTIONS}
    assert COPY.headings["curriculum"] == "What you can learn"


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
    data = _copy_data()
    del data["identity"]["heading"]
    assert any("identity lacks heading" in p for p in _home_problems(data))
    data = _copy_data()
    data["identity"]["text"] = []
    assert any("identity has no non-empty list" in p for p in _home_problems(data))
    assert _home_problems(None)
    with pytest.raises(ValueError, match="rules of the Home copy"):
        HomeCopy.parse(data, CURRICULUM, PUBLISHED, TERMS)


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
        "a discovery": (
            "integrity",
            "text",
            ["Agents discover new laws here."],
            "'discover'",
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


def test_a_reference_in_the_copy_resolves_to_a_link():
    data = _copy_data()
    data["philosophy"]["text"] = ["If unsure, begin with {slot:M1}."]
    home = replace(HOME, copy=HomeCopy.parse(data, CURRICULUM, PUBLISHED, TERMS))
    first = PATH.in_course(PATH.courses[0])[0]
    assert f"[{first.title}]({first.page.removesuffix('.qmd')}.html)" in (
        home.philosophy()
    )


# --- The owner's examples -----------------------------------------------------


def test_the_examples_are_the_owner_s_published_lessons_one_per_part():
    for part, directory in OWNER_EXAMPLES.items():
        lesson = HOME.example(part)
        assert lesson is not None
        assert lesson.page == f"lessons/{directory}/index.qmd"
        assert lesson.slot == COPY.examples[part]
    assert CURRICULUM.slot(COPY.examples["part-a"]).course
    assert CURRICULUM.slot(COPY.examples["part-b"]).path


def test_an_example_of_the_wrong_part_an_unknown_slot_or_an_unpublished_one_fails():
    planned = next(
        slot.label
        for slot in CURRICULUM.slots
        if slot.path and slot.label not in PUBLISHED
    )
    cases = {
        "a Part A slot for Part B": ("part-b", "M1", "no slot of a method path"),
        "a Part B slot for Part A": ("part-a", "SA5", "no slot of a course"),
        "an unknown slot": ("part-a", "Z99", "no slot of the curriculum"),
        "a planned slot": ("part-b", planned, "has no published lesson"),
    }
    for name, (part, label, message) in cases.items():
        data = _copy_data()
        data["curriculum"]["examples"][part] = label
        assert any(message in p for p in _home_problems(data)), name
    data = _copy_data()
    data["curriculum"]["examples"]["part-c"] = "M2"
    assert any("only part-a and part-b" in p for p in _home_problems(data))


def test_an_example_whose_lesson_is_not_published_fails_the_build():
    """Unpublishing the owner's lesson fails the copy file, rather than
    another lesson being chosen in its place."""
    published = PUBLISHED - {"SA5"}
    found = home_problems(COPY_DATA, CURRICULUM, published, TERMS)
    assert any("SA5, which has no published lesson" in p for p in found)


def test_without_examples_no_lesson_is_shown_and_none_is_chosen_by_code():
    data = _copy_data()
    del data["curriculum"]["examples"]
    home = replace(HOME, copy=HomeCopy.parse(data, CURRICULUM, PUBLISHED, TERMS))
    section = home.curriculum(SITE_SOURCE)
    assert "home-example" not in section
    assert home.example("part-a") is None and home.example("part-b") is None
    data = _copy_data()
    del data["curriculum"]["examples"]["part-b"]
    home = replace(HOME, copy=HomeCopy.parse(data, CURRICULUM, PUBLISHED, TERMS))
    assert home.curriculum(SITE_SOURCE).count("home-example") == 1


def test_each_example_has_its_preview_title_line_and_level():
    section = HOME.curriculum(SITE_SOURCE)
    entries = re.findall(
        r"::: \{\.home-example data-lesson-id=([\w-]+)\}\n(.*?)\n:::", section, re.S
    )
    chosen = [HOME.example("part-a"), HOME.example("part-b")]
    assert [lesson_id for lesson_id, _ in entries] == [x.id for x in chosen]
    for (_, block), lesson, letter in zip(entries, chosen, "AB", strict=True):
        assert f'src="previews/{lesson.id}.' in block
        assert f'width="{PREVIEW_WIDTH}" height="{PREVIEW_HEIGHT}"' in block
        assert 'alt="Preview, ' in block
        href = lesson.page.removesuffix(".qmd") + ".html"
        assert LINK.findall(block) == [href]
        assert f"#### [{lesson.title}]({href})" in block
        assert f"A lesson of Part {letter}: " in block
        assert re.search(r"level \d of 3", block)


# --- The page -----------------------------------------------------------------


def test_the_page_follows_identity_philosophy_curriculum_and_integrity_last():
    page = HOME.markdown(SITE_SOURCE)
    headings = re.findall(r"^## (.*?) \{#([\w-]+)\}", page, re.M)
    assert headings == [(COPY.headings[key], anchor) for key, anchor in SECTIONS]
    assert page.index('class="home-hero"') < page.index("## ")
    # Integrity is last: nothing after its links but the end of the page.
    assert page.rstrip().endswith(":::")
    assert "## Begin" not in page
    assert "From a question to a working model" not in page
    assert "lessons published" not in page


def test_identity_opens_with_the_canonical_sentence_and_its_one_link():
    identity = HOME.identity()
    paragraph = identity.split("\n\n")[1]
    assert paragraph.startswith(description())
    assert COPY.texts["identity"][0] in paragraph
    assert LINK.findall(identity) == ["about.html#creator-and-jidai"]


def test_integrity_links_the_account_of_the_evidence_and_the_source():
    integrity = HOME.integrity()
    for text in COPY.texts["integrity"]:
        assert text in integrity
    assert LINK.findall(integrity)[-2:] == ["verify.html", "https://example.org/repo"]
    assert "The source on GitHub" not in replace(HOME, repository="").integrity()


def test_what_you_can_learn_is_the_journey_s_text_as_on_the_atlas_and_about():
    section = HOME.curriculum(SITE_SOURCE)
    for key in ("part-a", "part-b", "relation"):
        for text in JOURNEY.sections[key]:
            assert _content().inline(text) in section, key
    order = [
        section.index("### Part A"),
        section.index("data-lesson-id=" + HOME.example("part-a").id),
        section.index("### Part B"),
        section.index("data-lesson-id=" + HOME.example("part-b").id),
        section.index("### From Part A to Part B"),
    ]
    assert order == sorted(order)
    # Home does not repeat the atlas's overview: no list of the courses.
    assert not re.search(r"^- ", section, re.M)
