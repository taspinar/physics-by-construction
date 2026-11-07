"""The budget of a lesson: one rule for every lesson, from one file
(scripts/lesson-budgets.conf, ADR 020 decision 6). A duration below the
warning threshold passes silently, one from the threshold up to the limit of
the lesson passes with a warning, and one at its limit or above fails. The
shell check and the reproduction tests read the same file and judge every
duration the same way. No test here depends on a real run time."""

import re
import subprocess
import warnings
from pathlib import Path

import pytest
from support import lesson_checks
from support.budgets import (
    BUDGETS_FILE,
    LessonTimeWarning,
    budget_seconds,
    check_within_budget,
    read_budgets,
    read_settings,
    verdict,
)
from support.paths import REPO_ROOT, SCRIPTS, SITE_SOURCE

MONTE_CARLO = "lessons/agents-abm/01-particles-in-a-box"
# Raised from 60 to 90 seconds by the owner on 2026-10-24 (#272): its
# reproduction measured 67 to 69 seconds, above the default limit of 60.
MONTE_CARLO_SECONDS = 90
# The lessons that had a line of their own at 60 seconds (#261), or that
# #374 proposed, and that the default limit covers now.
UNDER_THE_DEFAULT = [
    "lessons/astrophysics/01-the-three-body-problem",
    "lessons/astrophysics/05-relativistic-orbits",
    "lessons/fluids/06-vortex-formation-and-flow-around-obstacles",
    "lessons/mechanics/08-kepler-orbit",
    "lessons/mechanics/11-gravitational-wave-strain",
    "lessons/mechanics/12-inverse-physics-parameter-discovery",
]
SCRIPT = SCRIPTS / "check-lesson-pages.sh"
E2E = REPO_ROOT / "tests/e2e/test_lessons.py"
LESSONS = [
    page.parent.relative_to(SITE_SOURCE).as_posix()
    for page in lesson_checks.lesson_pages(REPO_ROOT)
]

TABLE = """\
# a comment

warn-seconds: 30
limit-seconds: 60

lessons/a/b | 90 | slower, because
"""


def table(tmp_path: Path, text: str = TABLE) -> Path:
    path = tmp_path / "budgets.conf"
    path.write_text(text)
    return path


def shell(call: str, budgets_file: Path = BUDGETS_FILE) -> subprocess.CompletedProcess:
    """The shell check's own functions, run alone on a table."""
    source = SCRIPT.read_text()
    functions = []
    for name in ("raw_setting", "setting_of", "budget_of", "verdict_of"):
        function = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", source, re.M | re.S)
        assert function, f"the check has no {name} function"
        functions.append(function.group(0))
    script = (
        "set -euo pipefail\n"
        f"budgets_file='{budgets_file}'\n"
        'fail() { echo "Error: $*" >&2; exit 1; }\n' + "".join(functions) + call
    )
    return subprocess.run(
        ["bash", "-c", script, "bash"], capture_output=True, text=True, check=False
    )


def shell_budget(lesson: str, budgets_file: Path = BUDGETS_FILE) -> int:
    result = shell(f'budget_of "{lesson}"', budgets_file)
    assert result.returncode == 0, result.stderr
    return int(result.stdout)


def shell_verdict(lesson: str, seconds: int, budgets_file: Path = BUDGETS_FILE) -> str:
    result = shell(f'verdict_of "{lesson}" {seconds}', budgets_file)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_the_warning_threshold_is_30_seconds_and_the_default_limit_60():
    assert read_settings() == (30, 60)
    assert (
        budget_seconds("lessons/mechanics/01-kinematics-as-a-program/index.html") == 60
    )


def test_only_the_monte_carlo_lesson_has_a_line_of_its_own_and_it_has_a_reason():
    budgets = read_budgets()
    assert set(budgets) == {MONTE_CARLO}
    seconds, reason = budgets[MONTE_CARLO]
    assert seconds == MONTE_CARLO_SECONDS
    for issue in ("#206", "#272", "#383"):
        assert issue in reason
    assert MONTE_CARLO in LESSONS


def test_a_line_only_raises_the_limit_above_the_default():
    _, default = read_settings()
    for lesson, (seconds, _) in read_budgets().items():
        assert seconds > default, f"{lesson} is redundant: {seconds} s <= {default} s"


@pytest.mark.parametrize("lesson", UNDER_THE_DEFAULT)
def test_the_lessons_of_the_earlier_raises_are_covered_by_the_default(lesson: str):
    assert lesson in LESSONS
    assert lesson not in read_budgets()
    assert budget_seconds(lesson + "/index.html") == 60
    assert shell_budget("site/" + lesson) == 60


@pytest.mark.parametrize("lesson", LESSONS)
def test_the_shell_check_and_the_tests_agree_on_every_lesson(lesson: str):
    assert shell_budget("site/" + lesson) == budget_seconds(lesson + "/index.html")


# What a duration of each kind earns, at and around the boundaries: the
# warning threshold is 30 s, the default limit 60 s, the line of lessons/a/b
# 90 s. The seconds are given, never measured.
BOUNDARIES = [
    ("lessons/a/c", 0, "ok"),
    ("lessons/a/c", 29, "ok"),
    ("lessons/a/c", 30, "warn"),
    ("lessons/a/c", 31, "warn"),
    ("lessons/a/c", 59, "warn"),
    ("lessons/a/c", 60, "fail"),
    ("lessons/a/c", 61, "fail"),
    ("lessons/a/b", 29, "ok"),
    ("lessons/a/b", 30, "warn"),
    ("lessons/a/b", 60, "warn"),
    ("lessons/a/b", 89, "warn"),
    ("lessons/a/b", 90, "fail"),
    ("lessons/a/bb", 60, "fail"),
]


@pytest.mark.parametrize(("lesson", "seconds", "expected"), BOUNDARIES)
def test_the_tests_and_the_shell_check_judge_the_boundaries_alike(
    tmp_path, lesson: str, seconds: int, expected: str
):
    path = table(tmp_path)
    assert verdict(lesson, seconds, path) == expected
    assert shell_verdict("site/" + lesson, seconds, path) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(29.99, "ok"), (30.0, "warn"), (59.99, "warn"), (60.0, "fail"), (60.01, "fail")],
)
def test_the_tests_judge_fractions_of_a_second(tmp_path, seconds: float, expected: str):
    assert verdict("lessons/a/c", seconds, table(tmp_path)) == expected


def test_the_shell_check_keeps_the_limit_of_a_lesson_not_listed(tmp_path):
    path = table(tmp_path)
    assert shell_budget("site/lessons/a/b", path) == 90
    assert shell_budget("site/lessons/a/c", path) == 60
    assert shell_budget("site/lessons/a/bb", path) == 60


@pytest.mark.parametrize("missing", ["warn-seconds", "limit-seconds"])
def test_a_table_without_a_setting_fails_the_shell_check_and_the_tests(
    tmp_path, missing: str
):
    text = "\n".join(
        line for line in TABLE.splitlines() if not line.startswith(missing)
    )
    path = table(tmp_path, text + "\n")
    result = shell('verdict_of "site/lessons/a/c" 10', path)
    assert result.returncode != 0
    assert f"has no number for '{missing}'" in result.stderr
    with pytest.raises(AssertionError, match="must set"):
        read_settings(path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("warn-seconds: 30", "warn-seconds: 0", "must be positive"),
        ("warn-seconds: 30", "warn-seconds: 60", "must be below limit-seconds"),
        ("warn-seconds: 30", "warn-seconds: 70", "must be below limit-seconds"),
        ("| 90 |", "| 30 |", "above warn-seconds"),
    ],
)
def test_incoherent_settings_fail_the_shell_check_and_the_tests(
    tmp_path, old: str, new: str, message: str
):
    assert old in TABLE
    path = table(tmp_path, TABLE.replace(old, new))
    result = shell('verdict_of "site/lessons/a/b" 10', path)
    assert result.returncode != 0
    assert message in result.stderr
    expected = {"must be below limit-seconds": "positive and below"}.get(
        message, message
    )
    with pytest.raises(AssertionError, match=expected):
        read_settings(path)


def test_a_setting_that_is_no_number_fails_the_shell_check(tmp_path):
    path = table(tmp_path, TABLE.replace("limit-seconds: 60", "limit-seconds: soon"))
    result = shell('budget_of "site/lessons/a/c"', path)
    assert result.returncode != 0
    assert "has no number for 'limit-seconds'" in result.stderr


def test_a_duration_below_the_threshold_passes_without_a_warning():
    lesson = "lessons/mechanics/01-kinematics-as-a-program/index.html"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        check_within_budget(lesson, 29.99)


def test_a_duration_from_the_threshold_to_the_limit_passes_with_a_warning():
    lesson = "lessons/mechanics/01-kinematics-as-a-program/index.html"
    for seconds in (30.0, 59.99):
        with pytest.warns(LessonTimeWarning, match="above the warning threshold"):
            check_within_budget(lesson, seconds)


def test_a_duration_at_the_limit_or_above_fails():
    lesson = "lessons/mechanics/01-kinematics-as-a-program/index.html"
    for seconds in (60.0, 75.0):
        with pytest.raises(AssertionError, match="its limit is 60 s"):
            check_within_budget(lesson, seconds)


def test_the_exception_of_the_monte_carlo_lesson_is_applied_by_both_checks():
    lesson = MONTE_CARLO + "/index.html"
    # 69 s is above the default limit and below its own: a warning, no failure.
    with pytest.warns(LessonTimeWarning):
        check_within_budget(lesson, 69.1)
    with pytest.raises(AssertionError, match="its limit is 90 s"):
        check_within_budget(lesson, 90.0)
    assert shell_verdict("site/" + MONTE_CARLO, 69) == "warn"
    assert shell_verdict("site/" + MONTE_CARLO, 89) == "warn"
    assert shell_verdict("site/" + MONTE_CARLO, 90) == "fail"
    # Another lesson at 69 s fails under the default limit.
    assert (
        shell_verdict("site/lessons/mechanics/01-kinematics-as-a-program", 69) == "fail"
    )


def test_both_checks_judge_with_the_one_rule_and_keep_no_number_of_their_own():
    # The shell check judges the render and the experiment alike, and the
    # tests of the reproduction judge both with the shared function.
    script = SCRIPT.read_text()
    assert script.count('verdict_of "$lesson" "$seconds"') == 2
    assert "default_budget_seconds" not in script
    e2e = E2E.read_text()
    assert e2e.count("check_within_budget(lesson, seconds)") == 2
    assert "budget_seconds" not in e2e.replace("check_within_budget", "")
    support = (REPO_ROOT / "tests/support/budgets.py").read_text()
    assert "= 30" not in support and "= 60" not in support
