"""The generated home page (F134, F158; ADR 021 decision 4 as amended): the
hero's data file and its rules (one fixed headline and subtext, the variants
of F134 as an unused reference), the one hero image (Issue #482 one image;
Issue #487 the owner's double-pendulum illustration, keyed, lifted under
the copy, and faded in its files) with its registration, its lift and its
edges on the committed bytes, the hero's markup (one image in the
HTML, no script), the Home copy file and its rules (the owner's fixed copy
of Issue #481), the course subjects of Part A from the curriculum, the two
actions of the first step, and the order of the page, all generated from
data. Home shows no example lesson and does not repeat the canonical
attribution."""

import copy
import re
from dataclasses import replace

import numpy as np
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
    HERO_IMAGE_FALLBACK,
    HERO_IMAGE_HEIGHT,
    HERO_IMAGE_SIZES,
    HERO_IMAGE_WIDTH,
    HERO_IMAGE_WIDTHS,
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
# The owner's request on Issue #487 (2026-11-12): one image, the owner's
# illustration of a double pendulum, named with classical mechanics.
OWNER_IMAGE = ("double-pendulum", "mechanics")
# The master the owner supplied, matched by SHA-256 on 2026-11-12.
OWNER_MASTER = (
    "pbc_hero_assets/pbc-double-pendulum-hero-original.png",
    "ac9062c74fe15d4ef302170e6ced4311c1467fee73def9bde1be6758b98bfaaf",
)
PAPER = np.array([250, 248, 243], dtype=float)
# The part of the image under the copy of a wide screen (the left 47 %),
# the plateau that is whole (60 to 86 % across), and the floor the lift
# gives the luma of every composited pixel under the copy, less the few
# levels the lossy colour dips (tools/illustrations/derive_assets.py).
_LIFTED = 0.47
_PLATEAU = (0.60, 0.86)
_FLOOR = 220


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
    for where in ("top", "variant headline", "variant subtext", "image"):
        data = _data()
        target = {
            "top": data,
            "variant headline": data["variants"][0],
            "variant subtext": data["variants"][0]["subtexts"][0],
            "image": data["image"],
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


# --- The hero's data file: the image ----------------------------------------


def test_the_data_file_holds_the_owner_s_one_double_pendulum_image():
    assert (HERO.image.id, HERO.image.sequence) == OWNER_IMAGE
    assert HERO.image.files == tuple(
        f"assets/hero/double-pendulum-{width}.webp" for width in HERO_IMAGE_WIDTHS
    )
    # Its alternative text names what is seen (the pendulum, the trace with
    # its curve, the ball in the well) and claims no measurement or result:
    # the image is an illustration, not a result of the project.
    assert HERO.image.alt.startswith("Illustration: ")
    for seen in ("double pendulum", "trace", "curve", "well"):
        assert seen in HERO.image.alt
    assert not re.search(
        r"\b(verified|result|measured|measurement|simulat\w*|data)\b", HERO.image.alt
    )


def _rgba(width: int) -> np.ndarray:
    with Image.open(SITE_SOURCE / HERO.image.file(width)) as opened:
        assert opened.format == "WEBP"
        return np.asarray(opened.convert("RGBA")).astype(float)


def _composite(rgba: np.ndarray) -> np.ndarray:
    """The pixels as the browser draws them over the paper."""
    return np.round(PAPER + rgba[..., 3:] / 255 * (rgba[..., :3] - PAPER))


def _luma(pixels: np.ndarray) -> np.ndarray:
    return 0.2126 * pixels[..., 0] + 0.7152 * pixels[..., 1] + 0.0722 * pixels[..., 2]


def _luminance(pixels: np.ndarray) -> np.ndarray:
    """The relative luminance (WCAG 2.1) of each pixel."""
    value = pixels / 255
    linear = np.where(value <= 0.03928, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[..., 0] + 0.7152 * linear[..., 1] + 0.0722 * linear[..., 2]


@pytest.mark.parametrize("width", HERO_IMAGE_WIDTHS)
def test_each_width_has_its_file_at_2_to_1_and_the_register_entry_of_its_master(
    width: int,
):
    """Each width's own test: a WebP file with an alpha channel under
    site/assets/hero, 2:1, and a complete register entry naming the owner's
    master and its hash, the owner as the author with the date and the
    licence, and how the file was derived; no script (the master is not
    computed by one) and no model (the owner's decision on Issue #487: a
    neutral origin), so the entry claims nothing about how it was made."""
    file = HERO.image.file(width)
    rgba = _rgba(width)
    assert rgba.shape == (width // 2, width, 4)
    entry = REGISTER[file.removeprefix("assets/")]
    assert (entry["master"], entry["sha256"]) == OWNER_MASTER
    assert entry["author"] == "Ahmet Taspinar"
    assert entry["licence"] and entry["date"]
    assert "script" not in entry and "model" not in entry
    assert "derive_assets.py --hero" in entry["source"]
    assert "illustration" in entry["source"] and "not a result" in entry["source"]


@pytest.mark.parametrize("width", HERO_IMAGE_WIDTHS)
def test_every_edge_is_transparent_and_the_right_part_is_whole(width: int):
    """No rectangular boundary (every edge pixel fully transparent) and the
    right part whole: on the plateau every inked pixel is opaque and the
    ink is the master's (the ball in the well is near black)."""
    rgba = _rgba(width)
    alpha = rgba[..., 3]
    height = alpha.shape[0]
    for edge in (alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]):
        assert edge.max() == 0
    plateau = rgba[
        round(0.20 * height) : round(0.80 * height),
        round(_PLATEAU[0] * width) : round(_PLATEAU[1] * width),
    ]
    inked = _luma(plateau[..., :3]) < 200
    assert inked.any()
    assert plateau[..., 3][inked].min() == 255
    assert _luminance(_composite(plateau)).min() < 0.05


@pytest.mark.parametrize("width", HERO_IMAGE_WIDTHS)
def test_under_the_copy_every_pixel_is_lifted_to_the_floor_but_not_wiped(
    width: int,
):
    """The owner's requirements on the committed bytes (Issue #487): under
    the copy of a wide screen (the left 47 % of the image) every pixel,
    composited on the paper, keeps the luma floor that gives the muted
    subtext and the link colour a WCAG contrast above 4.5 (the headline
    above 3), while the pendulum stays a recognisable pale drawing: its
    darkest ink is well below the paper, and its pale haze keeps most of
    its ink (a light pixel is lifted far less than a dark one)."""
    rgba = _rgba(width)
    height = rgba.shape[0]
    left = _composite(rgba[:, : round(_LIFTED * width)])
    luma = _luma(left)
    assert luma.min() >= _FLOOR
    for colour, least in (("#57606a", 4.5), ("#0047ab", 4.5)):
        text = _luminance(np.array([int(colour[i : i + 2], 16) for i in (1, 3, 5)]))
        assert (_luminance(left).min() + 0.05) / (text + 0.05) >= least, colour
    # The pendulum (ink at 11 to 35 % across, 25 to 65 % down in the master)
    # is still drawn: its darkest hundredth is at least 16 levels below the
    # paper's luma, and at least a fifth of its area is visibly inked.
    pendulum = luma[
        round(0.25 * height) : round(0.65 * height),
        round(0.11 * width) : round(0.35 * width),
    ]
    paper = float(_luma(PAPER))
    assert np.percentile(pendulum, 1) <= paper - 16
    assert (pendulum < paper - 6).mean() >= 0.2


@pytest.mark.parametrize("width", HERO_IMAGE_WIDTHS)
def test_the_lift_is_gradual_and_the_pendulum_stands_left_the_well_right(
    width: int,
):
    """The fade from the lifted part to the plateau is gradual: along the
    transition (47 to 60 % across) the darkest ink of each 2 % column band
    deepens from the floor to the master's ink in steps of a fraction of
    the way, never in one step and never back up by more than the few
    levels the content and the lossy colour move; no wipe and no step. And
    the composition is the master's: the darkest
    ink under the copy stands in the left third (the pendulum), the darkest
    ink of all in the right third (the ball in the well)."""
    composite = _composite(_rgba(width))
    luma = _luma(composite)
    height = luma.shape[0]
    band = luma[round(0.20 * height) : round(0.80 * height)]
    darkest = [
        band[:, round(start * width) : round((start + 0.02) * width)].min()
        for start in np.arange(_LIFTED, _PLATEAU[0], 0.02)
    ]
    steps = np.diff(darkest)
    assert (steps <= 16).all() and (steps >= -60).all(), darkest
    assert darkest[0] >= 200 and darkest[-1] < 100, darkest
    luminance = _luminance(composite)
    rows, columns = np.where(luminance < 0.80)
    left = columns < round(_LIFTED * width)
    assert 0.15 < columns[left].mean() / width < 0.35
    rows, columns = np.where(luminance < 0.05)
    assert 0.70 < columns.mean() / width < 0.90
    assert 0.45 < rows.mean() / height < 0.70


def test_an_image_rule_broken_fails():
    cases = {
        "id": ("id", "Double_Pendulum", "lower-case words joined by hyphens"),
        "sequence": ("sequence", "law-discovery", "no course of Part A"),
        "alt": ("alt", "An <em>image</em>", "holds markup"),
        "empty alt": ("alt", " ", "has no text"),
    }
    for name, (field, value, message) in cases.items():
        data = _data()
        data["image"][field] = value
        assert any(message in p for p in hero_problems(data)), name


def test_a_missing_or_malformed_image_fails():
    data = _data()
    del data["image"]["sequence"]
    assert any("the image lacks sequence" in p for p in hero_problems(data))
    data = _data()
    data["image"]["default"] = "double-pendulum"
    assert any("unknown fields: default" in p for p in hero_problems(data))
    data = _data()
    data["image"] = ["double-pendulum"]
    assert "the image is not a mapping" in hero_problems(data)
    data = _data()
    del data["image"]
    assert any("lacks image" in p for p in hero_problems(data))
    data = _data()
    data["images"] = data.pop("image")
    found = hero_problems(data)
    assert any("unknown fields: images" in p for p in found)
    assert any("lacks image" in p for p in found)


def test_an_image_without_a_file_or_a_register_entry_fails(tmp_path):
    (tmp_path / "assets" / "hero").mkdir(parents=True)
    (tmp_path / "assets" / "provenance.yaml").write_text(
        "assets:\n  hero/double-pendulum-1200.webp: {}\n", encoding="utf-8"
    )
    (tmp_path / "assets" / "hero" / "double-pendulum-1480.webp").write_bytes(b"")
    found = image_file_problems(HERO, tmp_path)
    assert (
        "the hero image double-pendulum has no file"
        " assets/hero/double-pendulum-1200.webp" in found
    )
    assert (
        "the hero file assets/hero/double-pendulum-1480.webp is not in the"
        " provenance register" in found
    )
    assert image_file_problems(HERO, SITE_SOURCE) == []


# --- The hero's markup -------------------------------------------------------


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


def test_the_one_image_is_in_the_html_with_its_widths_and_no_script():
    """The image is the HTML's (Issue #482): one <img> with the file of
    each width in its srcset and the sizes the CSS draws it at, the middle
    width as the src of a browser without srcset, its intrinsic size for
    the reserved box, the priority hint of the largest element of the
    page, and the alternative text of the data file; no script, no
    <noscript>, no embedded data, no parameter."""
    hero = HOME.hero()
    (image,) = re.findall(r"<img [^>]*>", hero)
    attributes = dict(re.findall(r'([\w-]+)="([^"]*)"', image))
    assert attributes["src"] == HERO.image.file(HERO_IMAGE_FALLBACK)
    assert attributes["srcset"] == ", ".join(
        f"{HERO.image.file(width)} {width}w" for width in HERO_IMAGE_WIDTHS
    )
    assert attributes["sizes"] == HERO_IMAGE_SIZES
    assert attributes["alt"] == HERO.image.alt.replace("'", APOSTROPHE)
    assert (attributes["width"], attributes["height"]) == (
        str(HERO_IMAGE_WIDTH),
        str(HERO_IMAGE_HEIGHT),
    )
    assert attributes["fetchpriority"] == "high"
    assert attributes["decoding"] == "async"
    assert "loading" not in attributes
    assert "<script" not in hero and "<noscript" not in hero
    assert "hero-images" not in hero and "data-hero-image" not in hero
    # No constellation, no inline SVG, no link inside the image.
    assert "<svg" not in hero and "hero-node" not in hero
    assert "<a " not in hero.split('class="hero-figure"')[1].split("</div>")[0]


def test_the_figure_follows_the_copy_and_the_actions():
    """The order of the source is the reading order below the desktop
    width: the copy, the two actions, then the image."""
    hero = HOME.hero()
    order = [
        hero.index('class="hero-copy"'),
        hero.index('class="home-actions"'),
        hero.index('id="hero-figure"'),
    ]
    assert order == sorted(order)


def test_the_alt_text_is_escaped_in_the_html():
    data = _data()
    data["image"]["alt"] = 'Illustration: plain & "simple".'
    home = replace(HOME, hero_copy=HeroCopy.parse(data))
    (image,) = re.findall(r"<img [^>]*>", home.hero())
    assert 'alt="Illustration: plain &amp; &quot;simple&quot;."' in image


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
