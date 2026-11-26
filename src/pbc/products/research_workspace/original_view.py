"""The static view of an original-track project (F155 part 2): one HTML file
written from the project state, in the style of the reproduction's view.

No server, no socket, no JavaScript. Every status is a word; the figure has
alt text and the table of its values beside it.
"""

import base64
import io
from pathlib import Path

from pbc.products.research_workspace import coil, followup
from pbc.products.research_workspace import log as worklog
from pbc.products.research_workspace import original as orig
from pbc.products.research_workspace import report as rep
from pbc.products.research_workspace.view import _STYLE, _e, _status, _table


def loss_figure(pilot: dict) -> str:
    """The real part of Z against the frequency from the pilot's R-L node
    sweep (processed), with its one-sigma bars and the three frequencies of
    R_L0 marked; no R_dc line, since no reading exists before M4."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from pbc.data.plotting import COLOURS, add_credit, label_status

    f = [x / 1e3 for x in pilot["frequency_hz"]]
    fig, ax = plt.subplots(figsize=(8, 4.2), constrained_layout=True)
    loss_f = [f[i] for i in coil.LOSS_POINTS]
    ax.axvspan(
        min(loss_f), max(loss_f), color="0.9", label="the three frequencies of R_L0"
    )
    ax.errorbar(
        f,
        pilot["R_L"],
        yerr=pilot["R_L_sigma"],
        fmt="o-",
        ms=4,
        lw=1.2,
        color=COLOURS[0],
        capsize=2,
        label="R_L = Re Z, pilot run 3, nominal 100 ohm, uncorrected (one sigma)",
    )
    ax.set_xscale("log")
    ax.set_xlabel("frequency [kHz]")
    ax.set_ylabel("R_L [ohm]")
    ax.legend(fontsize=7, loc="upper center")
    label_status(fig, "processed")
    add_credit(
        fig, "Data: A. Taspinar, F140 pilot (Analog Discovery 3), 2026-11-22, CC BY 4.0"
    )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, metadata={"Software": None})
    plt.close(fig)
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    alt = (
        "A line with dots and error bars on a logarithmic frequency axis: the"
        " real part of the impedance is high at the lowest frequencies, falls to"
        " its lowest values in a shaded band near the resonance, and rises"
        " steeply towards the highest frequency; the bars are widest at the two"
        " ends of the sweep."
    )
    return (
        f'<figure><img src="data:image/png;base64,{data}" alt="{_e(alt)}"'
        ' width="880" height="462"><figcaption>Processed: the loss read from the'
        " pilot's R-L node sweep rises away from the resonance on both sides; the"
        " pilot alone cannot say whether the rise is the coil's or the channels'"
        " (exploratory: these data chose the thresholds). The coil's DC"
        " resistance is not drawn: it is measured in M4.</figcaption></figure>"
    )


def render(data: dict, *, figure: bool = True) -> str:
    status = data["status"]
    banner = rep.banner_lines(status)
    pilot, trial, bounds, follow = (
        data["pilot"],
        data["controls"],
        data["boundaries"],
        data["followup"],
    )
    freeze = data["freeze"]
    outcome = follow["outcome"]
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Research Workspace: the coil-loss investigation</title>",
        f"<style>{_STYLE}</style></head><body>",
        "<header><div class='inner'>",
        "<h1>Why the ideal RLC model fails on the pilot's circuit</h1>",
        f"<p class='banner'>{_e(banner[0])}</p>",
        *[f"<p>{_e(line)}</p>" for line in banner[1:]],
        f"<p class='scope'>Scope: {_e(orig.SCOPE)}.</p>",
        "</div></header><main>",
    ]
    if data["problems"]:
        parts.append(
            "<section class='problems' aria-labelledby='problems'>"
            "<h2 id='problems'>The project does not verify</h2><ul>"
            + "".join(f"<li>{_e(p)}</li>" for p in data["problems"])
            + "</ul></section>"
        )
    plan = data["registration"]
    parts.append(
        "<section aria-labelledby='question'><h2 id='question'>The question and"
        f" its registration</h2><p>{_e(plan.question)}</p>"
        f"<p>Frozen: digest <code>{_e(freeze.digest[:16])}</code>, merge commit"
        f" <code>{_e(freeze.commit[:12])}</code> on <code>main</code>,"
        f" {_e(freeze.time)}. Evidence measured before that time is refused. The"
        " thresholds were chosen after seeing the pilot's data; only M1 to M5"
        " are confirmatory.</p>"
        + _table(
            "Every question considered, with its decision; rejected and deferred"
            " ones are kept with what would warrant revisiting them.",
            ["Question", "Assessment", "Decision", "Reason", "Revisit when"],
            [
                [
                    e.idea.key,
                    "passes"
                    if not data["assessments"][e.idea.key]["problems"]
                    else "; ".join(data["assessments"][e.idea.key]["problems"]),
                    e.decision,
                    e.reason,
                    e.revisit,
                ]
                for e in data["archive"]
            ],
        )
        + "</section>"
    )
    rows = []
    for name, (rule, predicted) in coil.EXPLANATIONS.items():
        got = outcome[rule.lower()]
        rows.append([name, rule, predicted, got, _status(status[rule])])
    parts.append(
        "<section aria-labelledby='map'><h2 id='map'>The evidence map</h2>"
        "<p>Each explanation with the outcome its rule predicts; no outcome is"
        " predicted by two. <code>exceeds</code> is predicted by neither and opens"
        " a new finding; a case that meets no predicted outcome is"
        " <code>inconclusive</code>, a result.</p>"
        + _table(
            "The explanations, the registered outcomes, and the follow-up's verdicts.",
            ["Explanation", "Rule", "Predicts", "Outcome", "Status"],
            rows,
            raw=(4,),
        )
        + "</section>"
    )
    pilot_rows = [
        [f"{x / 1e3:.1f}", f"{r:.1f}", f"{s:.2f}"]
        for x, r, s in zip(
            pilot["frequency_hz"], pilot["R_L"], pilot["R_L_sigma"], strict=True
        )
    ]
    parts.append(
        "<section aria-labelledby='pilot'><h2 id='pilot'>The existing sweeps"
        " (exploratory)</h2>"
        f"<p>Pilot run 3 with the nominal 100 ohm: L = {pilot['L_H'] * 1e3:.3f} mH,"
        f" C = {pilot['C_F'] * 1e9:.2f} nF, R_L0 = {pilot['R_L0']:.1f} ohm"
        f" (u_L {pilot['u_L']:.1f} ohm), Rise = {pilot['Rise']:.0f} ohm without a"
        f" correction, P0 = {pilot['P0_deg']:.2f} degrees. These data chose the"
        " thresholds; they confirm nothing.</p>"
        + (loss_figure(pilot) if figure else "")
        + _table(
            "R_L against the frequency, pilot run 3 (the figure's values).",
            ["f [kHz]", "R_L [ohm]", "one sigma [ohm]"],
            pilot_rows,
        )
        + _table(
            "The sensitivity to an assumed constant channel mismatch, divided out"
            " of both sweeps.",
            ["dphi [deg]", "dg", "R_L0 [ohm]", "Rise [ohm]", "P [deg]"],
            [
                [
                    f"{r['dphi_deg']:g}",
                    f"{r['dg']:g}",
                    f"{r['R_L0']:.1f}",
                    f"{r['Rise']:.0f}",
                    f"{r['P_deg']:.2f}",
                ]
                for r in pilot["sensitivity"]
            ],
        )
        + "</section>"
    )
    control_rows = [
        [
            name,
            str(r["seed"]),
            r["g1"],
            r["g2"],
            str(r["precondition"]),
            r["g1_pilot"],
            "; ".join(r["misses"]) or "nothing",
        ]
        for name, rows_ in trial["results"].items()
        for r in rows_
    ]
    parts.append(
        "<section aria-labelledby='controls'><h2 id='controls'>The positive"
        " controls (simulated)</h2>"
        f"<p>Status: {_status(status['controls'])}. With ideal channels the largest"
        f" |dphi| was {trial['resolution']['max_abs_dphi_deg']:.3f} degrees and the"
        f" largest |dg| {trial['resolution']['max_abs_dg']:.4f}, against the"
        f" thresholds {coil.MISMATCH_PHASE_DEG} degrees and {coil.MISMATCH_GAIN}.</p>"
        + _table(
            "Every simulated session: the outcomes of the rules and what missed.",
            [
                "Control",
                "Seed",
                "G1",
                "G2",
                "Precondition",
                "G1 for the pilot",
                "Missed",
            ],
            control_rows,
        )
        + f"<p>Boundary cases: {_status(status['boundaries'])}.</p>"
        + _table(
            "Values below, at, and above every threshold, with the outcome the"
            " registration's text gives.",
            ["Rule", "Inputs", "Expected", "Got"],
            [
                [
                    c["rule"],
                    ", ".join(f"{v:g}" for v in c["inputs"]),
                    c["expected"],
                    c["got"],
                ]
                for c in bounds["cases"]
            ],
        )
        + "</section>"
    )
    if follow["status"] == followup.NOT_EVALUATED:
        follow_text = (
            "<p>Not evaluated: the bench session (M0 to M5) is the owner's, after"
            " part 2 is merged into <code>main</code>.</p>"
        )
    else:
        items = (
            follow["reasons"]
            + [f"Deviation: {d}" for d in follow["deviations"]]
            + outcome["notes"]
        )
        follow_text = (
            f"<p>Status: {_e(follow['status'])}.</p><ul>"
            + "".join(f"<li>{_e(i)}</li>" for i in items)
            + "</ul>"
            + _table(
                "The follow-up's quantities.",
                ["Quantity", "Value"],
                [[k, f"{v:.6g}"] for k, v in sorted(outcome["values"].items())],
            )
        )
    log = data["log"]
    parts.append(
        "<section aria-labelledby='followup'><h2 id='followup'>The follow-up</h2>"
        + follow_text
        + _table(
            "The findings of the follow-up log and their states.",
            ["Finding", "Kind", "State", "Text"],
            [
                [k, e.content["kind"], worklog.state(log, k), e.content["text"]]
                for k, e in log.findings().items()
            ],
        )
        + _table(
            "The decisions of the log: the freeze and the outcome code's identity"
            " first.",
            ["Subject", "Decision", "Reason", "By"],
            [
                [c["subject"], c["decision"], c["reason"], c["by"]]
                for c in (e.content for e in log.of(worklog.DECISION))
            ],
        )
        + "</section>"
    )
    parts.append(
        "<section aria-labelledby='claims'><h2 id='claims'>Claims and their"
        " evidence</h2>"
        + _table(
            "Every claim with its run links and its status.",
            ["Claim", "Status", "Runs", "Text"],
            [
                [c.id, _status(status[c.id]), ", ".join(c.runs), c.text]
                for c in data["ledger"].claims
            ],
            raw=(1,),
        )
        + "</section>"
    )
    parts.append(
        "</main><footer>Data: A. Taspinar, F140 pilot (Analog Discovery 3),"
        " 2026-11-22, CC BY 4.0 (ad3-rlc-pilot).</footer></body></html>\n"
    )
    return "".join(parts)


def write(data: dict, path: Path, *, figure: bool = True) -> None:
    Path(path).write_text(render(data, figure=figure), encoding="utf-8")
