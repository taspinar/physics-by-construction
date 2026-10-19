"""The one-dimensional shallow-water equations (lesson FL5): water of depth h
and depth-averaged velocity u over a bed of height b(x),

    h_t + (h u)_x = 0,
    (h u)_t + (h u^2 + g h^2 / 2)_x = -g h b_x.

The state of a cell is (h, h u), in m and m^2/s. Long waves travel at
u +- sqrt(g h) relative to the ground. ``hll_flux`` is the Riemann solver of
the shared finite-volume interface (``pbc.fluids.finite_volume``), with the
wave-speed estimates of Einfeldt, which keep the depth from becoming
negative under the CFL condition.

Over a bed that is not flat the pressure term and the bed slope must balance
exactly when the water is at rest. ``well_balanced`` builds the fluxes and the
bed source by hydrostatic reconstruction (Audusse et al., 2004), which keeps
a lake at rest to round-off; ``pointwise_source`` is the naive alternative
that does not. ``dam_break`` is the exact solution of the dam break over a
flat bed, wet (Stoker) or dry (Ritter) downstream.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import brentq

from pbc.fluids.finite_volume import Array, Boundary, interface_fluxes, with_ghosts

__all__ = [
    "DRY",
    "GRAVITY",
    "DamBreak",
    "dam_break",
    "flux",
    "hll_flux",
    "max_speed",
    "pointwise_source",
    "reflective",
    "velocity",
    "well_balanced",
]

GRAVITY = 9.81  # m/s^2
DRY = 1e-10  # m: below this depth a cell is dry, and its velocity is zero


def velocity(q: Array) -> Array:
    """The velocity h u / h of each state (m/s), zero where the cell is dry."""
    h = q[..., 0]
    wet = h > DRY
    return np.where(wet, q[..., 1] / np.where(wet, h, 1.0), 0.0)


def flux(q: Array) -> Array:
    """The physical flux (h u, h u^2 + g h^2 / 2) of the states ``q``."""
    h = q[..., 0]
    u = velocity(q)
    return np.stack([h * u, h * u * u + 0.5 * GRAVITY * h * h], axis=-1)


def max_speed(q: Array) -> float:
    """The largest signal speed |u| + sqrt(g h) of the states, for the CFL
    condition."""
    return float(np.max(np.abs(velocity(q)) + np.sqrt(GRAVITY * q[..., 0])))


def hll_flux(left: Array, right: Array) -> Array:
    """The HLL flux through a face: the exact flux of a Riemann solution
    reduced to its two outermost waves, with the speeds of Einfeldt (the
    extreme of the characteristic speeds of the two states and of their Roe
    average). Where both waves move the same way the face sees the upstream
    flux."""
    h_left, h_right = left[:, 0], right[:, 0]
    u_left, u_right = velocity(left), velocity(right)
    c_left, c_right = np.sqrt(GRAVITY * h_left), np.sqrt(GRAVITY * h_right)
    root_left, root_right = np.sqrt(h_left), np.sqrt(h_right)
    roots = root_left + root_right
    wet = roots > 0
    safe = np.where(wet, roots, 1.0)
    u_roe = np.where(wet, (root_left * u_left + root_right * u_right) / safe, 0.0)
    c_roe = np.sqrt(0.5 * GRAVITY * (h_left + h_right))
    slow = np.minimum(np.minimum(u_left - c_left, u_right - c_right), u_roe - c_roe)
    fast = np.maximum(np.maximum(u_left + c_left, u_right + c_right), u_roe + c_roe)
    f_left, f_right = flux(left), flux(right)
    span = np.where(fast > slow, fast - slow, 1.0)
    middle = (
        fast[:, None] * f_left
        - slow[:, None] * f_right
        + (slow * fast)[:, None] * (right - left)
    ) / span[:, None]
    return np.where(
        slow[:, None] >= 0, f_left, np.where(fast[:, None] <= 0, f_right, middle)
    )


def reflective(q: Array) -> tuple[Array, Array]:
    """A wall at each end: the ghost cell mirrors the depth and reverses the
    velocity, so no water crosses the face."""
    return q[0] * np.array([1.0, -1.0]), q[-1] * np.array([1.0, -1.0])


def well_balanced(
    bed: Array, dx: float, boundary: Boundary
) -> tuple[Callable[[Array], Array], Callable[[Array], Array]]:
    """The face fluxes and the bed source of hydrostatic reconstruction over
    the cell bed heights ``bed`` (m) on cells of width ``dx`` (m), for
    ``finite_volume.evolve``.

    At each face the two depths are rebuilt over the higher of the two beds,
    h* = max(0, h + b - max(b_left, b_right)), keeping each cell's velocity,
    and the HLL flux is taken between the rebuilt states. The source adds to
    each cell the pressure g / 2 (h^2 - h*^2) of the difference at its two
    faces. For water at rest with a flat surface the rebuilt states on the two
    sides of a face are equal, the fluxes are the pressure g h*^2 / 2, and
    the source cancels their difference exactly."""
    bed_padded = np.concatenate([[bed[0]], bed, [bed[-1]]])
    top = np.maximum(bed_padded[:-1], bed_padded[1:])

    def rebuilt(q: Array) -> tuple[Array, Array, Array]:
        padded = with_ghosts(q, boundary)
        h, u = padded[:, 0], velocity(padded)
        h_left = np.maximum(0.0, h[:-1] + bed_padded[:-1] - top)
        h_right = np.maximum(0.0, h[1:] + bed_padded[1:] - top)
        left = np.stack([h_left, h_left * u[:-1]], axis=-1)
        right = np.stack([h_right, h_right * u[1:]], axis=-1)
        return left, right, h

    def fluxes(q: Array) -> Array:
        left, right, _ = rebuilt(q)
        return hll_flux(left, right)

    def source(q: Array) -> Array:
        left, right, h = rebuilt(q)
        cell = h[1:-1]
        # The cell's own side of its right face is left[1:], of its left face
        # right[:-1].
        push = 0.5 * GRAVITY * (left[1:, 0] ** 2 - right[:-1, 0] ** 2)
        return np.stack([np.zeros_like(cell), push], axis=-1) / dx

    return fluxes, source


def pointwise_source(
    bed: Array, dx: float, boundary: Boundary
) -> tuple[Callable[[Array], Array], Callable[[Array], Array]]:
    """The naive discretisation over the bed ``bed`` (m): HLL fluxes between
    the cell states as they are, and the source -g h db/dx with a central
    difference of the bed. Each is consistent, but their errors do not cancel
    for water at rest, which then starts to move."""
    bed_padded = np.concatenate([[bed[0]], bed, [bed[-1]]])
    slope = (bed_padded[2:] - bed_padded[:-2]) / (2.0 * dx)

    def fluxes(q: Array) -> Array:
        return interface_fluxes(q, hll_flux, boundary)

    def source(q: Array) -> Array:
        return np.stack([np.zeros(len(q)), -GRAVITY * q[:, 0] * slope], axis=-1)

    return fluxes, source


@dataclass(frozen=True)
class DamBreak:
    """The exact dam break over a flat bed from still water of depth
    ``upstream`` left of the dam and ``downstream`` right of it (m): the
    depth ``middle`` and velocity ``middle_velocity`` between the
    rarefaction and the front, and the speed ``front_speed`` of the front
    (a shock over a wet bed, the dry front 2 sqrt(g h) over a dry one)."""

    upstream: float
    downstream: float
    middle: float
    middle_velocity: float
    front_speed: float

    def depth(self, x: ArrayLike, t: float, dam: float = 0.0) -> Array:
        """The depth (m) at the positions ``x`` (m) at the time ``t`` (s)."""
        xi = (np.asarray(x, dtype=float) - dam) / t
        c_up = np.sqrt(GRAVITY * self.upstream)
        c_mid = np.sqrt(GRAVITY * self.middle)
        tail = self.middle_velocity - c_mid
        fan = (2.0 * c_up - xi) ** 2 / (9.0 * GRAVITY)
        return np.select(
            [xi <= -c_up, xi <= tail, xi <= self.front_speed],
            [self.upstream, fan, self.middle],
            self.downstream,
        )

    def velocity(self, x: ArrayLike, t: float, dam: float = 0.0) -> Array:
        """The velocity (m/s) at the positions ``x`` (m) at the time ``t`` (s)."""
        xi = (np.asarray(x, dtype=float) - dam) / t
        c_up = np.sqrt(GRAVITY * self.upstream)
        c_mid = np.sqrt(GRAVITY * self.middle)
        tail = self.middle_velocity - c_mid
        return np.select(
            [xi <= -c_up, xi <= tail, xi <= self.front_speed],
            [0.0, 2.0 / 3.0 * (c_up + xi), self.middle_velocity],
            0.0,
        )


def dam_break(upstream: float, downstream: float) -> DamBreak:
    """The exact solution of the dam break: a rarefaction into the deep water
    and, over a wet bed, a shock into the shallow water.

    The middle depth h_m is the root of 2 (c_up - c_m) = (h_m - h_d)
    sqrt(g (h_m + h_d) / (2 h_m h_d)), the velocity behind the rarefaction
    equal to the velocity behind the shock, with c = sqrt(g h); the shock
    moves at h_m u_m / (h_m - h_d), which conserves the mass across it."""
    if not upstream > downstream >= 0:
        raise ValueError("the dam holds deeper water upstream")
    c_up = np.sqrt(GRAVITY * upstream)
    if downstream == 0:
        return DamBreak(upstream, 0.0, 0.0, 2.0 * c_up, 2.0 * c_up)

    def mismatch(h: float) -> float:
        behind_fan = 2.0 * (c_up - np.sqrt(GRAVITY * h))
        behind_shock = (h - downstream) * np.sqrt(
            0.5 * GRAVITY * (h + downstream) / (h * downstream)
        )
        return behind_fan - behind_shock

    middle = brentq(mismatch, downstream, upstream, xtol=1e-15, rtol=1e-15)
    u_middle = 2.0 * (c_up - np.sqrt(GRAVITY * middle))
    return DamBreak(
        upstream,
        downstream,
        middle,
        u_middle,
        middle * u_middle / (middle - downstream),
    )
