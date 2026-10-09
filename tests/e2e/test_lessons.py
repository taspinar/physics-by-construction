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
NEWTONS_LAWS = "lessons/mechanics/02-newtons-laws/index.html"
PROJECTILE = "lessons/mechanics/03-projectile-motion-with-drag/index.html"
OSCILLATOR = "lessons/mechanics/04-harmonic-oscillator/index.html"
INTEGRATORS = "lessons/mechanics/05-numerical-integrators/index.html"
ENERGY = "lessons/mechanics/06-energy-conservation/index.html"
MOMENTUM = "lessons/mechanics/07-momentum-and-collisions/index.html"
KEPLER = "lessons/mechanics/08-kepler-orbit/index.html"


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


def test_the_mechanics_lessons_are_among_the_lessons():
    # Guards the parametrized tests below: without lessons they would not run.
    assert {
        KINEMATICS,
        NEWTONS_LAWS,
        PROJECTILE,
        OSCILLATOR,
        INTEGRATORS,
        ENERGY,
        MOMENTUM,
        KEPLER,
    } <= set(LESSONS)


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
    page_without_scripts.locator("details.solution > summary").first.click()
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


# Rows of the tables the lessons print, at the precision they display. They
# were produced on macOS (arm64); the site is built on Linux (x86-64). The
# same rows on both is what "reproduces at the displayed precision" means
# across platforms, so these lists are checked wherever the tests run.
REFERENCE_ROWS = {
    KINEMATICS: [
        "2.4 3.234 2.057 -11.536 -11.536",
        "24 0.100000 1.176798",
        "768 0.003125 0.036775 2.0000",
        "768 0.003125 0.015908 0.999",
        "steps needed: 28244",
        "error with them: 0.99997 mm",
        "480 -0.018750 -0.056172 0.998",
        "size of the error after 2.4 s: 0.000000000 m",
    ],
    NEWTONS_LAWS: [
        "time constant 2.0 s, terminal speed 19.613 m/s",
        "10.0 19.497 19.481 157.139 157.171",
        "3200 0.003125 0.000516 -0.001032 0.999",
        "back at the ground after 2.55 s, 17.32 m away",
        "0.0 49.0 -24.5 85.8 -79.7 168.6 -203.8 354.7 -483.1 773.6 -1111.4",
        "from the simulation: 9.209 s",
        "position then: 1.0648 m, exact 1.0000 m",
    ],
    PROJECTILE: [
        "drag constant c = 1.06e-03 kg/m, terminal speed 23.2 m/s",
        "with drag: range 35.40 m, time of flight 3.01 s, highest point 11.22 m",
        "exact drag-free range: 63.73 m",
        "0.000781 63.7461 0.0138 0.0138",
        "0.000781 35.4021 -0.0041 0.999 35.3980",
        "without drag: longest throw 63.77 m at 45.0 degrees",
        "95 per cent of it after 4.33 s",
        "drag shortens the range by 4.1 per cent for steel and 44 per cent for tennis",
    ],
    OSCILLATOR: [
        "omega 2.0 rad/s, period 3.1416 s, time step 0.0491 s, omega dt = 0.0982",
        "8.25 -1.664 -0.707 2.994 1.414",
        "energy after 3 periods: 6.307 times the initial energy; predicted 6.307",
        "4096 0.00153 1.0293 0.02891 1.000",
        "steps per period needed: 39676",
        "2 1.000 0.857 0.793 0.734",
        "5 1.001 0.539 0.396 0.291",
        "semi-axes of the exact orbit: 1.000 m and 0.500 m",
    ],
    INTEGRATORS: [
        "explicit Euler 3.223 0.636 10.487637 150",
        "800 5.06e-02 (1.04) 3.96e-03 (1.01) 3.45e-05 (2.00) 3.99e-10 (4.00)",
        "symplectic Euler energy between 0.91060 and 1.10886 times the start,"
        " 0.91071 at the end; 32000 calls",
        "Runge-Kutta 4 energy between 0.97497 and 1.00000 times the start,"
        " 0.97497 at the end; 128000 calls",
        "3.0 2.094 1.35e+73 1.08e+54 4.01e+52 1.81e-33",
        "320 4.40e-05 (2.00) 2.15e-11 (4.00)",
        "Runge-Kutta 4 21 8.4e-04 168",
        "Runge-Kutta 4 50 400 2.6e-05",
    ],
    ENERGY: [
        "170° 4.8944 2.4394 4.8944",
        "released at 120°: period 2.7546 s, 1.3729 T0; 2746 steps of 0.02006 s",
        "velocity Verlet 7.4e-04 1.0000",
        "400 8.9e-01 (1.01) 6.5e-03 (1.00) 4.6e-05 (2.00) 1.5e-09 (4.85)",
        "velocity Verlet 7.4e-04 -0.98 -1.97 -3.74",
        "explicit Euler 0.9924 1.3224 3289°",
        "explicit Euler passes the energy of the top after 1.07 s, in swing 1",
        "from the series: 22.9°; from the exact period: 22.8°",
        "400 10.6315 10.6307 8.3e-04 4.6e-05",
        "steps per T0 needed: 861",
    ],
    MOMENTUM: [
        "reduced mass 0.75 kg, omega = 4.0 rad/s, period 1.5708 s",
        "contact time pi sqrt(mu / k) = 0.0811 s; the spheres overlap from 0.533 s"
        " to 0.612 s",
        "10 -1.00095 0.50048 9.5e-04 1.8e-02",
        "1000 0.0702 1139 54.45° -5.55° 90.00°",
        "0.1 0.3306 0.3306",
        "0.00 -0.1301 +0.1499 +0.9801",
        "1 kg 1.0000 0.5994 0.6667 0.6664",
    ],
    KEPLER: [
        "perihelion 0.50 AU at 51.6 km/s, aphelion 1.50 AU",
        "Runge-Kutta 4 1.6e-03 6.3e-05 9.2e-06",
        "3200 1.4e+00 (0.58) 9.0e-03 (0.99) 3.5e-04 (2.00) 5.9e-10 (4.07)",
        "semi-major axis between 0.9710 and 1.0000 AU",
        "perihelion turned by -872.3° in all, -0.872° per orbit",
        "200 -0.2208°",
        "the star moves at between 17.1 and 51.6 m/s",
        "4.0 8.0000 1.0000",
        "99 per cent: after 30 years at 22.7 AU, farthest 24.6 AU; a = 12.6 AU,"
        " e = 0.960, period 45 yr",
        "the Sun moves at between 11.9 and 13.1 m/s about the centre of mass",
    ],
}


@pytest.mark.parametrize("lesson", sorted(REFERENCE_ROWS))
def test_the_lessons_display_the_same_numbers_on_every_platform(
    page: Page, server: SiteServer, lesson: str
):
    page.goto(server.url + lesson, wait_until="load")

    printed = [
        " ".join(line.split())
        for output in page.locator("main .cell-output-stdout").all_text_contents()
        for line in output.splitlines()
    ]
    missing = [row for row in REFERENCE_ROWS[lesson] if row not in printed]
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
    if any(command.endswith("check-lean.sh") for command in commands):
        # A learner's first run fetches the Mathlib build cache. The test
        # shares the packages of this checkout, as test_lean_check.py does, so
        # it neither downloads Mathlib again nor builds it.
        (clone / "lean" / ".lake").mkdir()
        (clone / "lean" / ".lake" / "packages").symlink_to(
            REPO_ROOT / "lean" / ".lake" / "packages", target_is_directory=True
        )

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
