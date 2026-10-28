"""Linear waves on water of finite depth: the dispersion relation and what
follows from it.

A small wave of angular frequency omega on still water of depth h has the
wavenumber k that solves the linear dispersion relation

    omega^2 = g k tanh(k h).

For a long wave (k h small) tanh(k h) is k h, the relation becomes
omega = sqrt(g h) k, and the wave obeys the wave equation of the lesson
"The wave equation" with the speed sqrt(g h): every frequency travels at the
same speed. For a shorter wave the phase speed omega / k depends on the
frequency, so the water is dispersive, and energy travels at the group
speed d omega / d k, slower than the crests.

Over a bed whose depth changes slowly on the scale of a wavelength, the wave
keeps its frequency and takes the local wavenumber k(h(x)), so the phase it
accumulates is the integral of k along the bed (the slowly varying, or WKB,
approximation; it neglects reflection by the bed and every nonlinear effect).

Quantities are in SI units: lengths in m, times in s, angular frequencies in
rad/s, wavenumbers in rad/m.
"""

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray

Array = NDArray[np.float64]

G = 9.81  # m/s^2; the solvers of the flume used 9.81 (D-SPH) and 9.82 (i-VoF)
NEWTON_TOLERANCE = 1e-14  # relative change of k at which Newton's method stops


def wavenumber(omega: ArrayLike, depth: ArrayLike, g: float = G) -> Array:
    """The k > 0 with omega^2 = g k tanh(k h), by Newton's method.

    The start is the explicit approximation of Fenton and McKee (1990),
    k h = (omega^2 h / g) coth((omega sqrt(h / g))^(3/2))^(2/3), within about
    two percent of the root at every depth, so a few steps reach round-off.
    """
    omega = np.asarray(omega, dtype=float)
    depth = np.asarray(depth, dtype=float)
    if np.any(omega <= 0) or np.any(depth <= 0):
        raise ValueError("the frequency and the depth must be positive")
    deep = omega**2 / g
    k = deep / np.tanh((omega * np.sqrt(depth / g)) ** 1.5) ** (2 / 3)
    for _ in range(100):
        t = np.tanh(k * depth)
        f = g * k * t - omega**2
        slope = g * t + g * k * depth * (1 - t**2)
        step = f / slope
        k = k - step
        if np.all(np.abs(step) <= NEWTON_TOLERANCE * k):
            return k
    raise RuntimeError("Newton's method did not converge")


def shallow_wavenumber(omega: ArrayLike, depth: ArrayLike, g: float = G) -> Array:
    """The wavenumber of the long-wave limit, omega / sqrt(g h): the wave
    equation with the speed sqrt(g h), which has no dispersion."""
    return np.asarray(omega, dtype=float) / np.sqrt(g * np.asarray(depth, dtype=float))


def phase_speed(omega: ArrayLike, depth: ArrayLike, g: float = G) -> Array:
    """omega / k, the speed of a crest (m/s)."""
    return np.asarray(omega, dtype=float) / wavenumber(omega, depth, g)


def group_speed(omega: ArrayLike, depth: ArrayLike, g: float = G) -> Array:
    """d omega / d k = (omega / 2k) (1 + 2 k h / sinh(2 k h)), the speed of
    the energy and of the front of a wave train (m/s)."""
    omega = np.asarray(omega, dtype=float)
    depth = np.asarray(depth, dtype=float)
    k = wavenumber(omega, depth, g)
    kh2 = 2 * k * depth
    return 0.5 * omega / k * (1 + kh2 / np.sinh(kh2))


def _along(
    x: ArrayLike, depth_at: Callable[[Array], Array], rate: Callable[[Array], Array],
    *, start: float, samples: int,
) -> Array:  # fmt: skip
    """The integral of rate(depth_at(s)) ds from ``start`` to each ``x``
    (trapezoidal rule on ``samples`` points up to the largest x)."""
    x = np.asarray(x, dtype=float)
    s = np.linspace(start, max(float(x.max()), start), samples)
    values = rate(depth_at(s))
    cumulative = np.concatenate(
        [[0.0], np.cumsum(0.5 * (values[1:] + values[:-1]) * np.diff(s))]
    )
    return np.interp(x, s, cumulative)


def accumulated_phase(
    x: ArrayLike, depth_at: Callable[[Array], Array], omega: float, *,
    start: float, dispersive: bool = True, g: float = G, samples: int = 20001,
) -> Array:  # fmt: skip
    """The phase (rad) that a wave of ``omega`` accumulates from ``start`` to
    each ``x`` over the bed ``depth_at``: the integral of the local
    wavenumber, of the dispersion relation or, with ``dispersive=False``, of
    the long-wave limit."""
    local = wavenumber if dispersive else shallow_wavenumber
    return _along(
        x, depth_at, lambda h: local(omega, h, g), start=start, samples=samples
    )


def group_travel_time(
    x: ArrayLike, depth_at: Callable[[Array], Array], omega: float, *,
    start: float, g: float = G, samples: int = 20001,
) -> Array:  # fmt: skip
    """The time (s) the energy of a wave of ``omega`` takes from ``start`` to
    each ``x``: the integral of one over the local group speed."""
    return _along(
        x, depth_at, lambda h: 1 / group_speed(omega, h, g), start=start,
        samples=samples,
    )  # fmt: skip


def propagate(
    time: ArrayLike, elevation: ArrayLike, distance: float, depth: float, *,
    dispersive: bool = True, g: float = G,
) -> Array:  # fmt: skip
    """The record ``elevation`` at a point, carried ``distance`` further along
    a flat bed of ``depth`` by linear theory.

    Each Fourier component exp(i omega t) of the record is multiplied by
    exp(-i k(omega) distance), with k of the dispersion relation or, with
    ``dispersive=False``, of the long-wave limit, which delays the whole
    record by distance / sqrt(g h). The discrete transform treats the record
    as periodic, so it has to hold a whole number of periods of a steady
    wave; the mean is kept as it is. Samples are equally spaced.
    """
    time = np.asarray(time, dtype=float)
    elevation = np.asarray(elevation, dtype=float)
    dt = float(np.mean(np.diff(time)))
    spectrum = np.fft.rfft(elevation)
    omega = 2 * np.pi * np.fft.rfftfreq(elevation.size, dt)
    k = np.zeros_like(omega)
    local = wavenumber if dispersive else shallow_wavenumber
    k[1:] = local(omega[1:], depth, g)
    return np.fft.irfft(spectrum * np.exp(-1j * k * distance), n=elevation.size)
