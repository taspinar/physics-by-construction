"""Required checks on the learning path of the built site (architecture,
"Lesson model"): the path page and every lesson header are generated from
the lesson front matter, and a learner reaches every lesson from the home
page without JavaScript.

The expected order, neighbours, and prerequisites are read from the lesson
sources with the same module that generates the pages; that the module
orders and validates correctly is covered by tests/unit/test_learning_path.py.
"""

from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin

import pytest
from playwright.sync_api import Browser, BrowserContext, Page
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import DIFFICULTIES, LearningPath
from pbc.authoring.path import PATH_PAGE, Lesson

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
LESSON_PATH = LearningPath.read(SITE_SOURCE)


def built(lesson: Lesson) -> str:
    return Path(lesson.page).with_suffix(".html").as_posix()


@pytest.fixture
def without_scripts(browser: Browser) -> BrowserContext:
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context
    context.close()


def test_the_site_has_lessons_and_a_path_page(site_dir: Path):
    # Guards the tests below: without lessons they would check nothing, and
    # the checks every page gets (accessibility, widths) must see the path.
    assert LESSON_PATH.lessons
    assert (site_dir / PATH).is_file()


def test_every_lesson_is_reached_from_the_home_page_without_javascript(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    visited: set[str] = set()
    queue = deque(["index.html"])
    while queue:
        name = queue.popleft()
        if name in visited:
            continue
        visited.add(name)
        page.goto(server.url + name, wait_until="load")
        for href in page.locator("a[href]").evaluate_all(
            "links => links.map(a => a.getAttribute('href'))"
        ):
            target = urldefrag(urljoin(server.url + name, href)).url
            if target.startswith(server.url) and target.endswith(".html"):
                queue.append(target[len(server.url) :])

    assert PATH in visited
    assert {built(lesson) for lesson in LESSON_PATH.lessons} <= visited


def _hrefs(page: Page, selector: str) -> list[str]:
    return page.locator(selector).evaluate_all("links => links.map(a => a.href)")


def test_path_page_explains_the_difficulty_scale(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    scale = page.locator("main #difficulty").inner_text()
    for difficulty in DIFFICULTIES:
        assert difficulty.title.lower() in scale.lower()
        assert difficulty.description in scale


def test_path_page_lists_the_lessons_of_each_strand_in_order(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    for strand in LESSON_PATH.strands:
        section = page.locator(f"main section#{strand.id}")
        assert section.locator("h2").inner_text() == strand.title
        lessons = LESSON_PATH.in_strand(strand)
        items = section.locator("ol > li")
        assert items.count() == len(lessons)
        for item, lesson in zip(items.all(), lessons, strict=True):
            # The first link is the lesson, the others its prerequisites.
            links = item.locator("a").evaluate_all("links => links.map(a => a.href)")
            assert links[0] == server.url + built(lesson)
            assert links[1:] == [
                server.url + built(LESSON_PATH.lesson(item))
                for item in lesson.prerequisites
            ]
            text = item.inner_text()
            assert DIFFICULTIES[lesson.difficulty - 1].title in text
            assert all(outside in text for outside in lesson.outside)
    # A strand without a lesson has no section.
    assert page.locator("main section.level2").count() == 1 + len(LESSON_PATH.strands)


@pytest.mark.parametrize("lesson", LESSON_PATH.lessons, ids=lambda lesson: lesson.id)
def test_lesson_header_shows_the_facts_of_the_path_with_links(
    without_scripts: BrowserContext, server: SiteServer, lesson: Lesson
):
    page = without_scripts.new_page()
    page.goto(server.url + built(lesson), wait_until="load")
    header = page.locator("main .lesson-header")
    assert header.count() == 1
    # The header comes before the text of the lesson.
    assert page.locator("main > :not(header) .lesson-header").count() == 1
    first = page.locator("main > :not(header)").first
    assert first.locator(".lesson-header").count() == 1

    rows = dict(
        zip(
            header.locator("dt").all_inner_texts(),
            header.locator("dd").all(),
            strict=True,
        )
    )
    assert list(rows) == ["Strand", "Difficulty", "Prerequisites", "Previous", "Next"]

    strand = next(s for s in LESSON_PATH.strands if s.id == lesson.strand)
    in_strand = LESSON_PATH.in_strand(strand)
    assert rows["Strand"].inner_text() == (
        f"{strand.title}, lesson {in_strand.index(lesson) + 1} of {len(in_strand)}"
    )
    assert _hrefs(rows["Strand"], "a") == [f"{server.url}{PATH}#{strand.id}"]

    difficulty = DIFFICULTIES[lesson.difficulty - 1]
    assert difficulty.title in rows["Difficulty"].inner_text()
    assert _hrefs(rows["Difficulty"], "a") == [f"{server.url}{PATH}#difficulty"]

    assert _hrefs(rows["Prerequisites"], "a") == [
        server.url + built(LESSON_PATH.lesson(item)) for item in lesson.prerequisites
    ]
    assert all(
        outside in rows["Prerequisites"].inner_text() for outside in lesson.outside
    )

    for name, neighbour in (
        ("Previous", LESSON_PATH.previous(lesson)),
        ("Next", LESSON_PATH.next(lesson)),
    ):
        if neighbour is None:
            assert "none" in rows[name].inner_text()
            assert _hrefs(rows[name], "a") == [server.url + PATH]
        else:
            assert rows[name].inner_text() == neighbour.title
            assert _hrefs(rows[name], "a") == [server.url + built(neighbour)]
