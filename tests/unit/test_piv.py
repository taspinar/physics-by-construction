"""The vorticity stencils of the PIV lab (FL7): exact where they should be,
second order on an analytic vortex with the stated error ratio, the stated
noise on independent errors, the mask respected; the band-pass and the
reflection of the street."""

import numpy as np
import pytest

from pbc.fluids import piv
from pbc.fluids.vortices import shedding_frequency


@pytest.mark.parametrize("stencil", piv.STENCILS)
def test_both_stencils_are_exact_on_a_quadratic_field(stencil):
    h = 0.1
    y, x = np.mgrid[0:12, 0:15] * h
    u = 3 * y**2 - x * y
    v = 2 * x**2 + 5 * x * y
    omega = piv.vorticity(u, v, h, stencil)
    exact = (4 * x + 5 * y) - (6 * y - x)
    inside = np.isfinite(omega)
    reach = piv.REACH[stencil]
    assert inside.sum() == (12 - 2 * reach) * (15 - 2 * reach)
    assert omega[inside] == pytest.approx(exact[inside], abs=1e-10)


def _lamb_oseen_error(stencil: str, h: float) -> float:
    n = round(3.0 / h)
    axis = np.arange(-n, n + 1) * h
    x, y = np.meshgrid(axis, axis)
    u, v, exact = piv.lamb_oseen(x, y)
    omega = piv.vorticity(u, v, h, stencil)
    inside = np.isfinite(omega)
    return float(np.max(np.abs(omega[inside] - exact[inside])) / exact.max())


def test_the_stencils_are_second_order_with_the_stated_ratio():
    for stencil in piv.STENCILS:
        coarse, fine = (_lamb_oseen_error(stencil, h) for h in (0.1, 0.05))
        assert coarse / fine == pytest.approx(4.0, rel=0.02)
    ratio = _lamb_oseen_error("least squares", 0.05) / _lamb_oseen_error(
        "central", 0.05
    )
    assert ratio == pytest.approx(
        piv.TRUNCATION["least squares"] / piv.TRUNCATION["central"], rel=0.02
    )


@pytest.mark.parametrize("stencil", piv.STENCILS)
def test_the_noise_gain_on_independent_errors(stencil):
    rng = np.random.default_rng(7)
    h, s = 0.5, 0.01
    u, v = rng.normal(0, s, (2, 400, 400))
    omega = piv.vorticity(u, v, h, stencil)
    assert np.nanstd(omega) * h / s == pytest.approx(piv.NOISE_GAIN[stencil], rel=0.01)


@pytest.mark.parametrize("stencil", piv.STENCILS)
def test_no_vorticity_where_the_stencil_touches_the_mask(stencil):
    u = np.ones((3, 11, 11))
    mask = np.zeros(u.shape, bool)
    mask[:, 5, 5] = True
    omega = piv.vorticity(u, u, 1.0, stencil, mask)
    r = piv.REACH[stencil]
    assert np.isnan(omega[:, 5 - r : 6 + r, 5 - r : 6 + r]).all()
    assert np.isfinite(omega[:, 5, 5 + r + 1]).all()
    assert np.isfinite(omega[:, 5 + r + 1, 5]).all()


def test_the_band_pass_keeps_the_shedding_and_its_crossings():
    rate = 20.0
    t = np.arange(4000) / rate
    rng = np.random.default_rng(3)
    clean = np.sin(2 * np.pi * 0.9 * t)
    noisy = clean + 0.6 * rng.normal(size=t.size) + 0.5 * np.sin(2 * np.pi * 0.02 * t)
    filtered = piv.band_pass(noisy, 0.5, 1.3, rate)
    f, _ = shedding_frequency(t, filtered)
    assert f == pytest.approx(0.9, rel=0.01)
    f_raw, _ = shedding_frequency(t, noisy)
    assert f_raw > 1.2  # noise adds crossings: the reason for the filter


def test_the_reflection_of_an_antisymmetric_street():
    y = np.arange(-5, 6)[:, None] * 1.0
    x = np.arange(20)[None, :] * 1.0
    omega = np.sign(y) * np.sin(x)  # opposite signs on the two sides
    band, mirrored = piv.reflect(omega, 5, 4)
    assert band.shape == mirrored.shape == (9, 20)
    assert mirrored == pytest.approx(-band)
