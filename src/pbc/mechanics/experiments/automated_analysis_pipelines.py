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

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.data import flume_analysis
from pbc.data.figure_provenance import FigureProvenance, role
from pbc.data.pipeline import EXPECTED_DIR, check_report, differences
from pbc.data.uncertainty import propagate
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

    with experiment.capture("halved-speed-uncertainty"):
        halved_speed_uncertainty(best)
    with experiment.capture("euler-against-the-reference"):
        euler_against_the_reference(best)
    return experiment


if __name__ == "__main__":
    main(run)
