"""A second lesson made from the template, as docs/authoring.md describes,
passes the lesson source checks and builds next to the lessons of the site.
"""

import shutil
from pathlib import Path

import pytest
from playwright.sync_api import Browser
from support import lesson_checks, site_checks
from support.checks import output, run_check
from support.paths import REPO_ROOT, SITE_SOURCE
from support.site_checks import describe
from support.site_server import SiteServer

TEMPLATE = REPO_ROOT / "docs" / "lesson-template.qmd"
LESSON = "lessons/mechanics/02-made-from-the-template"
# The two values the guide tells an author to set before anything else.
PLACEHOLDERS = {
    "  id: REPLACE-ME\n": "  id: made-from-the-template\n",
    "  order: 0\n": "  order: 2\n",
}


@pytest.fixture(scope="module")
def repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A copy of the site sources with one more lesson, made from the template."""
    repository = tmp_path_factory.mktemp("template") / "repository"
    shutil.copytree(
        SITE_SOURCE,
        repository / "site",
        ignore=shutil.ignore_patterns("_site", ".quarto", "*_files", "*.quarto_ipynb"),
    )
    text = TEMPLATE.read_text()
    for placeholder, value in PLACEHOLDERS.items():
        assert placeholder in text
        text = text.replace(placeholder, value)
    page = repository / "site" / LESSON / "index.qmd"
    page.parent.mkdir(parents=True)
    page.write_text(text)
    return repository


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
    ]

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
            "pbc.mechanics.kinematics:euler_step"
        ]
    assert not violations, describe(violations)
    # The marker of the template reached the page as a block and as a phrase.
    assert (built / page).read_text().count('class="not-verified-label"') == 2
