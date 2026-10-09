"""Newton's second law as a first-order system, and a generic stepper.

A particle moves in a line, a plane, or space. Its position ``x`` and
velocity ``v`` are vectors with one entry per dimension. Forces are functions
of time, position, and velocity; Newton's law turns their sum into the
acceleration; a stepper advances the state by one time step. Every lesson
after the first one uses this interface, and later lessons add steppers.

Quantities are in SI units: seconds, metres, metres per second, metres per
second squared, kilograms, and newtons.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

type Vector = NDArray[np.float64]

# A force model: F(t, x, v) is the force in N on the particle at time t (s)
# when it is at x (m) and moves with v (m/s), as a vector like x and v.
type Force = Callable[[float, Vector, Vector], Vector]

# What a stepper needs from a model: a(t, x, v) is the acceleration in m/s²
# at time t (s) of the particle at x (m) moving with v (m/s), as a vector.
type Acceleration = Callable[[float, Vector, Vector], Vector]


@dataclass(frozen=True)
class State:
    """The particle at one instant: the time and the vectors of position
    and velocity.

    ``x`` and ``v`` are arrays of the same length, one entry per dimension
    of the motion: one for a line, two for a plane. Lists and numbers are
    converted.
    """

    t: float  # time, s
    x: Vector  # position, m
    v: Vector  # velocity, m/s

    def __post_init__(self) -> None:
        x = np.array(self.x, dtype=np.float64, ndmin=1)
        v = np.array(self.v, dtype=np.float64, ndmin=1)
        if x.ndim != 1 or x.shape != v.shape:
            raise ValueError(
                "x and v must be vectors of the same length,"
                f" got shapes {x.shape} and {v.shape}"
            )
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "v", v)


@dataclass(frozen=True)
class Trajectory:
    """The states of a simulation: one row per instant, one column per
    dimension of the motion."""

    t: NDArray[np.float64]  # times, s, shape (n,)
    x: NDArray[np.float64]  # positions, m, shape (n, d)
    v: NDArray[np.float64]  # velocities, m/s, shape (n, d)

    @classmethod
    def of(cls, states: list[State]) -> Trajectory:
        return cls(
            t=np.array([state.t for state in states]),
            x=np.array([state.x for state in states]),
            v=np.array([state.v for state in states]),
        )


# A stepper: step(state, acceleration, dt) returns the state one time step of
# dt (s) later. Explicit Euler is the stepper of this lesson; later lessons
# add others with the same signature, so the simulation loop stays the same.
type Stepper = Callable[[State, Acceleration, float], State]


def newton(mass: float, *forces: Force) -> Acceleration:
    """Newton's second law for a particle of ``mass`` (kg) under ``forces``.

    Returns the acceleration function a(t, x, v) = (sum of the forces) / m.
    Each force is a function F(t, x, v) that returns a vector in N.
    """
    if mass <= 0:
        raise ValueError(f"mass must be positive, got {mass}")

    def acceleration(t: float, x: Vector, v: Vector) -> Vector:
        total = np.zeros_like(x)
        for force in forces:
            total = total + force(t, x, v)
        return total / mass

    return acceleration


def weight(mass: float, g: ArrayLike) -> Force:
    """The weight m g of a particle of ``mass`` (kg).

    ``g`` is the gravitational acceleration as a vector in m/s² with the
    same number of entries as the position: ``[-9.81]`` on a vertical line
    with up positive, ``[0.0, -9.81]`` in a vertical plane with y upward.
    """
    force = mass * np.array(g, dtype=np.float64, ndmin=1)

    def weight_force(t: float, x: Vector, v: Vector) -> Vector:
        return force

    return weight_force


def euler_step(state: State, acceleration: Acceleration, dt: float) -> State:
    """Advance ``state`` by one explicit Euler step of length ``dt`` (s).

    Position and velocity both change at the rates that hold at the start
    of the step: the old velocity moves the particle, and the acceleration
    at the old state changes the velocity.

    ``state`` (t in s, x in m, v in m/s) is the state at the start of the
    step. ``acceleration`` (m/s²) is the acceleration, given t, x and v.
    ``dt`` (s) is the step length. The ``return`` (t in s, x in m, v in m/s)
    is the state at the end of the step.
    """
    return State(
        t=state.t + dt,
        x=state.x + state.v * dt,
        v=state.v + acceleration(state.t, state.x, state.v) * dt,
    )


def simulate(
    initial: State,
    acceleration: Acceleration,
    dt: float,
    n_steps: int,
    step: Stepper = euler_step,
    until: Callable[[State], bool] | None = None,
) -> Trajectory:
    """Take up to ``n_steps`` steps of length ``dt`` (s) from ``initial``.

    ``step`` is the stepper; explicit Euler unless another is given. The
    trajectory holds the initial state and the state after every step. With
    ``until``, the simulation stops early, after the first state for which
    ``until(state)`` is true; that state is the last one of the trajectory.
    """
    if dt <= 0:
        raise ValueError(f"dt must be positive, got {dt}")
    if n_steps < 0:
        raise ValueError(f"n_steps must not be negative, got {n_steps}")
    states = [initial]
    for _ in range(n_steps):
        states.append(step(states[-1], acceleration, dt))
        if until is not None and until(states[-1]):
            break
    return Trajectory.of(states)
