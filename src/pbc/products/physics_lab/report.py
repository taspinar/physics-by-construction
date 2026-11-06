"""The report of a run and its figure, the frequency response.

The figure shows the points the evaluator recomputed from the raw samples,
as markers, and the closed form of the model as a dashed line drawn apart,
in two panels on one logarithmic frequency axis: the gain and the phase. The
two are told apart by marker and line style as well as colour. No
uncertainty band is drawn: the noise of the channels is stated, but no
per-point uncertainty is estimated, and the report says so.

The figure and the report are written from the same numbers with fixed
precision, so that the same seed gives the same bytes.
"""

from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.products.physics_lab.protocol import (
    F0_TOLERANCE,
    Q_TOLERANCE,
    Point,
    model_gain,
    model_phase,
    reference,
)

ALT = (
    "Two panels on a shared logarithmic frequency axis. Top: the gain of the"
    " capacitor voltage over the source voltage, on a logarithmic axis, rising"
    " to a peak near the resonance and falling beyond it; the measured points"
    " as round markers lie on the dashed line of the closed form. Bottom: the"
    " phase in degrees, falling from near zero through minus ninety at the"
    " resonance towards minus one hundred and eighty, markers on the dashed"
    " closed form. A dotted vertical line marks the estimated resonance."
)


def draw_figure(path: Path, points: list[Point], circuit: SeriesRLC, f0: float | None):
    """Write the frequency-response figure as SVG to ``path``."""
    matplotlib.rcParams["svg.hashsalt"] = "physics-lab"
    blue, _, grey = FIGURE_COLOURS[0], FIGURE_COLOURS[1], FIGURE_COLOURS[2]
    figure = Figure(figsize=(7.0, 5.6), layout="constrained")
    gain_axes, phase_axes = figure.subplots(2, 1, sharex=True)
    measured = sorted(points, key=lambda p: p.frequency_hz)
    f = np.array([p.frequency_hz for p in measured])
    low, high = (f.min() / 1.2, f.max() * 1.2) if len(f) else (1e3, 2.5e4)
    grid = np.geomspace(low, high, 400)
    gain_axes.plot(
        grid,
        model_gain(circuit, grid),
        linestyle="--",
        color=grey,
        label="closed form of the model",
    )
    phase_axes.plot(grid, model_phase(circuit, grid), linestyle="--", color=grey)
    if len(f):
        gain_axes.plot(
            f,
            [p.gain for p in measured],
            linestyle="none",
            marker="o",
            color=blue,
            label="measured, from the raw samples",
        )
        phase_axes.plot(
            f, [p.phase_deg for p in measured], linestyle="none", marker="o", color=blue
        )
    if f0 is not None:
        gain_axes.axvline(
            f0, linestyle=":", color=blue, linewidth=1.0, label="estimated f0"
        )
        phase_axes.axvline(f0, linestyle=":", color=blue, linewidth=1.0)
    gain_axes.set_xscale("log")
    gain_axes.set_yscale("log")
    gain_axes.set_ylabel("gain |V_C / V_S| (dimensionless)")
    phase_axes.set_ylabel("phase of V_C / V_S (degrees)")
    phase_axes.set_xlabel("frequency (Hz)")
    phase_axes.set_yticks([0, -45, -90, -135, -180])
    # Below both panels, so that it covers no data.
    handles, labels = gain_axes.get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncols=3, frameon=False)
    figure.savefig(path, format="svg", metadata={"Date": None})


def _percent(x: float) -> str:
    return f"{x * 100:+.2f} %"


def write_report(result, points: list[Point], circuit: SeriesRLC) -> None:
    """Write ``report.md`` and the figure of ``result``."""
    files = result.files
    analysis, check, run = result.analysis, result.check, result.run
    draw_figure(files["figure"], points, circuit, analysis.f0_hz)
    config = run.configuration
    route = (
        "scripted baseline (no model)"
        if result.route == "baseline"
        else "bounded agent, replayed from its recorded trace"
    )
    ref = reference(circuit)
    lines = [
        "# Frequency response of the prepared series RLC circuit",
        "",
        f"- Execution mode: {run.mode}: {run.label}.",
        f"- Device or model: {run.device['device']}.",
        f"- Route: {route}.",
        f"- Protocol: {config['protocol']}, seed {config['seed']},"
        f" {len(points)} points at {config['amplitude_v']:g} V.",
        f"- Status: {result.status}.",
    ]
    lines += [f"- Diagnostic: {d}" for d in result.diagnostics]
    lines += [
        "",
        "## Result",
        "",
        "Computed by the evaluator from the raw samples (`raw.csv`), compared"
        " with the closed form of the model, which the route never sees.",
        "",
    ]
    if check is not None and analysis.f0_hz is not None and analysis.q is not None:
        lines += [
            "| Quantity | Measured | Closed form | Relative difference |",
            "|---|---|---|---|",
            f"| f0 (Hz) | {analysis.f0_hz:.0f} | {ref['f0_hz']:.0f} |"
            f" {_percent(check.metrics['f0_relative_error'])} |",
            f"| Q | {analysis.q:.3f} | {ref['q']:.3f} |"
            f" {_percent(check.metrics['q_relative_error'])} |",
            "",
            f"Verdict: {'within' if check.correct else 'outside'} the tolerance"
            f" (f0 within {F0_TOLERANCE:.0%}, Q within {Q_TOLERANCE:.0%}).",
        ]
    else:
        lines.append("No estimate: " + (analysis.note if points else "no points."))
    if result.candidate_answer is not None:
        lines += [
            "",
            "The agent's own answer, unverified (the evaluator's numbers above"
            " are the result):",
            "",
            f"> {result.candidate_answer or '(no answer)'}",
        ]
    lines += [
        "",
        "## Figure",
        "",
        f"![{ALT}](frequency-response.svg)",
        "",
        "Measured points against the closed form of the model; the dotted"
        " line marks the estimated resonance. The channel noise is stated in"
        " the run record; no per-point uncertainty is estimated, so no band"
        " is drawn.",
        "",
        "## Points",
        "",
        "| Frequency (Hz) | Gain | Phase (degrees) |",
        "|---|---|---|",
    ]
    lines += [
        f"| {p.frequency_hz:.1f} | {p.gain:.4f} | {p.phase_deg:.2f} |"
        for p in sorted(points, key=lambda p: p.frequency_hz)
    ]
    lines += [
        "",
        "## What this run does not show",
        "",
        {
            "simulated": "It is a simulation: it shows that the protocol and"
            " the analysis recover the model's own f0 and Q, not that a"
            " physical circuit behaves so. Hardware is not demonstrated (F140).",
            "recorded": "It replays a recorded sample: it is not a new"
            " experiment, and it shows only what that sample holds"
            " (its declaration is in `run.json`).",
            "live": "A live result varies within the declared tolerances and"
            " stays on this machine.",
        }[run.mode],
        "",
        "## Files",
        "",
        "`raw.csv` (every sample), `points.csv` (the route's points),"
        " `run.json` (the run record), `evidence.json` (the evidence ledger),"
        " `frequency-response.svg` (the figure).",
        "",
    ]
    files["report"].write_text("\n".join(lines), encoding="utf-8")
