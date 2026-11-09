"""The Shang and Tu cylinder-wake PIV sample parses into what its card says,
the extraction that wrote it is checked on a small synthetic record, and the
reference analysis gives the numbers of the dossier (ADR 007;
docs/datasets/piv-cylinder-wake.md).
"""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import scipy.io

from pbc.data import SAMPLES_DIR
from pbc.data.card import load_card
from pbc.data.reference import cylinder_wake as cw

PIV = SAMPLES_DIR / "piv-cylinder-wake"
ROOT = Path(__file__).parents[2]
TOOL = ROOT / "tools/datasets/cylinder_wake_extract.py"


def tool():
    spec = importlib.util.spec_from_file_location("cylinder_wake_extract", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wake():
    return cw.load(PIV)


@pytest.fixture(scope="module")
def analysis(wake):
    return cw.analyse(wake)


# The sample.


def test_piv_cylinder_wake_sample_parses(wake):
    meta = wake.meta
    # Provenance: the record, its file, and its checksums.
    assert meta["source"]["md5"] == "4cc876439c48f7970afa477ea17d217a"
    assert meta["source"]["bytes"] == 1082404799
    assert meta["record_shape"] == [135, 80, 8000]
    # Field names, units, and layout.
    assert set(cw.SAMPLE_FILES) == {p.name for p in PIV.iterdir()}
    assert meta["units"].startswith("u, v: m/s; x, y: m")
    assert "[frame, y, x]" in meta["layout"]
    # Shapes and types: 60 frames on 46 x 61 points; float32 velocities.
    for name in (cw.U_FILE, cw.V_FILE):
        raw = np.load(PIV / name, allow_pickle=False)
        assert raw.dtype == np.float32 and raw.shape == (60, 46, 61)
    assert np.load(PIV / cw.MASK_FILE, allow_pickle=False).dtype == np.bool_
    assert wake.mean.shape == (2, 46, 61)
    assert wake.probes.shape == (8000, 2, 2)
    # Coordinates: the record's grid, 1.05035 mm apart, x and y increasing.
    for axis in (wake.x, wake.y):
        assert np.allclose(np.diff(axis), 1.05035e-3, atol=1e-8)
    assert (wake.x[0], wake.x[-1]) == pytest.approx((-0.057991, 0.005030), abs=1e-6)
    assert (wake.y[0], wake.y[-1]) == pytest.approx((-0.051356, -0.004091), abs=1e-6)
    # Cadence: 20 frames per second, frames 0-59.
    assert meta["fps"] == 20.0 and meta["frames"] == [0, 59]
    # Masks: exactly where u and v are both zero; 260 to 263 points of 2,806
    # in each frame (the cylinder and its shadows), the same 260 in every
    # frame and a few more at their edge; no NaN in u or v.
    assert np.array_equal(wake.mask, (wake.u == 0) & (wake.v == 0))
    per_frame = wake.mask.sum(axis=(1, 2))
    assert (per_frame.min(), per_frame.max()) == (260, 263)
    assert wake.mask.all(axis=0).sum() == 260
    assert np.all(np.isfinite(wake.u)) and np.all(np.isfinite(wake.v))
    # The mean is NaN only where every one of the 8000 frames is masked.
    assert np.isnan(wake.mean[0]).sum() == 260
    assert meta["valid_frames_min"] == 7105
    # Probes on the wake axis, never masked.
    assert meta["probes"]["2D"]["y"] == meta["probes"]["5D"]["y"]
    assert meta["probes"]["2D"]["y"] == pytest.approx(-0.0271987, abs=1e-6)
    assert np.all((wake.probes[:, :, 0] != 0) | (wake.probes[:, :, 1] != 0))
    # Velocities in m/s: the free stream about 4.4 cm/s.
    assert 0.040 < np.nanmean(wake.mean[0, -1]) < 0.050
    assert np.abs(wake.u).max() < 0.2 and np.abs(wake.v).max() < 0.2


def test_the_probes_are_the_crop_at_their_grid_points(wake):
    # The probe series of frames 0-59 equal the cropped fields at the probes'
    # positions: the reordering of the crop kept every value in its place.
    for k, probe in enumerate(wake.meta["probes"].values()):
        ix = int(np.argmin(np.abs(wake.x - probe["x"])))
        iy = int(np.argmin(np.abs(wake.y - probe["y"])))
        np.testing.assert_array_equal(wake.probes[:60, k, 0], wake.u[:, iy, ix])
        np.testing.assert_array_equal(wake.probes[:60, k, 1], wake.v[:, iy, ix])


def test_the_card_pins_the_record_and_the_tool(wake):
    card = load_card(ROOT / "data/registry/piv-cylinder-wake.yaml")
    (download,) = card["downloads"]
    module = tool()
    assert download["algorithm"] == "md5" and download["digest"] == module.MD5
    assert download["filename"] == module.FILENAME
    assert wake.meta["source"]["sha256"] == module.SHA256
    for sample in card["samples"]:
        data = (PIV / sample["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sample["sha256"]
        assert len(data) == sample["bytes"]


def test_the_tool_refuses_a_file_that_is_not_the_record(tmp_path):
    other = tmp_path / "cylinder_vel.mat"
    scipy.io.savemat(other, {"u": np.zeros((3, 2, 2))})
    with pytest.raises(ValueError, match="md5"):
        tool().convert(other, tmp_path)


# The extraction, on a small synthetic record.


def synthetic_record(frames=64):
    i = np.arange(135)[:, None, None]
    j = np.arange(80)[None, :, None]
    t = np.arange(frames)[None, None, :]
    x = np.broadcast_to(0.0827563 - 1.05035e-3 * i[:, :, 0], (135, 80)).copy()
    y = np.broadcast_to(-0.0671121 + 1.05035e-3 * j[:, :, 0], (135, 80)).copy()
    u = 1e-4 * (i + 1) + 1e-6 * j + 1e-8 * t
    v = -1e-4 * (j + 1) + 1e-6 * i - 1e-8 * t
    u, v = u.astype(float), v.astype(float)
    u[120:124, 20:40, :] = v[120:124, 20:40, :] = 0.0  # a mask
    return {"u": u, "v": v, "x": x, "y": y}


def test_read_mat_reads_the_four_variables(tmp_path):
    record = synthetic_record(frames=3)
    path = tmp_path / "small.mat"
    scipy.io.savemat(path, record)
    read = cw.read_mat(path)
    for key in ("u", "v", "x", "y"):
        np.testing.assert_array_equal(read[key], record[key])
    scipy.io.savemat(path, {"u": record["u"], "v": record["v"]})
    with pytest.raises(ValueError, match="no variable"):
        cw.read_mat(path)


def test_extract_reorders_the_crop_and_keeps_every_value(tmp_path):
    record = synthetic_record()
    sample = cw.extract(record, {"record": "synthetic"})
    cw.write_sample(sample, tmp_path)
    wake = cw.load(tmp_path)
    i1, j0 = cw.CROP_I[1], cw.CROP_J[0]
    # [frame, y, x] with x increasing: x index ix is record index i1 - ix.
    for frame, iy, ix in ((0, 0, 0), (5, 10, 20), (59, 45, 60)):
        i, j = i1 - ix, j0 + iy
        assert wake.u[frame, iy, ix] == pytest.approx(
            record["u"][i, j, frame], rel=1e-6
        )
        assert wake.v[frame, iy, ix] == pytest.approx(
            record["v"][i, j, frame], rel=1e-6
        )
        assert wake.x[ix] == record["x"][i, j] and wake.y[iy] == record["y"][i, j]
    # The mask, the mean over the unmasked frames, and the probes.
    masked = wake.mask.any(axis=0)
    assert masked.sum() == 4 * 20
    assert np.isnan(wake.mean[0][masked]).all()
    assert wake.mean[0, 0, 0] == pytest.approx(record["u"][i1, j0].mean(), rel=1e-6)
    i, j = cw.PROBES["2D"]
    assert wake.probes.shape == (64, 2, 2)
    np.testing.assert_allclose(wake.probes[:, 0, 1], record["v"][i, j], rtol=1e-6)
    meta = json.loads((tmp_path / cw.META_FILE).read_text())
    assert meta["source"] == {"record": "synthetic"}


# The analysis.


def test_vorticity_of_a_solid_body_rotation_is_twice_the_rate():
    x = np.linspace(-0.01, 0.01, 21)
    y = np.linspace(-0.008, 0.008, 17)
    xx, yy = np.meshgrid(x, y)
    rate = 3.0  # 1/s
    mask = np.zeros(xx.shape, bool)
    mask[8, 10] = True
    omega = cw.vorticity(-rate * yy, rate * xx, mask, x, y)
    assert np.nanmax(np.abs(omega - 2 * rate)) < 1e-9
    # NaN on the masked point and its eight neighbours, nowhere else.
    assert np.isnan(omega).sum() == 9 and np.isnan(omega[7:10, 9:12]).all()


def test_the_peak_finder_recovers_a_known_frequency():
    t = np.arange(8000) / cw.FPS
    rng = np.random.default_rng(1)
    series = 0.02 * np.sin(2 * np.pi * 0.8765 * t) + 0.002 * rng.standard_normal(8000)
    assert cw.peak(*cw.spectrum(series)) == pytest.approx(0.8765, abs=0.002)
    assert cw.block_peaks(series) == pytest.approx([0.8765] * 4, abs=0.003)


def test_the_shedding_frequency_and_the_strouhal_number(analysis):
    # v on the wake axis: the mean of four 100 s blocks, at both probes.
    assert analysis.frequency["2D"] == pytest.approx(0.8887, abs=1e-4)
    assert analysis.frequency_err["2D"] == pytest.approx(0.0028, abs=1e-4)
    assert analysis.frequency["5D"] == pytest.approx(0.8881, abs=1e-4)
    # The paper's 0.889 Hz lies within one standard error.
    assert abs(analysis.frequency["2D"] - cw.F_PUBLISHED) < analysis.frequency_err["2D"]
    assert analysis.welch_frequency["2D"] == pytest.approx(0.8914, abs=1e-4)
    # u on the axis oscillates at twice the frequency.
    assert analysis.harmonic_u == pytest.approx(1.792, abs=1e-3)
    assert analysis.harmonic_u / analysis.frequency["2D"] == pytest.approx(2, abs=0.02)
    # St with D = 9.5 mm and U = 4.35 cm/s, 5.5 % below Roshko at Re = 413.
    assert analysis.strouhal == pytest.approx(0.1941, abs=1e-4)
    assert analysis.roshko == pytest.approx(0.2055, abs=1e-4)
    assert analysis.strouhal / analysis.roshko - 1 == pytest.approx(-0.055, abs=0.002)


def test_the_geometry_read_from_the_mask_and_the_mean_field(analysis):
    assert analysis.cylinder_x == pytest.approx(-0.04329, abs=1e-5)
    assert analysis.axis_y == pytest.approx(-0.02720, abs=1e-5)
    # The probes 2 D and 5 D behind the shadow's centre, to a grid spacing.
    assert (analysis.recirculation - analysis.cylinder_x) / cw.DIAMETER == (
        pytest.approx(2.14, abs=0.01)
    )
    assert analysis.free_stream_sample == pytest.approx(0.0452, abs=1e-4)
    assert analysis.vorticity_p99 == pytest.approx(21.4, abs=0.1)
    assert analysis.masked_fraction == pytest.approx(0.0928, abs=1e-4)
