"""The experiment of the capstone "Autonomous Physics Lab" (SA9, F145).

It runs the reference workflow of the product ``pbc.products.physics_lab``
on the simulated bench, with the example inputs of
``products/physics-lab/examples/``, as a learner runs it from the command
line (``products/physics-lab/WORKFLOW.md``):

- the series RLC campaign of ``campaign-series-rlc.toml`` by the classical
  adaptive policy: the frequency-response sweep, its refinement, and the
  repeated ring-downs. One change is made on purpose: the link between the
  bench and the program loses a burst of samples in one acquisition, below
  the guarded instrument, so that the quality gate refuses that measurement
  and the policy repeats it;
- the LED pair of ``campaign-led-pair.toml``: the amplitude response, the
  fitted characteristic, and the held-out check;
- the agent route, replayed from its committed trace (a scripted
  placeholder, not a model), beside the adaptive policy and the scripted
  sweep on fresh benches of the same plan and seed;
- a circuit that is not what the plan declares (the inductance, the
  capacitance, and a series loss off by the amounts of F140's pilot): the
  closed-form check fails and the two protocols still agree;
- the pilot's measured sweep ``ad3-rlc-pilot``, replayed by the recorded
  adapter through F138's protocol and drawn by the dataset's reference
  code, as it is.

Every number comes from the product's own export and evaluator. No device,
no model, and no key is used. Run it as a program to write the figures and
numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.autonomous_physics_lab out
"""

import json
import tempfile
import textwrap
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.data.figure_provenance import FigureProvenance
from pbc.electromagnetism import pilot_record
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, MARKER, MUTED, figsize, figure_style, finish
from pbc.instruments import SIMULATED, SINE, Capture, Refused
from pbc.instruments.conformance import CallLog
from pbc.instruments.contract import driver_waveforms
from pbc.instruments.simulated import SimulatedRLCBench
from pbc.products.physics_lab import (
    bench,
    lab,
    quality,
    resonance,
    transient,
)
from pbc.products.physics_lab.campaign import (
    FREQUENCY_RESPONSE,
    TRANSIENT,
    Campaign,
    Record,
    next_step,
    run_segment,
)

EXAMPLES = lab.EXAMPLES
RLC_PLAN = EXAMPLES / "campaign-series-rlc.toml"
LED_PLAN = EXAMPLES / "campaign-led-pair.toml"
# region: lossy-link
# The acquisition (counted from 1) in which the link loses samples, and how
# many consecutive samples it loses there.
LOST_AT = 10
LOST_SAMPLES = 40
# endregion: lossy-link
# region: mismatch
# The circuit on the bench when the plan declares EM5's parts: the ratios of
# F140's pilot (L 0.861 and C 1.455 times the labels, a coil loss of 63 ohm
# beside the 100 ohm resistor), held constant over frequency.
L_RATIO, C_RATIO, LOSS_OHM = 0.861, 1.455, 63.0
# endregion: mismatch
PILOT_FIGURE = FigureProvenance(
    status="processed",
    dataset="ad3-rlc-pilot",
    combines=("simulated",),
    processing="The pilot's raw traces (raw.csv of the sweep capacitor),"
    " unmodified; the phasor fits and the gain and phase (the dataset's reading,"
    " pbc.data.reference.ad3_rlc_pilot), the closed form of the parts' labels,"
    " and the residual of the gain: this lesson's code, not part of the record.",
)


# -- the lossy link -----------------------------------------------------------------


class LossyLink:
    """The driver of the simulated bench behind a link that loses
    ``LOST_SAMPLES`` samples of acquisition number ``LOST_AT``: below the
    guarded instrument, where a real cable or USB link loses them. Its
    identity says so, so the run record names the fault."""

    def __init__(self, driver: Any, at: int = LOST_AT, length: int = LOST_SAMPLES):
        self.driver = driver
        self.mode = driver.mode
        self.waveforms = driver_waveforms(driver)
        self.at, self.length = at, length
        self.captures = 0

    def identity(self) -> dict[str, str]:
        identity = dict(self.driver.identity())
        identity["link"] = (
            f"loses {self.length} samples of acquisition {self.at}, on purpose"
        )
        return identity

    def set_output(
        self, amplitude_v: float, frequency_hz: float, waveform: str = SINE
    ) -> None:
        if waveform == SINE:
            self.driver.set_output(amplitude_v, frequency_hz)
        else:
            self.driver.set_output(amplitude_v, frequency_hz, waveform=waveform)

    def output_off(self) -> None:
        self.driver.output_off()

    def capture(self, sample_rate_hz: float, samples: int) -> Capture:
        capture = self.driver.capture(sample_rate_hz, samples)
        self.captures += 1
        if self.captures != self.at:
            return capture
        channels = {}
        for name, values in capture.channels.items():
            kept = np.array(values, dtype=float)
            kept[samples // 3 : samples // 3 + self.length] = np.nan
            channels[name] = kept
        return Capture(capture.sample_rate_hz, capture.t, channels, capture.units)


def behind_lossy_link(campaign: Campaign) -> None:
    """Put the bench of ``campaign`` behind the lossy link, before its first
    measurement (``lab.run_campaign``'s ``on_campaign``)."""
    instrument = campaign.instrument
    instrument._driver = LossyLink(instrument._driver)


def on_another_circuit(circuit: SeriesRLC, seed: int):
    """``on_campaign``: the bench holds ``circuit``, whatever the plan
    declares."""

    def swap(campaign: Campaign) -> None:
        campaign.instrument._driver = SimulatedRLCBench(circuit=circuit, seed=seed)

    return swap


# -- the safety boundary -------------------------------------------------------------


def refusals(plan) -> tuple[list[tuple[str, str, str]], int]:
    """What the guarded instrument answers to four requests, and how many
    calls of the four reached the bench (a call log below the guard)."""
    rows, reached = [], 0
    requests = (
        ("1 V at 5 kHz, the circuit not confirmed", False, (1.0, 5000.0), False),
        ("5 V at 5 kHz", True, (5.0, 5000.0), False),
        ("1 V at 80 kHz", True, (1.0, 80_000.0), False),
        ("1 V at 5 kHz after a stop", True, (1.0, 5000.0), True),
    )
    for label, confirmed, arguments, stopped in requests:
        instrument, _ = bench.make_instrument(plan, SIMULATED, confirmed=confirmed)
        log = CallLog(instrument._driver)
        instrument._driver = log
        if stopped:
            instrument.request_stop("stop requested by the learner")
        try:
            instrument.excite(*arguments)
            answer = "accepted"
        except Refused as reason:
            answer = str(reason)
        reached += len(log.device_calls())
        rows.append((label, "accepted" if answer == "accepted" else "refused", answer))
    return rows, reached


# -- the tables ----------------------------------------------------------------------


def setting_text(record: Record) -> str:
    if record.step.protocol == FREQUENCY_RESPONSE:
        return f"{record.step.setting:,.1f} Hz"
    if record.step.protocol == TRANSIENT:
        return "step 0 to 1 V"
    return f"{record.step.setting:g} V"


def result_text(record: Record) -> str:
    n = record.numbers
    if not record.valid:
        return "refused: " + record.note
    if record.step.protocol == FREQUENCY_RESPONSE:
        return f"gain {n['gain']:.4f}, phase {n['phase_deg']:.2f} deg"
    if record.step.protocol == TRANSIENT:
        return f"f0 {n['f0_hz']:,.1f} Hz, Q {n['q']:.4f}"
    return f"gain {n['gain']:.4f}, h3 {n['h3']:.4f}"


def measurement_rows(records: Sequence[Record]) -> list[tuple[Any, ...]]:
    return [
        (
            r.id,
            r.step.protocol,
            r.step.stage,
            setting_text(r),
            ", ".join(r.step.basis) or "-",
            result_text(r),
        )
        for r in records
    ]


MEASUREMENT_COLUMNS = [
    ("id", "", ""),
    ("protocol", "", ""),
    ("stage", "", ""),
    ("setting", "", ""),
    ("follows from", "", ""),
    ("what it gave", "", ""),
]


def check_rows(evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Each protocol's estimates against the closed form of the declared
    circuit, as the evaluator computed them from ``raw.csv``."""
    rows = []
    fit = evaluation[FREQUENCY_RESPONSE]["fit"]
    checks = evaluation["simulator_checks"]
    ring = evaluation[TRANSIENT]
    pairs = (
        ("frequency response", fit["f0_hz"], fit["q"], checks.get(FREQUENCY_RESPONSE)),
        ("ring-down", ring["f0_hz"], ring["q"], checks.get(TRANSIENT)),
    )
    for name, f0, q, check in pairs:
        rows.append(
            (
                name,
                f0["value"],
                f0["se"],
                q["value"],
                q["se"],
                check["reference_f0_hz"],
                check["reference_q"],
                "passed" if check["correct"] else "failed",
            )
        )
    return rows


CHECK_COLUMNS = [
    ("protocol", "", ""),
    ("f0", "Hz", ",.2f"),
    ("its standard error", "Hz", ".2f"),
    ("Q", "", ".4f"),
    ("its standard error", "", ".4f"),
    ("f0 of the closed form", "Hz", ",.2f"),
    ("Q of the closed form", "", ".4f"),
    ("check", "", ""),
]


def agreement_rows(evaluation: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            "f0" if a["quantity"] == "f0_hz" else "Q",
            a["difference"],
            a["combined_se"],
            a["sigmas"],
            "agree" if a["agree"] else "disagree",
        )
        for a in evaluation["agreements"]
    ]


AGREEMENT_COLUMNS = [
    ("quantity", "", ""),
    ("frequency response minus ring-down", "", ".4g"),
    ("combined standard error", "", ".4g"),
    ("difference in combined standard errors", "", ".2f"),
    ("verdict (within 2)", "", ""),
]


def route_rows(comparison: dict[str, Any]) -> list[tuple[Any, ...]]:
    return [
        (
            route,
            comparison["measurements"][route],
            entry["measurements"],
            entry["final_width"],
            entry["needed"],
        )
        for route, entry in comparison["routes"].items()
    ]


ROUTE_COLUMNS = [
    ("route", "", ""),
    ("measurements, all protocols", "", "d"),
    ("frequency-response measurements", "", "d"),
    ("final relative width of f0", "", ".2e"),
    ("needed for the common width", "", "d"),
]


# -- the routes ----------------------------------------------------------------------


def route_histories(plan, seed: int, agent_records: Sequence[Record]) -> dict:
    """The width of the interval of f0 after each frequency-response
    measurement, per route: the agent's replayed campaign, and the adaptive
    policy and the scripted sweep on fresh benches of the same plan and seed,
    as ``lab.baseline_comparison`` runs them."""
    histories = {lab.AGENT: lab.width_history(agent_records)}
    with tempfile.TemporaryDirectory() as scratch:
        for route, policy in (
            (lab.ADAPTIVE, next_step),
            (lab.SCRIPTED, lab.scripted_policy),
        ):
            instrument, rails = bench.make_instrument(
                plan, SIMULATED, seed=seed, confirmed=True
            )
            campaign = Campaign(plan, instrument, rails)
            run_segment(campaign, Path(scratch) / f"{route}.json", policy)
            histories[route] = lab.width_history(campaign.records)
    return histories


def needed_for_target(histories: dict, target: float) -> list[tuple[str, Any]]:
    """Exercise 2: the measurements each route needs for ``target``."""
    rows = []
    for route, history in histories.items():
        count = lab.needed(history, target)
        rows.append((route, "never, within its campaign" if count is None else count))
    return rows


# -- the figures ---------------------------------------------------------------------


def draw_frequency_response(records: Sequence[Record], fit: dict) -> Figure:
    """Gain and phase of every valid frequency-response measurement with one
    standard error, and the second-order response the evaluator fitted."""
    valid = [r for r in records if r.step.protocol == FREQUENCY_RESPONSE and r.valid]
    f = np.array([r.numbers["frequency_hz"] for r in valid])
    gain = np.array([r.numbers["gain"] for r in valid])
    gain_se = np.array([r.numbers["gain_se"] for r in valid])
    phase = np.array([r.numbers["phase_deg"] for r in valid])
    phase_se = np.array([r.numbers["phase_se_deg"] for r in valid])
    grid = np.geomspace(f.min(), f.max(), 400)
    h = resonance.model(
        grid, fit["f0_hz"]["value"], fit["q"]["value"], fit["k"]["value"]
    )
    with figure_style():
        fig, (top, bottom) = plt.subplots(
            2, 1, sharex=True, figsize=figsize("pair", legend=2)
        )
        for ax, y, se in ((top, gain, gain_se), (bottom, phase, phase_se)):
            ax.errorbar(
                f, y, yerr=se, linestyle="none", marker="o", markersize=MARKER,
                color=FIGURE_COLOURS[0], label="measured, one standard error",
            )  # fmt: skip
        top.plot(
            grid, np.abs(h), linestyle="--", color=FIGURE_COLOURS[1],
            linewidth=LINE["model"], label="fitted second-order response",
        )  # fmt: skip
        bottom.plot(
            grid, np.degrees(np.unwrap(np.angle(h))), linestyle="--",
            color=FIGURE_COLOURS[1], linewidth=LINE["model"],
        )  # fmt: skip
        bottom.axhline(-90.0, color=MUTED, linewidth=LINE["guide"], linestyle=":")
        top.set_xscale("log")
        top.set_yscale("log")
        top.set_ylabel("gain (V/V)")
        bottom.set_ylabel("phase (deg)")
        bottom.set_xlabel("frequency (Hz)")
        bottom.legend(
            *top.get_legend_handles_labels(),
            loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=1, frameon=False,
        )  # fmt: skip
    return finish(fig)


def draw_ringdown(ringdown: transient.Ringdown) -> Figure:
    """One ring-down after the step: the response the fit used, the fitted
    damped oscillation, and the residuals below."""
    start, end = ringdown.window
    t = np.asarray(ringdown.capture.t[start:end], dtype=float)
    v = np.asarray(ringdown.capture.channels["response"][start:end], dtype=float)
    t0 = t - t[0]
    curve = ringdown.fit.curve(t0)
    with figure_style():
        fig, (top, bottom) = plt.subplots(
            2, 1, sharex=True, figsize=figsize("pair", legend=2),
            gridspec_kw={"height_ratios": (2, 1)},
        )  # fmt: skip
        top.plot(
            1e3 * t0, v, linestyle="none", marker="o", markersize=MARKER - 3.0,
            color=FIGURE_COLOURS[0], label="response after the step",
        )  # fmt: skip
        top.plot(
            1e3 * t0, curve, linestyle="--", color=FIGURE_COLOURS[1],
            linewidth=LINE["model"], label="fitted damped oscillation",
        )  # fmt: skip
        bottom.plot(
            1e3 * t0, 1e3 * (v - curve), linestyle="none", marker="o",
            markersize=MARKER - 3.0, color=FIGURE_COLOURS[0],
        )  # fmt: skip
        bottom.axhline(0.0, color=MUTED, linewidth=LINE["guide"])
        top.set_ylabel("capacitor voltage (V)")
        bottom.set_ylabel("residual (mV)")
        bottom.set_xlabel("time from the start of the fit (ms)")
        bottom.legend(
            *top.get_legend_handles_labels(),
            loc="upper center", bbox_to_anchor=(0.5, -0.55), ncol=1, frameon=False,
        )  # fmt: skip
    return finish(fig)


def draw_amplitude_response(evaluation: dict[str, Any]) -> Figure:
    """The fundamental gain and the third-harmonic ratio of the LED pair
    against the source amplitude, and the gain predicted from the
    characteristic fitted at the largest amplitude alone."""
    result = evaluation["amplitude-response"]
    points = sorted(result["points"], key=lambda p: p["amplitude_v"])
    a = [p["amplitude_v"] for p in points]
    predicted = sorted(
        (g["amplitude_v"], g["b"]["value"], g["b"]["se"])
        for g in result["held_out"]["agreements"]
    )
    with figure_style():
        fig, (top, bottom) = plt.subplots(
            2, 1, sharex=True, figsize=figsize("pair", legend=2)
        )
        top.errorbar(
            a, [p["gain"] for p in points], yerr=[p["gain_se"] for p in points],
            linestyle="none", marker="o", markersize=MARKER,
            color=FIGURE_COLOURS[0], label="measured, one standard error",
        )  # fmt: skip
        top.errorbar(
            [x for x, _, _ in predicted], [y for _, y, _ in predicted],
            yerr=[s for _, _, s in predicted], linestyle="--", marker="s",
            markersize=MARKER, fillstyle="none", color=FIGURE_COLOURS[1],
            linewidth=LINE["model"],
            label=f"predicted from {result['held_out']['fitted_on_v']:g} V alone",
        )  # fmt: skip
        bottom.errorbar(
            a, [p["h3"] for p in points], yerr=[p["h3_se"] for p in points],
            linestyle="none", marker="o", markersize=MARKER, color=FIGURE_COLOURS[0],
        )  # fmt: skip
        top.set_ylabel("gain G1 (V/V)")
        bottom.set_ylabel("h3 = V3 / V1 (V/V)")
        bottom.set_xlabel("source amplitude (V)")
        bottom.legend(
            *top.get_legend_handles_labels(),
            loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=1, frameon=False,
        )  # fmt: skip
    return finish(fig)


ROUTE_STYLE = {
    lab.AGENT: ("o", "-", 0),
    lab.ADAPTIVE: ("s", "--", 1),
    lab.SCRIPTED: ("^", ":", 2),
}


def draw_routes(histories: dict, common: float, target: float) -> Figure:
    """The relative width of the interval of f0 after each frequency-response
    measurement, per route, on a log axis, with the common width of the
    comparison and the plan's target."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=3))
        # The scripted sweep last, with larger open markers: its points are
        # the adaptive policy's first ones and would hide under them.
        for route in sorted(histories, key=lambda r: r == lab.SCRIPTED):
            marker, style, colour = ROUTE_STYLE[route]
            shown = [(n, w) for n, w in histories[route] if w is not None]
            scripted = route == lab.SCRIPTED
            ax.plot(
                [n for n, _ in shown], [w for _, w in shown], marker=marker,
                fillstyle="none" if scripted else "full", linestyle=style,
                markersize=MARKER + 3.0 if scripted else MARKER,
                linewidth=LINE["data"], color=FIGURE_COLOURS[colour],
                label=f"{route} route",
            )  # fmt: skip
        ax.axhline(common, color=MUTED, linewidth=LINE["guide"], linestyle="-.")
        ax.axhline(target, color=MUTED, linewidth=LINE["guide"], linestyle=":")
        ax.annotate("common width", (ax.get_xlim()[0], common), xytext=(4, 3),
                    textcoords="offset points", color=MUTED)  # fmt: skip
        ax.annotate("plan's target", (ax.get_xlim()[0], target), xytext=(4, -12),
                    textcoords="offset points", color=MUTED)  # fmt: skip
        ax.set_yscale("log")
        ax.set_xlabel("frequency-response measurements")
        ax.set_ylabel("relative width of f0")
        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=False
        )
    return finish(fig, grid=True)


# -- the experiment ------------------------------------------------------------------


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    plan, seed = lab.load_plan(RLC_PLAN)
    led_plan, led_seed = lab.load_plan(LED_PLAN)
    reference = transient.reference(plan.declared_circuit)
    experiment.number("f0", reference["f0_hz"], ",.1f")
    experiment.number("q", reference["q"], ".3f")
    experiment.number("seed", seed, "d")
    experiment.number("budget", plan.budget, "d")
    experiment.number("sweep-points", plan.sweep_points, "d")
    experiment.number("ringdowns", plan.min_ringdowns, "d")
    experiment.number("f0-target", 100 * plan.f0_target, ".3f")
    experiment.number("q-target", 100 * plan.q_target, ".0f")
    experiment.number("max-missing", 100 * quality.MAX_MISSING, "g")

    experiment.table(
        "envelope",
        [
            (limit["quantity"], limit["low"], limit["high"], limit["unit"])
            for limit in bench.lab_envelope(plan, False).describe()["limits"]
        ],
        [
            ("quantity", "", ""),
            ("lowest", "", ",.10g"),
            ("highest", "", ",.10g"),
            ("unit", "", ""),
        ],
        "The envelope of the simulated bench, enforced by the guarded instrument"
        " before any call reaches the bench.",
    )
    refused, reached = refusals(plan)
    experiment.table(
        "refusals",
        refused,
        [
            ("request", "", ""),
            ("verdict", "", ""),
            ("what the instrument said", "", ""),
        ],
        "Four requests to the guarded instrument of the simulated bench, and"
        " what it answered.",
    )
    experiment.number("calls-reaching-bench", reached, "d")
    with experiment.capture("confirmation"):
        print(textwrap.fill(bench.confirmation(plan, live=False), 72))

    with tempfile.TemporaryDirectory() as name:
        scratch = Path(name)

        # The series RLC campaign, behind the lossy link.
        rlc = lab.run_campaign(
            plan,
            scratch / "rlc",
            seed=seed,
            confirmed=True,
            on_campaign=behind_lossy_link,
        )
        records = rlc.records
        invalid = [r for r in records if not r.valid]
        experiment.table(
            "campaign-measurements",
            measurement_rows(records),
            MEASUREMENT_COLUMNS,
            "Every measurement of the series RLC campaign, in the order made: the"
            " stage that asked for it, the measurements it follows from, and what"
            " the protocol read from it.",
        )
        experiment.number("measurements", len(records), "d")
        experiment.number("segment-status", rlc.segment.status)
        experiment.number("invalid", len(invalid), "d")
        experiment.number("invalid-id", invalid[0].id)
        experiment.number("retry-id", records[records.index(invalid[0]) + 1].id)
        experiment.number(
            "refinements", sum(r.step.stage == "refine" for r in records), "d"
        )
        evaluation = rlc.evaluation
        fit = evaluation[FREQUENCY_RESPONSE]["fit"]
        experiment.number(
            "valid-points", evaluation[FREQUENCY_RESPONSE]["valid_points"], "d"
        )
        experiment.number("reduced-chi2", fit["reduced_chi2"], ".2f")
        experiment.figure(
            "fig-frequency-response", partial(draw_frequency_response, records, fit)
        )
        ring_record = next(r for r in records if r.step.protocol == TRANSIENT)
        ringdown = transient.analyse_ringdown(
            ring_record.capture, plan.transient_settings, bench.rails_for(SIMULATED)
        )
        experiment.number("ring-samples", ringdown.fit.samples, ",d")
        experiment.figure("fig-ringdown", partial(draw_ringdown, ringdown))
        experiment.table(
            "simulator-checks",
            check_rows(evaluation),
            CHECK_COLUMNS,
            "f0 and Q of each protocol, recomputed by the evaluator from raw.csv,"
            " against the closed form of the declared circuit: the simulator's"
            " check.",
        )
        experiment.table(
            "consistency",
            agreement_rows(evaluation),
            AGREEMENT_COLUMNS,
            "The independent check of a real circuit: the two protocols on the"
            " same circuit, f0 in Hz and Q dimensionless.",
        )
        run_json = json.loads((rlc.out_dir / "run.json").read_text(encoding="utf-8"))
        experiment.table(
            "export",
            [
                (path.name, what)
                for path, what in (
                    (
                        rlc.out_dir / "raw.csv",
                        "every sample of every acquisition, valid or not",
                    ),
                    (
                        rlc.out_dir / "measurements.csv",
                        "what each measurement gave, valid or not, and why",
                    ),
                    (rlc.out_dir / "report.md", "the report, with its figures"),
                    (
                        rlc.out_dir / "run.json",
                        "the run record: modes, plan, checks, invalid measurements",
                    ),
                    (rlc.out_dir / "evidence.json", "the evaluator's ledger"),
                )
                if path.exists()
            ],
            [("file", "", ""), ("what it holds", "", "")],
            "The export of the series RLC campaign.",
        )
        experiment.number("execution-modes", ", ".join(run_json["execution_modes"]))
        experiment.number("link", run_json["run"]["device"]["link"])

        # The LED pair.
        led = lab.run_campaign(led_plan, scratch / "led", seed=led_seed, confirmed=True)
        led_eval = led.evaluation["amplitude-response"]
        characteristic = led_eval["characteristic"]
        check = led.evaluation["simulator_checks"]["amplitude-response"]
        experiment.figure(
            "fig-amplitude-response", partial(draw_amplitude_response, led.evaluation)
        )
        experiment.number("led-measurements", len(led.records), "d")
        experiment.number("led-fitted-on", led_eval["held_out"]["fitted_on_v"], "g")
        held = led_eval["held_out"]["agreements"]
        experiment.number("held-out-points", len(held), "d")
        experiment.number("held-out-worst", max(g["sigmas"] for g in held), ".2f")
        experiment.number(
            "held-out-verdict", "agree" if led_eval["held_out"]["agree"] else "disagree"
        )
        experiment.table(
            "led-characteristic",
            [
                (
                    "ideality factor n",
                    characteristic["n"]["value"],
                    characteristic["n"]["se"],
                    check["reference_n"],
                ),
                (
                    "voltage at 1 mA (V)",
                    characteristic["v_ref"]["value"],
                    characteristic["v_ref"]["se"],
                    check["reference_v_ref"],
                ),
            ],
            [
                ("quantity", "", ""),
                ("fitted", "", ".4f"),
                ("standard error", "", ".4f"),
                ("of the simulated LEDs", "", ".4f"),
            ],
            "The characteristic of the LED pair fitted over every valid"
            " amplitude, against the LEDs the simulated bench holds.",
        )
        experiment.number("led-check", "passed" if check["correct"] else "failed")

        # The agent route beside the baselines.
        agent = lab.run_campaign(
            plan, scratch / "agent", seed=seed, confirmed=True, route=lab.AGENT
        )
        agent_json = json.loads(
            (agent.out_dir / "run.json").read_text(encoding="utf-8")
        )
        comparison = agent_json["comparison"]
        experiment.table(
            "routes",
            route_rows(comparison),
            ROUTE_COLUMNS,
            "The agent route, replayed from its scripted placeholder trace, beside"
            " the classical adaptive policy and the scripted sweep on fresh benches"
            " of the same plan and seed.",
        )
        experiment.number("common-width", comparison["target"], ".2e")
        experiment.number("agent-answer", agent.answer)
        histories = route_histories(plan, seed, agent.records)
        experiment.figure(
            "fig-routes",
            partial(draw_routes, histories, comparison["target"], plan.f0_target),
        )
        experiment.table(
            "needed-for-target",
            needed_for_target(histories, plan.f0_target),
            [("route", "", ""), ("frequency-response measurements needed", "", "")],
            "The measurements each route needs for the plan's own target width of f0.",
        )

        # A circuit that is not what the plan declares.
        declared = plan.declared_circuit
        actual = SeriesRLC(
            resistance=declared.resistance + LOSS_OHM,
            inductance=L_RATIO * declared.inductance,
            capacitance=C_RATIO * declared.capacitance,
        )
        other = lab.run_campaign(
            plan,
            scratch / "other",
            seed=seed,
            confirmed=True,
            on_campaign=on_another_circuit(actual, seed),
        )
        actual_reference = transient.reference(actual)
        experiment.number("actual-f0", actual_reference["f0_hz"], ",.0f")
        experiment.number("actual-q", actual_reference["q"], ".2f")
        experiment.table(
            "mismatch-checks",
            check_rows(other.evaluation),
            CHECK_COLUMNS,
            "The same campaign on a bench whose parts are not the declared ones:"
            " each protocol against the closed form of the declared circuit.",
        )
        experiment.table(
            "mismatch-consistency",
            agreement_rows(other.evaluation),
            AGREEMENT_COLUMNS,
            "The two protocols on that bench, f0 in Hz and Q dimensionless.",
        )

        # The pilot's measured sweep, as it is.
        replay = pilot_record.replay(scratch / "pilot")
        metrics = replay.check.metrics
        experiment.table(
            "pilot",
            [
                (
                    "f0 (Hz)",
                    f"{metrics['f0_hz']:,.0f}",
                    f"{metrics['reference_f0_hz']:,.0f}",
                ),
                ("Q", f"{metrics['q']:.3f}", f"{metrics['reference_q']:.3f}"),
            ],
            [
                ("quantity", "", ""),
                ("from the recorded sweep", "", ""),
                ("closed form of the labels", "", ""),
            ],
            "The pilot's capacitor sweep, replayed by the recorded adapter through"
            " the frequency-response protocol of the slice, against the closed"
            " form of the parts' labels.",
        )
        experiment.number("pilot-points", len(replay.measurements), "d")
        experiment.number("pilot-mode", replay.run.mode)
        experiment.number("pilot-check", "passed" if replay.check.correct else "failed")
        experiment.number(
            "pilot-f0-error", 100 * abs(metrics["f0_relative_error"]), ".1f"
        )
        experiment.number(
            "pilot-q-error", 100 * abs(metrics["q_relative_error"]), ".0f"
        )
    experiment.figure(
        "fig-pilot-discrepancy",
        pilot_record.draw_discrepancy,
        provenance=PILOT_FIGURE,
    )
    return experiment


if __name__ == "__main__":
    main(run)
