"""The integrators of the mechanics course, behind one stepping interface.

Every stepper has the signature ``step(state, acceleration, dt) -> State``
of ``pbc.mechanics.dynamics`` and plugs into ``simulate`` through its
``step`` argument. Explicit Euler is defined with the interface, in
``pbc.mechanics.dynamics``; the three steppers here are the other methods
the course compares, and ``INTEGRATORS`` lists all four with their order of
accuracy and their cost in acceleration evaluations per step.
"""

from dataclasses import dataclass

from pbc.mechanics.dynamics import Acceleration, State, Stepper, euler_step


def symplectic_euler_step(state: State, acceleration: Acceleration, dt: float) -> State:
    """Advance ``state`` by one symplectic Euler step of length ``dt`` (s).

    The velocity changes first, with the acceleration at the old state;
    then the *new* velocity moves the particle. One change of order against
    explicit Euler, with the same cost; it is the simplest method that keeps
    the energy of an oscillator bounded.
    """
    v = state.v + acceleration(state.t, state.x, state.v) * dt
    return State(t=state.t + dt, x=state.x + v * dt, v=v)


def verlet_step(state: State, acceleration: Acceleration, dt: float) -> State:
    """Advance ``state`` by one velocity Verlet step of length ``dt`` (s).

    The position moves by the Taylor expansion to second order, with the
    acceleration at the old state; the velocity changes by the average of
    the old acceleration and the one at the new position. When the force
    depends on the velocity, the new acceleration is evaluated at the
    explicit Euler prediction of the new velocity, which keeps the method
    second order.
    """
    a = acceleration(state.t, state.x, state.v)
    t = state.t + dt
    x = state.x + state.v * dt + 0.5 * a * dt**2
    a_next = acceleration(t, x, state.v + a * dt)
    return State(t=t, x=x, v=state.v + 0.5 * (a + a_next) * dt)


def rk4_step(state: State, acceleration: Acceleration, dt: float) -> State:
    """Advance ``state`` by one step of the classical fourth-order
    Runge-Kutta method, of length ``dt`` (s).

    The rates of change of position and velocity are evaluated four times:
    at the start of the step, twice at its midpoint, and at its end, each
    time at a state predicted with the rates found so far. The step uses
    their weighted average, which matches the Taylor expansion of the motion
    to fourth order.
    """
    t, x, v = state.t, state.x, state.v
    half = 0.5 * dt
    k1_x, k1_v = v, acceleration(t, x, v)
    k2_x = v + half * k1_v
    k2_v = acceleration(t + half, x + half * k1_x, k2_x)
    k3_x = v + half * k2_v
    k3_v = acceleration(t + half, x + half * k2_x, k3_x)
    k4_x = v + dt * k3_v
    k4_v = acceleration(t + dt, x + dt * k3_x, k4_x)
    return State(
        t=t + dt,
        x=x + dt / 6.0 * (k1_x + 2.0 * k2_x + 2.0 * k3_x + k4_x),
        v=v + dt / 6.0 * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v),
    )


@dataclass(frozen=True)
class Integrator:
    """One method of the course: its stepper, with what to expect from it."""

    name: str
    step: Stepper
    # The error at a fixed time is proportional to dt ** order for a smooth
    # force and a step small enough for the method.
    order: int
    # Acceleration evaluations per step. The stepping interface keeps nothing
    # between steps, so velocity Verlet evaluates twice; a loop that carried
    # the last acceleration over would evaluate once.
    evaluations: int


# The four methods, in the order the course introduces them.
INTEGRATORS = (
    Integrator("explicit Euler", euler_step, order=1, evaluations=1),
    Integrator("symplectic Euler", symplectic_euler_step, order=1, evaluations=1),
    Integrator("velocity Verlet", verlet_step, order=2, evaluations=2),
    Integrator("Runge-Kutta 4", rk4_step, order=4, evaluations=4),
)
