"""Shang and Tu cylinder-wake PIV: vorticity, mean flow, and shedding frequency.

Status of the figure: *processed*. The record (Zenodo 20765567, one MAT file
``cylinder_vel.mat``) holds velocity fields u and v [m/s] on a 135 x 80 grid
x, y [m] for 8000 frames at 20 Hz, computed by LaVision DaVis 8.1.2 from PIV
image pairs of the flow past a finite cylinder at Re = 413 in a water channel,
in a plane at mid-span. The fields are therefore processed measurements, not
raw images. Exact zeros of u and v mark the cylinder and its laser shadows: a
mask, not data.

``tools/datasets/cylinder_wake_extract.py`` reads the MAT file once, outside
the build (``read_mat``, ``scipy.io.loadmat``: the file is MAT 5.0, no h5py),
and writes the committed sample with ``extract``:

- ``wake_u.npy``, ``wake_v.npy``: u and v of frames 0-59 (3 s, about 2.7
  shedding periods) on a crop of the near wake, float32, index order
  [frame, y, x] with x and y increasing (the record's x decreases along its
  first axis; the crop is reordered, no value changed beyond float32);
- ``wake_mask.npy``: True where u and v are both exactly zero in the record;
- ``wake_mean.npy``: the mean u and v over the unmasked frames of all 8000;
- ``probes.npy``: u and v at two grid points on the wake axis for all 8000
  frames (400 s), for the spectrum;
- ``wake_meta.json``: the grid, the crop and probe indices in the record, the
  cadence, the units, and the source.

This module reads that sample, derives the vorticity by central differences
(a derived quantity, not a measurement), the time-mean streamlines and the
recirculation length, and the shedding frequency from the spectrum of v at
the probes; it compares the frequency with the record's paper (Tu et al.,
Exp. Fluids 55, 1805, 2014: 0.889 Hz) and the Strouhal number with Roshko's
correlation for 200 <= Re < 2000.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.io
from scipy import ndimage, signal

from pbc.data.plotting import COLOURS, add_credit, label_status, signed_image

U_FILE = "wake_u.npy"
V_FILE = "wake_v.npy"
MASK_FILE = "wake_mask.npy"
MEAN_FILE = "wake_mean.npy"
PROBES_FILE = "probes.npy"
META_FILE = "wake_meta.json"
SAMPLE_FILES = (U_FILE, V_FILE, MASK_FILE, MEAN_FILE, PROBES_FILE, META_FILE)

# The record: 135 x 80 grid points, 8000 frames at 20 Hz.
RECORD_SHAPE = (135, 80, 8000)
FPS = 20.0  # Hz, the record's description
# The crop, as record indices (first axis i: x decreasing; second axis j: y
# increasing), inclusive: x from -58.0 to +5.0 mm, y from -51.4 to -4.1 mm.
CROP_I = (74, 134)
CROP_J = (15, 60)
FRAMES = 60  # frames 0-59 of the record
# Probes on the wake axis (j = 38, y = -27.2 mm), about 2 D and 5 D behind
# the centre of the cylinder's shadow (x = -43.3 mm).
PROBES = {"2D": (102, 38), "5D": (75, 38)}

# The experiment, from the paper (Tu et al. 2014, Section 4.1; arXiv 1401.7047).
DIAMETER = 9.5e-3  # m
FREE_STREAM = 0.0435  # m/s
REYNOLDS = 413
F_PUBLISHED = 0.889  # Hz, the dominant spectral peak the paper reports
# Roshko (1954), St Re = 0.212 Re - 2.7 for 200 <= Re < 2000 (long cylinders, air).
ROSHKO = (0.212, 2.7)

# The spectrum: Welch, Hann windows of 2048 frames (102.4 s), half overlap.
NPERSEG = 2048
BLOCKS = 4  # non-overlapping blocks of 100 s for the spread of the peak
F_MIN = 0.3  # Hz: the peak is searched above the slow drift of u


@dataclass(frozen=True)
class Wake:
    u: np.ndarray  # (frames, ny, nx) m/s, masked samples are 0 as in the record
    v: np.ndarray
    mask: np.ndarray  # (frames, ny, nx) bool, True: no data
    mean: np.ndarray  # (2, ny, nx) m/s, mean u and v; NaN where always masked
    probes: np.ndarray  # (8000, 2, 2) m/s: frame, probe (2D, 5D), component (u, v)
    x: np.ndarray  # (nx,) m, increasing
    y: np.ndarray  # (ny,) m, increasing
    meta: dict


# Reading the record and writing the sample (the one-time extraction).


def read_mat(path: Path) -> dict[str, np.ndarray]:
    """u, v, x, y of the record's MAT 5.0 file (``scipy.io.loadmat``)."""
    data = scipy.io.loadmat(Path(path), variable_names=("u", "v", "x", "y"))
    missing = {"u", "v", "x", "y"} - set(data)
    if missing:
        raise ValueError(f"{path}: no variable {sorted(missing)}")
    u, v, x, y = (np.asarray(data[k], dtype=float) for k in ("u", "v", "x", "y"))
    if u.ndim != 3 or v.shape != u.shape or {x.shape, y.shape} != {u.shape[:2]}:
        raise ValueError(f"{path}: shapes u {u.shape}, v {v.shape}, x {x.shape}")
    return {"u": u, "v": v, "x": x, "y": y}


def _reorder(field: np.ndarray) -> np.ndarray:
    """Record [i, j, frame] (x decreasing along i) to [frame, y, x] increasing."""
    return np.ascontiguousarray(np.transpose(field, (2, 1, 0))[:, :, ::-1])


def extract(record: dict[str, np.ndarray], source: dict) -> dict:
    """The arrays and the metadata of the committed sample."""
    u, v, x, y = record["u"], record["v"], record["x"], record["y"]
    (i0, i1), (j0, j1) = CROP_I, CROP_J
    crop = (slice(i0, i1 + 1), slice(j0, j1 + 1))
    xs, ys = x[crop][:, 0][::-1], y[crop][0, :]
    if not (np.all(np.diff(xs) > 0) and np.all(np.diff(ys) > 0)):
        raise ValueError("the crop's x and y do not increase after reordering")
    cu, cv = u[crop], v[crop]
    masked = (cu == 0) & (cv == 0)
    valid = (~masked).sum(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.stack(
            [np.where(masked, 0.0, f).sum(axis=2) / valid for f in (cu, cv)]
        )
    mean[:, valid == 0] = np.nan
    mean = np.ascontiguousarray(np.transpose(mean, (0, 2, 1))[:, :, ::-1])
    probes = np.stack(
        [np.stack([u[i, j, :], v[i, j, :]], axis=1) for i, j in PROBES.values()],
        axis=1,
    )
    meta = {
        "source": source,
        "record_shape": list(u.shape),
        "frames": [0, FRAMES - 1],
        "fps": FPS,
        "crop_record_i": list(CROP_I),
        "crop_record_j": list(CROP_J),
        "x": [float(a) for a in xs],
        "y": [float(a) for a in ys],
        "probes": {
            name: {"record_index": [i, j], "x": float(x[i, j]), "y": float(y[i, j])}
            for name, (i, j) in PROBES.items()
        },
        "valid_frames_min": int(valid[valid > 0].min()),
        "units": "u, v: m/s; x, y: m (the record's); frame: 1/20 s",
        "layout": (
            "wake_u, wake_v, wake_mask: [frame, y, x], x and y increasing; "
            "wake_mean: [component (u, v), y, x]; "
            "probes: [frame, probe (2D, 5D), component (u, v)]"
        ),
        "mask": "True where u and v are both exactly 0 in the record",
    }
    return {
        U_FILE: _reorder(cu[:, :, :FRAMES]).astype(np.float32),
        V_FILE: _reorder(cv[:, :, :FRAMES]).astype(np.float32),
        MASK_FILE: _reorder(masked[:, :, :FRAMES]),
        MEAN_FILE: mean.astype(np.float32),
        PROBES_FILE: probes.astype(np.float32),
        META_FILE: meta,
    }


def write_sample(sample: dict, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    for name, value in sample.items():
        if name.endswith(".json"):
            text = json.dumps(value, indent=1) + "\n"
            (output_dir / name).write_text(text, encoding="ascii")
        else:
            np.save(output_dir / name, value, allow_pickle=False)


def load(data_dir: Path) -> Wake:
    """The committed sample; the arrays hold no Python object."""
    data_dir = Path(data_dir)
    meta = json.loads((data_dir / META_FILE).read_text(encoding="ascii"))
    arrays = {
        name: np.load(data_dir / name, allow_pickle=False)
        for name in (U_FILE, V_FILE, MASK_FILE, MEAN_FILE, PROBES_FILE)
    }
    shape = (FRAMES, len(meta["y"]), len(meta["x"]))
    for name in (U_FILE, V_FILE, MASK_FILE):
        if arrays[name].shape != shape:
            raise ValueError(f"{name}: shape {arrays[name].shape}, expected {shape}")
    return Wake(
        u=arrays[U_FILE].astype(float),
        v=arrays[V_FILE].astype(float),
        mask=arrays[MASK_FILE].astype(bool),
        mean=arrays[MEAN_FILE].astype(float),
        probes=arrays[PROBES_FILE].astype(float),
        x=np.array(meta["x"]),
        y=np.array(meta["y"]),
        meta=meta,
    )


# The analysis.


def vorticity(
    u: np.ndarray, v: np.ndarray, mask: np.ndarray, x: np.ndarray, y: np.ndarray
) -> np.ndarray:
    """dv/dx - du/dy [1/s] of fields [..., y, x] by central differences
    (one-sided at the border); NaN where the stencil touches a masked point."""
    dvdx = np.gradient(v, x, axis=-1)
    dudy = np.gradient(u, y, axis=-2)
    near = ndimage.binary_dilation(
        mask, structure=np.ones((1,) * (mask.ndim - 2) + (3, 3), bool)
    )
    return np.where(near, np.nan, dvdx - dudy)


def spectrum(series: np.ndarray, nperseg: int = NPERSEG):
    """Welch power spectral density [(m/s)^2/Hz] of a series at 20 Hz."""
    series = np.asarray(series, dtype=float)
    return signal.welch(series - series.mean(), fs=FPS, nperseg=nperseg)


def peak(freq: np.ndarray, power: np.ndarray, f_min: float = F_MIN) -> float:
    """The frequency of the largest peak above ``f_min``, refined by a
    parabola through the logarithm of the three bins around it."""
    k = int(np.argmax(np.where(freq > f_min, power, -np.inf)))
    a, b, c = np.log(power[k - 1 : k + 2])
    return float(freq[k] + 0.5 * (a - c) / (a - 2 * b + c) * (freq[1] - freq[0]))


def block_peaks(series: np.ndarray, blocks: int = BLOCKS) -> np.ndarray:
    """The peak frequency of each of ``blocks`` non-overlapping blocks
    (Hann window, zero-padded to 16384 points)."""
    out = []
    for part in np.array_split(np.asarray(series, dtype=float), blocks):
        windowed = (part - part.mean()) * np.hanning(part.size)
        power = np.abs(np.fft.rfft(windowed, 16384)) ** 2
        freq = np.fft.rfftfreq(16384, 1 / FPS)
        out.append(peak(freq, power))
    return np.array(out)


def strouhal(frequency: float) -> float:
    return frequency * DIAMETER / FREE_STREAM


def roshko(reynolds: float) -> float:
    """St = 0.212 - 2.7 / Re (Roshko 1954), valid for 200 <= Re < 2000."""
    slope, offset = ROSHKO
    return slope - offset / reynolds


def shadow_centre_x(wake: Wake) -> float:
    """x [m] of the centre of the mask's column below the cylinder (the
    shadow cast in -y keeps the cylinder's x extent), from the bottom row."""
    columns = wake.mask[0, 0]
    return float(wake.x[columns].mean())


def recirculation_end(wake: Wake, axis_y: float) -> float:
    """x [m] where the mean u on the row nearest ``axis_y`` turns positive
    behind the cylinder (linear interpolation)."""
    row = wake.mean[0, int(np.argmin(np.abs(wake.y - axis_y)))]
    behind = wake.x > shadow_centre_x(wake)
    xs, us = wake.x[behind], row[behind]
    negative = np.where(us < 0)[0]
    k = negative[-1]
    return float(xs[k] - us[k] * (xs[k + 1] - xs[k]) / (us[k + 1] - us[k]))


@dataclass(frozen=True)
class Analysis:
    frequency: dict  # Hz, mean of the four block peaks of v at each probe
    frequency_err: dict  # Hz, standard error of that mean (sd / 2)
    block_frequency: dict  # Hz, the four 100 s blocks at each probe
    welch_frequency: dict  # Hz, the peak of the Welch spectrum of v
    harmonic_u: float  # Hz, the peak of u at the 2D probe above 1.2 Hz
    strouhal: float  # from the 2D probe, with D and U of the paper
    strouhal_err: float  # from frequency_err alone
    roshko: float  # St of Roshko's correlation at Re = 413
    free_stream_sample: float  # m/s, mean u of the top row of the crop
    cylinder_x: float  # m, the centre of the shadow column
    axis_y: float  # m, the probes' row
    recirculation: float  # m, end of the mean recirculation behind the shadow
    vorticity_p99: float  # 1/s, 99th percentile of |omega| over the 60 frames
    masked_fraction: float  # of the crop's points, all 60 frames


def analyse(wake: Wake) -> Analysis:
    frequency, error, blocks, welch = {}, {}, {}, {}
    for k, name in enumerate(PROBES):
        welch[name] = peak(*spectrum(wake.probes[:, k, 1]))
        blocks[name] = block_peaks(wake.probes[:, k, 1])
        frequency[name] = float(blocks[name].mean())
        error[name] = float(blocks[name].std(ddof=1) / np.sqrt(BLOCKS))
    f_u, p_u = spectrum(wake.probes[:, 0, 0])
    axis_y = wake.meta["probes"]["2D"]["y"]
    omega = vorticity(wake.u, wake.v, wake.mask, wake.x, wake.y)
    return Analysis(
        frequency=frequency,
        frequency_err=error,
        block_frequency=blocks,
        welch_frequency=welch,
        harmonic_u=peak(f_u, p_u, f_min=1.2),
        strouhal=strouhal(frequency["2D"]),
        strouhal_err=strouhal(error["2D"]),
        roshko=roshko(REYNOLDS),
        free_stream_sample=float(np.nanmean(wake.mean[0, -1])),
        cylinder_x=shadow_centre_x(wake),
        axis_y=axis_y,
        recirculation=recirculation_end(wake, axis_y),
        vorticity_p99=float(np.nanpercentile(np.abs(omega), 99)),
        masked_fraction=float(wake.mask.mean()),
    )


# The figure.


def make_figure(data_dir: Path):
    wake = load(data_dir)
    result = analyse(wake)
    mm = 1e3
    extent = (
        wake.x[0] * mm - 0.525,
        wake.x[-1] * mm + 0.525,
        wake.y[0] * mm - 0.525,
        wake.y[-1] * mm + 0.525,
    )
    fig = plt.figure(figsize=(13, 9), constrained_layout=True)
    grid = fig.add_gridspec(2, 2)
    snap = fig.add_subplot(grid[0, 0])
    mean = fig.add_subplot(grid[0, 1])
    series = fig.add_subplot(grid[1, 0])
    power = fig.add_subplot(grid[1, 1])
    probe_xy = [(p["x"] * mm, p["y"] * mm) for p in wake.meta["probes"].values()]

    # Frame 0: the derived vorticity, the masked region grey.
    omega = vorticity(wake.u[0], wake.v[0], wake.mask[0], wake.x, wake.y)
    signed_image(
        snap,
        omega,
        label="vorticity ω (derived from u, v)",
        unit="1/s",
        extent=extent,
        interpolation="nearest",
    )
    snap.plot(
        *zip(*probe_xy, strict=True),
        "o",
        mfc="none",
        mec="k",
        ms=8,
        label="probes 2D and 5D",
    )
    snap.plot([], [], "s", color="0.85", label="masked: cylinder and shadows")
    snap.set_xlabel("x [mm] (flow to +x)")
    snap.set_ylabel("y [mm]")
    snap.set_title("Frame 0: vorticity by central differences")
    snap.legend(fontsize=7, loc="lower right")

    # The mean over 8000 frames: u and the streamlines of (mean u, mean v).
    signed_image(
        mean,
        wake.mean[0],
        label="mean u over 400 s",
        unit="m/s",
        extent=extent,
        interpolation="nearest",
    )
    mu, mv = (np.ma.masked_invalid(c) for c in wake.mean)
    mean.streamplot(
        wake.x * mm,
        wake.y * mm,
        mu,
        mv,
        color="k",
        linewidth=0.6,
        density=1.2,
        arrowsize=0.7,
    )
    mean.axvline(
        result.recirculation * mm,
        color=COLOURS[1],
        ls="--",
        label=f"end of mean recirculation, x = {result.recirculation * mm:.1f} mm",
    )
    mean.plot([], [], "-", color="k", lw=0.6, label="streamlines of the mean field")
    mean.set_xlim(extent[:2])
    mean.set_ylim(extent[2:])
    mean.set_xlabel("x [mm] (flow to +x)")
    mean.set_ylabel("y [mm]")
    mean.set_title("Time-mean field, 8000 frames")
    mean.legend(fontsize=7, loc="lower right")

    # v at the 2D probe: the first 30 s, the 60 committed frames shaded.
    t = np.arange(wake.probes.shape[0]) / FPS
    first = t < 30
    series.plot(
        t[first],
        wake.probes[first, 0, 1] * mm,
        "-",
        color=COLOURS[0],
        lw=0.9,
        label="v at probe 2D [processed]",
    )
    series.plot(
        t[first],
        wake.probes[first, 0, 0] * mm,
        "-",
        color=COLOURS[2],
        lw=0.9,
        alpha=0.8,
        label="u at probe 2D [processed]",
    )
    series.axvspan(
        0, FRAMES / FPS, color="0.5", alpha=0.15, label="frames 0-59 (the field sample)"
    )
    series.set_ylim(-45, 60)
    series.set_xlabel("time [s] (20 frames per second)")
    series.set_ylabel("velocity [mm/s]")
    series.set_title("Velocity on the wake axis, 2 D behind the cylinder")
    series.legend(fontsize=7, loc="upper center", ncol=3)

    # The spectra at the 2D probe.
    for k, (component, colour, style) in enumerate(
        (("u", COLOURS[2], "-"), ("v", COLOURS[0], "-"))
    ):
        f, p = spectrum(wake.probes[:, 0, k])
        power.semilogy(
            f[1:],
            p[1:],
            style,
            color=colour,
            lw=1.0,
            label=f"{component} at probe 2D (Welch, 102.4 s windows)",
        )
    power.axvline(
        F_PUBLISHED,
        color=COLOURS[1],
        ls=":",
        label=f"published shedding frequency {F_PUBLISHED} Hz",
    )
    power.axvline(
        2 * F_PUBLISHED, color=COLOURS[1], ls="-.", lw=0.8, label="twice that"
    )
    power.set_xlim(0, 4)
    power.set_xlabel("frequency [Hz]")
    power.set_ylabel("power spectral density [(m/s)²/Hz]")
    power.set_title(
        f"Spectra: v peaks at {result.frequency['2D']:.3f} ± "
        f"{result.frequency_err['2D']:.3f} Hz, St = {result.strouhal:.3f}"
    )
    power.legend(fontsize=7, loc="upper right")

    label_status(fig, "processed")
    add_credit(
        fig,
        "Data: J. Shang, J. Tu, 'Particle image velocimetry (PIV) data of flow "
        "past a cylinder', Zenodo, 2026, doi 10.5281/zenodo.20765567, CC BY 4.0 "
        "https://creativecommons.org/licenses/by/4.0/. A crop of 60 frames, the "
        "time mean, and two probe series extracted by this project; vorticity, "
        "streamlines and spectra are this project's processing.",
    )
    return fig
