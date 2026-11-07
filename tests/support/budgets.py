"""The time budget of a lesson (scripts/lesson-budgets.conf, ADR 020 decision
6): a duration below the warning threshold passes silently, one from the
threshold up to the limit of the lesson passes with a warning, and one at its
limit or above fails. The numbers, the threshold, the default limit and the
exceptions, are all in that file; scripts/check-lesson-pages.sh reads the
same file and judges a duration the same way."""

import warnings
from pathlib import Path, PurePosixPath

from support.paths import SCRIPTS

BUDGETS_FILE = SCRIPTS / "lesson-budgets.conf"
WARN_KEY = "warn-seconds"
LIMIT_KEY = "limit-seconds"


class LessonTimeWarning(UserWarning):
    """A lesson took the warning threshold or more but less than its limit."""


def _read(path: Path) -> tuple[dict[str, int], dict[str, tuple[int, str]]]:
    settings: dict[str, int] = {}
    budgets: dict[str, tuple[int, str]] = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "|" not in line:
            key, _, value = (field.strip() for field in line.partition(":"))
            assert key in (WARN_KEY, LIMIT_KEY), f"unknown setting: {line!r}"
            assert key not in settings, f"{key} is set twice"
            settings[key] = int(value)
            continue
        lesson, seconds, reason = (field.strip() for field in line.split("|", 2))
        assert lesson not in budgets, f"{lesson} has two budgets"
        assert reason, f"the budget of {lesson} has no reason"
        budgets[lesson] = (int(seconds), reason)
    assert set(settings) == {WARN_KEY, LIMIT_KEY}, (
        f"{path} must set {WARN_KEY} and {LIMIT_KEY}"
    )
    warn, limit = settings[WARN_KEY], settings[LIMIT_KEY]
    assert 0 < warn < limit, (
        f"{WARN_KEY} ({warn}) must be positive and below {LIMIT_KEY} ({limit})"
    )
    for lesson, (seconds, _) in budgets.items():
        assert seconds > warn, (
            f"the limit of {lesson} ({seconds}) must be above {WARN_KEY} ({warn})"
        )
    return settings, budgets


def read_settings(path: Path = BUDGETS_FILE) -> tuple[int, int]:
    """The warning threshold and the default limit, in seconds."""
    settings, _ = _read(path)
    return settings[WARN_KEY], settings[LIMIT_KEY]


def read_budgets(path: Path = BUDGETS_FILE) -> dict[str, tuple[int, str]]:
    """The lessons with a limit of their own: directory below site/ to
    (seconds, reason)."""
    return _read(path)[1]


def _directory(lesson: str) -> str:
    """The directory of a lesson, given as the path of its built page
    ('lessons/<topic>/<lesson>/index.html') or as its directory."""
    path = PurePosixPath(lesson)
    return str(path.parent if path.suffix else path)


def warn_seconds(path: Path = BUDGETS_FILE) -> int:
    return read_settings(path)[0]


def budget_seconds(lesson: str, path: Path = BUDGETS_FILE) -> int:
    """The limit of a lesson: its own, or the default."""
    _, default = read_settings(path)
    seconds, _ = read_budgets(path).get(_directory(lesson), (default, ""))
    return seconds


def verdict(lesson: str, seconds: float, path: Path = BUDGETS_FILE) -> str:
    """'ok' below the warning threshold, 'warn' from it up to the limit of the
    lesson, 'fail' at the limit and above."""
    if seconds >= budget_seconds(lesson, path):
        return "fail"
    if seconds >= warn_seconds(path):
        return "warn"
    return "ok"


def check_within_budget(lesson: str, seconds: float) -> None:
    """Fail when a lesson took its limit or more; warn, visibly in the report
    of the run and without failing it, when it took the warning threshold or
    more."""
    limit = budget_seconds(lesson)
    assert seconds < limit, f"{lesson} took {seconds:.2f} s; its limit is {limit} s"
    if verdict(lesson, seconds) == "warn":
        warnings.warn(
            f"{lesson} took {seconds:.2f} s, above the warning threshold of "
            f"{warn_seconds()} s (its limit is {limit} s)",
            LessonTimeWarning,
            stacklevel=2,
        )
