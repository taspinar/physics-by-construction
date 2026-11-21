"""The experiment of the lesson "Running adaptive and resumable measurement
campaigns".

A campaign measures the resonance of the series RLC bench of SA3 through the
guarded instrument of ``pbc.instruments`` on its simulated adapter, point by
point by F138's frequency-response procedure (``pbc.electromagnetism.campaign``):
a sweep, local refinement by bisection, and repeats, every suggestion linked
to the measurements it follows from. The adaptive campaign is compared with
fixed sweeps of as many points. The campaign is then interrupted during a
measurement, cleaned up, recorded in the evaluator's ledger, and resumed
from its checkpoint; resumes from checkpoints that are not valid are
refused. No live hardware is used or shown. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.electromagnetism.experiments.measurement_campaigns out
"""

import copy
import shutil
import tempfile
from dataclasses import replace
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS, diagrams
from pbc.electromagnetism.campaign import (
    REFINE,
    REPEAT,
    RESUME_CHECKS,
    SWEEP,
    Measurement,
    Plan,
    ResumeRefused,
    Suggestion,
    SuggestionRefused,
    analyse,
    check_suggestion,
    evaluate,
    evaluate_segment,
    load_checkpoint,
    measure_point,
    new_ledger,
    reference,
    resume,
    run_segment,
    save_checkpoint,
)
from pbc.electromagnetism.circuits import SeriesRLC
from pbc.evidence.records import digest_files
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, MARKER, figsize, figure_style, finish
from pbc.instruments import Envelope, Instrument, Limit
from pbc.instruments.conformance import CallLog
from pbc.instruments.simulated import BENCH_CIRCUIT, SimulatedRLCBench

SEED = 143
PLAN = Plan()
# The bench's envelope: F138's.
ENVELOPE = Envelope(
    amplitude=Limit("excitation amplitude", "V", 0.01, 2.0),
    frequency=Limit("excitation frequency", "Hz", 100.0, 50_000.0),
    sample_rate=Limit("sample rate", "samples/s", 1_000.0, 5_000_000.0),
    samples=Limit("samples per acquisition", "samples", 16, 16_384, integer=True),
    timeout_s=10.0,
)
# The operator presses stop during this acquisition of the first segment.
STOP_AT = 12
# The numbers of measurements at which the adaptive campaign and the fixed
# sweep are compared.
COUNTS = (9, 11, 13, 15, 17)
COMPARE_AT = 15
SOURCE = Path(__file__).parents[1] / "campaign.py"


class OperatorStop(SimulatedRLCBench):
    """The simulated bench with an operator who presses stop while the
    ``stop_at``-th acquisition is running: the instrument's stop, from
    outside the campaign."""

    def __init__(self, stop_at: int, **options):
        super().__init__(**options)
        self.stop_at = stop_at
        self.acquisitions = 0
        self.press = None  # the instrument's request_stop, once it exists

    def capture(self, sample_rate_hz, samples):
        capture = super().capture(sample_rate_hz, samples)
        self.acquisitions += 1
        if self.acquisitions == self.stop_at and self.press is not None:
            self.press("operator interrupt")
        return capture


def code() -> str:
    """The digest of the campaign's source, for the ledger."""
    return digest_files([SOURCE], SOURCE.parent)


def full_campaign(directory: Path, plan: Plan = PLAN):
    """The campaign run once without interruption; its segment and ledger."""
    ledger = new_ledger(plan, (SEED,), code())
    instrument = Instrument(SimulatedRLCBench(seed=SEED), ENVELOPE)
    segment = run_segment(
        instrument, plan, ledger, directory, directory / "full.json", "full"
    )
    return segment, ledger


def interrupted_campaign(directory: Path):
    """The first segment, stopped by the operator during an acquisition."""
    ledger = new_ledger(PLAN, (SEED, SEED + 1), code())
    # region: interrupted
    bench = OperatorStop(STOP_AT, seed=SEED)
    instrument = Instrument(bench, ENVELOPE)
    bench.press = instrument.request_stop
    first = run_segment(
        instrument, PLAN, ledger, directory, directory / "checkpoint.json", "segment-1"
    )
    # endregion: interrupted
    return first, ledger


def resumed_campaign(directory: Path, ledger):
    """The second segment, on a new instrument, resumed from the checkpoint
    once ``resume`` has accepted it."""
    # region: resumed
    instrument = Instrument(SimulatedRLCBench(seed=SEED + 1), ENVELOPE)
    checkpoint, previous = resume(
        ledger, directory, directory / "checkpoint.json", PLAN, instrument
    )
    second = run_segment(
        instrument, PLAN, ledger, directory, directory / "checkpoint.json",
        "segment-2", resumed=checkpoint, prior=(previous,),
    )  # fmt: skip
    # endregion: resumed
    return second


def fixed_sweep(count: int) -> list[Measurement]:
    """``count`` log-spaced measurements over the plan's range, on a bench
    with the same seed."""
    instrument = Instrument(SimulatedRLCBench(seed=SEED), ENVELOPE)
    found = []
    for n, f in enumerate(np.geomspace(PLAN.low_hz, PLAN.high_hz, count), start=1):
        gain, phase = measure_point(instrument, PLAN, float(f))
        found.append(Measurement(f"s{n:02d}", float(f), gain, phase, SWEEP, ()))
    return found


def measurement_rows(measurements) -> list[tuple]:
    return [
        (m.id, m.frequency_hz, m.gain, m.phase_deg, m.stage, ", ".join(m.basis))
        for m in measurements
    ]


MEASUREMENT_COLUMNS = [
    ("id", "", ""),
    ("frequency", "Hz", ".1f"),
    ("gain", "V/V", ".4f"),
    ("phase", "deg", ".3f"),
    ("stage", "", ""),
    ("follows from", "", ""),
]


def draw_campaign_steps(measurements, f0_hz: float) -> Figure:
    """The frequency of each measurement against its order, by stage, with
    the resonance of the closed form as a reference line."""
    styles = {
        SWEEP: ("o", FIGURE_COLOURS[0], "sweep"),
        REFINE: ("s", FIGURE_COLOURS[1], "refinement"),
        REPEAT: ("^", FIGURE_COLOURS[2], "repeat"),
    }
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=1))
        ax.axhline(
            f0_hz / 1e3, color=FIGURE_COLOURS[3], linestyle=":",
            linewidth=LINE["guide"], label="f0 of the closed form",
        )  # fmt: skip
        for stage, (marker, colour, label) in styles.items():
            chosen = [(n, m) for n, m in enumerate(measurements, 1) if m.stage == stage]
            ax.plot(
                [n for n, _ in chosen], [m.frequency_hz / 1e3 for _, m in chosen],
                linestyle="none", marker=marker, markersize=MARKER + 1.5,
                color=colour, label=label,
            )  # fmt: skip
        ax.set_yscale("log")
        ax.set_xlabel("measurement number")
        ax.set_ylabel("frequency (kHz)")
        ax.legend(loc="lower right")
    return finish(fig)


def comparison(full) -> list[tuple[int, float, float]]:
    """The relative error of f0 against the closed form after ``n``
    measurements of the adaptive campaign and of a fixed sweep of ``n``."""
    rows = []
    for n in COUNTS:
        adaptive = evaluate(full.measurements[:n], BENCH_CIRCUIT)
        fixed = evaluate(fixed_sweep(n), BENCH_CIRCUIT)
        rows.append(
            (n, abs(adaptive["f0_relative_error"]), abs(fixed["f0_relative_error"]))
        )
    return rows


def draw_adaptive_against_sweep(rows) -> Figure:
    """The error of f0 against the number of measurements, log scale."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=1))
        counts = [r[0] for r in rows]
        ax.plot(
            counts, [r[2] for r in rows], marker="o", markersize=MARKER,
            color=FIGURE_COLOURS[0], linewidth=LINE["data"], label="fixed sweep",
        )  # fmt: skip
        ax.plot(
            counts, [r[1] for r in rows], marker="s", markersize=MARKER,
            color=FIGURE_COLOURS[1], linewidth=LINE["data"], linestyle="--",
            label="adaptive campaign",
        )  # fmt: skip
        ax.set_yscale("log")
        ax.set_xlabel("measurements")
        ax.set_ylabel("|relative error of f0|")
        ax.legend(loc="center right")
    return finish(fig, grid=True)


def draw_checkpoint_and_resume() -> Figure:
    """The interruption, the checkpoint, and the checks of a resume, as a
    sketch."""
    fig, ax = diagrams.canvas(6.4, 4.0, (0.0, 12.8), (0.0, 8.0))
    diagrams.state_box(
        ax,
        (2.4, 6.9),
        f"segment 1\nm01 ... m{STOP_AT - 1:02d}",
        width=3.6,
        height=1.2,
        colour=0,
    )
    diagrams.state_box(
        ax, (7.0, 6.9), f"m{STOP_AT:02d} in flight:\nstop, output off",
        width=3.8, height=1.2, colour=3,
    )  # fmt: skip
    diagrams.state_box(
        ax,
        (2.4, 4.2),
        f"checkpoint\nafter m{STOP_AT - 1:02d}",
        width=3.6,
        height=1.2,
        colour=1,
    )
    diagrams.state_box(
        ax, (7.4, 4.2), "ledger: segment 1,\ninconclusive, digest", width=4.4,
        height=1.2, colour=1,
    )  # fmt: skip
    diagrams.state_box(
        ax, (6.4, 1.3),
        "resume checks: " + ", ".join(RESUME_CHECKS)
        + f"\nthen segment 2 from m{STOP_AT:02d}",
        width=11.4, height=1.2, colour=2,
    )  # fmt: skip
    diagrams.arrow(ax, (4.2, 6.9), (5.1, 6.9), colour=0)
    diagrams.arrow(ax, (2.4, 6.3), (2.4, 4.8), colour=1)
    diagrams.text(ax, (2.6, 5.55), "after every\nmeasurement", ha="left")
    diagrams.arrow(ax, (4.2, 4.2), (5.2, 4.2), colour=1)
    diagrams.arrow(ax, (7.0, 6.3), (7.2, 4.8), colour=3, linestyle="--")
    diagrams.text(ax, (8.6, 5.55), "noted, not kept", ha="left", colour="#57606a")
    diagrams.arrow(ax, (2.4, 3.6), (3.4, 1.9), colour=2)
    diagrams.arrow(ax, (7.4, 3.6), (7.0, 1.9), colour=2)
    return fig


def refused_resumes(experiment: Experiment, directory: Path, first, ledger) -> None:
    """Five resumes that must be refused, each on a copy of the interrupted
    campaign, with a call log showing that nothing reached the bench."""
    rows = []

    def attempt(case, path, plan, circuit, prepared_ledger, root):
        log = CallLog(SimulatedRLCBench(circuit=circuit, seed=SEED + 1))
        instrument = Instrument(log, ENVELOPE)
        check = ""
        try:
            resume(prepared_ledger, root, path, plan, instrument)
            outcome = "accepted"
        except ResumeRefused as refusal:
            outcome = refusal.reason
            check = refusal.check
        rows.append((case, check, outcome, len(log.device_calls())))

    def copy_of(name):
        root = directory / name
        shutil.copytree(directory / "interrupted", root)
        return root, copy.deepcopy(ledger)

    root, cases = copy_of("older")
    older = root / "older.json"
    state = load_checkpoint(root / "checkpoint.json")
    save_checkpoint(older, replace(state, measurements=state.measurements[:9]))
    attempt("an older copy, after the sweep", older, PLAN, BENCH_CIRCUIT, cases, root)

    root, cases = copy_of("edited")
    edited = root / "checkpoint.json"
    state = load_checkpoint(edited)
    last = state.measurements[-1]
    changed = replace(last, phase_deg=last.phase_deg + 1.0)
    save_checkpoint(
        edited, replace(state, measurements=(*state.measurements[:-1], changed))
    )
    attempt("a phase edited by one degree", edited, PLAN, BENCH_CIRCUIT, cases, root)

    root, cases = copy_of("plan")
    narrower = replace(PLAN, target_width=PLAN.target_width / 2)
    attempt(
        "a narrower target in the plan", root / "checkpoint.json", narrower,
        BENCH_CIRCUIT, cases, root,
    )  # fmt: skip

    root, cases = copy_of("bench")
    other = SeriesRLC(120.0, BENCH_CIRCUIT.inductance, BENCH_CIRCUIT.capacitance)
    attempt(
        "another bench (R = 120 ohm)", root / "checkpoint.json", PLAN, other, cases,
        root,
    )  # fmt: skip

    root, cases = copy_of("finished")
    instrument = Instrument(SimulatedRLCBench(seed=SEED + 1), ENVELOPE)
    checkpoint, previous = resume(
        cases, root, root / "checkpoint.json", PLAN, instrument
    )
    run_segment(
        instrument, PLAN, cases, root, root / "checkpoint.json", "segment-2",
        resumed=checkpoint, prior=(previous,),
    )  # fmt: skip
    attempt(
        "the finished campaign, resumed again", root / "checkpoint.json", PLAN,
        BENCH_CIRCUIT, cases, root,
    )  # fmt: skip

    experiment.table(
        "refused-resumes",
        rows,
        [
            ("checkpoint", "", ""),
            ("check that failed", "", ""),
            ("reason", "", ""),
            ("calls that reached the bench", "", "d"),
        ],
        "Resumes from checkpoints that are not valid, each refused before the"
        " instrument was asked to do anything.",
    )


def lost_basis(first) -> None:
    """Exercise 1: a suggestion that follows from the measurement lost in
    flight, checked against the measurements of the checkpoint."""
    suggestion = Suggestion(5_190.0, REFINE, ("m11", "m12"), "a hand-made guess")
    try:
        check_suggestion(suggestion, first.measurements)
    except SuggestionRefused as refusal:
        print(refusal)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    ref = reference(BENCH_CIRCUIT)
    experiment.number("f0", ref["f0_hz"], ".1f")
    experiment.number("q", ref["q"], ".3f")
    experiment.number("sweep-points", PLAN.sweep_points, "d")
    experiment.number("low", PLAN.low_hz, ".0f")
    experiment.number("high", PLAN.high_hz, ".0f")
    experiment.number("target-width", 100 * PLAN.target_width, ".1f")
    experiment.number("repeats", PLAN.repeats, "d")
    experiment.number("plan-budget", PLAN.budget, "d")
    experiment.number("stop-at", STOP_AT, "d")
    experiment.number("compare-at", COMPARE_AT, "d")

    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        full, full_ledger = full_campaign(directory)
        evaluation = evaluate_segment(full_ledger, directory, "full", BENCH_CIRCUIT)
        analysis = analyse(full.measurements)
        experiment.table(
            "campaign-measurements",
            measurement_rows(full.measurements),
            MEASUREMENT_COLUMNS,
            "Every measurement of the uninterrupted campaign, in the order made,"
            " with the stage that asked for it and the measurements its"
            " suggestion followed from.",
        )
        experiment.number("measurements", len(full.measurements), "d")
        experiment.number("full-status", full.status)
        experiment.figure(
            "fig-campaign-steps",
            partial(draw_campaign_steps, full.measurements, ref["f0_hz"]),
        )
        experiment.table(
            "campaign-result",
            [
                ("f0 of the campaign", analysis.f0_hz, "Hz"),
                ("its standard error, from the repeats", analysis.f0_error_hz, "Hz"),
                ("f0 of the closed form", ref["f0_hz"], "Hz"),
                (
                    "relative error of f0",
                    evaluation.metrics["f0_relative_error"],
                    "",
                ),
                ("Q of the campaign", analysis.q, ""),
                ("Q of the closed form", ref["q"], ""),
                ("relative error of Q", evaluation.metrics["q_relative_error"], ""),
                ("final bracket, low end", analysis.bracket_hz[0], "Hz"),
                ("final bracket, high end", analysis.bracket_hz[1], "Hz"),
            ],
            [("quantity", "", ""), ("value", "", ".6g"), ("unit", "", "")],
            "The estimates of the uninterrupted campaign, recomputed by the"
            " evaluator from its checkpoint, against the closed form.",
        )

        rows = comparison(full)
        experiment.table(
            "adaptive-vs-sweep",
            [(n, a, s, s / a) for n, a, s in rows],
            [
                ("measurements", "", "d"),
                ("|error of f0|, adaptive", "", ".2e"),
                ("|error of f0|, fixed sweep", "", ".2e"),
                ("ratio", "", ".0f"),
            ],
            "The relative error of f0 after as many measurements of the adaptive"
            " campaign and of a fixed log-spaced sweep over the same range.",
        )
        at = next(r for r in rows if r[0] == COMPARE_AT)
        experiment.number("ratio-at", at[2] / at[1], ".0f")
        experiment.figure(
            "fig-adaptive-against-sweep", partial(draw_adaptive_against_sweep, rows)
        )

        experiment.figure("fig-checkpoint-and-resume", draw_checkpoint_and_resume)
        interrupted = directory / "interrupted"
        interrupted.mkdir()
        first, ledger = interrupted_campaign(interrupted)
        experiment.number("first-status", first.status)
        experiment.number("first-measurements", len(first.measurements), "d")
        experiment.number("lost-frequency", first.lost.frequency_hz, ".1f")
        experiment.number("first-output", "off" if first.output is None else "on")
        with experiment.capture("lost-basis"):
            lost_basis(first)
        refused_resumes(experiment, directory, first, ledger)

        second = resumed_campaign(interrupted, ledger)
        evaluate_segment(ledger, interrupted, "segment-2", BENCH_CIRCUIT)
        experiment.table(
            "ledger",
            [
                (
                    a.id,
                    a.status,
                    ", ".join(a.prior),
                    "; ".join(a.diagnostics),
                    "yes" if a.artifacts[0].sha256 else "no",
                )
                for a in ledger.attempts
            ],
            [
                ("segment", "", ""),
                ("status", "", ""),
                ("follows", "", ""),
                ("diagnostics", "", ""),
                ("checkpoint digest recorded", "", ""),
            ],
            "The evaluator's ledger of the interrupted campaign: one attempt per"
            " segment, the second following the first.",
        )
        resumed = analyse(second.measurements)
        same = sum(
            a.frequency_hz == b.frequency_hz
            for a, b in zip(full.measurements, second.measurements, strict=False)
        )
        kept = sum(
            a == b
            for a, b in zip(first.measurements, second.measurements, strict=False)
        )
        experiment.table(
            "resumed-vs-uninterrupted",
            [
                ("measurements", len(full.measurements), len(second.measurements)),
                ("taken from the checkpoint", 0, kept),
                ("at the same frequencies as uninterrupted", same, same),
                ("f0 (Hz)", analysis.f0_hz, resumed.f0_hz),
                (
                    "standard error of f0 (Hz)",
                    analysis.f0_error_hz,
                    resumed.f0_error_hz,
                ),
            ],
            [
                ("quantity", "", ""),
                ("uninterrupted", "", ".6g"),
                ("resumed", "", ".6g"),
            ],
            "The resumed campaign against the uninterrupted one. The measurements"
            " after the checkpoint are new: the bench's noise is drawn again.",
        )
        difference = abs(resumed.f0_hz - analysis.f0_hz)
        combined = float(np.hypot(resumed.f0_error_hz, analysis.f0_error_hz))
        experiment.number("f0-difference", difference, ".3f")
        experiment.number("f0-combined-error", combined, ".3f")

        more = replace(PLAN, repeats=10, budget=40)
        (directory / "ten").mkdir()
        ten, _ = full_campaign(directory / "ten", more)
        ten_analysis = analyse(ten.measurements)
        experiment.table(
            "more-repeats",
            [
                (
                    PLAN.repeats,
                    len(full.measurements),
                    analysis.f0_error_hz,
                    analysis.f0_hz - ref["f0_hz"],
                ),
                (
                    more.repeats,
                    len(ten.measurements),
                    ten_analysis.f0_error_hz,
                    ten_analysis.f0_hz - ref["f0_hz"],
                ),
            ],
            [
                ("repeats at each end", "", "d"),
                ("measurements", "", "d"),
                ("standard error of f0", "Hz", ".4f"),
                ("f0 minus the closed form", "Hz", ".4f"),
            ],
            "The campaign with three and with ten measurements at each end of the"
            " final bracket.",
        )
    return experiment


if __name__ == "__main__":
    main(run)
