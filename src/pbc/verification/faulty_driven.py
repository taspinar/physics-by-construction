"""Simulations of the damped driven oscillator with one deliberate fault
each.

EVERY SIMULATION IN THIS MODULE IS WRONG ON PURPOSE. Each is the reference
solution, ``pbc.mechanics.resonance.simulate_driven``, with one mistake of
the kind that is made when a model is turned into code, by a person or by a
coding agent. The lesson on verifying scientific code runs the checks of
``pbc.verification.driven`` on them, and the tests show that each fails
exactly the checks its entry names. Only that lesson and the tests may
import this module (``tests/unit/test_verification_driven.py`` enforces it).
"""

from dataclasses import dataclass

import numpy as np

from pbc.mechanics.dynamics import State, Trajectory, simulate
from pbc.mechanics.integrators import rk4_step
from pbc.verification.driven import Simulation

FAULTY = True  # a marker a reader of the source and the tests can find


def _simulate(acceleration, initial: State, dt: float, n_steps: int) -> Trajectory:
    return simulate(initial, acceleration, dt, n_steps, step=rk4_step)


def drive_not_divided_by_mass(initial, mass, k, b, force, omega, dt, n_steps):
    """The driving force is added to the acceleration as it is: a force in
    N where an acceleration in m/s² belongs."""

    def acceleration(t, x, v):
        return (-k * x - b * v) / mass + force * np.cos(omega * t)

    return _simulate(acceleration, initial, dt, n_steps)


def drive_frozen_within_the_step(initial, mass, k, b, force, omega, dt, n_steps):
    """The driving force is computed once per step, at its start, and held
    while the four stages of the Runge-Kutta step are taken."""
    states = [initial]
    for _ in range(n_steps):
        held = force * np.cos(omega * states[-1].t)

        def acceleration(t, x, v, held=held):
            return (-k * x - b * v + held) / mass

        states.append(rk4_step(states[-1], acceleration, dt))
    return Trajectory.of(states)


def frequency_in_hertz(initial, mass, k, b, force, omega, dt, n_steps):
    """The driving frequency is taken as cycles per second: the force is
    cos(2 π Ω t) where the model has cos(Ω t)."""

    def acceleration(t, x, v):
        return (-k * x - b * v + force * np.cos(2.0 * np.pi * omega * t)) / mass

    return _simulate(acceleration, initial, dt, n_steps)


def drag_with_the_wrong_sign(initial, mass, k, b, force, omega, dt, n_steps):
    """The drag pushes along the velocity instead of against it."""

    def acceleration(t, x, v):
        return (-k * x + b * v + force * np.cos(omega * t)) / mass

    return _simulate(acceleration, initial, dt, n_steps)


@dataclass(frozen=True)
class FaultySimulation:
    """A faulty simulation, its fault in words, and the checks that fail."""

    name: str
    simulate: Simulation
    fault: str
    caught_by: tuple[str, ...]


GALLERY = (
    FaultySimulation(
        "drive not divided by the mass",
        drive_not_divided_by_mass,
        "the driving force enters the acceleration without the division by m",
        ("limits", "convergence-order", "units", "energy-balance"),
    ),
    FaultySimulation(
        "drive frozen within the step",
        drive_frozen_within_the_step,
        "the driving force is evaluated once per step, not at each stage",
        ("convergence-order", "energy-balance"),
    ),
    FaultySimulation(
        "frequency in hertz",
        frequency_in_hertz,
        "the driving frequency is read as cycles per second",
        ("convergence-order", "energy-balance"),
    ),
    FaultySimulation(
        "drag with the wrong sign",
        drag_with_the_wrong_sign,
        "the drag accelerates the mass",
        ("limits", "convergence-order", "energy-balance"),
    ),
)
