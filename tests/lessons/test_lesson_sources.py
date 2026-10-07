"""Required checks on the lesson sources (architecture, "Lesson source
checks"). docs/authoring.md describes the format they enforce.
"""

from pathlib import Path

import pytest
from support import lesson_checks
from support.paths import REPO_ROOT
from support.site_checks import describe


@pytest.fixture(scope="session")
def repository(request: pytest.FixtureRequest) -> Path:
    return Path(request.config.getoption("--repository") or REPO_ROOT).resolve()


def test_there_is_a_lesson_to_check(repository: Path):
    # Guards the tests below: without lessons they would pass on nothing.
    assert lesson_checks.lesson_pages(repository)


def test_front_matter_follows_the_schema(repository: Path):
    violations = lesson_checks.check_metadata(repository)
    assert not violations, describe(violations)


def test_lessons_have_the_required_sections(repository: Path):
    violations = lesson_checks.check_sections(repository)
    assert not violations, describe(violations)


def test_lessons_form_a_learning_path(repository: Path):
    violations = lesson_checks.check_path(repository)
    assert not violations, describe(violations)


def test_displayed_code_is_executed_or_marked_not_verified(repository: Path):
    violations = lesson_checks.check_displayed_code(repository)
    assert not violations, describe(violations)


def test_figures_are_drawn_by_cells_and_have_alt_text(repository: Path):
    violations = lesson_checks.check_figures(repository)
    assert not violations, describe(violations)


def test_no_generated_artifact_is_committed(repository: Path):
    violations = lesson_checks.check_committed_files(repository)
    assert not violations, describe(violations)
