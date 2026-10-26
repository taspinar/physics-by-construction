"""Light across a flat interface: Snell's law, Fermat's principle, the
Fresnel amplitudes, and a pulse across a step of the refractive index.

Medium 1 (refractive index n1) lies above the interface y = 0, medium 2
(n2) below it. Angles are measured from the normal, in radians.

Nothing here derives a result from the formula it is compared with: the
path of least time is found by searching the travel time, the Fresnel
amplitudes by solving the two boundary conditions as a linear system, and
the pulse by a finite-difference scheme. The closed forms are in this
module to be compared with.

Lengths are in m, speeds in units of the speed of light in vacuum where a
grid is used.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]

GOLDEN = (np.sqrt(5.0) - 1.0) / 2.0


def snell_angle(theta: ArrayLike, n1: float, n2: float) -> Array:
    """The angle of the refracted ray from n1 sin(theta1) = n2 sin(theta2).

    Raises ``ValueError`` for an angle beyond the critical angle, where no
    ray is refracted (total internal reflection)."""
    s = n1 * np.sin(np.asarray(theta, dtype=float)) / n2
    if np.any(np.abs(s) > 1.0):
        raise ValueError("beyond the critical angle no ray is refracted")
    return np.arcsin(s)


def critical_angle(n1: float, n2: float) -> float:
    """The angle of incidence beyond which light going from n1 into n2 is
    totally reflected, arcsin(n2 / n1); only for n1 > n2."""
    if n1 <= n2:
        raise ValueError("a critical angle exists only from the denser medium")
    return float(np.arcsin(n2 / n1))


def brewster_angle(n1: float, n2: float) -> float:
    """The angle of incidence arctan(n2 / n1) at which r_p vanishes."""
    return float(np.arctan2(n2, n1))


def golden_minimum(
    f: Callable[[float], float], low: float, high: float, *, steps: int = 200
) -> float:
    """The point of the smallest value of ``f`` in [low, high], by
    golden-section search. ``f`` must fall and then rise on the interval;
    only values of ``f`` are used, no derivative. Each step keeps
    0.618... of the bracket; after ``steps`` steps it is at round-off."""
    a, b = low, high
    c = b - GOLDEN * (b - a)
    d = a + GOLDEN * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(steps):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - GOLDEN * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + GOLDEN * (b - a)
            fd = f(d)
        if b - a <= 4 * np.finfo(float).eps * max(abs(a), abs(b), 1.0):
            break
    return 0.5 * (a + b)


def travel_time(
    x: float, *, height: float, depth: float, distance: float, n1: float, n2: float
) -> float:
    """The time, in units of 1 / c (m), that light takes from the source at
    (0, ``height``) in medium 1 to the interface at (x, 0) and on to the
    target at (``distance``, -``depth``) in medium 2, along straight lines:
    the optical path n1 r1 + n2 r2."""
    return n1 * np.hypot(x, height) + n2 * np.hypot(distance - x, depth)


def least_time_path(
    *, height: float, depth: float, distance: float, n1: float, n2: float
) -> tuple[float, float, float]:
    """The point x (m) where the path of least time crosses the interface,
    found by searching ``travel_time`` (Fermat's principle), and the angles
    of incidence and of refraction (rad) of that path."""
    x = golden_minimum(
        lambda x: travel_time(
            x, height=height, depth=depth, distance=distance, n1=n1, n2=n2
        ),
        0.0,
        distance,
    )
    return x, float(np.arctan2(x, height)), float(np.arctan2(distance - x, depth))


def _cos_refracted(theta: ArrayLike, n1: float, n2: float) -> NDArray[np.complex128]:
    """cos(theta2) from Snell's law, complex beyond the critical angle: the
    positive imaginary root, the wave that decays away from the interface."""
    s = n1 * np.sin(np.asarray(theta, dtype=float)) / n2
    return np.sqrt(np.asarray(1.0 - s**2, dtype=complex))


def fresnel_solved(theta: ArrayLike, n1: float, n2: float) -> dict[str, Array]:
    """The amplitudes r_s, t_s, r_p, t_p of the reflected and transmitted
    electric field for an incident field of unit amplitude, found by solving
    the boundary conditions at each angle as a 2 x 2 linear system.

    s (field normal to the plane of incidence): the tangential E,
    1 + r = t, and the tangential H, n1 cos1 (1 - r) = n2 cos2 t.
    p (field in the plane): the tangential H, n1 (1 + r) = n2 t, and the
    tangential E, cos1 (1 - r) = cos2 t. With this sign convention r_s and
    r_p have opposite signs at normal incidence. Beyond the critical angle
    cos2 is imaginary and |r| = 1. The amplitudes are complex."""
    theta = np.atleast_1d(np.asarray(theta, dtype=float))
    c1 = np.cos(theta).astype(complex)
    c2 = _cos_refracted(theta, n1, n2)
    out = {
        name: np.empty(theta.shape, dtype=complex) for name in ("rs", "ts", "rp", "tp")
    }
    for i in range(theta.size):
        s_matrix = np.array([[1.0, -1.0], [-n1 * c1[i], -n2 * c2[i]]])
        s_right = np.array([-1.0, -n1 * c1[i]])
        out["rs"][i], out["ts"][i] = np.linalg.solve(s_matrix, s_right)
        p_matrix = np.array([[n1, -n2], [-c1[i], -c2[i]]], dtype=complex)
        p_right = np.array([-n1, -c1[i]], dtype=complex)
        out["rp"][i], out["tp"][i] = np.linalg.solve(p_matrix, p_right)
    return out


def fresnel_closed(theta: ArrayLike, n1: float, n2: float) -> dict[str, Array]:
    """The closed Fresnel forms in the convention of ``fresnel_solved``:
    r_s = (n1 cos1 - n2 cos2) / (n1 cos1 + n2 cos2), t_s = 2 n1 cos1 / (same),
    r_p = (n2 cos1 - n1 cos2) / (n2 cos1 + n1 cos2), t_p = 2 n1 cos1 / (same)."""
    theta = np.atleast_1d(np.asarray(theta, dtype=float))
    c1 = np.cos(theta)
    c2 = _cos_refracted(theta, n1, n2)
    s = n1 * c1 + n2 * c2
    p = n2 * c1 + n1 * c2
    return {
        "rs": (n1 * c1 - n2 * c2) / s,
        "ts": 2 * n1 * c1 / s,
        "rp": (n2 * c1 - n1 * c2) / p,
        "tp": 2 * n1 * c1 / p,
    }


def reflectance(r: ArrayLike) -> Array:
    """The fraction of the incident power that is reflected, |r|^2."""
    return np.abs(np.asarray(r)) ** 2


def transmittance(t: ArrayLike, theta: ArrayLike, n1: float, n2: float) -> Array:
    """The fraction of the incident power that crosses the interface,
    Re(n2 cos2) |t|^2 / (n1 cos1): the intensity scales with n |E|^2 and the
    beam's cross-section with the cosine of its angle. Zero beyond the
    critical angle, where cos2 is imaginary."""
    theta = np.asarray(theta, dtype=float)
    c2 = _cos_refracted(theta, n1, n2)
    return np.real(n2 * c2) * np.abs(np.asarray(t)) ** 2 / (n1 * np.cos(theta))


def bisect_root(f: Callable[[float], float], low: float, high: float) -> float:
    """A root of ``f`` between ``low`` and ``high``, where ``f`` changes
    sign, by bisection to round-off."""
    f_low = f(low)
    if f_low * f(high) > 0.0:
        raise ValueError("f must change sign between low and high")
    for _ in range(200):
        middle = 0.5 * (low + high)
        if middle in (low, high):
            break
        if f(middle) * f_low > 0.0:
            low, f_low = middle, f(middle)
        else:
            high = middle
    return 0.5 * (low + high)


def node_speeds(x: ArrayLike, *, interface: float, c1: float, c2: float) -> Array:
    """The wave speed at each node of a grid with a step from ``c1`` to
    ``c2`` at the node nearest ``interface``. That node carries half a cell
    of each medium, so its 1 / c^2 is the mean of the two: the condition
    that the field and its slope are continuous there."""
    x = np.asarray(x, dtype=float)
    on = int(np.argmin(np.abs(x - interface)))
    speeds = np.where(np.arange(x.size) < on, c1, c2).astype(float)
    speeds[on] = np.sqrt(2.0 / (c1**-2 + c2**-2))
    return speeds


def solve_varying(
    u0: ArrayLike,
    v0: ArrayLike,
    *,
    speeds: ArrayLike,
    dx: float,
    dt: float,
    n_steps: int,
) -> Array:
    """The field after ``n_steps`` steps of u_tt = c(x)^2 u_xx, from the
    shape ``u0`` and the velocity ``v0``, with the speed of each node in
    ``speeds`` and both ends fixed.

    The scheme of ``pbc.waves.wave.solve`` with a Courant number per node:
    u^(n+1) = 2 u^n - u^(n-1) + (c_i dt / dx)^2 (second difference), first
    step by the Taylor expansion. For one speed it is the same scheme. The
    electric field of light in a medium without magnetisation obeys this
    equation with c(x) = c0 / n(x)."""
    u = np.array(u0, dtype=float)
    v = np.asarray(v0, dtype=float)
    c2 = (np.asarray(speeds, dtype=float) * dt / dx) ** 2
    if np.max(c2) > 1.0:
        raise ValueError("the Courant number exceeds one at some node")

    def second(w: Array) -> Array:
        out = np.zeros_like(w)
        out[1:-1] = w[2:] - 2.0 * w[1:-1] + w[:-2]
        return out

    u[0] = u[-1] = 0.0
    current = u + dt * v + 0.5 * c2 * second(u)
    current[0] = current[-1] = 0.0
    previous = u
    for _ in range(n_steps - 1):
        previous, current = current, 2.0 * current - previous + c2 * second(current)
    return current


def interface_exact(
    x: ArrayLike,
    t: float,
    profile: Callable[[Array], Array],
    *,
    interface: float,
    c1: float,
    c2: float,
) -> Array:
    """The exact field at the time ``t`` of a pulse ``profile(x - c1 t)``
    that starts in medium 1 and moves towards the interface: the incident
    and the reflected pulse r profile(2 x_i - x - c1 t) on the left, the
    transmitted pulse t profile(x_i + (c1 / c2)(x - x_i) - c1 t),
    compressed by c2 / c1, on the right. With n proportional to 1 / c,
    r = (n1 - n2) / (n1 + n2) and t = 2 n1 / (n1 + n2)."""
    x = np.asarray(x, dtype=float)
    r = (c2 - c1) / (c1 + c2)
    tr = 2.0 * c2 / (c1 + c2)
    left = profile(x - c1 * t) + r * profile(2 * interface - x - c1 * t)
    right = tr * profile(interface + (c1 / c2) * (x - interface) - c1 * t)
    return np.where(x < interface, left, right)
