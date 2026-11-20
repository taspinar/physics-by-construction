"""Physical constraints as hunts for a counterexample (lesson SA7).

A closed form offered as the motion of a mass on a spring, x'' = -(k/m) x,
must obey constraints that need no reference solution: its **dimensions**
(the motion does not depend on the units it is computed in), its
**symmetries** (the mirror and time reversal), its **limiting cases** (the
start, and a spring too weak to matter), and the **conservation** of its
energy. Each constraint is a claim about every input, so one input that
breaks it is a counterexample, and the constraint says which inputs to try.

Each check runs over a fixed list of cases, ``CASES``, in order, and
reports the first trial whose relative deviation exceeds ``TOLERANCE`` as
its witness, or that it found none in the trials it made. Finding none is
not a proof: the four constraints are necessary for the motion, not
sufficient, and the cases are finitely many.

A candidate is a function ``motion(initial, mass, k, t)`` with the
signature of ``pbc.mechanics.oscillator.harmonic_motion``: the start (a
``State`` on a line), the mass (kg), the spring constant (N/m), and the
times (s), returning a ``Trajectory``.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from pbc.mechanics.dynamics import State, Trajectory
from pbc.mechanics.oscillator import energy

type Motion = Callable[[State, float, float, ArrayLike], Trajectory]

# The largest relative deviation a correct closed form may show, written
# before any check runs: far above round-off, far below a fault.
TOLERANCE = 1e-8
# The ratio k / m of a spring too weak to matter over the times of a case,
# in s⁻².
WEAK = 1e-12
# Changes of the units of mass, length, and time: the new unit of each, in
# kg, m, and s.
SCALINGS = ((2.0, 3.0, 5.0), (0.7, 0.2, 1.9), (13.0, 0.05, 0.4))
SAMPLES = 41  # times per case, over two periods

CHECKS = ("dimensions", "symmetry", "limits", "conservation")


@dataclass(frozen=True)
class Case:
    """One input of the hunt: a mass (kg), a spring constant (N/m), and a
    start at the time zero, a position (m) and a velocity (m/s)."""

    mass: float
    k: float
    x0: float
    v0: float

    @property
    def omega(self) -> float:
        """The angular frequency of the case, sqrt(k / m), in rad/s."""
        return float(np.sqrt(self.k / self.mass))

    def start(self) -> State:
        return State(0.0, self.x0, self.v0)

    def times(self) -> NDArray[np.float64]:
        """Two periods of the case, from the start."""
        return np.linspace(0.0, 4.0 * np.pi / self.omega, SAMPLES)


# region: cases
# Not round numbers, and every start at a positive displacement, as most
# tests would write it; the velocities have both signs.
CASES = (
    Case(mass=0.37, k=1.3, x0=0.12, v0=0.0),
    Case(mass=0.37, k=1.3, x0=0.12, v0=-0.45),
    Case(mass=2.9, k=11.0, x0=0.05, v0=0.3),
)
# endregion: cases


@dataclass(frozen=True)
class Finding:
    """The outcome of one check of one candidate.

    ``counterexample`` is True when a trial broke the constraint; then
    ``case`` and ``trial`` name the witness and ``deviation`` is its
    relative deviation. Otherwise ``deviation`` is the largest one seen
    and the outcome says only that ``tried`` trials found nothing."""

    check: str
    counterexample: bool
    tried: int
    deviation: float
    case: Case | None = None
    trial: str = ""

    @property
    def outcome(self) -> str:
        return "counterexample" if self.counterexample else "none found"


def deviation(observed: Trajectory, demanded: Trajectory, duration: float) -> float:
    """The largest relative distance between two motions on the same times:
    positions measured against the largest of the demanded position and the
    demanded velocity times ``duration`` (s), velocities against that length
    over ``duration``."""
    length = max(
        float(np.max(np.abs(demanded.x))),
        float(np.max(np.abs(demanded.v))) * duration,
    )
    position = float(np.max(np.abs(observed.x - demanded.x))) / length
    velocity = float(np.max(np.abs(observed.v - demanded.v))) * duration / length
    return max(position, velocity)


def _hunt(check: str, trials: Iterable[tuple[Case, str, float]]) -> Finding:
    tried, largest = 0, 0.0
    for case, trial, found in trials:
        tried += 1
        if not found <= TOLERANCE:  # a NaN breaks the constraint too
            return Finding(check, True, tried, found, case, trial)
        largest = max(largest, found)
    return Finding(check, False, tried, largest)


def _on_a_line(t: NDArray[np.float64], x: ArrayLike, v: ArrayLike) -> Trajectory:
    shape = (t.size, 1)
    return Trajectory(t, np.broadcast_to(x, shape), np.broadcast_to(v, shape))


def dimensions(motion: Motion, cases: Iterable[Case] = CASES) -> Finding:
    """The motion does not depend on the units: computed in other units of
    mass, length, and time and converted back, it is the same motion."""

    def trials():
        for case in cases:
            t = case.times()
            reference = motion(case.start(), case.mass, case.k, t)
            for mass_unit, length_unit, time_unit in SCALINGS:
                mass = case.mass / mass_unit
                k = case.k * time_unit**2 / mass_unit  # N/m is kg/s²
                x0 = case.x0 / length_unit
                v0 = case.v0 * time_unit / length_unit
                other = motion(State(0.0, x0, v0), mass, k, t / time_unit)
                back = Trajectory(
                    t, other.x * length_unit, other.v * length_unit / time_unit
                )
                units = f"units of {mass_unit:g} kg, {length_unit:g} m, {time_unit:g} s"
                yield case, units, deviation(back, reference, t[-1])

    return _hunt("dimensions", trials())


def symmetry(motion: Motion, cases: Iterable[Case] = CASES) -> Finding:
    """The mirror and time reversal. A spring pulls back equally from either
    side, so the motion from (-x0, -v0) is the mirror image of the motion
    from (x0, v0). Its force depends on neither the time nor the velocity,
    so the motion run backwards from (x0, v0) is the motion forwards from
    (x0, -v0), with the velocity reversed."""

    def trials():
        for case in cases:
            t = case.times()
            forward = motion(case.start(), case.mass, case.k, t)
            mirrored = motion(State(0.0, -case.x0, -case.v0), case.mass, case.k, t)
            image = Trajectory(t, -forward.x, -forward.v)
            yield case, "the mirror", deviation(mirrored, image, t[-1])

            backward = motion(case.start(), case.mass, case.k, -t)
            run_back = Trajectory(t, backward.x, -backward.v)
            reversed_start = motion(State(0.0, case.x0, -case.v0), case.mass, case.k, t)
            yield case, "time reversal", deviation(run_back, reversed_start, t[-1])

    return _hunt("symmetry", trials())


def limits(motion: Motion, cases: Iterable[Case] = CASES) -> Finding:
    """Two limiting cases: at the start the motion is the start itself, and
    on a spring too weak to matter it is the free motion x0 + v0 t."""

    def trials():
        for case in cases:
            at_start = motion(case.start(), case.mass, case.k, [0.0])
            start = _on_a_line(np.zeros(1), case.x0, case.v0)
            yield case, "the start", deviation(at_start, start, 1.0 / case.omega)

            t = case.times()
            weak = motion(case.start(), case.mass, WEAK * case.mass, t)
            free = _on_a_line(t, (case.x0 + case.v0 * t)[:, np.newaxis], case.v0)
            yield case, "a weak spring", deviation(weak, free, t[-1])

    return _hunt("limits", trials())


def conservation(motion: Motion, cases: Iterable[Case] = CASES) -> Finding:
    """The energy m v² / 2 + k x² / 2 of the motion does not change."""

    def trials():
        for case in cases:
            path = motion(case.start(), case.mass, case.k, case.times())
            e = energy(path, case.mass, case.k)
            yield case, "the energy", float(np.max(np.abs(e - e[0]))) / e[0]

    return _hunt("conservation", trials())


def examine(motion: Motion, cases: Iterable[Case] = CASES) -> tuple[Finding, ...]:
    """The four checks of ``motion``, in the order of ``CHECKS``."""
    cases = tuple(cases)
    return tuple(
        check(motion, cases) for check in (dimensions, symmetry, limits, conservation)
    )
