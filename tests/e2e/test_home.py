"""The built home page (F134, F158; ADR 021 decision 4 as amended): the hero
with the owner's one fixed headline and subtext (Issues #462 and #481), the
same with and without scripts and after a reload, and one of the four Part A
illustrations, forced by the `hero-image` parameter or picked at random,
exactly one hero image requested per load; the default image without
scripts; one <h1> that does not change after load; no layout shift; no
request beyond the image and no storage by its script; the layout rule of
"Home page" at 1280 by 800, 768 by 1024, 390 by 844, 360 by 640, and 320
CSS px and at 200 % text; the two actions with the header's destinations;
the four sections of the owner's copy in order (Issue #481), Part A with its
course subjects, no example lesson, every link generated from data and
reaching its target.
The accessibility scan, the keyboard pass, the reflow at 320 CSS px, and
the payload budget are the checks every page gets
(tests/e2e/test_built_site.py)."""

from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import _RECORD_STORAGE_WRITES, _STORAGE_ENTRIES, DESKTOP
from support.site_server import SiteServer

from pbc.authoring import LearningPath
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
IMAGES = [image.id for image in HERO.images]
TABLET = {"width": 768, "height": 1024}
PHONE_TALL = {"width": 390, "height": 844}
PHONE_SMALL = {"width": 360, "height": 640}
PHONE_NARROW = {"width": 320, "height": 568}
APOSTROPHE = chr(0x2019)


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


def load_recorded(
    browser: Browser, server: SiteServer, query: str, viewport=DESKTOP
) -> tuple[Page, BrowserContext, list[str]]:
    requests: list[str] = []
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    page.goto(server.url + "index.html" + query, wait_until="networkidle")
    return page, context, requests


# --- The hero's copy -----------------------------------------------------------


def test_without_scripts_the_page_has_the_fixed_text_the_default_image_and_one_h1(
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
    # The default image, from <noscript>, shown and loaded.
    image = page.locator(".hero-figure img.hero-image")
    assert image.count() == 1
    image_default = HERO.image(HERO.default_image)
    assert image.get_attribute("src") == image_default.file
    assert image.get_attribute("alt") == typographic(image_default.alt)
    assert image.evaluate("i => i.complete && i.naturalWidth === 1200")
    assert image.is_visible()


def test_the_hero_text_is_fixed_with_scripts_after_a_reload_and_whatever_is_asked(
    browser: Browser, server: SiteServer
):
    """One headline and one subtext, the owner's (round 2 of Issue #462): the
    page with scripts shows the same text as the page without, after every
    reload, and the old `hero` parameter of the pairs changes nothing."""
    context = browser.new_context(viewport=DESKTOP)
    page = open_home(context, server)
    for _ in range(3):
        assert shown(page) == FIXED
        assert page.locator("h1").count() == 1
        assert page.locator(".hero-copy *").count() == 2  # the h1 and the subtext
        page.reload(wait_until="networkidle")
    for query in ("?hero=2b", "?hero=3a&hero-image=vortex-street", "?hero=9z"):
        page = open_home(context, server, query)
        assert shown(page) == FIXED
        assert page.locator(".hero-copy *").count() == 2
        page.close()
    context.close()


# --- The hero image ------------------------------------------------------------


@pytest.mark.parametrize("image_id", IMAGES)
def test_the_image_parameter_shows_each_image_with_exactly_one_request(
    browser: Browser, server: SiteServer, site_dir: Path, image_id: str
):
    """Each image's own browser test: the parameter forces it, with its alt
    text, as the one hero image the page requests; its bytes are counted."""
    page, context, requests = load_recorded(browser, server, f"?hero-image={image_id}")
    image = HERO.image(image_id)
    shown_image = page.locator(".hero-figure img.hero-image")
    assert shown_image.count() == 1
    assert page.locator("img.hero-image").count() == 1
    assert shown_image.get_attribute("alt") == typographic(image.alt)
    assert shown_image.evaluate("i => i.complete && i.naturalWidth === 1200")
    assert page.locator(".hero-figure").get_attribute("data-hero-image") == image_id
    assert hero_requests(requests, server) == [f"{image_id}.webp"]
    # The payload of the hero image: one file of at most 100 KB.
    size = (site_dir / image.file).stat().st_size
    assert 0 < size <= 100_000
    context.close()


def test_without_a_valid_parameter_an_image_is_picked_at_random_one_per_load(
    browser: Browser, server: SiteServer
):
    seen = Counter()
    for _ in range(16):
        page, context, requests = load_recorded(browser, server, "?hero-image=ising")
        (requested,) = hero_requests(requests, server)
        chosen = page.locator(".hero-figure").get_attribute("data-hero-image")
        assert requested == f"{chosen}.webp"
        seen[chosen] += 1
        context.close()
    assert set(seen) <= set(IMAGES)
    assert len(seen) > 1


def test_the_script_runs_before_the_first_paint_right_after_the_figure(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    script = page.locator('script[src$="learner/hero.js"]')
    assert script.count() == 1
    # Parser-blocking: it runs while the page is parsed, before it is painted.
    for attribute in ("async", "defer", "type"):
        assert script.get_attribute(attribute) is None, attribute
    # Between the copy and the script only the figure, which holds nothing
    # but <noscript> when scripts run, and the data of the images.
    assert script.evaluate(
        "s => [s.previousElementSibling, s.previousElementSibling"
        ".previousElementSibling, s.previousElementSibling.previousElementSibling"
        ".previousElementSibling].map(e => e.id)"
    ) == ["hero-images", "hero-figure", "hero-copy"]
    assert page.locator("#hero-figure > noscript").count() == 1


# Where the hero's parts stand, relative to the hero, and the hero itself.
_BOXES = """
() => {
  const hero = document.querySelector(".home-hero").getBoundingClientRect();
  const at = (selector) => {
    const box = document.querySelector(selector).getBoundingClientRect();
    return [box.x - hero.x, box.y - hero.y, box.width, box.height];
  };
  return {
    copy: at(".hero-copy"),
    actions: at(".home-hero .home-actions"),
    figure: at(".hero-figure"),
    next: at("#about-the-site"),
  };
}
"""


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE_TALL], ids=["desktop", "phone"])
def test_the_swap_moves_nothing_and_the_h1_does_not_change_after_load(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    # The web fonts swap in after the first paint and move the text by
    # themselves, script or not; without them the layout depends on the
    # image alone.
    context = browser.new_context(viewport=viewport)
    context.route("**/*.woff2", lambda route: route.abort())
    layouts = []
    for image_id in IMAGES:
        page = open_home(context, server, f"?hero-image={image_id}")
        boxes = page.evaluate(_BOXES)
        at_load = page.locator("h1").inner_text()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert page.locator("h1").inner_text() == at_load == FIXED[0]
        assert page.evaluate(_BOXES) == boxes, image_id
        layouts.append(boxes)
        page.close()
    context.close()
    # Whichever image is shown, the figure keeps its box and nothing after
    # it moves.
    assert all(layout == layouts[0] for layout in layouts), layouts


def _load(browser: Browser, server: SiteServer, empty_script: bool):
    requests: list[str] = []
    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
    if empty_script:
        context.route("**/learner/hero.js", lambda route: route.fulfill(body=""))
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    page.goto(
        server.url + "index.html?hero-image=hot-cold-gas",
        wait_until="networkidle",
    )
    page.wait_for_timeout(200)
    result = (
        Counter(url for url in requests),
        page.evaluate("window.__storageWrites"),
        Counter(page.evaluate(_STORAGE_ENTRIES)),
        context.cookies(),
        shown(page),
    )
    context.close()
    return result


def test_the_script_requests_the_one_image_and_nothing_else_and_stores_nothing(
    browser: Browser, server: SiteServer
):
    with_script = _load(browser, server, empty_script=False)
    without = _load(browser, server, empty_script=True)
    assert with_script[4] == without[4] == FIXED
    # With an empty script in its place (scripts on, so <noscript> is not
    # shown) no hero image is requested; with the script exactly one more
    # request: the image it was asked for. Writes, storage, and cookies are
    # the same.
    added = with_script[0] - without[0]
    assert list(added.elements()) == [server.url + "assets/hero/hot-cold-gas.webp"]
    assert without[0] - with_script[0] == Counter()
    assert with_script[1:4] == without[1:4]


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
    round 2 of Issue #462). The image is never moved or shrunk for this:
    beside the copy on a desktop, right after the actions on a phone."""
    context = browser.new_context(viewport=viewport)
    for image_id in IMAGES:
        page = open_home(context, server, f"?hero-image={image_id}")
        for selector in visible:
            box = _box(page, selector)
            assert box["y"] >= 0, selector
            assert box["y"] + box["height"] + margin <= viewport["height"], selector
        figure = _box(page, ".hero-figure")
        # Not shrunk: the full width of the content on a phone, the larger
        # column on a desktop, its own full width (40rem) on a tablet.
        if viewport in (DESKTOP, TABLET):
            assert figure["width"] >= 480
        else:
            assert abs(figure["width"] - _box(page, ".home-hero")["width"]) < 1
        page.close()
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
    for image_id in IMAGES:
        page = open_home(context, server, f"?hero-image={image_id}")
        figure = _box(page, ".hero-figure")
        assert figure["y"] >= 0, image_id
        visible = min(figure["y"] + figure["height"], viewport["height"]) - figure["y"]
        assert visible >= _RECOGNISABLE * figure["height"], (image_id, visible)
        assert visible >= 150
        if viewport is DESKTOP:
            assert figure["y"] + figure["height"] <= viewport["height"], image_id
        page.close()
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
    reference = open_home(context, server, "?hero-image=exoplanet-transit")
    tall = _image(reference)
    tall_column = _box(reference, ".home-hero")["width"]
    context.close()
    assert abs(tall["width"] - tall_column) < 1
    context = browser.new_context(viewport=viewport)
    for image_id in IMAGES:
        page = open_home(context, server, f"?hero-image={image_id}")
        image = _image(page)
        assert image["loaded"] and image["shown"], image_id
        # Uncropped: drawn in its natural aspect, so neither the fit nor the
        # figure cuts anything off.
        assert image["fit"] != "none" and image["clip"] == "visible", image_id
        natural_ratio = image["natural"][1] / image["natural"][0]
        assert abs(image["height"] - image["width"] * natural_ratio) < 1, image_id
        # Scaled by the width only: the same share of the column as at 390.
        column = _box(page, ".home-hero")["width"]
        assert abs(image["width"] - tall["width"] * column / tall_column) < 1
        actions = _box(page, ".home-hero .home-actions")
        figure = _box(page, ".hero-figure")
        assert actions["y"] + actions["height"] <= figure["y"] + 0.5, image_id
        page.close()
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
    the copy, the actions, and the image do not overlap, the reading order
    is the copy, then the two actions, then (stacked) the image, the
    headline keeps its size at normal text and is enlarged at 200 % with
    no word of the copy broken inside, and both actions can be reached
    with the keyboard."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server, "?hero-image=exoplanet-transit")
    normal = _font_size(page, "main h1")
    if scale != 1:
        page.add_style_tag(content=f"html {{ font-size: {100 * scale}% !important; }}")
        page.wait_for_timeout(100)
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
    beside = figure["x"] >= copy["x"] + copy["width"]
    assert beside or actions["y"] + actions["height"] <= figure["y"] + 0.5
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
