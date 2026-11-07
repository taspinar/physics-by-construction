"""A second lesson made from the template, as docs/authoring.md describes,
passes the lesson source checks and builds next to the lessons of the site.
"""

import re
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import Browser
from support import lesson_checks, site_checks
from support.checks import output, run_check
from support.paths import REPO_ROOT, SITE_SOURCE
from support.site_checks import describe
from support.site_server import SiteServer

from pbc.authoring import STRANDS, LearningPath

TEMPLATE = REPO_ROOT / "docs" / "lesson-template.qmd"
# The new lesson takes the next position of the mechanics strand, after the
# lessons the site has.
PATH = LearningPath.read(SITE_SOURCE)
MECHANICS = PATH.in_strand(STRANDS[0])
ORDER = len(MECHANICS) + 1
LESSON = f"lessons/mechanics/{ORDER:02d}-made-from-the-template"
# The two values the guide tells an author to set before anything else.
PLACEHOLDERS = {
    "  id: REPLACE-ME\n": "  id: made-from-the-template\n",
    "  order: 0\n": f"  order: {ORDER}\n",
    # The one entry of the register that the Go deeper example may name.
    "REPLACE-WITH-A-REGISTER-KEY": "euler-local-global-error",
}


@pytest.fixture(scope="module")
def repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the site sources with one more lesson, made from the template.

    The lessons of the site are reduced to their front matter. The learning
    path, the header of the new lesson, and the path page are generated from
    front matter alone, so the new lesson still joins the path; the bodies
    would only make the build execute every lesson again, which
    ``site-build`` already does (ADR 003, first response to the time budget).
    """
    repository = tmp_path_factory.mktemp("template") / "repository"
    shutil.copytree(
        SITE_SOURCE,
        repository / "site",
        ignore=shutil.ignore_patterns("_site", ".quarto", "*_files", "*.quarto_ipynb"),
    )
    for page in lesson_checks.lesson_pages(repository):
        front_matter, separator, _ = page.read_text().partition("\n---\n")
        assert separator, f"{page} has no front matter"
        # The bodies are gone, so a 'preview' would name a cell that is not
        # there; those lessons get the conceptual fallback.
        front_matter = re.sub(r"^  preview: .*\n", "", front_matter, flags=re.M)
        page.write_text(front_matter + separator)
    # Without the bodies there are no claims, so the worked examples of "How
    # we verify the science" would name missing targets and fail the build,
    # as they must (tests/integration/test_verify_build.py); the page is not
    # what this copy tests.
    (repository / "site" / "verify.qmd").unlink()
    text = TEMPLATE.read_text()
    for placeholder, value in PLACEHOLDERS.items():
        assert placeholder in text
        text = text.replace(placeholder, value)
    page = repository / "site" / LESSON / "index.qmd"
    page.parent.mkdir(parents=True)
    page.write_text(text)
    return repository


def _copy_with_experiment(tmp_path: Path, *, module: bool, unit_test: bool) -> Path:
    """A repository with the lesson made from the template, as the guide says:
    its experiment module and the unit test of it renamed for the new lesson
    id (docs/authoring.md, "The experiment of a lesson")."""
    old = "lesson_template"
    new = "made_from_the_template"
    text = TEMPLATE.read_text()
    for placeholder, value in PLACEHOLDERS.items():
        text = text.replace(placeholder, value)
    page = tmp_path / "site" / LESSON / "index.qmd"
    page.parent.mkdir(parents=True)
    page.write_text(text.replace(old, new))
    if module:
        source = REPO_ROOT / f"src/pbc/mechanics/experiments/{old}.py"
        target = tmp_path / f"src/pbc/mechanics/experiments/{new}.py"
        target.parent.mkdir(parents=True)
        shutil.copy(source, target)
    if unit_test:
        target = tmp_path / f"tests/unit/test_{new}_experiment.py"
        target.parent.mkdir(parents=True)
        target.write_text("")
    return tmp_path


def test_lesson_made_from_the_template_passes_the_experiment_check(tmp_path: Path):
    repository = _copy_with_experiment(tmp_path, module=True, unit_test=True)

    violations = lesson_checks.check_experiments(repository, required=True)

    assert not violations, describe(violations)


@pytest.mark.parametrize(
    ("module", "unit_test", "message"),
    [
        (False, True, "has no file src/pbc/mechanics/experiments/"),
        (True, False, "has no unit test tests/unit/test_made_from_the_template"),
    ],
)
def test_lesson_made_from_the_template_without_its_experiment_fails_the_check(
    tmp_path: Path, module: bool, unit_test: bool, message: str
):
    repository = _copy_with_experiment(tmp_path, module=module, unit_test=unit_test)

    problems = describe(lesson_checks.check_experiments(repository, required=True))

    assert message in problems


def test_template_as_copied_is_reported_until_its_placeholders_are_set(
    tmp_path: Path,
):
    page = tmp_path / "site" / LESSON / "index.qmd"
    page.parent.mkdir(parents=True)
    shutil.copy(TEMPLATE, page)

    problems = describe(lesson_checks.check_metadata(tmp_path))

    assert "'lesson.id'" in problems and "'lesson.order'" in problems


def test_lesson_made_from_the_template_passes_the_source_checks(repository: Path):
    violations = [
        *lesson_checks.check_metadata(repository),
        *lesson_checks.check_sections(repository),
        *lesson_checks.check_displayed_code(repository),
        *lesson_checks.check_figures(repository),
        *lesson_checks.check_format_2(repository),
    ]
    # The other lessons are reduced to their front matter and lack the sections.
    violations = [v for v in violations if v.page == f"site/{LESSON}/index.qmd"]

    assert not violations, describe(violations)


def test_lesson_made_from_the_template_builds_with_every_construct(
    repository: Path, browser: Browser
):
    built = repository / "built"
    result = run_check("site-build", repository / "site", built)
    assert result.returncode == 0, output(result)

    page = f"{LESSON}/index.html"
    violations = site_checks.check_sections(
        built, page, [*lesson_checks.REQUIRED_SECTIONS, "exercises"]
    )
    violations += site_checks.check_images(built)
    with SiteServer(built, "/sub-path/") as server:
        violations += site_checks.check_not_verified_labels(browser, server, built)
        violations += site_checks.check_displayed_code(
            browser, server, built, REPO_ROOT
        )
        assert site_checks.excerpt_sources(browser, server, page) == [
            "pbc.mechanics.kinematics:euler_step",
            "pbc.mechanics.experiments.lesson_template:",
            "pbc.mechanics.experiments.lesson_template:braking_cart",
            "pbc.mechanics.experiments.lesson_template:draw_replace_with_a_name",
            "pbc.mechanics.experiments.lesson_template:largest_error",
        ]
    assert not violations, describe(violations)
    # The marker of the template reached the page as a block and as a phrase.
    assert (built / page).read_text().count('class="not-verified-label"') == 2
    # The new lesson joined the learning path: its header places it after the
    # last mechanics lesson of the site, and the path page lists all of them.
    header = (built / page).read_text().split('class="lesson-header"')[1]
    # The header places it in its course, after the lessons the course has.
    in_course = len(PATH.in_course(PATH.courses[0]))
    # It has no slot, so the course view puts it after every lesson with one
    # and, among those without, by the linear order.
    courses = PATH.in_course(PATH.courses[0])
    before = sum(1 for item in courses if item.slot or item.strand == STRANDS[0].id)
    assert f"lesson {before + 1} of {in_course + 1}" in header
    assert "Replace: what the reader can do after the lesson" in header
    previous = Path(MECHANICS[-1].page).parent.name
    assert f'href="../{previous}/index.html"' in header
    # The path page shows each lesson once, as a row of one sequence of the
    # course atlas (F133): the new lesson has no slot and is no Lean lesson,
    # so it is a row of its course, after the course's slots.
    path_page = (built / "path/index.html").read_text()
    rows = re.findall(
        r'<li class="path-card[^"]*" data-state="published" data-lesson-id="([^"]+)"',
        path_page,
    )
    assert len(rows) == len(set(rows)) == len(PATH.lessons) + 1
    assert {lesson.id for lesson in PATH.lessons} < set(rows)
    assert path_page.count(f'href="../{page}"') == 1
    mechanics = re.search(
        r'<details [^>]*id="course-mechanics".*?</details>', path_page
    ).group(0)
    assert f'href="../{page}"' in mechanics
