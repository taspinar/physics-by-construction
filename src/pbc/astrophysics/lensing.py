"""The deflection of light by a mass, and the point lens.

**Deflection.** In units with G = c = 1 a mass has the length m = GM/c².
General relativity bends a ray that passes a spherical mass with impact
parameter b along the orbit of a photon in the Schwarzschild geometry,
whose equation in u = 1/r is

    d²u/dphi² + u = 3 m u².

The ray comes in from u = 0, turns at its closest approach r0, with
1/b² = u0² (1 - 2 m u0), and leaves symmetrically, so the total angle it
sweeps exceeds pi by the deflection

    alpha = 2 * integral from 0 to u0 of du / sqrt(1/b² - u² (1 - 2 m u)) - pi.

Far from the mass the weak-field formula alpha = 4m/b holds, with the
next term (15 pi / 4)(m/b)². A Newtonian particle at the speed of light
on a hyperbola is turned by 2 arctan(m/b), half as much at large b.

**The point lens.** A mass M at distance D_l bends the light of a source at
D_s by alpha, so that a source at the angle beta from the line of sight
appears at the angles theta solving the lens equation, in units of the
Einstein radius

    theta_E = sqrt(4 GM D_ls / (c² D_l D_s)),   D_ls = D_s - D_l,
    y = x - x / |x|²,   y = beta / theta_E,  x = theta / theta_E

(distances along a flat, static line of sight). A source at the offset u
has two images at x = (u +- sqrt(u² + 4)) / 2, and the total magnification
of a point source is A(u) = (u² + 2) / (u sqrt(u² + 4)). A uniform source
of finite size is magnified by the average of A over its disk, because the
lens keeps the surface brightness: inverse ray shooting counts the rays from
a grid of the image plane that land on the source, which measures the same
area ratio without the formula. When the lens moves across the line of sight
with speed v, u changes on the Einstein time t_E = D_l theta_E / v.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import brentq
from scipy.special import roots_legendre


def weak_field_deflection(b: ArrayLike, m: float = 1.0) -> NDArray:
    """The weak-field deflection 4m/b, in radians."""
    return 4 * m / np.asarray(b, dtype=np.float64)


def newtonian_deflection(b: ArrayLike, m: float = 1.0) -> NDArray:
    """The turn 2 arctan(m/b) of a Newtonian particle that passes the mass
    at the speed of light with impact parameter b."""
    return 2 * np.arctan(m / np.asarray(b, dtype=np.float64))


def closest_approach(b: float, m: float = 1.0) -> float:
    """The closest distance r0 of a ray of impact parameter ``b``, from
    b² = r0³ / (r0 - 2m), the root beyond the photon sphere r = 3m. A ray
    with b at or below sqrt(27) m is captured and has none."""
    if b <= np.sqrt(27) * m:
        raise ValueError(f"a ray with b = {b} <= sqrt(27) m is captured")
    return brentq(
        lambda r: r**3 - b * b * (r - 2 * m), 3 * m, b + 3 * m, xtol=1e-15 * b
    )


def deflection(b: float, m: float = 1.0, nodes: int = 64) -> float:
    """The deflection of a ray of impact parameter ``b`` by the mass of
    length ``m``, from the integral of the photon orbit by Gauss-Legendre
    quadrature with ``nodes`` points.

    With u = u0 w the integral is 2 * integral from 0 to 1 of
    dw / sqrt((1 - w²) - 2 m u0 (1 - w³)); the factor (1 - w) under the root
    makes it singular at the turning point w = 1, and w = 1 - s² removes the
    singularity: 4 * integral from 0 to 1 of
    ds / sqrt((1 + w) - 2 m u0 (1 + w + w²)), a smooth integrand."""
    u0 = 1 / closest_approach(b, m)
    s, weights = roots_legendre(nodes)
    s = 0.5 * (s + 1)  # from [-1, 1] to [0, 1]
    w = 1 - s**2
    integrand = 4 / np.sqrt((1 + w) - 2 * m * u0 * (1 + w + w**2))
    return float(0.5 * np.sum(weights * integrand) - np.pi)


def lens_map(x: ArrayLike) -> NDArray:
    """The source position y = x - x / |x|² of the image positions ``x``
    (the last axis holds the two components), in Einstein radii."""
    x = np.asarray(x, dtype=np.float64)
    return x - x / np.sum(x**2, axis=-1, keepdims=True)


def image_positions(u: ArrayLike) -> tuple[NDArray, NDArray]:
    """The two images of a point source at the offset ``u`` along the line
    through the lens: x = (u + sqrt(u² + 4)) / 2 outside the Einstein ring,
    on the source's side, and (u - sqrt(u² + 4)) / 2 inside it, opposite."""
    u = np.asarray(u, dtype=np.float64)
    root = np.sqrt(u**2 + 4)
    return (u + root) / 2, (u - root) / 2


def magnification(u: ArrayLike) -> NDArray:
    """The total magnification (u² + 2) / (u sqrt(u² + 4)) of a point
    source at the offset ``u``."""
    u = np.asarray(u, dtype=np.float64)
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))


def disk_magnification(u: float, radius: float, nodes: int = 64) -> float:
    """The magnification of a uniform disk of ``radius`` centred at the
    offset ``u`` (both in Einstein radii, with u > radius): the average of
    the point-source magnification over the disk, by Gauss-Legendre
    quadrature in the radius and the angle of the disk."""
    if u <= radius:
        raise ValueError("the disk must not cover the lens")
    s, ws = roots_legendre(nodes)
    rho = 0.5 * radius * (s + 1)  # [0, radius]
    wr = 0.5 * radius * ws
    phi = np.pi * (s + 1)  # [0, 2 pi]
    wp = np.pi * ws
    R, P = np.meshgrid(rho, phi, indexing="ij")
    offset = np.hypot(u + R * np.cos(P), R * np.sin(P))
    total = np.sum(wr[:, None] * wp[None, :] * R * magnification(offset))
    return float(total / (np.pi * radius**2))


def ray_shoot(
    u: float, radius: float, half: float, n: int, chunk: int = 500
) -> tuple[float, NDArray]:
    """Inverse ray shooting: the image plane [-half, half]² on a grid of
    n by n cell centres, each ray mapped to the source plane by the lens
    equation; the magnification of a uniform disk of ``radius`` at
    (u, 0) as the area of the cells whose rays land on the disk over the
    area of the disk, and the boolean image of those cells (rows along y)."""
    edges = np.linspace(-half, half, n + 1)
    centres = 0.5 * (edges[1:] + edges[:-1])
    hit = np.zeros((n, n), dtype=bool)
    for start in range(0, n, chunk):
        y = centres[start : start + chunk]
        X, Y = np.meshgrid(centres, y)
        source = lens_map(np.stack([X, Y], axis=-1))
        hit[start : start + chunk] = (source[..., 0] - u) ** 2 + source[
            ..., 1
        ] ** 2 < radius**2
    cell = (edges[1] - edges[0]) ** 2
    return float(hit.sum() * cell / (np.pi * radius**2)), hit


def einstein_radius(gm: float, lens: float, source: float, c: float) -> float:
    """The Einstein radius sqrt(4 GM (D_s - D_l) / (c² D_l D_s)), in
    radians, of a lens of mass parameter ``gm`` at the distance ``lens``,
    for a source at the distance ``source``."""
    if not 0 < lens < source:
        raise ValueError("the lens must lie between the observer and the source")
    return float(np.sqrt(4 * gm * (source - lens) / (c**2 * lens * source)))


def light_curve(t: ArrayLike, t0: float, einstein_time: float, u0: float) -> NDArray:
    """The magnification of a point source at the times ``t`` as the lens
    passes with the smallest offset ``u0`` at ``t0`` and the Einstein time
    ``einstein_time``: A(sqrt(u0² + ((t - t0) / t_E)²))."""
    tau = (np.asarray(t, dtype=np.float64) - t0) / einstein_time
    return magnification(np.sqrt(u0**2 + tau**2))
