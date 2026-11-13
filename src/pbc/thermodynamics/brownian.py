"""Brownian motion as a camera records it, and the Stokes-Einstein relation.

The random walk of the lesson "Random walks and diffusion" spreads with a
mean squared displacement (MSD) <r^2> = 2 d D t in d dimensions. A sphere of
radius r in a fluid of viscosity eta at temperature T walks with

    D = k_B T / (6 pi eta r),

the Stokes-Einstein relation: the thermal kicks of the fluid against the
Stokes drag of the sphere. A video camera does not record where a sphere is
at an instant. It integrates the light over an exposure tau_e, so a frame
shows the mean position over the exposure, and the tracking locates that mean
with an error of standard deviation sigma per coordinate. For a free
Brownian particle the MSD of the recorded positions at a lag tau >= tau_e is

    MSD(tau) = 2 d D (tau - tau_e / 3) + 2 d sigma^2,

a straight line of the same slope 2 d D whose intercept is lowered by the
blur and raised by the noise (Savin and Doyle, Biophys. J. 88, 623, 2005).
The blur also correlates successive steps: per coordinate their covariance
is D tau_e / 3 - sigma^2, positive for blur, negative for noise.

``camera_walks`` checks these formulas with the walker of the lesson
"Random walks and diffusion" (``pbc.thermodynamics.diffusion.random_walks``)
taking many short steps per frame, with no formula of this module inside it.
Quantities are in any consistent units (SI in ``stokes_einstein``).
"""

import numpy as np
from numpy.typing import NDArray

from pbc.thermodynamics.diffusion import random_walks

Array = NDArray[np.float64]
BOLTZMANN = 1.380649e-23  # J/K, exact (SI 2019)


def stokes_einstein(kelvin: float, viscosity: float, radius: float) -> float:
    """D = k_B T / (6 pi eta r) (m^2/s) of a sphere of ``radius`` (m) in a
    fluid of ``viscosity`` (Pa s) at ``kelvin`` (K)."""
    return BOLTZMANN * kelvin / (6.0 * np.pi * viscosity * radius)


def camera_msd(
    tau: Array, d: float, exposure: float, noise: float, dimension: int = 2
) -> Array:
    """The MSD of positions averaged over ``exposure`` and located with the
    error ``noise`` per coordinate, at lags ``tau`` of at least the exposure:
    2 dim D (tau - exposure / 3) + 2 dim noise^2."""
    tau = np.asarray(tau, dtype=float)
    if np.any(tau < exposure):
        raise ValueError("the formula holds for lags of at least the exposure")
    return 2.0 * dimension * (d * (tau - exposure / 3.0) + noise**2)


def camera_step_correlation(
    frame_time: float, d: float, exposure: float, noise: float
) -> float:
    """The correlation of successive one-frame steps of one coordinate:
    (D exposure / 3 - noise^2) / (2 D (frame_time - exposure / 3) + 2 noise^2),
    +1/4 for an exposure of a whole frame without noise, -1/2 for noise alone."""
    if not 0.0 <= exposure <= frame_time:
        raise ValueError("the exposure must lie between 0 and the frame time")
    covariance = d * exposure / 3.0 - noise**2
    variance = 2.0 * d * (frame_time - exposure / 3.0) + 2.0 * noise**2
    return float(covariance / variance)


def camera_walks(
    n_walkers: int,
    n_frames: int,
    frame_time: float,
    exposure: float,
    d: float,
    noise: float,
    rng: np.random.Generator,
    substeps: int = 20,
) -> Array:
    """What a camera records of ``n_walkers`` walkers of the plane: an array
    of shape ``(n_frames, n_walkers, 2)``.

    Each walker is the walker of ``random_walks`` with ``substeps`` steps per
    frame, of the length that gives the diffusion coefficient ``d``
    (l^2 = 4 d dt). It moves straight during a step, so the mean of its path
    over an exposure is the trapezoid rule over the step ends. Frame k
    records that mean over [k frame_time, k frame_time + exposure], plus a
    Gaussian error of standard deviation ``noise`` per coordinate. The
    exposure must be a whole number of steps, at most one frame.
    """
    dt = frame_time / substeps
    exposed = exposure / dt
    if not np.isclose(exposed, round(exposed)) or not 0 <= round(exposed) <= substeps:
        raise ValueError("the exposure must be a whole number of steps of a frame")
    exposed = round(exposed)
    paths = random_walks(n_walkers, n_frames * substeps, np.sqrt(4.0 * d * dt), rng)
    starts = np.arange(n_frames) * substeps
    if exposed == 0:
        recorded = paths[starts]
    else:
        weights = np.ones(exposed + 1)
        weights[[0, -1]] = 0.5
        weights /= exposed
        recorded = sum(w * paths[starts + k] for k, w in enumerate(weights))
    return recorded + rng.normal(0.0, noise, recorded.shape) if noise else recorded
