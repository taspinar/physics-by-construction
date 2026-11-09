"""Lycopodium spores: the dark ring of the diffraction halo at two wavelengths,
against the spore diameters measured under the microscope.

Status of the figure: *processed* (line profiles that the creators extracted
from photographs with the Tracker software; morphometry that they computed
with ImageJ; here centred, folded, and smoothed).

A layer of spores on glass diffracts a laser beam into a halo of rings. By
Babinet's principle each opaque spore diffracts like a hole of its size, and
spores at random places add their intensities, so the halo is the Airy
pattern of one disk of diameter d, averaged over the diameters present:
I(q) ~ sum over spores of d^4 [2 J1(pi d q) / (pi d q)]^2 with q = sin(theta)
/ lambda. Its rings depend on q alone, so their angles scale with the
wavelength.

The record does not state the unit of the profile's x coordinate, the
distance from the spores to the screen, or which photographs the profiles
come from, and the photographs saturate the camera in the centre. So the
scale-free test is the one this module makes: the radius of the dark ring
at 405 nm over that at 632.8 nm, against the wavelength ratio 0.640. The
ensemble model from the microscope diameters gives the q of each ring; with
one ring measured the record does not settle whether the dark ring is the
first or the second minimum (``ring_order``), and the implied screen distance
is given for both, in the profile's unit.

The uncertainty of a ring radius is not in the record: it is taken here as
half the range of the radius over the smoothing widths ``WIDTHS`` (a
sensitivity range of the analysis), and the two sides of the profile are
compared as a check.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks
from scipy.special import j1

from pbc.data.plotting import COLOURS, add_credit, label_status

PROFILES = {0.6328: "profile_633nm.csv", 0.405: "profile_405nm.csv"}  # um -> file
MORPHOMETRY = {
    "x160": "Lycopodium_Morphometry_x160.csv",
    "x80": "Lycopodium_Morphometry_x80.csv",
}
PROFILE_HEADER = ("n", "x", "y", "luma")
WHOLE_SPORE = 15.0  # um: smaller particles are fragments of spore walls
SATURATED = 250.0  # luma at and above which the camera is taken as saturated
WIDTH = 1.0  # smoothing width of the nominal analysis, in units of x
WIDTHS = (0.5, 0.75, 1.0, 1.5, 2.0)  # the sensitivity range
PROMINENCE = 2.0  # luma: smaller dips are not candidates
SIDE_WINDOW = 3.0  # units of x: a side's minimum is searched this near the fold's


@dataclass(frozen=True)
class Profile:
    wavelength: float  # um
    n: np.ndarray
    x: np.ndarray  # Tracker coordinate along the scanline, unit not stated
    y: np.ndarray  # constant: the height of the scanline
    luma: np.ndarray  # 0..255


def read_profile(path: Path, wavelength: float) -> Profile:
    """Read a profile CSV written by ``tools/datasets/lycopodium_xlsx_to_csv.py``."""
    lines = [
        line
        for line in Path(path).read_text(encoding="ascii").splitlines()
        if not line.startswith("#")
    ]
    if tuple(lines[0].split(",")) != PROFILE_HEADER:
        raise ValueError(f"{path}: header {lines[0]!r}, expected {PROFILE_HEADER}")
    values = np.array([[float(v) for v in line.split(",")] for line in lines[1:]])
    n, x, y, luma = values.T
    return Profile(wavelength, n.astype(int), x, y, luma)


def load_profiles(data_dir: Path) -> dict[float, Profile]:
    return {w: read_profile(Path(data_dir) / f, w) for w, f in PROFILES.items()}


def read_morphometry(path: Path) -> dict[str, np.ndarray]:
    """Read a morphometry CSV of the sample: an ImageJ result of the record,
    ';'-separated, re-encoded from Latin-1 to UTF-8 by
    ``tools/datasets/lycopodium_morphometry_to_utf8.py``.

    The first column (no name) is the particle number, and an empty column
    separates ImageJ's measurements from the creators' r^2, r and d; columns
    are returned by name, without the empty one.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = [h.strip() for h in lines[0].split(";")]
    rows = [line.split(";") for line in lines[1:] if line.strip()]
    if any(len(r) != len(header) for r in rows):
        raise ValueError(f"{path}: rows of unequal length")
    out = {}
    for k, name in enumerate(header):
        if k == 0:
            out["number"] = np.array([int(r[0]) for r in rows])
        elif name:
            out[name] = np.array([float(r[k]) for r in rows])
    return out


def diameter_column(table: dict[str, np.ndarray]) -> np.ndarray:
    return table["d (µm)"]


def whole_spores(table: dict[str, np.ndarray]) -> np.ndarray:
    """Diameters [um] of the particles larger than ``WHOLE_SPORE``."""
    d = diameter_column(table)
    return d[d > WHOLE_SPORE]


def summary(d: np.ndarray) -> tuple[int, float, float, float]:
    """Count, mean, standard deviation, and standard error of the mean."""
    sd = float(np.std(d, ddof=1))
    return d.size, float(np.mean(d)), sd, sd / np.sqrt(d.size)


# The diffraction profile.


def centre(profile: Profile, inner: float = 3.0) -> float:
    """The x about which the profile is most nearly mirror-symmetric: the
    least mean square difference of luma at c + r and c - r for inner < r <
    R, on a grid of 0.005 in x within 3 of x = 0."""
    span = min(-profile.x[0], profile.x[-1]) - 3.0
    step = float(np.mean(np.diff(profile.x)))
    r = np.arange(inner, span, step)

    def asymmetry(c):
        left = np.interp(c - r, profile.x, profile.luma)
        right = np.interp(c + r, profile.x, profile.luma)
        return float(np.mean((right - left) ** 2))

    grid = np.arange(-3.0, 3.0 + 1e-9, 0.005)
    return float(grid[np.argmin([asymmetry(c) for c in grid])])


def folded(profile: Profile, c: float) -> tuple[np.ndarray, np.ndarray]:
    """Radius from ``c`` and the mean of the luma on both sides, sampled at the
    profile's step."""
    step = float(np.mean(np.diff(profile.x)))
    r = np.arange(0.0, min(c - profile.x[0], profile.x[-1] - c), step)
    left = np.interp(c - r, profile.x, profile.luma)
    right = np.interp(c + r, profile.x, profile.luma)
    return r, (left + right) / 2


def _smooth(values: np.ndarray, width: float, step: float) -> np.ndarray:
    k = max(3, round(width / step) | 1)
    return uniform_filter1d(values, k, mode="nearest")


def _vertex(r: np.ndarray, m: np.ndarray, i: int) -> float:
    """The vertex of the parabola through the three samples around ``i``."""
    a, b, c = m[i - 1], m[i], m[i + 1]
    denominator = a - 2 * b + c
    shift = 0.0 if denominator == 0 else 0.5 * (a - c) / denominator
    return float(r[i] + shift * (r[1] - r[0]))


def core_radius(r: np.ndarray, luma: np.ndarray) -> float:
    """The largest radius at which the folded profile is saturated."""
    return float(r[luma >= SATURATED].max())


def dark_ring(profile: Profile, width: float = WIDTH, c: float | None = None) -> float:
    """Radius of the dark ring: the most prominent minimum of the folded
    profile, smoothed by a moving average of ``width``, outside the
    saturated core."""
    c = centre(profile) if c is None else c
    r, luma = folded(profile, c)
    m = _smooth(luma, width, r[1] - r[0])
    found, props = find_peaks(-m, prominence=PROMINENCE)
    keep = r[found] > core_radius(r, luma)
    i = found[keep][np.argmax(props["prominences"][keep])]
    return _vertex(r, m, i)


def bright_ring(profile: Profile, width: float = WIDTH) -> float:
    """Radius of the first maximum with ``PROMINENCE`` beyond the dark ring."""
    c = centre(profile)
    dark = dark_ring(profile, width, c)
    r, luma = folded(profile, c)
    m = _smooth(luma, width, r[1] - r[0])
    found, _ = find_peaks(m, prominence=PROMINENCE)
    i = found[r[found] > dark][0]
    return _vertex(r, m, i)


def side_rings(profile: Profile, width: float = WIDTH) -> tuple[float, float]:
    """The dark ring on the left and on the right side separately: the lowest
    point of each smoothed side within ``SIDE_WINDOW`` of the folded value."""
    c = centre(profile)
    target = dark_ring(profile, width, c)
    step = float(np.mean(np.diff(profile.x)))
    m = _smooth(profile.luma, width, step)
    out = []
    for sign in (-1, 1):
        r = sign * (profile.x - c)
        near = np.flatnonzero(np.abs(r - target) <= SIDE_WINDOW)
        i = near[np.argmin(m[near])]
        out.append(float(r[i]))
    return out[0], out[1]


@dataclass(frozen=True)
class Ring:
    radius: float  # nominal analysis, units of x
    uncertainty: float  # half the range over WIDTHS
    radii: tuple[float, ...]  # one per width of WIDTHS


def ring(profile: Profile) -> Ring:
    c = centre(profile)
    radii = tuple(dark_ring(profile, w, c) for w in WIDTHS)
    return Ring(dark_ring(profile, WIDTH, c), (max(radii) - min(radii)) / 2, radii)


def ratio(profiles: dict[float, Profile]) -> tuple[float, float]:
    """r(405 nm) / r(632.8 nm) with its uncertainty from both rings."""
    short, long = ring(profiles[0.405]), ring(profiles[0.6328])
    value = short.radius / long.radius
    relative = np.hypot(
        short.uncertainty / short.radius, long.uncertainty / long.radius
    )
    return value, value * relative


# The ensemble model.


def ensemble(q: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Airy intensity of spores of the diameters ``d`` [um] at q = sin(theta)
    / lambda [1/um], normalised to one at q = 0."""
    u = np.pi * np.outer(np.asarray(q, float), d)
    safe = np.where(u > 0, u, 1.0)
    amplitude = np.where(u > 0, 2 * j1(safe) / safe, 1.0)
    return (amplitude**2 * d**4).sum(axis=1) / (d**4).sum()


def model_extrema(d: np.ndarray, count: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """q [1/um] of the first ``count`` minima and maxima of ``ensemble``."""
    q = np.linspace(1e-5, 6.0 / d.mean(), 30001)
    intensity = ensemble(q, d)
    minima, _ = find_peaks(-intensity)
    maxima, _ = find_peaks(intensity)
    return q[minima[:count]], q[maxima[:count]]


def screen_distance(radius: float, q: float, wavelength: float) -> float:
    """Distance to the screen, in the unit of ``radius``, at which a ring of
    ``q`` [1/um] at ``wavelength`` [um] has that radius on a flat screen."""
    return radius / np.tan(np.arcsin(q * wavelength))


def ring_order(profiles: dict[float, Profile], d: np.ndarray) -> dict[str, float]:
    """The bright-to-dark radius ratio of each profile against the model's
    for a dark ring of order 1 and of order 2."""
    minima, maxima = model_extrema(d)
    out = {
        f"measured {w} um": bright_ring(p) / dark_ring(p) for w, p in profiles.items()
    }
    out["model order 1"] = float(maxima[0] / minima[0])
    out["model order 2"] = float(maxima[1] / minima[1])
    return out


def make_figure(data_dir: Path) -> plt.Figure:
    profiles = load_profiles(data_dir)
    tables = {k: read_morphometry(Path(data_dir) / f) for k, f in MORPHOMETRY.items()}
    d = whole_spores(tables["x160"])
    minima, _ = model_extrema(d)
    rings = {w: ring(p) for w, p in profiles.items()}
    value, error = ratio(profiles)
    expected = 0.405 / 0.6328

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    (ax_raw, ax_fold), (ax_d, ax_r) = axes
    styles = {0.6328: (COLOURS[1], "-"), 0.405: (COLOURS[0], "--")}

    for w, p in profiles.items():
        colour, ls = styles[w]
        c = centre(p)
        ax_raw.plot(
            p.x - c, p.luma, color=colour, ls=ls, lw=0.7, label=f"{w * 1000:.1f} nm"
        )
        for sign in (-1, 1):
            ax_raw.axvline(sign * rings[w].radius, color=colour, ls=":", lw=0.9)
    ax_raw.axhline(
        SATURATED, color="0.4", lw=0.8, label=f"saturated (luma >= {SATURATED:.0f})"
    )
    ax_raw.set_xlabel("x - centre [unit of the record, not stated]")
    ax_raw.set_ylabel("luma [0-255, camera brightness]")
    ax_raw.set_title("Processed: the two line profiles; dotted: dark ring", fontsize=10)
    ax_raw.legend(fontsize=8, loc="upper right")

    for w, p in profiles.items():
        colour, ls = styles[w]
        r, luma = folded(p, centre(p))
        m = _smooth(luma, WIDTH, r[1] - r[0])
        ax_fold.plot(
            r / w,
            m,
            color=colour,
            ls=ls,
            lw=1.2,
            label=f"{w * 1000:.1f} nm, folded, moving average {WIDTH} x",
        )
        ax_fold.axvline(rings[w].radius / w, color=colour, ls=":", lw=0.9)
    ax_fold.set_xlim(0, 60)
    ax_fold.set_xlabel("radius / wavelength [unit of x per um]")
    ax_fold.set_ylabel("luma [0-255, camera brightness]")
    ax_fold.set_title(
        "Processed: on radius / wavelength the dark rings nearly coincide",
        fontsize=10,
    )
    ax_fold.legend(fontsize=8, loc="upper right")

    bins = np.arange(15, 52, 1.5)
    for (name, table), colour, hatch in zip(
        tables.items(), (COLOURS[2], COLOURS[3]), ("", "//"), strict=True
    ):
        spores = whole_spores(table)
        n, mean, sd, sem = summary(spores)
        ax_d.hist(
            spores,
            bins=bins,
            density=True,
            histtype="step",
            color=colour,
            hatch=hatch,
            lw=1.4,
            label=f"{name}: n = {n}, mean {mean:.2f} +- {sem:.2f} um, sd {sd:.2f}",
        )
    ax_d.set_xlabel("spore diameter d [um] (ImageJ, from the area)")
    ax_d.set_ylabel("fraction per um [1/um]")
    ax_d.set_title("Processed: microscope diameters, whole spores (d > 15 um)")
    ax_d.legend(fontsize=7.5, loc="upper left")
    ax_d.set_ylim(0, 0.26)

    lam = np.array(sorted(profiles))
    radius = np.array([rings[w].radius for w in lam])
    sigma = np.array([rings[w].uncertainty for w in lam])
    slope = float(np.sum(radius * lam / sigma**2) / np.sum(lam**2 / sigma**2))
    ax_r.errorbar(
        lam * 1000,
        radius,
        yerr=sigma,
        fmt="o",
        color=COLOURS[0],
        capsize=4,
        label="dark ring (bars: half-range over smoothing widths)",
    )
    grid = np.linspace(0, 0.7, 50)
    ax_r.plot(
        grid * 1000,
        slope * grid,
        color=COLOURS[1],
        ls="--",
        label="model: radius proportional to wavelength",
    )
    ax_r.set_xlim(0, 700)
    ax_r.set_ylim(0, None)
    ax_r.set_xlabel("wavelength [nm]")
    ax_r.set_ylabel("dark-ring radius [unit of x]")
    ax_r.set_title(
        f"Processed: r(405)/r(632.8) = {value:.3f} +- {error:.3f}; "
        f"wavelength ratio {expected:.3f}",
        fontsize=10,
    )
    ax_r.legend(fontsize=8, loc="upper left")
    for order, q in ((1, minima[0]), (2, minima[1])):
        distance = screen_distance(rings[0.6328].radius, q, 0.6328)
        ax_r.annotate(
            f"if it is minimum {order}: screen at {distance:.0f} units of x (632.8 nm)",
            (290, (0.12 if order == 1 else 0.05) * ax_r.get_ylim()[1]),
            fontsize=8,
        )
    add_credit(
        fig,
        "Data: O. Voronkin, S. Lushchin, 'Morphometry and Optical Data of "
        "Lycopodium Spores for the Study of Diffraction and Interference', "
        "Zenodo, doi 10.5281/zenodo.15846643, CC BY 4.0; intensity profiles "
        "converted from XLSX to CSV, values unchanged; morphometry CSVs "
        "re-encoded to UTF-8, values unchanged. Centring, folding, smoothing, "
        "ring radii, and the model: this figure's code "
        "(pbc.data.reference.lycopodium), not part of the record.",
    )
    label_status(fig, "processed")
    return fig
