"""The heat equation with a periodic surface temperature: the damped wave.

A homogeneous half-space z >= 0 of thermal diffusivity alpha (m^2/s) obeys
the heat equation of the lesson "Heat conduction and diffusion",

    dT/dt = alpha d2T/dz2.

When its surface z = 0 follows T_mean + A0 cos(omega t - phi0) for long
enough, every depth follows the same period, and the periodic solution that
stays bounded as z grows is the damped wave

    T(z, t) = T_mean + A0 exp(-z / d) cos(omega t - z / d - phi0),
    d = sqrt(2 alpha / omega),

the damping depth. Substituting a complex amplitude exp(i omega t) f(z)
gives f'' = (i omega / alpha) f, whose decaying root is
f = exp(-(1 + i) z / d): the amplitude falls by a factor e and the phase
lags by one radian over the same length d. So alpha = omega d^2 / 2 follows
from the slope of ln A against z and, independently, from the slope of the
lag against z.

``periodic_ftcs`` checks the formula against the explicit scheme of the T6
lesson (``pbc.thermodynamics.conduction.ftcs_step``), with no formula of
this module inside it.
"""

import numpy as np
from numpy.typing import NDArray

from pbc.thermodynamics.conduction import Fixed, ftcs_step

Array = NDArray[np.float64]


def damping_depth(alpha: float, omega: float) -> float:
    """d = sqrt(2 alpha / omega) (m): the depth over which the wave of
    angular frequency ``omega`` (rad/s) falls by e and lags by one radian."""
    return float(np.sqrt(2.0 * alpha / omega))


def periodic_temperature(z, t, mean, amplitude, phase, omega, alpha):
    """T(z, t) = mean + amplitude exp(-z/d) cos(omega t - z/d - phase): the
    periodic solution of the heat equation in a homogeneous half-space whose
    surface follows mean + amplitude cos(omega t - phase)."""
    d = damping_depth(alpha, omega)
    z = np.asarray(z, dtype=float)
    return mean + amplitude * np.exp(-z / d) * np.cos(omega * t - z / d - phase)


def diffusivity_from_slope(slope: float, omega: float) -> float:
    """alpha = omega d^2 / 2 from the slope 1/d (1/m) of -ln A or of the
    phase lag against depth."""
    return omega / (2.0 * slope**2)


def harmonic_of(t: Array, y: Array, omega: float) -> complex:
    """The complex amplitude c of the least-squares fit
    y = m + Re(c exp(i omega t)): |c| is the amplitude, -arg c the phase lag."""
    design = np.column_stack([np.ones_like(t), np.cos(omega * t), np.sin(omega * t)])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    return complex(coefficients[1], -coefficients[2])


def periodic_ftcs(
    alpha: float,
    omega: float,
    depths: Array,
    *,
    dz: float,
    r: float,
    bottom: float,
    periods: int,
) -> tuple[Array, Array]:
    """Drive T6's explicit scheme with the surface held at cos(omega t) (a
    unit amplitude about zero) and the bottom ``bottom`` (m) held at zero,
    from a ground at zero, for ``periods`` periods; return the amplitude and
    the phase lag of the last period's harmonic at ``depths``. The step is
    the period divided into a whole number of steps with r at most ``r``."""
    z = np.arange(0.0, bottom + dz / 2, dz)
    period = 2 * np.pi / omega
    steps = int(np.ceil(period * alpha / (r * dz**2)))
    dt = period / steps
    ratio = alpha * dt / dz**2
    temperature = np.zeros(z.size)
    rows = np.rint(np.asarray(depths) / dz).astype(int)
    last = np.empty((steps, rows.size))
    for n in range(periods * steps):
        surface = np.cos(omega * (n + 1) * dt)
        temperature = ftcs_step(temperature, ratio, dz, 1.0, Fixed(surface), Fixed(0.0))
        if n >= (periods - 1) * steps:
            last[n - (periods - 1) * steps] = temperature[rows]
    t = (np.arange((periods - 1) * steps, periods * steps) + 1) * dt
    c = np.array([harmonic_of(t, last[:, k], omega) for k in range(rows.size)])
    return np.abs(c), -np.angle(c)
