"""The checks of the validation contract on a model, the damped driven
oscillator (``pbc.verification.driven``): the reference solution of
``pbc.mechanics.resonance`` passes every check, each faulty simulation fails
exactly the checks its entry names, and every check has a subject it fails
(the contract's rule 4)."""

import ast
from pathlib import Path

import numpy as np
import pytest

from pbc.mechanics.dynamics import State, Trajectory
from pbc.mechanics.integrators import verlet_step
from pbc.mechanics.resonance import (
    driven_motion,
    simulate_driven,
    steady_state_amplitude,
)
from pbc.verification import driven
from pbc.verification.driven import (
    MODEL_CHECKS,
    ModelClaim,
    check_convergence_order,
    driven_error,
    energy_balance,
    rescaled,
    verify_simulation,
)
from pbc.verification.faulty import (
    verlet_that_remembers_the_acceleration,
    verlet_with_a_stopped_clock,
)
from pbc.verification.faulty_driven import GALLERY, drive_not_divided_by_mass

ROOT = Path(__file__).parents[2]
REFERENCE_CLAIM = ModelClaim(order=4)


def failed(simulate, claim=REFERENCE_CLAIM) -> tuple[str, ...]:
    return tuple(f.check for f in verify_simulation(simulate, claim) if not f.passed)


def with_stepper(step):
    return lambda *arguments: simulate_driven(*arguments, step=step)


# --- The reference solution (acceptance criterion 3). ---


def test_the_reference_solution_passes_every_check_of_the_model():
    findings = verify_simulation(simulate_driven, REFERENCE_CLAIM)
    assert tuple(f.check for f in findings) == MODEL_CHECKS
    assert all(f.passed for f in findings), [f.detail for f in findings]


def test_the_reference_solution_follows_the_exact_driven_motion():
    # Independent of the checks: the closed form at one step, with an
    # explicit tolerance, from a start that is neither at rest nor at zero.
    start = State(t=0.7, x=[-0.4], v=[1.1])
    dt, n = 0.005, 2000
    run = simulate_driven(start, 0.8, 3.0, 0.5, 2.0, 1.7, dt, n)
    exact = driven_motion(start, 0.8, 3.0, 0.5, 2.0, 1.7, 0.7 + np.arange(n + 1) * dt)
    # A fourth-order error has the size (ω₀ dt)⁴ of the amplitude: 9e-9 here.
    tolerance = (np.sqrt(3.0 / 0.8) * dt) ** 4
    assert 1e-9 < tolerance < 1e-8
    assert np.max(np.abs(run.x - exact.x)) < tolerance
    assert np.max(np.abs(run.v - exact.v)) < tolerance


def test_the_reference_solution_reaches_the_steady_amplitude():
    mass, k, b, force, omega = 0.5, 2.0, 0.4, 1.5, 1.5
    period = 2.0 * np.pi / omega
    n = 60 * 200  # sixty driving periods: the transient is below e ** -30
    run = simulate_driven(
        State(t=0.0, x=[0.0], v=[0.0]), mass, k, b, force, omega, period / 200, n
    )
    amplitude = np.max(np.abs(run.x[-400:, 0]))
    assert amplitude == pytest.approx(
        float(steady_state_amplitude(mass, k, b, force, omega)), rel=1e-4
    )


def test_a_correct_method_of_order_two_passes_under_its_own_claim():
    assert failed(with_stepper(verlet_step), ModelClaim(order=2)) == ()
    # and fails the convergence check, and only it, under a claim it does
    # not meet: the checks test the claim, not the code alone
    assert failed(with_stepper(verlet_step), ModelClaim(order=4)) == (
        "convergence-order",
    )


def test_a_claim_of_order_one_is_refused_because_the_tolerances_are_not_its_own():
    with pytest.raises(ValueError, match="order 2 or more"):
        ModelClaim(order=1)
    with pytest.raises(ValueError, match="whole number"):
        ModelClaim(order=2.0)


# --- Every check can fail (the contract's rule 4). ---


@pytest.mark.parametrize("entry", GALLERY, ids=lambda entry: entry.name)
def test_each_faulty_simulation_fails_exactly_the_checks_it_names(entry):
    assert failed(entry.simulate) == entry.caught_by


def test_every_check_of_the_model_has_a_simulation_it_fails():
    caught = {check for entry in GALLERY for check in entry.caught_by}
    assert caught == set(MODEL_CHECKS)


def test_a_missing_division_by_the_mass_hides_at_a_mass_of_one_kilogram():
    hidden = check_convergence_order(
        drive_not_divided_by_mass, REFERENCE_CLAIM, mass=1.0
    )
    assert hidden.passed
    assert not check_convergence_order(
        drive_not_divided_by_mass, REFERENCE_CLAIM
    ).passed
    # the change of the unit of mass finds it whatever the mass is
    assert rescaled(drive_not_divided_by_mass, 1e3, 1.0, 1.0) > 1.0
    assert rescaled(drive_not_divided_by_mass, 1.0, 1e2, 1.0) < 1e-12


def test_the_stopped_clock_shows_once_the_force_depends_on_time():
    # On the oscillator of the stepper checks only ``clock`` finds it; the
    # driving force makes it a wrong motion.
    assert failed(with_stepper(verlet_with_a_stopped_clock), ModelClaim(order=2)) == (
        "convergence-order",
        "energy-balance",
    )


def test_a_stepper_with_hidden_state_still_passes_the_model_checks():
    # The model checks do not replace the interface checks: ``purity`` of
    # ``pbc.verification.checks`` is the only check that finds this fault.
    # Each run takes its steps one after another on a stepper of its own,
    # which is how a simulation uses one, so the leaked state never shows.
    def simulate(*arguments):
        step = verlet_that_remembers_the_acceleration()
        return simulate_driven(*arguments, step=step)

    assert failed(simulate, ModelClaim(order=2)) == ()


# --- The parts of the checks. ---


def test_the_error_against_the_exact_motion_falls_as_the_fourth_power():
    coarse, fine = driven_error(simulate_driven, 50), driven_error(simulate_driven, 100)
    assert coarse / fine == pytest.approx(16.0, rel=0.1)


def test_the_energy_balance_of_the_exact_motion_closes():
    t = np.linspace(0.0, 3.0 * driven.PERIOD, 1201)
    exact = driven_motion(
        driven.START, driven.MASS, driven.K, driven.B, driven.FORCE, driven.DRIVE, t
    )
    missing, dissipated = energy_balance(exact)
    assert dissipated > 1.0
    assert abs(missing) / dissipated < 1e-8


def test_the_energy_balance_does_not_close_for_another_force():
    t = np.linspace(0.0, 3.0 * driven.PERIOD, 1201)
    other = driven_motion(
        driven.START,
        driven.MASS,
        driven.K,
        driven.B,
        1.1 * driven.FORCE,
        driven.DRIVE,
        t,
    )
    missing, dissipated = energy_balance(other)
    assert abs(missing) / dissipated > 1e-2


def test_a_run_that_is_not_finite_or_too_short_fails_and_is_not_passed():
    def not_finite(initial, mass, k, b, force, omega, dt, n_steps):
        run = simulate_driven(initial, mass, k, b, force, omega, dt, n_steps)
        return Trajectory(t=run.t, x=run.x * np.nan, v=run.v)

    def too_short(initial, mass, k, b, force, omega, dt, n_steps):
        return simulate_driven(initial, mass, k, b, force, omega, dt, n_steps - 1)

    assert failed(not_finite) == MODEL_CHECKS
    assert failed(too_short) == MODEL_CHECKS


def test_a_simulation_that_raises_has_failed_the_check_and_says_with_what():
    def raises(initial, mass, k, b, force, omega, dt, n_steps):
        raise ValueError("omega must be positive")

    findings = verify_simulation(raises, REFERENCE_CLAIM)
    assert tuple(f.check for f in findings) == MODEL_CHECKS
    assert not any(f.passed for f in findings)
    assert "ValueError: omega must be positive" in findings[0].detail


def test_a_finding_has_the_evidence_form_of_the_contract():
    for finding in verify_simulation(simulate_driven, REFERENCE_CLAIM):
        assert finding.claim and finding.detail
        assert np.isfinite(finding.measured) and finding.tolerance > 0
        name = finding.check.replace("-", "_")
        assert finding.reproduction == (
            f"pbc.verification.driven.check_{name}(simulate, claim)"
        )
        assert callable(vars(driven)[f"check_{name}"])


def test_the_parameters_of_the_checks_hide_no_factor():
    # No parameter is 1, and the oscillator is underdamped, as the closed
    # form needs.
    values = (driven.MASS, driven.K, driven.B, driven.FORCE, driven.DRIVE)
    assert all(value != 1.0 for value in values)
    assert 2.0 * np.sqrt(driven.K * driven.MASS) > driven.B


# --- The gallery stays a gallery. ---

IMPORTERS = ["src/pbc/mechanics/experiments/verifying_scientific_code.py"]


def test_only_the_lesson_imports_the_faulty_simulations():
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
            if any(name.endswith("verification.faulty_driven") for name in names):
                importers.append(path.relative_to(ROOT).as_posix())
    assert sorted(set(importers)) == IMPORTERS


def test_the_module_says_in_its_docstring_that_it_is_wrong_on_purpose():
    source = (ROOT / "src/pbc/verification/faulty_driven.py").read_text()
    assert "WRONG ON PURPOSE" in ast.get_docstring(ast.parse(source))
