"""The shared header on a narrow screen (F158, round 2 of Issue #462;
docs/atelier.md, "Header"): below 640 CSS px the bar is one line (the mark,
the initials "PBC" with the full name as the link's accessible name, the
search control, and the menu toggle) and the four items are in a native
menu, closed at load with scripts, open without them; the toggle works by
pointer and keyboard, is named and exposes its state, and Escape closes the
menu with the focus back on the toggle; at 200 % text nothing in the bar
overlaps and the page does not scroll sideways; from 640 CSS px the items
stand in the bar. The same header is on every page: Home, About, and a
lesson are checked. The four-item rule and the footer are
tests/e2e/test_built_site.py's; the search's function is its own test."""

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, TABLET
from support.site_server import SiteServer

from pbc.authoring import LearningPath

TITLE = "Physics by Construction"
ITEMS = ["Home", "Course Atlas", "About", "Start learning"]
FIRST_LESSON = (
    LearningPath.read(SITE_SOURCE).lessons[0].page.removesuffix(".qmd") + ".html"
)
PAGES = ["index.html", "about.html", FIRST_LESSON]
COMPACT = [
    {"width": 320, "height": 568},
    {"width": 360, "height": 640},
    {"width": 390, "height": 844},
    {"width": 639, "height": 900},
]
WIDE = [{"width": 640, "height": 900}, TABLET, DESKTOP]
BAR = ("img.navbar-logo.light-content", ".pbc-title-short", ".pbc-menu-toggle")


def open_page(context: BrowserContext, server: SiteServer, name: str) -> Page:
    page = context.new_page()
    page.goto(server.url + name, wait_until="load")
    return page


def box(page: Page, selector: str) -> dict:
    found = page.locator(selector).bounding_box()
    assert found is not None, selector
    return found


def items(page: Page) -> list[str]:
    return [
        t.strip()
        for t in page.locator(".navbar .navbar-nav .nav-link").all_inner_texts()
    ]


def overlapping(boxes: list[dict]) -> list[tuple[int, int]]:
    """The pairs of boxes that intersect."""
    found = []
    for i, a in enumerate(boxes):
        for j, b in enumerate(boxes[i + 1 :], start=i + 1):
            if (
                a["x"] < b["x"] + b["width"]
                and b["x"] < a["x"] + a["width"]
                and a["y"] < b["y"] + b["height"]
                and b["y"] < a["y"] + a["height"]
            ):
                found.append((i, j))
    return found


@pytest.mark.parametrize("viewport", COMPACT, ids=lambda v: f"{v['width']}px")
@pytest.mark.parametrize("name", PAGES)
def test_below_640_the_bar_is_one_line_and_the_menu_is_closed(
    browser: Browser, server: SiteServer, viewport: dict, name: str
):
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server, name)
    menu = page.locator(".navbar details.pbc-menu")
    assert menu.count() == 1
    assert not menu.evaluate("m => m.open")
    for item in page.locator(".navbar .navbar-nav .nav-link").all():
        assert not item.is_visible()
    # One line: the mark, "PBC", the search control, and the toggle share a
    # row inside the bar, and nothing is past an edge.
    bar = [box(page, selector) for selector in (*BAR, ".aa-DetachedSearchButton")]
    header = box(page, "#quarto-header")
    for found in bar:
        assert found["x"] >= 0 and found["x"] + found["width"] <= viewport["width"]
        assert found["y"] >= 0
        assert found["y"] + found["height"] <= header["y"] + header["height"]
    middles = [found["y"] + found["height"] / 2 for found in bar]
    assert max(middles) - min(middles) < 12, middles
    assert overlapping(bar) == []
    assert header["height"] <= 64
    # The short form is what shows; the full name is the link's name, so a
    # reader hears it and nothing is hidden text.
    assert box(page, ".pbc-title-short")["width"] > 10
    assert box(page, ".pbc-title-full")["width"] <= 1
    assert page.get_by_role("link", name=TITLE, exact=True).count() == 2
    assert page.locator(".pbc-title-short").get_attribute("aria-hidden") == "true"
    context.close()


@pytest.mark.parametrize("name", PAGES)
def test_the_menu_opens_by_pointer_and_closes_on_escape_with_the_focus_on_the_toggle(
    browser: Browser, server: SiteServer, name: str
):
    context = browser.new_context(viewport=COMPACT[0])
    page = open_page(context, server, name)
    toggle = page.get_by_role("button", name="Menu", exact=True)
    assert toggle.count() == 1
    expect(toggle).to_have_attribute("aria-expanded", "false")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    assert page.locator(".pbc-menu").evaluate("m => m.open")
    assert items(page) == ITEMS
    links = page.locator(".navbar .navbar-nav .nav-link").all()
    for link in links:
        found = link.bounding_box()
        assert link.is_visible() and found is not None
        assert found["height"] >= 44
        assert found["x"] >= 0 and found["x"] + found["width"] <= 320
    # In a column, in order, under the bar.
    tops = [link.bounding_box()["y"] for link in links]
    assert tops == sorted(tops) and tops[0] >= box(page, ".pbc-menu-toggle")["y"] + 44
    assert page.locator(".navbar .nav-link .pbc-start").is_visible()
    page.keyboard.press("Escape")
    assert not page.locator(".pbc-menu").evaluate("m => m.open")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    assert page.evaluate("document.activeElement.className") == "pbc-menu-toggle"
    context.close()


def test_the_menu_opens_by_keyboard_and_its_entries_follow_in_the_tab_order(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=COMPACT[0])
    page = open_page(context, server, "index.html")
    for _ in range(10):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement.localName") == "summary":
            break
    else:
        raise AssertionError("the toggle did not take focus")
    assert page.evaluate("document.activeElement.closest('.navbar') !== null")
    page.keyboard.press("Enter")
    assert page.locator(".pbc-menu").evaluate("m => m.open")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.textContent.trim()") == "Home"
    page.keyboard.press("Space")
    assert page.url.endswith("index.html")  # Space on a link scrolls, no more
    page.keyboard.press("Escape")
    assert not page.locator(".pbc-menu").evaluate("m => m.open")
    assert page.evaluate("document.activeElement.localName") == "summary"
    context.close()


def test_the_toggle_is_named_and_exposes_its_state(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=COMPACT[0])
    page = open_page(context, server, "index.html")
    toggle = page.locator(".pbc-menu-toggle")
    assert toggle.get_attribute("aria-label") == "Menu"
    assert toggle.inner_text().strip() == ""  # the icon is drawn, not written
    assert toggle.aria_snapshot().strip() == '- button "Menu"'
    assert page.get_by_role("button", name="Menu", expanded=False).count() == 1
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    assert toggle.aria_snapshot().strip() == '- button "Menu" [expanded]'
    assert page.get_by_role("button", name="Menu", expanded=True).count() == 1
    # Without scripts the menu is open and the state in the HTML says so.
    page.close()
    context.close()
    context = browser.new_context(viewport=COMPACT[0], java_script_enabled=False)
    page = open_page(context, server, "index.html")
    assert page.locator(".pbc-menu-toggle").get_attribute("aria-expanded") == "true"
    context.close()


@pytest.mark.parametrize("name", PAGES)
def test_without_scripts_the_menu_stands_open_and_the_toggle_still_works(
    browser: Browser, server: SiteServer, name: str
):
    context = browser.new_context(viewport=COMPACT[0], java_script_enabled=False)
    page = open_page(context, server, name)
    assert page.locator(".pbc-menu").evaluate("m => m.open")
    assert items(page) == ITEMS
    for link in page.locator(".navbar .navbar-nav .nav-link").all():
        assert link.is_visible()
    assert page.locator(".navbar .search-fallback").is_visible()
    page.locator(".pbc-menu-toggle").click()
    assert not page.locator(".pbc-menu").evaluate("m => m.open")
    assert not page.locator(".navbar .navbar-nav .nav-link").first.is_visible()
    context.close()


@pytest.mark.parametrize("viewport", WIDE, ids=lambda v: f"{v['width']}px")
def test_from_640_the_items_stand_in_the_bar_and_the_toggle_is_hidden(
    browser: Browser, server: SiteServer, viewport: dict
):
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server, "index.html")
    assert page.locator(".pbc-menu").evaluate("m => m.open")
    assert not page.locator(".pbc-menu-toggle").is_visible()
    assert items(page) == ITEMS
    for link in page.locator(".navbar .navbar-nav .nav-link").all():
        assert link.is_visible()
    assert box(page, ".pbc-title-full")["width"] > 100
    assert box(page, ".pbc-title-short")["width"] <= 1
    assert page.get_by_role("link", name=TITLE, exact=True).count() == 2
    context.close()


def test_the_menu_follows_the_viewport(browser: Browser, server: SiteServer):
    context = browser.new_context(viewport=DESKTOP)
    page = open_page(context, server, "index.html")
    page.set_viewport_size(COMPACT[0])
    page.wait_for_timeout(100)
    assert not page.locator(".pbc-menu").evaluate("m => m.open")
    page.set_viewport_size(DESKTOP)
    page.wait_for_timeout(100)
    assert page.locator(".pbc-menu").evaluate("m => m.open")
    context.close()


@pytest.mark.parametrize(
    "viewport",
    [COMPACT[0], COMPACT[1], TABLET, DESKTOP],
    ids=["320px", "360px", "768px", "1280px"],
)
@pytest.mark.parametrize("name", ["index.html", "about.html"])
def test_at_200_percent_text_nothing_in_the_header_overlaps_and_the_page_fits(
    browser: Browser, server: SiteServer, viewport: dict, name: str
):
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server, name)
    page.add_style_tag(content="html { font-size: 200% !important; }")
    page.wait_for_timeout(100)
    # Home on a phone does not scroll sideways at 200 % text, with the menu
    # closed and open. (About's licence table, and on a tablet the theme's
    # content column and the "On this page" sidebar, are wider than the
    # screen at 200 % text by themselves, outside the header; the header's
    # parts are checked on every page and size.)
    if name == "index.html" and viewport["width"] < 640:
        assert (
            page.evaluate("document.documentElement.scrollWidth") <= viewport["width"]
        )
    if viewport["width"] < 640:
        page.locator(".pbc-menu-toggle").click()
        expect(page.locator(".pbc-menu-toggle")).to_have_attribute(
            "aria-expanded", "true"
        )
    if name == "index.html" and viewport["width"] < 640:
        assert (
            page.evaluate("document.documentElement.scrollWidth") <= viewport["width"]
        )
    parts = {
        f"{index}: {element.evaluate('e => e.className')}": element.bounding_box()
        for index, element in enumerate(
            page.locator(
                ".navbar img.navbar-logo.light-content, .navbar .navbar-title,"
                " .navbar .nav-link, .navbar .pbc-menu-toggle,"
                " .navbar .aa-DetachedSearchButton, .navbar #quarto-search input"
            ).all()
        )
        if element.is_visible()
    }
    assert len(parts) >= 6
    assert overlapping(list(parts.values())) == []
    for name, found in parts.items():
        assert found["x"] >= -0.5, name
        assert found["x"] + found["width"] <= viewport["width"] + 0.5, (name, found)
    context.close()


@pytest.mark.parametrize("viewport", COMPACT[:3], ids=lambda v: f"{v['width']}px")
@pytest.mark.parametrize("name", PAGES)
def test_at_200_percent_text_the_bar_is_still_one_line_on_a_phone(
    browser: Browser, server: SiteServer, viewport: dict, name: str
):
    """The owner's correction of 2026-11-10 (round 2, third part): at 320
    by 568 with 200 % text the search control fell onto a second line and
    the header was 134 px tall. The bar's gaps are capped like its gutter
    (site.css, --pbc-bar-gap), so the mark, "PBC", the search control, and
    the toggle share the one row at 320, 360, and 390 px, with the toggle's
    44 px target, every accessible name, the search, and the page's width
    kept."""
    context = browser.new_context(viewport=viewport)
    page = open_page(context, server, name)
    page.add_style_tag(content="html { font-size: 200% !important; }")
    page.wait_for_timeout(100)
    mark, title, toggle, search = (
        box(page, selector) for selector in (*BAR, ".aa-DetachedSearchButton")
    )
    bar = [mark, title, toggle, search]
    header = box(page, "#quarto-header")
    # One row: the middles within 12 px as at 100 %, and every part's middle
    # inside every other part's vertical extent (a second line put the
    # search control's middle 60 px under the mark's box); left to right
    # the mark, "PBC", the search, the toggle, none overlapping, none past
    # an edge of the screen or the header, and the header not two rows
    # tall (74 px, the title's line at 200 %; it was 134 px).
    middles = [found["y"] + found["height"] / 2 for found in bar]
    assert max(middles) - min(middles) < 12, middles
    for found in bar:
        for middle in middles:
            assert found["y"] <= middle <= found["y"] + found["height"], (
                found,
                middles,
            )
    edges = [
        mark["x"] + mark["width"],
        title["x"],
        title["x"] + title["width"],
        search["x"],
        search["x"] + search["width"],
        toggle["x"],
    ]
    assert edges == sorted(edges), edges
    assert overlapping(bar) == []
    for found in bar:
        assert found["x"] >= 0 and found["x"] + found["width"] <= viewport["width"]
        assert found["y"] >= 0
        assert found["y"] + found["height"] <= header["y"] + header["height"]
    assert header["height"] <= 80, header
    # Nothing traded for the line: the toggle's target, the names, the
    # search control, and the width of Home.
    assert toggle["width"] >= 44 and toggle["height"] >= 44
    assert page.get_by_role("button", name="Menu", exact=True).count() == 1
    assert page.get_by_role("button", name="Search", exact=True).is_visible()
    assert page.get_by_role("link", name=TITLE, exact=True).count() == 2
    if name == "index.html":
        assert (
            page.evaluate("document.documentElement.scrollWidth") <= viewport["width"]
        )
    context.close()
