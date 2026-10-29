"""The gravitational wave of two bodies spiralling together, from their motion.

**The inspiral.** Two masses m1 and m2 on a circular orbit of separation a
turn at the angular frequency omega = sqrt(GM / a³), M = m1 + m2 (Kepler's
third law), and the orbit shrinks at the rate da/dt of the quadrupole power
(``pbc.mechanics.chirp.shrink_rate``, the one input that is not
Newtonian). Integrating a and the orbital phase together gives the motion
of the two bodies at every time; the model is cut off at the innermost
stable circular orbit, a = 6 GM / c², where a slowly shrinking circular
orbit stops being a fair description.

**The wave.** The quadrupole formula gives the strain far from the source
from the second time derivative of the trace-free mass quadrupole
Q_ij = sum m (x_i x_j - delta_ij |x|² / 3) of the bodies. For an observer at
the distance D in the direction n, with p and q two unit vectors across n,

    h_plus  = (G / (c⁴ D)) (Q''_pp - Q''_qq),
    h_cross = (2 G / (c⁴ D)) Q''_pq.

For a circular orbit seen at the inclination iota (the angle between n and
the orbit's axis) the two polarisations have the amplitudes
h0 (1 + cos² iota) / 2 and h0 cos iota, at twice the orbital frequency, with

    h0 = (4 / D) (G Mc / c²)^(5/3) (pi f / c)^(2/3),

where Mc is the chirp mass and f the wave frequency. Here the second
derivative is taken numerically from the positions, so the closed forms of
``pbc.mechanics.chirp`` and ``strain_amplitude`` can be checked against it.

Units are SI; masses are in solar masses, as in ``pbc.mechanics.chirp``.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from pbc.mechanics.chirp import (
    GM_SUN,
    GM_SUN_OVER_C3,
    M_SUN,
    C,
    G,
    chirp_mass,
    shrink_rate,
)

MPC = 3.0856775814913673e22  # m, a megaparsec

Array = NDArray[np.float64]


def isco_separation(total_mass: float) -> float:
    """The separation 6 GM / c² of the innermost stable circular orbit, in
    metres, for a total mass in solar masses."""
    return 6.0 * total_mass * GM_SUN / C**2


def isco_frequency(total_mass: float) -> float:
    """The wave frequency c³ / (6^(3/2) pi G M) in hertz at the innermost
    stable circular orbit: twice the orbital frequency at ``isco_separation``."""
    return 1.0 / (6.0**1.5 * np.pi * total_mass * GM_SUN_OVER_C3)


def inspiral(
    m1: float, m2: float, f_start: float, t: ArrayLike | None = None
) -> tuple[Array, Array, Array]:
    """Integrate the separation and the orbital phase of a shrinking circular
    orbit from the wave frequency ``f_start`` to the innermost stable orbit.

    Returns ``(t, a, phi)`` in s, m, and rad, with ``phi`` zero at the start:
    at the times ``t`` if given (those after the innermost orbit are
    dropped), else at the end alone. The orbit shrinks by ``shrink_rate``
    and turns at sqrt(GM / a³); nothing here uses the closed form of the
    chirp."""
    gm = (m1 + m2) * GM_SUN
    a0 = (gm / (np.pi * f_start) ** 2) ** (1.0 / 3.0)
    a_end = isco_separation(m1 + m2)
    if a0 <= a_end:
        raise ValueError("f_start is at or above the innermost stable orbit")

    def rates(_t, y):
        return [shrink_rate(y[0], m1, m2), np.sqrt(gm / y[0] ** 3)]

    def end(_t, y):
        return y[0] - a_end

    end.terminal = True
    # The time to reach a = 0 bounds the integration from above.
    horizon = a0**4 / (4.0 * -shrink_rate(1.0, m1, m2))
    times = None if t is None else np.asarray(t, dtype=float)
    solution = solve_ivp(
        rates,
        (0.0, horizon),
        [a0, 0.0],
        method="DOP853",
        t_eval=None if times is None else times[times < horizon],
        events=end,
        rtol=1e-12,
        atol=[1e-9 * a_end, 1e-10],
    )
    if times is None:
        return (
            solution.t_events[0],
            solution.y_events[0][:, 0],
            solution.y_events[0][:, 1],
        )
    return solution.t, solution.y[0], solution.y[1]


def positions(
    a: ArrayLike, phi: ArrayLike, m1: float, m2: float
) -> tuple[Array, Array]:
    """The positions of the two bodies about their centre of mass, shape
    ``(n, 3)`` each, on a separation ``a`` at the orbital phase ``phi`` in the
    x-y plane."""
    a = np.asarray(a, dtype=float)
    phi = np.asarray(phi, dtype=float)
    relative = np.stack([a * np.cos(phi), a * np.sin(phi), np.zeros_like(a)], axis=-1)
    total = m1 + m2
    return (m2 / total) * relative, -(m1 / total) * relative


def quadrupole(x1: ArrayLike, x2: ArrayLike, m1: float, m2: float) -> Array:
    """The trace-free mass quadrupole Q_ij = sum m (x_i x_j - delta_ij |x|²/3)
    in kg m², shape ``(n, 3, 3)``, of two bodies at ``x1`` and ``x2``
    (masses in solar masses)."""
    q = np.zeros((*np.shape(x1)[:-1], 3, 3))
    for x, m in ((np.asarray(x1, dtype=float), m1), (np.asarray(x2, dtype=float), m2)):
        outer = x[..., :, None] * x[..., None, :]
        square = np.einsum("...ii->...", outer)
        q += m * M_SUN * (outer - square[..., None, None] * np.eye(3) / 3.0)
    return q


def second_derivative(y: ArrayLike, dt: float) -> Array:
    """The second derivative along the first axis of samples ``y`` spaced by
    ``dt``, by the fourth-order central difference
    (-y[k-2] + 16 y[k-1] - 30 y[k] + 16 y[k+1] - y[k+2]) / (12 dt²); the
    result has two samples fewer at each end."""
    y = np.asarray(y, dtype=float)
    return (-y[:-4] + 16.0 * y[1:-3] - 30.0 * y[2:-2] + 16.0 * y[3:-1] - y[4:]) / (
        12.0 * dt**2
    )


def polarisations(
    q_ddot: ArrayLike, distance: float, inclination: float
) -> tuple[Array, Array]:
    """The strains ``(h_plus, h_cross)`` at ``distance`` metres in the
    direction n = (0, sin i, cos i), at the inclination ``i`` from the
    orbit's axis z, from the second derivative of the quadrupole: the
    quadrupole formula with p = (1, 0, 0) and q = (0, cos i, -sin i)."""
    q_ddot = np.asarray(q_ddot, dtype=float)
    p = np.array([1.0, 0.0, 0.0])
    q = np.array([0.0, np.cos(inclination), -np.sin(inclination)])
    pp = np.einsum("i,...ij,j->...", p, q_ddot, p)
    qq = np.einsum("i,...ij,j->...", q, q_ddot, q)
    pq = np.einsum("i,...ij,j->...", p, q_ddot, q)
    scale = G / (C**4 * distance)
    return scale * (pp - qq), 2.0 * scale * pq


def wave_phase(h_plus: ArrayLike, h_cross: ArrayLike) -> Array:
    """The phase of a face-on wave from its two polarisations, unwrapped:
    arg(-(h_plus + i h_cross)).

    The convention follows from ``polarisations``. Seen face on, along +z,
    a rigid orbit of separation a at the orbital phase phi (increasing
    counterclockwise, as in ``positions``) has
    Q_xx - Q_yy + 2 i Q_xy = mu a² exp(2 i phi), whose second derivative is
    -4 omega² mu a² exp(2 i phi); so h_plus = -A cos 2 phi,
    h_cross = -A sin 2 phi, and this phase is exactly 2 phi. It grows at the
    wave's angular frequency 2 pi f, as ``pbc.mechanics.chirp.chirp_phase``
    does, so the two can be compared directly. For a shrinking orbit the
    derivatives of a and omega add (5/4) eps to it, eps = |da/dt| / (a omega):
    the computed wave is ahead of twice the orbital phase."""
    return np.unwrap(np.angle(-(np.asarray(h_plus) + 1j * np.asarray(h_cross))))


def strain_amplitude(f: ArrayLike, mc: float, distance: float) -> Array:
    """The closed-form amplitude h0 = (4 / D) (G Mc / c²)^(5/3) (pi f / c)^(2/3)
    of a face-on circular binary of chirp mass ``mc`` (solar masses) at
    ``distance`` metres and wave frequency ``f``."""
    f = np.asarray(f, dtype=float)
    return (
        4.0
        / distance
        * (mc * GM_SUN / C**2) ** (5.0 / 3.0)
        * (np.pi * f / C) ** (2.0 / 3.0)
    )


def cycles_in_band(f_low: float, f_high: float, mc: float) -> float:
    """The closed-form number of wave cycles between the frequencies
    ``f_low`` and ``f_high``, the integral of f dt = f df / (df/dt):
    (G Mc / c³)^(-5/3) (f_low^(-5/3) - f_high^(-5/3)) / (32 pi^(8/3))."""
    return (
        (mc * GM_SUN_OVER_C3) ** (-5.0 / 3.0)
        * (f_low ** (-5.0 / 3.0) - f_high ** (-5.0 / 3.0))
        / (32.0 * np.pi ** (8.0 / 3.0))
    )


def mass_for_chirp_mass(m1: float, mc: float) -> float:
    """The second mass, in solar masses, that gives the chirp mass ``mc``
    with ``m1``: the root of (m1 m2)^(3/5) / (m1 + m2)^(1/5) = mc, which
    grows with m2 and has one root when ``mc`` is below ``m1``'s reach."""
    return brentq(lambda m2: chirp_mass(m1, m2) - mc, 1e-6 * mc, 1e6 * mc, xtol=1e-14)
