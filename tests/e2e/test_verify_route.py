"""The route of a change on the built page "How we verify the science"
(Issue #469): the section and its parts read without scripts, one drawing
of the diagram is shown at a time with its title and the same steps as the
list under it, the counts on the page are those of the configuration, and
the section fits the screen at 320 CSS px, also at 200 % text."""

import re

import pytest
from playwright.sync_api import Browser
from support.site_checks import DESKTOP, PHONE
from support.site_server import SiteServer

from pbc.authoring.route import DIAGRAM_TITLE, GROUPS, STEPS, route_page

PAGE = "verify.html"
ROUTE = route_page()


def _open(browser: Browser, server: SiteServer, viewport: dict, scripts: bool):
    context = browser.new_context(viewport=viewport, java_script_enabled=scripts)
    page = context.new_page()
    page.goto(server.url + PAGE)
    return context, page


def test_the_section_and_its_text_version_read_without_scripts(
    browser: Browser, server: SiteServer
):
    context, page = _open(browser, server, DESKTOP, scripts=False)
    section = page.locator("main section#route")
    assert section.count() == 1
    for part in ("route-steps", "route-levels", "route-checks", "route-limits"):
        assert section.locator(f"section#{part}").count() == 1, part
    items = section.locator("section#route-steps ol > li")
    assert items.count() == len(STEPS)
    leads = [
        text.replace("\u2019", "'")  # the typographic apostrophe of the page
        for text in items.locator("> strong:first-child").all_inner_texts()
    ]
    assert leads == [re.match(r"\*\*(.+?)\*\*", s.text).group(1) for s in STEPS]
    context.close()


@pytest.mark.parametrize(
    ("viewport", "layout"),
    [(DESKTOP, "wide"), (PHONE, "narrow")],
    ids=["1280x800", "320x568"],
)
def test_the_drawing_is_shown_in_the_layout_of_the_width_with_every_step(
    browser: Browser, server: SiteServer, viewport: dict, layout: str
):
    """One drawing, an image with its title: two rows of four on a desktop
    (wider than tall), one column on a phone (taller than wide); every step
    and every label is rendered, and the drawing fits the screen."""
    context, page = _open(browser, server, viewport, scripts=False)
    drawings = page.locator("section#route-steps svg.route-diagram")
    assert drawings.count() == 1
    drawing = drawings.first
    assert drawing.get_attribute("role") == "img"
    title_id, description_id = drawing.get_attribute("aria-labelledby").split()
    assert drawing.locator(f"title[id='{title_id}']").text_content() == DIAGRAM_TITLE
    assert drawing.locator(f"desc[id='{description_id}']").count() == 1
    box = drawing.bounding_box()
    assert (box["width"] > box["height"]) == (layout == "wide")
    assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5
    texts = drawing.locator("text")
    # SVG text has no innerText; its content is read as textContent.
    labels = texts.evaluate_all("ts => ts.map(t => t.textContent)")
    for step in STEPS:
        assert f"{step.number} {step.title}" in labels, step.title
    # Every text is rendered inside the drawing: nothing is hidden or moved
    # out of it by the layout.
    for text in texts.all():
        assert text.is_visible()
        inside = text.bounding_box()
        assert inside["x"] >= box["x"] - 0.5, inside
        assert inside["x"] + inside["width"] <= box["x"] + box["width"] + 0.5, inside
        assert inside["y"] >= box["y"] - 0.5, inside
        assert inside["y"] + inside["height"] <= box["y"] + box["height"] + 0.5
    context.close()


def test_the_counts_on_the_page_are_those_of_the_configuration(
    browser: Browser, server: SiteServer
):
    context, page = _open(browser, server, DESKTOP, scripts=False)
    numbers = ROUTE.facts.numbers
    steps = page.locator("section#route-steps").inner_text()
    assert f"at most {numbers['rounds']} rounds" in steps
    assert f"in {numbers['jobs']} jobs" in steps
    assert ROUTE.facts.roles.implementer in steps
    assert ROUTE.facts.roles.reviewer in steps
    checks = page.locator("section#route-checks").inner_text()
    assert f"one list of {numbers['checks']} checks" in checks
    assert f"in {numbers['jobs']} jobs" in checks
    assert f"{numbers['self_tests']} self-tests" in checks
    assert f"holds {numbers['cards']} cards" in checks
    for group in GROUPS:
        assert f"{group.title} ({len(group.checks)} checks)" in checks
    context.close()


@pytest.mark.parametrize("scale", [1, 2], ids=["100%", "200% text"])
def test_the_section_fits_a_320_px_screen(
    browser: Browser, server: SiteServer, scale: int
):
    """Every element of the section stays within the screen; the style tag
    that enlarges the text needs scripts, so that case runs with them."""
    context, page = _open(browser, server, PHONE, scripts=scale == 2)
    if scale == 2:
        page.add_style_tag(content=f"html {{ font-size: {100 * scale}% !important; }}")
    page.wait_for_timeout(100)
    outside = page.evaluate(
        """() => {
          const width = document.documentElement.clientWidth;
          const out = [];
          for (const e of document.querySelectorAll('section#route *')) {
            const r = e.getBoundingClientRect();
            if (r.width > 0 && (r.right > width + 1 || r.left < -1)) {
              out.push(e.tagName + ': ' + (e.textContent || '').slice(0, 40));
            }
          }
          return out;
        }"""
    )
    assert outside == []
    context.close()
