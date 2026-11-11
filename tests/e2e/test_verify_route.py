"""The route of a change on the built page "How we verify the science"
(Issue #469): the section and its parts read without scripts, the counts
on the page are those of the configuration, and the rendered review of the
Issue as a check: at each of its five widths, in the light and the dark
scheme of the browser, at 100 % and 200 % text, the drawing is one image
with its title in the layout of its width and the same steps as the list
under it, every label stands inside its box with the contrast of text, and
the section fits the screen."""

import re

import pytest
from playwright.sync_api import Browser
from support.site_checks import DESKTOP, PHONE, TABLET
from support.site_server import SiteServer

from pbc.authoring.route import DIAGRAM_TITLE, GROUPS, STEPS, route_page

PAGE = "verify.html"
ROUTE = route_page()
# The widths of the rendered review of criterion 5 of the Issue.
VIEWPORTS = {
    "1280x800": DESKTOP,
    "768x1024": TABLET,
    "390x844": {"width": 390, "height": 844},
    "360x640": {"width": 360, "height": 640},
    "320x568": PHONE,
}
SCHEMES = ("light", "dark")
SCALES = (1, 2)
# The least contrast of text against its background (WCAG 2, 1.4.3).
TEXT_CONTRAST = 4.5


def _open(
    browser: Browser,
    server: SiteServer,
    viewport: dict,
    scripts: bool,
    scheme: str = "light",
):
    context = browser.new_context(
        viewport=viewport, java_script_enabled=scripts, color_scheme=scheme
    )
    page = context.new_page()
    page.goto(server.url + PAGE)
    return context, page


def _enlarge_text(page, scale: int) -> None:
    """The browser's text size, as a reader sets it: the style tag that
    enlarges the text needs scripts, so that case runs with them."""
    if scale != 1:
        page.add_style_tag(content=f"html {{ font-size: {100 * scale}% !important; }}")
    page.wait_for_timeout(100)


def _luminance(rgb: str) -> float:
    channels = [int(n) / 255 for n in re.findall(r"\d+", rgb)[:3]]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(one: str, other: str) -> float:
    a, b = sorted((_luminance(one), _luminance(other)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _within(inner: dict, outer: dict, slack: float = 0.5) -> bool:
    return (
        inner["x"] >= outer["x"] - slack
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + slack
        and inner["y"] >= outer["y"] - slack
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + slack
    )


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


@pytest.mark.parametrize("scale", SCALES, ids=["100%", "200% text"])
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("viewport", VIEWPORTS.values(), ids=VIEWPORTS.keys())
def test_the_drawing_is_shown_in_the_layout_of_the_width_with_every_step(
    browser: Browser, server: SiteServer, viewport: dict, scheme: str, scale: int
):
    """One drawing, an image with its title, in the layout of its width: two
    rows of four (wider than tall) where the figure is at least 44rem wide,
    the desktop at 100 % text, and one column (taller than wide) at every
    other width and at 200 % text, where 44rem is wider than the desktop's
    column. Every step and every label is rendered inside the drawing; a
    step's label stands inside its box; a label has the contrast of text
    against its box in the light and the dark scheme of the browser."""
    context, page = _open(browser, server, viewport, scripts=scale == 2, scheme=scheme)
    _enlarge_text(page, scale)
    drawings = page.locator("section#route-steps svg.route-diagram")
    assert drawings.count() == 1
    drawing = drawings.first
    assert drawing.get_attribute("role") == "img"
    title_id, description_id = drawing.get_attribute("aria-labelledby").split()
    assert drawing.locator(f"title[id='{title_id}']").text_content() == DIAGRAM_TITLE
    assert drawing.locator(f"desc[id='{description_id}']").count() == 1
    box = drawing.bounding_box()
    wide = viewport is DESKTOP and scale == 1
    assert (box["width"] > box["height"]) == wide, box
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
        assert _within(text.bounding_box(), box), text.text_content()
    # Each step's title and two lines stand inside its box, with the
    # contrast of text against the box's fill.
    boxes = drawing.locator("g.movable")
    assert boxes.count() == len(STEPS)
    for group in boxes.all():
        frame = group.locator("rect").bounding_box()
        fill = group.locator("rect").evaluate("r => getComputedStyle(r).fill")
        lines = group.locator("text")
        assert lines.count() == 3
        for line in lines.all():
            assert _within(line.bounding_box(), frame), line.text_content()
            ink = line.evaluate("t => getComputedStyle(t).fill")
            assert _contrast(ink, fill) >= TEXT_CONTRAST, (
                line.text_content(),
                ink,
                fill,
            )
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


@pytest.mark.parametrize("scale", SCALES, ids=["100%", "200% text"])
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("viewport", VIEWPORTS.values(), ids=VIEWPORTS.keys())
def test_the_section_fits_the_screen(
    browser: Browser, server: SiteServer, viewport: dict, scheme: str, scale: int
):
    """Every element of the section stays within the screen at each width
    of the rendered review, in both schemes, at 100 % and 200 % text."""
    context, page = _open(browser, server, viewport, scripts=scale == 2, scheme=scheme)
    _enlarge_text(page, scale)
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
