"""The named checks of the scientific validation contract, applied to a
stepper of the mechanics course.

``verify`` runs the checks of ``CHECKS`` in the order of the contract
(``docs/validation-contract.md``) against what the method claims, and
returns one ``Finding`` per check with the measured value, the tolerance,
and the verdict. The references are independent of the code under test: the
exact oscillator, the exact motion under no force and under a constant one,
and the clock of the experiment, never the stepper's own time.

A check does not prove a method right. It states one thing a right method
must do, measures it, and fails when it is not so; the contract says what
else is needed before a result is believed.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from pbc.mechanics.dynamics import Acceleration, State, Stepper, newton, simulate
from pbc.mechanics.oscillator import energy, harmonic_motion, spring
from pbc.verification.estimates import fitted_order, invariant_band

# The oscillator of the course: omega = 2 rad/s, period pi s.
MASS = 0.5  # kg
K = 2.0  # N/m
OMEGA = 2.0  # rad/s
PERIOD = float(np.pi)  # s
RELEASED = State(t=0.0, x=[1.0], v=[0.0])
OSCILLATOR = newton(MASS, spring(K))

BOUNDED_CLAIM = "the energy of the oscillator stays in a band that does not grow"

# Tolerances, fixed before any stepper is run (the contract: tolerances first).
EXACT = 1e-12  # for what an exact method reproduces to round-off
ORDER_MARGIN = 0.4  # the observed order may differ from the claim by this much
BAND_GROWTH = 1.5  # a band may grow by this factor between the first and last periods


@dataclass(frozen=True)
class Claim:
    """What a method says about itself, and so what is checked.

    ``order`` is the order of accuracy; ``bounded_energy`` says whether the
    energy of an oscillator stays within a band for all time.
    """

    order: int
    bounded_energy: bool


@dataclass(frozen=True)
class Finding:
    """The evidence of one check: the claim it tests, what was measured,
    against what tolerance, the verdict, and how to run the check again."""

    check: str
    claim: str
    reproduction: str
    passed: bool
    measured: float
    tolerance: float
    detail: str


def _reproduction(check: str) -> str:
    """How to run a check again: the call, on a fresh stepper and a claim."""
    return (
        f"pbc.verification.checks.check_{check.replace('-', '_')}(build, claim)"
        " with build() returning a fresh stepper"
    )


def _finding(
    check: str,
    claim: str,
    passed: bool,
    measured: float,
    tolerance: float,
    detail: str,
) -> Finding:
    return Finding(
        check, claim, _reproduction(check), passed, measured, tolerance, detail
    )


def _constant(value: list[float]) -> Acceleration:
    vector = np.array(value, dtype=np.float64)

    def acceleration(t: float, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        return vector

    return acceleration


def _finite_max(values: np.ndarray) -> float:
    """The largest value, or ``inf`` when any value is not finite."""
    return float(np.max(values)) if np.all(np.isfinite(values)) else float("inf")


def check_limits(build: Callable[[], Stepper], claim: Claim) -> Finding:
    """Limit: with no force the motion is uniform, and under a constant
    force the velocity grows linearly, exactly, for every method, and the
    position as ``x0 + v0 t + g t**2 / 2``, exactly for a method of order 2
    or more."""
    dt, n = 0.1, 20
    start = State(t=0.0, x=[1.0, 2.0], v=[0.5, -1.0])
    free = simulate(start, _constant([0.0, 0.0]), dt, n, step=build())
    t = np.arange(n + 1) * dt
    uniform = np.abs(free.x - (start.x + np.outer(t, start.v))).max()
    uniform = max(uniform, np.abs(free.v - start.v).max())

    g = [0.0, -9.81]
    falling = simulate(start, _constant(g), dt, n, step=build())
    velocity = np.abs(falling.v - (start.v + np.outer(t, g))).max()
    exact_x = start.x + np.outer(t, start.v) + 0.5 * np.outer(t**2, g)
    position = np.abs(falling.x - exact_x).max()
    # A method of order 1 may be off by 0.5 g dt**2 in each step; one of a
    # higher order is exact for a constant force. Only the excess counts.
    allowance = 0.5 * np.abs(g).max() * t[-1] * dt if claim.order < 2 else 0.0
    excess = np.maximum(position - allowance, 0.0)
    measured = _finite_max(np.array([uniform, velocity, excess]))
    return _finding(
        "limits",
        "no force gives uniform motion; a constant force gives the exact"
        " velocity, and the exact position for a method of order 2 or more",
        measured <= EXACT,
        measured,
        EXACT,
        f"uniform motion off by {uniform:.1e} m,"
        f" velocity under constant force by {velocity:.1e} m/s,"
        f" position by {position:.1e} m (allowed {allowance:.1e} m)",
    )


def check_clock(build: Callable[[], Stepper], claim: Claim) -> Finding:
    """Interface: a step of length dt advances the time by dt."""
    dt = 0.125
    after = build()(State(t=3.0, x=[1.0], v=[0.0]), OSCILLATOR, dt)
    measured = abs(after.t - (3.0 + dt))
    return _finding(
        "clock",
        "a step of length dt advances the time by dt",
        measured <= EXACT,
        measured,
        EXACT,
        f"a step of {dt} s advanced the time by {after.t - 3.0:.3f} s",
    )


def check_purity(build: Callable[[], Stepper], claim: Claim) -> Finding:
    """Interface: the result of a step depends on its arguments alone, not
    on the steps taken before."""
    step = build()
    state = State(t=0.0, x=[1.0], v=[0.0])
    first = step(state, OSCILLATOR, 0.1)
    for x in (2.0, -3.0, 0.5):
        step(State(t=1.0, x=[x], v=[x]), OSCILLATOR, 0.1)
    again = step(state, OSCILLATOR, 0.1)
    measured = _finite_max(
        np.abs(np.concatenate([first.x - again.x, first.v - again.v]))
    )
    return _finding(
        "purity",
        "the result of a step depends on its arguments alone",
        measured <= EXACT,
        measured,
        EXACT,
        f"the same step, repeated after other steps, differs by {measured:.1e}",
    )


def oscillator_error(
    build: Callable[[], Stepper], steps_per_period: int, periods: int = 2
) -> float:
    """Largest distance from the exact oscillator over the run, in the plane
    (x, v / omega), at the times of the experiment, not of the stepper."""
    n = periods * steps_per_period
    dt = PERIOD / steps_per_period
    run = simulate(RELEASED, OSCILLATOR, dt, n, step=build())
    exact = harmonic_motion(RELEASED, MASS, K, np.arange(n + 1) * dt)
    distance = np.sqrt(
        np.sum((run.x - exact.x) ** 2 + ((run.v - exact.v) / OMEGA) ** 2, axis=1)
    )
    return _finite_max(distance)


def check_convergence_order(build: Callable[[], Stepper], claim: Claim) -> Finding:
    """Convergence: halving the step divides the error by 2 ** order."""
    counts = [50, 100, 200, 400, 800]
    errors = np.array([oscillator_error(build, n) for n in counts])
    order = fitted_order(PERIOD / np.array(counts), errors)
    return _finding(
        "convergence-order",
        "halving the step divides the error by 2 ** the claimed order",
        bool(np.isfinite(order)) and abs(order - claim.order) <= ORDER_MARGIN,
        order,
        ORDER_MARGIN,
        f"fitted order {order:.2f}, claimed {claim.order}",
    )


def check_bounded_energy(build: Callable[[], Stepper], claim: Claim) -> Finding:
    """Conservation: the energy of the oscillator stays in a band that does
    not grow, over a hundred periods."""
    n_per, periods = 32, 100
    run = simulate(RELEASED, OSCILLATOR, PERIOD / n_per, n_per * periods, step=build())
    with np.errstate(over="ignore", invalid="ignore"):
        values = energy(run, MASS, K)
    if not np.all(np.isfinite(values)):
        return _finding(
            "bounded-energy",
            BOUNDED_CLAIM,
            False,
            float("inf"),
            BAND_GROWTH,
            "the energy is not finite",
        )
    early, late = invariant_band(values, slice(0, 5 * n_per), slice(-5 * n_per, None))
    growth = late / early if early > 0 else float("inf")
    return _finding(
        "bounded-energy",
        BOUNDED_CLAIM,
        growth <= BAND_GROWTH,
        growth,
        BAND_GROWTH,
        f"the energy band is {early:.1e} in the first 5 periods"
        f" and {late:.1e} in the last 5",
    )


# The names of the checks, in the order of the contract: interface, limits,
# then the properties that need a reference or a long run.
CHECKS = ("clock", "purity", "limits", "convergence-order", "bounded-energy")


def verify(build: Callable[[], Stepper], claim: Claim) -> list[Finding]:
    """Run the checks against ``claim`` and return one finding per check that
    applies. ``build`` returns a fresh stepper on every call, so that one
    check cannot leave state behind for the next; the check of bounded
    energy applies only to a method that claims it. Every simulation of a
    check gets its own stepper."""
    findings = [
        check_clock(build, claim),
        check_purity(build, claim),
        check_limits(build, claim),
        check_convergence_order(build, claim),
    ]
    if claim.bounded_energy:
        findings.append(check_bounded_energy(build, claim))
    return findings
