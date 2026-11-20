"""The physical-constraint checks of lesson SA7
(``pbc.verification.constraints``): the exact motion of the oscillator
passes every check, each deliberately wrong closed form of
``pbc.verification.faulty_motion`` fails exactly the checks its entry names,
every check rejects at least one of them, and every witness is a real
violation of its constraint."""

import ast
from pathlib import Path

import numpy as np
import pytest

from pbc.mechanics.dynamics import State, Trajectory
from pbc.mechanics.oscillator import energy, harmonic_motion
from pbc.verification import constraints
from pbc.verification.constraints import (
    CASES,
    CHECKS,
    TOLERANCE,
    Case,
    conservation,
    deviation,
    dimensions,
    examine,
    limits,
    symmetry,
)
from pbc.verification.faulty_motion import EXERCISE, GALLERY

ROOT = Path(__file__).parents[2]
CANDIDATES = (*GALLERY, EXERCISE)


def failed(motion, cases=CASES) -> frozenset[str]:
    return frozenset(f.check for f in examine(motion, cases) if f.counterexample)


def test_the_exact_motion_passes_every_check():
    findings = examine(harmonic_motion)

    assert [f.check for f in findings] == list(CHECKS)
    assert not any(f.counterexample for f in findings)
    assert all(f.tried > 0 and f.deviation <= TOLERANCE for f in findings)


@pytest.mark.parametrize("faulty", CANDIDATES, ids=[c.name for c in CANDIDATES])
def test_each_wrong_candidate_fails_exactly_the_checks_named_for_it(faulty):
    assert failed(faulty.motion) == faulty.caught_by


@pytest.mark.parametrize("check", CHECKS)
def test_every_check_rejects_a_deliberately_wrong_candidate(check):
    rejected = [g.name for g in GALLERY if check in failed(g.motion)]

    assert rejected, f"no wrong candidate of the gallery fails {check}"


def test_three_faults_are_seen_by_one_check_only():
    alone = {next(iter(g.caught_by)) for g in GALLERY if len(g.caught_by) == 1}

    assert alone == {"symmetry", "limits", "conservation"}


def test_the_missing_root_hides_from_all_but_dimensions_at_a_unit_ratio():
    # At k / m = 1 s⁻² the frequency k / m is the frequency sqrt(k / m).
    unit = (Case(mass=1.0, k=1.0, x0=0.12, v0=-0.45),)

    assert failed(GALLERY[0].motion, unit) == {"dimensions"}


def test_every_case_starts_at_a_positive_displacement():
    # The arctangent's fault is visible only from a negative one: the cases
    # do not contain it, and only the mirror reaches it.
    assert all(case.x0 > 0 for case in CASES)
    assert {np.sign(case.v0) for case in CASES} == {-1.0, 0.0, 1.0}


def test_the_values_of_the_cases_are_not_one():
    assert all(1.0 not in (c.mass, c.k, c.k / c.mass) for c in CASES)


# --- Each witness is a real violation, computed again without the checks. ---


def _wrong(name):
    return next(g for g in CANDIDATES if g.name == name).motion


def test_the_mirror_witness_of_the_arctangent():
    finding = symmetry(_wrong("phase from the arctangent"))
    case = finding.case
    t = case.times()
    motion = _wrong("phase from the arctangent")
    forward = motion(case.start(), case.mass, case.k, t)
    mirrored = motion(State(0.0, -case.x0, -case.v0), case.mass, case.k, t)

    assert finding.trial == "the mirror"
    # From the mirrored start it runs on top of the unmirrored motion.
    np.testing.assert_allclose(mirrored.x, forward.x, atol=1e-12)
    assert np.max(np.abs(mirrored.x + forward.x)) > 0.1 * case.x0


def test_the_start_witness_of_the_wrong_sign():
    finding = limits(_wrong("phase with the wrong sign"))
    case = finding.case
    at_start = _wrong("phase with the wrong sign")(
        case.start(), case.mass, case.k, [0.0]
    )

    assert finding.trial == "the start" and case.v0 != 0.0
    assert at_start.x[0, 0] == pytest.approx(case.x0)
    assert at_start.v[0, 0] == pytest.approx(-case.v0)


def test_the_energy_witness_of_the_frequency_in_hertz():
    finding = conservation(_wrong("frequency in hertz"))
    case = finding.case
    path = _wrong("frequency in hertz")(case.start(), case.mass, case.k, case.times())
    e = energy(path, case.mass, case.k)

    assert np.ptp(e) / e[0] == pytest.approx(finding.deviation, rel=1e-9)
    assert finding.deviation > TOLERANCE


def test_the_dimensions_witness_names_the_change_of_units():
    finding = dimensions(_wrong("missing square root"))

    assert finding.trial.startswith("units of ")
    assert finding.deviation > 1.0


# --- The checks themselves. ---


def test_a_check_reports_the_first_witness_and_stops():
    finding = limits(_wrong("phase with the wrong sign"))

    # The first case starts from rest, where the wrong sign changes nothing;
    # the second case's start is the third trial.
    assert finding.tried == 3
    assert finding.case == CASES[1]


def test_a_check_that_finds_nothing_says_how_much_it_tried():
    finding = conservation(harmonic_motion)

    assert finding.outcome == "none found" and finding.tried == len(CASES)
    assert finding.case is None and finding.trial == ""


def test_a_motion_that_returns_nan_breaks_the_constraint():
    def undefined(initial, mass, k, t):
        good = harmonic_motion(initial, mass, k, t)
        return Trajectory(good.t, good.x * np.nan, good.v)

    assert conservation(undefined).counterexample


def test_the_deviation_is_relative_to_the_motion():
    t = np.linspace(0.0, 1.0, 5)
    demanded = Trajectory(t, np.ones((5, 1)), np.zeros((5, 1)))
    observed = Trajectory(t, np.full((5, 1), 1.5), np.full((5, 1), 0.25))

    assert deviation(observed, demanded, 2.0) == pytest.approx(0.5)
    assert deviation(demanded, demanded, 2.0) == 0.0


def test_the_weak_spring_is_weak_over_the_times_of_every_case():
    for case in CASES:
        assert np.sqrt(constraints.WEAK) * case.times()[-1] < 1e-4


# --- The faulty module stays where it belongs. ---

IMPORTERS = ["src/pbc/mechanics/experiments/counterexample_hunter.py"]


def test_only_the_lesson_imports_the_faulty_motions():
    importers = []
    for path in (ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            if any(name.endswith("verification.faulty_motion") for name in names):
                importers.append(path.relative_to(ROOT).as_posix())
    assert sorted(set(importers)) == IMPORTERS


def test_the_module_says_in_its_docstring_that_it_is_wrong_on_purpose():
    source = (ROOT / "src/pbc/verification/faulty_motion.py").read_text()
    assert "WRONG ON PURPOSE" in ast.get_docstring(ast.parse(source))
