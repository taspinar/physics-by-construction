"""A gallery of steppers with one deliberate fault each.

EVERY STEPPER IN THIS MODULE IS WRONG ON PURPOSE. They exist so that the
lesson on verifying scientific code can show the checks catching them, and
so that the tests can show the same checks passing the correct steppers.
Nothing else may import this module, and no simulation of the course may use
one of them (``tests/unit/test_verification.py`` enforces the second).

Each entry names the correct method it poses as, the fault, and the checks
that must fail. A fault that only one check can see is the point of the
gallery: the checks do not replace each other.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pbc.mechanics.dynamics import Acceleration, State, Stepper
from pbc.mechanics.integrators import rk4_step, symplectic_euler_step, verlet_step
from pbc.verification.checks import Claim

FAULTY = True  # a marker a reader of the source and the tests can find


def verlet_without_the_half(
    state: State, acceleration: Acceleration, dt: float
) -> State:
    """Velocity Verlet whose position update has ``a dt**2`` where the
    Taylor expansion has ``a dt**2 / 2``."""
    a = acceleration(state.t, state.x, state.v)
    t = state.t + dt
    x = state.x + state.v * dt + a * dt**2
    a_next = acceleration(t, x, state.v + a * dt)
    return State(t=t, x=x, v=state.v + 0.5 * (a + a_next) * dt)


def symplectic_euler_with_the_wrong_sign(
    state: State, acceleration: Acceleration, dt: float
) -> State:
    """Symplectic Euler whose velocity update subtracts the acceleration."""
    v = state.v - acceleration(state.t, state.x, state.v) * dt
    return State(t=state.t + dt, x=state.x + v * dt, v=v)


def verlet_with_a_stopped_clock(
    state: State, acceleration: Acceleration, dt: float
) -> State:
    """Velocity Verlet that returns the time it was given."""
    after = verlet_step(state, acceleration, dt)
    return State(t=state.t, x=after.x, v=after.v)


def rk4_with_equal_weights(
    state: State, acceleration: Acceleration, dt: float
) -> State:
    """Runge-Kutta 4 that averages its four rates with equal weights
    instead of 1, 2, 2, 1 over 6."""
    t, x, v = state.t, state.x, state.v
    half = 0.5 * dt
    k1_x = v
    k1_v = acceleration(t, x, v)
    k2_x = v + half * k1_v
    k2_v = acceleration(t + half, x + half * k1_x, k2_x)
    k3_x = v + half * k2_v
    k3_v = acceleration(t + half, x + half * k2_x, k3_x)
    k4_x = v + dt * k3_v
    k4_v = acceleration(t + dt, x + dt * k3_x, k4_x)
    return State(
        t=t + dt,
        x=x + dt / 4.0 * (k1_x + k2_x + k3_x + k4_x),
        v=v + dt / 4.0 * (k1_v + k2_v + k3_v + k4_v),
    )


def explicit_euler_as_symplectic(
    state: State, acceleration: Acceleration, dt: float
) -> State:
    """A "symplectic Euler" that moves the particle with the old velocity:
    the two updates are in the wrong order, which is explicit Euler."""
    x = state.x + state.v * dt
    v = state.v + acceleration(state.t, state.x, state.v) * dt
    return State(t=state.t + dt, x=x, v=v)


def verlet_that_remembers_the_acceleration() -> Stepper:
    """Velocity Verlet that keeps the acceleration of the last step it took
    and uses it at the start of the next one, whatever state it is given.

    Run in sequence on a force that does not depend on the velocity it is
    exact, which is why the fault survives every test that only runs a
    simulation."""
    remembered: list = []

    def step(state: State, acceleration: Acceleration, dt: float) -> State:
        a = remembered[0] if remembered else acceleration(state.t, state.x, state.v)
        t = state.t + dt
        x = state.x + state.v * dt + 0.5 * a * dt**2
        a_next = acceleration(t, x, state.v + a * dt)
        remembered[:] = [a_next]
        return State(t=t, x=x, v=state.v + 0.5 * (a + a_next) * dt)

    return step


@dataclass(frozen=True)
class FaultyStepper:
    """A wrong stepper: what it poses as, what is wrong, and what must fail."""

    name: str
    build: Callable[[], Stepper]
    poses_as: str  # the correct method it imitates
    claim: Claim  # what the correct method claims, and so what is checked
    fault: str
    caught_by: tuple[str, ...]  # the checks that must fail, in contract order


# The claim of each correct method of the gallery.
VERLET_CLAIM = Claim(order=2, bounded_energy=True)
SYMPLECTIC_EULER_CLAIM = Claim(order=1, bounded_energy=True)
RK4_CLAIM = Claim(order=4, bounded_energy=False)

GALLERY = (
    FaultyStepper(
        "verlet without the half",
        lambda: verlet_without_the_half,
        "velocity Verlet",
        VERLET_CLAIM,
        "the position update has a dt² where the Taylor expansion has a dt²/2",
        ("limits", "convergence-order"),
    ),
    FaultyStepper(
        "symplectic Euler with the wrong sign",
        lambda: symplectic_euler_with_the_wrong_sign,
        "symplectic Euler",
        SYMPLECTIC_EULER_CLAIM,
        "the velocity update subtracts the acceleration",
        ("limits", "convergence-order", "bounded-energy"),
    ),
    FaultyStepper(
        "verlet with a stopped clock",
        lambda: verlet_with_a_stopped_clock,
        "velocity Verlet",
        VERLET_CLAIM,
        "the returned state keeps the old time",
        ("clock",),
    ),
    FaultyStepper(
        "rk4 with equal weights",
        lambda: rk4_with_equal_weights,
        "Runge-Kutta 4",
        RK4_CLAIM,
        "the four rates are averaged with equal weights",
        ("convergence-order",),
    ),
    FaultyStepper(
        "explicit Euler as symplectic",
        lambda: explicit_euler_as_symplectic,
        "symplectic Euler",
        SYMPLECTIC_EULER_CLAIM,
        "the position moves with the old velocity: the updates are in the wrong order",
        ("bounded-energy",),
    ),
    FaultyStepper(
        "verlet that remembers",
        verlet_that_remembers_the_acceleration,
        "velocity Verlet",
        VERLET_CLAIM,
        "the acceleration of the last step is reused, whatever state comes next",
        ("purity",),
    ),
)

# The correct methods that the gallery imitates, with their claims, to run
# the same checks on.
CORRECT = (
    ("velocity Verlet", lambda: verlet_step, VERLET_CLAIM),
    ("symplectic Euler", lambda: symplectic_euler_step, SYMPLECTIC_EULER_CLAIM),
    ("Runge-Kutta 4", lambda: rk4_step, RK4_CLAIM),
)
