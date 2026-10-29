"""Toy cosmological models: a homogeneous universe that expands.

The distances between galaxies grow with the scale factor a(t), equal to one
today. The Friedmann equation gives the Hubble rate H = (da/dt)/a in units of
its value today, H0,

    E(a) = H / H0 = sqrt(Omega_r a^-4 + Omega_m a^-3 + Omega_k a^-2 + Omega_L),

with the density parameters of radiation, matter, and the cosmological
constant today, and the curvature Omega_k = 1 - Omega_r - Omega_m -
Omega_L. Light emitted when the scale factor was a arrives stretched by
1 + z = 1/a, the redshift. Times are in units of the Hubble time 1/H0 and
distances in units of the Hubble distance c/H0. A ray from redshift z has
crossed the comoving distance

    D_C = integral from 0 to z of dz' / E(z'),

and the luminosity and angular diameter distances, which relate the flux
and the angular size of a source to its luminosity and its size, are
D_L = (1 + z) D_M and D_A = D_M / (1 + z), with D_M = D_C in a flat model
and sinh or sin of sqrt(|Omega_k|) D_C over sqrt(|Omega_k|) in an open or a
closed one. Analytic cases: matter only (Einstein-de Sitter), D_C =
2 (1 - 1/sqrt(1 + z)) and a = (3 t / 2)^(2/3); empty (Milne), D_L = z (1 +
z/2) and a = t; a cosmological constant only (de Sitter), D_C = z and
a = exp(t - t0). At small z every model gives D_L = z + (1 - q0) z²/2 + ...,
with the deceleration parameter q0 = Omega_r + Omega_m / 2 - Omega_L.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import quad, solve_ivp


@dataclass(frozen=True)
class Model:
    """A Friedmann model by its density parameters today; the curvature
    makes up the rest of one."""

    matter: float
    radiation: float = 0.0
    lam: float = 0.0  # the cosmological constant, Omega_Lambda

    @property
    def curvature(self) -> float:
        """Omega_k = 1 - Omega_r - Omega_m - Omega_Lambda."""
        return 1.0 - self.matter - self.radiation - self.lam

    @property
    def deceleration(self) -> float:
        """The deceleration parameter today, q0 = Omega_r + Omega_m/2 -
        Omega_Lambda."""
        return self.radiation + self.matter / 2 - self.lam


def hubble_rate(model: Model, a: ArrayLike) -> NDArray[np.float64]:
    """The Hubble rate E(a) = H/H0 at the scale factor ``a``, from the
    Friedmann equation."""
    a = np.asarray(a, dtype=np.float64)
    e2 = (
        model.radiation / a**4
        + model.matter / a**3
        + model.curvature / a**2
        + model.lam
    )
    if np.any(e2 <= 0):
        raise ValueError("the model does not expand at this scale factor")
    return np.sqrt(e2)


def age(model: Model) -> float:
    """The age of the model in Hubble times, the time since a = 0:
    the integral from 0 to 1 of da / (a E(a)), written in s = sqrt(a) so
    that the integrand stays finite at the start."""
    value, _ = quad(
        lambda s: 2 / (s * hubble_rate(model, s**2)) if s > 0 else 0.0,
        0.0,
        1.0,
        epsabs=1e-13,
        epsrel=1e-13,
    )
    return float(value)


@dataclass(frozen=True)
class Expansion:
    """The scale factor against the time from today, in Hubble times."""

    tau: NDArray[np.float64]
    a: NDArray[np.float64]


def expansion(
    model: Model,
    past: float,
    future: float,
    smallest: float = 1e-3,
    tolerance: float = 1e-12,
) -> Expansion:
    """Integrate da/dtau = a E(a) (DOP853) from a = 1 today back for ``past``
    Hubble times, or until a falls to ``smallest``, and forward for
    ``future``; return the scale factor on one time axis, today at zero."""

    def rate(tau, y):
        return [y[0] * hubble_rate(model, y[0])]

    def start(tau, y):
        return y[0] - smallest

    start.terminal = True
    halves = []
    for end in (-past, future):
        solution = solve_ivp(
            rate,
            (0.0, end),
            [1.0],
            method="DOP853",
            events=start,
            dense_output=False,
            rtol=tolerance,
            atol=tolerance * smallest,
            max_step=abs(end) / 200,
        )
        if not solution.success:
            raise RuntimeError(solution.message)
        halves.append((solution.t, solution.y[0]))
    (tp, ap), (tf, af) = halves
    return Expansion(
        np.concatenate([tp[::-1], tf[1:]]), np.concatenate([ap[::-1], af[1:]])
    )


def comoving_distance(model: Model, z: float) -> float:
    """The comoving distance to redshift ``z`` in Hubble distances,
    the integral from 0 to z of dz' / E(z'), by adaptive quadrature."""
    value, _ = quad(
        lambda x: 1 / hubble_rate(model, 1 / (1 + x)),
        0.0,
        z,
        epsabs=1e-13,
        epsrel=1e-13,
    )
    return float(value)


def transverse_distance(model: Model, comoving: float) -> float:
    """The transverse comoving distance D_M of a comoving distance in a
    model of any curvature."""
    k = model.curvature
    if abs(k) < 1e-15:
        return comoving
    root = np.sqrt(abs(k))
    if k > 0:
        return float(np.sinh(root * comoving) / root)
    return float(np.sin(root * comoving) / root)


def luminosity_distance(model: Model, z: float) -> float:
    """The luminosity distance (1 + z) D_M to redshift ``z``, in Hubble
    distances: a source of luminosity L gives the flux L / (4 pi D_L²)."""
    return (1 + z) * transverse_distance(model, comoving_distance(model, z))


def angular_diameter_distance(model: Model, z: float) -> float:
    """The angular diameter distance D_M / (1 + z) to redshift ``z``, in
    Hubble distances: a source of size l subtends the angle l / D_A."""
    return transverse_distance(model, comoving_distance(model, z)) / (1 + z)


def ray_distance(model: Model, z: float, tolerance: float = 1e-12) -> float:
    """The comoving distance to redshift ``z`` found by following a ray of
    light back in time: integrate da/dtau = a E(a) together with the
    comoving distance it crosses, dchi/dtau = -1/a, from today until the
    scale factor falls to 1/(1 + z). A second method, independent of the
    quadrature in redshift."""

    def rate(tau, y):
        return [y[0] * hubble_rate(model, y[0]), -1 / y[0]]

    def emitted(tau, y):
        return y[0] - 1 / (1 + z)

    emitted.terminal = True
    solution = solve_ivp(
        rate,
        (0.0, -10 * (1 + z)),
        [1.0, 0.0],
        method="DOP853",
        events=emitted,
        rtol=tolerance,
        atol=tolerance / (1 + z),
    )
    if not solution.success or len(solution.t_events[0]) == 0:
        raise RuntimeError("the ray did not reach the redshift")
    return float(solution.y_events[0][0][1])


def einstein_de_sitter_comoving(z: ArrayLike) -> NDArray[np.float64]:
    """The comoving distance in a flat universe of matter only:
    2 (1 - 1/sqrt(1 + z))."""
    return 2 * (1 - 1 / np.sqrt(1 + np.asarray(z, dtype=np.float64)))


def milne_luminosity(z: ArrayLike) -> NDArray[np.float64]:
    """The luminosity distance in an empty universe: z (1 + z/2)."""
    z = np.asarray(z, dtype=np.float64)
    return z * (1 + z / 2)


def de_sitter_comoving(z: ArrayLike) -> NDArray[np.float64]:
    """The comoving distance in a universe with a cosmological constant only:
    z."""
    return np.asarray(z, dtype=np.float64)


def flat_lambda_age(matter: float) -> float:
    """The age of a flat universe of matter and a cosmological constant
    1 - matter, in Hubble times: 2 asinh(sqrt(L / m)) / (3 sqrt(L))."""
    lam = 1 - matter
    return float(2 * np.arcsinh(np.sqrt(lam / matter)) / (3 * np.sqrt(lam)))


def flat_lambda_scale_factor(matter: float, t: ArrayLike) -> NDArray[np.float64]:
    """The scale factor of a flat universe of matter and a cosmological
    constant at the time ``t`` since a = 0, in Hubble times:
    (m / L)^(1/3) sinh(3 sqrt(L) t / 2)^(2/3)."""
    lam = 1 - matter
    t = np.asarray(t, dtype=np.float64)
    return (matter / lam) ** (1 / 3) * np.sinh(1.5 * np.sqrt(lam) * t) ** (2 / 3)


def low_redshift_luminosity(model: Model, z: ArrayLike) -> NDArray[np.float64]:
    """The luminosity distance to second order in z: z + (1 - q0) z²/2."""
    z = np.asarray(z, dtype=np.float64)
    return z + (1 - model.deceleration) * z**2 / 2
