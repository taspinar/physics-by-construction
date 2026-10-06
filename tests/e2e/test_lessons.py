"""Required checks on the built lesson pages (docs/authoring.md).

The checks of test_built_site.py cover lesson pages like every other page:
alt text and dimensions of figures, readability without JavaScript, the
accessibility scan. The checks here are about what only a lesson promises.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page
from support import lesson_checks, site_checks
from support.paths import REPO_ROOT, SITE_SOURCE
from support.site_checks import DESKTOP, PHONE, describe
from support.site_server import SiteServer, configured_repository_url

# A lesson page may take this long to execute and render (architecture, "CI
# pipeline and time budget").
LESSON_BUDGET_SECONDS = 30

# Every lesson of the repository, as the path of its built page.
LESSONS = [
    page.relative_to(SITE_SOURCE).with_suffix(".html").as_posix()
    for page in lesson_checks.lesson_pages(REPO_ROOT)
]
KINEMATICS = "lessons/mechanics/01-kinematics-as-a-program/index.html"


@pytest.fixture
def page(browser: Browser) -> Page:
    context = browser.new_context(viewport=DESKTOP)
    yield context.new_page()
    context.close()


@pytest.fixture
def page_without_scripts(browser: Browser) -> Page:
    context = browser.new_context(viewport=DESKTOP, java_script_enabled=False)
    yield context.new_page()
    context.close()


def _head_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_the_first_lesson_is_among_the_lessons():
    # Guards the parametrized tests below: without lessons they would not run.
    assert KINEMATICS in LESSONS


@pytest.mark.parametrize("lesson", LESSONS)
def test_lesson_is_published_with_every_required_section(site_dir: Path, lesson: str):
    violations = site_checks.check_sections(
        site_dir, lesson, lesson_checks.REQUIRED_SECTIONS
    )
    assert not violations, describe(violations)
    practice = [
        section
        for section in lesson_checks.PRACTICE_SECTIONS
        if not site_checks.check_sections(site_dir, lesson, [section])
    ]
    assert practice, f"{lesson} has neither exercises nor an interactive visualization"


@pytest.mark.parametrize("lesson", LESSONS)
def test_home_page_links_to_the_lesson(page: Page, server: SiteServer, lesson: str):
    page.goto(server.url + "index.html", wait_until="load")

    targets = page.locator("main a").evaluate_all("links => links.map(a => a.href)")
    assert server.url + lesson in targets


def test_material_marked_not_verified_shows_a_label(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_not_verified_labels(browser, server, site_dir)
    assert not violations, describe(violations)


def test_the_not_verified_label_is_visible_text_on_the_sample_page(
    page_without_scripts: Page, server: SiteServer
):
    # The rendering-check page marks one block and one phrase in the open
    # and one block inside a solution. Without this test the check above
    # could pass because nothing on the site is marked.
    page_without_scripts.goto(server.url + "rendering-check.html", wait_until="load")

    labels = page_without_scripts.locator(".not-verified .not-verified-label")
    assert labels.count() == 3
    in_solution = page_without_scripts.locator("details.solution .not-verified-label")
    assert in_solution.count() == 1
    assert not in_solution.is_visible()
    page_without_scripts.locator("details.solution > summary").click()
    for index in range(labels.count()):
        assert labels.nth(index).is_visible()
        assert "not verified" in labels.nth(index).inner_text().lower()


def test_excerpts_are_identical_to_their_source_and_every_cell_ran(
    browser: Browser, server: SiteServer, site_dir: Path
):
    violations = site_checks.check_displayed_code(browser, server, site_dir, REPO_ROOT)
    assert not violations, describe(violations)


def test_the_first_lesson_shows_its_program_by_reference(
    browser: Browser, server: SiteServer
):
    # Without excerpts on the page, the comparison above would compare nothing.
    assert set(site_checks.excerpt_sources(browser, server, KINEMATICS)) >= {
        "pbc.mechanics.kinematics:State",
        "pbc.mechanics.kinematics:euler_step",
        "pbc.mechanics.kinematics:simulate",
    }


def test_the_first_lesson_shows_mathml_results_and_figures(
    page_without_scripts: Page, server: SiteServer
):
    page = page_without_scripts
    page.goto(server.url + KINEMATICS, wait_until="load")

    widths = page.locator("main math").evaluate_all(
        "equations => equations.map(e => e.getBoundingClientRect().width)"
    )
    assert len(widths) >= 10 and all(width > 0 for width in widths)
    assert page.locator(".MathJax, .katex, mjx-container").count() == 0
    # Numbers are what executed cells printed, and both figures were drawn.
    assert page.locator("main .cell-output-stdout").count() >= 5
    figures = page.locator("main img.figure-img")
    assert figures.count() == 2
    assert all(
        figures.evaluate_all(
            "images => images.map(i => i.complete && i.naturalWidth > 0 && !!i.alt)"
        )
    )


# Rows of the tables the first lesson prints, at the precision it displays.
# They were produced on macOS (arm64); the site is built on Linux (x86-64).
# The same rows on both is what "reproduces at the displayed precision"
# means across platforms, so this list is checked wherever the tests run.
KINEMATICS_REFERENCE = [
    "2.4 3.234 2.057 -11.536 -11.536",
    "24 0.100000 1.176798",
    "768 0.003125 0.036775 2.0000",
    "768 0.003125 0.015908 0.999",
    "steps needed: 28244",
    "error with them: 0.99997 mm",
    "480 -0.018750 -0.056172 0.998",
    "size of the error after 2.4 s: 0.000000000 m",
]


def test_the_first_lesson_displays_the_same_numbers_on_every_platform(
    page: Page, server: SiteServer
):
    page.goto(server.url + KINEMATICS, wait_until="load")

    printed = [
        " ".join(line.split())
        for output in page.locator("main .cell-output-stdout").all_text_contents()
        for line in output.splitlines()
    ]
    missing = [row for row in KINEMATICS_REFERENCE if row not in printed]
    assert not missing, f"not printed by the page: {missing}"


def test_solutions_open_without_javascript(
    page_without_scripts: Page, server: SiteServer
):
    page = page_without_scripts
    page.goto(server.url + KINEMATICS, wait_until="load")

    solutions = page.locator("#exercises .exercise details.solution")
    assert solutions.count() == page.locator("#exercises .exercise").count() >= 2
    first = solutions.first
    answer = first.locator(".cell-output-stdout")
    assert not answer.is_visible()
    first.locator("summary").click()
    assert answer.is_visible()


# Runs in the page. Returns the links that extend past the right edge of the
# screen. A long file path in a link does that when it cannot wrap, and the
# page clips it without scrolling, so the rule for page width does not see it.
_CLIPPED_LINKS = """
() => [...document.querySelectorAll("main a")]
  .filter((link) => !link.closest("pre") && link.getBoundingClientRect().right
    > document.documentElement.clientWidth + 1)
  .map((link) => link.textContent.trim().slice(0, 60))
"""


@pytest.mark.parametrize("lesson", LESSONS)
def test_links_to_files_fit_a_phone_screen(
    browser: Browser, server: SiteServer, lesson: str
):
    context = browser.new_context(viewport=PHONE, java_script_enabled=False)
    page = context.new_page()
    page.goto(server.url + lesson, wait_until="load")

    clipped = page.evaluate(_CLIPPED_LINKS)
    context.close()

    assert not clipped, f"cut off at the edge of the screen: {clipped}"


def _reproduce_commands(page: Page, server: SiteServer, lesson: str) -> list[str]:
    page.goto(server.url + lesson, wait_until="load")
    listing = page.locator("#reproduce-this pre.reproduce-commands code")
    return listing.text_content().strip().splitlines()


@pytest.mark.parametrize("lesson", LESSONS)
def test_reproduce_section_names_the_built_commit(
    page: Page, server: SiteServer, lesson: str
):
    commands = _reproduce_commands(page, server, lesson)

    # The repository is the one the site links to, at the commit that was built.
    repository = configured_repository_url(SITE_SOURCE)
    assert commands[0] == f"git clone {repository}.git"
    assert f"git checkout {_head_commit()}" in commands
    source = Path(lesson).with_suffix(".qmd").as_posix()
    assert commands[-1] == f"uv run --locked quarto render site/{source}"


def _clone_of_the_working_tree(target: Path) -> Path:
    """Copy what a clone of this checkout would hold: the files Git tracks
    or would add."""
    for file in lesson_checks.committed_files(REPO_ROOT):
        (target / file).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / file, target / file)
    return target


@pytest.mark.parametrize("lesson", LESSONS)
def test_reproduce_commands_regenerate_the_page_within_the_time_budget(
    page: Page, server: SiteServer, site_dir: Path, tmp_path: Path, lesson: str
):
    commands = _reproduce_commands(page, server, lesson)
    setup = commands.index("uv sync --locked")
    assert commands[0].startswith("git clone ") and commands[1].startswith("cd ")
    clone = _clone_of_the_working_tree(tmp_path / "clone")

    # The commands after the setup, exactly as the page shows them. They use
    # the environment of this checkout instead of a second 'uv sync'.
    seconds = {}
    for command in commands[setup + 1 :]:
        started = time.monotonic()
        result = subprocess.run(
            ["bash", "-eo", "pipefail", "-c", command],
            cwd=clone,
            env={**os.environ, "UV_PROJECT": str(REPO_ROOT)},
            capture_output=True,
            text=True,
            check=False,
        )
        seconds[command] = time.monotonic() - started
        assert result.returncode == 0, f"{command}\n{result.stdout}{result.stderr}"

    # Every number and figure of the page: the regenerated page and its
    # figure files are the published ones, byte for byte.
    reproduced = clone / "site" / "_site" / lesson
    assert reproduced.read_bytes() == (site_dir / lesson).read_bytes()
    figures = sorted(
        file.relative_to(site_dir)
        for file in (site_dir / lesson).parent.rglob("*")
        if file.is_file() and file.suffix != ".html"
    )
    assert figures, "the lesson has no figure to compare"
    for figure in figures:
        regenerated = clone / "site" / "_site" / figure
        assert regenerated.read_bytes() == (site_dir / figure).read_bytes(), figure

    assert seconds[commands[-1]] < LESSON_BUDGET_SECONDS
