"""The circular speed of a galaxy from its mass: the model of the AST9 lab.

Newtonian gravity, circular orbits. A star on a circular orbit of radius r
needs the inward acceleration v^2 / r. For mass arranged in spherical shells
only the mass inside r pulls on it, as if it sat at the centre, so

    v^2(r) = G M(<r) / r,    M(<r) = integral from 0 to r of 4 pi s^2 rho(s) ds,

the point-mass speed of the Kepler-orbit lesson with M replaced by the mass
inside the orbit. The speeds of several components add in squares, since
their accelerations add. The two halo densities are those of de Blok et al.
2008 (AJ 136, 2648, section 5.3; the register entry
``deblok-things-mass-models``): the NFW profile with a central cusp and the
pseudo-isothermal sphere with a core.

``shell_sum_speed_squared`` does not use the shell theorem: it adds the pull
of every thin shell, integrated numerically over its surface, so that the
lab can check the formula above rather than assume it.

Units: radii in kpc, densities in M_sun/pc^3, masses in M_sun, speeds in
km/s.
"""

import numpy as np
from scipy.integrate import quad

# G in kpc (km/s)^2 per solar mass, from the IAU 2015 nominal solar mass
# parameter GM_sun = 1.3271244e20 m^3/s^2 and the IAU 2012 astronomical unit
# (1 pc = 648000/pi au, au = 149597870700 m).
PARSEC = 648000 / np.pi * 149_597_870_700.0  # m
G_KPC = 1.3271244e20 / (1e3 * PARSEC) / 1e6  # kpc (km/s)^2 / M_sun
PC3_PER_KPC3 = 1e9


def nfw_density(r, r_s: float, rho_s: float):
    """NFW density [M_sun/pc^3]: rho_s / ((r/r_s) (1 + r/r_s)^2), a cusp."""
    x = np.asarray(r) / r_s
    return rho_s / (x * (1 + x) ** 2)


def iso_density(r, r_c: float, rho_0: float):
    """Pseudo-isothermal density [M_sun/pc^3]: rho_0 / (1 + (r/r_c)^2), a core."""
    return rho_0 / (1 + (np.asarray(r) / r_c) ** 2)


def enclosed_mass(density, r: float) -> float:
    """M(<r) [M_sun]: 4 pi s^2 rho(s) integrated numerically from 0 to r."""
    value, _ = quad(
        lambda s: 4 * np.pi * s**2 * density(s) * PC3_PER_KPC3,
        0.0,
        r,
        epsabs=0.0,
        epsrel=1e-11,
        limit=200,
    )
    return value


def circular_speed_squared(mass: float, r: float) -> float:
    """v^2 = G M(<r) / r [(km/s)^2] for a spherical mass inside r."""
    return G_KPC * mass / r


def shell_pull(r: float, s: float) -> float:
    """The inward acceleration at distance r from the centre of a thin shell
    of radius s and unit mass, in units of G: the Newtonian pull of each
    surface element, integrated numerically over the cosine of the angle,
    (1/2) integral of (r - s mu) / (r^2 + s^2 - 2 r s mu)^(3/2) d mu."""
    value, _ = quad(
        lambda mu: (r - s * mu) / (r * r + s * s - 2 * r * s * mu) ** 1.5,
        -1.0,
        1.0,
        # Outside the shell the integral is zero, so the tolerance is also
        # absolute, at 1e-12 of the pull of the shell at the larger radius.
        epsabs=1e-12 / max(r, s) ** 2,
        epsrel=1e-11,
        limit=400,
    )
    return 0.5 * value


def shell_sum_speed_squared(density, r: float, outer: float) -> tuple[float, float]:
    """v^2 = r g(r) [(km/s)^2], with g the pull of all shells from the centre
    to ``outer`` summed numerically; and the part of v^2 from the shells
    outside r (zero if the shell theorem holds)."""

    def pull(s):
        return 4 * np.pi * s**2 * density(s) * PC3_PER_KPC3 * shell_pull(r, s)

    inside, _ = quad(pull, 0.0, r, epsabs=0.0, epsrel=1e-10, limit=400)
    # The outer shells' pull may be zero: an absolute tolerance, 1e-10 of
    # the inner shells' pull.
    outside, _ = quad(pull, r, outer, epsabs=1e-10 * abs(inside), limit=400)
    return G_KPC * r * (inside + outside), G_KPC * r * outside
