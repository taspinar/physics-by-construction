"""The ring-down task of the physics-lab starter (F139, Issue #613): the
skeleton ``my_lab/ringdown.py``, its ``SPECIFICATION.md``, and the provided
tests ``tests/test_ringdown.py``, the common task of the pilot's routes.

The repository's ``starters`` check runs the starter's tests against the
skeleton, where the provided tests are skipped by the starter's
``conftest.py``. These tests show the two sides of that skip in a copy of
the starter: against the skeleton the twelve provided tests are skipped and
nothing fails; with a working fit in its place they run, unchanged, and
pass, so the task can be done. The working fit here is the product's
reference, ``pbc.products.physics_lab.ringdown`` (F145), behind the
skeleton's interface; no solution is committed to the starter.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
STARTER = ROOT / "products/physics-lab/starter"
TRACE = ROOT / "products/physics-lab/fixtures/starter-agent.json"
PROVIDED = 12

# A learner's finished file: the skeleton's dataclass and signature, with a
# body. It delegates to the reference, which is what F145 made of the
# pilot's manual route.
WORKING_FIT = """
from collections.abc import Sequence
from dataclasses import dataclass

from pbc.products.physics_lab import ringdown as reference


@dataclass(frozen=True)
class RingdownFit:
    decay_rate: float
    decay_rate_se: float
    damped_frequency_hz: float
    damped_frequency_se: float
    f0_hz: float
    f0_se: float
    q: float
    q_se: float


def fit_ringdown(t_s: Sequence[float], v: Sequence[float]) -> RingdownFit:
    fit = reference.fit_ringdown(t_s, v)
    return RingdownFit(
        fit.decay_rate, fit.decay_rate_se, fit.damped_frequency_hz,
        fit.damped_frequency_se, fit.f0_hz, fit.f0_se, fit.q, fit.q_se,
    )
"""


def copy_of_the_starter(tmp_path: Path) -> Path:
    copy = tmp_path / "my-lab"
    shutil.copytree(STARTER, copy, ignore=shutil.ignore_patterns("__pycache__"))
    (copy / "fixtures").mkdir()
    shutil.copy(TRACE, copy / "fixtures")
    return copy


def run_tests(copy: Path, *args: str, passes: bool = True) -> str:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(copy)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rs", *args],
        cwd=copy,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert (result.returncode == 0) is passes, output
    return output


def count(output: str, outcome: str) -> int:
    found = re.search(rf"(\d+) {outcome}", output)
    return int(found.group(1)) if found else 0


def test_against_the_skeleton_the_provided_tests_are_skipped_with_the_reason(
    tmp_path,
):
    output = run_tests(copy_of_the_starter(tmp_path))
    assert count(output, "skipped") == PROVIDED
    assert count(output, "failed") == 0
    assert "YOUR WORK: fit_ringdown in my_lab/ringdown.py is not written" in output


def test_with_a_working_fit_the_provided_tests_run_unchanged_and_pass(tmp_path):
    copy = copy_of_the_starter(tmp_path)
    provided = (copy / "tests/test_ringdown.py").read_bytes()
    (copy / "my_lab/ringdown.py").write_text(WORKING_FIT)
    output = run_tests(copy)
    assert count(output, "skipped") == 0
    assert count(output, "passed") >= PROVIDED + 1
    assert (copy / "tests/test_ringdown.py").read_bytes() == provided


def test_a_fit_that_raises_something_else_is_judged_by_the_tests(tmp_path):
    """Only ``NotImplementedError`` skips: a wrong fit fails, it is never
    skipped."""
    copy = copy_of_the_starter(tmp_path)
    skeleton = (copy / "my_lab/ringdown.py").read_text()
    wrong = skeleton.replace(
        'raise NotImplementedError("YOUR WORK: the ring-down fit")',
        'raise ValueError("not a ring-down")',
    )
    assert wrong != skeleton
    (copy / "my_lab/ringdown.py").write_text(wrong)
    output = run_tests(copy, passes=False)
    assert count(output, "skipped") == 0
    assert count(output, "failed") >= 1


# A learner's partial work: the input checks written first, the trailing
# raise of the skeleton still in place.
PARTIAL_FIT_BODY = """    if len(t_s) != len(v) or len(t_s) < 16:
        raise ValueError("a record of at least 16 samples, t and v alike")
    raise NotImplementedError("YOUR WORK: the ring-down fit")"""


def test_partial_work_that_still_raises_skips_all_until_noconftest(tmp_path):
    """The skip is all or nothing (review 01 of #613, S1): while the body
    still ends in ``NotImplementedError`` every provided test is skipped,
    those the written checks would pass among them. ``--noconftest``, which
    the starter's README and ``ROUTES.md`` name, runs them on such work."""
    copy = copy_of_the_starter(tmp_path)
    skeleton = (copy / "my_lab/ringdown.py").read_text()
    partial = skeleton.replace(
        '    raise NotImplementedError("YOUR WORK: the ring-down fit")',
        PARTIAL_FIT_BODY,
    )
    assert partial != skeleton
    (copy / "my_lab/ringdown.py").write_text(partial)
    output = run_tests(copy)
    assert count(output, "skipped") == PROVIDED
    output = run_tests(copy, "--noconftest", "tests/test_ringdown.py", passes=False)
    assert count(output, "skipped") == 0
    assert count(output, "passed") + count(output, "failed") == PROVIDED
