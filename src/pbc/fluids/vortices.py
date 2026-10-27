"""Vortices and the flow around an obstacle (lesson FL3), on the solver of
``pbc.fluids.navier_stokes``.

Two flows. The double shear layer: two thin layers of opposite shear in a
periodic box, slightly disturbed, roll up into vortices. And a circular
cylinder in a stream: the body is imposed by direct forcing, the velocity set
to zero in the cells it covers before each projection, and a fringe region
just upstream of the periodic boundary relaxes the flow back to the free
stream, so that the wake leaving the box on the right does not re-enter on
the left. The box is periodic across the stream, so it holds a row of
cylinders one box width apart: the blockage D / width is part of the model.

Lengths are in units of the diameter D and velocities in units of the free
stream U, so the Reynolds number is Re = U D / nu = 1 / nu, and a frequency
f gives the Strouhal number St = f D / U.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from pbc.fluids.navier_stokes import Grid, march, project, vorticity

__all__ = [
    "ROSHKO_FIT",
    "ROSHKO_STABLE",
    "Cylinder",
    "Wake",
    "circulation",
    "cylinder_wake",
    "double_shear_layer",
    "fringe_weight",
    "roshko_strouhal",
    "shedding_frequency",
    "solid_fraction",
    "wake_constraint",
]

Array = NDArray[np.float64]

# region: roshko
# Roshko (1954), NACA Report 1191, p. 11: the "stable range" of regular vortex
# streets, and his fit to the measured shedding frequencies within it,
# S = 0.212 (1 - 21.2 / R), stated for 50 < R < 150.
ROSHKO_STABLE = (40.0, 150.0)
ROSHKO_FIT = (50.0, 150.0)


def roshko_strouhal(reynolds: float) -> float:
    """The Strouhal number of a circular cylinder by Roshko's fit to his
    measurements, within the Reynolds numbers it was fitted for."""
    if not ROSHKO_FIT[0] < reynolds < ROSHKO_FIT[1]:
        raise ValueError(f"Roshko's fit holds for 50 < Re < 150, not {reynolds}")
    return 0.212 * (1.0 - 21.2 / reynolds)


# endregion: roshko


def double_shear_layer(
    grid: Grid, steepness: float = 30.0, perturbation: float = 0.05
) -> tuple[Array, Array]:
    """Two shear layers on the unit square: u = tanh(steepness (y - 1/4))
    below y = 1/2 and tanh(steepness (3/4 - y)) above, with the small
    disturbance v = perturbation sin(2 pi (x + 1/4)), projected."""
    _, y = grid.points("u")
    u = np.where(
        y <= 0.5, np.tanh(steepness * (y - 0.25)), np.tanh(steepness * (0.75 - y))
    )
    x, _ = grid.points("v")
    v = perturbation * np.sin(2 * np.pi * (x + 0.25))
    u, v, _ = project(u, v, grid)
    return u, v


def circulation(u: Array, v: Array, grid: Grid) -> float:
    """The circulation around the box, the integral of the vorticity over it
    (m^2/s); zero for any periodic velocity, since the box has no edge."""
    return float(np.sum(vorticity(u, v, grid)) * grid.dx * grid.dy)


@dataclass(frozen=True)
class Cylinder:
    """A circular cylinder of the given ``diameter`` centred at ``centre``."""

    centre: tuple[float, float]
    diameter: float = 1.0


def solid_fraction(grid: Grid, cylinder: Cylinder) -> tuple[Array, Array]:
    """The fraction of each u and v point inside the cylinder: one inside,
    zero outside, and a linear ramp one cell wide across the surface, so that
    the body does not jump from cell to cell as a staircase."""

    def fraction(where: str) -> Array:
        x, y = grid.points(where)
        r = np.hypot(x - cylinder.centre[0], y - cylinder.centre[1])
        return np.clip(0.5 - (r - cylinder.diameter / 2) / grid.dx, 0.0, 1.0)

    return fraction("u"), fraction("v")


def fringe_weight(grid: Grid, start: float, length: float) -> tuple[Array, Array]:
    """The weight of the fringe at the u and v points: zero before ``start``,
    rising as sin^2 over ``length`` to one, and one up to the end of the box."""

    def weight(where: str) -> Array:
        x, _ = grid.points(where)
        s = np.clip((x - start) / length, 0.0, 1.0)
        return np.sin(0.5 * np.pi * s) ** 2

    return weight("u"), weight("v")


def wake_constraint(
    grid: Grid,
    cylinder: Cylinder,
    speed: float,
    fringe: tuple[float, float],
    rate: float,
) -> Callable[[Array, Array, float], tuple[Array, Array]]:
    """The constraint of a stage of the wake: in the fringe the velocity
    relaxes towards (``speed``, 0) at ``rate`` (1/s) times the fringe's
    weight, exactly over the stage; then the velocity in the body is removed
    in proportion to its solid fraction."""
    solid_u, solid_v = solid_fraction(grid, cylinder)
    weight_u, weight_v = fringe_weight(grid, *fringe)

    # region: constraint
    def constrain(u: Array, v: Array, dt: float) -> tuple[Array, Array]:
        u = speed + (u - speed) * np.exp(-rate * weight_u * dt)
        v = v * np.exp(-rate * weight_v * dt)
        return u * (1.0 - solid_u), v * (1.0 - solid_v)

    # endregion: constraint
    return constrain


@dataclass(frozen=True)
class Wake:
    """A computed wake: the times of the steps, the cross-stream velocity at
    the probe at each, the final velocity, its grid, and the cylinder."""

    t: Array
    probe: Array
    u: Array
    v: Array
    grid: Grid
    cylinder: Cylinder
    reynolds: float


def cylinder_wake(
    reynolds: float,
    cells_per_diameter: int = 10,
    width: float = 12.0,
    length: float = 20.0,
    upstream: float = 6.0,
    duration: float = 60.0,
    courant: float = 1.5,
    kick: float = 0.3,
    probe_distance: float = 2.0,
    fringe_rate: float = 50.0,
) -> Wake:
    """The flow past a cylinder of diameter one in a stream of speed one at
    the Reynolds number ``reynolds``, in a box ``length`` by ``width``, the
    cylinder ``upstream`` from the left end and midway across, the last three
    diameters of the box a fringe. A small cross-stream push of speed ``kick``
    behind the cylinder and off its axis breaks the symmetry at the start, so
    that shedding, where the flow sheds, begins sooner. The probe is
    ``probe_distance`` diameters behind the centre, on the axis."""
    grid = Grid(
        round(length * cells_per_diameter),
        round(width * cells_per_diameter),
        length,
        width,
    )
    cylinder = Cylinder((upstream, width / 2))
    constrain = wake_constraint(grid, cylinder, 1.0, (length - 3.0, 2.0), fringe_rate)
    solid_u, solid_v = solid_fraction(grid, cylinder)
    x, y = grid.points("v")
    bump = np.exp(-((x - upstream - 1.5) ** 2 + (y - width / 2 - 0.3) ** 2))
    u, v, _ = project((1.0 - solid_u), kick * bump * (1.0 - solid_v), grid)
    i = round((upstream + probe_distance) / grid.dx - 0.5)
    j = round((width / 2) / grid.dy)
    times, probe = [], []

    def observe(t: float, u: Array, v: Array) -> None:
        times.append(t)
        probe.append(v[j, i])

    u, v, _ = march(
        u,
        v,
        grid,
        1.0 / reynolds,
        duration,
        None,
        courant,
        constrain,
        observe,
        largest_step=0.1,
    )
    return Wake(np.array(times), np.array(probe), u, v, grid, cylinder, reynolds)


def shedding_frequency(t: Array, signal: Array) -> tuple[float, Array]:
    """The frequency of an oscillating ``signal`` (Hz) from its upward
    crossings of its mean, each placed by linear interpolation between the
    two samples around it: the number of whole periods between the first and
    the last crossing over the time between them. Also returns the crossing
    times."""
    s = signal - np.mean(signal)
    k = np.nonzero((s[:-1] < 0) & (s[1:] >= 0))[0]
    if len(k) < 2:
        raise ValueError("fewer than two upward crossings: no oscillation")
    crossings = t[k] - s[k] * (t[k + 1] - t[k]) / (s[k + 1] - s[k])
    return float((len(crossings) - 1) / (crossings[-1] - crossings[0])), crossings
