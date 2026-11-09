"""NIST Numisheet 2020 DP980: a tension, compression, tension test of a sheet steel.

Status of the figure: *processed* (engineering stress is the mean force of two
load cells over the original cross-section; engineering strain is a virtual
extensometer of 23.6 mm gauge length from stereo digital image correlation;
both are NIST's processing, and NIST calls the stress-strain curves "provided
for reference only"). The elastic line, the 0.2 % offset line and the chord of
the unloading are computed here and drawn apart from the measurement.

The protocol (NIST's report, section 2.2.1): tension to about 75 % of the
uniform strain, a 10 s hold, compression back to an engineering strain near
zero, a 10 s hold, tension again until the specimen breaks, all in
displacement control at a nominal 0.00025 per second. The hysteresis loop
runs from the stress maximum of the first tension through the compression and
back along the reload to the same strain, closed by a straight segment
(``Loop``).

The record gives no uncertainty for these columns. It states a noise floor of
the local DIC strain (263 um/m for this test, over a 0.86 mm virtual gauge)
and a difference of typically less than 300 N between the two load cells,
whose mean is the force. The module derives the rest: the scatter of the
extensometer strain before the force ramp, the standard error of the elastic
fit, and the dependence of E on the stress window (``window_sensitivity``).
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.fit import FitResult, fit_curve
from pbc.data.plotting import COLOURS, add_credit, label_status

STEM = "C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain"
FILE = f"{STEM}.csv"
ATTRIBUTES = f"{STEM}-attributes.csv"
FIELDS = ("Time", "Estrain", "Estress", "Tstrain", "Tstress")
UNITS = {
    "Time": "s",
    "Estress": "MPa",
    "Estrain": "mm/mm",
    "Tstress": "MPa",
    "Tstrain": "mm/mm",
}
# The specimen, from the file name (NIST's naming convention, Table 3):
# thickness 1.424 mm, width 17.93 mm, 0 degrees to the rolling direction.
THICKNESS_MM = 1.424
WIDTH_MM = 17.93
# The stress window of the elastic fit [MPa] on the first loading, and the
# windows of the sensitivity analysis.
ELASTIC_WINDOW = (100.0, 400.0)
WINDOWS = ((50.0, 300.0), (100.0, 300.0), (100.0, 400.0), (150.0, 450.0))
OFFSET = 0.002
# The record's statements (report sections 2.2.1 and 4.2).
LOAD_CELL_DIFFERENCE_N = 300.0
DIC_NOISE_FLOOR = 263e-6


@dataclass(frozen=True)
class Test:
    time: np.ndarray  # s
    strain: np.ndarray  # engineering strain, mm/mm
    stress: np.ndarray  # engineering stress, MPa
    true_strain: np.ndarray  # ln(1 + e), computed by NIST
    true_stress: np.ndarray  # S (1 + e), computed by NIST


@dataclass(frozen=True)
class Segments:
    """Indices of the protocol: the first reversal (the highest stress of the
    first tension), the end of the hold (the largest strain before the
    compression), the second reversal (the most compressive stress), and the
    end of the second hold (the smallest strain just after it)."""

    reversal: int
    hold_end: int
    compression: int
    second_hold_end: int


def read_attributes(path: Path) -> dict[str, str]:
    """Units of the columns, from NIST's ``-attributes.csv``."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "Variable" not in rows[0] or "Units" not in rows[0]:
        raise ValueError(f"{path}: not a NIST attributes file")
    return {row["Variable"]: row["Units"] for row in rows}


def read_stress_strain(path: Path) -> Test:
    """Read a NIST Numisheet ``-Stress-Strain.csv``: a header row and five
    numeric columns."""
    with open(path, newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    if tuple(header) != FIELDS:
        raise ValueError(f"{path}: columns {header}, expected {list(FIELDS)}")
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    if data.shape[1] != len(FIELDS):
        raise ValueError(f"{path}: {data.shape[1]} columns")
    column = {name: data[:, k] for k, name in enumerate(FIELDS)}
    return Test(
        column["Time"],
        column["Estrain"],
        column["Estress"],
        column["Tstrain"],
        column["Tstress"],
    )


def load(data_dir: Path) -> Test:
    return read_stress_strain(Path(data_dir) / FILE)


def segments(test: Test) -> Segments:
    compression = int(np.argmin(test.stress))
    reversal = int(np.argmax(test.stress[:compression]))
    hold_end = reversal + int(np.argmax(test.strain[reversal:compression]))
    # The second hold: the strain keeps falling for a few seconds after the
    # most compressive stress, as the stress relaxes at a fixed displacement.
    second = compression + int(np.argmin(test.strain[compression : compression + 30]))
    return Segments(reversal, hold_end, compression, second)


def preload(test: Test) -> np.ndarray:
    """The rows before the force ramp: the stress has not yet exceeded 1 MPa."""
    return np.arange(int(np.argmax(np.abs(test.stress) > 1.0)))


def elastic_fit(test: Test, window: tuple[float, float] = ELASTIC_WINDOW) -> FitResult:
    """Fit S = E e + S0 to the first loading inside a stress window.

    E is in GPa, S0 in MPa; without a per-point uncertainty the standard
    errors come from the scatter of the residuals.
    """
    first = slice(0, segments(test).reversal)
    e, s = test.strain[first], test.stress[first]
    keep = (s > window[0]) & (s < window[1])
    return fit_curve(
        lambda x, modulus, s0: modulus * 1e3 * x + s0,
        e[keep],
        s[keep],
        [200.0, 0.0],
        names=("E", "S0"),
    )


def window_sensitivity(test: Test) -> dict[tuple[float, float], FitResult]:
    """E for each stress window of ``WINDOWS``: the curve of a dual-phase
    steel bends early, so E depends on where the line is fitted."""
    return {window: elastic_fit(test, window) for window in WINDOWS}


def offset_yield(test: Test, result: FitResult, offset: float = OFFSET) -> float:
    """Stress [MPa] where the first loading crosses the elastic line shifted by
    ``offset`` in strain, interpolated between the two samples."""
    first = slice(0, segments(test).reversal)
    e, s = test.strain[first], test.stress[first]
    line = result.value("E") * 1e3 * (e - offset) + result.value("S0")
    gap = s - line
    k = int(np.argmax((gap < 0) & (e > offset)))
    w = gap[k - 1] / (gap[k - 1] - gap[k])
    return float(s[k - 1] + w * (s[k] - s[k - 1]))


@dataclass(frozen=True)
class Loop:
    """The hysteresis loop as a closed path in the (e, S) plane.

    ``start`` is the row of the highest stress of the first tension (the
    stress maximum, ``Segments.reversal``; the strain still rises a little
    into the hold after it). ``end`` is the first row of the reload, after the
    most compressive stress, whose strain is at least that of ``start``. The
    measured rows ``start`` to ``end`` are closed by a straight segment from
    ``end`` back to ``start``; ``gap_strain`` and ``gap_stress`` are that
    segment's extent (end minus start). ``work`` is the closed integral of
    S de [MJ/m^3]: positive when the path runs clockwise in the (e, S) plane,
    as a loop does whose reloading branch lies above its unloading branch,
    and then equal to the enclosed area and to the net work per volume done on
    the specimen over the cycle. ``closing`` is the part of ``work`` that the
    closing segment contributes."""

    rows: slice
    start: int
    end: int
    work: float
    closing: float
    gap_strain: float
    gap_stress: float


def loop(test: Test) -> Loop:
    """The hysteresis loop, closed and integrated as ``Loop`` defines it:
    trapezoids over the measured rows plus the straight closing segment."""
    seg = segments(test)
    start = seg.reversal
    end = seg.compression + int(
        np.argmax(test.strain[seg.compression :] >= test.strain[start])
    )
    rows = slice(start, end + 1)
    e, s = test.strain, test.stress
    measured = float(np.trapezoid(s[rows], e[rows]))
    closing = float(0.5 * (s[end] + s[start]) * (e[start] - e[end]))
    return Loop(
        rows,
        start,
        end,
        measured + closing,
        closing,
        float(e[end] - e[start]),
        float(s[end] - s[start]),
    )


def unloading_modulus(test: Test, high: float = 950.0, low: float = 0.0) -> float:
    """Chord slope [GPa] of the unloading after the hold, between two stresses
    of the first unloading (the stress falls from the hold to zero)."""
    seg = segments(test)
    rows = np.arange(seg.hold_end, seg.compression)
    zero = rows[int(np.argmax(test.stress[rows] < 0))]
    rows = rows[rows <= zero]
    s, e = test.stress[rows], test.strain[rows]
    keep = (s < high) & (s > low)
    slope, _ = np.polyfit(e[keep], s[keep], 1)
    return float(slope / 1e3)


def reload_maximum(test: Test) -> int:
    """Row of the highest stress of the final tension: necking starts there,
    and beyond it the strain is no longer uniform over the gauge length."""
    start = segments(test).compression
    return start + int(np.argmax(test.stress[start:]))


def stress_from_load_cells(test: Test) -> float:
    """Half the stated load-cell difference over the original cross-section
    [MPa]: the scale on which the friction of the anti-buckling fixture can
    shift the mean force."""
    return LOAD_CELL_DIFFERENCE_N / 2 / (THICKNESS_MM * WIDTH_MM)


def make_figure(data_dir: Path) -> plt.Figure:
    test = load(data_dir)
    seg = segments(test)
    result = elastic_fit(test)
    modulus = result.value("E")
    yield_stress = offset_yield(test, result)
    cycle = loop(test)
    rows = cycle.rows
    neck = reload_maximum(test)
    e, s, t = test.strain, test.stress, test.time

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    (ax_full, ax_low), (ax_time, ax_res) = axes
    point = {"marker": "o", "ms": 2.0, "lw": 0.6}
    parts = (
        (slice(0, seg.reversal + 1), "1: first tension", COLOURS[0]),
        (
            slice(seg.reversal, seg.compression + 1),
            "2: unloading, compression",
            COLOURS[1],
        ),
        (slice(seg.compression, None), "3: tension to fracture", COLOURS[2]),
    )
    for part, label, colour in parts:
        ax_full.plot(e[part], s[part], color=colour, label=label, **point)
    ax_full.fill(
        e[rows],
        s[rows],
        color=COLOURS[4],
        alpha=0.25,
        label=f"loop, closed at e = {e[cycle.start]:.4f}: "
        f"enclosed area {cycle.work:.1f} MJ/m^3 (clockwise)",
    )
    ax_full.plot(
        e[cycle.start],
        s[cycle.start],
        "k^",
        ms=6,
        label=f"stress maximum, loop start: {s[cycle.start]:.0f} MPa "
        f"at e = {e[cycle.start]:.4f}",
    )
    ax_full.plot(
        e[neck],
        s[neck],
        "kv",
        ms=6,
        label=f"necking starts: {s[neck]:.0f} MPa at e = {e[neck]:.3f}",
    )
    ax_full.axhline(0, color="0.5", lw=0.8)
    ax_full.set_xlabel("engineering strain e [mm/mm]")
    ax_full.set_ylabel("engineering stress S [MPa]")
    ax_full.set_title(
        "Processed: tension, compression, tension again (measured)", fontsize=10
    )
    ax_full.legend(fontsize=7, loc="lower right")

    first = slice(0, seg.reversal + 1)
    mask = e[first] < 0.012
    ax_low.plot(
        e[first][mask],
        s[first][mask],
        color=COLOURS[0],
        marker="o",
        ms=2.5,
        ls="none",
        label="measured, first tension",
    )
    grid = np.linspace(0, 0.012, 200)
    line = modulus * 1e3 * grid + result.value("S0")
    shown = line < 1000
    ax_low.plot(
        grid[shown],
        line[shown],
        color=COLOURS[1],
        ls="--",
        lw=1.2,
        label=f"elastic fit, {ELASTIC_WINDOW[0]:.0f}-{ELASTIC_WINDOW[1]:.0f} MPa: "
        f"E = {modulus:.0f} GPa",
    )
    shifted = modulus * 1e3 * (grid - OFFSET) + result.value("S0")
    keep = (shifted > 0) & (shifted < 1000)
    ax_low.plot(
        grid[keep],
        shifted[keep],
        color=COLOURS[3],
        ls=":",
        lw=1.2,
        label="the same line shifted by 0.2 %",
    )
    ax_low.axhline(
        yield_stress,
        color="0.5",
        lw=0.8,
        label=f"0.2 % offset yield: {yield_stress:.0f} MPa",
    )
    ax_low.set_xlim(0, 0.012)
    ax_low.set_ylim(0, 1050)
    ax_low.set_xlabel("engineering strain e [mm/mm]")
    ax_low.set_ylabel("engineering stress S [MPa]")
    ax_low.set_title(
        "Processed: elastic regime and yield (fit is a model)", fontsize=10
    )
    ax_low.legend(fontsize=7, loc="lower right")

    ax_time.plot(t, s, color=COLOURS[0], marker=".", ms=2, lw=0.6, label="stress")
    ax_time.axvspan(
        t[seg.reversal],
        t[seg.hold_end],
        color="0.85",
        label="holds",
    )
    ax_time.axvspan(t[seg.compression], t[seg.second_hold_end], color="0.85")
    ax_time.axhline(0, color="0.5", lw=0.8)
    ax_time.set_xlabel("time [s]")
    ax_time.set_ylabel("engineering stress S [MPa]")
    ax_time.set_title(
        "Processed: the protocol in time (4 images/s, then 1 image/s)", fontsize=10
    )
    ax_time.legend(fontsize=7, loc="lower right")

    fitted = (s[first] > ELASTIC_WINDOW[0]) & (s[first] < ELASTIC_WINDOW[1])
    upto = s[first] < 650
    model = modulus * 1e3 * e[first] + result.value("S0")
    ax_res.plot(
        s[first][upto],
        (s[first] - model)[upto],
        color=COLOURS[2],
        marker=".",
        ls="none",
        label="measured minus elastic line",
    )
    ax_res.axvspan(*ELASTIC_WINDOW, color="0.9", label="fit window")
    ax_res.axhline(0, color="0.5", lw=0.8)
    rms = float(np.sqrt(np.mean((s[first] - model)[fitted] ** 2)))
    ax_res.set_xlabel("engineering stress S [MPa]")
    ax_res.set_ylabel("residual S - (E e + S0) [MPa]")
    ax_res.set_title(
        f"Residuals: {rms:.1f} MPa rms in the window, then the curve bends", fontsize=10
    )
    ax_res.legend(fontsize=7, loc="lower left")
    add_credit(
        fig,
        "Data: NIST, Luecke, Rust, Iadicola, 'Data for Numisheet 2020 uniaxial tensile "
        "and tension/compression tests', doi 10.18434/M32202, v1.2.0; file "
        f"{FILE}, unmodified (NIST data, 17 U.S.C. 105). Fits, offset line and loop "
        "area: this figure's code (pbc.data.reference.nist_numisheet), not part of "
        "the record.",
    )
    label_status(fig, "processed")
    return fig
