"""The trackpy ``bulk_water`` sample parses into what its card says, the
tracking that wrote it is repeated by the build on the committed frames and
works on synthetic images, and the reference analysis gives the numbers of
the dossier (ADR 007; docs/datasets/trackpy-bulk-water.md).
"""

import hashlib
import importlib.util
from pathlib import Path

import matplotlib.image as mpimg
import numpy as np
import pytest

from pbc.data import SAMPLES_DIR, tracking
from pbc.data.card import load_card
from pbc.data.reference import trackpy_bulk_water as bw

BW = SAMPLES_DIR / "trackpy-bulk-water"
ROOT = Path(__file__).parents[2]
TOOL = ROOT / "tools/datasets/bulk_water_tracks.py"
# Git blob SHA-1 of the README at trackpy-examples commit 09fb3074 (the
# GitHub tree of sample_data/bulk_water, read 2026-11-08).
README_BLOB = "6d41fcad4a3878eec2e77f3549af42e4ff6c7f92"


def tool():
    spec = importlib.util.spec_from_file_location("bulk_water_tracks", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tracks():
    return bw.load(BW)


@pytest.fixture(scope="module")
def analysis(tracks):
    return bw.analyse(tracks)


# The sample.


def test_trackpy_bulk_water_sample_parses(tracks):
    # Provenance and processing: the header names the commit and the steps.
    assert tracks.header[0].endswith(
        "at commit 09fb3074a173585d48b5001b5b4b7e6479999598"
    )
    assert "processing of this project, not the provider's" in tracks.header[2]
    assert "mass >= 90.0" in tracks.header[2]
    assert "within 3.0 px" in tracks.header[2]
    # Field names and units.
    names = (BW / bw.TRACKS).read_text().splitlines()[len(tracks.header)]
    assert tuple(names.split(",")) == bw.FIELDS
    assert "24 frames per second" in tracks.header[3]
    assert "x, y: px" in tracks.header[3] and "1 um = 2.85 px" in tracks.header[3]
    # Shapes: 23,685 features in 40 frames, 582 to 603 per frame.
    for column in (tracks.frame, tracks.particle, tracks.mass):
        assert column.shape == (23685,)
    assert tracks.xy.shape == (23685, 2)
    per_frame = np.bincount(tracks.frame)
    assert per_frame.size == bw.FRAME_COUNT
    assert (per_frame.min(), per_frame.max()) == (582, 603)
    # Cadence: every frame 0-39 present, a track occupies consecutive frames
    # (no memory in the linking), and the rows are in frame order.
    assert np.all(np.diff(tracks.frame) >= 0)
    order = np.lexsort((tracks.frame, tracks.particle))
    same = np.diff(tracks.particle[order]) == 0
    assert np.all(np.diff(tracks.frame[order])[same] == 1)
    assert np.unique(tracks.particle).size == 1268
    assert (np.bincount(tracks.particle) >= bw.MIN_LENGTH).sum() == 596
    # Masks: none; every position inside the frame, at least RADIUS from the
    # border, and every mass at or above the cut.
    assert np.all(np.isfinite(tracks.xy)) and np.all(np.isfinite(tracks.mass))
    # (the peak is; the centroid moves less than a pixel from it).
    rows, cols = bw.SHAPE
    assert tracks.xy[:, 0].min() > bw.RADIUS - 1
    assert tracks.xy[:, 0].max() < cols - 1 - bw.RADIUS + 1
    assert tracks.xy[:, 1].min() > bw.RADIUS - 1
    assert tracks.xy[:, 1].max() < rows - 1 - bw.RADIUS + 1
    assert tracks.mass.min() >= bw.MINMASS


def test_the_readme_is_the_providers_and_the_green_frames_parse():
    data = (BW / bw.README).read_bytes()
    assert hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == README_BLOB
    readme = data.decode("ascii")
    assert "24 frames per second" in readme
    assert "1 micron = 2.85 pixels" in readme
    # The green channel of frames 000-002: uint8 grey levels, (3, 424, 640),
    # no mask; the spheres are dark on a field of about 120 grey levels.
    raw = np.load(BW / bw.FRAMES, allow_pickle=False)
    assert raw.dtype == np.uint8 and raw.shape == (3, 424, 640)
    green = bw.read_frames(BW / bw.FRAMES)
    assert (green[0].min(), green[0].max()) == (94, 142)
    assert 110 < np.median(green) < 135


def test_read_frame_takes_the_green_channel_of_an_rgba_png(tmp_path):
    rng = np.random.default_rng(5)
    rgba = rng.integers(0, 256, (*bw.SHAPE, 4), dtype=np.uint8)
    rgba[..., 3] = 255
    path = tmp_path / "frame.png"
    mpimg.imsave(path, rgba)
    np.testing.assert_array_equal(bw.read_frame(path), rgba[..., 1])
    mpimg.imsave(tmp_path / "small.png", rgba[:10, :10])
    with pytest.raises(ValueError, match="shape"):
        bw.read_frame(tmp_path / "small.png")


def test_the_reader_refuses_other_columns(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text("# x\nframe,track,x,y,mass\n0,0,1.0,2.0,100.0\n")
    with pytest.raises(ValueError, match="columns"):
        bw.read_tracks(path)
    path.write_text("frame,particle,x,y,mass\n0.5,0,1.0,2.0,100.0\n")
    with pytest.raises(ValueError, match="integer"):
        bw.read_tracks(path)


def test_the_build_repeats_the_tracking_of_frames_000_to_002():
    # The CSV was written from 40 frames; its rows of frames 0-2 depend only
    # on these three frames (the numbering is by order of appearance).
    frames = list(bw.read_frames(BW / bw.FRAMES))
    repeated = bw.format_rows(bw.track(frames))
    lines = (BW / bw.TRACKS).read_text().splitlines()
    body = [line for line in lines[5:] if int(line.split(",")[0]) < 3]
    assert repeated == body


def test_relinking_with_the_same_parameters_gives_the_same_tracks(tracks):
    again = bw.relink(tracks, bw.SEARCH_RANGE)
    np.testing.assert_array_equal(again.particle, tracks.particle)
    np.testing.assert_array_equal(again.frame, tracks.frame)


def test_the_tool_pins_the_frames_of_the_card_and_refuses_others(tmp_path):
    module = tool()
    card = load_card(ROOT / "data/registry/trackpy-bulk-water.yaml")
    digests = {d["filename"]: d["digest"] for d in card["downloads"]}
    assert len(module.FRAME_SHA256) == bw.FRAME_COUNT
    for name, digest in module.FRAME_SHA256.items():
        assert digests[name] == digest
    for name in module.FRAME_SHA256:
        (tmp_path / name).write_bytes(b"not a frame")
    with pytest.raises(ValueError, match="sha256"):
        module.convert(tmp_path, tmp_path)
    assert module.header() == list(bw.load(BW).header)


# The tracking, on images and walks whose answer is known.


def dark_spheres(centres, shape=(60, 80), sigma=1.6, depth=60.0, noise=1.0, seed=0):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    image = np.full(shape, 140.0)
    for x, y in centres:
        image -= depth * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    return image + np.random.default_rng(seed).normal(0, noise, shape)


def test_locate_finds_dark_spheres_to_a_tenth_of_a_pixel():
    centres = [(15.3, 12.7), (40.0, 30.45), (62.8, 44.1), (20.6, 47.9)]
    found = tracking.locate(dark_spheres(centres), 5, 50.0, invert=True)
    assert len(found) == len(centres)
    for x, y in centres:
        distance = np.hypot(found[:, 0] - x, found[:, 1] - y)
        assert distance.min() < 0.1
    # Not inverted, the dark spheres are not where features are found.
    bright = tracking.locate(dark_spheres(centres), 5, 50.0)
    for x, y in centres:
        assert np.hypot(bright[:, 0] - x, bright[:, 1] - y).min() > 1.0


def test_link_follows_mutual_nearest_neighbours_and_starts_the_rest():
    a = np.array([[10.0, 10.0], [30.0, 10.0], [50.0, 10.0]])
    b = np.array([[30.5, 10.2], [10.4, 9.8], [70.0, 10.0]])  # 50 moved too far
    c = np.array([[10.9, 9.5], [31.0, 10.0], [71.0, 10.0]])
    numbers = tracking.link([a, b, c], 3.0)
    assert numbers[0].tolist() == [0, 1, 2]
    assert numbers[1].tolist() == [1, 0, 3]
    assert numbers[2].tolist() == [0, 1, 3]
    # Two features that both want the same one: only the mutual pair links.
    d = np.array([[10.0, 10.0], [11.0, 10.0]])
    e = np.array([[11.8, 10.0]])
    assert tracking.link([d, e], 3.0)[1].tolist() == [1]


def test_msd_sums_equal_the_sum_over_every_pair_of_frames():
    rng = np.random.default_rng(3)
    frame = np.array([2, 0, 1, 3, 0, 1, 2, 5, 6])
    track = np.array([7, 7, 7, 7, 2, 2, 2, 9, 9])
    xy = rng.normal(size=(frame.size, 2))
    lags = np.array([1, 2, 3])
    sums, counts, numbers = tracking.msd_sums(frame, track, xy, lags)
    assert numbers.tolist() == [2, 7, 9]
    for row, number in enumerate(numbers):
        mine = track == number
        f, p = frame[mine], xy[mine]
        for k, lag in enumerate(lags):
            pairs = [
                (i, j)
                for i in range(f.size)
                for j in range(f.size)
                if f[j] - f[i] == lag
            ]
            assert counts[row, k] == len(pairs)
            assert sums[row, k] == pytest.approx(
                sum(((p[j] - p[i]) ** 2).sum() for i, j in pairs)
            )


def test_drift_and_msd_recover_a_known_walk():
    rng = np.random.default_rng(1)
    frames, walkers, sigma = 40, 2000, 0.5
    flow = np.array([0.3, -0.1])  # px per frame, the same for all
    steps = rng.normal(0, sigma, (walkers, frames - 1, 2)) + flow
    start = rng.uniform(0, 500, (walkers, 1, 2))
    paths = np.concatenate([start, start + np.cumsum(steps, axis=1)], axis=1)
    frame = np.tile(np.arange(frames), walkers)
    track = np.repeat(np.arange(walkers), frames)
    xy = paths.reshape(-1, 2)
    motion = tracking.drift(frame, track, xy)
    mean_step = steps.mean(axis=0)
    np.testing.assert_allclose(motion[1:], np.cumsum(mean_step, axis=0))
    lags = np.arange(1, 6)
    sums, counts, numbers = tracking.msd_sums(frame, track, xy - motion[frame], lags)
    assert numbers.tolist() == list(range(walkers))
    np.testing.assert_array_equal(counts[0], frames - lags)
    msd = sums.sum(axis=0) / counts.sum(axis=0)
    # 2 sigma^2 per lag in two dimensions (the drift estimate removes
    # 1/walkers of it); 2,000 walkers give about 1 % statistical error.
    np.testing.assert_allclose(msd, 2 * sigma**2 * lags, rtol=0.03)


def test_drift_refuses_a_track_with_a_gap():
    with pytest.raises(ValueError, match="skips"):
        tracking.drift(np.array([0, 2]), np.array([0, 0]), np.zeros((2, 2)))


# The numbers of the dossier.


def test_the_msd_fit_gives_the_diffusion_coefficient_of_the_dossier(analysis):
    a = analysis
    assert a.tracks == 596 and a.features == 21200
    assert a.diffusion == pytest.approx(0.4034, abs=5e-5)
    assert a.diffusion_err == pytest.approx(0.0098, abs=5e-4)
    assert a.intercept == pytest.approx(-0.0355, abs=5e-5)
    assert a.intercept_err == pytest.approx(0.0031, abs=3e-4)
    assert a.msd[0] == pytest.approx(0.0439, abs=5e-5)
    assert a.msd[-1] == pytest.approx(0.6430, abs=5e-5)
    # The residual of lag 1 is positive and much larger than its error.
    lag1 = a.msd[0] - (4 * a.diffusion * a.tau[0] + a.intercept)
    assert lag1 == pytest.approx(0.0122, abs=2e-4)
    assert lag1 > 10 * a.msd_err[0]


def test_the_drift_and_the_steps_are_those_of_the_dossier(analysis):
    a = analysis
    velocity = a.drift[-1] / ((bw.FRAME_COUNT - 1) / bw.FPS)
    np.testing.assert_allclose(velocity, [0.522, 0.161], atol=5e-4)
    assert a.step_correlation == pytest.approx(0.142, abs=5e-4)
    assert a.excess_kurtosis == pytest.approx(3.23, abs=5e-3)
    assert a.track_spread == pytest.approx(0.33, abs=5e-3)
    assert a.track_spread_expected == pytest.approx(0.16, abs=5e-3)


def test_the_drift_is_that_of_all_linked_features_not_of_the_long_tracks(
    tracks, analysis
):
    # The dossier: the drift is the motion of the whole sample, estimated from
    # every linked feature before the tracks are selected by length.
    every = tracking.drift(
        tracks.frame, tracks.particle, tracks.xy * bw.MICRONS_PER_PIXEL
    )
    np.testing.assert_array_equal(analysis.drift, every)
    long = np.bincount(tracks.particle)[tracks.particle] >= bw.MIN_LENGTH
    selected = tracking.drift(
        tracks.frame[long],
        tracks.particle[long],
        tracks.xy[long] * bw.MICRONS_PER_PIXEL,
    )
    assert abs(selected[-1, 0] - every[-1, 0]) > 0.01  # µm: the choice matters
    # and it does not depend on the selection of tracks for the MSD
    shorter = bw.analyse(tracks, min_length=25, bootstrap=2)
    np.testing.assert_array_equal(shorter.drift, every)


def test_stokes_einstein_at_20_and_25_degrees():
    assert bw.stokes_einstein(20.0) == pytest.approx(0.4288, abs=5e-5)
    assert bw.stokes_einstein(25.0) == pytest.approx(0.4907, abs=5e-5)


def test_the_processing_choices_are_the_sensitivity_table_of_the_dossier(tracks):
    table = {name: round(value, 3) for name, value in bw.sensitivity(tracks).items()}
    assert table == {
        "link range 2 px": 0.382,
        "link range 4 px": 0.411,
        "mass >= 120": 0.395,
        "tracks >= 10 frames": 0.403,
        "tracks >= 25 frames": 0.403,
        "lags 1-5": 0.377,
        "lags 2-10": 0.409,
        "no drift subtracted": 0.438,
    }


def test_the_frames_show_the_edges_of_8_pixel_compression_blocks():
    for green in bw.read_frames(BW / bw.FRAMES):
        steps = bw.block_steps(green)
        assert steps.argmax() == 7
        assert steps[7] > 1.3 * steps[:7].mean()
