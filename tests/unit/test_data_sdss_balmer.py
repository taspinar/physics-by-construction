"""The SDSS Balmer spectrum: the conversion keeps every value, and the
reference analysis recovers the Rydberg constant it is given (ADR 007;
docs/datasets/sdss-balmer-spectrum.md).

The card's decision is ``defer`` (the rights are not settled), so no sample is
committed and the numbers of the dossier are not asserted here: every test
runs on a spectrum this file writes, through the same chain the dossier used
(a FITS file, the conversion, the reader, the analysis, the figure).
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import yaml

from pbc.data.card import validate_card
from pbc.data.plotting import check_figure, figure_status
from pbc.data.reference import sdss_balmer

ROOT = Path(__file__).parents[2]
CONVERTER = ROOT / "tools/datasets/sdss_spec_to_csv.py"
CARD = ROOT / "data/registry/sdss-balmer-spectrum.yaml"


def converter():
    spec = importlib.util.spec_from_file_location("sdss_spec_to_csv", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A small FITS file in the layout of an SDSS spec-lite file.


def card(key: str, value) -> bytes:
    if isinstance(value, str):
        text = f"'{value:<8}'"
    elif isinstance(value, bool):
        text = f"{'T' if value else 'F':>20}"
    else:
        text = f"{value:>20}"
    return f"{key:<8}= {text}".ljust(80).encode("ascii")


def block(raw: bytes, fill: bytes = b" ") -> bytes:
    return raw.ljust(-(-len(raw) // 2880) * 2880, fill)


def header(cards: list[bytes]) -> bytes:
    return block(b"".join(cards) + b"END".ljust(80))


def table(rows: np.ndarray, forms: list[tuple[str, str]], name: str) -> bytes:
    cards = [
        card("XTENSION", "BINTABLE"),
        card("BITPIX", 8),
        card("NAXIS", 2),
        card("NAXIS1", rows.dtype.itemsize),
        card("NAXIS2", rows.size),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("TFIELDS", len(forms)),
    ]
    for k, (column, form) in enumerate(forms, 1):
        cards += [card(f"TTYPE{k}", column), card(f"TFORM{k}", form)]
    cards.append(card("EXTNAME", name))
    return header(cards) + block(rows.tobytes(), b"\0")


COADD = np.dtype(
    [
        ("flux", ">f4"),
        ("loglam", ">f4"),
        ("ivar", ">f4"),
        ("and_mask", ">i4"),
        ("or_mask", ">i4"),
        ("wdisp", ">f4"),
        ("sky", ">f4"),
        ("model", ">f4"),
    ]
)
COADD_FORMS = [
    ("flux", "E"),
    ("loglam", "E"),
    ("ivar", "E"),
    ("and_mask", "J"),
    ("or_mask", "J"),
    ("wdisp", "E"),
    ("sky", "E"),
    ("model", "E"),
]
SPECOBJ = np.dtype(
    [
        ("CLASS", "S1", (6,)),
        ("SUBCLASS", "S1", (21,)),
        ("Z", ">f4"),
        ("Z_ERR", ">f4"),
        ("ZWARNING", ">i4"),
    ]
)


def small_fits(coadd: np.ndarray, *, vacuum: bool = True) -> bytes:
    primary = header(
        [
            card("SIMPLE", True),
            card("BITPIX", 8),
            card("NAXIS", 0),
            card("EXTEND", True),
            card("VACUUM", vacuum),
            card("BUNIT", "1E-17 erg/cm^2/s/Ang"),
            card("HELIO_RV", 10.5664821629),
        ]
    )
    specobj = np.zeros(1, dtype=SPECOBJ)
    specobj["CLASS"][0] = np.frombuffer(b"GALAXY", dtype="S1")
    specobj["SUBCLASS"][0] = np.frombuffer(b"STARBURST".ljust(21), dtype="S1")
    specobj["Z"], specobj["Z_ERR"], specobj["ZWARNING"] = 0.01499, 6e-6, 0
    return (
        primary
        + table(coadd, COADD_FORMS, "COADD")
        + table(
            specobj,
            [
                ("CLASS", "6A"),
                ("SUBCLASS", "21A"),
                ("Z", "E"),
                ("Z_ERR", "E"),
                ("ZWARNING", "J"),
            ],
            "SPECOBJ",
        )
    )


# A synthetic spectrum with known physics.

R_TRUE = 10968000.0  # 1/m, the Rydberg constant the synthetic lines obey
Z0, Z1 = 0.015, 1.5e-5  # z(lambda) = Z0 + Z1 (lambda - 5500) / 1000
NOISE = 2.0  # flux units per pixel


def observed(rest: float, z0: float = Z0, z1: float = Z1) -> float:
    """lambda_obs = rest (1 + z(lambda_obs)), solved by iteration."""
    lam = rest * (1 + z0)
    for _ in range(50):
        lam = rest * (1 + z0 + z1 * (lam - 5500.0) / 1000.0)
    return lam


def synthetic_coadd(seed: int = 7, z1: float = Z1) -> np.ndarray:
    """A continuum of 100 with every line of the analysis as a Gaussian of
    sigma 75 km/s, averaged over each pixel by fine sampling (not by the
    module's own pixel_gaussian), plus Gaussian noise of NOISE."""
    loglam = (3.5801 + 1e-4 * np.arange(3843)).astype(np.float32)
    lam = 10.0 ** loglam.astype(float)
    rest = dict(sdss_balmer.FORBIDDEN)
    for n, name in sdss_balmer.BALMER.items():
        rest[name] = 1e10 / (R_TRUE * (0.25 - 1 / n**2))
    fine = np.linspace(-0.5, 0.5, 41)
    sub = 10.0 ** (loglam.astype(float)[:, None] + 1e-4 * fine[None, :])
    flux = np.full(lam.shape, 100.0)
    for name, wavelength in rest.items():
        centre = observed(wavelength, z1=z1)
        sigma = centre * 75 / sdss_balmer.C_KMS
        # [O III] 5008 the brightest line, as in the real spectrum, so that
        # rough_z finds it first
        height = {"H alpha": 3000.0, "[O III] 5008": 4000.0}.get(name, 800.0)
        flux += height * np.exp(-0.5 * ((sub - centre) / sigma) ** 2).mean(axis=1)
    rng = np.random.default_rng(seed)
    flux += rng.normal(0.0, NOISE, flux.shape)
    coadd = np.zeros(loglam.size, dtype=COADD)
    coadd["flux"], coadd["loglam"] = flux, loglam
    coadd["ivar"] = 1 / NOISE**2
    coadd["wdisp"] = 0.83
    coadd["and_mask"][100] = 8388608  # one BRIGHTSKY pixel, far from any line
    return coadd


@pytest.fixture(scope="module")
def sample_dir(tmp_path_factory):
    """The synthetic spectrum through the conversion, as the sample would be."""
    directory = tmp_path_factory.mktemp("sdss")
    source = directory / "synthetic.fits"
    source.write_bytes(small_fits(synthetic_coadd()))
    converter().convert(source, directory / sdss_balmer.FILE, check_input=False)
    return directory


@pytest.fixture(scope="module")
def analysis(sample_dir):
    return sdss_balmer.analyse(sdss_balmer.load(sample_dir))


# The conversion.


def test_the_conversion_keeps_every_row_and_value(tmp_path):
    coadd = synthetic_coadd()[:6]
    coadd["flux"][2] = 1.0e-7
    coadd["ivar"][3] = 0.0  # a pixel the pipeline rejected
    source = tmp_path / "small.fits"
    source.write_bytes(small_fits(coadd))
    out = tmp_path / "small.csv"
    tool = converter()
    with pytest.raises(ValueError, match="pinned input"):
        tool.convert(source, out)
    tool.convert(source, out, check_input=False)
    lines = out.read_text().splitlines()
    assert lines[2] == "# units: " + ", ".join(
        f"{name} [{unit}]" for name, unit in sdss_balmer.UNITS.items()
    )
    assert lines[3] == (
        "# pipeline (SPECOBJ): CLASS GALAXY, SUBCLASS STARBURST, Z 0.01499,"
        " Z_ERR 0.000006, ZWARNING 0; HELIO_RV 10.5664821629 km/s applied"
    )
    assert lines[4] == ",".join(sdss_balmer.FIELDS)
    values = [line.split(",") for line in lines[5:]]
    assert len(values) == coadd.size
    for row, text in zip(coadd, values, strict=True):
        for name, cell in zip(("loglam", "flux", "ivar"), text[:3], strict=True):
            assert np.float32(float(cell)) == row[name], name
        assert int(text[3]) == row["and_mask"]
        assert np.float32(float(text[4])) == row["wdisp"]
    # The reference module reads what the conversion writes.
    spectrum = sdss_balmer.read_spectrum(out)
    assert spectrum.flux.shape == (6,)
    assert sdss_balmer.pipeline_value(spectrum, "SUBCLASS") == "STARBURST"
    assert sdss_balmer.good(spectrum).tolist() == [1, 1, 1, 0, 1, 1]


def test_air_wavelengths_and_unpinned_files_are_refused(tmp_path):
    source = tmp_path / "air.fits"
    source.write_bytes(small_fits(synthetic_coadd()[:4], vacuum=False))
    with pytest.raises(ValueError, match="VACUUM"):
        converter().convert(source, tmp_path / "air.csv", check_input=False)


def test_the_reader_refuses_other_columns(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text("# x\nloglam,flux,ivar,or_mask,wdisp\n3.6,1,1,0,1\n")
    with pytest.raises(ValueError, match="columns"):
        sdss_balmer.read_spectrum(path)


def test_the_card_pins_the_file_the_converter_pins():
    card = yaml.safe_load(CARD.read_text())
    assert validate_card(card, "sdss-balmer-spectrum") == []
    tool = converter()
    (download,) = card["downloads"]
    assert download["filename"] == tool.INPUT_NAME
    assert download["algorithm"] == "sha256"
    assert download["digest"] == tool.INPUT_SHA256
    assert tool.INPUT_SHA1 in download["digest_source"]
    # Deferred: the rights are not settled, so nothing is committed.
    assert card["decision"]["value"] == "defer"
    assert not card.get("samples")
    assert not (ROOT / "data/samples/sdss-balmer-spectrum").exists()


# The line model.


def test_the_pixel_average_of_a_gaussian_keeps_its_area_and_its_peak():
    lo = 6600 + 0.1 * np.arange(400)
    values = sdss_balmer.pixel_gaussian(lo, lo + 0.1, 5.0, 6620.0, 1.5)
    assert np.sum(values * 0.1) == pytest.approx(5.0 * 1.5 * np.sqrt(2 * np.pi))
    narrow = sdss_balmer.pixel_gaussian(6619.9995, 6620.0005, 5.0, 6620.0, 1.5)
    assert narrow == pytest.approx(5.0, rel=1e-6)


def test_the_bohr_formula_misses_laboratory_hydrogen_by_its_fine_structure():
    """CODATA 2018 gives R_H = R_inf / (1 + m_e/m_p) = 10967758.34 1/m; the
    laboratory Balmer wavelengths, centroids of fine-structure multiplets,
    give 1.12e-5 more by the Bohr formula, slightly more for H alpha than
    for H delta."""
    r_h = sdss_balmer.R_H
    assert r_h == pytest.approx(10967758.34, abs=0.01)
    lab = sdss_balmer.bohr_lab_rydberg()
    assert lab / sdss_balmer.R_H - 1 == pytest.approx(1.123e-5, abs=0.002e-5)
    per_line = {
        n: 1e10 / (wavelength * sdss_balmer.balmer_term(n))
        for n, wavelength in sdss_balmer.BALMER_LAB.items()
    }
    assert per_line[3] > per_line[4] > per_line[5] > per_line[6]


# The analysis, on the synthetic spectrum.


def test_every_line_is_found_where_it_was_put(analysis):
    for name, line in analysis.lines.items():
        if name in sdss_balmer.FORBIDDEN:
            rest = sdss_balmer.FORBIDDEN[name]
        else:
            n = next(k for k, v in sdss_balmer.BALMER.items() if v == name)
            rest = 1e10 / (R_TRUE * sdss_balmer.balmer_term(n))
        assert abs(line.centre - observed(rest)) < 4 * line.error, name
        assert line.sigma == pytest.approx(line.centre * 75 / 299792.458, rel=0.05)
    for fit in analysis.fits:
        assert fit.result.ok, (fit.names, fit.result.warnings)


def test_the_calibration_recovers_the_redshift_and_its_slope(analysis):
    cal = analysis.rydberg.calibration
    z0_err, z1_err = np.sqrt(np.diag(cal.covariance))
    assert cal.params[0] == pytest.approx(Z0, abs=4 * z0_err)
    assert cal.params[1] == pytest.approx(Z1, abs=4 * z1_err)
    assert cal.chi2 / cal.dof < 3


def test_the_balmer_lines_give_back_the_rydberg_constant(analysis):
    """R from the calibrated rest wavelengths equals the R the lines were
    made with, within its error, and the four lines agree (the 1/n^2 law)."""
    ryd = analysis.rydberg
    assert ryd.levels == (3, 4, 5, 6)
    assert abs(ryd.r - R_TRUE) < 3 * ryd.r_err
    # 1/m: eight noise seeds give 2.9 to 4.3, and R within 1.4 errors
    assert ryd.r_err < 6
    assert ryd.chi2 < 16  # 3 degrees of freedom: p = 0.001
    for n in ryd.levels:
        assert abs(ryd.residual_kms(n)) < 1


def test_one_redshift_for_all_lines_is_biased_when_the_scale_has_a_slope(
    analysis,
):
    """The comparison of the dossier: with a slope in z(lambda) and one z,
    the hydrogen lines no longer agree, the bluer the further off."""
    flat = sdss_balmer.rydberg(analysis.lines, slope=False)
    assert flat.chi2 > 10 * max(analysis.rydberg.chi2, 1.0)
    values = [flat.per_line[n] for n in flat.levels]
    assert values == sorted(values)  # rising from H alpha to H delta


def test_the_redshift_and_r_are_degenerate_without_the_forbidden_lines(
    sample_dir,
):
    """Only (1 + z) / R is in the hydrogen lines: shifting every forbidden
    rest wavelength by a factor shifts R by the same factor."""
    spectrum = sdss_balmer.load(sample_dir)
    lines, _ = sdss_balmer.fit_lines(spectrum)
    base = sdss_balmer.rydberg(lines, slope=False).r
    factor = 1 + 1e-4
    shifted = {
        name: (
            sdss_balmer.Line(
                line.name,
                line.centre * factor,
                line.centre_err * factor,
                line.sigma,
                line.flux,
                line.reduced_chi2,
                line.dof,
            )
            if name in sdss_balmer.FORBIDDEN
            else line
        )
        for name, line in lines.items()
    }
    # Forbidden lines observed 1e-4 redder: z rises, so R rises with it.
    assert sdss_balmer.rydberg(shifted, slope=False).r / base == pytest.approx(
        factor, rel=2e-6
    )


def test_the_fit_does_not_depend_on_the_starting_redshift(sample_dir):
    spectrum = sdss_balmer.load(sample_dir)
    start = sdss_balmer.rough_z(spectrum)
    base, _ = sdss_balmer.fit_lines(spectrum, z_start=start)
    for dz in (-3e-4, 3e-4):  # 90 km/s, about a pixel and a half
        moved, _ = sdss_balmer.fit_lines(spectrum, z_start=start + dz)
        for name in base:
            assert moved[name].centre == pytest.approx(base[name].centre, abs=1e-6)


def test_the_sensitivity_variants_run_and_name_their_choices(sample_dir):
    variants = sdss_balmer.sensitivity(sdss_balmer.load(sample_dir))
    assert set(variants) == set(sdss_balmer.VARIANTS)
    assert variants["no H delta"].levels == (3, 4, 5)
    assert "[Ne III] 3870" not in variants["no [Ne III]"].calibration.z
    assert variants["one z"].calibration.params.size == 1


def test_the_reference_figure_is_processed_and_follows_the_conventions(
    sample_dir,
):
    figure = sdss_balmer.make_figure(sample_dir)
    assert figure_status(figure) == "processed"
    assert check_figure(figure) == []
    text = " ".join(t.get_text() for t in figure.texts)
    assert "Sloan Digital Sky Survey" in text and "not part of the record" in text


def test_the_dossier_states_the_status_of_its_figure_and_the_decision():
    text = (ROOT / "docs/datasets/sdss-balmer-spectrum.md").read_text()
    text = text.replace("**", "")
    assert "Status label: processed" in text
    assert "Decision: defer" in text
