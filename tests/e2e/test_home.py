"""The built home page (F134, F158; ADR 021 decision 4 as amended): the hero
with the owner's one fixed headline and subtext (Issues #462 and #481), the
same with and without scripts and after a reload, over one large
fluid-dynamics illustration (Issue #482): one image in the HTML, no script
in the hero, exactly one hero file requested per load, the one sized for
the viewport; no layout shift from the image; no storage; no rectangular
boundary on the render and the text's contrast over the fading image,
measured; the layout rule of "Home page" at 1280 by 800, 768 by 1024, 390 by
844, 360 by 640, and 320 CSS px and at 200 % text; the two actions with the
header's destinations; the four sections of the owner's copy in order
(Issue #481), Part A with its course subjects, no example lesson, every
link generated from data and reaching its target.
The accessibility scan, the keyboard pass, the reflow at 320 CSS px, and
the payload budget are the checks every page gets
(tests/e2e/test_built_site.py)."""

import io
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
import pytest
from PIL import Image
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import LearningPath
from pbc.authoring.design import PAGE
from pbc.authoring.home import (
    ATLAS_ACTION,
    FIRST_LESSON_ACTION,
    HERO_IMAGES,
    SECTIONS,
    SUBJECTS_LABEL,
    HeroCopy,
)
from pbc.authoring.path import COURSES

LESSONS = LearningPath.read(SITE_SOURCE)
HERO = HeroCopy.read(SITE_SOURCE)
TABLET = {"width": 768, "height": 1024}
PHONE_TALL = {"width": 390, "height": 844}
PHONE_SMALL = {"width": 360, "height": 640}
PHONE_NARROW = {"width": 320, "height": 568}
APOSTROPHE = chr(0x2019)
# The share of the hero's width the image takes from 992 CSS px (the
# owner's 70 to 80 %; site.css draws it at 78 %), and the share of the image
# the copy's column may lie over (the left 31 %, where the file's matte
# keeps the ink at a quarter at most).
_IMAGE_SHARE = (0.70, 0.80)
_UNDER_THE_COPY = 0.32
_WIDE = 992


def typographic(text: str) -> str:
    return text.replace("'", APOSTROPHE)


@pytest.fixture
def without_scripts(browser: Browser):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


def open_home(context: BrowserContext, server: SiteServer, query: str = "") -> Page:
    page = context.new_page()
    page.goto(server.url + "index.html" + query, wait_until="load")
    return page


def built(lesson_page: str, server: SiteServer) -> str:
    return server.url + lesson_page.removesuffix(".qmd") + ".html"


def hrefs(locator) -> list[str]:
    return locator.evaluate_all("links => links.map(a => a.href)")


FIXED = (typographic(HERO.headline), typographic(HERO.subtext))


def shown(page: Page) -> tuple[str, str]:
    return (
        page.locator("main h1").inner_text(),
        page.locator(".hero-copy .hero-subtext").inner_text(),
    )


def hero_requests(requests: list[str], server: SiteServer) -> list[str]:
    """The hero images among the requested addresses, by file name."""
    prefix = urlsplit(server.url + HERO_IMAGES + "/").path
    return [
        path.removeprefix(prefix)
        for path in (unquote(urlsplit(url).path) for url in requests)
        if path.startswith(prefix)
    ]


def _hero(page: Page) -> tuple[str, str, list[str]]:
    """The hero as rendered: the copy's and the figure's HTML, and the two
    actions as text with their resolved targets (the theme's own script
    rewrites an href to its absolute form; the target is what matters)."""
    return (
        page.locator(".hero-copy").evaluate("e => e.innerHTML"),
        page.locator(".hero-figure").evaluate("e => e.innerHTML"),
        page.locator(".home-hero a").evaluate_all(
            "links => links.map(a => a.textContent + ' ' + a.href)"
        ),
    )


# --- The hero's copy -----------------------------------------------------------


def test_without_scripts_the_page_has_the_fixed_text_the_image_and_one_h1(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    assert page.locator("h1").count() == 1
    assert shown(page) == FIXED
    assert page.locator(".hero-copy .hero-subtext").count() == 1
    assert page.title() == "Physics by Construction"
    description = page.locator('meta[name="description"]').get_attribute("content")
    assert description and "Physics taught by constructing it" in description
    ids = page.locator("main section.level2").evaluate_all(
        "sections => sections.map(s => s.id)"
    )
    assert ids == [anchor for _, anchor in SECTIONS]
    # The image, from the HTML, shown and loaded.
    image = page.locator(".hero-figure img.hero-image")
    assert image.count() == 1
    assert image.get_attribute("alt") == typographic(HERO.image.alt)
    assert image.evaluate("i => i.complete && i.naturalWidth > 0")
    assert image.is_visible()


def test_the_hero_is_the_same_with_scripts_after_a_reload_and_whatever_is_asked(
    browser: Browser, server: SiteServer, without_scripts: BrowserContext
):
    """One headline, one subtext, one image, the owner's (round 2 of Issue
    #462; Issue #482): the page with scripts shows the same hero as the page
    without, after every reload, and the old `hero` and `hero-image`
    parameters change nothing."""
    static = _hero(open_home(without_scripts, server))
    context = browser.new_context(viewport=DESKTOP)
    page = open_home(context, server)
    for _ in range(3):
        assert shown(page) == FIXED
        assert page.locator("h1").count() == 1
        assert page.locator(".hero-copy *").count() == 2  # the h1 and the subtext
        assert _hero(page) == static
        page.reload(wait_until="networkidle")
    for query in ("?hero=2b", "?hero=3a&hero-image=double-pendulum", "?hero=9z"):
        page = open_home(context, server, query)
        assert shown(page) == FIXED
        assert _hero(page) == static
        page.close()
    context.close()


# --- The hero image ------------------------------------------------------------


def test_the_hero_holds_no_script_and_the_image_is_in_the_html(
    without_scripts: BrowserContext, server: SiteServer
):
    """Nothing in the hero runs or blocks: no script and no <noscript>; the
    image is an ordinary <img> with its srcset, found by the preload scanner,
    asked for first and never lazy."""
    page = open_home(without_scripts, server)
    assert page.locator(".home-hero script, .home-hero noscript").count() == 0
    assert page.locator('script[src*="hero"]').count() == 0
    image = page.locator(".hero-figure > img.hero-image")
    assert image.count() == 1
    assert image.get_attribute("srcset") and image.get_attribute("sizes")
    assert image.get_attribute("fetchpriority") == "high"
    assert image.get_attribute("loading") is None


def load_recorded(
    browser: Browser,
    server: SiteServer,
    viewport: dict[str, int] = DESKTOP,
    scale: float = 1,
) -> tuple[Page, BrowserContext, list[str]]:
    requests: list[str] = []
    context = browser.new_context(viewport=viewport, device_scale_factor=scale)
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    page.goto(server.url + "index.html", wait_until="networkidle")
    return page, context, requests


@pytest.mark.parametrize(
    ("viewport", "scale", "width"),
    [
        (DESKTOP, 1, 1200),
        (DESKTOP, 2, 1800),
        (TABLET, 2, 1800),
        (PHONE_TALL, 3, 1200),
    ],
    ids=["1280x800@1x", "1280x800@2x", "768x1024@2x", "390x844@3x"],
)
def test_the_page_requests_the_one_file_sized_for_the_viewport(
    browser: Browser,
    server: SiteServer,
    site_dir: Path,
    viewport: dict[str, int],
    scale: float,
    width: int,
):
    """Exactly one hero file per load, the smallest of the srcset that
    covers the image's drawn width at the screen's pixel density (78 % of
    the hero from 992 CSS px, the whole width below), within the per-file
    budget. (That the page stores nothing and sets no cookie is the check
    every page gets, tests/e2e/test_built_site.py; the hero adds no
    script.)"""
    page, context, requests = load_recorded(browser, server, viewport, scale)
    page.wait_for_timeout(200)
    assert hero_requests(requests, server) == [f"{HERO.image.id}-{width}.webp"]
    current = page.locator(".hero-image").evaluate("i => i.currentSrc")
    assert current.endswith(f"/{HERO.image.id}-{width}.webp")
    size = (site_dir / HERO.image.file(width)).stat().st_size
    assert 0 < size <= 100_000
    context.close()


# Where the hero's parts stand, relative to the hero, and the hero itself.
_BOXES = """
() => {
  const hero = document.querySelector(".home-hero").getBoundingClientRect();
  const at = (selector) => {
    const box = document.querySelector(selector).getBoundingClientRect();
    return [box.x - hero.x, box.y - hero.y, box.width, box.height];
  };
  return {
    hero: [hero.width, hero.height],
    copy: at(".hero-copy"),
    actions: at(".home-hero .home-actions"),
    figure: at(".hero-figure"),
    next: at("#about-the-site"),
  };
}
"""


@pytest.mark.parametrize(
    "viewport", [DESKTOP, TABLET, PHONE_TALL], ids=["desktop", "tablet", "phone"]
)
def test_the_image_moves_nothing_when_it_arrives_and_the_h1_does_not_change(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """Layout stability: the page laid out with the hero files blocked (the
    box reserved by the image's dimensions and the figure's aspect ratio)
    is the page laid out with the image drawn, to the pixel; the headline
    is the same at load and after."""
    # The web fonts swap in after the first paint and move the text by
    # themselves, image or not; without them the layout depends on the
    # image alone.
    layouts = []
    for blocked in (True, False):
        context = browser.new_context(viewport=viewport)
        context.route("**/*.woff2", lambda route: route.abort())
        if blocked:
            context.route(f"**/{HERO_IMAGES}/*", lambda route: route.abort())
        page = open_home(context, server)
        at_load = page.locator("h1").inner_text()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert page.locator("h1").inner_text() == at_load == FIXED[0]
        loaded = page.locator(".hero-image").evaluate("i => i.naturalWidth > 0")
        assert loaded is not blocked
        layouts.append(page.evaluate(_BOXES))
        context.close()
    assert layouts[0] == layouts[1], layouts
    figure = layouts[0]["figure"]
    assert abs(figure[3] - figure[2] / 2) < 1


# --- The layout ------------------------------------------------------------------


def _box(page: Page, selector: str) -> dict:
    box = page.locator(selector).bounding_box()
    assert box is not None, selector
    return box


_MESSAGE = ("main h1", ".hero-copy .hero-subtext")
_PRIMARY = ".home-hero .home-action-primary"
_SECONDARY = ".home-hero .home-action"
# The least room between the primary action and the fold on the smallest
# phones: a reasonable margin (the owner, round 2), far under the measured
# one, so that no face decides it.
_MARGIN = 24


@pytest.mark.parametrize(
    ("viewport", "visible", "margin"),
    [
        (DESKTOP, (*_MESSAGE, _PRIMARY, _SECONDARY), 0),
        (TABLET, (*_MESSAGE, _PRIMARY, _SECONDARY), 0),
        (PHONE_TALL, (*_MESSAGE, _PRIMARY, _SECONDARY), 0),
        (PHONE_SMALL, (*_MESSAGE, _PRIMARY), _MARGIN),
        (PHONE_NARROW, (*_MESSAGE, _PRIMARY), _MARGIN),
    ],
    ids=["1280x800", "768x1024", "390x844", "360x640", "320x568"],
)
def test_the_message_and_the_actions_are_above_the_fold(
    browser: Browser,
    server: SiteServer,
    viewport: dict[str, int],
    visible: tuple,
    margin: int,
):
    """On a desktop, a tablet, and a phone of 390 by 844 the identity message
    and both actions; at 360 by 640 and 320 by 568 the message and the
    primary action, which ends a reasonable margin above the fold, while the
    secondary may fall just below it (the owner's decisions of 2026-11-10 and
    round 2 of Issue #462). The image is never moved or shrunk for this: the
    ground of the hero at 70 to 80 % of its width on a desktop (Issue #482),
    the whole column right after the actions below 992 CSS px."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    for selector in visible:
        box = _box(page, selector)
        assert box["y"] >= 0, selector
        assert box["y"] + box["height"] + margin <= viewport["height"], selector
    figure = _box(page, ".hero-figure")
    hero = _box(page, ".home-hero")
    if viewport["width"] >= _WIDE:
        share = figure["width"] / hero["width"]
        assert _IMAGE_SHARE[0] <= share <= _IMAGE_SHARE[1], share
        assert abs(figure["x"] + figure["width"] - hero["x"] - hero["width"]) < 1
    else:
        assert abs(figure["width"] - hero["width"]) < 1
    context.close()


# The share of the image's height that is above the fold at 390 by 844: a
# substantial, recognisable part (the owner, round 2 of Issue #462). On the
# render the whole image is in view there; 40 % leaves room for the faces
# of another machine, and a few pixels or an edge cannot pass.
_RECOGNISABLE = 0.4


@pytest.mark.parametrize(
    "viewport", [DESKTOP, TABLET, PHONE_TALL], ids=["1280x800", "768x1024", "390x844"]
)
def test_the_image_is_in_view_from_390_by_844_up(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """On a desktop, a tablet, and a phone from 390 by 844 up the hero image
    is in view without scrolling: its top on the screen, at least 40 % of
    its height above the fold, the whole image on a desktop."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    figure = _box(page, ".hero-figure")
    assert figure["y"] >= 0
    visible = min(figure["y"] + figure["height"], viewport["height"]) - figure["y"]
    assert visible >= _RECOGNISABLE * figure["height"], visible
    assert visible >= 150
    if viewport is DESKTOP:
        assert figure["y"] + figure["height"] <= viewport["height"]
    context.close()


def _image(page: Page) -> dict:
    """The displayed and the natural size of the hero image, and whether it
    is drawn whole: loaded, visible, and not cropped by fit or overflow."""
    return page.locator(".hero-figure img").evaluate(
        """i => {
            const s = getComputedStyle(i), f = getComputedStyle(i.parentElement);
            const r = i.getBoundingClientRect();
            return {width: r.width, height: r.height,
                    natural: [i.naturalWidth, i.naturalHeight],
                    loaded: i.complete && i.naturalWidth > 0,
                    shown: s.display !== "none" && s.visibility === "visible"
                           && parseFloat(s.opacity) > 0,
                    fit: s.objectFit, clip: f.overflow};
        }"""
    )


@pytest.mark.parametrize(
    "viewport", [PHONE_SMALL, PHONE_NARROW], ids=["360x640", "320x568"]
)
def test_on_the_smallest_phones_the_image_follows_whole_and_unshrunk(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """The owner's decision of 2026-11-10 (option C): at 360 by 640 and
    320 by 568 the image may follow below the fold, but it is never weakened
    for it: present, after the actions, uncropped (its natural aspect, drawn
    whole), and unshrunk (the displayed size it has at 390 wide, scaled by
    the width: the full width of the content column, as there)."""
    context = browser.new_context(viewport=PHONE_TALL)
    reference = open_home(context, server)
    tall = _image(reference)
    tall_column = _box(reference, ".home-hero")["width"]
    context.close()
    assert abs(tall["width"] - tall_column) < 1
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    image = _image(page)
    assert image["loaded"] and image["shown"]
    # Uncropped: drawn in its natural aspect, so neither the fit nor the
    # figure cuts anything off.
    assert image["fit"] != "none" and image["clip"] == "visible"
    natural_ratio = image["natural"][1] / image["natural"][0]
    assert abs(image["height"] - image["width"] * natural_ratio) < 1
    # Scaled by the width only: the same share of the column as at 390.
    column = _box(page, ".home-hero")["width"]
    assert abs(image["width"] - tall["width"] * column / tall_column) < 1
    actions = _box(page, ".home-hero .home-actions")
    figure = _box(page, ".hero-figure")
    assert actions["y"] + actions["height"] <= figure["y"] + 0.5
    context.close()


def _font_size(page: Page, selector: str) -> float:
    return page.locator(selector).evaluate(
        "e => parseFloat(getComputedStyle(e).fontSize)"
    )


def _words(page: Page, selector: str) -> list[tuple[str, int, float, float]]:
    """Each word of the element's text with the number of line boxes it is
    drawn in (two when it is broken inside) and its left and right edge."""
    return page.locator(selector).evaluate(
        """e => {
            const words = [];
            const walk = node => {
                if (node.nodeType !== Node.TEXT_NODE) {
                    node.childNodes.forEach(walk);
                    return;
                }
                for (const match of node.textContent.matchAll(/\\S+/g)) {
                    const range = document.createRange();
                    range.setStart(node, match.index);
                    range.setEnd(node, match.index + match[0].length);
                    const rects = [...range.getClientRects()].filter(r => r.width > 0);
                    words.push([match[0], rects.length,
                                Math.min(...rects.map(r => r.left)),
                                Math.max(...rects.map(r => r.right))]);
                }
            };
            walk(e);
            return words;
        }"""
    )


# How much larger the headline is at 200 % text than at 100 %, by the
# screen's width: at 320 CSS px the column at 200 % is 212 px wide and
# holds the longest word ("intelligence.", 5.6 em) at 1.27 times the phone
# size at most; from 360 px the column allows 1.4 and more (measured 1.48
# at 360, 1.66 at 390, 1.41 on the desktop, where the size is CSS
# arithmetic in rem and vw).
_ENLARGED = {320: 1.2, None: 1.35}


def _enlarge(page: Page, scale: int) -> None:
    if scale != 1:
        page.add_style_tag(content=f"html {{ font-size: {100 * scale}% !important; }}")
        page.wait_for_timeout(100)


@pytest.mark.parametrize(
    "viewport",
    [DESKTOP, PHONE_TALL, PHONE_SMALL, PHONE_NARROW],
    ids=["1280x800", "390x844", "360x640", "320x568"],
)
@pytest.mark.parametrize("scale", [1, 2], ids=["100%", "200% text"])
def test_the_hero_reflows_without_overlap_at_every_size_and_at_200_percent_text(
    browser: Browser, server: SiteServer, viewport: dict[str, int], scale: int
):
    """At every size, and with the text twice as large: no horizontal scroll,
    the copy and the actions do not overlap, and on a wide screen they lie
    over the faint end of the image's trail only (its left third; Issue
    #482) while below 992 CSS px the image follows the actions; the reading
    order is the copy, then the two actions, then the image; the headline
    keeps its size at normal text and is enlarged at 200 % with no word of
    the copy broken inside; both actions can be reached with the keyboard."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    normal = _font_size(page, "main h1")
    _enlarge(page, scale)
    # The page's content is no wider than its column, and the page, with the
    # shared header, no wider than the screen.
    main = page.locator("main").evaluate("m => [m.scrollWidth, m.clientWidth]")
    assert main[0] <= main[1], main
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= viewport["width"]
    copy = _box(page, ".hero-copy")
    actions = _box(page, ".home-hero .home-actions")
    figure = _box(page, ".hero-figure")
    assert copy["y"] + copy["height"] <= actions["y"] + 0.5
    if viewport["width"] >= _WIDE:
        # Over the faint end of the trail only: the copy and the actions end
        # within the left third of the image, whatever the text size.
        for box in (copy, actions):
            under = (box["x"] + box["width"] - figure["x"]) / figure["width"]
            assert under <= _UNDER_THE_COPY, under
    else:
        assert actions["y"] + actions["height"] <= figure["y"] + 0.5
    for box in (copy, actions, figure):
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5
    # At normal text the headline keeps its size, at least the phone size;
    # at 200 % it is enlarged, by at least the ratio of its column (the
    # owner's correction of round 2: smaller by size on a narrow column
    # instead of broken words).
    size = _font_size(page, "main h1")
    if scale == 1:
        assert size >= 28 - 0.5
    else:
        assert size >= _ENLARGED.get(viewport["width"], _ENLARGED[None]) * normal
    # No word of the headline or the subtext is broken inside: each is on
    # one line, within the copy's column.
    for selector in ("main h1", ".hero-copy .hero-subtext"):
        for word, pieces, left, right in _words(page, selector):
            assert pieces == 1, (selector, word, size)
            assert left >= copy["x"] - 0.5 and right <= copy["x"] + copy["width"] + 0.5
    # Both actions are links in the tab order, the primary first.
    order = page.evaluate(
        "() => [...document.querySelectorAll('.home-hero a')]"
        ".map(a => [a.className, a.tabIndex])"
    )
    assert order == [["home-action-primary", 0], ["home-action", 0]]
    context.close()


# --- The image on the render: no boundary, and the text's contrast ----------------


def _channel(value: np.ndarray) -> np.ndarray:
    value = value / 255
    return np.where(value <= 0.03928, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def _luminance(pixels: np.ndarray) -> np.ndarray:
    """The relative luminance (WCAG 2.1) of each pixel of an RGB array."""
    return (
        0.2126 * _channel(pixels[..., 0])
        + 0.7152 * _channel(pixels[..., 1])
        + 0.0722 * _channel(pixels[..., 2])
    )


def _pixels(page: Page, box: dict) -> np.ndarray:
    """The rendered pixels of ``box`` (CSS px at scale 1), as RGB."""
    clip = {key: max(0.0, box[key]) for key in ("x", "y")}
    clip |= {"width": box["width"], "height": box["height"]}
    shot = page.screenshot(clip=clip, full_page=True)
    return np.asarray(Image.open(io.BytesIO(shot)).convert("RGB"))


def _colour(page: Page, selector: str) -> str:
    """The computed text colour of the element, as #rrggbb."""
    return page.locator(selector).evaluate(
        """e => {
            const [r, g, b] = getComputedStyle(e).color.match(/\\d+/g).map(Number);
            return "#" + [r, g, b].map(v => v.toString(16).padStart(2, "0")).join("");
        }"""
    )


def _ratio(text: str, backdrop_luminance: float) -> float:
    pixel = np.array([[int(text[i : i + 2], 16) for i in (1, 3, 5)]], dtype=float)
    lighter, darker = sorted((float(_luminance(pixel)[0]), backdrop_luminance))
    return (darker + 0.05) / (lighter + 0.05)


PAPER = np.array([int(PAGE["background"][i : i + 2], 16) for i in (1, 3, 5)])


@pytest.mark.parametrize(
    "viewport",
    [DESKTOP, TABLET, PHONE_TALL, PHONE_SMALL, PHONE_NARROW],
    ids=["1280x800", "768x1024", "390x844", "360x640", "320x568"],
)
def test_the_image_has_no_rectangular_boundary_on_the_render(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    """Every pixel along the four edges of the image's box is the paper, at
    every size (the fade is in the file; on a wide screen the copy over the
    box is made transparent first), while the image is there: the
    cylinder, the darkest part, is drawn inside the box."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    page.wait_for_load_state("networkidle")
    figure = _box(page, ".hero-figure")
    page.add_style_tag(
        content=".hero-copy, .home-hero .home-actions { visibility: hidden; }"
    )
    page.wait_for_timeout(100)
    pixels = _pixels(page, figure)
    for edge in (pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]):
        assert np.abs(edge.astype(int) - PAPER).max() <= 3, edge
    assert _luminance(pixels).min() < 0.2
    context.close()


# The least contrast of the text against the darkest pixel behind its box:
# 4.5 for the subtext and the links (WCAG AA for text), 3 for the headline
# (large text).
_CONTRAST = {
    "main h1": 3.0,
    ".hero-copy .hero-subtext": 4.5,
    _PRIMARY: 4.5,
    _SECONDARY: 4.5,
}


@pytest.mark.parametrize(
    "viewport",
    [DESKTOP, TABLET, PHONE_TALL, PHONE_SMALL, PHONE_NARROW],
    ids=["1280x800", "768x1024", "390x844", "360x640", "320x568"],
)
@pytest.mark.parametrize("scale", [1, 2], ids=["100%", "200% text"])
def test_the_text_keeps_its_contrast_over_the_fading_image(
    browser: Browser, server: SiteServer, viewport: dict[str, int], scale: int
):
    """Measured where the text meets the image, not assumed (Issue #482):
    with the text made transparent, the darkest pixel behind the box of
    the headline, the subtext, and each action still gives the text's
    colour the contrast WCAG asks for, at every size and at 200 % text."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server)
    page.wait_for_load_state("networkidle")
    _enlarge(page, scale)
    colours = {selector: _colour(page, selector) for selector in _CONTRAST}
    boxes = {selector: _box(page, selector) for selector in _CONTRAST}
    page.add_style_tag(
        content=", ".join(_CONTRAST) + " { color: transparent !important; }"
    )
    page.wait_for_timeout(100)
    for selector, least in _CONTRAST.items():
        darkest = float(_luminance(_pixels(page, boxes[selector])).min())
        ratio = _ratio(colours[selector], darkest)
        assert ratio >= least, (selector, colours[selector], darkest, ratio)
    context.close()


# --- The first step ---------------------------------------------------------------


def test_home_and_the_header_give_the_same_two_destinations(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    primary = page.locator(".home-hero a.home-action-primary")
    secondary = page.locator(".home-hero a.home-action")
    assert primary.inner_text() == ATLAS_ACTION
    assert secondary.inner_text() == FIRST_LESSON_ACTION
    header_atlas = page.locator(".navbar .nav-link", has_text="Course Atlas")
    header_start = page.locator(".navbar .nav-link:has(.pbc-start)")
    assert hrefs(primary) == hrefs(header_atlas)
    assert hrefs(secondary) == hrefs(header_start)
    first = LESSONS.in_course(LESSONS.courses[0])[0]
    assert hrefs(secondary) == [built(first.page, server)]
    assert hrefs(primary) == [server.url + "path/index.html"]
    # The primary is the one filled control of the page.
    assert page.locator("main .home-action-primary").count() == 1


# --- The rest of the page ----------------------------------------------------------


def test_part_a_names_its_subjects_and_no_example_lesson_is_shown(
    without_scripts: BrowserContext, server: SiteServer
):
    """The course subjects after Part A's text, as one list in the order of
    the curriculum, plain names; no example lesson or preview on Home
    (Issue #481): lesson discovery belongs to the Course Atlas."""
    page = open_home(without_scripts, server)
    section = page.locator("main section#what-you-can-learn")
    subjects = section.locator("ul.home-subjects")
    assert subjects.count() == 1
    assert subjects.get_attribute("aria-label") == SUBJECTS_LABEL
    assert subjects.locator("li").all_inner_texts() == [c.title for c in COURSES]
    assert subjects.locator("a").count() == 0
    assert section.locator(".home-part-a ul.home-subjects").count() == 1
    assert section.locator("a, img").count() == 0
    assert page.locator("main .home-example, main img.home-preview").count() == 0


def test_every_link_of_the_page_content_reaches_its_target(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    links = hrefs(page.locator("main a"))
    assert server.url + "about.html#creator-and-jidai" in links
    assert server.url + "verify.html" in links
    for link in links:
        if not link.startswith(server.url):
            continue
        address, _, fragment = link.partition("#")
        target = without_scripts.new_page()
        assert target.goto(address).ok, link
        if fragment:
            assert target.locator(f"[id='{fragment}']").count() == 1, link
        target.close()


def test_the_page_tells_one_story_in_the_order_of_the_copy_file(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    text = page.locator("main").inner_text()
    assert "From a question to a working model" not in text
    assert "lessons published" not in text
    headings = page.locator("main h2").all_inner_texts()
    assert headings == [
        "What is Physics by Construction?",
        "Build. Experiment. Understand.",
        "From computational physics to artificial intelligence",
        "How we verify what we teach",
    ]
    assert page.locator("main h3").all_inner_texts() == [
        "Part A \u2014 Computational and experimental physics",
        "Part B \u2014 Can AI help us discover new physics?",
        "First understand the physics. Then challenge the AI.",
    ]
    # No constellation and no inline image in the hero.
    assert page.locator(".home-hero svg").count() == 0
