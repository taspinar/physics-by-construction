"""A planet crossing its star: the orbit, the contacts, and the light curve.

**Geometry.** Lengths are in units of the star's radius R. The planet, a
dark disk of radius p, moves on a circular orbit of radius a about the star,
inclined so that its closest projected distance from the star's centre is
the impact parameter b = a cos i. The observer looks along +z; the sky is
the x-y plane, and the planet is in front of the star when z > 0. The
transit begins and ends when the projected separation d equals 1 + p (first
and fourth contacts) and is full between d = 1 - p (second and third). For a
circular orbit of period P the durations follow from the angle the planet
turns between the contacts:

    T14 = (P / pi) arcsin( sqrt((1 + p)² - b²) / (a sin i) ),
    T23 = (P / pi) arcsin( sqrt((1 - p)² - b²) / (a sin i) ),

with no full phase when b > 1 - p (a grazing transit).

**Flux.** The star's brightness per unit area is I(r) at the distance r from
its centre: uniform, or darker towards the limb by the quadratic law
I = 1 - u1 (1 - mu) - u2 (1 - mu)², mu = sqrt(1 - r²). The light lost is the
integral of I over the part of the planet's disk that lies on the star,
divided by the integral over the star. For a uniform star it is the area of
overlap of two disks over pi, so a full transit has the depth p²; here it is
also computed by counting the cells of a grid over the planet's disk, which
takes any I.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp

Array = NDArray[np.float64]
Intensity = Callable[[Array], Array]


def _positive(**values: float) -> None:
    """Raise ValueError unless each named value is finite and positive."""
    for name, value in values.items():
        if not (np.isfinite(value) and value > 0):
            raise ValueError(f"{name} must be finite and positive")


def uniform(r: ArrayLike) -> Array:
    """A star of the same brightness everywhere on its disk."""
    return np.ones_like(np.asarray(r, dtype=float))


def quadratic_limb(u1: float, u2: float) -> Intensity:
    """The quadratic limb-darkening law 1 - u1 (1 - mu) - u2 (1 - mu)²,
    mu = sqrt(1 - r²), the cosine of the angle at which the surface is seen."""

    def intensity(r: ArrayLike) -> Array:
        mu = np.sqrt(np.clip(1.0 - np.asarray(r, dtype=float) ** 2, 0.0, None))
        return 1.0 - u1 * (1.0 - mu) - u2 * (1.0 - mu) ** 2

    return intensity


def total_flux(u1: float = 0.0, u2: float = 0.0) -> float:
    """The integral of the quadratic law over the star's disk,
    pi (1 - u1 / 3 - u2 / 6); pi for a uniform star."""
    return np.pi * (1.0 - u1 / 3.0 - u2 / 6.0)


def overlap_area(d: ArrayLike, p: float) -> Array:
    """The area of overlap of the unit disk and a disk of radius ``p`` whose
    centre is at the distance ``d``: the closed form of two circular
    segments, pi p² inside, zero outside."""
    _positive(p=p)
    d = np.atleast_1d(np.asarray(d, dtype=float))
    area = np.zeros_like(d)
    inside = d <= 1.0 - p
    area[inside] = np.pi * p**2
    part = (d > 1.0 - p) & (d < 1.0 + p)
    x = d[part]
    k0 = np.arccos(np.clip((x**2 + p**2 - 1.0) / (2.0 * x * p), -1.0, 1.0))
    k1 = np.arccos(np.clip((x**2 + 1.0 - p**2) / (2.0 * x), -1.0, 1.0))
    root = np.sqrt(np.clip(4.0 * x**2 - (1.0 + x**2 - p**2) ** 2, 0.0, None))
    area[part] = p**2 * k0 + k1 - 0.5 * root
    return area


def uniform_flux(d: ArrayLike, p: float) -> Array:
    """The closed-form flux of a uniform star, relative to its full flux,
    with the planet at the projected separation ``d``."""
    return 1.0 - overlap_area(d, p) / np.pi


def grid_flux(
    d: ArrayLike,
    p: float,
    intensity: Intensity = uniform,
    cells: int = 400,
    full: float | None = None,
) -> Array:
    """The flux relative to the full flux with the planet at the projected
    separation ``d``, by counting a grid of ``cells`` by ``cells`` over the
    square around the planet's disk: each cell whose centre is on both disks
    hides its area times the brightness there. ``full`` is the integral of
    ``intensity`` over the star (pi for a uniform star)."""
    full = np.pi if full is None else full
    _positive(p=p, full=full)
    if int(cells) != cells or cells < 1:
        raise ValueError("cells must be a positive whole number")
    side = 2.0 * p / cells
    offsets = -p + side * (np.arange(cells) + 0.5)
    gx, gy = np.meshgrid(offsets, offsets)
    on_planet = gx**2 + gy**2 <= p**2
    gx, gy = gx[on_planet], gy[on_planet]
    hidden = []
    for x in np.atleast_1d(np.asarray(d, dtype=float)):
        r = np.hypot(x + gx, gy)
        on_star = r <= 1.0
        hidden.append(np.sum(intensity(r[on_star])) * side**2)
    return 1.0 - np.array(hidden) / full


def central_depth(p: float, u1: float = 0.0, u2: float = 0.0) -> float:
    """The closed-form depth of a planet at the centre of a star with the
    quadratic law: 2 pi * integral from 0 to p of I(r) r dr, over the total
    flux. With mu = sqrt(1 - r²), r dr = -mu dmu and the integral runs over
    mu from sqrt(1 - p²) to 1, where each power of (1 - mu) times mu
    integrates in closed form. The planet is no larger than the star."""
    if not 0.0 < p <= 1.0:
        raise ValueError("p must lie in (0, 1]")
    m = np.sqrt(1.0 - p**2)

    def between(f):  # f(1) - f(m)
        return f(1.0) - f(m)

    plain = between(lambda x: x**2 / 2)
    linear = between(lambda x: x**2 / 2 - x**3 / 3)
    square = between(lambda x: x**2 / 2 - 2 * x**3 / 3 + x**4 / 4)
    return 2.0 * np.pi * (plain - u1 * linear - u2 * square) / total_flux(u1, u2)


def durations(
    period: float, a: float, inclination: float, p: float
) -> tuple[float, float]:
    """The analytic total and full durations ``(T14, T23)`` of a circular
    orbit, in the unit of ``period``; ``T23`` is nan for a grazing transit
    and both are nan when there is no transit. ``a`` is in stellar radii and
    larger than 1 + p, the inclination between 0 and pi, and the planet no
    larger than the star, 0 < p <= 1."""
    _positive(period=period, p=p)
    if p > 1.0:
        raise ValueError("the planet must be no larger than the star, p <= 1")
    if not a > 1.0 + p:
        raise ValueError("the orbit must lie outside the star and the planet")
    if not 0.0 < inclination < np.pi:
        raise ValueError("the inclination must lie between 0 and pi")
    b = a * np.cos(inclination)
    out = []
    for edge in (1.0 + p, 1.0 - p):
        chord = edge**2 - b**2
        out.append(
            period / np.pi * np.arcsin(np.sqrt(chord) / (a * np.sin(inclination)))
            if chord > 0
            else np.nan
        )
    return out[0], out[1]


def orbit_start(
    gm: float, a: float, inclination: float, before: float
) -> tuple[Array, Array]:
    """Position and velocity of a circular orbit of radius ``a`` and
    parameter ``gm`` at the angle ``before`` (radians) ahead of mid-transit,
    the orbit inclined by ``inclination`` from the sky so that mid-transit is
    at x = 0, y = -a cos i, z = a sin i."""
    speed = np.sqrt(gm / a)
    theta = -before
    ci, si = np.cos(inclination), np.sin(inclination)
    position = a * np.array([np.sin(theta), -np.cos(theta) * ci, np.cos(theta) * si])
    velocity = speed * np.array(
        [np.cos(theta), np.sin(theta) * ci, -np.sin(theta) * si]
    )
    return position, velocity


def transit_orbit(
    gm: float,
    a: float,
    inclination: float,
    p: float,
    t: ArrayLike,
    before: float,
    radius: float = 1.0,
) -> tuple[Array, Array, dict[str, Array]]:
    """Integrate the planet's orbit about the star (DOP853) from ``before``
    radians ahead of mid-transit, and locate the contacts.

    ``a`` and ``radius`` (the star's) share one length unit, consistent with
    ``gm`` and the times ``t``. Returns the times, the projected separation
    in stellar radii at them, and the contact times: ``"outer"`` where the
    separation crosses 1 + p and ``"inner"`` where it crosses 1 - p, with
    the planet in front of the star. The step is kept below the spacing of
    ``t``, so that no pair of crossings falls within one step unseen. The
    times must be finite and strictly increasing, at least two of them.

    The inputs must describe a transit: the planet no larger than the star
    (p <= 1), the orbit clear of the star and the planet (``a`` larger than
    (1 + p) ``radius``), the impact parameter ``a cos i / radius`` so
    small in size that the planet's disk crosses the star's (below 1 + p),
    and the inclination between 0 and pi, so that mid-transit falls in front
    of the star (z = a sin i > 0) and not behind it."""
    _positive(gm=gm, a=a, p=p, radius=radius)
    if p > 1.0:
        raise ValueError("the planet must be no larger than the star, p <= 1")
    if not a > (1.0 + p) * radius:
        raise ValueError("the orbit must lie outside the star and the planet")
    if not abs(a * np.cos(inclination)) / radius < 1.0 + p:
        raise ValueError(
            "the impact parameter must put the planet on the star's disk, |b| < 1 + p"
        )
    if not 0.0 < inclination < np.pi:
        raise ValueError("the inclination must lie between 0 and pi")
    t = np.asarray(t, dtype=float)
    if t.ndim != 1 or t.size < 2 or not np.all(np.isfinite(t)):
        raise ValueError("t must hold at least two finite times")
    if np.any(np.diff(t) <= 0):
        raise ValueError("t must be strictly increasing")
    position, velocity = orbit_start(gm, a, inclination, before)

    def rates(_t, y):
        r = y[:3]
        return np.concatenate([y[3:], -gm * r / np.linalg.norm(r) ** 3])

    def crossing(edge):
        def event(_t, y):
            if y[2] <= 0:  # behind the star
                return 1.0
            return np.hypot(y[0], y[1]) / radius - edge

        return event

    solution = solve_ivp(
        rates,
        (t[0], t[-1]),
        np.concatenate([position, velocity]),
        method="DOP853",
        t_eval=t,
        events=[crossing(1.0 + p), crossing(1.0 - p)],
        rtol=1e-12,
        atol=1e-12 * a,
        max_step=float(np.min(np.diff(t))),
    )
    if not solution.success:
        raise RuntimeError(f"the orbit integration failed: {solution.message}")
    separation = np.hypot(solution.y[0], solution.y[1]) / radius
    return (
        solution.t,
        separation,
        {"outer": solution.t_events[0], "inner": solution.t_events[1]},
    )
