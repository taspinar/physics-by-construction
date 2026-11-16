"""The experiment of the lesson "The wave equation".

A pulse on a string with fixed ends solved by the leapfrog scheme
(``pbc.waves.wave``) against its exact reflections, the convergence of the
scheme, and its stability limit. Run it as a program to write the figures
and numbers of the page:

    uv run --locked --no-dev python -m pbc.waves.experiments.wave_equation out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, TEXT, figsize, figure_style, finish
from pbc.waves.wave import (
    amplitude_growth,
    error_norm,
    grid,
    growth_factor,
    observed_order,
    reflected_pulse,
    solve,
    standing_mode,
    zigzag_run,
)

# region: setup
LENGTH = 1.0  # string length, m
SPEED = 100.0  # wave speed, m/s
# endregion: setup


def bump(s):
    return np.exp(-(((s - 0.3) / 0.05) ** 2))


# region: pulse
cells = 400
dx = LENGTH / cells
dt = 0.5 * dx / SPEED
x = grid(LENGTH, cells)
snapshot_times = [0.0, 0.004, 0.008, 0.012, 0.016]
steps = round(snapshot_times[-1] / dt)
# endregion: pulse
# region: convergence
cell_counts = np.array([50, 100, 200, 400, 800])
pulse_time = 0.012
mode_time = 0.0123
# endregion: convergence


def pulse_run():
    """The pulse released from rest and its reflections, against the exact
    solution at five times."""
    pulse = solve(
        bump(x), np.zeros_like(x), c=SPEED, dx=dx, dt=dt, n_steps=steps, every=1
    )
    pick = [int(np.argmin(np.abs(pulse.t - t))) for t in snapshot_times]
    exact = [
        reflected_pulse(bump, x, pulse.t[j], length=LENGTH, c=SPEED, ends="fixed")
        for j in pick
    ]
    worst = max(error_norm(pulse.u[j], e) for j, e in zip(pick, exact, strict=True))
    assert worst < 0.01, "the computed pulse leaves the exact one"
    return pulse, pick, exact, worst


def draw_pulse_reflections(pulse, pick, exact) -> Figure:
    """The pulse at five times, computed and exact, shifted for each time."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for row, (j, e) in enumerate(zip(pick, exact, strict=True)):
            offset = -1.2 * row
            ax.plot(x, pulse.u[j] + offset, color=FIGURE_COLOURS[0])
            ax.plot(
                x,
                e + offset,
                color=FIGURE_COLOURS[1],
                linestyle="--",
                linewidth=LINE["model"],
            )
            ax.text(
                1.02,
                offset,
                f"{pulse.t[j] * 1000:.0f} ms",
                va="center",
                fontsize=TEXT["note"],
            )
        ax.set_xlabel("position (m)")
        ax.set_ylabel("displacement, shifted\nfor each time\n(arbitrary units)")
        ax.set_yticks([])
        ax.set_xlim(0, 1.12)
    return finish(fig)


def final_error(n_cells, shape, reference, time):
    h = LENGTH / n_cells
    xs = grid(LENGTH, n_cells)
    n_steps = round(time / (0.5 * h / SPEED))
    result = solve(
        shape(xs),
        np.zeros_like(xs),
        c=SPEED,
        dx=h,
        dt=0.5 * h / SPEED,
        n_steps=n_steps,
        every=n_steps,
    )
    return error_norm(result.u[-1], reference(xs, result.t[-1]))


def pulse_reference(xs, t):
    return reflected_pulse(bump, xs, t, length=LENGTH, c=SPEED, ends="fixed")


def mode_shape(xs):
    return np.sin(3 * np.pi * xs / LENGTH)


def mode_reference(xs, t):
    return standing_mode(xs, t, length=LENGTH, n=3, c=SPEED)


def convergence(experiment: Experiment):
    """The error of the pulse and of the standing mode as the spacing is
    halved, and the fitted orders; record the table."""
    spacing = LENGTH / cell_counts
    pulse_errors = np.array(
        [final_error(n, bump, pulse_reference, pulse_time) for n in cell_counts]
    )
    mode_errors = np.array(
        [final_error(n, mode_shape, mode_reference, mode_time) for n in cell_counts]
    )
    # The coarsest grid of the pulse resolves its width badly, so the order is
    # fitted on the three finest grids.
    pulse_order = observed_order(spacing[-3:], pulse_errors[-3:])
    mode_order = observed_order(spacing, mode_errors)
    assert abs(pulse_order - 2.0) < 0.1 and abs(mode_order - 2.0) < 0.1

    experiment.table(
        "convergence",
        list(zip(cell_counts, spacing, pulse_errors, mode_errors, strict=True)),
        [
            ("cells", "", "d"),
            ("spacing", "m", ".5f"),
            ("error of the pulse", "", ".5f"),
            ("error of the mode", "", ".5f"),
        ],
        "The largest error of the displacement at a fixed time, for the pulse and "
        "for the standing mode, as the spacing is halved with the Courant number "
        "at one half.",
    )
    return spacing, pulse_errors, mode_errors, pulse_order, mode_order


def draw_convergence(spacing, pulse_errors, mode_errors) -> Figure:
    """The error against the spacing, with slopes one and two."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        ax.loglog(spacing, pulse_errors, "o-", color=FIGURE_COLOURS[0], label="pulse")
        ax.loglog(
            spacing, mode_errors, "s-", color=FIGURE_COLOURS[1], label="standing mode"
        )
        ax.loglog(
            spacing,
            mode_errors[-1] * (spacing / spacing[-1]) ** 2,
            color="gray",
            linewidth=LINE["guide"],
            label="slope two",
        )
        ax.loglog(
            spacing,
            mode_errors[-1] * (spacing / spacing[-1]),
            color="gray",
            linestyle=":",
            linewidth=LINE["guide"],
            label="slope one",
        )
        # The spacings as the ticks: the minor labels of the log axis ran
        # into each other at this width.
        ax.set_xticks(spacing, labels=[f"{value:.2g}" for value in spacing])
        ax.minorticks_off()
        ax.set_xlabel("grid spacing (m)")
        ax.set_ylabel("largest error of\nthe displacement")
        # Four entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


# region: courants
courants = [0.5, 0.9, 1.0, 1.02, 1.1, 1.5]
# endregion: courants


def cfl_run(experiment: Experiment):
    """A zigzag of the size of round-off at six Courant numbers: its largest
    value and, above the limit, its growth per step; record the table."""
    runs = {c: zigzag_run(c) for c in courants}
    rows = []
    for c in courants:
        result = runs[c]
        peak = np.max(np.abs(result.u))
        if c <= 1.0:
            rows.append((c, peak / 1e-10, None, 1.0))
        else:
            rows.append((c, peak / 1e-10, amplitude_growth(result), growth_factor(c)))
    for _, _, measured, predicted in rows:
        if measured is not None:
            assert abs(measured / predicted - 1.0) < 0.01
    assert all(row[1] < 1.5 for row in rows if row[0] <= 1.0)

    experiment.table(
        "cfl-run",
        rows,
        [
            ("Courant number", "", ".2f"),
            ("largest value over forty steps, in units of the start", "", ".3g"),
            ("measured growth per step", "", ".3f"),
            ("predicted growth per step", "", ".3f"),
        ],
        "The largest value of the field in forty steps from a zigzag of the size of "
        "round-off, and, above the limit, its measured and predicted growth per "
        "step.",
    )
    return runs, rows


def draw_cfl(runs) -> Figure:
    """The largest value of the zigzag against the step, for five Courant
    numbers."""
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=5))
        # The yellow of before (#c9a227, 2.4:1 against the plate) is the
        # next palette colour not used here (S3).
        for c, colour in zip(
            (0.9, 1.0, 1.02, 1.1, 1.5),
            (
                "#4a7ab5",
                FIGURE_COLOURS[0],
                FIGURE_COLOURS[3],
                "#d9622b",
                FIGURE_COLOURS[1],
            ),
            strict=True,
        ):
            size = np.max(np.abs(runs[c].u), axis=1) / 1e-10
            ax.semilogy(size, color=colour, label=f"C = {c}")
        ax.set_xlabel("step")
        ax.set_ylabel("largest value\n(units of the start)")
        # Five entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def free_ends():
    """Exercise 1: the pulse on a string with free ends; its largest error
    and the part that has returned."""
    free = solve(
        bump(x),
        np.zeros_like(x),
        c=SPEED,
        dx=dx,
        dt=dt,
        n_steps=steps,
        left="free",
        right="free",
        every=steps,
    )
    free_exact = reflected_pulse(
        bump, x, free.t[-1], length=LENGTH, c=SPEED, ends="free"
    )
    free_error = error_norm(free.u[-1], free_exact)
    returned = free.u[-1][x > 0.75]
    return free_error, returned


def at_the_limit():
    """Exercise 2: the standing mode at a Courant number of one."""
    n_cells = 100
    h = LENGTH / n_cells
    xs = grid(LENGTH, n_cells)
    at_limit = solve(
        mode_shape(xs),
        np.zeros_like(xs),
        c=SPEED,
        dx=h,
        dt=h / SPEED,
        n_steps=round(mode_time / (h / SPEED)),
        every=round(mode_time / (h / SPEED)),
    )
    return error_norm(at_limit.u[-1], mode_reference(xs, at_limit.t[-1]))


def growth_to_one():
    """Exercise 3: the growth per step at a Courant number of 1.05, and the
    steps that bring round-off to one."""
    factor = growth_factor(1.05)
    needed = np.log(1e10) / np.log(factor)
    return factor, needed


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    pulse, pick, exact, worst = pulse_run()
    experiment.figure(
        "fig-pulse-reflections", partial(draw_pulse_reflections, pulse, pick, exact)
    )
    experiment.number("worst", worst, ".4f")

    spacing, pulse_errors, mode_errors, pulse_order, mode_order = convergence(
        experiment
    )
    experiment.figure(
        "fig-convergence",
        partial(draw_convergence, spacing, pulse_errors, mode_errors),
    )
    experiment.number("pulse-order", pulse_order, ".2f")
    experiment.number("mode-order", mode_order, ".2f")

    runs, rows = cfl_run(experiment)
    experiment.figure("fig-cfl", partial(draw_cfl, runs))
    experiment.number("courant-3", courants[3])
    experiment.number("measured-3", rows[3][2], ".3f")
    experiment.number("predicted-3", rows[3][3], ".3f")
    experiment.number("courant-5", courants[5])
    experiment.number("measured-5", rows[5][2], ".2f")
    experiment.number("predicted-5", rows[5][3], ".2f")
    experiment.number("predicted-3-short", rows[3][3], ".2f")
    experiment.number("steps-to-one", np.log(1e10) / np.log(rows[3][3]), ".0f")

    free_error, returned = free_ends()
    experiment.number("free-error", free_error, ".4f")
    experiment.number("returned-max", returned.max(), ".2f")
    experiment.number("returned-min", returned.min(), ".2f")
    limit_error = at_the_limit()
    experiment.number(
        "limit-bound", max(1e-12, 10 ** np.ceil(np.log10(limit_error))), ".0e"
    )
    factor, needed = growth_to_one()
    experiment.number("factor", factor, ".3f")
    experiment.number("needed", needed, ".0f")
    return experiment


if __name__ == "__main__":
    main(run)
