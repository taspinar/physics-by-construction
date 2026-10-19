"""The conservative finite-volume method in one dimension: the interface that
the Burgers and shallow-water lessons share (FL9, FL5, and the capstone FL10).

A cell j of width dx holds the average q_j of the conserved quantities. Over a
step dt the average changes only by what flows through the two faces of the
cell,

    q_j <- q_j - dt / dx (F_{j+1/2} - F_{j-1/2}),

and the flux F_{j+1/2} through a face is computed once, from the states on its
two sides, by a Riemann solver: a function ``riemann(left, right)`` of the
system that returns the flux for arrays of left and right states. What leaves
one cell enters its neighbour, so the sum over the cells changes only by the
fluxes through the two ends of the domain. ``evolve`` records that budget at
every step.

A state array has the cells along its first axis: shape (n,) for one conserved
quantity, (n, m) for a system of m. A boundary is a function that returns the
ghost cells beyond the two ends, each of the shape of one cell.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
RiemannSolver = Callable[[Array, Array], Array]
Boundary = Callable[[Array], tuple[Array, Array]]

__all__ = [
    "Run",
    "conservative_update",
    "evolve",
    "interface_fluxes",
    "periodic",
    "rusanov",
    "transmissive",
    "with_ghosts",
]


def periodic(q: Array) -> tuple[Array, Array]:
    """The domain closes on itself: the ghost beyond the left end is the last
    cell, the one beyond the right end the first."""
    return q[-1], q[0]


def transmissive(q: Array) -> tuple[Array, Array]:
    """An open end: each ghost copies the cell next to it, so a wave leaves
    the domain without a jump at the face."""
    return q[0], q[-1]


def with_ghosts(q: Array, boundary: Boundary) -> Array:
    """The cells with one ghost cell added at each end: shape (n + 2, ...)."""
    left, right = boundary(q)
    return np.concatenate([np.asarray(left)[None], q, np.asarray(right)[None]])


def interface_fluxes(q: Array, riemann: RiemannSolver, boundary: Boundary) -> Array:
    """The flux through each of the n + 1 faces of the n cells, the first face
    at the left end of the domain and the last at the right end."""
    padded = with_ghosts(q, boundary)
    return riemann(padded[:-1], padded[1:])


def conservative_update(q: Array, fluxes: Array, dt: float, dx: float) -> Array:
    """One step of the cell averages from the fluxes through their faces:
    each cell gains what enters through its left face and loses what leaves
    through its right face."""
    return q - dt / dx * (fluxes[1:] - fluxes[:-1])


def rusanov(
    flux: Callable[[Array], Array], speed: Callable[[Array], Array]
) -> RiemannSolver:
    """The Rusanov (local Lax-Friedrichs) flux of any system: the mean of the
    two physical fluxes, minus a diffusion set by the largest signal speed
    ``speed`` of the two states. It needs no solution of the Riemann problem,
    and smears a shock over more cells than an exact solver does."""

    def riemann(left: Array, right: Array) -> Array:
        a = np.maximum(speed(left), speed(right))
        if left.ndim > 1:
            a = a[:, None]
        return 0.5 * (flux(left) + flux(right)) - 0.5 * a * (right - left)

    return riemann


@dataclass(frozen=True)
class Run:
    """A run of ``evolve``: the final cell averages ``q``, the times ``t``
    (k + 1,) of the steps, the ``totals`` (k + 1, ...) of each conserved
    quantity over the domain (the sum of the averages times dx), and
    ``inflow`` (k + 1, ...), what entered through the two ends up to each
    time (the flux in at the left end minus the flux out at the right end,
    summed over the steps). The budget of a conservative scheme is
    ``totals - totals[0] - inflow``: zero up to round-off, plus what a
    ``source`` added."""

    q: Array
    t: Array
    totals: Array
    inflow: Array

    @property
    def budget_residual(self) -> Array:
        """The change of each total minus what entered through the ends, at
        each time."""
        return self.totals - self.totals[0] - self.inflow


def evolve(
    q0: Array,
    dx: float,
    t_end: float,
    fluxes: Callable[[Array], Array],
    max_speed: Callable[[Array], float],
    courant: float,
    source: Callable[[Array], Array] | None = None,
) -> Run:
    """Advance the cell averages ``q0`` from the time 0 to ``t_end`` with
    steps chosen by the CFL condition: dt = ``courant`` dx / ``max_speed``,
    the last step shortened to end at ``t_end``. ``fluxes(q)`` returns the
    n + 1 face fluxes of the state (``interface_fluxes`` with a Riemann
    solver and a boundary); ``source(q)``, if given, is added as dt times
    its value, computed from the same state as the fluxes. A state with no
    wave speed (all zero, or fully dry) bounds no step: it is left as it is
    and the run jumps to ``t_end`` in one step with no flux and no source."""
    q = np.array(q0, dtype=float)
    t = 0.0
    times = [t]
    totals = [q.sum(axis=0) * dx]
    inflow = [np.zeros_like(totals[0])]
    while t < t_end:
        speed = max_speed(q)
        if speed == 0.0:
            times.append(t_end)
            totals.append(totals[-1])
            inflow.append(inflow[-1])
            break
        dt = min(courant * dx / speed, t_end - t)
        face = fluxes(q)
        added = None if source is None else source(q)
        q = conservative_update(q, face, dt, dx)
        if added is not None:
            q = q + dt * added
        t = t_end if t + dt >= t_end else t + dt
        times.append(t)
        totals.append(q.sum(axis=0) * dx)
        inflow.append(inflow[-1] + dt * (face[0] - face[-1]))
    return Run(q=q, t=np.array(times), totals=np.array(totals), inflow=np.array(inflow))
