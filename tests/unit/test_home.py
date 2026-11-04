"""The generated home page (F134, ADR 021 decision 4): the hero's data file and
its rules, the hero's markup and image, the examples chosen by code, and the
links, all generated from data."""

import copy
import json
import re
from dataclasses import replace

import pytest
import yaml
from support.paths import SITE_SOURCE

from pbc.authoring import COURSES, LearningPath
from pbc.authoring.atlas import AtlasManifest
from pbc.authoring.home import (
    HERO_FILE,
    HERO_PAIRS,
    NODE_HEIGHT,
    NODE_WIDTH,
    PHONE_COURSE_NODES,
    PHONE_HEIGHT,
    PHONE_PATH_NODES,
    PHONE_SCALE,
    WIDTH,
    HeroCopy,
    HomeContent,
    hero_problems,
)
from pbc.authoring.identity import description
from pbc.authoring.previews import HEIGHT as PREVIEW_HEIGHT
from pbc.authoring.previews import WIDTH as PREVIEW_WIDTH

PATH = LearningPath.read(SITE_SOURCE)
MANIFEST = AtlasManifest.read(SITE_SOURCE, PATH.curriculum)
DATA = yaml.safe_load((SITE_SOURCE / HERO_FILE).read_text(encoding="utf-8"))
HERO = HeroCopy.parse(DATA)
HOME = HomeContent(PATH, MANIFEST, HERO, "https://example.org/repo")
APOSTROPHE = chr(0x2019)  # as the build sets an apostrophe
LINK = re.compile(r"\]\(([^)]*)\)")
HREF = re.compile(r'\bhref="([^"]*)"')


def _data():
    return copy.deepcopy(DATA)


# --- The hero's data file ----------------------------------------------------


def test_the_data_file_holds_exactly_the_eight_pairs_of_the_owner():
    assert hero_problems(DATA) == []
    assert [pair.id for pair in HERO.pairs] == list(HERO_PAIRS)
    assert HERO.default in HERO_PAIRS
    # The owner's copy, as supplied on the Issue (two of the eight).
    assert HERO.pair("1a").headline == (
        "The universe has no obligation to fit the limits of human intelligence."
    )
    assert HERO.pair("3b").subtext.startswith(
        "We do not know what physics will look like in a hundred years."
    )
    # Pairs of one headline share it.
    assert HERO.pair("2a").headline == HERO.pair("2c").headline


def test_a_missing_pair_fails():
    data = _data()
    data["headlines"][2]["subtexts"].pop()
    assert any("3b" in p and "missing" in p for p in hero_problems(data))


def test_a_duplicate_pair_fails():
    data = _data()
    data["headlines"][0]["subtexts"].append(dict(data["headlines"][0]["subtexts"][0]))
    assert any("1a appears more than once" in p for p in hero_problems(data))


def test_a_duplicate_headline_fails():
    data = _data()
    data["headlines"][1]["id"] = "1"
    found = hero_problems(data)
    assert any("headline id '1' appears more than once" in p for p in found)


def test_an_extra_pair_fails():
    data = _data()
    data["headlines"][2]["subtexts"].append({"id": "c", "text": "One more."})
    assert any("3c" in p and "not the owner's eight" in p for p in hero_problems(data))


def test_an_unknown_field_fails_at_every_level():
    for where in ("top", "headline", "subtext"):
        data = _data()
        target = {
            "top": data,
            "headline": data["headlines"][0],
            "subtext": data["headlines"][0]["subtexts"][0],
        }[where]
        target["weight"] = 2
        assert any("unknown fields: weight" in p for p in hero_problems(data)), where


def test_markup_or_empty_text_fails():
    data = _data()
    data["headlines"][0]["subtexts"][1]["text"] = "Physics <b>and</b> AI."
    data["headlines"][1]["text"] = " "
    found = hero_problems(data)
    assert any("subtext 1b holds markup" in p for p in found)
    assert any("headline 2 has no text" in p for p in found)


def test_a_default_that_is_no_pair_fails():
    data = _data()
    data["default"] = "4a"
    assert any("default '4a'" in p for p in hero_problems(data))
    with pytest.raises(ValueError, match="rules of the hero"):
        HeroCopy.parse(data)


def test_a_site_without_the_data_file_fails(tmp_path):
    with pytest.raises(ValueError):
        HeroCopy.read(tmp_path)


# --- The hero's markup -------------------------------------------------------


def _pairs(hero: str) -> list[dict]:
    (found,) = re.findall(
        r'<script type="application/json" id="hero-pairs">(.*?)</script>', hero
    )
    return json.loads(found)


def test_the_hero_carries_one_h1_with_the_default_pair_and_the_pairs_as_data():
    hero = HOME.hero()
    default = HERO.pair(HERO.default)
    assert hero.count("<h1") == 1
    (h1,) = re.findall(r"<h1[^>]*>(.*?)</h1>", hero)
    assert h1 == default.headline.replace("'", APOSTROPHE)
    assert f'data-hero="{HERO.default}"' in hero
    assert default.subtext.replace("'", APOSTROPHE) in hero
    pairs = _pairs(hero)
    assert [pair["id"] for pair in pairs] == list(HERO_PAIRS)
    for pair in pairs:
        expected = HERO.pair(pair["id"])
        assert pair["headline"] == expected.headline.replace("'", APOSTROPHE)
        assert pair["subtext"] == expected.subtext.replace("'", APOSTROPHE)
    # Every other pair is only data: no other subtext is text of the page.
    text = re.sub(r"<script.*?</script>", "", hero, flags=re.S)
    for pair in HERO.pairs:
        if pair.subtext != default.subtext:
            assert pair.subtext.replace("'", APOSTROPHE) not in text
    # The script from the site's origin, right after the copy.
    assert '<script src="learner/hero.js"></script>' in hero
    assert hero.index('class="hero-copy"') < hero.index("learner/hero.js")


def test_the_embedded_pairs_cannot_close_their_script_element():
    data = _data()
    data["headlines"][0]["subtexts"][0]["text"] = "Plain text & more."
    home = HomeContent(PATH, MANIFEST, HeroCopy.parse(data))
    hero = home.hero()
    assert "\\u0026" in hero
    assert _pairs(hero)[0]["subtext"] == "Plain text & more."


def test_the_hero_holds_no_copy_but_the_data_file_s():
    source = (SITE_SOURCE / "index.qmd").read_text(encoding="utf-8")
    for pair in HERO.pairs:
        assert pair.headline not in source and pair.subtext not in source
    # The page writes no link and no heading of its own.
    assert not LINK.search(source)
    markdown = re.sub(r"```\{python\}.*?```", "", source, flags=re.S)
    assert not re.search(r"^#+ ", markdown, re.M)


# --- The hero image ----------------------------------------------------------


def test_the_image_is_two_constellations_of_registered_parts_with_text_labels():
    image = HOME.hero_image()
    registered = yaml.safe_load(
        (SITE_SOURCE / "assets" / "provenance.yaml").read_text(encoding="utf-8")
    )["assets"]
    nodes = re.findall(
        r'<g class="hero-node hero-node-(a|b)" data-sequence="([\w-]+)"', image
    )
    assert [part for part, _ in nodes] == ["a"] * len(COURSES) + ["b"] * len(PATH.paths)
    assert [sequence for _, sequence in nodes] == [
        *(course.id for course in COURSES),
        *(item.id for item in PATH.paths),
    ]
    sources = re.findall(r'<image href="([^"]+)"', image)
    assert len(sources) == len(nodes) == 12
    for source in sources:
        assert source.startswith("assets/atlas/")
        assert source.removeprefix("assets/") in registered, source
    # Every label is SVG text from the curriculum; there is no link.
    labels = [
        " ".join(re.findall(r"<tspan[^>]*>(.*?)</tspan>", text))
        for text in re.findall(r'<text class="hero-label".*?</text>', image)
    ]
    assert labels == [course.title for course in COURSES] + [
        item.title for item in PATH.paths
    ]
    assert "<a " not in image and 'href="http' not in image
    assert 'role="img"' in image
    title = re.search(r"<title[^>]*>(.*?)</title>", image).group(1)
    assert "imply no order of study" in title
    for item in [*COURSES, *PATH.paths]:
        assert item.title in title


# --- What the site is, the examples, the invitation --------------------------


def test_what_the_site_is_is_three_sentences_with_the_canonical_one_first():
    text, links = HOME.about().split("\n\n")
    assert text.startswith(description())
    assert len(re.findall(r"[.!?](?:\s|$)", text)) == 3
    assert LINK.findall(links) == [
        "about.html#creator-and-jidai",
        "verify.html",
        "https://example.org/repo",
    ]


def test_the_examples_are_three_kinds_from_three_courses_none_the_first():
    examples = HOME.examples()
    assert len(examples) == 3
    simulation, measured, agent = examples
    assert simulation.methods == ("simulation",) and simulation.difficulty == 1
    assert "measured-data" in measured.methods
    assert "llm-agents" in agent.methods
    courses = [lesson.course for lesson in examples]
    assert len(set(courses)) == 3
    assert PATH.courses[0].id not in courses
    # Each is the first of its kind in path order among the courses left.
    order = [lesson.id for lesson in PATH.lessons]
    for lesson in examples:
        assert lesson.id in order


def test_the_choice_follows_the_front_matter():
    # Without the wave flume lab, the next measured-data lesson outside the
    # courses already chosen is taken, or none.
    lessons = tuple(x for x in PATH.lessons if x.id != HOME.examples()[1].id)
    home = replace(HOME, path=replace(PATH, lessons=lessons))
    measured = [x for x in home.examples() if "measured-data" in x.methods]
    for lesson in measured:
        assert lesson.id != HOME.examples()[1].id
        assert lesson.course != PATH.courses[0].id


def test_the_capstone_is_a_published_one_of_a_course_no_example_has():
    capstone = HOME.capstone()
    assert capstone is not None
    slot = next(s for s in PATH.curriculum.slots if s.label == capstone.slot)
    assert slot.is_capstone
    assert capstone.course not in {lesson.course for lesson in HOME.examples()}
    # With no published capstone there is none.
    capstones = {s.label for s in PATH.curriculum.slots if s.is_capstone}
    lessons = tuple(x for x in PATH.lessons if x.slot not in capstones)
    assert replace(HOME, path=replace(PATH, lessons=lessons)).capstone() is None


def test_the_capstone_is_never_one_of_the_examples():
    """When every published capstone's course is used, the fallback skips a
    capstone that is itself an example, and there is none when no other is
    left (S1 of review 02)."""
    em9 = next(x for x in PATH.lessons if x.slot == "EM9")
    measured = replace(em9, methods=(*em9.methods, "measured-data"))
    lessons = tuple(
        measured if x is em9 else x
        for x in PATH.lessons
        if x.slot != "W8"  # EM9 becomes the measured-data example
    )
    home = replace(HOME, path=replace(PATH, lessons=lessons))
    assert measured.id in {x.id for x in home.examples()}
    used = {x.course for x in home.examples()}
    published = [x for x in lessons if x.slot in {"T11", "EM9"}]
    assert all(x.course in used for x in published)
    # The other published capstone is chosen, never EM9 a second time.
    assert home.capstone().slot == "T11"
    # With EM9 the only published capstone, there is none.
    alone = tuple(x for x in lessons if x.slot != "T11")
    assert replace(HOME, path=replace(PATH, lessons=alone)).capstone() is None


def test_a_published_product_capstone_is_chosen_like_a_course_capstone():
    """A method path's product capstone is a capstone of the choice (ADR 022
    decision 3): published, it is chosen when no course capstone is left,
    with its path named; planned, it is never chosen."""
    capstones = {s.label for s in PATH.curriculum.slots if s.is_capstone}
    without = tuple(x for x in PATH.lessons if x.slot not in capstones)
    # No product capstone is published yet: none is chosen.
    assert replace(HOME, path=replace(PATH, lessons=without)).capstone() is None
    lab = replace(next(x for x in without if x.id == "agent-experiment"), slot="SA9")
    lessons = tuple(lab if x.id == lab.id else x for x in without)
    home = replace(HOME, path=replace(PATH, lessons=lessons))
    assert home.capstone() == lab
    section = home.examples_section(SITE_SOURCE)
    assert MANIFEST.capstone("SA9").explanation in section
    assert (
        "the capstone project of the path Reliable scientific agents and"
        " experiment automation" in section
    )


def test_every_label_of_the_hero_stays_inside_the_image():
    """A label has at most two lines, and every line, centred on its node,
    stays within the WIDTH of the image: at 13 px a character of the label
    is about 6.2 units wide (measured in Chromium), taken here as 6.5. The
    longer path titles wrap into longer lines than the courses'."""
    image = HOME.hero_image()
    labels = re.findall(r'<text class="hero-label" x="(\d+)"[^>]*>(.*?)</text>', image)
    assert len(labels) == len(COURSES) + len(PATH.paths)
    for x, text in labels:
        lines = re.findall(r"<tspan[^>]*>(.*?)</tspan>", text)
        assert 1 <= len(lines) <= 2
        for line in lines:
            half = len(line) * 6.5 / 2
            assert half <= int(x) <= WIDTH - half, line


def test_on_a_phone_the_nodes_stand_in_two_columns_inside_the_taller_box():
    """Below 40em the style sheet applies each node's phone transform and the
    phone lines; the nodes, scaled, stay inside WIDTH by PHONE_HEIGHT units,
    and the two columns are far enough apart for labels of about 13 CSS px."""
    image = HOME.hero_image()
    assert f'style="--hero-phone-ratio: {WIDTH} / {PHONE_HEIGHT}"' in image
    assert 'preserveAspectRatio="xMidYMin meet"' in image
    transforms = re.findall(
        r'<g class="hero-node[^"]*"[^>]*--hero-phone: ([^"]+)"', image
    )
    phone = PHONE_COURSE_NODES + PHONE_PATH_NODES
    assert len(transforms) == len(phone) == 12
    for transform, (x, y) in zip(transforms, phone, strict=True):
        assert transform.startswith(f"translate({x}px, {y}px) scale({PHONE_SCALE})")
        half_width = NODE_WIDTH * PHONE_SCALE / 2
        half_height = NODE_HEIGHT * PHONE_SCALE / 2
        assert half_width <= x <= WIDTH - half_width
        assert half_height <= y <= PHONE_HEIGHT - half_height
    assert sorted({x for x, _ in phone}) == [170, 470]
    lines = re.findall(r'<path class="([^"]*)" d="([^"]*)"/>', image)
    assert [c for c, _ in lines if "hero-phone" in c] == [
        "hero-bridge hero-phone",
        "hero-line hero-line-a hero-phone",
        "hero-line hero-line-b hero-phone",
    ]
    assert len([c for c, _ in lines if "hero-wide" in c]) == 3


def test_each_entry_has_its_preview_title_line_and_level():
    section = HOME.examples_section(SITE_SOURCE)
    entries = re.findall(
        r"::: \{\.home-example data-lesson-id=([\w-]+)\}\n(.*?)\n:::", section, re.S
    )
    chosen = [*HOME.examples(), HOME.capstone()]
    assert [lesson_id for lesson_id, _ in entries] == [x.id for x in chosen]
    for (_, block), lesson in zip(entries, chosen, strict=True):
        assert f'src="previews/{lesson.id}.' in block
        assert f'width="{PREVIEW_WIDTH}" height="{PREVIEW_HEIGHT}"' in block
        assert 'alt="Preview, ' in block
        href = lesson.page.removesuffix(".qmd") + ".html"
        assert LINK.findall(block) == [href]
        assert f"### [{lesson.title}]({href})" in block
        assert re.search(r"level \d of 3", block)
    capstone = HOME.capstone()
    assert MANIFEST.capstone(capstone.slot).explanation in entries[-1][1]
    assert "the capstone project of" in entries[-1][1]


def test_the_invitation_is_the_start_link_and_the_atlas_and_nothing_else():
    first = PATH.in_course(PATH.courses[0])[0]
    assert LINK.findall(HOME.begin()) == [
        first.page.removesuffix(".qmd") + ".html",
        "path/index.html#atlas",
    ]
    hero_links = HREF.findall(HOME.hero().split("<svg")[0])
    assert hero_links == [
        first.page.removesuffix(".qmd") + ".html",
        "path/index.html#atlas",
    ]


def test_the_page_tells_one_story_without_the_rejected_section():
    page = HOME.markdown(SITE_SOURCE)
    headings = re.findall(r"^## (.*?) \{", page, re.M)
    assert headings == ["What this site is", "What you can learn", "Begin"]
    assert "From a question to a working model" not in page
    # The atlas's overview of the courses is not repeated: no count of
    # lessons, and no list of the courses outside the image.
    assert "lessons published" not in page
    outside_image = re.sub(r"<svg.*?</svg>", "", page, flags=re.S)
    named = [c.title for c in COURSES if c.title in outside_image]
    assert len(named) <= 4  # the examples' and the capstone's courses
