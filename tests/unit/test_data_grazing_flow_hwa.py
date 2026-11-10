"""The grazing-flow benchmark sample parses into what its card says, and the
reference analysis gives the numbers of the dossier (ADR 007;
docs/datasets/grazing-flow-hwa-benchmark.md).
"""

import numpy as np
import pytest
import yaml

from pbc.data import SAMPLES_DIR
from pbc.data.reference import grazing_flow_hwa as gf

DIR = SAMPLES_DIR / "grazing-flow-hwa-benchmark"
CARD = yaml.safe_load(
    (SAMPLES_DIR.parents[0] / "registry" / f"{DIR.name}.yaml").read_text()
)
CASES = [w + s for w in gf.WALLS for s in gf.SPEEDS] + ["UP" + s for s in gf.SPEEDS]


@pytest.fixture(scope="module")
def data():
    return gf.load(DIR)


# The sample.


def test_grazing_flow_sample_parses(data):
    for case in CASES:
        upstream = case.startswith("UP")
        profiles = gf.read_profiles(DIR / "HWA_PROFILES_v2" / f"HW_{case}.csv")
        parameters = gf.read_parameters(DIR / "BL_PARAMETERS" / f"BL_{case}.csv")
        # Field names are checked by the readers; shapes: 215 rows of five
        # stations (35 upstream) by 8 columns, 5 parameter rows (1) by 10.
        assert profiles.shape == ((35, 8) if upstream else (215, 8))
        assert parameters.shape == ((1, 10) if upstream else (5, 10))
        # Units: the parameter column headed x/L holds x in metres.
        assert gf.parameter_x_is_metres(profiles, parameters)
        np.testing.assert_allclose(
            np.sort(parameters[:, 0]),
            [-0.66] if upstream else [-0.033333, -0.016667, 0.0, 0.016667, 0.033333],
            atol=1e-6,
        )
        # The liner and the nominal speed on the first row only.
        liner = {"D00": 0.0, "D35": 3.5, "D45": 4.5, "UPV": -1.0}[case[:3]]
        assert parameters[0, 8] == liner
        assert parameters[0, 9] == float(case[-2:])
        assert np.isnan(parameters[1:, 8:]).all()
        # Masks: only Lambda/delta is ever empty.
        assert np.isfinite(profiles[:, :7]).all()
        for station in data[case]:
            n = 35 if upstream else 43
            assert station.y_over_delta.shape == (n,)
            empty = int(np.isnan(station.length_scale).sum())
            assert (empty == 14) if upstream else (8 <= empty <= 12)
            # Cadence: increasing y from 0.005 to 0.007 delta (0.021 to 0.026 upstream).
            # One defect: the upstream profile at 25 m/s gives rows 5 and 6 the
            # same y/delta (0.04139) with U/Ue 0.555 and 0.532.
            steps = np.diff(station.y_over_delta)
            if case == "UPV25":
                assert list(np.flatnonzero(steps <= 0)) == [4]
                assert steps[4] == 0
                np.testing.assert_allclose(
                    station.U_over_Ue[4:6], [0.554580, 0.532299], atol=1e-6
                )
            else:
                assert (steps > 0).all()
            assert station.y_over_delta[0] < (0.027 if upstream else 0.0071)
            # Uncertainty columns: a 95 % half-width for U/Ue, bounds for TI.
            assert (station.U_uncertainty > 0).all()
            assert station.U_uncertainty.max() < 4.4e-4
            assert (station.TI_lower <= station.TI).all()
            ti, upper = station.TI, station.TI_upper
            assert (ti <= upper).all()
            assert (
                max(
                    (station.TI_upper - station.TI).max(),
                    (station.TI - station.TI_lower).max(),
                )
                < 1e-3
            )
            # Plausible air: 292 to 304 K, 99.4 to 100.7 kPa.
            assert 292 < station.T < 304 and 99.4e3 < station.p < 100.7e3


def test_the_readers_refuse_other_files(tmp_path):
    path = tmp_path / "BL.csv"
    path.write_bytes(b"x,y\n1,2\n")
    with pytest.raises(ValueError, match="CRLF"):
        gf.read_parameters(path)
    path.write_bytes(b"x,y\r\n1,2\r\n")
    with pytest.raises(ValueError, match="header"):
        gf.read_parameters(path)


def test_the_samples_are_the_cards_and_its_tests():
    paths = sorted(s["path"] for s in CARD["samples"])
    assert paths == sorted(
        [f"HWA_PROFILES_v2/HW_{c}.csv" for c in CASES]
        + [f"BL_PARAMETERS/BL_{c}.csv" for c in CASES]
    )
    md5 = {d["filename"]: d["digest"] for d in CARD["downloads"]}
    assert md5["HWA_PROFILES_v2.zip"] == "b0aaf672c259c1785c0c8c1f1b46f94f"
    assert md5["BL_PARAMETERS.zip"] == "fef62fb9bf16f0456e14e65bab2538b1"
    for sample in CARD["samples"]:
        assert sample["path"].split("/")[0] + ".zip" in sample["derivation"]


# The numbers of the dossier.


def test_air_and_the_friction_velocity(data):
    s = data["D00V20"][2]
    assert gf.air_viscosity(273.15) == pytest.approx(1.716e-5)
    assert s.nu == pytest.approx(1.578e-5, abs=1e-8)
    assert s.re_theta == pytest.approx(4499, abs=1)
    assert s.utau == pytest.approx(0.762, abs=1e-3)
    assert s.re_tau == pytest.approx(1429, abs=1)


def test_the_solid_wall_log_law(data):
    kappas, bs = [], []
    for speed in gf.SPEEDS:
        for s in data["D00" + speed]:
            kappa, b, n = gf.log_fit(s)
            assert 6 <= n <= 10
            kappas.append(kappa)
            bs.append(b)
    assert min(kappas) == pytest.approx(0.387, abs=1e-3)
    assert max(kappas) == pytest.approx(0.421, abs=1e-3)
    assert min(bs) == pytest.approx(4.48, abs=0.01)
    assert max(bs) == pytest.approx(5.39, abs=0.01)


def test_the_porous_walls_leave_the_solid_wall_law(data):
    # With the solid-wall u_tau, the log fit over the porous inserts from
    # x/L = 0 on gives kappa far below 0.41: the wall law does not hold there.
    for wall in ("D35", "D45"):
        for speed in gf.SPEEDS:
            for s in data[wall + speed][2:]:
                assert gf.log_fit(s)[0] < 0.31


def test_the_shape_factor(data):
    solid = [s.H for sp in gf.SPEEDS for s in data["D00" + sp]]
    assert min(solid) == pytest.approx(1.326, abs=1e-3)
    assert max(solid) == pytest.approx(1.357, abs=1e-3)
    rises = []
    for wall in ("D35", "D45"):
        for speed in gf.SPEEDS:
            stations = data[wall + speed]
            rises.append(stations[-1].H - stations[0].H)
    assert min(rises) > 0.046 and max(rises) < 0.058
    # Recomputed from the solid-wall profiles (linear to the wall), H is
    # 1 to 4 per cent above the record's: the first point is at y+ 5 to 13.
    for speed in gf.SPEEDS:
        for s in data["D00" + speed]:
            assert 1.0 < gf.shape_factor(s) / s.H < 1.04
    # The laminar layer is far off: 2.591.
    assert max(solid) < 0.53 * 2.5911
