"""The SRM 660c sample parses into what its card says, the numbers of its
dossier follow from it, and the one-time CIF conversion is faithful (ADR 007
and its addendum of #417).
"""

import hashlib
import importlib.util
import zipfile

import numpy as np
import pytest

from pbc.data import REPO_ROOT, SAMPLES_DIR
from pbc.data.card import load_card
from pbc.data.reference import srm660c as lab6

DIR = SAMPLES_DIR / "nist-srm660c-lab6"
CARD = load_card(REPO_ROOT / "data/registry/nist-srm660c-lab6.yaml")
SCRIPT = REPO_ROOT / "tools/datasets/srm660c_cif_to_csv.py"


def converter():
    spec = importlib.util.spec_from_file_location(SCRIPT.stem, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def patterns():
    return lab6.load(DIR)


@pytest.fixture(scope="module")
def specimens():
    return lab6.read_specimens(DIR / "specimens.csv")


@pytest.fixture(scope="module")
def analyses(patterns):
    return {
        s: (lab6.analyse_measured(p), lab6.analyse_model(p))
        for s, p in patterns.items()
    }


def test_srm660c_sample_parses(patterns, specimens):
    # Field names and shapes: 20 specimens, two from each of ten bottles,
    # 5332 rows each of 2theta, intensity, weight, and NIST's model.
    assert sorted(patterns) == sorted(lab6.SPECIMENS) and len(patterns) == 20
    assert sorted(specimens) == sorted(lab6.SPECIMENS)
    for name, p in patterns.items():
        assert p.two_theta.shape == p.intensity.shape == p.weight.shape == (5332,)
        assert p.calc.shape == (5332,)
        # Masks: none; every value is a finite number, weights positive,
        # count rates non-negative.
        for column in (p.two_theta, p.intensity, p.weight, p.calc):
            assert np.isfinite(column).all()
        assert (p.weight > 0).all() and (p.intensity >= 0).all()
        assert (p.calc > 0).all()
        # Units and cadence: 2theta in degrees from 20.3 to 150.908, rising,
        # in 24 scan windows (one per reflection), steps 0.008 to 0.016
        # within a window.
        assert p.two_theta[0] == pytest.approx(20.3, abs=1e-3)
        assert p.two_theta[-1] == pytest.approx(150.908, abs=2e-3)
        parts = lab6.windows(p.two_theta)
        assert len(parts) == 24, name
        steps = np.concatenate([np.diff(p.two_theta[ix]) for ix in parts])
        assert steps.min() > 0.0075 and steps.max() < 0.0165
        # Each window holds one reflection: its maximum lies within 0.07
        # degrees of the certificate's computed position (Table 1).
        tops = [p.two_theta[ix][np.argmax(p.intensity[ix])] for ix in parts]
        np.testing.assert_allclose(tops, lab6.TABLE1_TWO_THETA, atol=0.07)
        # The weights are Poisson weights tau^2 / (N + 1) of N counts in a
        # counting time tau, so intensity = N / tau and N is a whole number.
        tau = (
            p.weight * p.intensity
            + np.sqrt((p.weight * p.intensity) ** 2 + 4 * p.weight)
        ) / 2
        assert tau.min() > 0.99 and tau.max() < 50
        # NIST's model follows the measurement: chi-square per point below 2.
        assert np.mean(((p.intensity - p.calc) / p.sigma) ** 2) < 2.0
    for row in specimens.values():
        assert row["temperature_c"] == 20.85
        assert row["points"] == 5332
        assert 4.156777 < row["cell_length_a_angstrom"] < 4.156803
        assert -0.14 < row["vertical_displacement_mm"] < -0.039


def test_the_samples_are_the_conversion_outputs():
    for sample in CARD["samples"]:
        data = (DIR / sample["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sample["sha256"]
        assert len(data) == sample["bytes"]
    (download,) = CARD["downloads"]
    assert download["digest"] == converter().INPUT_SHA256
    assert download["filename"] == converter().ZIP_NAME
    # Every specimen file names the pinned zip in its first line.
    for name in lab6.SPECIMENS:
        first = (DIR / f"660c_{name}.csv").read_text().splitlines()[0]
        assert converter().INPUT_SHA256 in first


def test_bragg_law_indexes_the_reflections(analyses):
    measured = {s: a for s, (a, _) in analyses.items()}
    peaks = np.array([[p.two_theta for p in measured[s].peaks] for s in lab6.SPECIMENS])
    # The fitted K-alpha-1 positions lie within 0.04 degrees of the
    # certificate's information values; they are higher by 0.006 to 0.038
    # degrees above 30 degrees (the specimen displacement, the temperature).
    offset = peaks.mean(0) - np.array(lab6.TABLE1_TWO_THETA)
    assert np.abs(offset).max() < 0.04
    # A single reflection gives a within 0.0067 angstrom of the certified
    # value (100) down to 0.0005 (511): the error of the specimen
    # displacement falls with the angle, which the extrapolation uses.
    a = np.array([[p.a for p in measured[s].peaks] for s in lab6.SPECIMENS])
    worst = np.abs(a - lab6.CERTIFIED_A).max(0)
    assert worst[0] == pytest.approx(0.0067, abs=1e-4)
    assert worst[-1] == pytest.approx(0.0005, abs=1e-4)
    assert (np.diff(worst) < 0).all()
    # d = lambda / (2 sin theta) and a = d sqrt(h^2 + k^2 + l^2).
    p = measured["100a"].peaks[-1]
    assert p.hkl == (5, 1, 1)
    assert p.a == pytest.approx(
        lab6.WAVELENGTH / (2 * np.sin(np.radians(p.two_theta / 2))) * np.sqrt(27)
    )


def test_the_lattice_parameter_and_the_bias_of_the_method(analyses, specimens):
    measured = np.array([analyses[s][0].a0 for s in lab6.SPECIMENS])
    model = np.array([analyses[s][1].a0 for s in lab6.SPECIMENS])
    nist = np.array([specimens[s]["cell_length_a_angstrom"] for s in lab6.SPECIMENS])
    mean, sd, sem = lab6.summary(measured)
    assert mean == pytest.approx(4.156485, abs=1e-6)
    assert sd == pytest.approx(0.0000136, abs=1e-6)
    assert sem == pytest.approx(0.0000030, abs=2e-7)
    assert lab6.summary(model)[0] == pytest.approx(4.156480, abs=1e-6)
    assert nist.mean() == pytest.approx(4.156789, abs=1e-6)
    # The simple method misses NIST's own model by -74 ppm, and the
    # measurement by -73 ppm: the gap is the method's, not the data's.
    bias = (model.mean() - nist.mean()) / nist.mean() * 1e6
    assert bias == pytest.approx(-74.4, abs=0.5)
    assert (mean - nist.mean()) / nist.mean() * 1e6 == pytest.approx(-73.2, abs=0.5)
    # Measured minus model by the same method: +1.1 ppm, far below the
    # certificate's expanded uncertainty (19 ppm).
    difference = measured - model
    assert difference.mean() / model.mean() * 1e6 == pytest.approx(1.13, abs=0.1)
    relative_u = lab6.CERTIFIED_U / lab6.CERTIFIED_A * 1e6
    assert relative_u == pytest.approx(19.2, abs=0.1)
    # Against the certified value (22.5 degC): -82 ppm, 4.3 times U. NIST's
    # own in-file values (20.85 degC) are 8.9 ppm below it.
    assert (mean - lab6.CERTIFIED_A) / lab6.CERTIFIED_U == pytest.approx(
        -4.27, abs=0.02
    )
    assert (nist.mean() - lab6.CERTIFIED_A) / lab6.CERTIFIED_A * 1e6 == pytest.approx(
        -8.86, abs=0.05
    )
    # The slope of each Nelson-Riley line follows the specimen displacement
    # of the CIF: the extrapolation removes it.
    slope = np.array([analyses[s][0].slope for s in lab6.SPECIMENS])
    shift = np.array([specimens[s]["vertical_displacement_mm"] for s in lab6.SPECIMENS])
    assert np.corrcoef(slope, shift)[0, 1] > 0.999


def test_the_kalpha2_doublet(analyses):
    ratio = np.array([analyses[s][0].ratio for s in lab6.SPECIMENS])
    share = np.array([analyses[s][0].share for s in lab6.SPECIMENS])
    assert ratio.mean() == pytest.approx(1.0024799, abs=2e-7)
    assert ratio.std(ddof=1) < 2e-6
    assert ratio.mean() * lab6.WAVELENGTH == pytest.approx(1.544413, abs=1e-6)
    assert share.mean() == pytest.approx(0.515, abs=0.002)
    model = np.array([analyses[s][1].ratio for s in lab6.SPECIMENS])
    assert model.mean() == pytest.approx(1.0024812, abs=2e-7)


def test_the_pseudo_voigt_and_the_nelson_riley_function():
    assert lab6.pseudo_voigt(1.0, 1.0, 0.1, 0.3) == pytest.approx(1.0)
    for eta in (0.0, 0.5, 1.0):
        assert lab6.pseudo_voigt(1.05, 1.0, 0.1, eta) == pytest.approx(0.5)
    assert lab6.nelson_riley(np.pi / 2) == pytest.approx(0.0, abs=1e-15)
    assert lab6.kalpha2(90.0, 1.0) == pytest.approx(90.0)


def _cif(specimen: str, rows, calc_rows=None) -> str:
    stem = f"660_cert_cif_mosaic_consensus_{specimen}"
    calc_rows = rows if calc_rows is None else calc_rows

    def loop(rs):
        return (
            "loop_\n  _pd_proc_2theta_corrected\n  _pd_proc_intensity_total\n"
            "  _pd_proc_ls_weight\n"
            + "".join(f"         {' '.join(r)}  \n" for r in rs)
        )

    return (
        "#\ndata_citation_NIST\n\nloop_\n  _citation_id\n  _citation_title\n"
        "         primary   'A title'\n; a text field\n_with a tag-like line\n;\n"
        "data_cell_LaB6_660c\n\n_cell_length_a                          4.156780\n"
        f"data_pd_spec_{stem}\n\n_pd_spec_temperature                    20.85\n"
        "_pd_spec_vertical_displacement_mm       -0.07877\n"
        f"data_pd_proc_{stem}_meas\n\n_pd_proc_number_of_points {len(rows)}\n"
        + loop(rows)
        + f"data_pd_proc_{stem}_calc\n\n_pd_proc_number_of_points {len(calc_rows)}\n"
        + loop(calc_rows)
    )


def _zip(path, cifs):
    with zipfile.ZipFile(path, "w") as archive:
        for specimen, text in cifs.items():
            archive.writestr(f"660_cert_cif_mosaic_consensus_{specimen}.cif", text)
        archive.writestr("__MACOSX/._x", b"\x00")


def test_the_conversion_keeps_every_row_and_token(tmp_path):
    tool = converter()
    rows = [["20.300", "19.00", "1.03e-01"], ["20.310", "10.50", "1.81e-01"]]
    calc = [["20.300", "11.63", "1.72e-01"], ["20.310", "11.64", "1.71e-01"]]
    source = tmp_path / "srm.zip"
    _zip(source, {s: _cif(s, rows, calc) for s in tool.SPECIMENS})
    out = tmp_path / "out"
    tool.convert(source, out, check_input=False)
    lines = (out / "660c_100a.csv").read_text().splitlines()
    assert lines[3:] == [
        "two_theta,intensity,weight,calc_intensity",
        "20.300,19.00,1.03e-01,11.63",
        "20.310,10.50,1.81e-01,11.64",
    ]
    pattern = lab6.read_pattern(out / "660c_100a.csv")
    assert pattern.weight.tolist() == [0.103, 0.181]
    table = lab6.read_specimens(out / "specimens.csv")
    assert table["1000b"] == {
        "temperature_c": 20.85,
        "vertical_displacement_mm": -0.07877,
        "cell_length_a_angstrom": 4.15678,
        "points": 2.0,
    }
    # The pinned check refuses a file that is not the inspected zip.
    with pytest.raises(ValueError, match="not the pinned input"):
        tool.convert(source, out)


def test_the_conversion_refuses_another_layout(tmp_path):
    tool = converter()
    rows = [["20.300", "19.00", "1.03e-01"], ["20.310", "10.50", "1.81e-01"]]
    # Another 2theta in the model block.
    shifted = [["20.300", "11.63", "1.0"], ["20.320", "11.64", "1.0"]]
    cifs = {s: _cif(s, rows) for s in tool.SPECIMENS}
    cifs["500a"] = _cif("500a", rows, shifted)
    _zip(tmp_path / "a.zip", cifs)
    with pytest.raises(ValueError, match="differ"):
        tool.convert(tmp_path / "a.zip", tmp_path / "a", check_input=False)
    # A missing specimen.
    del cifs["500a"]
    _zip(tmp_path / "b.zip", cifs)
    with pytest.raises(ValueError, match="members"):
        tool.convert(tmp_path / "b.zip", tmp_path / "b", check_input=False)
    # Fewer rows than declared.
    cifs = {s: _cif(s, rows) for s in tool.SPECIMENS}
    cifs["100a"] = cifs["100a"].replace("number_of_points 2", "number_of_points 3", 1)
    _zip(tmp_path / "c.zip", cifs)
    with pytest.raises(ValueError, match="declared 3"):
        tool.convert(tmp_path / "c.zip", tmp_path / "c", check_input=False)
