"""Required checks on the course atlas of the built path page (ADR 021
decision 3, F133): twelve sequences and the Lean entry as native exclusive
disclosures, the open panel beside the cards on a wide screen and under its
card on a phone, every published lesson reached without JavaScript and by
keyboard alone, the anchors of the previous atlas, and the address module,
which requests, stores, and sets nothing.

What the sequences hold (rows, counts, states) is computed here from
``Atlas``, the module that generates the page, never from the page itself;
tests/unit/test_atlas.py covers the generated HTML. Verification runs these
checks in Chromium; ``--engine firefox`` and ``--engine webkit`` run them in
the other engines (docs/development.md, "Other browser engines").
"""

from pathlib import Path

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, BrowserContext, Page
from support import site_checks
from support.paths import SITE_SOURCE
from support.site_checks import PHONE, WCAG_TAGS, describe
from support.site_server import SiteServer

from pbc.authoring.atlas import Atlas, AtlasSequence
from pbc.authoring.path import PATH_PAGE
from pbc.authoring.website import introduced, introduction_page

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
ATLAS = Atlas.read(SITE_SOURCE)
INTRODUCED = introduced(SITE_SOURCE)
SEQUENCES = ATLAS.sequences()
LESSONS = ATLAS.path.lessons
WIDE = {"width": 1280, "height": 800}
NARROW = {"width": 390, "height": 844}

# The anchors of the path page at the base of F133 (6627512), from the page
# its generators wrote (docs: the plan of #338, "Anchors of the base page").
# These stay ids of the page:
KEPT = [
    "atlas",
    "choose",
    "courses",
    "paths",
    "methods",
    "difficulty",
    "order",
    "your-progress",
    "progress-controls",
    "recommendations",
    "learner-state-data",
    *(f"course-{c}" for c in ("mechanics", "thermodynamics", "waves",
                              "electromagnetism", "fluids", "quantum",
                              "astrophysics", "materials")),
    *(f"path-{p}" for p in ("reasoning", "law-discovery", "benchmarking",
                            "autonomous-research")),
    *(f"method-{m}" for m in ("simulation", "measured-data", "llm-agents", "abm",
                              "lean")),
]  # fmt: skip
# These open the sequence that holds them now: the lesson lists of the
# courses and the concept panels of the map.
OPENED = {
    **{
        f"course-{c.id}-lessons": f"course-{c.id}"
        for c in (s for s in SEQUENCES if s.part == "A")
    },
    **{
        f"concept-{concept.id}": (
            f"course-{concept.area}"
            if concept.area in {s.id for s in SEQUENCES if s.part == "A"}
            else f"path-{concept.area}"
        )
        for concept in ATLAS.concepts
    },
}
# The rest belonged to the drawings and controls that left the page (the map,
# its markers and controls, the dependency map, the filters); they reach the
# top of the page, which is the atlas.


def by_part(part: str) -> list[AtlasSequence]:
    return [sequence for sequence in SEQUENCES if sequence.part == part]


@pytest.fixture
def without_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=WIDE, java_script_enabled=False)
    yield context
    context.close()


@pytest.fixture
def with_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=WIDE)
    yield context
    context.close()


def open_page(context: BrowserContext, server: SiteServer, fragment: str = "") -> Page:
    page = context.new_page()
    page.goto(server.url + PATH + fragment, wait_until="networkidle")
    return page


def open_ids(page: Page) -> list[str]:
    return page.locator("details.atlas-sequence[open]").evaluate_all(
        "items => items.map(item => item.id)"
    )


def show(page: Page, anchor: str) -> None:
    """Open the sequence ``anchor`` as a reader does, by its card."""
    if page.locator(f"#{anchor}").get_attribute("open") is None:
        page.locator(f"#{anchor} > summary").click()


def box(page: Page, selector: str) -> dict[str, float]:
    found = page.locator(selector).first.bounding_box()
    assert found is not None, selector
    return found


# --- The layout ------------------------------------------------------------------


@pytest.mark.parametrize("scripts", [True, False], ids=["scripts", "no-scripts"])
def test_a_wide_screen_shows_the_cards_and_the_first_panel_beside_them(
    browser: Browser, server: SiteServer, scripts: bool
):
    context = browser.new_context(viewport=WIDE, java_script_enabled=scripts)
    page = open_page(context, server)
    cards = page.locator("details.atlas-sequence > summary")
    assert cards.count() == len(SEQUENCES) == 13
    assert open_ids(page) == ["course-mechanics"]
    assert (
        page.locator("#lean > summary")
        .inner_text()
        .startswith("Beyond the curriculum: proofs in Lean")
    )
    first_card = box(page, "#course-mechanics > summary")
    panel = box(page, "#course-mechanics .atlas-panel")
    # Every card in one column at the left, the panel beside them.
    lefts = {round(cards.nth(i).bounding_box()["x"]) for i in range(12)}
    assert lefts == {round(first_card["x"])}
    assert panel["x"] >= first_card["x"] + first_card["width"]
    # The first course's panel is readable without scrolling: its title, its
    # description, and its first rows are inside the window.
    for selector in (
        "#course-mechanics .atlas-panel-title",
        "#course-mechanics .atlas-description",
        "#course-mechanics .atlas-row >> nth=2",
    ):
        part = box(page, selector)
        assert part["y"] >= 0 and part["y"] + part["height"] <= WIDE["height"], selector
        assert part["x"] + part["width"] <= WIDE["width"]
    context.close()


def test_a_phone_shows_an_accordion_with_the_open_panel_under_its_card(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=NARROW)
    page = open_page(context, server)
    card = box(page, "#course-mechanics > summary")
    panel = box(page, "#course-mechanics .atlas-panel")
    following = box(page, "#course-thermodynamics > summary")
    assert panel["y"] >= card["y"] + card["height"] - 1
    assert following["y"] >= panel["y"] + panel["height"] - 1
    assert panel["x"] >= card["x"] and panel["x"] + panel["width"] <= NARROW["width"]
    page.locator("#path-benchmarking > summary").click()
    assert open_ids(page) == ["path-benchmarking"]
    # Opening scrolls the card into view after the toggle; measure once that
    # has happened, and the card and the panel in one step, so that a slow
    # runner cannot take the two boxes on either side of the scroll.
    page.wait_for_function(
        "() => document.querySelector('#path-benchmarking > summary')"
        ".getBoundingClientRect().top <= window.innerHeight / 2"
    )
    card, panel = page.evaluate(
        """() => [
            "#path-benchmarking > summary",
            "#path-benchmarking .atlas-panel",
        ].map((selector) => {
                const r = document.querySelector(selector).getBoundingClientRect();
                return { y: r.y, height: r.height };
            })"""
    )
    assert panel["y"] >= card["y"] + card["height"] - 1
    # Opening scrolls the card into view.
    assert -1 <= card["y"] <= NARROW["height"] / 2
    assert page.locator("#lean > summary").is_visible()
    context.close()


def test_without_the_wide_rule_the_page_falls_back_to_the_accordion(
    with_scripts: BrowserContext, server: SiteServer
):
    """A browser without ::details-content gets the accordion: the wide rule is
    removed from the stylesheet, as such a browser would ignore it."""
    page = open_page(with_scripts, server)
    removed = page.evaluate(
        """() => {
          let removed = 0;
          for (const sheet of document.styleSheets) {
            let rules;
            try { rules = sheet.cssRules; } catch { continue; }
            for (let i = rules.length - 1; i >= 0; i--) {
              if (rules[i] instanceof CSSSupportsRule &&
                  rules[i].conditionText.includes("details-content")) {
                sheet.deleteRule(i);
                removed++;
              }
            }
          }
          return removed;
        }"""
    )
    assert removed == 1
    card = box(page, "#course-mechanics > summary")
    panel = box(page, "#course-mechanics .atlas-panel")
    following = box(page, "#course-thermodynamics > summary")
    assert panel["y"] >= card["y"] + card["height"] - 1
    assert following["y"] >= panel["y"] + panel["height"] - 1
    page.locator("#path-reasoning > summary").click()
    assert open_ids(page) == ["path-reasoning"]
    assert page.locator("#path-reasoning .atlas-row").first.is_visible()


# --- Without scripts, by keyboard ---------------------------------------------------


def test_without_scripts_every_published_lesson_is_reached_through_the_cards(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    reached: dict[str, str] = {}
    for sequence in SEQUENCES:
        show(page, sequence.anchor)
        # One sequence open at a time, without a script.
        assert open_ids(page) == [sequence.anchor]
        links = page.locator(f"#{sequence.anchor} .atlas-row a.lesson-link")
        shown = links.evaluate_all(
            "links => links.filter(a => a.checkVisibility())"
            ".map(a => a.getAttribute('href'))"
        )
        expected = [row.lesson for row in sequence.rows if row.lesson is not None]
        assert len(shown) == len(expected), sequence.id
        for lesson, href in zip(expected, shown, strict=True):
            assert href == "../" + lesson.page.removesuffix(".qmd") + ".html"
            reached[lesson.id] = href
        planned = page.locator(f"#{sequence.anchor} .atlas-row.planned-slot")
        assert planned.count() == sequence.planned + sequence.extension_planned
        assert planned.locator("a").count() == 0
    assert set(reached) == {lesson.id for lesson in LESSONS}


@pytest.mark.parametrize("viewport", [WIDE, NARROW], ids=["wide", "phone"])
def test_a_paths_optional_extensions_follow_its_core_under_their_own_heading(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """The extension rows of a method path stand after its core rows, under
    the heading "Optional extensions", visible and reachable without
    scripts, with the row marks of the core and no other (ADR 022 decision
    2); the core count of the card leaves them out."""
    context = browser.new_context(viewport=viewport, java_script_enabled=False)
    page = open_page(context, server)
    paths = [sequence for sequence in by_part("B") if sequence.extensions]
    assert paths
    for sequence in paths:
        show(page, sequence.anchor)
        group = page.locator(f"#{sequence.anchor} .atlas-extensions")
        heading = group.locator("h3")
        assert heading.inner_text().strip() == "Optional extensions"
        assert heading.is_visible()
        core = page.locator(f"#{sequence.anchor} .atlas-rows").first
        assert (
            box(page, f"#{sequence.anchor} .atlas-rows")["y"]
            < (heading.bounding_box()["y"])
        )
        assert core.locator(":scope > li").count() == len(sequence.core)
        rows = group.locator(".atlas-row")
        assert rows.count() == len(sequence.extensions)
        for index, row in enumerate(sequence.extensions):
            item = rows.nth(index)
            assert item.locator(".atlas-label").inner_text() == row.label
            if row.lesson is not None:
                link = item.locator("a.lesson-link")
                assert link.is_visible()
                assert link.get_attribute("href") == (
                    "../" + row.lesson.page.removesuffix(".qmd") + ".html"
                )
        card = page.locator(f"#{sequence.anchor} .atlas-card-count")
        assert (
            card.inner_text() == f"{sequence.published} of {len(sequence.core)} lessons"
        )
    # No row outside the core carries a mark the core does not have.
    marks = page.locator(".atlas-extensions .atlas-mark").evaluate_all(
        "marks => marks.map(m => m.className)"
    )
    assert set(marks) <= {"atlas-mark atlas-mark-planned"}
    context.close()


def test_by_keyboard_a_card_opens_and_its_panel_comes_next_in_order(
    browser: Browser, without_scripts: BrowserContext, server: SiteServer
):
    # Safari, and WebKit with it, moves to the next link with Option-Tab
    # unless the reader turns on "Press Tab to highlight each item"; the
    # order is the same (the manual check of #338 records it in Safari).
    tab = "Alt+Tab" if browser.browser_type.name == "webkit" else "Tab"
    page = open_page(without_scripts, server)
    page.locator("#course-mechanics > summary").focus()
    # The first course is open: Tab goes into its panel.
    page.keyboard.press(tab)
    first = ATLAS.sequences()[0].rows[0].lesson
    assert page.evaluate("document.activeElement.textContent") == first.title
    for key, sequence in (("Enter", SEQUENCES[5]), ("Space", by_part("B")[1])):
        summary = page.locator(f"#{sequence.anchor} > summary")
        summary.focus()
        style = summary.evaluate(
            "e => { const s = getComputedStyle(e);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }"
        )
        assert style[0] not in ("none", "hidden") and style[1] >= 2
        page.keyboard.press(key)
        assert open_ids(page) == [sequence.anchor]
        page.keyboard.press(tab)
        row = next(row for row in sequence.rows if row.lesson is not None)
        assert page.evaluate("document.activeElement.textContent") == row.title


def test_by_keyboard_alone_every_sequence_opens_and_every_published_lesson_is_reached(
    browser: Browser, without_scripts: BrowserContext, server: SiteServer
):
    tab = "Alt+Tab" if browser.browser_type.name == "webkit" else "Tab"
    focus_ring = (
        "e => { const s = getComputedStyle(e);"
        " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }"
    )
    page = open_page(without_scripts, server)
    reached: set[str] = set()
    first = f"{SEQUENCES[0].anchor}"
    # Tab from the top of the page until the first card takes the focus.
    for _ in range(200):
        page.keyboard.press(tab)
        if page.evaluate("document.activeElement.parentElement?.id") == first:
            break
    for index, sequence in enumerate(SEQUENCES):
        summary = page.locator(f"#{sequence.anchor} > summary")
        assert (
            page.evaluate("document.activeElement.parentElement?.id") == sequence.anchor
        )
        style, width = summary.evaluate(focus_ring)
        assert style not in ("none", "hidden") and width >= 2, sequence.id
        key = "Enter" if index % 2 == 0 else "Space"
        if page.locator(f"#{sequence.anchor}").get_attribute("open") is not None:
            page.keyboard.press(key)  # close the card that opens at load
            assert page.locator(f"#{sequence.anchor}").get_attribute("open") is None
        page.keyboard.press(key)
        assert open_ids(page) == [sequence.anchor], sequence.id
        expected = [row.lesson for row in sequence.rows if row.lesson is not None]
        for lesson in expected:
            page.keyboard.press(tab)
            focused = page.evaluate(
                "({inside: !!document.activeElement.closest("
                f"'#{sequence.anchor} .atlas-row a.lesson-link'), "
                "href: document.activeElement.getAttribute('href')})"
            )
            assert focused["inside"], (sequence.id, lesson.id)
            assert focused["href"] == "../" + lesson.page.removesuffix(".qmd") + ".html"
            style, width = page.locator(":focus").evaluate(focus_ring)
            assert style not in ("none", "hidden") and width >= 1, lesson.id
            reached.add(lesson.id)
        if sequence.id in INTRODUCED:
            # F156: the panel ends with the link to the introduction.
            page.keyboard.press(tab)
            focused = page.evaluate(
                "({inside: !!document.activeElement.closest("
                f"'#{sequence.anchor} .atlas-introduction'), "
                "href: document.activeElement.getAttribute('href')})"
            )
            assert focused["inside"], sequence.id
            assert focused["href"] == (
                "../" + introduction_page(sequence.id).removesuffix(".qmd") + ".html"
            )
        if index + 1 < len(SEQUENCES):
            # The next Tab leaves the open card for the next summary.
            page.keyboard.press(tab)
    assert reached == {lesson.id for lesson in LESSONS}


def test_the_textual_equivalent_names_every_sequence_and_lesson_with_its_state(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    text = page.locator("ol.atlas-text").inner_text()
    for sequence in SEQUENCES:
        assert sequence.title in text
        for row in sequence.rows:
            name = f"{row.label} {row.title}" if row.label else row.title
            state = "published" if row.lesson else "planned"
            assert f"{name} ({state}" in text, name
    # Present for assistive technology, not shown.
    hidden = page.locator("section:has(> ol.atlas-text)")
    assert "visually-hidden" in hidden.get_attribute("class")
    size = hidden.bounding_box()
    assert size["width"] <= 1 and size["height"] <= 1


def test_published_and_planned_rows_differ_in_words_and_form(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    show(page, "course-fluids")
    planned = page.locator("#course-fluids .atlas-row.planned-slot").first
    assert "planned" in planned.inner_text()
    assert (
        planned.locator(".atlas-planned-title").evaluate(
            "e => getComputedStyle(e).fontStyle"
        )
        == "italic"
    )
    capstone = page.locator("#course-fluids .atlas-row-capstone")
    assert "Capstone" in capstone.inner_text()
    description = ATLAS.manifest.capstone("FL10").explanation
    assert capstone.locator(".capstone-description").inner_text() == description
    show(page, "course-thermodynamics")
    t11 = page.locator("#course-thermodynamics .atlas-row-capstone a.lesson-link")
    assert t11.count() == 1


# --- The anchors and the address module --------------------------------------------


def test_every_kept_anchor_of_the_base_page_is_an_id_of_the_page(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    for anchor in KEPT:
        assert page.locator(f"#{anchor}").count() == 1, anchor


@pytest.mark.parametrize(
    "anchor",
    [
        "course-quantum",
        "path-benchmarking",
        "path-autonomous-research",
        "lean",
        "course-waves-lessons",
        f"concept-{ATLAS.in_area('law-discovery')[0].id}",
        f"concept-{ATLAS.in_area('materials')[-1].id}",
    ],
)
def test_an_address_opens_its_sequence(
    with_scripts: BrowserContext, server: SiteServer, anchor: str
):
    page = open_page(with_scripts, server, f"#{anchor}")
    target = OPENED.get(anchor, anchor)
    assert open_ids(page) == [target]
    assert page.locator(f"#{target} .atlas-panel").is_visible()


def test_every_alias_of_the_base_page_names_its_sequence(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    aliases = dict(
        page.locator("details.atlas-sequence[data-aliases]").evaluate_all(
            "items => items.flatMap(item =>"
            " item.dataset.aliases.split(' ').map(alias => [alias, item.id]))"
        )
    )
    assert aliases == OPENED


def test_a_hash_change_opens_its_sequence_and_a_click_sets_the_hash(
    with_scripts: BrowserContext, server: SiteServer
):
    page = open_page(with_scripts, server)
    assert page.evaluate("location.hash") == ""
    page.locator("#course-quantum > summary").click()
    page.wait_for_function("location.hash === '#course-quantum'")
    assert open_ids(page) == ["course-quantum"]
    page.evaluate("location.hash = '#path-law-discovery'")
    page.wait_for_function("document.querySelector('#path-law-discovery').open")
    assert open_ids(page) == ["path-law-discovery"]
    page.locator("#path-law-discovery > summary").focus()
    page.keyboard.press("Enter")  # closing leaves the address as it is
    page.wait_for_timeout(100)
    assert open_ids(page) == []
    assert page.evaluate("location.hash") == "#path-law-discovery"


def test_the_atlas_module_contains_no_request_and_no_storage(site_dir: Path):
    violations = site_checks.check_atlas_module_sources(site_dir)
    assert not violations, describe(violations)


def operate_every_sequence(page: Page) -> int:
    count = 0
    for sequence in SEQUENCES:
        show(page, sequence.anchor)
        count += 1
    page.locator(f"#{SEQUENCES[3].anchor} > summary").focus()
    page.keyboard.press("Enter")
    page.evaluate("location.hash = '#path-reasoning'")
    return count + 1


@pytest.mark.parametrize("viewport", [WIDE, NARROW], ids=["desktop", "phone"])
def test_operating_the_atlas_requests_nothing_and_stores_nothing(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    violations = site_checks.check_controls_keep_nothing(
        browser, server, PATH, operate_every_sequence, viewport
    )
    assert not violations, describe(violations)


def test_progress_js_stays_the_only_script_of_the_page_that_can_store(
    without_scripts: BrowserContext, server: SiteServer, site_dir: Path
):
    page = open_page(without_scripts, server)
    scripts = page.locator("script[src]").evaluate_all(
        "items => items.map(item => item.getAttribute('src'))"
    )
    learner = sorted(src.rsplit("/", 1)[-1] for src in scripts if "learner/" in src)
    assert learner == ["atlas.js", "progress.js"]
    assert not (site_dir / site_checks.LEARNER / "path.js").exists()


# --- Accessibility, reflow, the payload ---------------------------------------------


@pytest.mark.parametrize("viewport", [WIDE, NARROW], ids=["desktop", "phone"])
def test_the_accessibility_scan_passes_with_a_course_and_a_path_open(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server)
    options = {
        "runOnly": {"type": "tag", "values": WCAG_TAGS},
        "resultTypes": ["violations"],
    }
    violations: list[str] = []
    for anchor in ("course-mechanics", "path-benchmarking", "course-fluids", "lean"):
        show(page, anchor)
        results = Axe().run(page, options=options)
        violations += [
            f"{finding['id']} at {item['target']} ({anchor})"
            for finding in results.response["violations"]
            for item in finding["nodes"]
        ]
    context.close()
    assert not violations, "\n".join(violations)


def test_the_page_reflows_at_320_pixels(browser: Browser, server: SiteServer):
    context = browser.new_context(viewport=PHONE)
    page = open_page(context, server)
    for anchor in ("course-mechanics", "path-law-discovery", "course-fluids"):
        show(page, anchor)
        assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
        right = page.locator(f"#{anchor} .atlas-panel").evaluate(
            "e => e.getBoundingClientRect().right"
        )
        assert right <= PHONE["width"]
    context.close()


def test_the_illustrations_load_at_the_density_of_the_screen(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=WIDE, device_scale_factor=2)
    page = open_page(context, server)
    sizes = page.locator("#course-mechanics img").evaluate_all(
        "images => images.map(i => [i.currentSrc.split('/').pop(),"
        " i.getBoundingClientRect().width, i.alt])"
    )
    context.close()
    (card, panel) = sizes
    # The 2x file of each slot, at the slot's width.
    assert card[0] == "mechanics-card-152.webp" and card[1] == 76
    assert card[2] == "Illustration of Classical mechanics"
    assert panel[0] == "mechanics-panel-400.webp" and panel[1] == 200
    assert panel[2] == "Illustration of Classical mechanics"


def test_the_initial_payload_of_the_page_is_within_the_budget(
    browser: Browser, server: SiteServer, capsys: pytest.CaptureFixture
):
    sizes: dict[str, int] = {}
    context = browser.new_context(viewport=WIDE, device_scale_factor=2)
    page = context.new_page()

    def record(response) -> None:
        try:
            sizes[response.url] = len(response.body())
        except Exception:  # a redirect or an aborted response has no body
            sizes.setdefault(response.url, 0)

    page.on("response", record)
    page.goto(server.url + PATH, wait_until="networkidle")
    context.close()
    total = sum(sizes.values())
    images = sum(size for url, size in sizes.items() if url.endswith(".webp"))
    with capsys.disabled():
        print(
            f"\nThe atlas at 1280 px, 2x: {total:,} bytes in {len(sizes)} files,"
            f" of which the illustrations {images:,}",
            end="",
        )
    violations = site_checks.check_payload({PATH: total})
    assert not violations, describe(violations)


# --- The relationships on a lesson page ------------------------------------------


def test_a_lesson_page_shows_its_concepts_connections_with_their_rationale(
    without_scripts: BrowserContext, server: SiteServer
):
    lesson = ATLAS.path.lesson("harmonic-oscillator")
    (concept,) = ATLAS.concepts_of(lesson)
    rationales = [
        c.rationale for c in ATLAS.manifest.connections if concept.id in c.concepts
    ]
    assert rationales
    page = without_scripts.new_page()
    page.goto(server.url + lesson.page.removesuffix(".qmd") + ".html")
    header = page.locator(".lesson-header")
    terms = header.locator("dt").all_inner_texts()
    assert "Connections" in terms
    text = header.inner_text().replace("\u2019", "'")
    for rationale in rationales:
        assert rationale.replace("\u2019", "'") in text
