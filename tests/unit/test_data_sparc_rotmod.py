"""The SPARC rotation-curve sample parses as its card says, and the numbers of
the dossier come from the reference module: the normalisation of Vdisk, the
maximum disk, the fits with and without a halo, and the degeneracy of Y."""

import hashlib

import numpy as np
import pytest
import yaml
from scipy.integrate import quad

from pbc.data import REGISTRY_DIR, SAMPLES_DIR
from pbc.data.reference import sparc_rotmod as s

DATA = SAMPLES_DIR / "sparc-rotation-curves"
CARD = REGISTRY_DIR / "sparc-rotation-curves.yaml"

# name: (distance in Mpc, rows, first radius, last radius, rows with Vgas < 0)
FILES = {
    "NGC3198": (13.8, 43, 0.32, 44.08, 6),
    "NGC2403": (3.16, 73, 0.16, 20.87, 0),
    "NGC2841": (14.1, 50, 3.44, 63.64, 9),
    "DDO154": (4.04, 12, 0.49, 5.92, 0),
    "NGC2903": (6.6, 34, 0.32, 24.96, 0),
}


@pytest.fixture(scope="module")
def sample():
    return s.load(DATA)


@pytest.fixture(scope="module")
def result(sample):
    return s.analyse(sample)


def test_sparc_rotmod_sample_parses(sample):
    card = yaml.safe_load(CARD.read_text())
    listed = {entry["path"]: entry for entry in card["samples"]}
    assert set(listed) == {f"{n}_rotmod.dat" for n in s.GALAXIES}
    for name, (distance, rows, first, last, negative) in FILES.items():
        path = DATA / f"{name}_rotmod.dat"
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == listed[path.name]["sha256"]
        assert len(raw) == listed[path.name]["bytes"]
        lines = raw.decode("ascii").splitlines()
        # Three header lines: the distance, the column names, the units.
        assert lines[0] == f"# Distance = {distance:g} Mpc"
        assert lines[1].split() == ["#", *s.COLUMNS]
        assert lines[2].split() == ["#", *s.UNITS]
        # Then tab-separated rows of eight numbers with two decimals.
        body = lines[3:]
        assert len(body) == rows
        for line in body:
            fields = line.split("\t")
            assert len(fields) == 8
            assert all(len(f.split(".")[1]) == 2 for f in fields)

        galaxy = sample[name]
        assert galaxy.distance == distance
        assert galaxy.radius.shape == (rows,)
        assert galaxy.radius[0] == first and galaxy.radius[-1] == last
        assert np.all(np.diff(galaxy.radius) > 0)
        columns = (
            galaxy.v_obs,
            galaxy.v_err,
            galaxy.v_disk,
            galaxy.v_bulge,
            galaxy.sb_disk,
            galaxy.sb_bulge,
        )
        assert all(np.all(np.isfinite(c)) and np.all(c >= 0) for c in columns)
        assert np.all(galaxy.v_obs > 0) and np.all(galaxy.v_err > 0)
        assert np.sum(galaxy.v_gas < 0) == negative
        # Only NGC 2841 has a bulge in the sample.
        assert (galaxy.v_bulge.max() > 0) == (name == "NGC2841")
        assert (galaxy.sb_bulge.max() > 0) == (name == "NGC2841")


def test_a_file_with_other_columns_or_units_is_refused(tmp_path):
    text = (DATA / "DDO154_rotmod.dat").read_text()
    bad = tmp_path / "X_rotmod.dat"
    bad.write_text(text.replace("Vdisk", "Vstar"))
    with pytest.raises(ValueError, match="columns"):
        s.read_rotmod(bad)
    bad.write_text(text.replace("kpc", "pc", 1))
    with pytest.raises(ValueError, match="units"):
        s.read_rotmod(bad)
    bad.write_text(text.replace("# Distance = 4.04 Mpc", "# D = 4.04"))
    with pytest.raises(ValueError, match="distance"):
        s.read_rotmod(bad)


def test_g_in_galactic_units():
    # G M_sun / (1 kpc) in (km/s)^2, the familiar 4.30e-6.
    g = s.G_KPC
    assert g == pytest.approx(4.3009e-6, rel=1e-4)


@pytest.mark.parametrize("halo", ["nfw", "iso"])
def test_the_halo_speeds_are_the_mass_of_their_densities(halo):
    radius, density = 3.0, 0.02  # kpc, M_sun/pc^3
    profile = {
        "nfw": lambda r: density / ((r / radius) * (1 + r / radius) ** 2),
        "iso": lambda r: density / (1 + (r / radius) ** 2),
    }[halo]
    for r in (0.5, 3.0, 20.0):
        mass = quad(lambda x: 4 * np.pi * x**2 * profile(x) * 1e9, 0, r)[0]
        speed2 = s.HALO_SQUARED[halo](np.array([r]), radius, density)[0]
        assert speed2 == pytest.approx(s.G_KPC * mass / r, rel=1e-8)


def test_vdisk_is_the_speed_of_the_light_at_mass_to_light_one(sample):
    # Vdisk^2 r / G at the last radius over the light of SBdisk inside it: a
    # thin disk's speed slightly exceeds the Keplerian one of its mass, so a
    # little above 1. At Y = 0.5 the ratio would be near 0.5.
    ratios = {name: s.normalisation_ratio(g) for name, g in sample.items()}
    assert ratios == pytest.approx(
        {
            "NGC3198": 1.025,
            "NGC2403": 1.021,
            "NGC2841": 1.065,
            "DDO154": 1.085,
            "NGC2903": 1.055,
        },
        abs=1e-3,
    )


def test_the_maximum_disk_touches_the_curve_and_exceeds_it_nowhere(sample, result):
    expected = {
        "NGC3198": 0.608,
        "NGC2403": 0.861,
        "NGC2841": 1.066,
        "DDO154": 1.473,
        "NGC2903": 0.069,
    }
    assert result["maximum_disk"] == pytest.approx(expected, abs=1e-3)
    for name, galaxy in sample.items():
        y = result["maximum_disk"][name]
        speed = np.sqrt(np.clip(galaxy.baryons_squared(y), 0, None))
        ceiling = galaxy.v_obs + galaxy.v_err
        assert np.all(speed <= ceiling + 1e-9)
        assert np.min(ceiling - speed) == pytest.approx(0, abs=1e-9)


def test_no_mass_to_light_ratio_fits_without_a_halo(result):
    for name in s.GALAXIES:
        given = result["fits"][(name, "none", 0.0)]
        floored = result["fits"][(name, "none", s.FLOOR)]
        assert given.reduced_chi2 > 170
        assert floored.reduced_chi2 > 17
        halo = min(result["fits"][(name, h, 0.0)].reduced_chi2 for h in ("nfw", "iso"))
        assert given.reduced_chi2 > 20 * halo


# (galaxy, halo): (Y, halo radius in kpc, density in M_sun/pc^3, chi2/dof),
# errV as given; the dossier's table.
FITS = {
    ("NGC3198", "nfw"): (0.451, 14.5, 0.00727, 1.39),
    ("NGC3198", "iso"): (0.517, 2.78, 0.0487, 1.24),
    ("NGC2403", "nfw"): (0.288, 7.15, 0.0235, 9.14),
    ("NGC2403", "iso"): (0.758, 3.03, 0.0364, 10.70),
    ("NGC2841", "nfw"): (1.021, 47.5, 0.00239, 1.41),
    ("NGC2841", "iso"): (1.095, 9.08, 0.0167, 1.34),
    ("DDO154", "nfw"): (0.000, 13.4, 0.00178, 8.73),
    ("DDO154", "iso"): (0.060, 1.44, 0.0292, 2.19),
    ("NGC2903", "nfw"): (0.223, 4.79, 0.114, 5.95),
    ("NGC2903", "iso"): (0.300, 0.943, 0.649, 6.23),
}


def test_the_halo_fits_are_the_dossiers(result):
    for (name, halo), (y, radius, density, reduced) in FITS.items():
        m = result["fits"][(name, halo, 0.0)]
        assert m.stellar == pytest.approx(y, abs=2e-3), (name, halo)
        assert m.halo_radius == pytest.approx(radius, rel=5e-3), (name, halo)
        assert m.halo_density == pytest.approx(density, rel=5e-3), (name, halo)
        assert m.reduced_chi2 == pytest.approx(reduced, abs=0.01), (name, halo)


def test_a_known_halo_and_mass_to_light_ratio_are_recovered(sample):
    # Synthetic test: NGC 3198's baryons at Y = 0.6 with a cored halo, the
    # file's errV as noise of a fixed seed; the fit must find them again.
    g = sample["NGC3198"]
    truth = np.sqrt(g.baryons_squared(0.6) + s.iso_squared(g.radius, 3.0, 0.04))
    rng = np.random.default_rng(470)
    noisy = truth + rng.normal(0, g.v_err)
    fake = s.Galaxy(
        "synthetic", g.distance, g.radius, noisy, g.v_err, g.v_gas,
        g.v_disk, g.v_bulge, g.sb_disk, g.sb_bulge,
    )  # fmt: skip
    m = s.fit_mass_model(fake, "iso")
    assert abs(m.stellar - 0.6) < 2 * m.fit.stderr[0]
    assert abs(m.fit.value("log_r") - np.log10(3.0)) < 2 * m.fit.stderr[1]
    assert abs(m.fit.value("log_rho") - np.log10(0.04)) < 2 * m.fit.stderr[2]
    assert 0.5 < m.reduced_chi2 < 1.6


def test_the_cusp_overshoots_the_dwarfs_inner_points_and_the_core_does_not(
    sample, result
):
    g = sample["DDO154"]
    nfw = result["fits"][("DDO154", "nfw", 0.0)]
    iso = result["fits"][("DDO154", "iso", 0.0)]
    assert nfw.reduced_chi2 > 3.5 * iso.reduced_chi2
    # The NFW fit puts its stars at the lower bound and still lies above the
    # first two points by more than twice their errV.
    assert nfw.stellar == pytest.approx(0.0, abs=1e-6)
    over = (nfw.total(g) - g.v_obs)[:2] / g.v_err[:2]
    assert np.all(over > 2.4)
    assert np.all(np.abs(iso.total(g) - g.v_obs)[:2] / g.v_err[:2] < 1.3)
    # The halo dominates: at the last point the gas gives 12 % of Vobs^2 and
    # the stars of the core fit 0.1 %.
    assert g.gas_squared()[-1] / g.v_obs[-1] ** 2 == pytest.approx(0.118, abs=1e-3)
    assert g.stars_squared(iso.stellar)[-1] / g.v_obs[-1] ** 2 < 2e-3


def test_the_mass_to_light_ratio_depends_on_the_halo_and_the_errors(sample, result):
    fits = result["fits"]
    # NGC 2403: 0.29 with a cusp, 0.76 with a core, 0.50 and 0.84 with the floor.
    assert fits[("NGC2403", "nfw", 0.0)].stellar == pytest.approx(0.288, abs=2e-3)
    assert fits[("NGC2403", "iso", 0.0)].stellar == pytest.approx(0.758, abs=2e-3)
    assert fits[("NGC2403", "nfw", s.FLOOR)].stellar == pytest.approx(0.502, abs=2e-3)
    assert fits[("NGC2403", "iso", s.FLOOR)].stellar == pytest.approx(0.836, abs=2e-3)
    # Y and the halo's density are anticorrelated in every free fit.
    for name in ("NGC3198", "NGC2403", "NGC2841", "NGC2903"):
        for halo in ("nfw", "iso"):
            corr = fits[(name, halo, 0.0)].fit.correlation[0, 2]
            assert corr < -0.8, (name, halo)
    # The core's profile in Y has two valleys for NGC 2403: a halo-dominated
    # disk and one near the maximum disk, the second the deeper.
    g = sample["NGC2403"]
    chi2 = s.stellar_profile(g, "iso", s.PROFILE_VALUES)
    inner = (np.diff(np.sign(np.diff(chi2))) > 0).nonzero()[0] + 1
    assert [round(float(s.PROFILE_VALUES[k]), 2) for k in inner] == [0.08, 0.76]
    assert chi2[inner[1]] < chi2[inner[0]]


def test_the_bar_of_ngc2903_breaks_the_model(sample, result):
    g = sample["NGC2903"]
    for halo in ("nfw", "iso"):
        m = result["fits"][("NGC2903", halo, 0.0)]
        assert m.reduced_chi2 > 5
        # The first two points lie far below every fitted curve.
        below = (m.total(g) - g.v_obs)[:2] / g.v_err[:2]
        assert np.all(below > 7)
    # Its maximum disk is set by those points and is far below the fits' Y.
    assert result["maximum_disk"]["NGC2903"] < 0.1
