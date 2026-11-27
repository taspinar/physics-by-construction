"""The owner's bench sessions of 2026-11-25 and 2026-11-26 (F145 part 3,
Issue #614): 27 live campaigns on the series RLC circuit of the F140 pilot
and 2 on a red LED pair, measured with an Analog Discovery 3.

Status of the figure: *processed*. The committed part of the dataset is, of
every campaign, the run record (``run.json``), the measurement table
(``measurements.csv``), and the evidence log (``evidence.json``) the product
exported, with the device's serial number replaced by ``AD3-001``
(``MANIFEST.tsv``); and the raw samples of the first RLC campaign of
2026-11-26 (its frequency-response records only) and of both LED runs. The
complete exports are in the archive the card names.

Two kinds of numbers are read here, and kept apart:

- the exports' own results, as recorded: f0 and Q of each protocol with
  their standard errors, the agreement of the two protocols, the verdict,
  the LED characteristic and its held-out check (``Campaign``);
- a re-analysis of this module, labelled as such: the frequency at which
  the phase of the frequency response crosses -90 degrees, interpolated
  linearly in log frequency between the two valid points around it
  (``phase_crossing_hz``), and the minutes after the plug-in of the device
  where the owner noted it (``minutes_after_plug_in``).

Nothing here explains a difference between campaigns or with the pilot.
"""

import csv
import itertools
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pbc.data.figure_provenance import REFERENCE as REFERENCE_ROLE
from pbc.data.figure_provenance import FigureProvenance, role
from pbc.data.plotting import COLOURS

DATASET = "ad3-bench-2026-11"
EXPORTS = "exports"
RUN, MEASUREMENTS, EVIDENCE, RAW = (
    "run.json",
    "measurements.csv",
    "evidence.json",
    "raw.csv",
)
DEVICE_ID = "AD3-001"
# The first RLC campaign of 2026-11-26 (the replay's sample, chosen by a rule
# that does not depend on a result) and the two LED runs.
RLC_SAMPLE = "2026-11-26-series-rlc"
LED_RUNS = ("2026-11-26-led-pair", "2026-11-26-led-pair-run2")
# The owner's note of the plug-in of the device before the RLC campaigns of
# 2026-11-26 (about 13:10 local, Issue #614), in UTC. The session of
# 2026-11-25 has none; the LED session's note (about 17:08 local) falls after
# the first LED run's recorded start (16:07:48 UTC), so the two clocks are
# not reconciled and no minutes are computed for it.
PLUGGED_IN = {"2026-11-26-series-rlc": datetime(2026, 11, 26, 12, 10, tzinfo=UTC)}
REFERENCE = FigureProvenance(
    status="processed",
    dataset=DATASET,
    processing="The exports' own results (run.json of every campaign: f0 and Q"
    " of both protocols with their standard errors; the LED pair's gain and"
    " third harmonic per amplitude), as recorded; the -90 degree crossing of"
    " the phase, interpolated from measurements.csv, is this module's"
    " re-analysis (pbc.data.reference.ad3_bench_2026_11), not part of the"
    " record.",
)


@dataclass(frozen=True)
class Estimate:
    value: float
    se: float


@dataclass(frozen=True)
class Campaign:
    """One campaign as its export recorded it."""

    name: str
    circuit: str
    started: datetime
    status: str
    verdict: bool | None
    acquisitions: int
    invalid: int
    f0_response: Estimate | None = None  # Hz, the frequency-response fit
    q_response: Estimate | None = None
    reduced_chi2: float | None = None
    f0_ringdown: Estimate | None = None  # Hz, the ring-downs combined
    q_ringdown: Estimate | None = None
    f0_sigmas: float | None = None  # the protocols' difference / combined s.e.
    q_sigmas: float | None = None
    f0_agree: bool | None = None
    q_agree: bool | None = None
    ideality: Estimate | None = None  # the LED characteristic's n
    v_ref: Estimate | None = None  # V at the reference current
    held_out_agree: bool | None = None


def export_dirs(data_dir: Path) -> list[Path]:
    """The export folders of the committed part, in the order measured."""
    folders = [p for p in (data_dir / EXPORTS).iterdir() if p.is_dir()]
    return sorted(folders, key=lambda p: read_run(p)["run"]["started"])


def read_run(folder: Path) -> dict:
    return json.loads((folder / RUN).read_text(encoding="utf-8"))


def _estimate(entry: dict | None) -> Estimate | None:
    if not entry:
        return None
    return Estimate(float(entry["value"]), float(entry["se"]))


def campaign(folder: Path) -> Campaign:
    """The recorded results of the campaign in ``folder``."""
    record = read_run(folder)
    evaluation = record["evaluation"]
    started = datetime.strptime(record["run"]["started"], "%Y-%m-%dT%H:%M:%SZ")
    fields: dict = {
        "name": folder.name,
        "circuit": record["plan"]["circuit"],
        "started": started.replace(tzinfo=UTC),
        "status": record["status"],
        "verdict": record["verdict"],
        "acquisitions": int(evaluation["acquisitions"]),
        "invalid": len(record.get("invalid") or []),
    }
    fit = (evaluation.get("frequency-response") or {}).get("fit")
    if fit:
        fields |= {
            "f0_response": _estimate(fit["f0_hz"]),
            "q_response": _estimate(fit["q"]),
            "reduced_chi2": float(fit["reduced_chi2"]),
        }
    transient = evaluation.get("transient")
    if transient:
        fields |= {
            "f0_ringdown": _estimate(transient["f0_hz"]),
            "q_ringdown": _estimate(transient["q"]),
        }
    for agreement in evaluation.get("agreements") or []:
        key = "f0" if agreement["quantity"] == "f0_hz" else "q"
        fields[f"{key}_sigmas"] = float(agreement["sigmas"])
        fields[f"{key}_agree"] = bool(agreement["agree"])
    amplitude = evaluation.get("amplitude-response")
    if amplitude:
        characteristic = amplitude["characteristic"]
        fields |= {
            "ideality": _estimate(characteristic["n"]),
            "v_ref": _estimate(characteristic["v_ref"]),
            "held_out_agree": bool(amplitude["held_out"]["agree"]),
        }
    return Campaign(**fields)


def campaigns(data_dir: Path) -> list[Campaign]:
    return [campaign(folder) for folder in export_dirs(data_dir)]


def read_measurements(folder: Path) -> list[dict[str, str]]:
    with (folder / MEASUREMENTS).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def phase_crossing_hz(folder: Path) -> float:
    """Re-analysis: the frequency (Hz) at which the phase of the valid
    frequency-response points crosses -90 degrees, linear in log frequency
    between the two points around the crossing."""
    rows = [
        r
        for r in read_measurements(folder)
        if r["protocol"] == "frequency-response" and r["valid"] == "1"
    ]
    points = [(float(r["frequency_hz"]), float(r["phase_deg"])) for r in rows]
    crossing = crossing_hz(points)
    if crossing is None:
        raise ValueError(f"{folder.name}: the phase does not cross -90 degrees")
    return crossing


def crossing_hz(points) -> float | None:
    """The frequency (Hz) at which (frequency, phase in degrees) points,
    sorted by frequency here, first cross -90 degrees, linear in log
    frequency between the two points around the crossing; ``None`` when the
    phase does not cross."""
    for (f1, p1), (f2, p2) in itertools.pairwise(sorted(points)):
        if p1 > -90.0 >= p2:
            share = (p1 + 90.0) / (p1 - p2)
            return float(math.exp(math.log(f1) + share * (math.log(f2) - math.log(f1))))
    return None


def minutes_after_plug_in(c: Campaign) -> float | None:
    """Minutes from the owner's noted plug-in to the campaign's start, where
    the owner noted one that the run records' clock reconciles; ``None``
    otherwise."""
    plugged = PLUGGED_IN.get(f"{c.started.date().isoformat()}-{c.circuit}")
    if plugged is None:
        return None
    return (c.started - plugged).total_seconds() / 60.0


def amplitude_points(folder: Path) -> list[dict]:
    """The LED pair's recorded points (amplitude V, gain and third harmonic
    with standard errors), ordered by the amplitude."""
    points = read_run(folder)["evaluation"]["amplitude-response"]["points"]
    return sorted(points, key=lambda p: p["amplitude_v"])


def make_figure(data_dir: Path) -> plt.Figure:
    found = campaigns(data_dir)
    rlc = [c for c in found if c.circuit == "series-rlc"]
    folders = {f.name: f for f in export_dirs(data_dir)}
    number = np.arange(1, len(rlc) + 1)
    first_day = sum(c.started.date() == rlc[0].started.date() for c in rlc)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    (ax_f0, ax_q), (ax_gain, ax_h3) = axes
    styles = (
        {"color": COLOURS[0], "marker": "o", "ms": 4, "ls": "none", "capsize": 2},
        {"color": COLOURS[1], "marker": "s", "ms": 4, "ls": "none", "capsize": 2},
    )
    for ax, attr, scale in (
        (ax_f0, ("f0_response", "f0_ringdown"), 1e-3),
        (ax_q, ("q_response", "q_ringdown"), 1.0),
    ):
        for style, name, label in zip(
            styles,
            attr,
            ("frequency response, 1 s.e.", "ring-downs, 1 s.e."),
            strict=True,
        ):
            values = [getattr(c, name) for c in rlc]
            bars = ax.errorbar(
                number + (0.15 if "ringdown" in name else -0.15),
                [v.value * scale for v in values],
                yerr=[v.se * scale for v in values],
                label=label,
                **style,
            )
            role(bars, "processed")
        line = ax.axvline(first_day + 0.5, color="0.5", lw=0.8, ls=":")
        role(line, REFERENCE_ROLE)
        ax.set_xlabel("campaign, in the order measured [number]")
    crossings = [phase_crossing_hz(folders[c.name]) * 1e-3 for c in rlc]
    (line,) = ax_f0.plot(
        number,
        crossings,
        color=COLOURS[2],
        marker="^",
        ms=4,
        ls="none",
        label="-90 degree crossing (re-analysis)",
    )
    role(line, "processed")
    ax_f0.set_ylabel("f0 [kHz]")
    ax_f0.set_title(
        f"Series RLC: f0 by both protocols ({first_day} campaigns on 2026-11-25,"
        f" {len(rlc) - first_day} on 2026-11-26)",
        fontsize=10,
    )
    ax_f0.legend(fontsize=8)
    ax_q.set_ylabel("Q [dimensionless]")
    ax_q.set_title("Series RLC: Q by both protocols", fontsize=10)
    ax_q.legend(fontsize=8)
    markers = ("o", "s")
    for k, name in enumerate(LED_RUNS):
        points = amplitude_points(folders[name])
        a = [p["amplitude_v"] for p in points]
        for ax, key in ((ax_gain, "gain"), (ax_h3, "h3")):
            bars = ax.errorbar(
                a,
                [p[key] for p in points],
                yerr=[p[f"{key}_se"] for p in points],
                label=f"LED run {k + 1}, 1 s.e.",
                color=COLOURS[k],
                marker=markers[k],
                ms=4,
                ls="none",
                capsize=2,
            )
            role(bars, "processed")
    ax_gain.set_xlabel("amplitude of the generator [V]")
    ax_gain.set_ylabel("gain at the fundamental [V/V]")
    ax_gain.set_title("LED pair: gain at the fundamental, 1 kHz", fontsize=10)
    ax_gain.legend(fontsize=8)
    ax_h3.set_xlabel("amplitude of the generator [V]")
    ax_h3.set_ylabel("third harmonic over the fundamental [V/V]")
    ax_h3.set_title("LED pair: third harmonic", fontsize=10)
    ax_h3.legend(fontsize=8)
    return fig
