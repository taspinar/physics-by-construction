"""The level model of hydrogen (``pbc.quantum.hydrogen``): the levels with the
reduced mass, the Balmer series against laboratory hydrogen, and the radial
equation on the grid of the quantum course."""

import numpy as np
import pytest

from pbc.data.reference.sdss_balmer import BALMER_LAB, ME_OVER_MP, R_INF
from pbc.quantum import hydrogen


def test_the_levels_scale_with_the_reduced_mass():
    n = np.arange(1, 7)
    assert hydrogen.level(n) == pytest.approx(-0.5 / n**2, rel=1e-15)
    mu = hydrogen.reduced_mass_ratio(ME_OVER_MP)
    assert mu == pytest.approx(1836.15267343 / 1837.15267343, rel=1e-14)
    assert hydrogen.level(n, mu) == pytest.approx(mu * hydrogen.level(n), rel=1e-15)
    with pytest.raises(ValueError):
        hydrogen.level(0)


def test_the_balmer_series_with_r_h_is_laboratory_hydrogen_to_the_fine_structure():
    # The Bohr formula with R_H against the laboratory vacuum wavelengths:
    # the difference is the fine structure, a few parts in 1e5, and it
    # would be 5e-4 (the recoil) with R_inf.
    r_h = hydrogen.rydberg_hydrogen(R_INF, ME_OVER_MP)
    for n, lab in BALMER_LAB.items():
        predicted = 1e10 / hydrogen.balmer_wavenumber(n, r_h)
        assert abs(predicted / lab - 1) < 3e-5
        heavy = 1e10 / hydrogen.balmer_wavenumber(n, R_INF)
        assert heavy / lab - 1 == pytest.approx(-ME_OVER_MP, abs=3e-5)
    with pytest.raises(ValueError):
        hydrogen.balmer_wavenumber(2, r_h)


def test_the_grid_converges_at_second_order_to_the_levels():
    mu = hydrogen.reduced_mass_ratio(ME_OVER_MP)
    n = np.arange(1, 5)
    exact = hydrogen.level(n, mu)
    coarse = hydrogen.radial_levels(0, 4, 120.0, 2400, mu)
    fine = hydrogen.radial_levels(0, 4, 120.0, 4800, mu)
    error_coarse, error_fine = coarse - exact, fine - exact
    assert np.all(np.abs(error_coarse / exact) < 1e-3)
    assert error_coarse / error_fine == pytest.approx(4.0, rel=0.01)
    # h = 0.05 here: the h^4 term leaves about 2e-7 in the ground state.
    assert hydrogen.richardson(coarse, fine) == pytest.approx(exact, rel=1e-6)


def test_the_energy_does_not_depend_on_the_angular_momentum():
    s = hydrogen.richardson(
        hydrogen.radial_levels(0, 4, 120.0, 2400),
        hydrogen.radial_levels(0, 4, 120.0, 4800),
    )
    p = hydrogen.richardson(
        hydrogen.radial_levels(1, 3, 120.0, 2400),
        hydrogen.radial_levels(1, 3, 120.0, 4800),
    )
    d = hydrogen.richardson(
        hydrogen.radial_levels(2, 2, 120.0, 2400),
        hydrogen.radial_levels(2, 2, 120.0, 4800),
    )
    assert p == pytest.approx(s[1:], rel=1e-7)
    assert d == pytest.approx(s[2:], rel=1e-7)


def test_a_wall_too_close_raises_the_levels():
    # The outer wall squeezes the large states: a check that the lab's wall
    # is far enough out is meaningful.
    near = hydrogen.radial_levels(0, 4, 30.0, 1200)
    far = hydrogen.radial_levels(0, 4, 120.0, 4800)
    assert near[3] > far[3] + 1e-3
    assert near[0] == pytest.approx(far[0], abs=1e-3)


def test_richardson_removes_the_second_order_term():
    h = np.array([0.1, 0.05])
    values = 2.0 + 3.0 * h**2
    assert hydrogen.richardson(values[0], values[1]) == pytest.approx(2.0, abs=1e-12)
