"""Required checks on the course atlas of the built path page (ADR 021
decision 3 as amended on 2026-11-11, F133, Issue #483): the owner's opening
with the three derived figures, twelve sequences and the Lean entry as
native exclusive disclosures that are closed at load and expand inline
beneath their own row at every width, every published lesson reached
without JavaScript and by keyboard alone, planned lessons that are no link,
the difficulty of every row, the anchors of the previous atlas, and the
address module, which requests, stores, and sets nothing.

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
from support.site_checks import _FORBIDDEN_IN_WIDGETS, PHONE, WCAG_TAGS, describe
from support.site_server import SiteServer
from support.slots import unfilled_slots

from pbc.authoring.atlas import ATLAS_INTRODUCTION, Atlas, AtlasSection, AtlasSequence
from pbc.authoring.glossary import Glossary
from pbc.authoring.journey import Journey
from pbc.authoring.path import DIFFICULTIES, PATH_PAGE
from pbc.authoring.website import introduced, introduction_page

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
ATLAS = Atlas.read(SITE_SOURCE)
INTRODUCED = introduced(SITE_SOURCE)
SEQUENCES = ATLAS.sequences()
LESSONS = ATLAS.path.lessons
LEVELS = {difficulty.level: difficulty.title for difficulty in DIFFICULTIES}
WIDE = {"width": 1280, "height": 800}
TABLET = {"width": 768, "height": 1024}
NARROW = {"width": 390, "height": 844}
VIEWPORTS = pytest.mark.parametrize(
    "viewport", [WIDE, TABLET, NARROW], ids=["desktop", "tablet", "phone"]
)

# The anchors of the path page at the base of F133 (6627512), from the page
# its generators wrote (docs: the plan of #338, "Anchors of the base page").
# These stay ids of the page:
KEPT = [
    "atlas",
    "choose",
    "courses",
    "paths",
    "about-the-lessons",
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
# its markers and controls, the dependency map, the filters), and since Issue
# #483 the journey's headings; they reach the top of the page, which is the
# atlas.


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
    """Open the sequence ``anchor`` as a reader does, by its row."""
    if page.locator(f"#{anchor}").get_attribute("open") is None:
        page.locator(f"#{anchor} > summary").click()


def box(page: Page, selector: str) -> dict[str, float]:
    found = page.locator(selector).first.bounding_box()
    assert found is not None, selector
    return found


def boxes(page: Page, *selectors: str) -> list[dict[str, float]]:
    """The boxes of several elements in one step, so that a scroll between
    two measurements cannot put them on either side of it."""
    return page.evaluate(
        """(selectors) => selectors.map((selector) => {
            const r = document.querySelector(selector).getBoundingClientRect();
            return { x: r.x, y: r.y, width: r.width, height: r.height };
        })""",
        list(selectors),
    )


# --- The opening -----------------------------------------------------------------


def test_the_opening_is_the_subtitle_the_two_paragraphs_and_the_three_figures(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    header = page.locator("#title-block-header")
    assert header.locator("h1").inner_text() == "Course Atlas"
    assert header.locator(".description").inner_text() == (
        "From classical mechanics to AI-assisted scientific research, explore"
        " the ideas, models, and experiments that shape our understanding of"
        " the physical world."
    )
    assert page.locator(".pbc-breadcrumb").count() == 0
    assert page.locator(".atlas-opening p").all_inner_texts() == list(
        ATLAS_INTRODUCTION
    )
    figures = AtlasSection(ATLAS).figures()
    shown = page.locator(".atlas-figures li").all_inner_texts()
    assert [" ".join(text.split()) for text in shown] == [
        f"{count} {word}{'' if count == 1 else 's'}" for count, word in figures
    ]
    assert [count for count, _ in figures] == [8, 4, len(LESSONS)]
    # The opening stands before the first row; nothing of the journey is
    # left, nor the sentence with the totals.
    opening = box(page, ".atlas-figures")
    first = box(page, "#course-mechanics > summary")
    assert opening["y"] + opening["height"] <= first["y"]
    assert page.locator("#journey").count() == 0
    text = page.locator("main").inner_text()
    assert "The learning journey" not in text
    assert "lessons published and" not in text


def test_the_atlas_holds_no_journey_and_about_still_does(
    without_scripts: BrowserContext, server: SiteServer
):
    journey = Journey.read(
        SITE_SOURCE, ATLAS.path.curriculum, Glossary.read(SITE_SOURCE)
    )
    opening = journey.sections["part-a"][0][:50]
    atlas = open_page(without_scripts, server)
    assert opening not in atlas.locator("main").inner_text()
    about = without_scripts.new_page()
    about.goto(server.url + "about.html", wait_until="load")
    assert opening in about.locator("main").inner_text()


# --- The layout ------------------------------------------------------------------


@VIEWPORTS
@pytest.mark.parametrize("scripts", [True, False], ids=["scripts", "no-scripts"])
def test_every_row_is_collapsed_at_load_and_opens_inline_beneath_itself(
    browser: Browser, server: SiteServer, viewport: dict[str, int], scripts: bool
):
    context = browser.new_context(viewport=viewport, java_script_enabled=scripts)
    page = open_page(context, server)
    rows = page.locator("details.atlas-sequence > summary")
    assert rows.count() == len(SEQUENCES) == 13
    assert open_ids(page) == []
    assert (
        page.locator("#lean > summary")
        .inner_text()
        .startswith("Beyond the curriculum: proofs in Lean")
    )
    # Every row in one column.
    lefts = {round(rows.nth(i).bounding_box()["x"]) for i in range(13)}
    assert len(lefts) == 1
    for anchor, following in (
        ("course-mechanics", "course-thermodynamics"),
        ("path-benchmarking", "path-autonomous-research"),
    ):
        page.locator(f"#{anchor} > summary").click()
        assert open_ids(page) == [anchor]
        if scripts:
            # Opening scrolls the row to the top of the window; measure once
            # that has happened.
            page.wait_for_function(
                f"() => document.querySelector('#{anchor} > summary')"
                ".getBoundingClientRect().top <= window.innerHeight / 2"
            )
        row, panel, next_row = boxes(
            page,
            f"#{anchor} > summary",
            f"#{anchor} .atlas-panel",
            f"#{following} > summary",
        )
        # The content beneath its row, above the next row, inside the window's
        # width, and never beside the rows.
        assert panel["y"] >= row["y"] + row["height"] - 1
        assert next_row["y"] >= panel["y"] + panel["height"] - 1
        assert panel["x"] >= row["x"]
        assert panel["x"] < row["x"] + row["width"]
        assert panel["x"] + panel["width"] <= viewport["width"]
        assert page.locator(f"#{anchor} .atlas-row").first.is_visible()
    context.close()


@VIEWPORTS
def test_nothing_of_the_atlas_is_sticky_or_fixed(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server)
    show(page, "course-mechanics")
    positions = page.locator("#atlas *").evaluate_all(
        "items => [...new Set(items.map(e => getComputedStyle(e).position))]"
    )
    assert not {"sticky", "fixed"} & set(positions), positions
    # The stylesheet carries no wide-screen layout of the two-layer atlas.
    assert page.evaluate(
        """() => [...document.styleSheets].every((sheet) => {
            try { return ![...sheet.cssRules].some((rule) =>
                rule.cssText.includes("details-content")); }
            catch { return true; }
        })"""
    )
    context.close()


def test_the_module_keeps_one_row_open_where_the_browser_lacks_exclusive_disclosures(
    with_scripts: BrowserContext, server: SiteServer
):
    """A browser without exclusive disclosures ignores the name attribute;
    the module then closes the others. Simulated by removing the attribute."""
    page = open_page(with_scripts, server)
    page.evaluate(
        "document.querySelectorAll('details.atlas-sequence')"
        ".forEach((item) => item.removeAttribute('name'))"
    )
    page.locator("#course-mechanics > summary").click()
    page.wait_for_function("document.querySelector('#course-mechanics').open")
    page.locator("#course-quantum > summary").click()
    # The toggle event that closes the other row is queued after the click.
    page.wait_for_function(
        "document.querySelectorAll('details.atlas-sequence[open]').length === 1"
    )
    assert open_ids(page) == ["course-quantum"]


def test_the_chevron_turns_without_motion_when_the_reader_prefers_none(
    browser: Browser, server: SiteServer
):
    for preference, duration in (("no-preference", "0.15s"), ("reduce", "0s")):
        context = browser.new_context(viewport=WIDE, reduced_motion=preference)
        page = open_page(context, server)
        mark = page.locator("#course-mechanics .atlas-card-mark")
        assert mark.get_attribute("aria-hidden") == "true"
        assert mark.evaluate("e => getComputedStyle(e).transitionDuration") == duration
        before = mark.evaluate("e => getComputedStyle(e).transform")
        show(page, "course-mechanics")
        page.wait_for_timeout(300)
        assert mark.evaluate("e => getComputedStyle(e).transform") != before
        context.close()


# --- Without scripts, by keyboard ---------------------------------------------------


def test_without_scripts_every_published_lesson_is_reached_through_the_rows(
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
        # A planned row is no link and nothing in it takes the focus.
        assert planned.locator("a, button, [tabindex]").count() == 0
        for index in range(planned.count()):
            assert "planned" in planned.nth(index).inner_text()
    assert set(reached) == {lesson.id for lesson in LESSONS}


def test_each_row_shows_the_difficulty_of_its_lesson_and_the_introduction_comes_first(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_page(without_scripts, server)
    checked = 0
    for sequence in SEQUENCES:
        show(page, sequence.anchor)
        rows = page.locator(f"#{sequence.anchor} .atlas-row[data-state=published]")
        for index, row in enumerate(r for r in sequence.rows if r.lesson is not None):
            item = rows.nth(index)
            assert (
                item.locator(".atlas-level").inner_text()
                == LEVELS[row.lesson.difficulty]
            )
            checked += 1
        link = page.locator(f"#{sequence.anchor} .atlas-introduction a")
        if sequence.id in INTRODUCED:
            assert link.count() == 1
            assert link.get_attribute("href") == (
                "../" + introduction_page(sequence.id).removesuffix(".qmd") + ".html"
            )
            assert link.inner_text() == (
                "Read the course introduction"
                if sequence.part == "A"
                else "Read the method path introduction"
            )
            # Before the lessons, after the description.
            description, intro, first = boxes(
                page,
                f"#{sequence.anchor} .atlas-description",
                f"#{sequence.anchor} .atlas-introduction",
                f"#{sequence.anchor} .atlas-row",
            )
            assert description["y"] < intro["y"] < first["y"]
        else:
            assert link.count() == 0
    assert checked == len(LESSONS)
    assert INTRODUCED and any(s.id not in INTRODUCED for s in SEQUENCES if s.part)


@pytest.mark.parametrize("viewport", [WIDE, NARROW], ids=["wide", "phone"])
def test_a_paths_optional_extensions_follow_its_core_under_their_own_heading(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """The extension rows of a method path stand after its core rows, under
    the heading "Optional extensions", visible and reachable without
    scripts, with the row marks of the core and no other (ADR 022 decision
    2); the core count of the row leaves them out."""
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
        counts = f"{sequence.published} published"
        if sequence.planned:
            counts += f" · {sequence.planned} planned"
        count = page.locator(f"#{sequence.anchor} .atlas-card-count")
        assert count.inner_text() == counts
    # No row outside the core carries a mark the core does not have.
    marks = page.locator(".atlas-extensions .atlas-mark").evaluate_all(
        "marks => marks.map(m => m.className)"
    )
    assert set(marks) <= {"atlas-mark atlas-mark-planned"}
    context.close()


def first_in_order(sequence: AtlasSequence) -> str:
    """The text of the first focusable element of an open sequence: the
    introduction link where one exists, else the first published lesson."""
    if sequence.id in INTRODUCED:
        return (
            "Read the course introduction"
            if sequence.part == "A"
            else "Read the method path introduction"
        )
    return next(row for row in sequence.rows if row.lesson is not None).title


def test_by_keyboard_a_row_opens_and_its_content_comes_next_in_order(
    browser: Browser, without_scripts: BrowserContext, server: SiteServer
):
    # Safari, and WebKit with it, moves to the next link with Option-Tab
    # unless the reader turns on "Press Tab to highlight each item"; the
    # order is the same (the manual check of #338 records it in Safari).
    tab = "Alt+Tab" if browser.browser_type.name == "webkit" else "Tab"
    page = open_page(without_scripts, server)
    for key, sequence in (
        ("Enter", SEQUENCES[0]),
        ("Enter", SEQUENCES[5]),
        ("Space", by_part("B")[1]),
    ):
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
        assert page.evaluate("document.activeElement.textContent") == first_in_order(
            sequence
        )


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
    # Tab from the top of the page until the first row takes the focus.
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
        page.keyboard.press(key)
        assert open_ids(page) == [sequence.anchor], sequence.id
        if sequence.id in INTRODUCED:
            # F156: the content opens with the link to the introduction.
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
        if index + 1 < len(SEQUENCES):
            # The next Tab leaves the open row for the next summary.
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
    # A sequence with a planned capstone, read from the files rather than the
    # Atlas under test, so that publishing a slot does not change the test.
    slot = next(s for s in unfilled_slots() if "capstone" in s["kind"])
    anchor = f"course-{slot['course']}" if "course" in slot else f"path-{slot['path']}"
    show(page, anchor)
    planned = page.locator(f"#{anchor} .atlas-row.planned-slot").first
    assert "planned" in planned.inner_text()
    assert (
        planned.locator(".atlas-planned-title").evaluate(
            "e => getComputedStyle(e).fontStyle"
        )
        == "italic"
    )
    capstone = page.locator(f"#{anchor} .atlas-row-capstone")
    assert "Capstone" in capstone.inner_text()
    description = ATLAS.manifest.capstone(slot["label"]).explanation
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
    # The address module, the menu script of the shared header (F158), and
    # the learner-state script. The list says which scripts the page runs;
    # the scan below says which of them could store, so that the property
    # rests on the sources and not on a name.
    assert learner == ["atlas.js", "menu.js", "progress.js"]
    assert not (site_dir / site_checks.LEARNER / "path.js").exists()
    storage = _FORBIDDEN_IN_WIDGETS["browser storage"]
    could_store = {
        name: storage.findall(
            (site_dir / site_checks.LEARNER / name).read_text(encoding="utf-8")
        )
        for name in learner
    }
    assert {name for name, found in could_store.items() if found} == {"progress.js"}, (
        could_store
    )


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
    # The notes under the sequences, open (the completed-lessons note is
    # hidden without saved progress).
    for note in page.locator("details.atlas-note > summary").all():
        if note.is_visible():
            note.click()
    results = Axe().run(page, options=options)
    violations += [
        f"{finding['id']} at {item['target']} (notes)"
        for finding in results.response["violations"]
        for item in finding["nodes"]
    ]
    context.close()
    assert not violations, "\n".join(violations)


def test_the_page_reflows_at_320_pixels(browser: Browser, server: SiteServer):
    context = browser.new_context(viewport=PHONE)
    page = open_page(context, server)
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE["width"]
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
    show(page, "course-mechanics")
    sizes = page.locator("#course-mechanics img").evaluate_all(
        "images => images.map(i => [i.currentSrc.split('/').pop(),"
        " i.getBoundingClientRect().width, i.alt])"
    )
    context.close()
    # One illustration per sequence, the 2x file of the card slot at the
    # slot's width; the panel files are for the introduction pages.
    (card,) = sizes
    assert card[0] == "mechanics-card-152.webp" and card[1] == 76
    assert card[2] == "Illustration of Classical mechanics"


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
