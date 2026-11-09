"""The built home page (F134, F158; ADR 021 decision 4 as amended): the hero
with the owner's pairs, one forced by the `hero` parameter or one at random,
and one of the four Part A illustrations, forced by the `hero-image`
parameter or picked at random independently of the pair, exactly one hero
image requested per load; the default pair and image without scripts; one
<h1> that does not change after load; no layout shift; no request beyond the
image and no storage by its script; the layout rule of "Home page" at
1280 by 800, 390 by 844, 360 by 640, and 320 CSS px and at 200 % text; the
two actions with the header's destinations; the four sections of the copy
file in order, every link generated from data and reaching its target.
The accessibility scan, the keyboard pass, the reflow at 320 CSS px, and
the payload budget are the checks every page gets
(tests/e2e/test_built_site.py)."""

from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
import yaml
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import _RECORD_STORAGE_WRITES, _STORAGE_ENTRIES, DESKTOP
from support.site_server import SiteServer

from pbc.authoring import LearningPath
from pbc.authoring.home import (
    ATLAS_ACTION,
    FIRST_LESSON_ACTION,
    HERO_IMAGES,
    HERO_PAIRS,
    HOME_FILE,
    SECTIONS,
    HeroCopy,
)

LESSONS = LearningPath.read(SITE_SOURCE)
HERO = HeroCopy.read(SITE_SOURCE)
IMAGES = [image.id for image in HERO.images]
PUBLISHED = {lesson.slot: lesson for lesson in LESSONS.lessons if lesson.slot}
PHONE_TALL = {"width": 390, "height": 844}
PHONE_SMALL = {"width": 360, "height": 640}
PHONE_NARROW = {"width": 320, "height": 568}
APOSTROPHE = chr(0x2019)


def typographic(text: str) -> str:
    return text.replace("'", APOSTROPHE)


def _examples() -> list:
    data = yaml.safe_load((SITE_SOURCE / HOME_FILE).read_text(encoding="utf-8"))
    examples = data["curriculum"].get("examples") or {}
    return [
        PUBLISHED[examples[part]] for part in ("part-a", "part-b") if part in examples
    ]


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


def shown(page: Page) -> tuple[str, str]:
    return (
        page.locator("main h1").inner_text(),
        page.locator(
            ".hero-copy > .hero-pair:not(.hero-ghost) .hero-subtext"
        ).inner_text(),
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


def test_without_scripts_the_page_has_the_default_pair_image_and_one_h1(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    default = HERO.pair(HERO.default)
    assert page.locator("h1").count() == 1
    assert shown(page) == (typographic(default.headline), typographic(default.subtext))
    assert page.locator(".hero-ghost").count() == 0
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


@pytest.mark.parametrize("pair_id", HERO_PAIRS)
def test_the_hero_parameter_shows_each_pair(
    browser: Browser, server: SiteServer, pair_id: str
):
    context = browser.new_context(viewport=DESKTOP)
    page = open_home(context, server, f"?hero={pair_id}")
    pair = HERO.pair(pair_id)
    assert shown(page) == (typographic(pair.headline), typographic(pair.subtext))
    assert page.locator(".hero-copy").get_attribute("data-hero") == pair_id
    assert page.locator("h1").count() == 1
    # Every pair stands hidden in the same cell, and none is announced.
    ghosts = page.locator(".hero-ghost")
    assert ghosts.count() == len(HERO_PAIRS)
    assert ghosts.evaluate_all(
        "gs => gs.every(g => g.getAttribute('aria-hidden') === 'true'"
        " && getComputedStyle(g).visibility === 'hidden')"
    )
    context.close()


def test_without_a_valid_parameter_a_pair_is_shown_at_random(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP)
    seen = set()
    for _ in range(12):
        page = open_home(context, server, "?hero=9z")
        seen.add(page.locator(".hero-copy").get_attribute("data-hero"))
        page.close()
    context.close()
    assert seen <= set(HERO_PAIRS)
    assert len(seen) > 1


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


def test_the_image_is_picked_independently_of_the_pair(
    browser: Browser, server: SiteServer
):
    """A forced pair leaves the image to chance, and a forced image leaves
    the pair to chance: the two are separate draws."""
    images, pairs = set(), set()
    context = browser.new_context(viewport=DESKTOP)
    for _ in range(16):
        page = open_home(context, server, "?hero=2b")
        images.add(page.locator(".hero-figure").get_attribute("data-hero-image"))
        page.close()
        page = open_home(context, server, "?hero-image=vortex-street")
        pairs.add(page.locator(".hero-copy").get_attribute("data-hero"))
        page.close()
    context.close()
    assert len(images) > 1 and len(pairs) > 1


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
    # but <noscript> when scripts run, and the data.
    assert script.evaluate(
        "s => [s.previousElementSibling, s.previousElementSibling"
        ".previousElementSibling, s.previousElementSibling.previousElementSibling"
        ".previousElementSibling, s.previousElementSibling.previousElementSibling"
        ".previousElementSibling.previousElementSibling].map(e => e.id)"
    ) == ["hero-images", "hero-pairs", "hero-figure", "hero-copy"]
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
    # pair and the image alone.
    context = browser.new_context(viewport=viewport)
    context.route("**/*.woff2", lambda route: route.abort())
    layouts = []
    for pair_id, image_id in zip(HERO_PAIRS, IMAGES * 2, strict=True):
        page = open_home(context, server, f"?hero={pair_id}&hero-image={image_id}")
        boxes = page.evaluate(_BOXES)
        at_load = page.locator("h1").inner_text()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert page.locator("h1").inner_text() == at_load
        assert page.evaluate(_BOXES) == boxes, (pair_id, image_id)
        layouts.append(boxes)
        page.close()
    context.close()
    # Whichever pair and image are shown, the copy is as tall as the longest
    # pair, the figure keeps its box, and nothing after them moves.
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
        server.url + "index.html?hero=2a&hero-image=hot-cold-gas",
        wait_until="networkidle",
    )
    page.wait_for_timeout(200)
    result = (
        Counter(url for url in requests),
        page.evaluate("window.__storageWrites"),
        Counter(page.evaluate(_STORAGE_ENTRIES)),
        context.cookies(),
        page.locator(".hero-copy").get_attribute("data-hero"),
    )
    context.close()
    return result


def test_the_script_requests_the_one_image_and_nothing_else_and_stores_nothing(
    browser: Browser, server: SiteServer
):
    with_script = _load(browser, server, empty_script=False)
    without = _load(browser, server, empty_script=True)
    assert with_script[4] == "2a" and without[4] == HERO.default
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


_MESSAGE = ("main h1", ".hero-pair:not(.hero-ghost) .hero-subtext")
_PRIMARY = ".home-hero .home-action-primary"
_SECONDARY = ".home-hero .home-action"


@pytest.mark.parametrize(
    ("viewport", "visible"),
    [
        (DESKTOP, (*_MESSAGE, _PRIMARY, _SECONDARY)),
        (PHONE_TALL, (*_MESSAGE, _PRIMARY, _SECONDARY)),
        (PHONE_SMALL, (*_MESSAGE, _PRIMARY)),
    ],
    ids=["1280x800", "390x844", "360x640"],
)
def test_the_message_and_the_actions_are_above_the_fold(
    browser: Browser, server: SiteServer, viewport: dict[str, int], visible: tuple
):
    """On a desktop the identity message and both actions; on a phone the
    message and the primary action, at 360 by 640 the secondary just below
    the fold; whichever pair is shown (the copy keeps the height of the
    longest). The image is never moved or shrunk for this: beside the copy
    on a desktop, right after the actions on a phone, its top on the screen
    at 1280 by 800 and 390 by 844."""
    context = browser.new_context(viewport=viewport)
    for pair_id in HERO_PAIRS:
        page = open_home(context, server, f"?hero={pair_id}")
        for selector in visible:
            box = _box(page, selector)
            assert box["y"] >= 0, selector
            assert box["y"] + box["height"] <= viewport["height"], (pair_id, selector)
        figure = _box(page, ".hero-figure")
        if viewport in (DESKTOP, PHONE_TALL):
            assert figure["y"] < viewport["height"] - 150, pair_id
        # Not shrunk: the full width of the content on a phone, the larger
        # column on a desktop.
        if viewport is DESKTOP:
            assert figure["width"] >= 480
        else:
            assert abs(figure["width"] - _box(page, ".home-hero")["width"]) < 1
        page.close()
    context.close()


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
    is the copy, then the two actions, then (stacked) the image, and both
    actions can be reached with the keyboard."""
    context = browser.new_context(viewport=viewport)
    page = open_home(context, server, "?hero=3a&hero-image=exoplanet-transit")
    if scale != 1:
        page.add_style_tag(content=f"html {{ font-size: {100 * scale}% !important; }}")
        page.wait_for_timeout(100)
    # The page's content is no wider than its column. (The shared header of
    # every page is the F132 check's; at 200 % text on 320 CSS px it is
    # wider than the screen on every page, outside this page's layout.)
    main = page.locator("main").evaluate("m => [m.scrollWidth, m.clientWidth]")
    assert main[0] <= main[1], main
    if scale == 1 or viewport["width"] > 320:
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
    # The text does grow: the headline is at least the scaled phone size.
    size = page.locator("main h1").evaluate(
        "h => parseFloat(getComputedStyle(h).fontSize)"
    )
    assert size >= 28 * scale - 0.5
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


def test_the_examples_are_the_owner_s_lessons(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    chosen = _examples()
    entries = page.locator("main section#what-you-can-learn .home-example")
    assert entries.evaluate_all("es => es.map(e => e.dataset.lessonId)") == [
        lesson.id for lesson in chosen
    ]
    for entry, lesson in zip(entries.all(), chosen, strict=True):
        assert hrefs(entry.locator("a")) == [built(lesson.page, server)]
        image = entry.locator("img.home-preview")
        assert (image.get_attribute("alt") or "").startswith("Preview, ")
        assert page.request.get(image.evaluate("i => i.src")).ok
        assert "level" in entry.locator(".home-meta").inner_text()


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
        "What this site is",
        "How physics is learned here",
        "What you can learn",
        "How the results are kept honest",
    ]
    assert page.locator("main h3").all_inner_texts() == [
        "Part A: Physics by construction",
        "Part B: Physics and AI",
        "From Part A to Part B",
    ]
    # No constellation and no inline image in the hero.
    assert page.locator(".home-hero svg").count() == 0
