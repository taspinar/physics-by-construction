"""Required checks on the course atlas of the built path page (ADR 018
decision 3, F125): the map, its panels, and its textual equivalent come from
the curriculum file, the front matter, and the map manifest, and a reader
reaches every published lesson through them without JavaScript.

What the module derives (counts, edges, states) is covered by
tests/unit/test_atlas.py; here the built page is compared with it.
"""

from pathlib import Path
from urllib.parse import urldefrag, urljoin

import pytest
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, PHONE
from support.site_server import SiteServer

from pbc.authoring.atlas import Atlas, AtlasSection
from pbc.authoring.path import PATH_PAGE, Lesson
from pbc.authoring.progress import EXPLANATION_ANCHOR

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
ATLAS = Atlas.read(SITE_SOURCE)
LESSONS = ATLAS.path.lessons


def built(lesson: Lesson) -> str:
    return Path(lesson.page).with_suffix(".html").as_posix()


@pytest.fixture
def without_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


@pytest.fixture
def page(without_scripts: BrowserContext, server: SiteServer) -> Page:
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")
    return page


def _targets(page: Page, selector: str, server: SiteServer) -> set[str]:
    hrefs = page.locator(selector).evaluate_all(
        "links => links.map(a => a.getAttribute('href'))"
    )
    return {urldefrag(urljoin(server.url + PATH, href)).url for href in hrefs}


def test_every_lesson_is_reached_through_the_map_and_its_panels(
    page: Page, server: SiteServer
):
    lessons = {server.url + built(lesson) for lesson in LESSONS}
    # The view layer of the drawing links every lesson, the lessons without a
    # slot included.
    assert _targets(page, "#atlas-map .atlas-views a", server) == lessons
    without_slot = {server.url + built(item) for item in LESSONS if not item.slot}
    assert without_slot and without_slot <= _targets(
        page, "#atlas-map .atlas-views a", server
    )
    # A concept node leads to its panel, and the panels link every lesson
    # that fills a slot of a concept.
    nodes = page.locator("#atlas-map .atlas-nodes a")
    assert nodes.count() == len(ATLAS.concepts)
    for href in nodes.evaluate_all("links => links.map(a => a.getAttribute('href'))"):
        assert href.startswith("#concept-")
        assert page.locator(f"details{href}.concept-panel").count() == 1
    in_concepts = {
        server.url + built(lesson)
        for item in ATLAS.concepts
        for lesson in ATLAS.lessons_of(item)
    }
    assert in_concepts <= _targets(page, ".atlas-concepts a", server)


def test_every_lesson_is_still_reached_through_the_index(
    page: Page, server: SiteServer
):
    lessons = {server.url + built(lesson) for lesson in LESSONS}
    assert lessons <= _targets(page, "main section#courses a", server)


def test_a_concept_opens_its_panel_with_its_lessons_by_keyboard(
    page: Page, server: SiteServer
):
    concept = next(item for item in ATLAS.concepts if ATLAS.lessons_of(item))
    node = page.locator(f'#atlas-map a[data-concept="{concept.id}"]')
    node.focus()
    page.keyboard.press("Enter")
    assert page.evaluate("location.hash") == f"#concept-{concept.id}"
    panel = page.locator(f"details#concept-{concept.id}")
    panel.locator("> summary").focus()
    page.keyboard.press("Enter")
    lesson = ATLAS.lessons_of(concept)[0]
    link = panel.locator(f'a[href$="{Path(built(lesson)).name}"]').first
    assert link.is_visible()
    assert concept.explanation in " ".join(panel.inner_text().split())


def test_the_switch_and_the_breadcrumb_are_links_that_resolve(page: Page):
    for href in page.locator(".atlas-switch a").evaluate_all(
        "links => links.map(a => a.getAttribute('href'))"
    ):
        assert page.locator(href).count() == 1
    crumbs = page.locator("nav.pbc-breadcrumb li")
    assert crumbs.first.locator("a").get_attribute("href") == "../index.html"
    assert crumbs.last.locator("[aria-current=page]").count() == 1


# The anchors of the path page before the atlas (F26, F62 to F64): each still
# names one element.
PREVIOUS_ANCHORS = [
    "choose",
    "courses",
    "paths",
    "methods",
    "difficulty",
    "order",
    "graph",
    "dependency-map",
    EXPLANATION_ANCHOR,
    *(f"course-{course.id}" for course in ATLAS.path.courses),
    *(f"course-{course.id}-lessons" for course in ATLAS.path.courses),
    *(f"path-{path.id}" for path in ATLAS.path.paths),
    *(f"method-{method.id}" for method in ATLAS.path.methods),
]


def test_every_previous_anchor_and_graph_node_still_resolves(
    page: Page, server: SiteServer
):
    for anchor in PREVIOUS_ANCHORS:
        assert page.locator(f"[id='{anchor}']").count() == 1, anchor
    nodes = _targets(page, "#dependency-map .prerequisite-graph a", server)
    assert nodes == {server.url + built(lesson) for lesson in LESSONS}


def test_planned_concepts_are_labelled_and_never_link_a_lesson(page: Page):
    planned = page.locator('#atlas-map a[data-concept-state="planned"]')
    assert planned.count() == sum(
        1 for item in ATLAS.concepts if ATLAS.state(item) == "planned"
    )
    for node in planned.all():
        assert node.get_attribute("href").startswith("#concept-")
        assert "planned" in node.get_attribute("aria-label")
    slots = page.locator('.atlas-concepts li[data-slot-state="planned"]')
    assert slots.locator("a").count() == 0


def test_the_capstones_carry_their_state_and_the_manifests_description(page: Page):
    items = page.locator(".atlas-capstone-item")
    assert items.count() == 3
    published = {lesson.slot for lesson in LESSONS if lesson.slot}
    for item in items.all():
        label = item.get_attribute("data-slot")
        description = item.locator(".capstone-description").inner_text()
        assert description == ATLAS.manifest.capstone(label).explanation
        if label in published:
            assert "Published." in item.inner_text()
            assert item.locator(".atlas-capstone-name a").count() == 1
        else:
            assert "Planned, not published." in item.inner_text()
            assert item.locator(".atlas-capstone-name a").count() == 0
    # EM9 is published (F80): it is no planned slot in the index of its course
    # (in a closed disclosure, so read by its text, not as rendered); T11
    # stays planned in its own.
    assert "EM9" in published
    em = page.locator("main section#course-electromagnetism li.planned-slot")
    assert "EM9" not in em.locator(".slot-label").all_text_contents()
    thermo = page.locator("main section#course-thermodynamics li.planned-slot")
    assert "T11" in thermo.locator(".slot-label").all_text_contents()


def test_the_textual_equivalent_is_in_the_page(page: Page):
    text = page.locator("section.visually-hidden ol.atlas-text > li")
    assert text.count() == len(AtlasSection(ATLAS).sentences())
    assert not text.first.is_visible() or text.first.bounding_box()["width"] <= 1
    legend = page.locator(".atlas-legend").inner_text()
    for words in ("Prerequisite", "Conceptual connection", "Capstone membership"):
        assert words in legend


def test_the_map_nodes_take_the_keyboard_in_map_order_with_visible_focus(
    page: Page,
):
    nodes = page.locator("#atlas-map .atlas-nodes a")
    nodes.first.focus()
    page.keyboard.press("Shift+Tab")
    page.keyboard.press("Tab")
    seen = []
    for _ in ATLAS.concepts:
        seen.append(page.evaluate("document.activeElement.dataset.concept"))
        width = page.evaluate(
            "getComputedStyle(document.activeElement"
            ".querySelector('.atlas-node-box')).strokeWidth"
        )
        assert float(width.removesuffix("px")) >= 3
        page.keyboard.press("Tab")
    assert seen == [item.id for item in ATLAS.concepts]


def test_the_map_scrolls_in_its_own_box_on_a_phone(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=PHONE, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="load")
    box = page.locator("#atlas-map")
    client, scroll = box.evaluate("e => [e.clientWidth, e.scrollWidth]")
    assert scroll > client
    assert box.get_attribute("tabindex") == "0"
    assert box.get_attribute("role") == "region"
    # The drawing keeps its natural size: its labels are not shrunk.
    width = box.locator("svg").evaluate("e => e.getBoundingClientRect().width")
    assert width == int(box.locator("svg").get_attribute("width"))
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    context.close()
