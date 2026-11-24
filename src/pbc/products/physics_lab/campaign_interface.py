"""The campaign section of the local interface (F145): the configuration of
a campaign (the plan, the route, the confirmation of the declared circuit),
its progress measurement by measurement, its results with their intervals,
the consistency verdict, the invalid measurements and failures with what to
do, the stop, and the export.

It is part of the same server-rendered page as F138's sweep
(``interface.App``), under the same loopback, Host, Origin, and token rules:
standard library only, no JavaScript, no build step (ADR 022 decision 5).
An invalid measurement is shown by its word and its reason, never by
colour alone. The campaign runs in the simulated mode from the example
plans; a live campaign is started from the command line, where the learner
sees the confirmation text before the device opens.
"""

import html
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pbc.instruments import SIMULATED
from pbc.products.physics_lab import lab
from pbc.products.physics_lab.campaign import Campaign, Record
from pbc.products.physics_lab.campaign_report import (
    ALT_AMPLITUDE,
    ALT_FREQUENCY,
    ALT_RINGDOWN,
)

PLANS = ("campaign-series-rlc.toml", "campaign-led-pair.toml")
PLAN_TEXT = {
    "campaign-series-rlc.toml": "Series RLC circuit: frequency response and"
    " ring-down, checked against each other",
    "campaign-led-pair.toml": "LED pair: amplitude-dependent response, with the"
    " held-out prediction",
}
ROUTE_TEXT = {
    lab.ADAPTIVE: "Classical adaptive policy",
    lab.SCRIPTED: "Scripted sweep, no refinement",
    lab.AGENT: "Bounded agent, replayed from its trace",
}
EXPORTS = (
    "report.md",
    "raw.csv",
    "measurements.csv",
    "run.json",
    "evidence.json",
    "frequency-response.svg",
    "ringdown.svg",
    "amplitude-response.svg",
)
FIGURES = (
    ("frequency-response.svg", ALT_FREQUENCY),
    ("ringdown.svg", ALT_RINGDOWN),
    ("amplitude-response.svg", ALT_AMPLITUDE),
)


@dataclass
class CampaignState:
    status: str = "idle"  # idle, running, finished, failed
    plan_name: str = PLANS[0]
    route: str = lab.ADAPTIVE
    records: list[Record] = field(default_factory=list)
    result: lab.LabResult | None = None
    error: str | None = None
    campaign: Campaign | None = None


class CampaignRunner:
    """Starts and holds one campaign at a time."""

    def __init__(
        self,
        out_root: Path,
        threaded: bool = True,
        runner: Callable[..., lab.LabResult] = lab.run_campaign,
    ):
        self.out_root = out_root
        self.threaded = threaded
        self.runner = runner
        self.state = CampaignState()
        self._lock = threading.Lock()

    def start(self, form: dict[str, str]) -> None:
        with self._lock:
            if self.state.status == "running":
                return
            plan_name = form.get("plan", PLANS[0])
            route = form.get("route", lab.ADAPTIVE)
            if plan_name not in PLANS or route not in lab.ROUTES:
                self.state = CampaignState(
                    status="failed", error="Choose one of the plans and routes shown."
                )
                return
            confirmed = form.get("circuit_confirmed") == "yes"
            self.state = CampaignState("running", plan_name, route)
        arguments = (plan_name, route, confirmed)
        if self.threaded:
            threading.Thread(target=self._run, args=arguments, daemon=True).start()
        else:
            self._run(*arguments)

    def _run(self, plan_name: str, route: str, confirmed: bool) -> None:
        state = self.state
        try:
            plan, seed = lab.load_plan(lab.EXAMPLES / plan_name)
            out_dir = self.out_root / f"campaign-{plan.circuit}-{route}-seed{seed}"
            result = self.runner(
                plan,
                out_dir,
                route=route,
                mode=SIMULATED,
                seed=seed,
                confirmed=confirmed,
                on_record=state.records.append,
                on_campaign=lambda c: setattr(state, "campaign", c),
            )
        except Exception as error:  # shown on the page, never swallowed
            state.status, state.error = "failed", f"{error}"
            return
        state.result = result
        failed = result.segment.status in ("failed", "interrupted")
        state.status = "failed" if failed else "finished"
        if failed:
            state.error = "; ".join(result.segment.diagnostics) or result.segment.status

    def stop(self) -> None:
        campaign = self.state.campaign
        if self.state.status == "running" and campaign is not None:
            campaign.instrument.request_stop("stopped from the interface")

    def file(self, name: str) -> Path | None:
        result = self.state.result
        if name not in EXPORTS or result is None:
            return None
        path = result.out_dir / name
        return path if path.is_file() else None


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def form(state: CampaignState, token_field: str) -> str:
    def option(name: str, value: str, label: str, current: str) -> str:
        checked = " checked" if value == current else ""
        return (
            f'<label><input type="radio" name="{name}" value="{value}"{checked}>'
            f" {_e(label)}</label>"
        )

    plans = "\n".join(option("plan", p, PLAN_TEXT[p], state.plan_name) for p in PLANS)
    routes = "\n".join(
        option("route", r, ROUTE_TEXT[r], state.route) for r in lab.ROUTES
    )
    return f"""
<form method="post" action="/campaign">
  {token_field}
  <h2>Run a campaign</h2>
  <fieldset><legend>Plan and circuit</legend>{plans}</fieldset>
  <fieldset><legend>Route</legend>{routes}</fieldset>
  <fieldset><legend>Circuit</legend>
    <label><input type="checkbox" name="circuit_confirmed" value="yes">
      The circuit of the plan is connected as declared. The product never
      rewires it; another circuit is another plan.</label>
  </fieldset>
  <button type="submit">Start the campaign</button>
</form>"""


def _record_row(record: Record) -> str:
    setting = "" if record.step.setting is None else f"{record.step.setting:g}"
    state = "valid" if record.valid else f"invalid: {record.note}"
    return (
        f"<tr><td>{_e(record.id)}</td><td>{_e(record.step.protocol)}</td>"
        f"<td>{_e(setting)}</td><td>{_e(record.step.stage)}</td>"
        f"<td>{_e(state)}</td></tr>"
    )


def _interval(e: dict[str, float] | None, digits: int) -> str:
    if e is None:
        return "none"
    return f"{e['value']:.{digits}f} ± {2 * e['se']:.{digits}f}"


def results(state: CampaignState, token_field: str) -> str:
    parts = []
    if state.status == "running":
        rows = "".join(_record_row(r) for r in state.records[-8:])
        parts.append(
            f'<p class="status">Campaign running: {len(state.records)}'
            " measurements so far.</p>"
            f'<form method="post" action="/campaign/stop">{token_field}<button'
            ' class="stop" type="submit">Stop the instrument</button></form>'
            f"<table><thead><tr><th>Id</th><th>Protocol</th><th>Setting</th>"
            f"<th>Stage</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table>"
        )
    if state.error:
        parts.append(
            '<div class="failure" role="alert"><p class="status">The campaign did'
            f" not finish.</p><p>{_e(state.error)}</p><p>An open interlock means"
            " the circuit was not confirmed. A stopped campaign keeps its"
            " checkpoint; resume it from the command line with --resume, or start"
            " it again here.</p></div>"
        )
    if state.result is not None:
        parts.append(_finished(state.result))
    return "\n".join(parts)


def _finished(result: lab.LabResult) -> str:
    evaluation: dict[str, Any] = result.evaluation
    rows = []
    fit = evaluation.get("frequency-response", {}).get("fit")
    if fit is not None:
        rows.append(("f0, frequency response (Hz)", _interval(fit["f0_hz"], 1)))
        rows.append(("Q, frequency response", _interval(fit["q"], 4)))
    transient = evaluation.get("transient", {})
    if transient.get("f0_hz") is not None:
        rows.append(("f0, ring-down (Hz)", _interval(transient["f0_hz"], 1)))
        rows.append(("Q, ring-down", _interval(transient["q"], 4)))
    table = "".join(f"<tr><td>{_e(a)}</td><td>{_e(b)}</td></tr>" for a, b in rows)
    verdicts = []
    for a in evaluation.get("agreements", []):
        word = "agree" if a["agree"] else "do not agree"
        verdicts.append(
            f"<li>{_e(a['quantity'])}: the two protocols {word}"
            f" ({a['sigmas']:.2f} combined standard errors apart).</li>"
        )
    amplitude = evaluation.get("amplitude-response", {})
    held = amplitude.get("held_out")
    if held is not None:
        word = "agrees" if held["agree"] else "does not agree"
        verdicts.append(
            f"<li>The characteristic fitted at {held['fitted_on_v']:g} V {word}"
            " with the gain at every other amplitude.</li>"
        )
    for protocol, check in evaluation.get("simulator_checks", {}).items():
        word = "passes" if check["correct"] else "fails"
        verdicts.append(f"<li>{_e(protocol)} {word} the closed form's check.</li>")
    invalid = [r for r in result.records if not r.valid]
    invalid_html = (
        "<h3>Invalid measurements, recorded and never fitted</h3><ul>"
        + "".join(f"<li>{_e(r.id)}: {_e(r.note)}</li>" for r in invalid)
        + "</ul>"
        if invalid
        else ""
    )
    figures = []
    for name, alt in FIGURES:
        path = result.out_dir / name
        if path.is_file():
            svg = path.read_text(encoding="utf-8")
            svg = svg[svg.find("<svg") :]
            figures.append(f'<figure role="img" aria-label="{_e(alt)}">{svg}</figure>')
    answer = (
        f'<p class="unverified">The agent said, unverified: {_e(result.answer)}</p>'
        if result.answer
        else ""
    )
    links = " ".join(
        f'<a href="/campaign-files/{n}">{n}</a>'
        for n in EXPORTS
        if (result.out_dir / n).is_file()
    )
    return f"""
<h2>Campaign by the {_e(result.route)} route</h2>
<p>{len(result.records)} measurements, {len(invalid)} invalid; segment
{_e(result.segment.status)}. Intervals are the value ± two standard errors,
recomputed from the raw samples.</p>
<table><thead><tr><th>Quantity</th><th>Interval</th></tr></thead>
<tbody>{table}</tbody></table>
<ul>{"".join(verdicts)}</ul>{invalid_html}{answer}{"".join(figures)}
<p>Exported to {_e(result.out_dir)}: {links}</p>"""
