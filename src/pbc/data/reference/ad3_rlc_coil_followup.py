"""The coil-loss follow-up's bench session of 2026-11-28 (F155 part 2b,
Issue #619): the registered sweeps M0 to M3 and M5 of the series RLC
circuit of the F140 pilot, measured with an Analog Discovery 3, the
readings M4 of a Mastech MAS830BC multimeter, the session's records, the
evaluation of the frozen registration's rules made the same day, and one
diagnostic sweep of 2026-11-26 made before the freeze.

Status of the figure: *processed*. The committed part of the dataset is
every file of the session and of the diagnostic sweep but three: the raw
samples of the early M0 (attempt 1, recorded as failed) and of the
diagnostic sweep, and the evaluation's ``view.html``, which are in the
archive the card names. The device's serial number is replaced by
``AD3-001`` (``MANIFEST.tsv``).

This module reads what was recorded, and nothing else: the session's
attempts (``session.toml``), the readings (``readings.toml``), each sweep's
run record and its points as the physics lab wrote them (``points.csv``:
gain and phase of channel 2 over channel 1 at each frequency, from the
least-squares phasor fit of each record), and the evaluation's report. The
registered quantities and the outcomes are computed by the Research
Workspace (``pbc.products.research_workspace``, its pinned outcome code),
not here. Nothing here explains a reading or a difference between sweeps.
"""

import csv
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

from pbc.data.figure_provenance import REFERENCE as REFERENCE_ROLE
from pbc.data.figure_provenance import FigureProvenance, role
from pbc.data.plotting import COLOURS

DATASET = "ad3-rlc-coil-followup"
EXPORTS = "exports"
SESSION = "2026-11-28-coil-loss"
DIAGNOSTIC = "2026-11-26-pilot-input-diagnostic"
EVALUATION = "evaluation-2026-11-28"
RUN, POINTS, RAW = "run.json", "points.csv", "raw.csv"
SESSION_FILE, READINGS_FILE = "session.toml", "readings.toml"
NOTES = ("M4-first-attempt-invalid.md", "meter-check-exploratory.md")
DEVICE_ID = "AD3-001"
# The registered thresholds of a measurable mismatch of the channels (G2 of
# the frozen registration), drawn as reference lines on M3.
DPHI_THRESHOLD_DEG = 0.3
DG_THRESHOLD = 0.003
# The window of the capacitor-node panel around the -90 degree crossing
# (kHz), where the sweeps differ; outside it they overlap at this scale.
CROSSING_WINDOW_KHZ = (30.0, 80.0)
REFERENCE = FigureProvenance(
    status="processed",
    dataset=DATASET,
    processing="The points of each sweep as the physics lab recorded them"
    " (points.csv: the gain and phase of channel 2 over channel 1 from the"
    " least-squares phasor fit of each record), unchanged; the gain of the"
    " same-node sweep M3 is drawn as gain - 1. No outcome is computed for the"
    " figure: the registered rules are applied by the Research Workspace.",
)


@dataclass(frozen=True)
class Attempt:
    """One ``[[sweep]]`` of ``session.toml``, as the owner recorded it."""

    measurement: str
    attempt: int
    directory: str
    outcome: str
    reason: str


@dataclass(frozen=True)
class Reading:
    """One ``[[reading]]`` of ``readings.toml`` (M4), in ohm."""

    quantity: str
    number: int
    range_ohm: float
    resolution_ohm: float
    value_ohm: float
    time: str


@dataclass(frozen=True)
class Points:
    """A sweep's recorded points: frequency (Hz), gain (V/V), phase
    (degrees)."""

    frequency_hz: tuple[float, ...]
    gain: tuple[float, ...]
    phase_deg: tuple[float, ...]


def session_dir(data_dir: Path) -> Path:
    return Path(data_dir) / EXPORTS / SESSION


def diagnostic_dir(data_dir: Path) -> Path:
    return Path(data_dir) / EXPORTS / DIAGNOSTIC


def attempts(data_dir: Path) -> list[Attempt]:
    """Every attempt of the session, in the order recorded."""
    data = tomllib.loads(
        (session_dir(data_dir) / SESSION_FILE).read_text(encoding="utf-8")
    )
    return [
        Attempt(
            s["measurement"],
            int(s["attempt"]),
            s["directory"],
            s["outcome"],
            s["reason"],
        )
        for s in data["sweep"]
    ]


def used(data_dir: Path) -> dict[str, Attempt]:
    """The attempt of each measurement the registered rules read: its last
    valid one."""
    out: dict[str, Attempt] = {}
    for a in attempts(data_dir):
        if a.outcome == "valid":
            out[a.measurement] = a
    return out


def session_record(data_dir: Path) -> dict:
    """``session.toml`` as recorded (the plug-in, the pin, the room)."""
    return tomllib.loads(
        (session_dir(data_dir) / SESSION_FILE).read_text(encoding="utf-8")
    )


def readings(data_dir: Path) -> list[Reading]:
    data = tomllib.loads(
        (session_dir(data_dir) / READINGS_FILE).read_text(encoding="utf-8")
    )
    return [
        Reading(
            r["quantity"],
            int(r["reading"]),
            float(r["range_ohm"]),
            float(r["resolution_ohm"]),
            float(r["value_ohm"]),
            r["time"],
        )
        for r in data["reading"]
    ]


def read_run(folder: Path) -> dict:
    return json.loads((Path(folder) / RUN).read_text(encoding="utf-8"))


def points(folder: Path) -> Points:
    """The sweep's recorded points, ordered by frequency (the physics lab
    measures the coarse points first, then refines near the crossing)."""
    with (Path(folder) / POINTS).open(encoding="utf-8") as handle:
        rows = sorted(csv.DictReader(handle), key=lambda r: float(r["frequency_hz"]))
    return Points(
        tuple(float(r["frequency_hz"]) for r in rows),
        tuple(float(r["gain"]) for r in rows),
        tuple(float(r["phase_deg"]) for r in rows),
    )


def sweep_dirs(data_dir: Path) -> dict[str, Path]:
    """Every sweep's folder by its name (the session's attempts and the
    diagnostic sweep)."""
    out = {a.directory: session_dir(data_dir) / a.directory for a in attempts(data_dir)}
    out[DIAGNOSTIC] = diagnostic_dir(data_dir)
    return out


def make_figure(data_dir: Path) -> plt.Figure:
    folders = sweep_dirs(data_dir)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    (ax_c, ax_rl), (ax_phi, ax_g) = axes
    styles = [
        {"color": COLOURS[k], "marker": m, "ms": 4, "ls": ls, "lw": 0.8}
        for k, (m, ls) in enumerate((("o", "-"), ("s", "--"), ("^", ":"), ("D", "-.")))
    ]
    capacitor = (
        ("M0", "M0, attempt 1 (4 min after the plug-in; recorded as failed)"),
        ("M0-repeat", "M0, attempt 2 (the repeat after the wait)"),
        ("M1", "M1"),
        (DIAGNOSTIC, "diagnostic sweep of 2026-11-26 (before the freeze)"),
    )
    low, high = CROSSING_WINDOW_KHZ
    window = []
    for style, (name, label) in zip(styles, capacitor, strict=True):
        p = points(folders[name])
        (line,) = ax_c.plot(
            [f * 1e-3 for f in p.frequency_hz], p.phase_deg, label=label, **style
        )
        role(line, "processed")
        window += [
            phase
            for f, phase in zip(p.frequency_hz, p.phase_deg, strict=True)
            if low <= f * 1e-3 <= high
        ]
    for style, (name, label) in zip(
        styles,
        (("M2", "M2"), ("M5", "M5 (after M4, the AD3 plugged in again)")),
        strict=False,
    ):
        p = points(folders[name])
        (line,) = ax_rl.plot(
            [f * 1e-3 for f in p.frequency_hz], p.phase_deg, label=label, **style
        )
        role(line, "processed")
    m3 = points(folders["M3"])
    khz = [f * 1e-3 for f in m3.frequency_hz]
    (line,) = ax_phi.plot(khz, m3.phase_deg, label="M3, both probes at W1", **styles[0])
    role(line, "processed")
    (line,) = ax_g.plot(
        khz, [g - 1.0 for g in m3.gain], label="M3, both probes at W1", **styles[0]
    )
    role(line, "processed")
    for ax, threshold, unit in (
        (ax_phi, DPHI_THRESHOLD_DEG, "degrees"),
        (ax_g, DG_THRESHOLD, ""),
    ):
        for sign in (1.0, -1.0):
            ref = ax.axhline(
                sign * threshold,
                color="0.4",
                lw=0.9,
                ls=":",
                label=(
                    f"registered threshold +-{threshold:g}{' ' + unit if unit else ''}"
                    if sign > 0
                    else None
                ),
            )
            role(ref, REFERENCE_ROLE)
    for ax in axes.flat:
        ax.set_xscale("log")
        ax.set_xlabel("frequency [kHz]")
        ax.legend(fontsize=7)
    ax_c.set_xlim(CROSSING_WINDOW_KHZ)
    ax_c.set_ylim(min(window) - 5.0, max(window) + 5.0)
    ax_c.xaxis.set_major_formatter(ScalarFormatter())
    ax_c.xaxis.set_minor_formatter(ScalarFormatter())
    ax_c.set_ylabel("phase of channel 2 over channel 1 [degrees]")
    ax_c.set_title(
        "Capacitor node near the -90 degree crossing: M0 (both attempts), M1,"
        " the diagnostic",
        fontsize=9,
    )
    ax_rl.set_ylabel("phase of channel 2 over channel 1 [degrees]")
    ax_rl.set_title("R-L node: M2 and its repeat M5", fontsize=10)
    ax_phi.set_ylabel("phase of channel 2 over channel 1 [degrees]")
    ax_phi.set_title("Same node (M3): the channels' relative phase", fontsize=10)
    ax_g.set_ylabel("gain of channel 2 over channel 1, minus 1 [dimensionless]")
    ax_g.set_title("Same node (M3): the channels' relative gain", fontsize=10)
    return fig
