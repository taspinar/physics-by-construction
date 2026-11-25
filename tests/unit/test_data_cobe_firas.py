"""The COBE FIRAS monopole sample parses as its card says, the Planck
intensity and its derivative have their limits, column 2 is rebuilt as the
header says, and the numbers of the dossier come from the reference module."""

import hashlib

import numpy as np
import pytest
import yaml

from pbc.data import REGISTRY_DIR, SAMPLES_DIR
from pbc.data.reference import cobe_firas as f

DATA = SAMPLES_DIR / "cobe-firas-monopole"
CARD = REGISTRY_DIR / "cobe-firas-monopole.yaml"


@pytest.fixture(scope="module")
def spectrum():
    return f.read_spectrum(DATA)


def test_cobe_firas_sample_parses(spectrum):
    card = yaml.safe_load(CARD.read_text())
    (entry,) = card["samples"]
    raw = (DATA / f.FILE).read_bytes()
    assert entry["path"] == f.FILE
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    assert len(raw) == entry["bytes"]
    assert len(spectrum.header) == 18
    assert spectrum.header[0] == "# COBE/FIRAS CMB monopole spectrum"
    assert "Table 4 of Fixsen et al. 1996 ApJ 473, 576" in spectrum.header[1]
    # Units as the header states them, column by column.
    text = "\n".join(spectrum.header)
    assert all(f"Column {column} = " in text for column in range(1, 6))
    assert text.count("units = kJy/sr") == 3
    assert "units = MJy/sr" in text and "units = cm^-1" in text
    assert f.UNITS["monopole"] == "MJy/sr" and f.UNITS["wavenumber"] == "cm^-1"
    # 43 frequencies on the paper's grid of 0.4538 cm^-1, rounded to 0.01.
    assert spectrum.wavenumber.shape == (f.ROWS,)
    assert spectrum.wavenumber[0] == 2.27 and spectrum.wavenumber[-1] == 21.33
    steps = np.diff(spectrum.wavenumber)
    assert np.all(np.abs(steps - 0.4538) < 0.011)
    # Columns 3 to 5 are integers; every uncertainty positive.
    for column in (spectrum.residual, spectrum.sigma, spectrum.galaxy):
        assert np.array_equal(column, np.round(column))
    assert spectrum.sigma.min() == 10 and spectrum.sigma.max() == 282
    # The reference temperature: the header's, equal to the card's.
    assert spectrum.t_ref == 2.725
    assert card["reference_temperature"]["value"] == spectrum.t_ref
    assert f.header_temperature(spectrum.header) == f.reference_temperature(card)


def test_a_header_with_another_reference_temperature_is_refused(tmp_path):
    text = (DATA / f.FILE).read_text().replace("2.725 K BB", "2.728 K BB")
    (tmp_path / f.FILE).write_text(text)
    with pytest.raises(ValueError, match=r"2\.728 K, the card's 2\.725 K"):
        f.read_spectrum(tmp_path)
    assert f.read_spectrum(tmp_path, t_ref=2.728).t_ref == 2.728


def test_planck_has_its_rayleigh_jeans_and_wien_limits():
    temperature = 2.725
    low = np.array([1e-4])  # cm^-1, x ~ 5e-5
    nu = f.C * 100 * low
    rayleigh_jeans = 2 * nu**2 * f.K_B * temperature / f.C**2 / f.MJY
    assert f.planck(low, temperature)[0] == pytest.approx(rayleigh_jeans[0], rel=1e-4)
    high = np.array([200.0])  # x ~ 106
    nu = f.C * 100 * high
    x = f.H * nu / (f.K_B * temperature)
    wien = 2 * f.H * nu**3 / f.C**2 * np.exp(-x) / f.MJY
    assert f.planck(high, temperature)[0] == pytest.approx(wien[0], rel=1e-12)


def test_the_derivative_in_t_matches_a_central_difference(spectrum):
    step = 1e-5
    numerical = (
        f.planck(spectrum.wavenumber, 2.725 + step)
        - f.planck(spectrum.wavenumber, 2.725 - step)
    ) / (2 * step)
    assert np.allclose(f.dplanck_dt(spectrum.wavenumber, 2.725), numerical, rtol=1e-8)


def test_the_peak_brightness_is_the_maximum_over_frequency():
    grid = np.linspace(1.0, 20.0, 200001)
    assert f.peak_brightness(2.725) == pytest.approx(
        f.planck(grid, 2.725).max(), rel=1e-9
    )
    assert f.peak_brightness(2.725) == pytest.approx(383.666, abs=1e-3)


def test_column_2_is_a_2725_k_blackbody_plus_column_3(spectrum):
    # With the CODATA 1986 constants within 0.8 kJy/sr (column 2 has three
    # decimals of MJy/sr, 1 kJy/sr); with the exact SI ones up to 7.6.
    rebuilt = f.rebuild_monopole(spectrum)
    assert np.abs(rebuilt - spectrum.monopole).max() * 1000 < 0.8
    exact = f.planck(spectrum.wavenumber, 2.725) + spectrum.residual / 1000
    assert 7.5 < np.abs(exact - spectrum.monopole).max() * 1000 < 7.7


def test_the_fit_recovers_an_injected_shift_and_galactic_scale(spectrum):
    rng = np.random.default_rng(20261125)
    injected_t, injected_g = 40e-6, 0.8
    residual = (
        injected_t * f.dplanck_dt(spectrum.wavenumber, spectrum.t_ref) * 1000
        + injected_g * spectrum.galaxy
        + rng.normal(0, spectrum.sigma)
    )
    synthetic = f.Spectrum(
        spectrum.wavenumber,
        spectrum.monopole,
        residual,
        spectrum.sigma,
        spectrum.galaxy,
        spectrum.header,
        spectrum.t_ref,
    )
    fit = f.fit_blackbody(synthetic)
    assert abs(fit.delta_t - injected_t) < 3 * fit.sigma_t
    assert abs(fit.galaxy_scale - injected_g) < 3 * fit.sigma_galaxy


def test_the_dossier_numbers(spectrum):
    fit = f.fit_blackbody(spectrum)
    assert fit.delta_t * 1e6 == pytest.approx(0.54, abs=0.01)
    assert fit.sigma_t * 1e6 == pytest.approx(8.06, abs=0.01)
    assert fit.galaxy_scale == pytest.approx(-0.0018, abs=1e-4)
    assert fit.sigma_galaxy == pytest.approx(0.0251, abs=1e-4)
    assert fit.chi2 == pytest.approx(45.02, abs=0.01) and fit.dof == 41
    assert fit.weighted_rms == pytest.approx(18.89, abs=0.01)
    ppm = fit.weighted_rms / 1000 / f.peak_brightness(spectrum.t_ref) * 1e6
    assert ppm == pytest.approx(49.25, abs=0.01)
