"""The built home page (F124, after F25): the opening with its verified figure
and, in a disclosure, its provenance and the energy, the three activities with
published examples, Part A (three featured courses and a compact row) and
Part B ("Physics + AI") from the curriculum file and the lessons with links
into the atlas, the capstone projects from the map manifest with the featured
one on the dark ground beside its conceptual artwork, and the invitation.
Read without JavaScript."""

import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import COURSES, LearningPath, home_artwork
from pbc.authoring.atlas import CAPSTONE, AtlasManifest
from pbc.authoring.home import (
    ARTWORK_LABEL,
    CONSTRUCT_EXAMPLE,
    FEATURED_CAPSTONE,
    FEATURED_COURSES,
    FEATURED_HEADING,
    INVESTIGATE_EXAMPLE,
    OPENING_SOURCE,
    VERIFY_EXAMPLE,
)
from pbc.mechanics.experiments import home_opening

LESSONS = LearningPath.read(SITE_SOURCE)
MANIFEST = AtlasManifest.read(SITE_SOURCE, LESSONS.curriculum)
SECTIONS = ["about-the-site", "part-a", "part-b", "capstones", "begin"]


@pytest.fixture
def home(browser: Browser, server: SiteServer):
    context: BrowserContext = browser.new_context(
        viewport=DESKTOP, java_script_enabled=False
    )
    page = context.new_page()
    page.goto(server.url + "index.html", wait_until="load")
    yield page
    context.close()


def plain(text: str) -> str:
    # The build turns apostrophes into typographic ones.
    return text.replace("\u2019", "'")


def built(lesson_id: str, server: SiteServer) -> str:
    page = LESSONS.lesson(lesson_id).page.removesuffix(".qmd") + ".html"
    return server.url + page


def hrefs(locator) -> list[str]:
    return locator.evaluate_all("links => links.map(a => a.href)")


def test_the_page_has_the_opening_then_the_sections_in_order(home):
    assert home.locator("main h1").all_inner_texts() == [
        "Build a world. See if it obeys physics."
    ]
    ids = home.locator("main section.level2").evaluate_all(
        "sections => sections.map(s => s.id)"
    )
    assert ids == SECTIONS
    # The opening, with its figure, comes before the first section.
    assert home.locator("main .home-opening #fig-opening").count() == 1
    assert home.locator("main .home-opening ~ section#about-the-site").count() == 1
    assert home.locator("footer").count() == 1


def test_no_section_presents_a_teaching_formula(home):
    text = home.locator("main").inner_text()
    assert "From a question to a working model" not in text
    assert "One result, constructed and proved" not in text
    headings = home.locator("main h2, main h3").all_inner_texts()
    assert not [h for h in headings if h[:1].isdigit() or h.startswith("Step")]
    assert not [h for h in headings if h in ("Construct", "Investigate", "Verify")]
    assert home.locator("main ol").count() == 0


def test_the_opening_figure_is_the_verified_figure_with_its_provenance(
    home, server: SiteServer, tmp_path: Path
):
    # Byte for byte the files the module's command writes in a process of its
    # own, as the experiment checks of the lessons compare (ADR 016 decision
    # 4): no script computes the figures. In this test process the figures of
    # other tests leave Matplotlib in another state.
    subprocess.run(
        [sys.executable, "-m", home_opening.__name__, str(tmp_path)], check=True
    )
    for label in (home_opening.LABEL, home_opening.ENERGY_LABEL):
        figure = home.locator(f"main #{label}")
        image = figure.locator("img")
        assert image.count() == 1
        assert len(image.get_attribute("alt") or "") > 100
        assert int(image.get_attribute("width")) > 0
        assert int(image.get_attribute("height")) > 0
        status = figure.locator(".figure-status")
        assert status.get_attribute("data-status") == "simulated"
        served = home.request.get(image.evaluate("img => img.src")).body()
        assert served == (tmp_path / f"{label}.png").read_bytes()
    # The motion and its caption are in view; the provenance and the energy
    # are in a native disclosure below it, closed.
    assert home.locator("main .home-figure #fig-opening").count() == 1
    assert home.locator("main details #fig-opening").count() == 0
    assert home.locator("main #fig-opening figcaption").is_visible()
    details = home.locator("main .home-figure details.home-details")
    assert details.count() == 1
    assert details.get_attribute("open") is None
    assert details.locator("summary").inner_text() == "How this figure was computed"
    assert details.locator(f"#{home_opening.ENERGY_LABEL}").count() == 1
    note = details.locator(".home-provenance")
    links = hrefs(note.locator("a"))
    assert any(link.endswith("/" + OPENING_SOURCE) for link in links)
    assert any("/commit/" in link for link in links)
    assert built("double-pendulum-chaos", server) in links
    assert "pbc.mechanics.chaos" in note.text_content()
    # No control, timer, or anything else that looks interactive.
    opening = home.locator("main .home-opening")
    assert opening.locator("input, button, select, video, canvas").count() == 0


def test_the_opening_offers_the_atlas_and_the_first_lesson(home, server):
    first = LESSONS.in_course(LESSONS.courses[0])[0]
    actions = hrefs(home.locator("main .home-actions a"))
    assert actions == [
        server.url + "path/index.html#atlas",
        built(first.id, server),
    ]


def test_each_activity_links_one_published_example(home, server: SiteServer):
    section = home.locator("main section#about-the-site")
    links = hrefs(section.locator("a"))
    for lesson_id in (CONSTRUCT_EXAMPLE, INVESTIGATE_EXAMPLE, VERIFY_EXAMPLE):
        assert links.count(built(lesson_id, server)) == 1
        assert home.request.get(built(lesson_id, server)).ok
    text = section.inner_text()
    for word in ("construct", "investigate", "verify"):
        assert word in text


def _check_row(row, item, anchor: str, path_page: str) -> None:
    text = plain(row.inner_text())
    assert plain(item.title) in text
    published = LESSONS.in_course(item) if anchor == "course" else LESSONS.in_path(item)
    links = hrefs(row.locator("a"))
    if published:
        assert links[0] == f"{path_page}#{anchor}-{item.id}"
        count = len(published)
        assert f"{count} lesson{'' if count == 1 else 's'} published" in text
    else:
        assert links == []
        assert "planned" in text and "no lesson published" in text


def test_part_a_features_three_courses_and_lists_the_others(home, server: SiteServer):
    path_page = server.url + "path/index.html"
    section = home.locator("main section#part-a")
    featured = section.locator(".home-featured .home-course")
    assert featured.evaluate_all("rows => rows.map(r => r.dataset.course)") == list(
        FEATURED_COURSES
    )
    for row, course_id in zip(featured.all(), FEATURED_COURSES, strict=True):
        course = next(course for course in COURSES if course.id == course_id)
        _check_row(row, course, "course", path_page)
        assert row.locator("svg.home-illustration[aria-hidden='true']").count() == 1
        first = LESSONS.in_course(course)[0]
        assert hrefs(row.locator("a"))[1:] == [built(first.id, server)]
    rows = section.locator(".home-compact li")
    others = [course for course in COURSES if course.id not in FEATURED_COURSES]
    assert rows.count() == len(others) == 5
    for row, course in zip(rows.all(), others, strict=True):
        _check_row(row, course, "course", path_page)
        assert row.locator("svg.home-illustration").count() == 1


def test_part_b_is_physics_and_ai_with_the_four_method_paths(home, server: SiteServer):
    section = home.locator("main section#part-b")
    assert section.locator("h2").inner_text() == "Physics + AI"
    rows = section.locator(".home-paths li")
    assert rows.count() == len(LESSONS.paths) == 4
    for row, item in zip(rows.all(), LESSONS.paths, strict=True):
        assert plain(row.inner_text()).startswith(plain(item.title))
        _check_row(row, item, "path", server.url + "path/index.html")


def test_the_atlas_anchors_the_home_page_links_exist(home, browser, server):
    targets = {
        link.split("#", 1)[1]
        for link in hrefs(home.locator("main a"))
        if link.startswith(server.url + "path/index.html#")
    }
    assert "atlas" in targets
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + "path/index.html")
    for target in targets:
        assert page.locator(f"[id='{target}']").count() == 1, target
    context.close()


def test_the_capstones_are_planned_and_show_only_the_manifest_explanation(home):
    slots = [slot for slot in LESSONS.curriculum.slots if slot.kind == CAPSTONE]
    boxes = home.locator("main section#capstones .home-capstone")
    assert boxes.count() == len(slots) == 3
    order = [FEATURED_CAPSTONE] + [
        slot.label for slot in slots if slot.label != FEATURED_CAPSTONE
    ]
    assert boxes.evaluate_all("boxes => boxes.map(b => b.dataset.slot)") == order
    for box in boxes.all():
        label = box.get_attribute("data-slot")
        assert box.locator("a").count() == 0
        assert box.locator(".home-planned").inner_text() == "planned"
        descriptions = box.locator(".capstone-description").all_inner_texts()
        assert [plain(d) for d in descriptions] == [
            plain(MANIFEST.capstone(label).explanation)
        ]
        # The name line and the description; the featured one adds the
        # editorial heading and the artwork's label, nothing else.
        paragraphs = box.locator(".home-capstone-name, .capstone-description")
        assert paragraphs.count() == 2
        if label == FEATURED_CAPSTONE:
            assert box.locator("h3").all_inner_texts() == [FEATURED_HEADING]
            assert box.locator(".home-artwork-label").inner_text() == ARTWORK_LABEL
            assert len(box.locator("p").all_inner_texts()) == 4
        else:
            assert len(box.locator("p").all_inner_texts()) == 2
    assert "hypothetical" in home.locator("[data-slot='T11']").inner_text()


def test_the_featured_capstone_is_dark_with_its_generated_artwork(home):
    feature = home.locator("main .home-capstone-feature")
    background = feature.evaluate("box => getComputedStyle(box).backgroundColor")
    assert background == "rgb(15, 34, 64)"
    image = feature.locator(".home-artwork img")
    assert image.get_attribute("alt") == home_artwork.ALT
    assert image.get_attribute("width") == str(home_artwork.WIDTH)
    assert image.get_attribute("height") == str(home_artwork.HEIGHT)
    served = home.request.get(image.evaluate("img => img.src"))
    assert served.ok
    assert served.body().decode("utf-8") == home_artwork.wavefront()


def test_the_home_page_links_to_the_path_and_about_pages(home, server: SiteServer):
    links = hrefs(home.locator("main a"))
    assert server.url + "path/index.html#atlas" in links
    assert server.url + "about.html#creator-and-jidai" in links
