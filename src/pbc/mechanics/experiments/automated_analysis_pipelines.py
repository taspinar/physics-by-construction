"""The experiment of the lesson "Automated analysis pipelines".

Two pipelines (``pbc.data.pipeline``): a simulated throw swept over the
launch angle with its uncertainty (``pbc.mechanics.analysis``), and the
measured waves of the committed flume sample with their repetitions, window,
and three numerical runs (``pbc.data.flume_analysis``); each ends in a report
checked against its committed expectation. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.automated_analysis_pipelines out
"""

import json
import tempfile
from functools import partial
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.data import flume_analysis, flume_stages
from pbc.data.figure_provenance import REFERENCE, FigureProvenance, role
from pbc.data.pipeline import EXPECTED_DIR, check_report, differences
from pbc.data.uncertainty import propagate
from pbc.evidence import ContractError, claim_status
from pbc.evidence.resumable import Research
from pbc.experiment import Experiment, main
from pbc.mechanics import analysis
from pbc.mechanics.analysis import SPEED, SPEED_SIGMA
from pbc.mechanics.projectile import projectile_range

# The provenance the window sweep of the flume record declares (Issue #531):
# its status and credit at the caption and in its PNG, from the card.
WINDOW_SWEEP = FigureProvenance(
    status="processed",
    dataset="aalborg-submerged-bar",
    artifact="processed-measured",
    processing="The record's surface elevation at gauge 5 of wave condition 1, five"
    " aligned repetitions, unmodified; the RMS elevation in each window, its mean"
    " over the repetitions and their standard error: this lesson's code, not part"
    " of the record.",
)

# The provenance of the shifts of the alternative branches (F153): each is
# read from the state files of the resumable pipeline on the same record.
BRANCH_SHIFTS = FigureProvenance(
    status="processed",
    dataset="aalborg-submerged-bar",
    artifact="processed-measured",
    processing="The record's surface elevation at gauge 5 of wave condition 1, five"
    " aligned repetitions, unmodified; the mean RMS elevation in each branch's"
    " window and its shift from the main branch in standard errors, read from"
    " the states of the resumable pipeline: this lesson's code, not part of the"
    " record.",
)


def angle_sweep():
    """The range for each launch angle with its uncertainty; the sweep, the
    share lost to drag, and the relative uncertainty, in per cent."""
    scan = analysis.angle_sweep()
    loss = 100 * (1 - scan.results["range"] / scan.results["no_drag"])
    relative = 100 * scan.results["sigma"] / scan.results["range"]
    return scan, loss, relative


def fine_sweep():
    """The best angle on the fine grid around the maximum, in degrees."""
    fine = analysis.fine_sweep()
    best = fine.argmax("range")
    print(f"best angle on the fine grid: {best:.1f} degrees")
    return best


def draw_range_sweep(scan) -> Figure:
    """The range against the launch angle with its uncertainty band."""
    angles = scan.values
    range_fig, range_ax = plt.subplots(figsize=(6.4, 3.6))
    range_ax.plot(
        angles,
        scan.results["no_drag"],
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="without drag",
    )
    range_ax.fill_between(
        angles,
        scan.results["range"] - scan.results["sigma"],
        scan.results["range"] + scan.results["sigma"],
        color=FIGURE_COLOURS[0],
        alpha=0.3,
        label="one standard uncertainty",
    )
    range_ax.plot(
        angles,
        scan.results["range"],
        color=FIGURE_COLOURS[0],
        marker="o",
        label="with drag",
    )
    range_ax.set_xlabel("launch angle (deg)")
    range_ax.set_ylabel("range (m)")
    range_ax.legend()
    return range_fig


def monte_carlo_check(experiment: Experiment, best):
    """The propagated uncertainty of the range at the best angle against the
    spread of a seeded Monte Carlo run; record the table."""
    _, spread = analysis.monte_carlo(best)
    propagated = analysis.range_with_uncertainty(best)["sigma"]
    experiment.table(
        "monte-carlo-check",
        [(propagated, spread, 100 * (spread / propagated - 1))],
        columns=[
            ("propagated uncertainty", "m", ".2f"),
            ("Monte Carlo spread", "m", ".2f"),
            ("difference", "%", ".0f"),
        ],
        caption="The first-order uncertainty of the range at the best angle and "
        "the spread of a seeded Monte Carlo run, to two decimals.",
    )
    return propagated, spread


def projectile_report(experiment: Experiment):
    """The report of the simulated problem, checked against its committed
    expectation; record the table."""
    report = analysis.build_report()
    check_report(report, EXPECTED_DIR / "projectile-range.txt")
    experiment.table(
        "projectile-report",
        report.rows(),
        columns=[("quantity", "", "s"), ("as shown", "", "s")],
        caption="The report of the simulated problem, as the build wrote it and as "
        "it is committed.",
    )
    return report


def flume_report(experiment: Experiment):
    """The RMS elevation and period of each repetition of the measured waves
    in the window; record the table."""
    measured, models = flume_analysis.load()
    rms, period = flume_analysis.repetition_results(measured, flume_analysis.WINDOW)
    mean_rms = flume_analysis.estimate(rms)
    mean_period = flume_analysis.estimate(period)
    resolution = flume_analysis.period_resolution(
        mean_period.mean, flume_analysis.WINDOW
    )
    experiment.table(
        "flume-report",
        [(k + 1, 1e3 * r, p) for k, (r, p) in enumerate(zip(rms, period, strict=True))],
        columns=[
            ("repetition", "", "d"),
            ("RMS elevation", "mm", ".2f"),
            ("period", "s", ".2f"),
        ],
        caption="RMS elevation and dominant period of each repetition in the "
        "window, to two decimals.",
    )
    return measured, models, mean_rms, resolution


def window_sweep(measured):
    """The mean RMS elevation of the repetitions and its standard error for
    each end of the window, in mm."""
    window_scan = flume_analysis.window_sweep(measured)
    sigmas = [
        1e3
        * flume_analysis.estimate(
            flume_analysis.repetition_results(
                measured, (flume_analysis.WINDOW[0], end)
            )[0]
        ).sigma
        for end in window_scan.values
    ]
    return window_scan, sigmas


def draw_window_sweep(window_scan, sigmas) -> Figure:
    """The mean RMS elevation against the end of the window."""
    ends = window_scan.values
    window_fig, window_ax = plt.subplots(figsize=(6.4, 3.6))
    bars = window_ax.errorbar(
        ends,
        1e3 * window_scan.results["rms"],
        yerr=sigmas,
        color=FIGURE_COLOURS[0],
        marker="o",
        capsize=3,
        label="mean of five repetitions",
    )
    role(bars, "processed")
    window_ax.set_xlabel("end of the window (s)")
    window_ax.set_ylabel("RMS elevation (mm)")
    window_ax.legend()
    return window_fig


def window_table(experiment: Experiment, window_scan, sigmas) -> float:
    """Record the table of the window ends; return the spread of the mean
    RMS elevation over them, in m."""
    spread = float(window_scan.results["rms"].max() - window_scan.results["rms"].min())
    experiment.table(
        "window-sweep",
        [
            (end, 1e3 * rms_value, s)
            for end, rms_value, s in zip(
                window_scan.values, window_scan.results["rms"], sigmas, strict=True
            )
        ],
        columns=[
            ("end of the window", "s", ".0f"),
            ("RMS elevation", "mm", ".2f"),
            ("standard error", "mm", ".2f"),
        ],
        caption="The window end, the mean RMS elevation of the repetitions, and its "
        "standard error, to two decimals.",
    )
    return spread


def model_comparison(experiment: Experiment, models, mean_rms):
    """The three numerical runs in the same window against the measurement;
    record the table and return their relative differences, in per cent."""
    runs = flume_analysis.model_results(models)
    rows = [
        (
            name,
            1e3 * run_rms,
            1e3 * (run_rms - mean_rms.mean),
            flume_analysis.agreement(mean_rms, run_rms),
            run_period,
        )
        for name, (run_rms, run_period) in runs.items()
    ]
    rel_diff = [100 * abs(run_rms / mean_rms.mean - 1) for run_rms, _ in runs.values()]
    experiment.table(
        "model-comparison",
        rows,
        columns=[
            ("run", "", "s"),
            ("RMS elevation", "mm", ".2f"),
            ("minus measurement", "mm", ".2f"),
            ("in standard errors", "", ".1f"),
            ("period", "s", ".2f"),
        ],
        caption="The three numerical runs in the same window, their RMS elevation "
        "relative to the measurement, and their period, to two decimals.",
    )
    return rel_diff


def flume_expectation():
    """The report of the measured problem, checked against its committed
    expectation."""
    flume = flume_analysis.build_report()
    check_report(flume, EXPECTED_DIR / "flume-waves.txt")
    print(
        "lines that differ from the committed expectation:"
        f" {len(differences(flume, (EXPECTED_DIR / 'flume-waves.txt').read_text()))}"
    )


def halved_speed_uncertainty(best):
    """Exercise 1: the uncertainty of the range at the best angle with the
    speed uncertainty and with half of it."""

    def at_best(sigma):
        _, error = propagate(
            lambda v: analysis.throw_range(float(v), best), [SPEED], [sigma]
        )
        return float(error)

    full, halved = at_best(SPEED_SIGMA), at_best(SPEED_SIGMA / 2)
    print(
        f"uncertainty of the range: {full:.2f} m with the old speed uncertainty,"
        f" {halved:.2f} m with half of it, ratio {halved / full:.2f}"
    )


def euler_against_the_reference(best):
    """Exercise 2: the range at the best angle with explicit Euler and with
    the fourth-order stepper of the pipeline."""
    euler = projectile_range(SPEED, best, analysis.MASS, analysis.DRAG, analysis.DT)
    reference = analysis.throw_range(SPEED, best)
    print(
        f"explicit Euler: {euler:.2f} m; fourth-order stepper: {reference:.2f} m;"
        f" difference {euler - reference:+.2f} m"
    )


def resumable_run(experiment: Experiment, root: Path) -> Research:
    """The main branch stopped after its window and resumed, the alternative
    branches forked after the load, and both claims evaluated; record the
    lineage table."""
    research = flume_stages.investigation(root)
    research.run("main", stop_after="window")
    research.resume("main")
    flume_stages.branch_out(research)
    flume_stages.evaluate(research)
    experiment.table(
        "pipeline-lineage",
        research.rows(),
        columns=[
            ("attempt", "", "s"),
            ("follows", "", "s"),
            ("status", "", "s"),
            ("reason", "", "s"),
        ],
        caption="Every attempt of the investigation in the order it ran: the"
        " attempt it follows, its status, and the reason of a failure.",
    )
    return research


def _edit_state(root: Path, branch: str, stage: str) -> None:
    path = root / branch / f"{stage}.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["output"]["window"][1] += 0.5
    path.write_text(json.dumps(state), encoding="utf-8")


def _try_resume(research: Research, name: str) -> str:
    try:
        research.resume(name)
    except ContractError as refusal:
        return "refused: " + str(refusal).split(": ", 1)[1]
    return "resumed"


def resume_attempts(experiment: Experiment, root: Path) -> None:
    """Five attempts to resume the main branch after its window, each in a
    copy of its own: untouched, an edited state, other code, a changed
    window, and the branch whose window failed; record the table."""
    rows = []

    def stopped(name: str, code: str | None = None) -> Research:
        research = flume_stages.investigation(root / name, code)
        research.run("main", stop_after="window")
        return research

    rows.append(("untouched", _try_resume(stopped("untouched"), "main")))
    edited = stopped("edited")
    _edit_state(root / "edited", "main", "window")
    rows.append(("the window state edited", _try_resume(edited, "main")))
    other = stopped("other")
    later = flume_stages.investigation(root / "other", code="other code")
    later.ledger = other.ledger
    rows.append(("other code", _try_resume(later, "main")))
    changed = stopped("changed")
    main_branch = changed.branches["main"]
    changed.branches["main"] = type(main_branch)(
        "main", {**main_branch.configuration, "window": [5.0, 12.0]}
    )
    rows.append(("the window changed to end at 12 s", _try_resume(changed, "main")))
    failing = stopped("failing")
    failing.fork("main", "end-40", "load", {"window": [5.0, 40.0]})
    failing.run("end-40")
    rows.append(("the branch end-40", _try_resume(failing, "end-40")))
    experiment.table(
        "pipeline-resumes",
        rows,
        columns=[("state of the branch", "", "s"), ("outcome", "", "s")],
        caption="Five attempts to resume after the window stage, each in its own"
        " directory, and what the pipeline did.",
    )


def shared_window_refused(research: Research) -> None:
    """A fork that would share the window stage while changing the window."""
    try:
        research.fork("main", "end-11", "window", {"window": [5.0, 11.0]})
    except ContractError as refusal:
        print(f"refused: {refusal}")


def branch_table(experiment: Experiment, research: Research) -> dict[str, float]:
    """The result of every branch, read from its states; record the table
    and return the shifts of the alternatives in standard errors."""
    shifts = flume_stages.shifts(research)
    rows = []
    for name, branch in research.branches.items():
        end = branch.configuration["window"][1]
        attempt = research.ledger.attempt(f"{name}/estimate")
        if attempt is None:
            rows.append((name, end, "none", "none", "failed at window"))
            continue
        rms = research.state(attempt.id).output["rms"]
        shown = f"{1e3 * rms['mean']:.2f} +/- {1e3 * rms['sigma']:.2f}"
        shift = f"{shifts.get(name, 0.0):.1f}"
        rows.append((name, end, shown, shift, "completed"))
    experiment.table(
        "pipeline-branches",
        rows,
        columns=[
            ("branch", "", "s"),
            ("window end", "s", ".0f"),
            ("RMS elevation", "mm", "s"),
            ("shift from main, in standard errors", "", "s"),
            ("status", "", "s"),
        ],
        caption="The mean RMS elevation of each branch with its standard error,"
        " read from the branch's estimate state, and its shift from the main"
        " branch in standard errors of the main branch.",
    )
    return shifts


def claims_table(experiment: Experiment, research: Research) -> None:
    """The claims of the ledger with the status the evaluations give them;
    record the table."""
    experiment.table(
        "pipeline-claims",
        [
            (claim.text, ", ".join(claim.runs), claim_status(research.ledger, claim))
            for claim in research.ledger.claims
        ],
        columns=[("claim", "", "s"), ("runs", "", "s"), ("evidence status", "", "s")],
        caption="The two claims of the ledger, the attempts each rests on, and"
        " the evidence status the evaluations give it.",
    )


def draw_branch_shifts(shifts: dict[str, float], ends: dict[str, float]) -> Figure:
    """The shift of each alternative branch against the end of its window,
    with the band of the negative claim and the end of the record."""
    shift_fig, shift_ax = plt.subplots(figsize=(6.4, 3.6))
    band = shift_ax.axhspan(
        -flume_stages.WITHIN,
        flume_stages.WITHIN,
        color=FIGURE_COLOURS[1],
        alpha=0.3,
        label="within two standard errors of main",
    )
    role(band, REFERENCE)
    (main_point,) = shift_ax.plot(
        [ends["main"]],
        [0.0],
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="none",
        label="main branch",
    )
    role(main_point, "processed")
    names = sorted(shifts, key=ends.get)
    (alternatives,) = shift_ax.plot(
        [ends[n] for n in names],
        [shifts[n] for n in names],
        color=FIGURE_COLOURS[0],
        marker="s",
        markerfacecolor="none",
        linestyle="none",
        label="alternative branches",
    )
    role(alternatives, "processed")
    record_end = shift_ax.axvline(
        30.0, color=FIGURE_COLOURS[2], linestyle=":", label="end of the record"
    )
    role(record_end, REFERENCE)
    shift_ax.annotate(
        "end-40 failed:\nno estimate",
        xy=(30.0, max(shifts.values()) / 4),
        xytext=(31.0, max(shifts.values()) / 4),
    )
    shift_ax.set_xlabel("end of the window (s)")
    shift_ax.set_ylabel("shift of the RMS elevation (standard errors)")
    shift_ax.set_xlim(8.0, 42.0)
    shift_ax.legend(loc="upper right")
    return shift_fig


def edited_alternative(root: Path) -> None:
    """Exercise 3: resume end-12 after one value of its window state is
    edited."""
    research = flume_stages.investigation(root)
    research.run("main", stop_after="load")
    research.fork("main", "end-12", "load", {"window": [5.0, 12.0]})
    research.run("end-12", stop_after="window")
    _edit_state(root, "end-12", "window")
    print(_try_resume(research, "end-12"))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("speed", SPEED, ".0f")
    experiment.number("speed-sigma", SPEED_SIGMA, ".1f")

    scan, loss, relative = angle_sweep()
    experiment.number("loss-min", loss.min(), ".0f")
    experiment.number("loss-max", loss.max(), ".0f")
    experiment.number("relative-min", relative.min(), ".1f")
    experiment.number("relative-max", relative.max(), ".1f")
    experiment.number("coarse-best", scan.argmax("range"), ".0f")
    with experiment.capture("fine-sweep"):
        best = fine_sweep()
    experiment.number("best", best, ".1f")
    experiment.figure("fig-range-sweep", partial(draw_range_sweep, scan))

    propagated, spread = monte_carlo_check(experiment, best)
    experiment.number("samples", analysis.SAMPLES)
    experiment.number(
        "monte-carlo-difference", abs(100 * (spread / propagated - 1)), ".0f"
    )
    experiment.number(
        "spread-uncertainty", 100 / (2 * (analysis.SAMPLES - 1)) ** 0.5, ".0f"
    )
    report = projectile_report(experiment)
    experiment.number(
        "report-differences",
        len(differences(report, (EXPECTED_DIR / "projectile-range.txt").read_text())),
    )

    measured, models, mean_rms, resolution = flume_report(experiment)
    experiment.number("mean-rms", 1e3 * mean_rms.mean, ".2f")
    experiment.number("mean-rms-sigma", 1e3 * mean_rms.sigma, ".2f")
    experiment.number(
        "window-length", flume_analysis.WINDOW[1] - flume_analysis.WINDOW[0], ".0f"
    )
    experiment.number("resolution", resolution, ".2f")
    window_scan, sigmas = window_sweep(measured)
    experiment.figure(
        "fig-window-sweep",
        partial(draw_window_sweep, window_scan, sigmas),
        provenance=WINDOW_SWEEP,
    )
    spread = window_table(experiment, window_scan, sigmas)
    experiment.number(
        "window-spread-in-errors", 1e3 * spread / (1e3 * mean_rms.sigma), ".0f"
    )
    rel_diff = model_comparison(experiment, models, mean_rms)
    experiment.number("rel-diff-min", min(rel_diff), ".1f")
    experiment.number("rel-diff-max", max(rel_diff), ".1f")
    with experiment.capture("flume-expectation"):
        flume_expectation()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        research = resumable_run(experiment, root / "lesson")
        resume_attempts(experiment, root / "resumes")
        with experiment.capture("shared-window-refused"):
            shared_window_refused(research)
        shifts = branch_table(experiment, research)
        claims_table(experiment, research)
        counts = {s: 0 for s in ("completed", "failed")}
        for attempt in research.ledger.attempts:
            counts[attempt.status] += 1
        start, main_end = flume_stages.MAIN["window"]
        experiment.number("branch-start", start, ".0f")
        experiment.number("branch-main-end", main_end, ".0f")
        for name, end in flume_stages.ALTERNATIVES.items():
            experiment.number(f"branch-{name}", end, ".0f")
        span = research.state("main/load").output["span"]
        experiment.number("record-end", span[1], ".0f")
        experiment.number("attempts-completed", counts["completed"])
        experiment.number("attempts-failed", counts["failed"])
        ends = {n: b.configuration["window"][1] for n, b in research.branches.items()}
        experiment.figure(
            "fig-branch-shifts",
            partial(draw_branch_shifts, shifts, ends),
            provenance=BRANCH_SHIFTS,
        )
        experiment.number("shift-min", min(shifts.values()), ".0f")
        experiment.number("shift-max", max(shifts.values()), ".0f")
        with experiment.capture("edited-alternative"):
            edited_alternative(root / "exercise")

    with experiment.capture("halved-speed-uncertainty"):
        halved_speed_uncertainty(best)
    with experiment.capture("euler-against-the-reference"):
        euler_against_the_reference(best)
    return experiment


if __name__ == "__main__":
    main(run)
