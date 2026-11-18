"""The checks of the scientific validation contract on a model: a
simulation of the damped driven oscillator,

    m x'' + b x' + k x = F₀ cos(Ω t).

The subject is a function with the interface of
``pbc.mechanics.resonance.simulate_driven`` (``Simulation`` below): the code
a person or a coding agent wrote from the specification of
``docs/coding-agent-workflow.md``. ``verify_simulation`` runs the checks of
``MODEL_CHECKS`` in the order of the contract and returns one ``Finding``
each, in the evidence form of ``pbc.verification.checks``. The checks keep
their names where they ask the question the stepper checks ask (``limits``,
``convergence-order``) and add the two this model needs: ``units``, because
its parameters carry five different units, and ``energy-balance``, the
model's invariant in place of a conserved energy.

Every reference is independent of the subject: an equilibrium, the closed
forms of ``pbc.mechanics.resonance``, the change of units, and the work
done on the simulated motion. The parameters are deliberately not round
numbers: at a mass of 1 kg a missing division by the mass changes nothing.

A check does not prove a simulation right; see ``pbc.verification.checks``.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import simpson

from pbc.mechanics.dynamics import State, Trajectory
from pbc.mechanics.resonance import driven_motion, natural_frequency
from pbc.verification.checks import EXACT, ORDER_MARGIN, Finding
from pbc.verification.estimates import fitted_order

# simulate(initial, mass, k, b, force, omega, dt, n_steps) -> Trajectory
type Simulation = Callable[
    [State, float, float, float, float, float, float, int], Trajectory
]

# The oscillator the checks run on, in SI units.
MASS = 0.5  # kg
K = 2.0  # N/m
B = 0.4  # kg/s
FORCE = 1.5  # N
DRIVE = 1.5  # rad/s, the angular frequency of the driving force
START = State(t=0.0, x=[0.3], v=[-0.2])
PERIOD = 2.0 * np.pi / natural_frequency(MASS, K)  # s, of the free motion

# Tolerances, fixed before any simulation is run (the contract: tolerances
# first). EXACT and ORDER_MARGIN are those of the stepper checks. DECAY and
# BALANCE are for a method of order 2 or more at 400 steps per period, where
# its error is of the size (2 π / 400)² = 2.5e-4 times a number below one: a
# claim of order 1 is refused, because these tolerances would not be its own.
LOWEST_ORDER = 2
DECAY = 1e-3  # m, how far the free decay may be from its closed form
RESCALED = 1e-9  # relative: a change of units changes only the round-off
BALANCE = 1e-3  # the part of the dissipated energy not accounted for
COUNTS = (25, 50, 100, 200, 400)  # steps per period of the convergence runs
# A change of units: grams, centimetres, and milliseconds for kg, m, and s.
UNITS = {"mass": (1e3, 1.0, 1.0), "length": (1.0, 1e2, 1.0), "time": (1.0, 1.0, 1e3)}


@dataclass(frozen=True)
class ModelClaim:
    """What a simulation of the oscillator says about itself: its ``order``
    of accuracy in the time step."""

    order: int

    def __post_init__(self) -> None:
        if isinstance(self.order, bool) or not isinstance(self.order, int):
            raise ValueError(f"the order must be a whole number, got {self.order!r}")
        if self.order < LOWEST_ORDER:
            raise ValueError(
                f"the tolerances of these checks are fixed for a method of order"
                f" {LOWEST_ORDER} or more, got a claim of order {self.order}"
            )


def _finding(
    check: str, claim: str, passed: bool, measured: float, tolerance: float, detail: str
) -> Finding:
    reproduction = (
        f"pbc.verification.driven.check_{check.replace('-', '_')}(simulate, claim)"
    )
    return Finding(
        check, claim, reproduction, bool(passed), measured, tolerance, detail
    )


def _shown(value: float, allowed: float) -> str:
    """A measured value for the evidence text: its size when it is above
    what is allowed, and only "below" the allowance when it is not, because
    a value at the level of round-off differs between machines."""
    return f"below {allowed:.0e}" if value <= allowed else f"{value:.1e}"


def _distance(run: Trajectory, exact: Trajectory, omega0: float) -> float:
    """The largest distance between two motions in the plane (x, v / ω₀), in
    m; ``inf`` when the run has another length or a value that is not
    finite."""
    if run.x.shape != exact.x.shape:
        return float("inf")
    distance = np.sqrt(
        np.sum((run.x - exact.x) ** 2 + ((run.v - exact.v) / omega0) ** 2, axis=1)
    )
    return float(np.max(distance)) if np.all(np.isfinite(distance)) else float("inf")


def check_limits(simulate: Simulation, claim: ModelClaim) -> Finding:
    """Limits: at rest with no force the mass stays at rest; under a
    constant force it stays at the deflection F₀ / k; with no driving force
    the motion is the decaying free motion of the closed form. The first two
    are exact for every method; the third has the tolerance ``DECAY``. The
    measured value is the largest deviation as a multiple of its allowance."""
    n = 100
    dt = PERIOD / n
    rest = simulate(State(t=0.0, x=[0.0], v=[0.0]), MASS, K, B, 0.0, DRIVE, dt, n)
    at_rest = float(np.max(np.abs(np.concatenate([rest.x, rest.v]))))
    deflection = FORCE / K
    held = simulate(
        State(t=0.0, x=[deflection], v=[0.0]), MASS, K, B, FORCE, 0.0, dt, n
    )
    static = float(np.max(np.abs(np.concatenate([held.x - deflection, held.v]))))
    n = 2 * 400
    dt = PERIOD / 400
    free = simulate(START, MASS, K, B, 0.0, DRIVE, dt, n)
    exact = driven_motion(START, MASS, K, B, 0.0, DRIVE, np.arange(n + 1) * dt)
    decay = _distance(free, exact, natural_frequency(MASS, K))
    exact_cases = max(at_rest, static)
    passed = np.isfinite(exact_cases) and exact_cases <= EXACT and decay <= DECAY
    return _finding(
        "limits",
        "rest stays rest, the static deflection F0 / k is an equilibrium, and"
        " without a driving force the motion is the free decay",
        passed,
        max(exact_cases / EXACT, decay / DECAY),
        1.0,
        f"rest moved by {_shown(at_rest, EXACT)}, the static deflection by"
        f" {_shown(static, EXACT)}; the free decay is off by"
        f" {_shown(decay, DECAY)} m",
    )


def driven_error(
    simulate: Simulation,
    steps_per_period: int,
    periods: int = 2,
    mass: float = MASS,
) -> float:
    """The largest distance in m, in the plane (x, v / ω₀), between the
    simulated motion and the exact driven motion over ``periods`` periods of
    the free motion, at the times of the experiment."""
    n = periods * steps_per_period
    dt = PERIOD / steps_per_period
    run = simulate(START, mass, K, B, FORCE, DRIVE, dt, n)
    exact = driven_motion(START, mass, K, B, FORCE, DRIVE, np.arange(n + 1) * dt)
    return _distance(run, exact, natural_frequency(mass, K))


def check_convergence_order(
    simulate: Simulation, claim: ModelClaim, mass: float = MASS
) -> Finding:
    """Convergence: against the exact driven motion, halving the step
    divides the error by 2 ** order."""
    errors = np.array([driven_error(simulate, n, mass=mass) for n in COUNTS])
    order = fitted_order(PERIOD / np.array(COUNTS), errors)
    return _finding(
        "convergence-order",
        "halving the step divides the error against the exact driven motion"
        " by 2 ** the claimed order",
        np.isfinite(order) and abs(order - claim.order) <= ORDER_MARGIN,
        order,
        ORDER_MARGIN,
        f"fitted order {round(order, 2) + 0.0:.2f}, claimed {claim.order}; error"
        f" {errors[-1]:.1e} m at {COUNTS[-1]} steps per period",
    )


def rescaled(
    simulate: Simulation, mass: float, length: float, time: float, n: int = 200
) -> float:
    """The relative difference between a run in SI units and the same run
    with the unit of mass, of length, and of time divided by the factors
    ``mass``, ``length``, and ``time`` (so every number is multiplied by the
    power of the factors its unit holds), converted back."""
    dt = PERIOD / 100
    reference = simulate(START, MASS, K, B, FORCE, DRIVE, dt, n)
    converted = simulate(
        State(
            t=START.t * time,
            x=START.x * length,
            v=START.v * length / time,
        ),
        MASS * mass,
        K * mass / time**2,
        B * mass / time,
        FORCE * mass * length / time**2,
        DRIVE / time,
        dt * time,
        n,
    )
    if not converted.x.shape == reference.x.shape == (n + 1, 1):
        return float("inf")
    difference = np.concatenate(
        [
            converted.x / length - reference.x,
            (converted.v * time / length - reference.v) / natural_frequency(MASS, K),
        ]
    )
    scale = float(np.max(np.abs(reference.x)))
    if not np.all(np.isfinite(difference)) or scale == 0:
        return float("inf")
    return float(np.max(np.abs(difference))) / scale


def check_units(simulate: Simulation, claim: ModelClaim) -> Finding:
    """Units: the same experiment written in grams, in centimetres, or in
    milliseconds gives the same motion, converted. A term whose unit is
    wrong changes with the unit."""
    found = {name: rescaled(simulate, *factors) for name, factors in UNITS.items()}
    worst = max(found.values())
    return _finding(
        "units",
        "the motion does not depend on the units the experiment is written in",
        worst <= RESCALED,
        worst,
        RESCALED,
        "relative change of the motion: "
        + ", ".join(
            f"{_shown(value, RESCALED)} for the unit of {name}"
            for name, value in found.items()
        ),
    )


def energy_balance(run: Trajectory, mass: float = MASS) -> tuple[float, float]:
    """The energy the motion ``run`` does not account for, and the energy
    the drag dissipated, both in J. The change of the kinetic and spring
    energy must equal the work of the driving force minus the dissipation,
    ∫ (F₀ cos(Ω t) v - b v²) dt, here by Simpson's rule over the run."""
    x, v, t = run.x[:, 0], run.v[:, 0], run.t
    energy = 0.5 * mass * v**2 + 0.5 * K * x**2
    work = simpson(FORCE * np.cos(DRIVE * t) * v, x=t)
    dissipated = simpson(B * v**2, x=t)
    return float(energy[-1] - energy[0] - (work - dissipated)), float(dissipated)


def check_energy_balance(simulate: Simulation, claim: ModelClaim) -> Finding:
    """Invariant: the energy changes by the work of the driving force minus
    what the drag dissipates. The times are the experiment's."""
    n = 3 * 400
    dt = PERIOD / 400
    run = simulate(START, MASS, K, B, FORCE, DRIVE, dt, n)
    if run.x.shape != (n + 1, 1) or not (
        np.all(np.isfinite(run.x)) and np.all(np.isfinite(run.v))
    ):
        return _finding(
            "energy-balance",
            "the energy changes by the work of the drive minus the dissipation",
            False,
            float("inf"),
            BALANCE,
            "the run is not finite or has the wrong length",
        )
    on_the_clock = Trajectory(t=START.t + np.arange(n + 1) * dt, x=run.x, v=run.v)
    missing, dissipated = energy_balance(on_the_clock)
    measured = abs(missing) / dissipated if dissipated > 0 else float("inf")
    return _finding(
        "energy-balance",
        "the energy changes by the work of the drive minus the dissipation",
        measured <= BALANCE,
        measured,
        BALANCE,
        f"{abs(missing):.1e} J of {dissipated:.2f} J dissipated is not accounted for",
    )


# The names of the checks of the model, in the order of the contract: the
# closed-form cases first, then the property that needs the reference
# solution, then the two that need neither.
MODEL_CHECKS = ("limits", "convergence-order", "units", "energy-balance")


def verify_simulation(simulate: Simulation, claim: ModelClaim) -> list[Finding]:
    """Run the checks of the model against ``claim`` and return one finding
    per check. A simulation that raises on an input of a check has failed
    that check, and the finding says with what."""
    findings = []
    for name, check in zip(
        MODEL_CHECKS,
        (check_limits, check_convergence_order, check_units, check_energy_balance),
        strict=True,
    ):
        try:
            findings.append(check(simulate, claim))
        except (ArithmeticError, ValueError, TypeError, IndexError) as error:
            findings.append(
                _finding(
                    name,
                    "the simulation runs on the inputs of the check",
                    False,
                    float("inf"),
                    0.0,
                    f"the simulation raised {type(error).__name__}: {error}",
                )
            )
    return findings
