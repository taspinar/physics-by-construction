"""Closed forms of the oscillator's motion with one deliberate fault each.

EVERY MOTION IN THIS MODULE IS WRONG ON PURPOSE. Each is offered as the
motion of a mass on a spring from a start (x0, v0), with the signature of
``pbc.mechanics.oscillator.harmonic_motion``, and carries one mistake of the
kind made when the formula is derived by hand or written by a model. The
lesson on counterexamples and physical constraints runs the checks of
``pbc.verification.constraints`` on them, and the tests show that each
fails exactly the checks its entry names. Only that lesson's experiment and
the tests may import this module
(``tests/unit/test_verification_constraints.py`` enforces it).
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import State, Trajectory
from pbc.verification.constraints import Motion

FAULTY = True  # a marker a reader of the source and the tests can find


def _elapsed(initial: State, t: ArrayLike) -> tuple[NDArray, NDArray]:
    times = np.array(t, dtype=np.float64, ndmin=1)
    return times, (times - initial.t)[:, np.newaxis]


def _oscillation(initial: State, omega: float, t: ArrayLike) -> Trajectory:
    """The textbook formula with the angular frequency it is given."""
    times, s = _elapsed(initial, t)
    cos, sin = np.cos(omega * s), np.sin(omega * s)
    return Trajectory(
        t=times,
        x=initial.x * cos + initial.v / omega * sin,
        v=-initial.x * omega * sin + initial.v * cos,
    )


def missing_square_root(initial: State, mass: float, k: float, t: ArrayLike):
    """The textbook formula with the angular frequency k / m where the model
    has sqrt(k / m)."""
    omega = k / mass
    return _oscillation(initial, omega, t)


def frequency_in_hertz(initial: State, mass: float, k: float, t: ArrayLike):
    """The textbook formula with the frequency in cycles per second,
    sqrt(k / m) / (2 pi), taken for the angular frequency in rad/s."""
    omega = np.sqrt(k / mass) / (2.0 * np.pi)
    return _oscillation(initial, omega, t)


def phase_from_the_arctangent(initial: State, mass: float, k: float, t: ArrayLike):
    """The motion as an amplitude and a phase, x = A cos(omega t - phi), with
    the phase from tan(phi) = v0 / (omega x0) by the arctangent, which
    returns an angle between -pi/2 and pi/2: right for every start at a
    positive displacement, and the wrong half of the circle for every start
    at a negative one, where ``np.arctan2`` is needed."""
    omega = np.sqrt(k / mass)
    times, s = _elapsed(initial, t)
    amplitude = np.sqrt(initial.x**2 + (initial.v / omega) ** 2)
    phase = np.arctan(initial.v / (omega * initial.x))
    return Trajectory(
        t=times,
        x=amplitude * np.cos(omega * s - phase),
        v=-amplitude * omega * np.sin(omega * s - phase),
    )


def phase_with_the_wrong_sign(initial: State, mass: float, k: float, t: ArrayLike):
    """The amplitude and phase form with cos(omega t + phi) where the
    derivation gives cos(omega t - phi): the motion of the start with the
    opposite velocity."""
    omega = np.sqrt(k / mass)
    times, s = _elapsed(initial, t)
    amplitude = np.sqrt(initial.x**2 + (initial.v / omega) ** 2)
    phase = np.arctan2(initial.v, omega * initial.x)
    return Trajectory(
        t=times,
        x=amplitude * np.cos(omega * s + phase),
        v=-amplitude * omega * np.sin(omega * s + phase),
    )


def division_by_omega_forgotten(initial: State, mass: float, k: float, t: ArrayLike):
    """The textbook formula with v0 sin(omega t) where it has
    (v0 / omega) sin(omega t), and the velocity its derivative."""
    omega = np.sqrt(k / mass)
    times, s = _elapsed(initial, t)
    cos, sin = np.cos(omega * s), np.sin(omega * s)
    return Trajectory(
        t=times,
        x=initial.x * cos + initial.v * sin,
        v=-initial.x * omega * sin + initial.v * omega * cos,
    )


@dataclass(frozen=True)
class Faulty:
    """A wrong closed form and the checks that must find a counterexample
    to it."""

    name: str
    motion: Motion
    caught_by: frozenset[str]


GALLERY = (
    Faulty(
        "missing square root",
        missing_square_root,
        frozenset({"dimensions", "conservation"}),
    ),
    Faulty(
        "phase from the arctangent",
        phase_from_the_arctangent,
        frozenset({"symmetry"}),
    ),
    Faulty(
        "phase with the wrong sign",
        phase_with_the_wrong_sign,
        frozenset({"limits"}),
    ),
    Faulty(
        "frequency in hertz",
        frequency_in_hertz,
        frozenset({"conservation"}),
    ),
)
# The candidate of the lesson's exercise, kept out of the gallery the page
# shows.
EXERCISE = Faulty(
    "division by omega forgotten",
    division_by_omega_forgotten,
    frozenset({"dimensions", "limits"}),
)
