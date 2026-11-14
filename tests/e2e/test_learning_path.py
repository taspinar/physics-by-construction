"""Required checks on the learning path of the built site (architecture,
"Lesson model"): the path page and every lesson header are generated from
the lesson front matter, and a learner reaches every lesson from the home
page without JavaScript. The sequences of the path page, the course atlas,
are checked by tests/e2e/test_atlas.py (F133).

The expected order, neighbours, and prerequisites are read from the lesson
sources with the same module that generates the pages; that the module
orders and validates correctly is covered by tests/unit/test_learning_path.py.
"""

from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin

import pytest
from playwright.sync_api import Browser, BrowserContext, Page
from support import part_b
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP
from support.site_server import SiteServer

from pbc.authoring import DIFFICULTIES, METHODS, LearningPath
from pbc.authoring.atlas import Atlas, AtlasManifest, connections
from pbc.authoring.glossary import Glossary
from pbc.authoring.path import PATH_PAGE, Lesson
from pbc.authoring.website import introduced, introduction_page

PATH = Path(PATH_PAGE).with_suffix(".html").as_posix()
LESSON_PATH = LearningPath.read(SITE_SOURCE)
GLOSSARY = Glossary.read(SITE_SOURCE)
INTRODUCED = introduced(SITE_SOURCE)
ATLAS = Atlas(LESSON_PATH, AtlasManifest.read(SITE_SOURCE, LESSON_PATH.curriculum))
CONNECTIONS = {
    lesson.id: connections(ATLAS, lesson, lesson.page) for lesson in LESSON_PATH.lessons
}


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


def _open_header_details(header) -> None:
    """Open the header's closed disclosure the way a reader does, by its
    summary, without scripts (F174)."""
    details = header.locator("details.lesson-header-details")
    assert details.count() == 1
    assert details.evaluate("d => d.open") is False
    details.locator(":scope > summary").click()
    assert details.evaluate("d => d.open") is True


def _hrefs(page: Page, selector: str) -> list[str]:
    return page.locator(selector).evaluate_all("links => links.map(a => a.href)")


def test_path_page_explains_the_difficulty_scale(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    scale = page.locator("main #difficulty").inner_text()
    for difficulty in DIFFICULTIES:
        assert difficulty.title in scale
    # The descriptions are in a closed native disclosure, opened without
    # scripts (Issue #483).
    note = page.locator("main #difficulty details#difficulty-levels")
    assert note.get_attribute("open") is None
    note.locator("summary").click()
    assert note.get_attribute("open") is not None
    levels = note.locator("dl").inner_text()
    for difficulty in DIFFICULTIES:
        assert difficulty.title in levels
        assert difficulty.description in levels


def test_path_page_explains_previous_and_next(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + PATH, wait_until="load")

    order = page.locator("main section#order").inner_text()
    assert "Previous and next" in order
    assert "recommended teaching order" in order
    assert "all you need first" in order
    assert "strand" not in order


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


@pytest.mark.parametrize("moved", part_b.LESSONS, ids=lambda moved: moved.id)
def test_every_part_b_lesson_keeps_the_address_of_the_base_and_shows_its_new_slot(
    without_scripts: BrowserContext,
    server: SiteServer,
    site_dir: Path,
    moved: part_b.Moved,
):
    """The curriculum migration (F136) changes a lesson's slot and nothing
    else: the built page is at the address of the base commit, it is the
    same lesson, and its header names the new slot, an extension as one."""
    address = Path(moved.page).with_suffix(".html").as_posix()
    assert (site_dir / address).is_file()
    lesson = LESSON_PATH.lesson(moved.id)
    assert built(lesson) == address
    page = without_scripts.new_page()
    page.goto(server.url + address, wait_until="load")
    assert _plain(page.locator("main h1").first.inner_text()) == _plain(lesson.title)
    header = page.locator("main .lesson-header")
    _open_header_details(header)
    terms = [_plain(text) for text in header.locator("dt").all_inner_texts()]
    if not moved.slot:
        assert "Slot" not in terms
        return
    slot = header.locator("dd").nth(terms.index("Slot")).inner_text()
    method_path = LESSON_PATH.curriculum.path(
        LESSON_PATH.curriculum.slot(moved.slot).path
    )
    if LESSON_PATH.curriculum.slot(moved.slot).extension:
        assert (
            slot
            == f"{moved.slot}, an optional extension of the path {method_path.title}"
        )
    else:
        core = len(LESSON_PATH.curriculum.core_in_path(method_path))
        assert slot.startswith(f"{moved.slot}, number ")
        assert f" of the {core} slots of the path {method_path.title}" in slot


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
    # The orientation is visible; the rest opens by its summary (F174).
    _open_header_details(header)

    rows = dict(
        zip(
            [_plain(text) for text in header.locator("dt").all_inner_texts()],
            header.locator("dd").all(),
            strict=True,
        )
    )
    # F156: the sequences of the lesson that have an introduction, by name.
    home = [lesson.course]
    slot = LESSON_PATH.slot_of(lesson)
    if slot is not None and slot.path:
        home.append(slot.path)
    introduced_here = [item for item in home if item in INTRODUCED]
    # The visible rows, then those of the disclosure: every row the header
    # had, none lost (F174).
    visible = header.locator(":scope > dl > dt")
    assert [_plain(text) for text in visible.all_inner_texts()] == [
        "Course",
        "Methods",
        "Difficulty",
        "What you'll learn",
        "Previous",
        "Next",
    ]
    assert list(rows) == [
        "Course",
        "Methods",
        "Difficulty",
        "What you'll learn",
        "Previous",
        "Next",
        *(["Slot"] if lesson.slot else []),
        *(["Introduction"] if introduced_here else []),
        "Prerequisites",
        "Before you begin",
        "Related",
        *(["Connections"] if CONNECTIONS[lesson.id] else []),
    ]

    course = next(c for c in LESSON_PATH.courses if c.id == lesson.course)
    in_course = LESSON_PATH.in_course(course)
    assert rows["Course"].inner_text() == (
        f"{course.title}, lesson {in_course.index(lesson) + 1} of {len(in_course)}"
    )
    assert _hrefs(rows["Course"], "a") == [f"{server.url}{PATH}#course-{course.id}"]

    if introduced_here:
        assert _hrefs(rows["Introduction"], "a") == [
            f"{server.url}{introduction_page(item).removesuffix('.qmd')}.html"
            for item in introduced_here
        ]

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

    # Each outside prerequisite is listed with its detail; its term links to
    # the entry of the glossary.
    begin = rows["Before you begin"]
    assert [_plain(text) for text in begin.locator("li").all_inner_texts()] == list(
        lesson.outside
    )
    assert _hrefs(begin, "a") == [
        f"{server.url}glossary.html#{GLOSSARY.entry(outside).anchor}"
        for outside in lesson.outside
    ]

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

    # The conceptual connections and capstone memberships of the lesson's
    # concept, from the atlas manifest, each with its rationale (F133).
    if CONNECTIONS[lesson.id]:
        items = rows["Connections"].locator(":scope > ul > li").all_inner_texts()
        assert len(items) == len(CONNECTIONS[lesson.id])
        for concept in ATLAS.concepts_of(lesson):
            for connection in ATLAS.manifest.connections:
                if concept.id in connection.concepts:
                    assert any(
                        _plain(connection.rationale) in _plain(item) for item in items
                    )

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

    # The same previous and next lesson end the page: the last element of
    # main, after the last section and whatever follows its cell (F174).
    pager = page.locator("main nav.lesson-pager")
    assert pager.count() == 1
    assert pager.get_attribute("aria-label") == "Previous and next lesson"
    assert pager.evaluate(
        "nav => nav.parentElement.tagName === 'MAIN'"
        " && nav.nextElementSibling === null"
        " && Boolean(document.querySelector('#reproduce-this')"
        ".compareDocumentPosition(nav) & Node.DOCUMENT_POSITION_FOLLOWING)"
    )
    assert [_plain(text) for text in pager.locator("dt").all_inner_texts()] == [
        "Previous",
        "Next",
    ]
    assert _hrefs(pager, "a") == _hrefs(rows["Previous"], "a") + _hrefs(
        rows["Next"], "a"
    )


def test_the_header_disclosure_opens_by_keyboard_after_previous_and_next(
    without_scripts: BrowserContext, server: SiteServer
):
    """The keyboard reaches the header's disclosure right after the visible
    links, opens it with Enter, and goes on into it (F174)."""
    lesson = LESSON_PATH.lessons[0]
    page = without_scripts.new_page()
    page.goto(server.url + built(lesson), wait_until="load")
    page.focus(".lesson-header > dl a >> nth=-1")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.parentElement.className") == (
        "lesson-header-details"
    )
    page.keyboard.press("Enter")
    assert page.evaluate("document.querySelector('.lesson-header-details').open")
    page.keyboard.press("Tab")
    assert page.evaluate(
        "document.activeElement.closest('.lesson-header-details') !== null"
    )


def test_glossary_page_defines_every_entry_and_links_the_lessons_without_javascript(
    without_scripts: BrowserContext, server: SiteServer
):
    page = without_scripts.new_page()
    page.goto(server.url + "glossary.html", wait_until="load")

    main = page.locator("main")
    for entry in GLOSSARY.entries:
        section = main.locator(f"section#{entry.anchor}")
        assert section.count() == 1, entry.term
        assert section.locator("h2").inner_text() == entry.term
        assert entry.definition in section.inner_text()
        users = [
            lesson
            for lesson in LESSON_PATH.lessons
            if any(GLOSSARY.entry(text) == entry for text in lesson.outside)
        ]
        assert users, f"no lesson assumes {entry.term}"
        assert [
            link.get_attribute("href")
            for link in section.locator("a").all()
            if link.inner_text() in {lesson.title for lesson in users}
        ] == [f"lessons/{built(lesson).split('lessons/')[1]}" for lesson in users]
