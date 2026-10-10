"""Required checks on self-checks and browser-local progress
(architecture, "Learner state" and invariant I16; docs/authoring.md,
"Self-checks and progress").

Lesson pages with a self-check have a script that stores progress in local
storage. The checks drive it as a reader would, with the keyboard, and watch
what leaves the page.
"""

import json
from pathlib import Path

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Browser, Page
from support import site_checks
from support.paths import SITE_SOURCE
from support.site_checks import DESKTOP, PHONE, WCAG_TAGS, describe
from support.site_server import SiteServer

from pbc.authoring import LearningPath
from pbc.authoring.progress import STORAGE_KEY, path_export

# The self-check of this lesson has choices; that of OPEN_LESSON has none.
CHOICE_LESSON = "lessons/mechanics/01-kinematics-as-a-program/index.html"
CHOICE_ID = "kinematics"
OPEN_LESSON = "lessons/lean/02-momentum-in-a-collision-proved/index.html"
OPEN_ID = "collision-momentum-proved"
PATH_PAGE = "path/index.html"

CHOICES = ".exercise.self-check fieldset.choice-form"


@pytest.fixture
def page(browser: Browser):
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


def stored(page: Page) -> dict | None:
    text = page.evaluate("(key) => localStorage.getItem(key)", STORAGE_KEY)
    return json.loads(text) if text is not None else None


def choose(page: Page, text: str) -> None:
    """Pick the option that starts with ``text`` and check it, with the
    keyboard: the option has the focus, Space selects it, and Tab reaches the
    button."""
    page.locator(f"{CHOICES} label", has_text=text).locator("input").focus()
    page.keyboard.press("Space")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.textContent") == "Check answer"
    page.keyboard.press("Enter")


def open_lesson(page: Page, server: SiteServer, name: str = CHOICE_LESSON) -> None:
    page.goto(server.url + name, wait_until="networkidle")
    page.locator(".learner-panel").wait_for()


# --- Completing a self-check ---------------------------------------------------


def test_a_wrong_answer_gives_feedback_and_does_not_complete_the_lesson(
    page: Page, server: SiteServer
):
    open_lesson(page, server)

    choose(page, "Yes. Every halving")

    result = page.locator(".self-check-result")
    assert "Not quite." in result.inner_text()
    assert "rounding errors" in result.inner_text()
    assert stored(page)["lessons"][CHOICE_ID] == {
        "selfCheck": {"done": False, "attempts": 1}
    }
    assert "not marked" in page.locator(".learner-status").inner_text()


def test_a_correct_answer_completes_the_lesson_and_persists_across_loads(
    page: Page, server: SiteServer
):
    open_lesson(page, server)

    choose(page, "No. At some time step")

    assert "Correct." in page.locator(".self-check-result").inner_text()
    assert stored(page) == {
        "version": 1,
        "lessons": {
            CHOICE_ID: {"completed": True, "selfCheck": {"done": True, "attempts": 1}}
        },
    }
    page.reload(wait_until="networkidle")
    assert "have completed" in page.locator(".learner-status").inner_text()
    assert page.locator(".exercise.self-check").get_attribute("data-done") == "true"


def test_the_learning_path_shows_completed_lessons_and_the_clear_control_removes_them(
    page: Page, server: SiteServer
):
    open_lesson(page, server)
    choose(page, "No. At some time step")

    page.goto(server.url + PATH_PAGE, wait_until="networkidle")

    total = len(LearningPath.read(SITE_SOURCE).lessons)
    summary = page.locator("#progress-controls [role=status]")
    assert summary.inner_text().startswith(f"1 of {total} lessons completed.")
    marked = page.locator(".path-card[data-completed='true']")
    assert marked.count() >= 1
    for index in range(marked.count()):
        assert marked.nth(index).get_attribute("data-lesson-id") == CHOICE_ID
    completed = page.locator(".completed-lessons li")
    assert [completed.nth(i).inner_text() for i in range(completed.count())] == [
        "Kinematics as a program (completed)"
    ]

    page.locator("#progress-controls button").focus()
    page.keyboard.press("Enter")

    assert stored(page) is None
    assert page.locator(".path-card[data-completed='true']").count() == 0
    assert page.locator(".completed-lessons li").count() == 0
    assert "cleared" in summary.inner_text()
    page.reload(wait_until="networkidle")
    assert summary.inner_text().startswith(f"0 of {total} lessons completed.")
    assert stored(page) is None


def test_a_self_check_without_choices_is_marked_done_by_the_reader(
    page: Page, server: SiteServer
):
    open_lesson(page, server, OPEN_LESSON)
    button = page.locator(".exercise.self-check button")

    button.focus()
    page.keyboard.press("Enter")

    assert button.inner_text() == "Mark self-check as not done"
    assert stored(page)["lessons"][OPEN_ID]["completed"] is True
    page.keyboard.press("Enter")
    assert stored(page)["lessons"][OPEN_ID]["selfCheck"]["done"] is False


def test_a_lesson_can_be_marked_completed_and_not_completed_with_the_keyboard(
    page: Page, server: SiteServer
):
    open_lesson(page, server)
    toggle = page.locator(".learner-panel button")

    toggle.focus()
    page.keyboard.press("Enter")
    assert stored(page)["lessons"][CHOICE_ID]["completed"] is True
    assert toggle.inner_text() == "Mark lesson as not completed"
    page.keyboard.press("Space")
    assert stored(page)["lessons"][CHOICE_ID]["completed"] is False


def test_another_tab_that_changes_the_state_updates_the_page(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP)
    first, second = context.new_page(), context.new_page()
    open_lesson(first, server)
    open_lesson(second, server)

    second.locator(".learner-panel button").click()

    first.wait_for_function(
        "document.querySelector('.learner-status')"
        ".textContent.includes('have completed')"
    )
    context.close()


# --- Nothing leaves the browser ------------------------------------------------


def test_no_request_carries_learner_state_and_no_cookie_is_set(
    browser: Browser, server: SiteServer
):
    violations = site_checks.check_learner_state_stays_local(
        browser,
        server,
        CHOICE_LESSON,
        lambda page: choose(page, "No. At some time step"),
    )
    violations += site_checks.check_learner_state_stays_local(
        browser,
        server,
        OPEN_LESSON,
        lambda page: page.locator(".exercise.self-check button").click(),
    )
    assert not violations, describe(violations)


def test_the_learner_script_has_no_request_other_origin_or_other_storage(
    site_dir: Path,
):
    assert (site_dir / "learner" / "progress.js").is_file()
    violations = site_checks.check_learner_script_sources(site_dir)
    assert not violations, describe(violations)


def test_only_the_learner_script_uses_local_storage(site_dir: Path):
    users = [
        script.relative_to(site_dir).as_posix()
        for script in sorted(site_dir.rglob("*.js"))
        if "localStorage" in script.read_text(encoding="utf-8")
        and "site_libs" not in script.parts
    ]
    assert users == ["learner/progress.js"]


# --- Without JavaScript --------------------------------------------------------


def self_check_pages(site_dir: Path) -> list[str]:
    return sorted(
        page.relative_to(site_dir).as_posix()
        for page in (site_dir / "lessons").rglob("index.html")
        if 'class="exercise self-check"' in page.read_text(encoding="utf-8")
    )


def test_every_self_check_is_an_exercise_with_a_visible_solution_without_scripts(
    browser: Browser, server: SiteServer, site_dir: Path
):
    pages = self_check_pages(site_dir)
    assert CHOICE_LESSON in pages and OPEN_LESSON in pages
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    for name in pages:
        page = context.new_page()
        page.goto(server.url + name, wait_until="load")
        check = page.locator(".exercise.self-check")
        assert check.is_visible(), name
        assert check.get_by_text("Self-check.", exact=True).is_visible(), name
        controls = (
            ".exercise.self-check :is(button, fieldset, input), #learner-panel button"
        )
        assert page.locator(controls).count() == 0, name
        summary = check.locator("details.solution > summary")
        assert summary.is_visible(), name
        summary.click()
        assert check.locator("details.solution").get_attribute("open") is not None
        body = check.locator("details.solution > :not(summary)").first
        assert body.is_visible() and body.inner_text().strip(), name
        page.close()
    context.close()


def test_the_choices_read_as_a_list_with_an_explanation_each_without_scripts(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + CHOICE_LESSON, wait_until="load")

    items = page.locator(".exercise.self-check ol.choices > li")

    assert items.count() == 3
    for index in range(items.count()):
        assert items.nth(index).is_visible()
        assert items.nth(index).locator(".feedback").is_visible()
    context.close()


# --- A change of the stored format ---------------------------------------------

VALID = {"version": 1, "lessons": {CHOICE_ID: {"completed": True}}}


@pytest.mark.parametrize(
    "stored_text",
    [
        json.dumps({"version": 0, "lessons": {CHOICE_ID: {"completed": True}}}),
        json.dumps({"version": 2, "lessons": {CHOICE_ID: {"completed": True}}}),
        json.dumps({"version": 1, "lessons": []}),
        json.dumps({"version": 1, "lessons": {CHOICE_ID: {"completed": "yes"}}}),
        json.dumps({"version": 1, "lessons": {CHOICE_ID: {"selfCheck": {"done": 1}}}}),
        json.dumps({"lessons": {CHOICE_ID: {"completed": True}}}),
        "[]",
        "null",
        "not json{",
    ],
    ids=[
        "older",
        "newer",
        "wrong-shape",
        "wrong-type",
        "wrong-self-check",
        "no-version",
        "array",
        "null",
        "malformed",
    ],
)
def test_data_of_another_format_is_discarded_and_the_page_works(
    browser: Browser, server: SiteServer, stored_text: str
):
    context = browser.new_context(viewport=DESKTOP)
    errors: list[str] = []
    page = context.new_page()
    # Any page of the origin lets the test set the stored text before the
    # lesson loads; the errors of the lesson page are the ones that count.
    page.goto(server.url + "about.html", wait_until="load")
    page.evaluate(
        "([key, text]) => localStorage.setItem(key, text)", [STORAGE_KEY, stored_text]
    )
    page.on("pageerror", lambda error: errors.append(str(error)))

    open_lesson(page, server)

    assert errors == []
    assert "not marked" in page.locator(".learner-status").inner_text()
    assert stored(page) is None
    page.locator(".learner-panel button").click()
    assert stored(page) == {"version": 1, "lessons": {CHOICE_ID: {"completed": True}}}
    context.close()


def test_data_of_the_current_format_is_kept(browser: Browser, server: SiteServer):
    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    page.goto(server.url + PATH_PAGE, wait_until="load")
    page.evaluate(
        "([key, text]) => localStorage.setItem(key, text)",
        [STORAGE_KEY, json.dumps(VALID)],
    )

    open_lesson(page, server)

    assert "have completed" in page.locator(".learner-status").inner_text()
    assert stored(page) == VALID
    context.close()


def test_a_browser_that_gives_no_storage_keeps_progress_until_the_page_is_left(
    browser: Browser, server: SiteServer
):
    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(
        "Object.defineProperty(window, 'localStorage',"
        " {get() { throw new DOMException('denied', 'SecurityError'); }})"
    )
    page = context.new_page()
    open_lesson(page, server)

    page.locator(".learner-panel button").click()

    status = page.locator(".learner-status").inner_text()
    assert "have completed" in status and "does not allow" in status
    context.close()


# --- Accessibility -------------------------------------------------------------


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_the_accessibility_scan_passes_in_several_states_of_the_controls(
    browser: Browser, server: SiteServer, viewport: dict[str, int]
):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    options = {
        "runOnly": {"type": "tag", "values": WCAG_TAGS},
        "resultTypes": ["violations"],
    }
    violations: list[str] = []

    def scan(state: str) -> None:
        results = Axe().run(page, options=options)
        violations.extend(
            f"{finding['id']} at {node['target']} ({state})"
            for finding in results.response["violations"]
            for node in finding["nodes"]
        )

    open_lesson(page, server)
    scan("lesson, before answering")
    choose(page, "Yes. Every halving")
    scan("lesson, wrong answer")
    choose(page, "No. At some time step")
    scan("lesson, correct answer")
    open_lesson(page, server, OPEN_LESSON)
    page.locator(".exercise.self-check button").click()
    scan("open self-check, marked done")
    page.goto(server.url + PATH_PAGE, wait_until="networkidle")
    scan("learning path, with progress")
    context.close()
    assert not violations, "\n".join(violations)


def test_the_controls_have_visible_labels_and_focus_rings(
    page: Page, server: SiteServer
):
    open_lesson(page, server)

    for selector in (
        CHOICES + " input",
        ".exercise.self-check button",
        ".learner-panel button",
    ):
        control = page.locator(selector).first
        control.focus()
        style = control.evaluate(
            "e => { const s = getComputedStyle(e);"
            " return [s.outlineStyle, parseFloat(s.outlineWidth)]; }"
        )
        assert style[0] not in ("none", "hidden") and style[1] >= 2, selector
    assert page.locator(CHOICES + " legend").inner_text() == "Choose one answer"


# --- The export ----------------------------------------------------------------


def test_the_built_site_carries_the_learning_path_as_data(site_dir: Path):
    built = json.loads((site_dir / "path.json").read_text(encoding="utf-8"))

    assert built == path_export(LearningPath.read(SITE_SOURCE))
    assert built["lessons"]
    for lesson in built["lessons"]:
        assert (site_dir / lesson["page"]).is_file(), lesson["id"]


def test_every_card_of_the_learning_path_names_a_lesson_of_the_export(
    page: Page, server: SiteServer, site_dir: Path
):
    ids = {
        lesson["id"]
        for lesson in json.loads((site_dir / "path.json").read_text())["lessons"]
    }
    page.goto(server.url + PATH_PAGE, wait_until="load")

    cards = page.locator(".path-card").evaluate_all(
        "cards => cards.map(card => card.dataset.lessonId)"
    )

    assert cards and set(cards) == ids
