"""The Python checks of verify.conf fail on input that violates them.

Each test runs the command verification runs, in a directory that holds the
project's tool configuration and one violating file.
"""

import shutil
from pathlib import Path

import pytest
from support.checks import output, run_check
from support.paths import REPO_ROOT


@pytest.fixture
def project(tmp_path: Path) -> Path:
    shutil.copy(REPO_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    return tmp_path


def test_lint_fails_on_an_unused_import(project: Path):
    (project / "module.py").write_text("import os\n")

    result = run_check("lint", cwd=project)

    assert result.returncode != 0
    assert "F401" in output(result)


def test_format_fails_on_unformatted_code(project: Path):
    (project / "module.py").write_text("x = [1,2,\n     3]\n")

    result = run_check("format", cwd=project)

    assert result.returncode != 0
    assert "would be reformatted" in output(result)


def test_unit_tests_fail_on_a_failing_test(project: Path):
    tests = project / "tests" / "unit"
    tests.mkdir(parents=True)
    (tests / "test_violation.py").write_text(
        "def test_violation():\n    assert 1 + 1 == 3\n"
    )

    result = run_check("unit-tests", cwd=project)

    # Exit status 1 is pytest's "tests failed"; other statuses are usage or
    # collection errors, which would not show that a failing test is caught.
    assert result.returncode == 1, output(result)
    assert "1 failed" in output(result)
