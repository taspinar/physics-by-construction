"""The report of a campaign and its figures (F145), drawn from the
evaluator's numbers, which come from the exported raw samples.

The figures follow the project's rules for a scientific figure: every axis
names its quantity and unit; the measurement is drawn with its standard
errors as bars and the models dashed and apart; series are told apart by
marker and line style as well as colour (``pbc.authoring.FIGURE_COLOURS``);
the legend covers no data; each figure has a text alternative without
computed values; and the same raw samples give the same bytes.

- ``frequency-response.svg``: gain and phase of the valid points with
  their errors, and the fitted second-order response;
- ``ringdown.svg``: the response after the step of the first valid
  ring-down, and the fitted curve, with the residuals below;
- ``amplitude-response.svg``: the fundamental gain and the third-harmonic
  ratio against the amplitude, with the held-out prediction of the gain.
"""

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.products.physics_lab import resonance, transient
from pbc.products.physics_lab.campaign import (
    AMPLITUDE_RESPONSE,
    FREQUENCY_RESPONSE,
    TRANSIENT,
)
from pbc.products.physics_lab.estimates import COVERAGE

BLUE, RED, GREY = FIGURE_COLOURS[0], FIGURE_COLOURS[1], FIGURE_COLOURS[2]

ALT_FREQUENCY = (
    "Two panels on a shared logarithmic frequency axis. Top: the gain of the"
    " response over the source, on a logarithmic axis, as round markers with"
    " error bars, and the fitted second-order response as a dashed line."
    " Bottom: the phase in degrees, markers with error bars and the dashed fit,"
    " falling through minus ninety near the resonance."
)
ALT_RINGDOWN = (
    "Two panels on a shared time axis from the step. Top: the response voltage"
    " after the step as small markers, rising past its final level and"
    " oscillating with a decaying amplitude, and the fitted damped oscillation"
    " as a dashed line. Bottom: the residuals of the fit, scattered about zero."
)
ALT_AMPLITUDE = (
    "Two panels on a shared amplitude axis. Top: the gain at the fundamental"
    " as round markers with error bars, near one at small amplitudes and"
    " falling at the largest, and the gain predicted from the characteristic"
    " fitted at the largest amplitude as square markers joined by a dashed"
    " line. Bottom: the ratio of the third harmonic to the fundamental as"
    " markers with error bars, near zero at small amplitudes and growing at the"
    " largest."
)


def _figure(rows: int, height: float) -> tuple[Figure, Any]:
    matplotlib.rcParams["svg.hashsalt"] = "physics-lab-campaign"
    figure = Figure(figsize=(7.0, height), layout="constrained")
    return figure, figure.subplots(rows, 1, sharex=True)


def _save(figure: Figure, axes, path: Path) -> None:
    handles, labels = axes.get_legend_handles_labels()
    if handles:
        figure.legend(
            handles, labels, loc="outside lower center", ncols=3, frameon=False
        )
    figure.savefig(path, format="svg", metadata={"Date": None})


def draw_frequency_response(path: Path, evaluation: dict[str, Any], points) -> None:
    figure, (gain_axes, phase_axes) = _figure(2, 5.6)
    f = np.array([p.frequency_hz for p in points])
    order = np.argsort(f)
    gain_axes.errorbar(
        f[order],
        [points[i].gain for i in order],
        yerr=[points[i].gain_se for i in order],
        linestyle="none",
        marker="o",
        color=BLUE,
        label="measured, from the raw samples (bars: one standard error)",
    )
    phase_axes.errorbar(
        f[order],
        [points[i].phase_deg for i in order],
        yerr=[points[i].phase_se_deg for i in order],
        linestyle="none",
        marker="o",
        color=BLUE,
    )
    fit = evaluation[FREQUENCY_RESPONSE]["fit"]
    if fit is not None and len(f):
        grid = np.geomspace(f.min() / 1.1, f.max() * 1.1, 400)
        h = resonance.model(
            grid, fit["f0_hz"]["value"], fit["q"]["value"], fit["k"]["value"]
        )
        gain_axes.plot(
            grid,
            np.abs(h),
            linestyle="--",
            color=GREY,
            label="fitted second-order response",
        )
        phase_axes.plot(
            grid, np.degrees(np.unwrap(np.angle(h))), linestyle="--", color=GREY
        )
    gain_axes.set_xscale("log")
    gain_axes.set_yscale("log")
    gain_axes.set_ylabel("gain |V_response / V_source|\n(dimensionless)")
    phase_axes.set_ylabel("phase (degrees)")
    phase_axes.set_xlabel("frequency (Hz)")
    _save(figure, gain_axes, path)


def draw_ringdown(path: Path, ringdown: transient.Ringdown) -> None:
    figure, (axes, residual_axes) = _figure(2, 5.0)
    start, end = ringdown.window or (0, 0)
    t = np.asarray(ringdown.capture.t[start:end], dtype=float)
    v = np.asarray(ringdown.capture.channels["response"][start:end], dtype=float)
    t0 = t - t[0]
    fit = ringdown.fit
    assert fit is not None
    curve = fit.curve(t0)
    axes.plot(
        t0 * 1e3,
        v,
        linestyle="none",
        marker=".",
        markersize=2,
        color=BLUE,
        label="measured response after the step",
    )
    axes.plot(
        t0 * 1e3, curve, linestyle="--", color=GREY, label="fitted damped oscillation"
    )
    residual_axes.plot(
        t0 * 1e3, v - curve, linestyle="none", marker=".", markersize=2, color=BLUE
    )
    residual_axes.axhline(0.0, color=GREY, linewidth=0.8)
    axes.set_ylabel("response (V)")
    residual_axes.set_ylabel("residual (V)")
    residual_axes.set_xlabel("time from the start of the fit (ms)")
    _save(figure, axes, path)


def draw_amplitude_response(path: Path, evaluation: dict[str, Any]) -> None:
    figure, (gain_axes, h3_axes) = _figure(2, 5.0)
    points = sorted(
        evaluation[AMPLITUDE_RESPONSE]["points"], key=lambda p: p["amplitude_v"]
    )
    a = [p["amplitude_v"] for p in points]
    gain_axes.errorbar(
        a,
        [p["gain"] for p in points],
        yerr=[p["gain_se"] for p in points],
        linestyle="none",
        marker="o",
        color=BLUE,
        label="measured (bars: one standard error)",
    )
    held = evaluation[AMPLITUDE_RESPONSE]["held_out"]
    if held is not None:
        predicted = sorted(
            (g["amplitude_v"], g["b"]["value"]) for g in held["agreements"]
        )
        gain_axes.plot(
            [x for x, _ in predicted],
            [y for _, y in predicted],
            linestyle="--",
            marker="s",
            color=RED,
            fillstyle="none",
            label="predicted from the largest amplitude",
        )
    h3_axes.errorbar(
        a,
        [p["h3"] for p in points],
        yerr=[p["h3_se"] for p in points],
        linestyle="none",
        marker="o",
        color=BLUE,
    )
    gain_axes.set_ylabel("fundamental gain (dimensionless)")
    h3_axes.set_ylabel("third harmonic / fundamental\n(dimensionless)")
    h3_axes.set_xlabel("source amplitude (V)")
    _save(figure, gain_axes, path)


def _estimate(e: dict[str, float] | None, digits: int = 1) -> str:
    if e is None:
        return "none"
    k = COVERAGE
    return f"{e['value']:.{digits}f} ± {k * e['se']:.{digits}f}"


def write_report(result, data: dict[str, Any]) -> dict[str, Path]:
    """Write ``report.md`` and the figures; return the figures' paths."""
    out, evaluation, plan = result.out_dir, result.evaluation, result.plan
    run = data["run"]
    files: dict[str, Path] = {}
    lines = [
        "# A campaign of the Autonomous Physics Lab",
        "",
        f"- Execution mode: {run['mode']}: {run['label']}.",
        f"- Device or model: {run['device'].get('device')}.",
        "- Circuit (declared by the plan, never changed by the product):"
        f" {plan.circuit}.",
        f"- Route: {result.route}; protocols: {', '.join(plan.protocols)}.",
        f"- Segment {result.segment.number}: {result.segment.status}, "
        f"{len(result.records)} measurements of a budget of {plan.budget}.",
        f"- Status: {data['status']}; the evaluator's verdict: {data['verdict']}.",
    ]
    lines += [f"- Diagnostic: {d}" for d in result.segment.diagnostics]
    lines += [
        "",
        f"Every number below is the evaluator's, recomputed from `raw.csv`;"
        f" an interval is the value ± {COVERAGE:g} standard errors.",
    ]
    raw = None
    if FREQUENCY_RESPONSE in plan.protocols:
        fr = evaluation.get(FREQUENCY_RESPONSE, {})
        fit = fr.get("fit")
        lines += [
            "",
            "## Frequency response",
            "",
            f"Valid points: {fr.get('valid_points', 0)}.",
        ]
        if fit is not None:
            lines += [
                "",
                "| Quantity | Interval |",
                "|---|---|",
                f"| f0 (Hz) | {_estimate(fit['f0_hz'])} |",
                f"| Q | {_estimate(fit['q'], 4)} |",
                f"| reduced chi-square | {fit['reduced_chi2']:.2f} |",
            ]
            from pbc.products.physics_lab.lab import read_raw

            raw = read_raw(result.files["raw"])
            points = [
                m.point
                for a in raw
                if a["protocol"] == FREQUENCY_RESPONSE
                for m in [
                    resonance.analyse_point(
                        a["capture"], a["frequency_hz"], a["amplitude_v"]
                    )
                ]
                if m.point is not None
            ]
            files["frequency-figure"] = out / "frequency-response.svg"
            draw_frequency_response(files["frequency-figure"], evaluation, points)
            lines += ["", f"![{ALT_FREQUENCY}](frequency-response.svg)"]
    if TRANSIENT in plan.protocols:
        tr = evaluation.get(TRANSIENT, {})
        lines += [
            "",
            "## Transient response (ring-down after a step)",
            "",
            f"Valid ring-downs: {tr.get('valid', 0)}; invalid: {tr.get('invalid', 0)}.",
            "",
            "| Quantity | Interval | Birge ratio of the repetitions |",
            "|---|---|---|",
        ]
        for name, key, digits in (("f0 (Hz)", "f0_hz", 1), ("Q", "q", 4)):
            e = tr.get(key)
            birge = "" if e is None else f"{e['birge']:.2f}"
            lines.append(f"| {name} | {_estimate(e, digits)} | {birge} |")
        if raw is None:
            from pbc.products.physics_lab.lab import read_raw

            raw = read_raw(result.files["raw"])
        first = next(
            (
                r
                for a in raw
                if a["protocol"] == TRANSIENT
                for r in [
                    transient.analyse_ringdown(a["capture"], plan.transient_settings)
                ]
                if r.fit is not None
            ),
            None,
        )
        if first is not None:
            files["ringdown-figure"] = out / "ringdown.svg"
            draw_ringdown(files["ringdown-figure"], first)
            lines += ["", f"![{ALT_RINGDOWN}](ringdown.svg)"]
    if evaluation.get("agreements"):
        lines += [
            "",
            "## Consistency of the two protocols",
            "",
            "| Quantity | Frequency response | Ring-down | Difference in combined"
            " standard errors | Agree |",
            "|---|---|---|---|---|",
        ]
        for a in evaluation["agreements"]:
            lines.append(
                f"| {a['quantity']} | {_estimate(a['a'], 4)} | {_estimate(a['b'], 4)}"
                f" | {a['sigmas']:.2f} | {'yes' if a['agree'] else 'no'} |"
            )
    if AMPLITUDE_RESPONSE in plan.protocols:
        am = evaluation.get(AMPLITUDE_RESPONSE, {})
        lines += [
            "",
            "## Amplitude-dependent response of the LED pair",
            "",
            f"Valid amplitudes: {am.get('valid', 0)}; invalid: {am.get('invalid', 0)}.",
        ]
        characteristic = am.get("characteristic")
        if characteristic is not None:
            lines += [
                "",
                f"Characteristic: n = {_estimate(characteristic['n'], 3)}, the"
                f" voltage at 1 mA {_estimate(characteristic['v_ref'], 4)} V.",
            ]
        held = am.get("held_out")
        if held is not None:
            lines += [
                "",
                f"Held-out check (fitted at {held['fitted_on_v']:g} V):"
                f" {'agrees' if held['agree'] else 'does not agree'} at every"
                " other amplitude."
                if held["agree"]
                else f"Held-out check (fitted at {held['fitted_on_v']:g} V): does not"
                " agree at every other amplitude.",
            ]
        if am.get("points"):
            files["amplitude-figure"] = out / "amplitude-response.svg"
            draw_amplitude_response(files["amplitude-figure"], evaluation)
            lines += ["", f"![{ALT_AMPLITUDE}](amplitude-response.svg)"]
    checks = evaluation.get("simulator_checks", {})
    if checks:
        lines += ["", "## The simulator's checks against the closed form", ""]
        for protocol, check in checks.items():
            lines.append(f"- {protocol}: {'passed' if check['correct'] else 'failed'}.")
    if data["invalid"]:
        lines += ["", "## Invalid measurements (recorded, never fitted)", ""]
        lines += [
            f"- {i['record']} ({i['protocol']}): {i['reason']}" for i in data["invalid"]
        ]
    if result.answer is not None:
        lines += [
            "",
            "The agent's own answer, unverified:",
            "",
            f"> {result.answer or '(no answer)'}",
        ]
    lines += _comparison_lines(data.get("comparison"))
    lines += [
        "",
        "## What this campaign does not show",
        "",
        {
            "simulated": "It is a simulation: it shows that the protocols and"
            " their analysis recover the model's own values, not that a physical"
            " circuit behaves so.",
            "recorded": "It replays a recorded sample: it is not a new"
            " experiment, and it shows only what that sample holds.",
            "live": "It is one campaign on this circuit and this device. The"
            " nominal closed form of the declared parts is not its reference;"
            " the agreement of the protocols is. The result stays on this"
            " machine. An educational and experimental tool, not a certified"
            " laboratory instrument.",
        }[run["mode"]],
        "",
    ]
    result.files["report"].write_text("\n".join(lines), encoding="utf-8")
    return files


def _comparison_lines(comparison: dict[str, Any] | None) -> list[str]:
    """The agent beside the classical routes (``lab.baseline_comparison``)."""
    if comparison is None:
        return []
    lines = [
        "",
        "## The agent beside the classical routes",
        "",
    ]
    if comparison.get("note"):
        lines.append(f"{comparison['note'][0].upper()}{comparison['note'][1:]}.")
    if comparison["target"] is None:
        lines += [""] if comparison.get("note") else []
        lines += ["| Route | Measurements |", "|---|---|"]
        lines += [f"| {r} | {n} |" for r, n in comparison["measurements"].items()]
        return lines
    lines += [
        f"The adaptive policy and the scripted sweep ran on fresh simulated"
        f" benches with the same plan and seed ({comparison['seed']}). The"
        f" common target is a relative width of the interval of f0 of"
        f" {comparison['target']:.3g}, the widest final width among the routes;"
        " each route is counted by the frequency-response measurements it"
        " needed to reach it.",
        "",
        "| Route | Measurements (all protocols) | Frequency-response measurements"
        " | Final relative width of f0 | Needed for the target |",
        "|---|---|---|---|---|",
    ]
    for route, r in comparison["routes"].items():
        final = "" if r["final_width"] is None else f"{r['final_width']:.3g}"
        needed = "not reached" if r["needed"] is None else str(r["needed"])
        lines.append(
            f"| {route} | {comparison['measurements'][route]} | {r['measurements']}"
            f" | {final} | {needed} |"
        )
    return lines
