"""Brownian motion as a camera records it (``pbc.thermodynamics.brownian``):
Stokes-Einstein, the blurred and noisy MSD, and the walker of the random-walks
lesson recorded by a camera against both formulas."""

import numpy as np
import pytest

from pbc.data.reference import trackpy_bulk_water
from pbc.thermodynamics.brownian import (
    camera_msd,
    camera_step_correlation,
    camera_walks,
    stokes_einstein,
)

FRAME = 1 / 24  # s
D = 0.4  # µm^2/s


def test_stokes_einstein_is_the_dossiers():
    # The dossier: 0.429 and 0.491 µm^2/s for r = 0.5 µm at 20 and 25 °C.
    for celsius, expected in ((20.0, 0.429), (25.0, 0.491)):
        eta = trackpy_bulk_water.VISCOSITY[celsius]
        value = 1e12 * stokes_einstein(celsius + 273.15, eta, 0.5e-6)
        assert value == pytest.approx(trackpy_bulk_water.stokes_einstein(celsius))
        assert value == pytest.approx(expected, abs=5e-4)


def test_stokes_einstein_scales_as_temperature_over_viscosity_and_radius():
    base = stokes_einstein(300.0, 1e-3, 1e-6)
    assert stokes_einstein(600.0, 1e-3, 1e-6) == pytest.approx(2 * base)
    assert stokes_einstein(300.0, 2e-3, 1e-6) == pytest.approx(base / 2)
    assert stokes_einstein(300.0, 1e-3, 2e-6) == pytest.approx(base / 2)


def test_the_camera_msd_keeps_the_slope_and_moves_the_intercept():
    tau = np.arange(1, 11) * FRAME
    ideal = camera_msd(tau, D, 0.0, 0.0)
    assert ideal == pytest.approx(4 * D * tau)
    blurred = camera_msd(tau, D, FRAME, 0.05)
    slope, intercept = np.polyfit(tau, blurred, 1)
    assert slope == pytest.approx(4 * D)
    assert intercept == pytest.approx(-4 * D * FRAME / 3 + 4 * 0.05**2)
    assert camera_msd(tau, D, 0.0, 0.0, dimension=1) == pytest.approx(2 * D * tau)
    with pytest.raises(ValueError):
        camera_msd(np.array([FRAME / 2]), D, FRAME, 0.0)


def test_the_step_correlation_in_its_limits():
    assert camera_step_correlation(FRAME, D, 0.0, 0.0) == 0.0
    assert camera_step_correlation(FRAME, D, FRAME, 0.0) == pytest.approx(0.25)
    # A localisation error far larger than the motion: steps alternate.
    assert camera_step_correlation(FRAME, 1e-9, 0.0, 1.0) == pytest.approx(-0.5)
    with pytest.raises(ValueError):
        camera_step_correlation(FRAME, D, 2 * FRAME, 0.0)


@pytest.mark.parametrize(
    ("exposure", "noise"), [(0.0, 0.0), (FRAME, 0.0), (FRAME, 0.03), (0.0, 0.05)]
)
def test_the_recorded_walk_follows_the_camera_formulas(exposure, noise):
    walks = camera_walks(
        3000, 30, FRAME, exposure, D, noise, np.random.default_rng(439)
    )
    assert walks.shape == (30, 3000, 2)
    lags = np.arange(1, 8)
    per_walker = np.stack(
        [((walks[k:] - walks[:-k]) ** 2).sum(axis=2).mean(axis=0) for k in lags],
        axis=1,
    )
    msd = per_walker.mean(axis=0)
    error = per_walker.std(axis=0, ddof=1) / np.sqrt(per_walker.shape[0])
    model = camera_msd(lags * FRAME, D, exposure, noise)
    # Within four standard errors of the simulation at every lag.
    assert np.all(np.abs(msd - model) < 4 * error)
    steps = np.diff(walks, axis=0)
    rho = np.corrcoef(steps[:-1].ravel(), steps[1:].ravel())[0, 1]
    # 3000 x 28 x 2 pairs: the standard error of rho is about 0.004.
    assert rho == pytest.approx(
        camera_step_correlation(FRAME, D, exposure, noise), abs=0.02
    )


def test_the_recorded_walk_is_a_function_of_its_seed():
    first = camera_walks(10, 5, FRAME, FRAME, D, 0.03, np.random.default_rng(1))
    again = camera_walks(10, 5, FRAME, FRAME, D, 0.03, np.random.default_rng(1))
    assert np.array_equal(first, again)
    with pytest.raises(ValueError):
        camera_walks(10, 5, FRAME, FRAME / 3.5, D, 0.0, np.random.default_rng(1))
