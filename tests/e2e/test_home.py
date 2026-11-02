"""The built home page (F134, ADR 021 decision 4): the hero with the owner's
pairs, one forced by the `hero` parameter or one at random, the default pair
without scripts, one <h1> that does not change after load, no layout shift,
and no request or storage by its script; the start button above the fold on
a desktop and a phone; what the site is, the examples chosen by code, and
the invitation, every link generated from data and reaching its target.
The accessibility scan, the reflow at 320 CSS px, and the payload budget are
the checks every page gets (tests/e2e/test_built_site.py)."""

from collections import Counter

import pytest
import yaml
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import _RECORD_STORAGE_WRITES, _STORAGE_ENTRIES, DESKTOP
from support.site_server import SiteServer

from pbc.authoring import LearningPath
from pbc.authoring.atlas import AtlasManifest
from pbc.authoring.home import HERO_PAIRS, HeroCopy, HomeContent

LESSONS = LearningPath.read(SITE_SOURCE)
HERO = HeroCopy.read(SITE_SOURCE)
HOME = HomeContent(LESSONS, AtlasManifest.read(SITE_SOURCE, LESSONS.curriculum), HERO)
PHONE_TALL = {"width": 390, "height": 844}
SECTIONS = ["about-the-site", "examples", "begin"]
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


def shown(page: Page) -> tuple[str, str]:
    return (
        page.locator("main h1").inner_text(),
        page.locator(
            ".hero-copy > .hero-pair:not(.hero-ghost) .hero-subtext"
        ).inner_text(),
    )


# --- The hero ------------------------------------------------------------------


def test_without_scripts_the_page_has_the_default_pair_and_one_h1(
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
    assert ids == SECTIONS


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
    actions: at(".home-actions"),
    image: at(".hero-image"),
    next: at("#about-the-site"),
  };
}
"""


def test_the_script_runs_before_the_first_paint_right_after_the_copy(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    script = page.locator('script[src$="learner/hero.js"]')
    assert script.count() == 1
    # Parser-blocking: it runs while the page is parsed, before it is painted.
    for attribute in ("async", "defer", "type"):
        assert script.get_attribute(attribute) is None, attribute
    # Nothing that is painted stands between the copy and the script.
    assert script.evaluate(
        "s => s.previousElementSibling.id === 'hero-pairs'"
        " && s.previousElementSibling.previousElementSibling"
        ".classList.contains('hero-copy')"
    )


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE_TALL], ids=["desktop", "phone"])
def test_the_swap_moves_nothing_and_the_h1_does_not_change_after_load(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    # The web fonts swap in after the first paint and move the text by
    # themselves, script or not; without them the layout depends on the
    # pair alone.
    context = browser.new_context(viewport=viewport)
    context.route("**/*.woff2", lambda route: route.abort())
    layouts = []
    for pair_id in HERO_PAIRS:
        page = open_home(context, server, f"?hero={pair_id}")
        at_load = page.locator("h1").inner_text()
        boxes = page.evaluate(_BOXES)
        page.wait_for_timeout(300)
        assert page.locator("h1").inner_text() == at_load
        assert page.evaluate(_BOXES) == boxes, pair_id
        layouts.append(boxes)
        page.close()
    context.close()
    # Whichever pair is shown, the copy is as tall as the longest pair and
    # nothing after it stands elsewhere.
    assert all(layout == layouts[0] for layout in layouts), layouts


def _load(browser: Browser, server: SiteServer, empty_script: bool):
    requests: list[str] = []
    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(f"({_RECORD_STORAGE_WRITES})()")
    if empty_script:
        context.route("**/learner/hero.js", lambda route: route.fulfill(body=""))
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    page.goto(server.url + "index.html?hero=2a", wait_until="networkidle")
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


def test_the_script_makes_no_request_and_uses_no_storage(
    browser: Browser, server: SiteServer
):
    with_script = _load(browser, server, empty_script=False)
    without = _load(browser, server, empty_script=True)
    assert with_script[4] == "2a" and without[4] == HERO.default
    # The page requests, writes, and keeps the same with the script as with
    # an empty file in its place.
    assert with_script[:4] == without[:4]


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE_TALL], ids=["desktop", "phone"])
def test_the_message_and_the_start_button_are_above_the_fold(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    for pair_id in HERO_PAIRS:
        page = open_home(context, server, f"?hero={pair_id}")
        for selector in (
            "main h1",
            ".hero-pair:not(.hero-ghost) .hero-subtext",
            ".home-hero .home-action-primary",
        ):
            box = page.locator(selector).bounding_box()
            assert box is not None and box["y"] >= 0, selector
            assert box["y"] + box["height"] <= viewport["height"], (pair_id, selector)
        page.close()
    context.close()


def test_the_hero_image_is_labelled_text_over_registered_parts(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    image = page.locator(".home-hero svg.hero-image")
    assert image.get_attribute("role") == "img"
    assert image.locator("title").count() == 1
    assert image.locator("a").count() == 0
    labels = image.locator("text.hero-label").all_text_contents()
    assert len(labels) == 12
    register = yaml.safe_load(
        (SITE_SOURCE / "assets" / "provenance.yaml").read_text(encoding="utf-8")
    )["assets"]
    sources = image.locator("image").evaluate_all(
        "items => items.map(i => i.getAttribute('href'))"
    )
    assert len(sources) == 12
    for source in sources:
        assert source.removeprefix("assets/") in register
        assert page.request.get(server.url + source).ok


# --- The rest of the page ------------------------------------------------------


def test_the_examples_and_the_capstone_are_the_chosen_lessons(
    without_scripts: BrowserContext, server: SiteServer
):
    page = open_home(without_scripts, server)
    chosen = [*HOME.examples(), HOME.capstone()]
    entries = page.locator("main section#examples .home-example")
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
    first = LESSONS.in_course(LESSONS.courses[0])[0]
    links = hrefs(page.locator("main a"))
    assert hrefs(page.locator("main section#begin a")) == [
        built(first.page, server),
        server.url + "path/index.html#atlas",
    ]
    assert hrefs(page.locator(".home-hero a")) == hrefs(
        page.locator("main section#begin a")
    )
    assert server.url + "about.html#creator-and-jidai" in links
    assert server.url + "verify.html" in links
    for link in links:
        if not link.startswith(server.url):
            continue
        address, _, fragment = link.partition("#")
        target = without_scripts.new_page()
        target.goto(address)
        if fragment:
            assert target.locator(f"[id='{fragment}']").count() == 1, link
        target.close()


def test_the_page_tells_one_story(without_scripts: BrowserContext, server: SiteServer):
    page = open_home(without_scripts, server)
    text = page.locator("main").inner_text()
    assert "From a question to a working model" not in text
    assert "lessons published" not in text
    headings = page.locator("main h2").all_inner_texts()
    assert headings == ["What this site is", "What you can learn", "Begin"]
