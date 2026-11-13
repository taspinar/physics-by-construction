"""The circular-speed model of the AST9 lab (``pbc.astrophysics.rotation_curves``):
the pull of thin shells summed numerically gives v^2 = G M(<r)/r, the shells
outside r add nothing, and the closed-form halo speeds of the reference module
are G M(<r)/r of their densities."""

from functools import partial

import numpy as np
import pytest

from pbc.astrophysics import rotation_curves as rc
from pbc.data.reference import sparc_rotmod


def test_g_is_the_one_of_the_reference_module():
    assert rc.G_KPC == sparc_rotmod.G_KPC
    # 4.3009e-6 kpc (km/s)^2 / M_sun, the value usually quoted.
    assert abs(rc.G_KPC / 4.3009e-6 - 1) < 1e-4


def test_a_shell_pulls_like_a_point_outside_and_not_at_all_inside():
    for r, s in ((3.0, 1.0), (3.0, 2.99), (10.0, 0.1)):
        assert rc.shell_pull(r, s) == pytest.approx(1 / r**2, rel=1e-9)
    for r, s in ((1.0, 3.0), (2.99, 3.0), (0.1, 10.0)):
        assert abs(rc.shell_pull(r, s)) < 1e-9 / s**2


def test_a_uniform_sphere_gives_the_known_speeds():
    # Inside a uniform sphere M(<r) grows as r^3, so v grows as r; outside,
    # the point-mass speed of the Kepler-orbit lesson.
    rho, radius = 0.1, 2.0  # M_sun/pc^3, kpc

    def density(s):
        return rho if s < radius else 0.0

    total = 4 / 3 * np.pi * radius**3 * rho * rc.PC3_PER_KPC3
    for r in (0.5, 1.0, 4.0):
        mass = 4 / 3 * np.pi * min(r, radius) ** 3 * rho * rc.PC3_PER_KPC3
        assert rc.enclosed_mass(density, min(r, radius)) == pytest.approx(
            mass, rel=1e-9
        )
        assert rc.circular_speed_squared(mass, r) == pytest.approx(
            rc.G_KPC * mass / r, rel=1e-15
        )
    assert rc.circular_speed_squared(total, 4.0) == pytest.approx(
        rc.circular_speed_squared(total, 1.0) / 4, rel=1e-15
    )


@pytest.mark.parametrize(
    ("density", "closed", "params"),
    [
        (rc.nfw_density, sparc_rotmod.nfw_squared, (10.0, 0.01)),
        (rc.iso_density, sparc_rotmod.iso_squared, (2.0, 0.05)),
        (rc.nfw_density, sparc_rotmod.nfw_squared, (1.5, 0.3)),
        (rc.iso_density, sparc_rotmod.iso_squared, (0.5, 1.0)),
    ],
)
def test_the_halo_speeds_are_the_shell_sum_of_their_densities(density, closed, params):
    profile = partial(density, **dict(zip(_names(density), params, strict=True)))
    for r in (0.3, 2.0, 10.0, 40.0):
        expected = float(closed(np.array(r), *params))
        mass = rc.enclosed_mass(profile, r)
        assert rc.circular_speed_squared(mass, r) == pytest.approx(expected, rel=1e-9)
        total, outside = rc.shell_sum_speed_squared(profile, r, 100.0)
        assert total == pytest.approx(expected, rel=1e-9)
        assert abs(outside) < 1e-9 * expected


def test_the_densities_are_a_cusp_and_a_core():
    small = np.array([1e-4, 1e-3])
    nfw = rc.nfw_density(small, 10.0, 0.01)
    iso = rc.iso_density(small, 2.0, 0.05)
    # NFW rises as 1/r at the centre; the isothermal sphere is flat there.
    assert nfw[0] / nfw[1] == pytest.approx(10.0, rel=1e-3)
    assert iso[0] / iso[1] == pytest.approx(1.0, rel=1e-6)
    # Far out NFW falls as r^-3, the isothermal sphere as r^-2.
    assert rc.nfw_density(1e4, 1.0, 1.0) / rc.nfw_density(2e4, 1.0, 1.0) == (
        pytest.approx(8.0, rel=1e-3)
    )
    assert rc.iso_density(1e4, 1.0, 1.0) / rc.iso_density(2e4, 1.0, 1.0) == (
        pytest.approx(4.0, rel=1e-6)
    )


def _names(density):
    return ("r_s", "rho_s") if density is rc.nfw_density else ("r_c", "rho_0")
