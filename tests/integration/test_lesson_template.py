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

from pbc.authoring import STRANDS, LearningPath
from pbc.authoring.path import Lesson

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
        page.write_text(front_matter + separator)
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
            "pbc.mechanics.kinematics:euler_step"
        ]
    assert not violations, describe(violations)
    # The marker of the template reached the page as a block and as a phrase.
    assert (built / page).read_text().count('class="not-verified-label"') == 2
    # The new lesson joined the learning path: its header places it after the
    # last mechanics lesson of the site, and the path page lists all of them.
    header = (built / page).read_text().split('class="lesson-header"')[1]
    # The header places it in its course, after the lessons the course has.
    in_course = len(PATH.in_course(PATH.courses[0]))
    assert f"lesson {len(MECHANICS) + 1} of {in_course + 1}" in header
    assert "Replace: what the reader can do after the lesson" in header
    previous = Path(MECHANICS[-1].page).parent.name
    assert f'href="../{previous}/index.html"' in header
    # Each entry of the path page links the lesson and its prerequisites, in
    # the course and in every method path the lesson is listed under.
    path_page = (built / "path/index.html").read_text()
    new = Lesson(
        **{
            **PATH.lesson(MECHANICS[0].id).__dict__,
            "strand": "mechanics",
            "prerequisites": (),
            "related": (),
        }
    )
    mechanics_ids = {lesson.id for lesson in MECHANICS}
    links = sum(
        (1 + len(lesson.methods))
        * (
            (lesson.strand == "mechanics")
            + sum(p in mechanics_ids for p in lesson.prerequisites)
        )
        for lesson in (*PATH.lessons, new)
    )
    lists, graph = path_page.split('<div class="prerequisite-graph"')
    graph = graph.split("</svg>")[0]
    assert lists.count('<a href="../lessons/mechanics/') == links
    # The graph has a node for every lesson, the new one too.
    assert graph.count("<a href=") == len(PATH.lessons) + 1
    assert f'href="../{page}"' in graph
