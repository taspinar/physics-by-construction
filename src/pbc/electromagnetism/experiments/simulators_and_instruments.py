"""The experiment of the lesson "Connecting simulators and instruments".

One procedure measures the response of the series RLC circuit of the lesson
"RLC circuits and resonance" through the guarded instrument of
``pbc.instruments``: on the simulated adapter, a model of the bench, and on
the recorded adapter, a sample of earlier captures declared as simulated.
The same instrument refuses what is outside its envelope before anything
reaches the adapter, which a call log shows, and every adapter is put
through the same contract tests. No live hardware is used or shown. Run it
as a program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.simulators_and_instruments out
"""

import math
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.messages import ToolCall
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.electromagnetism.circuits import steady_phasor
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, MARKER, figsize, figure_style, finish
from pbc.instruments import MODES, Envelope, Instrument, Limit, Refused
from pbc.instruments.conformance import (
    CHECKS,
    CallLog,
    Finding,
    Setting,
    check_driver,
)
from pbc.instruments.recorded import (
    Declaration,
    RecordedBench,
    RecordedSample,
    record_sample,
)
from pbc.instruments.simulated import BENCH_CIRCUIT, SimulatedRLCBench

SEED = 7
# region: envelope
ENVELOPE = Envelope(
    amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
    frequency=Limit("excitation frequency", "Hz", 100.0, 50_000.0),
    sample_rate=Limit("sample rate", "samples/s", 1_000.0, 5_000_000.0),
    samples=Limit("samples per acquisition", "samples", 16, 16_384, integer=True),
    timeout_s=5.0,
)
# endregion: envelope
AMPLITUDE_V = 1.0
SAMPLES_PER_PERIOD = 64
PERIODS = 8
FREQUENCIES_HZ = (2_000.0, 3_000.0, 4_000.0, 4_500.0, 5_000.0, 5_500.0, 6_000.0,
                  7_000.0, 8_000.0)  # fmt: skip
# A frequency between two recorded ones, for the prediction of the page.
BETWEEN_HZ = 5_250.0
# The gain the procedure measures, against the closed form, within this
# fraction; the bench's noise of 2 mV sets it.
GAIN_TOLERANCE = 0.005
PHASE_TOLERANCE_DEG = 0.5


def measure_response(
    instrument: Instrument, frequency_hz: float
) -> tuple[float, float]:
    """The gain and the phase (degrees) of the response channel against the
    source channel at ``frequency_hz``, measured through ``instrument``,
    whatever adapter is below it: eight periods at 64 samples per period."""
    instrument.excite(AMPLITUDE_V, frequency_hz)
    rate = SAMPLES_PER_PERIOD * frequency_hz
    capture = instrument.acquire(rate, PERIODS * SAMPLES_PER_PERIOD + 1)
    omega = 2.0 * math.pi * frequency_hz
    source = steady_phasor(capture.channels["source"], capture.t, omega)
    response = steady_phasor(capture.channels["response"], capture.t, omega)
    ratio = response / source
    return abs(ratio), math.degrees(math.atan2(ratio.imag, ratio.real))


def sweep(instrument: Instrument) -> list[tuple[float, float, float]]:
    """``measure_response`` at every frequency of the lesson, in order, as
    rows (frequency, gain, phase)."""
    return [(f, *measure_response(instrument, f)) for f in FREQUENCIES_HZ]


def closed_form(frequency_hz: float) -> tuple[float, float]:
    """The gain and phase (degrees) of the capacitor voltage of the bench's
    circuit for a source of one volt, from its phasor (EM5)."""
    ratio = BENCH_CIRCUIT.capacitor_phasor(1.0, 2.0 * math.pi * frequency_hz)
    return abs(ratio), math.degrees(math.atan2(ratio.imag, ratio.real))


def recorded_sample() -> RecordedSample:
    """The captures of the sweep, made once on a simulated bench and declared
    as a simulated sample: what a recorded adapter replays."""
    declaration = Declaration(
        dataset="rlc-bench-sweep",
        origin="simulated",
        description="the sweep of the lesson, recorded from the simulated bench",
        units={"source": "V", "response": "V"},
        provenance="pbc.instruments.simulated.SimulatedRLCBench, seed 7",
    )
    settings = [
        (AMPLITUDE_V, f, SAMPLES_PER_PERIOD * f, PERIODS * SAMPLES_PER_PERIOD + 1)
        for f in FREQUENCIES_HZ
    ]
    return record_sample(SimulatedRLCBench(seed=SEED), settings, declaration)


class ForgetfulBench(SimulatedRLCBench):
    """The simulated bench with one fault, for the exercise: switching the
    output off does nothing."""

    def output_off(self) -> None:
        pass


def refusals(experiment: Experiment) -> None:
    """Requests outside the envelope, through the instrument and through a
    tool whose own bounds are wider; a call log shows what reached the
    adapter."""
    log = CallLog(SimulatedRLCBench(seed=SEED))
    instrument = Instrument(log, ENVELOPE)

    def excite(amplitude_v: float, frequency_hz: float) -> dict[str, float]:
        instrument.excite(amplitude_v, frequency_hz)
        return {"ok": 1.0}

    careless = Tool(
        "excite",
        "set the output",
        (
            Parameter("amplitude_v", "V", 0, 1000),
            Parameter("frequency_hz", "Hz", 0, 1e9),
        ),
        excite,
    )
    # region: requests
    requests = [
        ("excite 12 V at 5 kHz", lambda: instrument.excite(12.0, 5_000.0)),
        ("excite 1 V at 50 Hz", lambda: instrument.excite(1.0, 50.0)),
        ("acquire at 20 Msamples/s", lambda: instrument.acquire(2e7, 513)),
        ("acquire 1e6 samples", lambda: instrument.acquire(320_000.0, 1_000_000)),
        (
            "tool: excite 230 V at 50 Hz",
            lambda: Allowlist((careless,)).dispatch(
                ToolCall("1", "excite", {"amplitude_v": 230.0, "frequency_hz": 50.0})
            ),
        ),
    ]
    # endregion: requests
    rows = []
    for request, operation in requests:
        before = len(log.device_calls())
        try:
            outcome = operation()
        except Refused as error:
            reason = str(error)
        else:
            reason = outcome.content["error"]
        rows.append((request, reason, len(log.device_calls()) - before))
    experiment.table(
        "refusals",
        rows,
        [
            ("request", "", ""),
            ("reason given", "", ""),
            ("calls reaching the adapter", "", "d"),
        ],
        "Five requests outside the envelope, the reason each was refused, and"
        " how many calls reached the adapter.",
    )
    experiment.number("refusals-reaching", sum(row[2] for row in rows), "d")

    # The stop: the output goes off, and every later operation is refused.
    measure_response(instrument, 5_000.0)
    instrument.request_stop("the reader pressed stop")
    after_stop = len(log.device_calls())
    try:
        measure_response(instrument, 5_000.0)
    except Refused as error:
        experiment.number("stop-reason", str(error))
    experiment.number("stop-reaching", len(log.device_calls()) - after_stop, "d")
    experiment.number("stop-last-call", log.calls[-1][0])
    snapshot = instrument.snapshot()
    experiment.table(
        "snapshot",
        [
            ("mode", snapshot["mode"]),
            ("device", snapshot["device"]["device"]),
            ("calibration", snapshot["device"]["calibration"]),
            (
                "output",
                "off" if snapshot["output"] is None else str(snapshot["output"]),
            ),
            ("halted", snapshot["halted"]),
            ("operations accepted", str(snapshot["operations"]["accepted"])),
            ("operations refused", str(snapshot["operations"]["refused"])),
        ],
        [("field", "", ""), ("value", "", "")],
        "The snapshot of the instrument after the refusals and the stop.",
    )


def conformance(experiment: Experiment) -> None:
    """The contract tests on the simulated and the recorded adapter, and on
    the forgetful one of the exercise."""
    setting = Setting(AMPLITUDE_V, 4_000.0, SAMPLES_PER_PERIOD * 4_000.0, 513)
    sample = recorded_sample()
    simulated = check_driver(lambda: SimulatedRLCBench(seed=SEED), setting)
    recorded = check_driver(lambda: RecordedBench(sample), setting)
    forgetful = check_driver(lambda: ForgetfulBench(seed=SEED), setting)
    experiment.table(
        "conformance",
        [
            (name, a.status, b.status)
            for (name, _), a, b in zip(CHECKS, simulated, recorded, strict=True)
        ],
        [("check", "", ""), ("simulated", "", ""), ("recorded", "", "")],
        "The contract tests on the simulated and the recorded adapter.",
    )
    experiment.number("checks", len(CHECKS), "d")
    experiment.table(
        "forgetful",
        [(f.check, f.status, f.detail) for f in forgetful if f.status != "passed"]
        + [(f.check, f.status, f.detail) for f in forgetful if f.check == "stop"],
        [("check", "", ""), ("status", "", ""), ("what it saw", "", "")],
        "The failed contract test of the forgetful adapter, and the stop check,"
        " which it passes.",
    )
    experiment.number("forgetful-passed", _passed(forgetful), "d")


def _passed(findings: list[Finding]) -> int:
    return sum(f.status == "passed" for f in findings)


def response_table(
    experiment: Experiment, name: str, rows: list[tuple[float, float, float]]
) -> None:
    experiment.table(
        name,
        [(f, g, closed_form(f)[0], p, closed_form(f)[1]) for f, g, p in rows],
        [
            ("frequency", "Hz", ".0f"),
            ("gain measured", "", ".4f"),
            ("gain, closed form", "", ".4f"),
            ("phase measured", "deg", ".2f"),
            ("phase, closed form", "deg", ".2f"),
        ],
        "The response measured through the instrument on the simulated adapter,"
        " against the closed form of the circuit; gains to four decimals, phases"
        " to a hundredth of a degree.",
    )


def deviations(rows: list[tuple[float, float, float]]) -> tuple[float, float]:
    """The largest relative deviation of the gain and the largest deviation
    of the phase (degrees) from the closed form."""
    gain = max(abs(g / closed_form(f)[0] - 1.0) for f, g, _ in rows)
    phase = max(abs(p - closed_form(f)[1]) for f, _, p in rows)
    return gain, phase


def draw_instrument_layers() -> Figure:
    """The layers between a measuring program and a device, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 4.2, (0.0, 12.8), (0.0, 8.4))
    diagrams.state_box(
        ax, (6.4, 7.5), "caller: a script, a tool,\nan agent", width=5.4, height=1.0,
        colour=0,
    )  # fmt: skip
    diagrams.state_box(
        ax,
        (6.4, 5.35),
        "Instrument\nenvelope, interlocks, timeout, stop\nsnapshot, run record",
        width=7.4,
        height=1.7,
        colour=1,
    )
    diagrams.state_box(
        ax, (6.4, 3.3), "Driver: identity, set_output,\noutput_off, capture",
        width=6.4, height=1.1, colour=0,
    )  # fmt: skip
    diagrams.arrow(ax, (6.4, 7.0), (6.4, 6.2), colour=1)
    diagrams.text(ax, (6.6, 6.6), "validated operations", ha="left")
    diagrams.arrow(ax, (6.4, 4.5), (6.4, 3.85), colour=1)
    diagrams.text(ax, (6.6, 4.17), "only within the envelope", ha="left")
    adapters = (
        (2.2, MODES[0], "a model of the bench", "-"),
        (6.4, MODES[1], "a declared sample", "-"),
        (10.6, MODES[2], "optional, not\ndemonstrated", "--"),
    )
    for x, mode, note, style in adapters:
        diagrams.state_box(ax, (x, 1.25), mode, width=2.8, height=0.8, colour=2)
        diagrams.arrow(ax, (6.4, 2.75), (x, 1.65), colour=0, linestyle=style)
        diagrams.text(ax, (x, 0.35), note, colour="#57606a")
    return fig


def draw_response(
    simulated: list[tuple[float, float, float]],
    recorded: list[tuple[float, float, float]],
) -> Figure:
    """Gain and phase measured through the instrument on two adapters, on
    the closed form of the circuit."""
    fine = np.linspace(1_500.0, 8_500.0, 400)
    model = np.array([closed_form(f) for f in fine])
    with figure_style():
        fig, (gain_ax, phase_ax) = plt.subplots(
            2, 1, figsize=figsize("stacked"), sharex=True
        )
        for ax, column in ((gain_ax, 0), (phase_ax, 1)):
            ax.plot(
                fine / 1e3, model[:, column], color=FIGURE_COLOURS[0],
                linewidth=LINE["model"], label="closed form",
            )  # fmt: skip
            ax.plot(
                [r[0] / 1e3 for r in simulated], [r[1 + column] for r in simulated],
                linestyle="none", marker="o", markersize=MARKER + 2.5,
                markerfacecolor="none", color=FIGURE_COLOURS[1],
                label="simulated adapter",
            )  # fmt: skip
            ax.plot(
                [r[0] / 1e3 for r in recorded], [r[1 + column] for r in recorded],
                linestyle="none", marker="x", markersize=MARKER + 1.0,
                color=FIGURE_COLOURS[2], label="recorded adapter",
            )  # fmt: skip
        gain_ax.set_ylabel("gain (V/V)")
        phase_ax.set_ylabel("phase (deg)")
        phase_ax.set_xlabel("frequency (kHz)")
        phase_ax.legend(loc="lower left", frameon=False)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-instrument-layers", draw_instrument_layers)

    # region: simulated
    instrument = Instrument(SimulatedRLCBench(seed=SEED), ENVELOPE)
    simulated = sweep(instrument)
    # endregion: simulated
    response_table(experiment, "simulated", simulated)
    gain, phase = deviations(simulated)
    experiment.number("gain-deviation", 100 * gain, ".2f")
    experiment.number("phase-deviation", phase, ".2f")
    experiment.number("points", len(FREQUENCIES_HZ), "d")
    experiment.number("noise", 1e3 * SimulatedRLCBench().noise_v, "g")
    experiment.number("settle", SimulatedRLCBench().settle_decays, "g")
    experiment.number("periods", PERIODS, "d")
    experiment.number("samples-per-period", SAMPLES_PER_PERIOD, "d")
    simulated_run = instrument.run_record(
        {"frequencies_hz": FREQUENCIES_HZ, "amplitude_v": AMPLITUDE_V},
        {"t": "s", "source": "V", "response": "V"},
        ("steady phasor of eight periods",),
        "", "",
    )  # fmt: skip

    # region: recorded
    replay = Instrument(RecordedBench(recorded_sample()), ENVELOPE)
    recorded = sweep(replay)
    # endregion: recorded
    experiment.number(
        "recorded-identical", "identical" if recorded == simulated else "different"
    )
    recorded_run = replay.run_record(
        {"frequencies_hz": FREQUENCIES_HZ, "amplitude_v": AMPLITUDE_V},
        {"t": "s", "source": "V", "response": "V"},
        ("steady phasor of eight periods",),
        "", "",
    )  # fmt: skip
    experiment.table(
        "run-records",
        [
            (r.mode, "yes" if r.new_experiment else "no", r.label, r.device["device"])
            for r in (simulated_run, recorded_run)
        ],
        [
            ("mode", "", ""),
            ("new experiment", "", ""),
            ("label", "", ""),
            ("device", "", ""),
        ],
        "The run records of the two sweeps.",
    )
    try:
        measure_response(replay, BETWEEN_HZ)
    except Refused as error:
        experiment.number("between-refusal", str(error))
    experiment.number("between", BETWEEN_HZ, ".0f")
    experiment.figure(
        "fig-response-through-the-contract", partial(draw_response, simulated, recorded)
    )

    refusals(experiment)
    conformance(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
