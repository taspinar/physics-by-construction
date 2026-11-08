"""The TESS WASP-18 sample parses into what its card says, the conversion that
wrote it keeps every value, and the reference analysis gives the numbers of
the dossier (ADR 007; docs/datasets/tess-exoplanet-light-curves.md).
"""

import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from pbc.astrophysics import transit
from pbc.data import SAMPLES_DIR
from pbc.data.reference import tess_wasp18

TESS = SAMPLES_DIR / "tess-exoplanet-light-curves"
ROOT = Path(__file__).parents[2]
CONVERTER = ROOT / "tools/datasets/tess_lc_to_csv.py"


def converter():
    spec = importlib.util.spec_from_file_location("tess_lc_to_csv", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def light_curve():
    return tess_wasp18.load(TESS)


@pytest.fixture(scope="module")
def analysis(light_curve):
    return tess_wasp18.analyse(light_curve)


# The sample.


def test_tess_wasp18_sample_parses(light_curve):
    lc = light_curve
    # Provenance: the header names the FITS file and its pinned checksum.
    assert lc.header[0] == (
        "# source: tess2020238165205-s0029-0000000100100827-0193-s_lc.fits"
        " (sha256 c89434e50db863e589c9321cf29c93e449ef1526f1a9db19552446b721fd0949)"
    )
    # Field names and units, as the FITS header gives them.
    names = (TESS / tess_wasp18.FILE).read_text().splitlines()[len(lc.header)]
    assert tuple(names.split(",")) == tess_wasp18.FIELDS
    assert lc.header[2] == "# units: " + ", ".join(
        f"{name.upper()} [{unit}]" for name, unit in tess_wasp18.UNITS.items()
    )
    # Shapes: every row of the LIGHTCURVE table, 18,864 cadences.
    for column in (lc.time, lc.flux, lc.flux_err, lc.quality):
        assert column.shape == (18864,)
    assert lc.quality.dtype.kind == "i"
    # Cadence: 120 s between consecutive time stamps, 2088.24 to 2114.44.
    finite = np.isfinite(lc.time)
    steps = np.diff(lc.time[finite]) * 86400
    assert np.median(steps) == pytest.approx(tess_wasp18.CADENCE, abs=0.01)
    assert np.all(steps > 119.99)
    assert lc.time[finite][[0, -1]] == pytest.approx([2088.23766, 2114.43656])
    # Masks: 681 cadences without a time, all flagged 8; 4,503 without a
    # PDCSAP value (flux and error missing together); 14,358 good cadences.
    assert (~finite).sum() == 681
    assert set(lc.quality[~finite]) == {8}
    assert np.isnan(lc.flux).sum() == 4503
    np.testing.assert_array_equal(np.isnan(lc.flux), np.isnan(lc.flux_err))
    assert tess_wasp18.good(lc).sum() == 14358
    # Units: e-/s of an 8.8 mag star, errors of about 540 ppm per cadence.
    good = tess_wasp18.good(lc)
    assert np.median(lc.flux[good]) == pytest.approx(47954.6, abs=0.1)
    ratio = np.median(lc.flux_err[good] / lc.flux[good])
    assert ratio == pytest.approx(540e-6, rel=0.01)


def test_the_reader_refuses_other_columns(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text("# x\ntime,sap_flux,sap_flux_err,quality\n1,2,3,0\n")
    with pytest.raises(ValueError, match="columns"):
        tess_wasp18.read_light_curve(path)


# The conversion, on a small FITS file written here.


def card(key: str, value) -> bytes:
    if isinstance(value, str):
        text = f"'{value:<8}'"
    elif isinstance(value, bool):
        text = f"{'T' if value else 'F':>20}"
    else:
        text = f"{value:>20}"
    return f"{key:<8}= {text}".ljust(80).encode("ascii")


def header(cards: list[bytes]) -> bytes:
    raw = b"".join(cards) + b"END".ljust(80)
    return raw.ljust(-(-len(raw) // 2880) * 2880, b" ")


def small_fits(rows: np.ndarray, extra: list[bytes] = ()) -> bytes:
    columns = [
        ("TIME", "D", "BJD - 2457000, days"),
        ("SAP_FLUX", "E", "e-/s"),
        ("PDCSAP_FLUX", "E", "e-/s"),
        ("PDCSAP_FLUX_ERR", "E", "e-/s"),
        ("QUALITY", "J", ""),
    ]
    primary = header([card("SIMPLE", True), card("BITPIX", 8), card("NAXIS", 0)])
    cards = [
        card("XTENSION", "BINTABLE"),
        card("BITPIX", 8),
        card("NAXIS", 2),
        card("NAXIS1", rows.dtype.itemsize),
        card("NAXIS2", rows.size),
        card("PCOUNT", 0),
        card("GCOUNT", 1),
        card("TFIELDS", len(columns)),
        *extra,
    ]
    for k, (name, form, unit) in enumerate(columns, 1):
        cards += [card(f"TTYPE{k}", name), card(f"TFORM{k}", form)]
        if unit:
            cards.append(card(f"TUNIT{k}", unit))
    data = rows.tobytes()
    data = data.ljust(-(-len(data) // 2880) * 2880, b"\0")
    return primary + header(cards) + data


ROW = np.dtype(
    [
        ("TIME", ">f8"),
        ("SAP_FLUX", ">f4"),
        ("PDCSAP_FLUX", ">f4"),
        ("PDCSAP_FLUX_ERR", ">f4"),
        ("QUALITY", ">i4"),
    ]
)


def test_the_conversion_keeps_every_row_and_value(tmp_path):
    rows = np.array(
        [
            (2088.237658962213, 1.0, np.nan, np.nan, 168),
            (2090.1234567890123, 2.0, 47954.594, 25.890612, 0),
            (np.nan, 3.0, np.nan, np.nan, 8),
            (2101.0, 4.0, 1.0e-7, 3.4028235e38, 512),
        ],
        dtype=ROW,
    )
    source = tmp_path / "small.fits"
    source.write_bytes(small_fits(rows))
    out = tmp_path / "small.csv"
    tool = converter()
    with pytest.raises(ValueError, match="pinned input"):
        tool.convert(source, out)
    tool.convert(source, out, check_input=False)
    lines = out.read_text().splitlines()
    assert lines[2] == (
        "# units: TIME [BJD - 2457000, days], PDCSAP_FLUX [e-/s],"
        " PDCSAP_FLUX_ERR [e-/s], QUALITY [none]"
    )
    assert lines[3] == "time,pdcsap_flux,pdcsap_flux_err,quality"
    values = [line.split(",") for line in lines[4:]]
    assert len(values) == rows.size
    for row, text in zip(rows, values, strict=True):
        for name, kind, cell in zip(
            ("TIME", "PDCSAP_FLUX", "PDCSAP_FLUX_ERR"),
            (np.float64, np.float32, np.float32),
            text[:3],
            strict=True,
        ):
            expected = kind(row[name])
            got = kind(float(cell))
            assert (np.isnan(expected) and cell == "nan") or got == expected
        assert int(text[3]) == row["QUALITY"]
    # The reference module reads what the conversion writes.
    lc = tess_wasp18.read_light_curve(out)
    assert lc.quality.tolist() == [168, 0, 8, 512]
    assert np.float32(lc.flux[1]) == np.float32(47954.594)


def test_a_fits_checksum_that_does_not_verify_is_refused(tmp_path):
    rows = np.array([(2090.0, 1.0, 2.0, 0.1, 0)], dtype=ROW)
    tool = converter()
    raw = small_fits(rows, [card("CHECKSUM", "0000000000000000")])
    assert tool.verify_checksums(raw) == ["HDU 1: CHECKSUM does not verify"]
    source = tmp_path / "bad.fits"
    source.write_bytes(raw)
    with pytest.raises(ValueError, match="CHECKSUM"):
        tool.convert(source, tmp_path / "bad.csv", check_input=False)


def test_the_ones_complement_sum_folds_the_carry():
    tool = converter()
    words = np.array([0xFFFFFFFF, 0x00000002], dtype=">u4").tobytes()
    assert tool.ones_complement_sum(words) == 2  # 0x1_0000_0001 folded


def test_the_sample_is_the_output_the_card_pins():
    data = (TESS / tess_wasp18.FILE).read_bytes()
    assert hashlib.sha256(data).hexdigest() == (
        "96cc3d255288b4158386e035358c7a8f4787180931fbe9863acd5113d14ecf11"
    )
    tool = converter()
    assert tool.INPUT_SHA256 in data.decode("ascii").splitlines()[0]


# The model.


def test_the_transit_model_reduces_to_the_ast7_closed_forms():
    d = np.linspace(0.0, 1.2, 25)
    np.testing.assert_allclose(
        tess_wasp18.limb_flux(d, 0.1, 0.0, 0.0),
        transit.uniform_flux(d, 0.1),
        atol=1e-12,
    )
    centre = 1.0 - tess_wasp18.limb_flux(np.array([0.0]), 0.1, 0.3, 0.2)[0]
    assert centre == pytest.approx(transit.central_depth(0.1, 0.3, 0.2), rel=1e-5)
    darkened = transit.grid_flux(
        d,
        0.1,
        transit.quadratic_limb(0.3, 0.2),
        cells=800,
        full=transit.total_flux(0.3, 0.2),
    )
    np.testing.assert_allclose(
        tess_wasp18.limb_flux(d, 0.1, 0.3, 0.2), darkened, atol=3e-6
    )


def test_the_separation_follows_the_circular_orbit():
    period, a, b = 1.0, 3.5, 0.4
    times = np.array([0.0, 0.25, 0.5])
    d = tess_wasp18.separation(times, 0.0, period, a, b)
    assert d[0] == pytest.approx(b)  # mid-transit: the impact parameter
    assert d[1] == pytest.approx(a)  # quadrature
    assert np.isinf(d[2])  # behind the star: no transit


# The analysis of the dossier.


def test_the_dips_give_21_transits_and_a_first_period(light_curve):
    events = tess_wasp18.transit_events(light_curve)
    assert events.size == 21
    _, period = tess_wasp18.linear_ephemeris(events)
    assert period == pytest.approx(0.94145, abs=1e-4)


def test_the_fit_gives_the_geometry_of_the_dossier(analysis):
    """The shape fit identifies p, a, b, u1, u2 on 21 complete transits; its
    values and standard errors (from PDCSAP_FLUX_ERR) and the derived geometry
    are those of the dossier."""
    shape = analysis.shape
    assert shape.ok, shape.warnings
    assert len(analysis.folded.epochs) == 21
    expected = {
        "p": (0.09795, 0.00039),
        "a": (3.437, 0.035),
        "b": (0.400, 0.027),
        "u1": (0.237, 0.047),
        "u2": (0.266, 0.088),
    }
    for name, (value, stderr) in expected.items():
        i = shape.names.index(name)
        assert shape.params[i] == pytest.approx(value, abs=stderr / 10), name
        assert shape.stderr[i] == pytest.approx(stderr, rel=0.05), name
    # The pipeline's errors describe the scatter to within 8 %.
    assert shape.reduced_chi2 == pytest.approx(1.16, abs=0.01)
    assert shape.dof == 4814
    # a, b and the limb darkening trade off against each other.
    corr = shape.correlation
    assert corr[1, 2] == pytest.approx(-0.98, abs=0.01)
    assert corr[3, 4] == pytest.approx(-0.97, abs=0.01)
    g = tess_wasp18.geometry(analysis)
    assert g["depth"] * 1e6 == pytest.approx(10696, abs=5)
    assert g["t14"] == pytest.approx(2.188, abs=0.001)
    assert g["t23"] == pytest.approx(1.720, abs=0.001)
    assert g["ingress"] == pytest.approx(14.04, abs=0.05)
    assert g["inclination"] == pytest.approx(83.32, abs=0.02)
    assert g["density"] == pytest.approx(867, abs=1)


def test_the_mid_times_give_the_ephemeris_and_scatter_more_than_their_errors(
    analysis,
):
    eph = analysis.ephemeris
    assert eph.period == pytest.approx(0.9414504, abs=2e-7)
    assert eph.period_err * 86400 == pytest.approx(0.38, abs=0.01)
    assert eph.t0 == pytest.approx(2098.205325, abs=2e-6)
    assert eph.t0_err * 86400 == pytest.approx(3.1, abs=0.05)
    # chi-square 41.8 for 19 degrees of freedom: the mid-times scatter about
    # 1.5 times more than the white-noise errors say.
    assert eph.dof == 19
    assert eph.chi2 == pytest.approx(41.8, abs=0.1)
    oc = tess_wasp18.o_minus_c(analysis)
    assert np.median(analysis.errors) * 1440 == pytest.approx(0.229, abs=0.002)
    assert np.abs(oc).max() == pytest.approx(0.98, abs=0.01)


def test_the_ephemeris_and_the_shape_are_uncorrelated_in_a_joint_fit(analysis):
    """Why the two are fitted apart without loss: the covariance of the joint
    fit of all seven parameters, from the Jacobian at the final values,
    correlates t0 and P with no shape parameter by more than 0.001 and gives
    the shape the standard errors of the separate fit."""
    folded = analysis.folded
    params = np.array(analysis.params())
    base = tess_wasp18.model_flux(folded.time, *params)
    columns = []
    for k in range(params.size):
        step = 1e-6 * max(abs(params[k]), 1e-3) if k else 1e-6
        moved = params.copy()
        moved[k] += step
        change = tess_wasp18.model_flux(folded.time, *moved) - base
        columns.append(change / step / folded.error)
    jacobian = np.array(columns).T
    covariance = np.linalg.inv(jacobian.T @ jacobian)
    stderr = np.sqrt(np.diag(covariance))
    correlation = covariance / np.outer(stderr, stderr)
    assert np.abs(correlation[:2, 2:]).max() < 0.002
    np.testing.assert_allclose(stderr[2:], analysis.shape.stderr, rtol=0.01)


def test_the_residuals_have_the_scatter_of_the_pipeline_errors(analysis):
    residual = tess_wasp18.residuals(analysis)
    assert residual.size == 4819
    assert residual.std() * 1e6 == pytest.approx(583, abs=1)
    assert np.median(analysis.folded.error) * 1e6 == pytest.approx(540, abs=1)
    assert abs(residual.mean()) < 20e-6


def test_the_normalisation_choices_are_the_sensitivity_table_of_the_dossier(
    light_curve, analysis
):
    """Windows of +-0.12 and +-0.20 d with a parabola move p by about one
    standard error; a straight line instead of the parabola makes the transit
    deeper and longer, because it sits above the curved baseline."""
    variants = tess_wasp18.sensitivity(light_curve)
    rows = {
        key: (*v.shape.params[:3], tess_wasp18.geometry(v)["depth"] * 1e6)
        for key, v in variants.items()
    }
    expected = {
        (0.12, 2): (0.09769, 3.448, 0.394, 10647),
        (0.20, 2): (0.09818, 3.427, 0.405, 10739),
        (0.16, 1): (0.09905, 3.387, 0.426, 10892),
    }
    for key, (p, a, b, depth) in expected.items():
        got_p, got_a, got_b, got_depth = rows[key]
        assert got_p == pytest.approx(p, abs=5e-5), key
        assert got_a == pytest.approx(a, abs=1e-3), key
        assert got_b == pytest.approx(b, abs=1e-3), key
        assert got_depth == pytest.approx(depth, abs=1), key
    p_err = analysis.shape.stderr[0]
    quadratic = [rows[(0.12, 2)][0], analysis.shape.params[0], rows[(0.20, 2)][0]]
    assert max(quadratic) - min(quadratic) == pytest.approx(0.0005, abs=0.00005)
    assert max(quadratic) - min(quadratic) > p_err
    assert rows[(0.16, 1)][3] - tess_wasp18.geometry(analysis)["depth"] * 1e6 > 150


def test_the_tic_values_in_the_header_imply_a_lower_density():
    """The FITS header's TIC values LOGG = 4.25879 and RADIUS = 1.34658 solar
    radii give rho = 3 g / (4 pi G R) = 693 kg/m3, 20 % below the transit's
    867 kg/m3; the header gives no uncertainty for them."""
    g = 10**4.25879 / 100  # m/s2
    radius = 1.34658 * 6.957e8  # m, nominal solar radius
    rho = 3 * g / (4 * np.pi * tess_wasp18.G * radius)
    assert rho == pytest.approx(693, abs=1)
