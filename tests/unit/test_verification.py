import ast
import re
from pathlib import Path

import numpy as np
import pytest

from pbc.mechanics.integrators import verlet_step
from pbc.verification import (
    CHECKS,
    Claim,
    convergence_table,
    fitted_order,
    invariant_band,
    invariant_drift,
    observed_orders,
    verify,
)
from pbc.verification.faulty import CORRECT, GALLERY

ROOT = Path(__file__).resolve().parents[2]


def _failed(findings) -> tuple[str, ...]:
    return tuple(f.check for f in findings if not f.passed)


# --- The estimates, on data whose answer is known. ---


def test_observed_orders_recover_the_exponent_of_an_exact_power_law():
    h = 0.1 / 2.0 ** np.arange(5)
    for p in (1, 2, 4):
        assert observed_orders(h, 3.0 * h**p) == pytest.approx([p] * 4, abs=1e-12)
        assert fitted_order(h, 3.0 * h**p) == pytest.approx(p, abs=1e-12)


def test_observed_orders_work_for_steps_that_do_not_halve():
    h = np.array([0.3, 0.1, 0.01])
    assert observed_orders(h, h**2) == pytest.approx([2.0, 2.0], abs=1e-12)


def test_an_error_that_was_not_measured_gives_nan_not_an_order():
    h = np.array([0.4, 0.2, 0.1])
    assert np.isnan(observed_orders(h, [1.0, 0.0, 0.0])).all()
    assert np.isnan(fitted_order(h, [1.0, np.inf, 0.1]))
    assert np.isnan(fitted_order(h, [1.0, np.nan, 0.1]))


def test_the_convergence_table_has_no_order_in_its_first_row():
    h = [0.4, 0.2, 0.1]
    rows = convergence_table(h, [0.16, 0.04, 0.01])
    assert [row[0] for row in rows] == h
    assert rows[0][2] is None
    assert [row[2] for row in rows[1:]] == pytest.approx([2.0, 2.0])


@pytest.mark.parametrize(
    "steps, errors",
    [
        ([0.1], [1.0]),
        ([0.1, 0.2], [1.0, 2.0]),
        ([0.2, 0.2], [1.0, 1.0]),
        ([0.2, -0.1], [1.0, 1.0]),
        ([0.2, 0.1], [1.0, 1.0, 1.0]),
    ],
)
def test_estimates_reject_data_that_is_not_a_convergence_study(steps, errors):
    with pytest.raises(ValueError):
        observed_orders(steps, errors)


def test_invariant_drift_and_band():
    values = np.array([2.0, 2.2, 1.8, 2.0])
    assert invariant_drift(values) == pytest.approx(0.1)
    assert invariant_band(values, slice(0, 2), slice(2, None)) == pytest.approx(
        (0.1, 0.1)
    )
    leaking = 1.0 - 0.01 * np.arange(10)
    early, late = invariant_band(leaking, slice(0, 3), slice(-3, None))
    assert late > 4 * early
    with pytest.raises(ValueError):
        invariant_drift([0.0, 1.0])


# --- The checks: correct steppers pass, each faulty one fails the named check. ---


@pytest.mark.parametrize("name, build, claim", CORRECT, ids=[c[0] for c in CORRECT])
def test_every_check_passes_a_correct_method(name, build, claim):
    findings = verify(build, claim)
    assert not _failed(findings), [f.detail for f in findings if not f.passed]
    assert {f.check for f in findings} <= set(CHECKS)


@pytest.mark.parametrize("faulty", GALLERY, ids=[g.name for g in GALLERY])
def test_each_faulty_stepper_fails_exactly_the_checks_named_for_it(faulty):
    assert _failed(verify(faulty.build, faulty.claim)) == faulty.caught_by


def test_the_checks_do_not_replace_each_other():
    # Every check of the contract is the only catch of some fault, or the
    # gallery would not justify keeping it.
    only_catch = {g.caught_by[0] for g in GALLERY if len(g.caught_by) == 1}
    assert only_catch == {"clock", "purity", "convergence-order", "bounded-energy"}
    assert "limits" in {c for g in GALLERY for c in g.caught_by}


def test_a_check_fails_when_the_claim_is_wrong_not_only_when_the_code_is():
    # A correct velocity Verlet claimed to be of order 4, and claimed to be
    # of order 1, fails the convergence check either way: the check cannot
    # pass by being loose.
    for order in (1, 4):
        findings = verify(lambda: verlet_step, Claim(order=order, bounded_energy=True))
        assert _failed(findings) == ("convergence-order",)


def test_an_order_one_method_beyond_the_per_step_allowance_fails_limits():
    # Symplectic Euler errs by 0.5 g dt**2 per step, the allowance; this
    # method errs by g dt**2 per step, which only a doubled bound would let by.
    from pbc.mechanics.dynamics import State

    def overshooting(state, acceleration, dt):
        a = np.asarray(acceleration(state.t, state.x, state.v), dtype=float)
        v = state.v + a * dt
        return State(t=state.t + dt, x=state.x + v * dt + 0.5 * a * dt**2, v=v)

    findings = verify(lambda: overshooting, Claim(order=1, bounded_energy=False))
    assert "limits" in _failed(findings)


def test_the_energy_check_applies_only_to_a_method_that_claims_it():
    findings = verify(lambda: verlet_step, Claim(order=2, bounded_energy=False))
    assert "bounded-energy" not in {f.check for f in findings}


def test_a_stepper_that_returns_nan_fails_instead_of_passing_unmeasured():
    from pbc.mechanics.dynamics import State

    def nan_step(state, acceleration, dt):
        return State(t=state.t + dt, x=state.x * np.nan, v=state.v * np.nan)

    findings = verify(lambda: nan_step, Claim(order=2, bounded_energy=True))
    assert set(_failed(findings)) >= {"limits", "convergence-order", "bounded-energy"}


def test_each_finding_carries_its_evidence():
    for finding in verify(lambda: verlet_step, Claim(order=2, bounded_energy=True)):
        assert finding.check in CHECKS
        assert np.isfinite(finding.measured) and finding.tolerance > 0
        assert finding.detail
        assert finding.claim
        assert f"check_{finding.check.replace('-', '_')}" in finding.reproduction


# --- The gallery stays a gallery. ---


def test_no_module_of_src_imports_the_faulty_steppers():
    importers = []
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            if any(name.endswith("verification.faulty") for name in names):
                importers.append(path.relative_to(ROOT).as_posix())
    assert importers == []


def test_the_gallery_module_says_in_its_docstring_that_it_is_wrong_on_purpose():
    source = (ROOT / "src/pbc/verification/faulty.py").read_text()
    assert "WRONG ON PURPOSE" in ast.get_docstring(ast.parse(source))


# --- The contract document and the lesson that names it. ---


def test_the_lesson_and_the_contract_name_each_other_and_the_checks():
    contract = (ROOT / "docs/validation-contract.md").read_text()
    lesson = (
        ROOT / "site/lessons/mechanics/09-verifying-scientific-code/index.qmd"
    ).read_text()
    title = re.search(r"^# (.+)$", contract, re.MULTILINE).group(1)
    assert title == "Scientific validation contract"
    assert title in lesson
    assert "docs/validation-contract.md" in lesson
    for check in CHECKS:
        assert f"`{check}`" in contract, check
    assert "pbc.verification" in contract
