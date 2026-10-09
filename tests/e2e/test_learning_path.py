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
from playwright.sync_api import Browser, BrowserContext, Locator, Page
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import DIFFICULTIES, METHODS, LearningPath
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


def _plain(text: str) -> str:
    # The build turns apostrophes into typographic ones.
    return text.replace("\u2019", "'")


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


def _check_items(
    items: Locator, lessons: tuple[Lesson, ...], server: SiteServer
) -> None:
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


def test_path_page_lists_the_lessons_of_each_course_in_order(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    for course in LESSON_PATH.courses:
        section = page.locator(f"main section#course-{course.id}")
        assert section.locator("h3").first.inner_text() == course.title
        lessons = LESSON_PATH.in_course(course)
        core = tuple(lesson for lesson in lessons if lesson.strand == course.id)
        extensions = tuple(lesson for lesson in lessons if lesson.strand != course.id)
        _check_items(
            section.locator(f"section#course-{course.id}-core > ol > li"),
            core,
            server,
        )
        _check_items(
            section.locator(f"section#course-{course.id}-extensions > ol > li"),
            extensions,
            server,
        )
        # Every lesson of the course is listed, once.
        assert len(core) + len(extensions) == len(lessons)
    # A course without a lesson has no section.
    assert page.locator("main section#courses > section.level3").count() == len(
        LESSON_PATH.courses
    )


def test_path_page_lists_the_lessons_of_each_method_in_path_order(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    for method in LESSON_PATH.methods:
        section = page.locator(f"main section#method-{method.id}")
        assert section.locator("h3").first.inner_text() == method.title
        _check_items(section.locator("ol > li"), LESSON_PATH.using(method), server)
    # A method without a lesson has no section.
    assert page.locator("main section#methods > section.level3").count() == len(
        LESSON_PATH.methods
    )


def test_path_page_lists_every_lesson_under_its_course_and_its_methods(
    without_scripts: BrowserContext, server: SiteServer
):
    # The page compared with the metadata, the other way round: for each
    # lesson, the sections that link it are exactly its course and methods.
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    for lesson in LESSON_PATH.lessons:
        sections = page.locator("main section.level3").evaluate_all(
            "(sections, href) => sections"
            ".filter(s => [...s.querySelectorAll(':scope > ol > li > p:first-child > a,"
            " :scope > section > ol > li > p:first-child > a')]"
            ".some(a => a.href === href))"
            ".map(s => s.id)",
            server.url + built(lesson),
        )
        assert sorted(sections) == sorted(
            [f"course-{lesson.course}"]
            + [f"method-{method}" for method in lesson.methods]
        ), lesson.id


def test_path_page_explains_previous_and_next(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    order = page.locator("main section#order").inner_text()
    assert "Previous and next" in order
    assert "course order" in order
    assert "prerequisites" in order


# Every lesson address that existed before the courses (F37): the address
# resolves to the lesson with this id.
PREVIOUS_ADDRESSES = {
    f"lessons/{directory}/index.html": lesson_id
    for directory, lesson_id in {
        "mechanics/01-kinematics-as-a-program": "kinematics",
        "mechanics/02-newtons-laws": "newtons-laws",
        "mechanics/03-projectile-motion-with-drag": "projectile-with-drag",
        "mechanics/04-harmonic-oscillator": "harmonic-oscillator",
        "mechanics/05-numerical-integrators": "numerical-integrators",
        "mechanics/06-energy-conservation": "energy-conservation",
        "mechanics/07-momentum-and-collisions": "momentum-and-collisions",
        "mechanics/08-kepler-orbit": "kepler-orbit",
        "agents-llm/01-an-agent-runs-an-experiment": "agent-experiment",
        "agents-abm/01-particles-in-a-box": "particles-in-a-box",
        "lean/01-proving-what-the-simulation-showed": (
            "proving-what-the-simulation-showed"
        ),
    }.items()
}


@pytest.mark.parametrize("address, lesson_id", PREVIOUS_ADDRESSES.items())
def test_every_previous_lesson_address_still_resolves_to_its_lesson(
    without_scripts: BrowserContext,
    server: SiteServer,
    site_dir: Path,
    address: str,
    lesson_id: str,
):
    assert (site_dir / address).is_file()
    lesson = LESSON_PATH.lesson(lesson_id)
    assert built(lesson) == address
    # The page served at the address is that lesson, not only a file there.
    page = without_scripts.new_page()
    page.goto(server.url + address, wait_until="load")
    assert _plain(page.locator("main h1").first.inner_text()) == _plain(lesson.title)


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
            [_plain(text) for text in header.locator("dt").all_inner_texts()],
            header.locator("dd").all(),
            strict=True,
        )
    )
    assert list(rows) == [
        "Course",
        "Methods",
        "Difficulty",
        "What you'll learn",
        "Prerequisites",
        "Related",
        "Previous",
        "Next",
    ]

    course = next(c for c in LESSON_PATH.courses if c.id == lesson.course)
    in_course = LESSON_PATH.in_course(course)
    assert rows["Course"].inner_text() == (
        f"{course.title}, lesson {in_course.index(lesson) + 1} of {len(in_course)}"
    )
    assert _hrefs(rows["Course"], "a") == [f"{server.url}{PATH}#course-{course.id}"]

    methods = [next(m for m in METHODS if m.id == item) for item in lesson.methods]
    assert rows["Methods"].inner_text() == ", ".join(m.title for m in methods)
    assert _hrefs(rows["Methods"], "a") == [
        f"{server.url}{PATH}#method-{m.id}" for m in methods
    ]

    difficulty = DIFFICULTIES[lesson.difficulty - 1]
    assert difficulty.title in rows["Difficulty"].inner_text()
    assert _hrefs(rows["Difficulty"], "a") == [f"{server.url}{PATH}#difficulty"]

    assert [
        _plain(text)
        for text in rows["What you'll learn"].locator("li").all_inner_texts()
    ] == list(lesson.outcomes)

    assert _hrefs(rows["Prerequisites"], "a") == [
        server.url + built(LESSON_PATH.lesson(item)) for item in lesson.prerequisites
    ]
    assert all(
        outside in rows["Prerequisites"].inner_text() for outside in lesson.outside
    )

    if lesson.related:
        assert _hrefs(rows["Related"], "a") == [
            server.url + built(LESSON_PATH.lesson(item)) for item in lesson.related
        ]
        assert rows["Related"].inner_text() == ", ".join(
            LESSON_PATH.lesson(item).title for item in lesson.related
        )
    else:
        assert rows["Related"].inner_text() == "none"
        assert _hrefs(rows["Related"], "a") == []

    for name, neighbour in (
        ("Previous", LESSON_PATH.previous(lesson)),
        ("Next", LESSON_PATH.next(lesson)),
    ):
        if neighbour is None:
            assert "none" in rows[name].inner_text()
            assert _hrefs(rows[name], "a") == [server.url + PATH + "#order"]
        else:
            assert rows[name].inner_text() == neighbour.title
            assert _hrefs(rows[name], "a") == [server.url + built(neighbour)]
