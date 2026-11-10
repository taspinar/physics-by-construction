"""The TU Delft boundary-layer sample parses into what its card says, and the
reference analysis gives the numbers of the dossier (ADR 007;
docs/datasets/tudelft-turbulent-boundary-layer.md).
"""

import numpy as np
import pytest
import yaml
from scipy.io import savemat, whosmat

from pbc.data import SAMPLES_DIR
from pbc.data.reference import tudelft_boundary_layer as tbl

DIR = SAMPLES_DIR / "tudelft-turbulent-boundary-layer"
CARD = yaml.safe_load(
    (SAMPLES_DIR.parents[0] / "registry" / f"{DIR.name}.yaml").read_text()
)
PIV_POINTS = {"U05": 496, "U10": 496, "U15": 497, "U20": 493}
PTV_POINTS = {"U05": 133, "U10": 132, "U15": 134, "U20": 129}


@pytest.fixture(scope="module")
def data():
    return tbl.load(DIR)


# The sample.


def test_tudelft_sample_parses(data):
    for case in tbl.CASES:
        for technique, fields, n in (
            ("PIV", tbl.PIV_FIELDS, PIV_POINTS[case]),
            ("PTV", tbl.PTV_FIELDS, PTV_POINTS[case]),
        ):
            path = DIR / technique / case / "EXPparam.mat"
            # MAT v5 with top-level doubles, not the struct the readme names.
            assert path.read_bytes().startswith(b"MATLAB 5.0 MAT-file")
            shapes = {name: (shape, kind) for name, shape, kind in whosmat(path)}
            assert sorted(shapes) == sorted(fields)
            for name, (shape, kind) in shapes.items():
                assert kind == "double"
                assert shape in ((1, 1), (n, 1)), (path, name, shape)
        piv, ptv = data[case]
        for column in (piv.y, piv.U, piv.uu, piv.uv, piv.vv):
            assert column.shape == (PIV_POINTS[case],)
            # Masks: none; every value is a number.
            assert np.isfinite(column).all()
        assert ptv.y.shape == ptv.U.shape == (PTV_POINTS[case],)
        assert np.isfinite(ptv.y).all() and np.isfinite(ptv.U).all()
        # Cadence: PIV in equal steps of 0.282 to 0.283 mm up to 1.28 to 1.30
        # delta; PTV unequally spaced from 0.048 mm to about 2.1 mm.
        steps = np.diff(piv.y)
        assert np.ptp(steps) < 1e-6 and 2.81e-4 < steps.mean() < 2.84e-4
        assert 1.28 < piv.y.max() / piv.delta < 1.30
        assert ptv.y.min() == pytest.approx(4.76e-5, abs=1e-7)
        assert 2.0e-3 < ptv.y.max() < 2.2e-3
        # Units: SI, with PTV y in millimetres. In millimetres the PTV points
        # below y+ = 5 lie on U+ = y+; in metres they would sit beyond y+ 500,
        # where the log law gives U+ above 20, while every PTV U+ is below 18.
        assert abs(tbl.sublayer_deviation(ptv)) < 0.02
        in_metres = ptv.y / tbl.PTV_Y_UNIT * ptv.Utau / ptv.nu
        assert in_metres.min() > 500
        assert ptv.Uplus.max() < 18 < 20 < np.log(500) / 0.41 + 5.0
        # Plausible air: rho near 1.2 kg/m^3, nu near 1.5e-5 m^2/s.
        assert 1.19 < piv.rho < 1.22 and 1.49e-5 < piv.nu < 1.51e-5
        # The stresses: uu and vv positive, uv negative where it is resolved.
        assert (piv.uu > 0).all() and (piv.vv > 0).all()
        assert (piv.uv[piv.y < 0.5 * piv.delta] < 0).all()


def test_the_samples_are_the_cards_and_its_tests():
    paths = sorted(s["path"] for s in CARD["samples"])
    assert paths == sorted(
        f"{t}/{c}/EXPparam.mat" for t in ("PIV", "PTV") for c in tbl.CASES
    )
    md5 = {d["filename"]: d["digest"] for d in CARD["downloads"]}
    assert md5["PIV.zip"] == "fa1cd9e0cd70adb33c9941813b3a7743"
    assert md5["PTV.zip"] == "b874c3c5764daf56db31cbdd227eca2f"
    for sample in CARD["samples"]:
        assert sample["path"].split("/")[0] + ".zip" in sample["derivation"]


def test_the_readers_refuse_other_variables(tmp_path):
    path = tmp_path / "EXPparam.mat"
    savemat(path, {"EXPparam": {"Uinf": 1.0}})  # the struct the readme describes
    with pytest.raises(ValueError, match="variables"):
        tbl.read_piv(path, "U05")
    with pytest.raises(ValueError, match="variables"):
        tbl.read_ptv(path, "U05")


# The numbers of the dossier.


def test_reynolds_numbers(data):
    expected = {
        "U05": (1351, 3079),
        "U10": (2415, 6533),
        "U15": (3552, 9240),
        "U20": (4647, 12020),
    }
    for case, (piv, _) in data.items():
        assert tbl.re_tau(piv) == pytest.approx(expected[case][0], abs=1)
        assert tbl.re_theta(piv) == pytest.approx(expected[case][1], abs=1)


def test_the_friction_velocity_agrees_with_coles_fernholz(data):
    differences = []
    for piv, _ in data.values():
        cf = tbl.coles_fernholz_utau(piv.Uinf, tbl.re_theta(piv))
        differences.append(piv.Utau / cf - 1)
    assert max(abs(d) for d in differences) < 0.012
    assert differences[0] == pytest.approx(0.0107, abs=5e-4)
    assert differences[1] == pytest.approx(-0.0114, abs=5e-4)


def test_the_log_law_and_its_window(data):
    nominal = {
        "U05": (0.4098, 5.072),
        "U10": (0.4001, 4.774),
        "U15": (0.4051, 4.982),
        "U20": (0.4088, 5.173),
    }
    kappas, bs = [], []
    for case, (piv, _) in data.items():
        kappa, b, n = tbl.log_fit(piv)
        assert kappa == pytest.approx(nominal[case][0], abs=5e-4)
        assert b == pytest.approx(nominal[case][1], abs=5e-3)
        assert n >= 40
        (k_lo, k_hi), (b_lo, b_hi) = tbl.log_fit_range(piv)
        assert k_lo <= kappa <= k_hi and b_lo <= b <= b_hi
        kappas += [k_lo, k_hi]
        bs += [b_lo, b_hi]
    # The window dominates: kappa 0.355 to 0.428 over the 15 windows.
    assert min(kappas) == pytest.approx(0.355, abs=1e-3)
    assert max(kappas) == pytest.approx(0.428, abs=1e-3)
    assert min(bs) == pytest.approx(3.02, abs=0.01)
    assert max(bs) == pytest.approx(5.55, abs=0.01)


def test_the_blasius_layer():
    lam = tbl.blasius()
    assert lam.wall_curvature == pytest.approx(0.332057, abs=1e-6)
    assert lam.eta99 == pytest.approx(4.910, abs=1e-3)
    assert lam.displacement == pytest.approx(1.7208, abs=1e-4)
    assert lam.momentum == pytest.approx(0.6641, abs=1e-4)
    h = lam.H
    assert h == pytest.approx(2.5911, abs=1e-4)


def test_the_shape_factor_turbulent_against_laminar(data):
    stated = {"U05": 1.3675, "U10": 1.3618, "U15": 1.3381, "U20": 1.3312}
    for case, (piv, ptv) in data.items():
        h_file = piv.H
        assert h_file == pytest.approx(stated[case], abs=1e-4)
        y, u = tbl.spliced(piv, ptv)
        _, theta, h = tbl.shape_factor(y, u, piv.delta)
        # Recomputed within 1.5 per cent of the file; theta within 1 per cent.
        assert abs(h / piv.H - 1) < 0.015
        assert abs(theta / piv.theta - 1) < 0.01
        # Far below the laminar layer: about half of Blasius's 2.59.
        assert h < 0.54 * tbl.blasius().H
    # H falls as the Reynolds number rises.
    assert list(stated.values()) == sorted(stated.values(), reverse=True)


def test_ptv_against_piv_and_the_shear_stress(data):
    means = {"U05": 1.003, "U10": 1.043, "U15": 1.032, "U20": 1.070}
    peaks = {"U05": 0.910, "U10": 0.961, "U15": 0.962, "U20": 0.973}
    for case, (piv, ptv) in data.items():
        mean, largest = tbl.ptv_over_piv(piv, ptv)
        assert mean == pytest.approx(means[case], abs=1e-3)
        assert largest < 1.10
        peak = tbl.shear_stress_peak(piv)
        assert peak == pytest.approx(peaks[case], abs=1e-3)
        assert peak < 1  # below the wall value of the total stress
