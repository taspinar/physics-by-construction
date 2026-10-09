"""The built home page names the three activities, links each to a published
example, lists what is published from the lessons, and labels what is
planned (F25)."""

import pytest
from playwright.sync_api import Browser, BrowserContext
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import PLANNED, LearningPath
from pbc.authoring.home import CONSTRUCT_EXAMPLE, INVESTIGATE_EXAMPLE, VERIFY_EXAMPLE

LESSONS = LearningPath.read(SITE_SOURCE)


@pytest.fixture
def home(browser: Browser, server: SiteServer):
    context: BrowserContext = browser.new_context(
        viewport=DESKTOP, java_script_enabled=False
    )
    page = context.new_page()
    page.goto(server.url + "index.html", wait_until="load")
    yield page
    context.close()


def plain(text: str) -> str:
    # The build turns apostrophes into typographic ones.
    return text.replace("\u2019", "'")


def built(lesson_id: str, server: SiteServer) -> str:
    page = LESSONS.lesson(lesson_id).page.removesuffix(".qmd") + ".html"
    return server.url + page


@pytest.mark.parametrize(
    ("section", "title", "lesson_id"),
    [
        ("construct", "Construct", CONSTRUCT_EXAMPLE),
        ("investigate", "Investigate", INVESTIGATE_EXAMPLE),
        ("verify", "Verify", VERIFY_EXAMPLE),
    ],
)
def test_each_activity_links_one_published_example(
    home, server: SiteServer, section: str, title: str, lesson_id: str
):
    heading = home.locator(f"main section#{section} > h3")
    assert heading.inner_text() == title
    links = home.locator(f"main section#{section} a").evaluate_all(
        "links => links.map(a => a.href)"
    )
    assert links == [built(lesson_id, server)]
    response = home.request.get(links[0])
    assert response.ok


def test_published_section_names_every_lesson_and_the_counts(home, server: SiteServer):
    section = home.locator("main section#published")
    text = section.inner_text()
    assert (
        f"publishes {len(LESSONS.lessons)} lessons in {len(LESSONS.strands)} strands"
        in text
    )
    links = section.locator("a").evaluate_all("links => links.map(a => a.href)")
    for lesson in LESSONS.lessons:
        assert links.count(built(lesson.id, server)) == 1, lesson.id
        assert plain(lesson.title) in plain(text)
    assert server.url + "path/index.html#courses" in links
    assert server.url + "path/index.html#methods" in links


def test_every_planned_item_names_a_roadmap_id_and_is_not_linked(home):
    section = home.locator("main section#planned")
    items = section.locator("li")
    assert items.count() == len(PLANNED)
    for item, planned in zip(items.all(), PLANNED, strict=True):
        text = item.inner_text()
        assert text.startswith(f"Planned, {planned.roadmap_id}: ")
        assert item.locator("a").count() == 0
    assert section.locator("a").count() == 0


def test_the_home_page_links_to_the_path_and_about_pages(home, server: SiteServer):
    links = home.locator("main a").evaluate_all("links => links.map(a => a.href)")
    assert server.url + "path/index.html" in links
    assert server.url + "about.html" in links
