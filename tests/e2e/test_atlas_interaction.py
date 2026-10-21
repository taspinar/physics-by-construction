"""Required checks on the course atlas with its modules (ADR 018 decision 3,
F126): selection with the selected-concept panel, the modes, zoom, the
region selector with its focused view, and the filters coordinated with the
index's, all by keyboard, storing and requesting nothing.

Without scripts the atlas is checked by tests/e2e/test_atlas.py, unchanged.
What a selection or a filter must show is computed here from ``Atlas``, the
module that generates the page, never from the page itself.
"""

from pathlib import Path

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, BrowserContext, Page
from support import site_checks
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, PHONE, TABLET, WCAG_TAGS, describe
from support.site_server import SiteServer

from pbc.authoring import COURSES as ALL_COURSES
from pbc.authoring.atlas import PLANNED, Atlas
from pbc.authoring.path import PATH_PAGE

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
ATLAS = Atlas.read(SITE_SOURCE)
COURSES = {course.id for course in ALL_COURSES}
PATHS = {path.id for path in ATLAS.path.curriculum.paths}
# The smallest label the drawing sets (the count of an area and the state of
# a concept), in CSS pixels at the natural size of the map.
MINIMUM_LABEL = 11.5

# Every edge of the map as the page writes it: (kind, from, to).
EDGES = (
    [("prerequisite", e.source, e.target) for e in ATLAS.prerequisite_edges()]
    + [("conceptual", *c.concepts) for c in ATLAS.manifest.connections]
    + [("capstone", m.member, m.capstone) for m in ATLAS.memberships()]
)


def related(
    concept: str, kinds: tuple[str, ...] = ("prerequisite", "conceptual", "capstone")
):
    """The edges of a concept, and the concepts at their other ends."""
    edges = {edge for edge in EDGES if concept in edge[1:] and edge[0] in kinds}
    ends = {end for _, a, b in edges for end in (a, b) if end != concept}
    return edges, ends


# A concept with every kind of relationship but capstone membership, and a
# lesson: the richest case to select.
RICH = max(
    (item for item in ATLAS.concepts if ATLAS.lessons_of(item)),
    key=lambda item: (
        len({kind for kind, *_ in related(item.id)[0]}),
        len(related(item.id)[0]),
    ),
).id


@pytest.fixture
def context(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=DESKTOP)
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext, server: SiteServer) -> Page:
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="networkidle")
    return page


def node(page: Page, concept: str):
    return page.locator(f'#atlas-map a[data-concept="{concept}"]')


def marked_edges(page: Page) -> set[tuple[str, str, str]]:
    return {
        tuple(item)
        for item in page.locator("#atlas-map .atlas-edge.is-related").evaluate_all(
            "edges => edges.map(e => [e.dataset.kind, e.dataset.from, e.dataset.to])"
        )
    }


def marked_nodes(page: Page) -> set[str]:
    return set(
        page.locator("#atlas-map a.is-neighbour").evaluate_all(
            "nodes => nodes.map(n => n.dataset.concept)"
        )
    )


def visible_kinds(page: Page) -> set[str]:
    return set(
        page.locator("#atlas-map .atlas-edge").evaluate_all(
            "edges => edges.filter(e => getComputedStyle(e).display !== 'none')"
            ".map(e => e.dataset.kind)"
        )
    )


# --- The default state ----------------------------------------------------------


def test_the_structure_stays_visible_by_default_with_every_edge_and_link(page: Page):
    nodes = page.locator("#atlas-map .atlas-nodes a")
    assert nodes.count() == len(ATLAS.concepts)
    assert page.locator("#atlas-map .atlas-outside").count() == 0
    assert (
        page.locator("#atlas-map .atlas-has-focus, #atlas-map .is-related").count() == 0
    )
    assert visible_kinds(page) == {"prerequisite", "conceptual", "capstone"}
    # The data is the data of the page: the script adds and removes no edge.
    edges = page.locator("#atlas-map .atlas-edge").evaluate_all(
        "edges => edges.map(e => [e.dataset.kind, e.dataset.from, e.dataset.to])"
    )
    assert sorted(map(tuple, edges)) == sorted(EDGES)
    # Every concept box still names its panel; every lesson plate its lesson.
    for href in nodes.evaluate_all("links => links.map(a => a.getAttribute('href'))"):
        assert href.startswith("#concept-")
    plates = page.locator("#atlas-map a.atlas-lesson")
    assert plates.count() == sum(len(lessons) for _, lessons in ATLAS.views())
    assert all(
        href.endswith("index.html")
        for href in plates.evaluate_all(
            "links => links.map(a => a.getAttribute('href'))"
        )
    )


# --- Selection ------------------------------------------------------------------


def test_choosing_a_concept_marks_its_relationships_and_shows_its_panel(page: Page):
    concept = ATLAS.manifest.concept(RICH)
    node(page, RICH).click()
    edges, ends = related(RICH)
    assert marked_edges(page) == edges
    assert marked_nodes(page) == ends
    assert "is-selected" in node(page, RICH).get_attribute("class")
    # The choice does not leave the map for the panel below.
    assert page.evaluate("location.hash") == ""
    panel = page.locator("#atlas-selection .atlas-selected")
    assert panel.is_visible()
    assert panel.locator("h3").inner_text() == concept.name
    text = " ".join(panel.inner_text().split())
    assert concept.explanation in text
    for lesson in ATLAS.lessons_of(concept):
        name = Path(Path(lesson.page).with_suffix(".html")).parent.name
        assert panel.locator(f'a[href*="/{name}/"]').count() >= 1
    for connection in ATLAS.manifest.connections:
        if RICH in connection.concepts:
            assert connection.rationale in text
    # Direction and meaning are said in words.
    assert "arrows into this concept" in text and "conceptual connections" in text


def test_a_concept_is_chosen_by_keyboard_and_escape_clears_it(page: Page):
    node(page, RICH).focus()
    page.keyboard.press("Enter")
    assert "is-selected" in node(page, RICH).get_attribute("class")
    assert page.locator("#atlas-selection .atlas-selected").is_visible()
    status = page.locator("#atlas-selection [role=status]").inner_text()
    assert ATLAS.manifest.concept(RICH).name in status
    page.keyboard.press("Escape")
    assert page.locator("#atlas-selection .atlas-selected").is_hidden()
    assert page.locator("#atlas-map .is-selected, #atlas-map .is-related").count() == 0
    assert page.evaluate("document.activeElement.dataset.concept") == RICH


def test_focus_and_hover_preview_the_relationships(page: Page):
    edges, ends = related(RICH)
    node(page, RICH).focus()
    assert marked_edges(page) == edges and marked_nodes(page) == ends
    assert page.locator("#atlas-map .is-selected").count() == 0
    page.locator("#atlas-controls select[name=region]").focus()
    assert marked_edges(page) == set()
    node(page, RICH).hover()
    assert marked_edges(page) == edges


def test_the_panels_concept_links_walk_the_relationships_by_keyboard(page: Page):
    node(page, RICH).focus()
    page.keyboard.press("Enter")
    _, ends = related(RICH)
    link = page.locator(
        "#atlas-selection .atlas-selected-body a[href*='#concept-']"
    ).first
    target = link.get_attribute("href").split("#concept-")[-1]
    assert target in ends
    link.focus()
    page.keyboard.press("Enter")
    assert "is-selected" in node(page, target).get_attribute("class")
    heading = page.locator("#atlas-selection .atlas-selected h3")
    assert heading.inner_text() == ATLAS.manifest.concept(target).name
    assert page.evaluate("document.activeElement.id") == "atlas-selected-name"
    assert marked_edges(page) == related(target)[0]
    # The link to the full panel still leads to it.
    page.locator("#atlas-selection .atlas-selected-more a").click()
    page.wait_for_function(f"document.getElementById('concept-{target}').open")
    assert page.evaluate("location.hash") == f"#concept-{target}"


def test_a_planned_concept_shows_its_planned_slots_and_no_lesson_link(page: Page):
    planned = next(
        item
        for item in ATLAS.concepts
        if ATLAS.state(item) == PLANNED and ATLAS.capstone_of(item) is None
    )
    node(page, planned.id).click()
    panel = page.locator("#atlas-selection .atlas-selected")
    assert panel.get_attribute("data-concept-state") == PLANNED
    slots = panel.locator("li[data-slot-state=planned]")
    assert slots.count() == len(ATLAS.planned_of(planned))
    assert slots.locator("a").count() == 0


# --- Modes ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode, kinds",
    [
        ("all", {"prerequisite", "conceptual", "capstone"}),
        ("concepts", set()),
        ("prerequisite", {"prerequisite"}),
        ("conceptual", {"conceptual"}),
    ],
)
def test_the_modes_show_the_kinds_of_relationship_apart(
    page: Page, mode: str, kinds: set[str]
):
    page.locator(f"#atlas-controls input[name=atlas-show][value={mode}]").check()
    assert visible_kinds(page) == kinds
    assert page.locator("#atlas-map .atlas-nodes a:visible").count() == len(
        ATLAS.concepts
    )
    node(page, RICH).click()
    assert marked_edges(page) == related(RICH, tuple(kinds))[0]


def test_the_modes_are_radio_buttons_moved_by_the_arrow_keys(page: Page):
    first = page.locator("#atlas-controls input[name=atlas-show]").first
    first.focus()
    page.keyboard.press("ArrowRight")
    assert (
        page.locator("#atlas-controls input[name=atlas-show]:checked").get_attribute(
            "value"
        )
        == "concepts"
    )
    assert visible_kinds(page) == set()


# --- Zoom and the size of the labels -------------------------------------------


def _drawn_width(page: Page) -> float:
    return page.locator("#atlas-map svg").evaluate(
        "e => e.getBoundingClientRect().width"
    )


def _smallest_label(page: Page) -> float:
    """The smallest rendered size of a visible label of the map, in CSS px."""
    return page.locator("#atlas-map svg").evaluate(
        """svg => {
          const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
          const sizes = [...svg.querySelectorAll('text')]
            .filter(t => t.checkVisibility({visibilityProperty: true}))
            .map(t => parseFloat(getComputedStyle(t).fontSize) * scale);
          return Math.min(...sizes);
        }"""
    )


def test_zoom_never_goes_below_the_natural_size_and_works_by_keyboard(page: Page):
    natural = int(page.locator("#atlas-map svg").get_attribute("width"))
    assert _drawn_width(page) == natural
    controls = page.locator("#atlas-controls")
    zoom_out = controls.get_by_role("button", name="Zoom out")
    zoom_in = controls.get_by_role("button", name="Zoom in")
    assert zoom_out.is_disabled()
    level = controls.locator(".atlas-zoom-level")
    assert level.inner_text() == "100%"
    zoom_in.focus()
    page.keyboard.press("Enter")
    assert level.inner_text() == "125%"
    assert abs(_drawn_width(page) - natural * 1.25) <= 1
    page.locator("#atlas-map").focus()
    page.keyboard.press("+")
    page.keyboard.press("+")
    page.keyboard.press("+")
    assert level.inner_text() == "200%" and zoom_in.is_disabled()
    page.keyboard.press("-")
    assert level.inner_text() == "150%"
    page.keyboard.press("0")
    assert level.inner_text() == "100%"
    for _ in range(3):
        page.keyboard.press("-")
    assert _drawn_width(page) == natural
    controls.get_by_role("button", name="Zoom in").click()
    controls.get_by_role("button", name="Actual size").click()
    assert _drawn_width(page) == natural


@pytest.mark.parametrize("scripts", [True, False], ids=["with-scripts", "without"])
@pytest.mark.parametrize("viewport", [DESKTOP, TABLET], ids=["desktop", "tablet"])
def test_the_labels_of_the_map_keep_their_size_and_the_map_scrolls_instead(
    browser: Browser, server: SiteServer, viewport: dict[str, int], scripts: bool
):
    context = browser.new_context(viewport=viewport, java_script_enabled=scripts)
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="networkidle")
    assert _smallest_label(page) >= MINIMUM_LABEL
    box = page.locator("#atlas-map")
    natural = int(box.locator("svg").get_attribute("width"))
    client = box.evaluate("e => e.clientWidth")
    if client < natural:
        # Narrower than the drawing: the box scrolls; the drawing is not shrunk.
        assert box.evaluate("e => e.scrollWidth") > client
    if scripts:
        page.locator("#atlas-controls").get_by_role("button", name="Zoom out").click(
            force=True
        )
        page.locator("#atlas-controls select[name=region]").select_option("mechanics")
        assert _smallest_label(page) >= MINIMUM_LABEL
    assert page.evaluate("document.documentElement.scrollWidth") <= viewport["width"]
    context.close()


# --- Regions and the phone ------------------------------------------------------


@pytest.fixture
def phone(browser: Browser, server: SiteServer) -> Page:
    context = browser.new_context(viewport=PHONE)
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="networkidle")
    yield page
    context.close()


def _region_list(page: Page) -> list[str]:
    return page.locator("#atlas-selection .atlas-region-list li > a").all_inner_texts()


def test_a_phone_opens_the_map_on_one_region_with_its_list_below(phone: Page):
    first = ATLAS.areas[0]
    region = phone.locator("#atlas-controls select[name=region]")
    assert region.is_visible() and region.input_value() == first
    assert _region_list(phone) == [item.name for item in ATLAS.in_area(first)]
    outside = phone.locator("#atlas-map .atlas-nodes a:not(.atlas-outside)")
    assert sorted(
        outside.evaluate_all("ns => ns.map(n => n.dataset.concept)")
    ) == sorted(item.id for item in ATLAS.in_area(first))
    # The region's box fits the screen at the natural size of its labels.
    box = phone.locator("#atlas-map")
    assert box.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    assert _smallest_label(phone) >= MINIMUM_LABEL
    link = phone.locator("#atlas-selection .atlas-region-list p a")
    assert phone.locator(link.get_attribute("href")).count() == 1
    assert phone.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    # The rest of the map is one choice away.
    region.select_option("")
    assert phone.locator("#atlas-map .atlas-outside").count() == 0
    assert phone.locator("#atlas-selection .atlas-region-list").is_hidden()


def test_the_region_selector_offers_every_area_and_the_views(page: Page):
    region = page.locator("#atlas-controls select[name=region]")
    assert region.input_value() == ""
    values = region.locator("option").evaluate_all("os => os.map(o => o.value)")
    assert values == ["", *ATLAS.areas, "views"]
    path = next(area for area in ATLAS.areas if area in PATHS)
    region.focus()
    region.select_option(path)
    assert _region_list(page) == [item.name for item in ATLAS.in_area(path)]
    region.select_option("views")
    assert page.locator("#atlas-map .atlas-nodes a:not(.atlas-outside)").count() == 0
    assert page.locator("#atlas-map a.atlas-lesson:not(.atlas-outside)").count() == sum(
        len(lessons) for _, lessons in ATLAS.views()
    )
    assert _region_list(page) == page.locator(
        "#atlas-map .atlas-view-title"
    ).evaluate_all("ts => ts.map(t => t.textContent.replace(/\\s+/g, ' ').trim())")


def test_choosing_a_concept_of_another_region_brings_its_region(phone: Page):
    first = ATLAS.areas[0]
    elsewhere = next(
        (
            end
            for end in related(ATLAS.in_area(first)[0].id)[1]
            if ATLAS.manifest.concept(end).area != first
        ),
        None,
    )
    if elsewhere is None:
        pytest.fail(
            "the first concept of the first area has no relationship outside it"
        )
    node(phone, ATLAS.in_area(first)[0].id).click()
    link = phone.locator(
        f"#atlas-selection .atlas-selected a[href='#concept-{elsewhere}']"
    )
    link.first.click()
    area = ATLAS.manifest.concept(elsewhere).area
    assert phone.locator("#atlas-controls select[name=region]").input_value() == area
    assert node(phone, elsewhere).is_visible()


def test_the_page_with_the_atlas_reflows_at_320_pixels(phone: Page):
    phone.locator("#atlas-controls details.atlas-filters > summary").click()
    node(phone, ATLAS.in_area(ATLAS.areas[0])[0].id).click()
    assert phone.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
    for selector in ("#atlas-controls", "#atlas-selection .atlas-selected"):
        width = phone.locator(selector).evaluate("e => e.getBoundingClientRect().right")
        assert width <= PHONE["width"]


# --- Filters --------------------------------------------------------------------


def _entries(item) -> list[dict]:
    """A concept's lessons and its planned slots, as the index lists them."""
    found = []
    for lesson in ATLAS.lessons_of(item):
        slot = ATLAS.path.curriculum.slot(lesson.slot)
        found.append(
            {
                "course": lesson.course,
                "path": slot.path if slot else "",
                "method": set(lesson.methods),
                "difficulty": str(lesson.difficulty),
                "state": "published",
            }
        )
    if ATLAS.planned_of(item):
        found.append(
            {
                "course": item.area if item.area in COURSES else "",
                "path": item.area if item.area in PATHS else "",
                "method": set(),
                "difficulty": "",
                "state": "planned",
            }
        )
    return found


def _keeps(entry: dict, want: dict[str, str]) -> bool:
    return all(
        not value or (value in entry[key] if key == "method" else entry[key] == value)
        for key, value in want.items()
    )


FILTER_CASES = [
    {"method": "lean"},
    {"state": "planned"},
    {"course": "mechanics", "state": "published"},
    {"path": next(iter(sorted(PATHS)))},
    {"difficulty": "1", "method": "simulation"},
]


@pytest.mark.parametrize("want", FILTER_CASES, ids=lambda w: "-".join(w.values()))
def test_the_filters_fade_what_the_data_leaves_out(page: Page, want: dict[str, str]):
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    form = page.locator("#atlas-controls form.atlas-filter-form")
    for key, value in want.items():
        form.locator(f"select[name={key}]").select_option(value)
    kept = set(
        page.locator("#atlas-map .atlas-nodes a:not(.is-filtered-out)").evaluate_all(
            "ns => ns.map(n => n.dataset.concept)"
        )
    )
    full = {
        key: want.get(key, "")
        for key in ("course", "path", "method", "difficulty", "state")
    }
    expected = {
        item.id
        for item in ATLAS.concepts
        if any(_keeps(e, full) for e in _entries(item))
    }
    assert kept == expected
    lessons = set(
        page.locator("#atlas-map a.atlas-lesson:not(.is-filtered-out)").evaluate_all(
            "ps => ps.map(p => p.dataset.lesson)"
        )
    )
    expected_lessons = set()
    for _, items in ATLAS.views():
        for lesson in items:
            entry = _entries_of_lesson(lesson)
            if _keeps(entry, full):
                expected_lessons.add(lesson.id)
    assert lessons == expected_lessons
    status = page.locator("#atlas-controls .atlas-status").inner_text()
    assert f"{len(expected)} concept" in status
    # Faded, not removed: every concept stays on the map and takes focus.
    assert page.locator("#atlas-map .atlas-nodes a:visible").count() == len(
        ATLAS.concepts
    )


def _entries_of_lesson(lesson) -> dict:
    slot = ATLAS.path.curriculum.slot(lesson.slot)
    return {
        "course": lesson.course,
        "path": slot.path if slot else "",
        "method": set(lesson.methods),
        "difficulty": str(lesson.difficulty),
        "state": "published",
    }


def test_the_maps_filters_and_the_index_filters_stay_in_step(page: Page):
    atlas_form = page.locator("#atlas-controls form.atlas-filter-form")
    index_form = page.locator("#path-filters form")
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    atlas_form.locator("select[name=course]").select_option("mechanics")
    assert index_form.locator("select[name=course]").input_value() == "mechanics"
    assert page.locator("li.path-card[data-course=mechanics]:visible").count() > 0
    hidden = page.locator(
        "main section#courses li.path-card:not([data-course=mechanics])"
    )
    assert hidden.count() > 0 and all(not row.is_visible() for row in hidden.all())
    index_form.locator("select[name=state]").select_option("planned")
    assert atlas_form.locator("select[name=state]").input_value() == "planned"
    assert atlas_form.locator("select[name=course]").input_value() == "mechanics"
    assert page.locator("#atlas-controls .atlas-status").inner_text() != ""
    # A path filter keeps the lessons of the path wherever the index lists them.
    path = next(iter(sorted(PATHS)))
    atlas_form.locator("button", has_text="Show all").click()
    atlas_form.locator("select[name=path]").select_option(path)
    assert index_form.locator("select[name=path]").input_value() == path
    members = {
        lesson.id
        for lesson in ATLAS.path.lessons
        if (slot := ATLAS.path.curriculum.slot(lesson.slot)) and slot.path == path
    }
    shown = set(
        page.locator(
            "main li.path-card:visible, main li.path-link:visible"
        ).evaluate_all("rows => rows.map(r => r.dataset.lessonId)")
    )
    assert shown == members
    index_form.locator("button", has_text="Show all").click()
    assert atlas_form.locator("select[name=path]").input_value() == ""
    assert page.locator("#atlas-map .is-filtered-out").count() == 0


def test_the_search_finds_the_same_lessons_with_and_without_the_filters(page: Page):
    before = site_checks.search_results(page, "eccentricity")
    assert any(result.endswith("08-kepler-orbit/index.html") for result in before)
    page.keyboard.press("Escape")
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    form = page.locator("#atlas-controls form.atlas-filter-form")
    form.locator("select[name=course]").select_option("thermodynamics")
    form.locator("select[name=state]").select_option("planned")
    after = site_checks.search_results(page, "eccentricity")
    assert after == before


# --- The switch -----------------------------------------------------------------


def test_the_switch_moves_focus_and_marks_the_part_in_view(page: Page):
    switch = page.locator(".atlas-switch")
    switch.get_by_role("link", name="Course index").click()
    page.wait_for_function("document.activeElement.closest('#choose') !== null")
    page.wait_for_function(
        "document.querySelector('.atlas-switch a[href$=\"#choose\"]')"
        ".getAttribute('aria-current') === 'location'"
    )
    switch = page.locator(".atlas-switch")
    switch.get_by_role("link", name="Map").click()
    page.wait_for_function("document.activeElement.id === 'atlas-map'")


# --- Keyboard, labels, accessibility, motion ------------------------------------


_CONTROLS = "#atlas-controls :is(select, input, button, summary)"


def test_every_control_has_a_label_takes_the_keyboard_and_shows_its_focus(page: Page):
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    node(page, RICH).click()
    controls = page.locator(f"{_CONTROLS}, #atlas-selection button")
    assert controls.count() >= 1 + 4 + 3 + 1 + 5 + 1 + 1
    # Tab from the switch reaches every control of the strip in order.
    page.locator(".atlas-switch a").last.focus()
    reached = []
    for _ in range(40):
        page.keyboard.press("Tab")
        if page.evaluate("!document.activeElement.closest('#atlas-controls')"):
            break
        reached.append(page.evaluate("document.activeElement.outerHTML.slice(0, 60)"))
    enabled = page.locator(
        "#atlas-controls :is(select, button:not(:disabled), summary,"
        " input[name=atlas-show]:checked)"
    )
    assert len(reached) == enabled.count()
    for control in controls.all():
        if not control.is_visible() or control.is_disabled():
            continue
        name = control.evaluate(
            """e => (e.labels && e.labels[0] ? e.labels[0].textContent
                     : e.getAttribute('aria-label') || e.textContent).trim()"""
        )
        assert name, control.evaluate("e => e.outerHTML.slice(0, 80)")
        control.focus()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        style = page.evaluate(
            "(() => { const s = getComputedStyle(document.activeElement);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; })()"
        )
        assert style[0] not in ("none", "hidden") and style[1] >= 2, name


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_the_accessibility_scan_passes_in_several_states_of_the_atlas(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="networkidle")
    options = {
        "runOnly": {"type": "tag", "values": WCAG_TAGS},
        "resultTypes": ["violations"],
    }
    violations: list[str] = []

    def scan(state: str) -> None:
        results = Axe().run(page, options=options)
        violations.extend(
            f"{finding['id']} at {item['target']} ({state})"
            for finding in results.response["violations"]
            for item in finding["nodes"]
        )

    scan("default")
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    page.locator("#atlas-controls select[name=method]").select_option("lean")
    scan("filtered")
    page.locator("#atlas-controls select[name=region]").select_option(ATLAS.areas[1])
    target = ATLAS.in_area(ATLAS.areas[1])[0].id
    node(page, target).click()
    scan("region, selected")
    page.locator("#atlas-controls input[name=atlas-show][value=prerequisite]").check()
    page.locator("#atlas-controls").get_by_role("button", name="Zoom in").click()
    scan("prerequisites, zoomed")
    context.close()
    assert not violations, "\n".join(violations)


def test_nothing_moves_when_the_reader_asks_for_less_motion(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = context.new_page()
    page.goto(server.url + PATH, wait_until="networkidle")
    node(page, RICH).click()
    page.locator("#atlas-controls").get_by_role("button", name="Zoom in").click()
    page.locator("#atlas-controls select[name=region]").select_option(ATLAS.areas[0])
    page.locator("#atlas-controls input[name=atlas-show][value=conceptual]").check()
    assert page.evaluate("document.getAnimations().length") == 0
    durations = page.locator(
        "#atlas-controls *, #atlas-map *, #atlas-selection *"
    ).evaluate_all(
        "es => es.map(e => getComputedStyle(e)).filter(s =>"
        " parseFloat(s.transitionDuration) > 0 || s.animationName !== 'none')"
        ".length"
    )
    assert durations == 0
    context.close()


# --- Nothing kept, nothing requested; the payload --------------------------------


def operate_everything(page: Page) -> int:
    """Operate every control of the atlas by keyboard and by pointer."""
    page.locator("#atlas-controls details.atlas-filters > summary").click()
    count = site_checks.drive_controls(
        page, "#atlas-controls :is(input, select, button, summary)"
    )
    page.locator("#atlas-controls select[name=region]").select_option("")
    for concept in (RICH, ATLAS.concepts[-1].id):
        node(page, concept).click()
        count += 1
    node(page, RICH).focus()
    page.keyboard.press("Enter")
    for link in page.locator(
        "#atlas-selection .atlas-selected-body a[href*='#concept-']"
    ).all()[:3]:
        link.click()
        count += 1
    page.locator("#atlas-map").focus()
    for key in ("+", "-", "0", "Escape"):
        page.keyboard.press(key)
    count += site_checks.drive_controls(page, "#atlas-selection button")
    return count


def test_the_atlas_modules_contain_no_request_and_no_storage(site_dir: Path):
    violations = site_checks.check_atlas_module_sources(site_dir)
    assert not violations, describe(violations)


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_operating_every_control_requests_nothing_and_stores_nothing(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    violations = site_checks.check_controls_keep_nothing(
        browser, server, PATH, operate_everything, viewport
    )
    assert not violations, describe(violations)


def test_the_enhancement_is_measured_apart_and_the_page_stays_within_its_budget(
    browser: Browser, server: SiteServer, site_dir: Path, capsys: pytest.CaptureFixture
):
    modules = {
        name: (site_dir / site_checks.LEARNER / name).stat().st_size
        for name in site_checks.ATLAS_MODULES
    }
    requested: set[str] = set()
    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    page.on("response", lambda response: requested.add(response.url))
    page.goto(server.url + PATH, wait_until="networkidle")
    context.close()
    # The modules load with the page and nothing else loads for them.
    for name in site_checks.ATLAS_MODULES:
        assert any(url.endswith(f"/learner/{name}") for url in requested), name
    sizes = site_checks.measure_payloads(browser, server, site_dir, [site_dir / PATH])
    page_total = sizes[PATH]
    enhancement = sum(modules.values())
    with capsys.disabled():
        print(f"\nThe atlas enhancement: {enhancement:,} bytes", end="")
        print(f" ({', '.join(f'{n} {s:,}' for n, s in modules.items())});", end="")
        print(f" the path page with it: {page_total:,} bytes")
    assert enhancement < page_total
    violations = site_checks.check_payload({PATH: page_total})
    assert not violations, describe(violations)
