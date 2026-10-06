"""Kinematics on a line: motion under an acceleration that is a known
function of time.

Quantities are in SI units: seconds, metres, metres per second, and metres
per second squared.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class State:
    """Everything the program knows about the particle at one instant."""

    t: float  # time, s
    x: float  # position, m
    v: float  # velocity, m/s


@dataclass(frozen=True)
class Trajectory:
    """The states of a simulation, one array entry per instant."""

    t: NDArray[np.float64]  # times, s
    x: NDArray[np.float64]  # positions, m
    v: NDArray[np.float64]  # velocities, m/s


def euler_step(
    state: State, acceleration: Callable[[float], float], dt: float
) -> State:
    """Advance ``state`` by one explicit Euler step of length ``dt``.

    Position and velocity both change at the rates that hold at the start of
    the step: the old velocity moves the particle, and the acceleration at
    the old time changes the velocity.
    """
    return State(
        t=state.t + dt,
        x=state.x + state.v * dt,
        v=state.v + acceleration(state.t) * dt,
    )


def simulate(
    initial: State, acceleration: Callable[[float], float], dt: float, n_steps: int
) -> Trajectory:
    """Take ``n_steps`` explicit Euler steps of length ``dt`` from ``initial``.

    The trajectory holds ``n_steps + 1`` states: the initial one and the
    state after every step.
    """
    if dt <= 0:
        raise ValueError(f"dt must be positive, got {dt}")
    if n_steps < 0:
        raise ValueError(f"n_steps must not be negative, got {n_steps}")
    states = [initial]
    for _ in range(n_steps):
        states.append(euler_step(states[-1], acceleration, dt))
    return Trajectory(
        t=np.array([state.t for state in states]),
        x=np.array([state.x for state in states]),
        v=np.array([state.v for state in states]),
    )


def constant_acceleration(initial: State, a: float, t: ArrayLike) -> Trajectory:
    """Return the exact motion under the constant acceleration ``a``.

    ``t`` holds the times at which the motion is evaluated, as a scalar or an
    array. The motion passes through ``initial`` at the time ``initial.t``.
    """
    times = np.asarray(t, dtype=np.float64)
    elapsed = times - initial.t
    return Trajectory(
        t=times,
        x=initial.x + initial.v * elapsed + 0.5 * a * elapsed**2,
        v=initial.v + a * elapsed,
    )
