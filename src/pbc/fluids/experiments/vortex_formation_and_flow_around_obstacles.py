"""The experiment of the lesson "Vortex formation and flow around obstacles".

The solver of ``pbc.fluids.navier_stokes`` with the flows of
``pbc.fluids.vortices``: a double shear layer that rolls up into vortices,
with its circulation, its energy budget, and its convergence under
refinement; and a circular cylinder in a stream, settling at a Reynolds number
of forty and shedding a vortex street at one hundred, whose Strouhal number
is compared with Roshko's measurements. The units are those of the box
(shear layer) and of the diameter and the free stream (cylinder). Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.fluids.experiments.vortex_formation_and_flow_around_obstacles out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.fluids.navier_stokes import (
    Grid,
    kinetic_energy,
    march,
    viscous_dissipation,
    vorticity,
)
from pbc.fluids.vortices import (
    ROSHKO_FIT,
    ROSHKO_STABLE,
    circulation,
    cylinder_wake,
    double_shear_layer,
    roshko_strouhal,
    shedding_frequency,
)
from pbc.verification.estimates import fitted_order

ROUND_OFF = 1e-12

# region: shear
STEEPNESS = 30.0  # the layers are about 1/30 of the box thick
PERTURBATION = 0.05  # m/s, the disturbance across the layers
SHEAR_NU = 1e-4  # m^2/s: a Reynolds number of ten thousand on the box
shear_cells = [64, 128, 256]
snapshots = [0.4, 0.8, 1.2]  # s
SHEAR_COURANT = 1.5
# endregion: shear

# region: wake
SHEDDING_RE = 100.0  # within Roshko's stable range
STEADY_RE = 40.0  # at its lower end, just below the onset in this model
CELLS_PER_DIAMETER = 10
WIDTH = 12.0  # diameters across the box: a blockage of 1/12
DURATION = 50.0  # in units of D / U
WINDOW = 20.0  # the last 20 D / U, where the frequency is measured
STEADY_DURATION = 60.0  # near the onset the oscillation decays slowly
# endregion: wake

NARROW_WIDTH = 8.0  # exercise 1: a blockage of 1/8


def shear_layer(n: int) -> dict:
    """The double shear layer on n by n cells up to each snapshot: the
    vorticity at the snapshots, the largest circulation at a snapshot, the
    fraction of the energy lost, and its relative mismatch with the
    dissipation integrated by the trapezoidal rule."""
    grid = Grid(n, n, 1.0, 1.0)
    u, v = double_shear_layer(grid, STEEPNESS, PERTURBATION)
    energy0 = kinetic_energy(u, v, grid)
    rates, times = [viscous_dissipation(u, v, grid, SHEAR_NU)], [0.0]
    shots, worst, now = [], 0.0, 0.0

    def observe(t, u, v):
        times.append(now + t)
        rates.append(viscous_dissipation(u, v, grid, SHEAR_NU))

    for target in snapshots:
        u, v, _ = march(
            u, v, grid, SHEAR_NU, target - now, courant=SHEAR_COURANT, observe=observe
        )
        now = target
        worst = max(worst, abs(circulation(u, v, grid)))
        shots.append(vorticity(u, v, grid))
    t, r = np.array(times), np.array(rates)
    dissipated = float(np.sum(0.5 * (r[1:] + r[:-1]) * np.diff(t)))
    lost = energy0 - kinetic_energy(u, v, grid)
    return {
        "shots": shots,
        "circulation": worst,
        "lost": lost / energy0,
        "mismatch": abs(lost - dissipated) / lost,
    }


def shear_layer_run(experiment: Experiment) -> dict:
    """The double shear layer on each grid; record the table and return the
    fields of the finest grid and the differences between grids."""
    fields, rows = {}, []
    for n in shear_cells:
        found = shear_layer(n)
        assert found["circulation"] < ROUND_OFF, "the circulation is not zero"
        fields[n] = found["shots"]
        rows.append([n, f"below {ROUND_OFF:.0e}", found["lost"], found["mismatch"]])
    # The corners of a grid are every second corner of the next finer grid.
    differences = [
        float(np.max(np.abs(fields[n][-1] - fields[2 * n][-1][::2, ::2])))
        for n in shear_cells[:-1]
    ]
    for row, d in zip(rows, [*differences, None], strict=False):
        row.append(d)
    experiment.table(
        "shear-layer-run",
        rows,
        [
            ("cells per side", "", "d"),
            ("largest circulation", "m²/s", ""),
            ("energy lost", "fraction", ".4f"),
            ("budget mismatch", "relative", ".1e"),
            ("vorticity change to the next grid", "1/s", ".2f"),
        ],
        "The double shear layer up to the last snapshot on each grid: the "
        "largest circulation around the box at a snapshot, the fraction of "
        "the energy lost, the relative difference between the energy lost and "
        "the integrated dissipation, and the largest difference of the "
        "vorticity at the last snapshot from the next finer grid at the same "
        "points.",
    )
    return {"fields": fields[shear_cells[-1]], "differences": differences}


def draw_shear_layer(found: dict) -> Figure:
    """The vorticity of the finest grid at the three snapshots, false colour
    centred on zero, one scale for all."""
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.9), sharey=True)
    limit = max(float(np.max(np.abs(w))) for w in found["fields"])
    for ax, w, t in zip(axes, found["fields"], snapshots, strict=False):
        image = ax.imshow(
            w, origin="lower", extent=(0, 1, 0, 1), cmap="PuOr", vmin=-limit, vmax=limit
        )
        ax.set_title(f"t = {t:.1f} s", fontsize="medium")
        ax.set_xlabel("x (m)")
    axes[0].set_ylabel("y (m)")
    fig.colorbar(
        image,
        ax=axes,
        label="vorticity (1/s)\n(false colour, zero at the centre)",
        shrink=0.85,
    )
    return fig


def wake_run(experiment: Experiment) -> dict:
    """The cylinder at the two Reynolds numbers: the shedding frequency and
    Strouhal number at one hundred, and the amplitude of the probe signal
    early and late at both; record the table and return the wakes."""
    shedding = cylinder_wake(SHEDDING_RE, CELLS_PER_DIAMETER, WIDTH, duration=DURATION)
    steady = cylinder_wake(
        STEADY_RE, CELLS_PER_DIAMETER, WIDTH, duration=STEADY_DURATION
    )
    late = shedding.t > DURATION - WINDOW
    frequency, crossings = shedding_frequency(shedding.t[late], shedding.probe[late])
    periods = np.diff(crossings)
    assert np.ptp(periods) < 0.01 * periods.mean(), "the shedding is not periodic"

    def amplitude(wake, start, end):
        window = (wake.t > start) & (wake.t <= end)
        return float(np.ptp(wake.probe[window]))

    middle = DURATION - WINDOW / 2
    early_s = amplitude(shedding, DURATION - WINDOW, middle)
    late_s = amplitude(shedding, middle, DURATION)
    early_q = amplitude(steady, STEADY_DURATION / 3, 2 * STEADY_DURATION / 3)
    late_q = amplitude(steady, 2 * STEADY_DURATION / 3, STEADY_DURATION)
    assert late_q < 0.5 * early_q, "the wake at forty does not settle"
    assert abs(late_s - early_s) < 0.05 * late_s, "the shedding has not saturated"
    reference = roshko_strouhal(SHEDDING_RE)
    span = (
        roshko_strouhal(ROSHKO_FIT[0] + 1e-9),
        roshko_strouhal(ROSHKO_FIT[1] - 1e-9),
    )
    assert span[0] < frequency < span[1], "outside the span of Roshko's fit"
    experiment.table(
        "wake-run",
        [
            (SHEDDING_RE, early_s, late_s, frequency, reference),
            (STEADY_RE, early_q, late_q, None, None),
        ],
        [
            ("Reynolds number", "", ".0f"),
            ("probe swing, earlier", "U", ".4f"),
            ("probe swing, later", "U", ".4f"),
            ("Strouhal number, computed", "", ".4f"),
            ("Strouhal number, Roshko's fit", "", ".4f"),
        ],
        "The cylinder at two Reynolds numbers, ten cells per diameter, box "
        "twelve diameters wide: the peak-to-peak swing of the cross-stream "
        "velocity two diameters behind the cylinder in the two halves of the "
        "last window of each run (for the steady case, the second and the "
        "last third of the run), and the Strouhal number of the shedding from "
        "the last window, with the value of Roshko's fit to his measurements.",
    )
    experiment.number("strouhal", frequency, ".3f")
    experiment.number("roshko", reference, ".3f")
    experiment.number("strouhal-excess", 100 * (frequency / reference - 1), ".0f")
    experiment.number("periods", len(periods), "d")
    experiment.number("stable-low", ROSHKO_STABLE[0], ".0f")
    experiment.number("stable-high", ROSHKO_STABLE[1], ".0f")
    experiment.number("range-low", span[0], ".3f")
    experiment.number("range-high", span[1], ".3f")
    experiment.number("steady-decay", early_q / late_q, ".1f")
    experiment.number("shedding-re", SHEDDING_RE, ".0f")
    experiment.number("steady-re", STEADY_RE, ".0f")
    experiment.number("cells-per-diameter", CELLS_PER_DIAMETER, "d")
    experiment.number("blockage", 1 / WIDTH, ".3f")
    return {"shedding": shedding, "steady": steady}


def draw_karman_street(wake) -> Figure:
    """The vorticity of the wake at the end of the run, false colour centred
    on zero, with the cylinder drawn and the fringe left out."""
    grid = wake.grid
    w = vorticity(wake.u, wake.v, grid)
    keep = round((grid.lx - 3.0) / grid.dx)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    limit = 3.0
    image = ax.imshow(
        w[:, :keep],
        origin="lower",
        cmap="PuOr",
        vmin=-limit,
        vmax=limit,
        extent=(0, keep * grid.dx, 0, grid.ly),
    )
    ax.add_patch(
        Circle(
            wake.cylinder.centre,
            wake.cylinder.diameter / 2,
            facecolor="white",
            edgecolor=FIGURE_COLOURS[2],
        )
    )
    ax.set_ylim(grid.ly / 2 - 4, grid.ly / 2 + 4)
    ax.set_xlabel("x (diameters)")
    ax.set_ylabel("y (diameters)")
    ax.set_aspect("equal")
    bar = fig.colorbar(image, ax=ax, shrink=0.8, extend="both")
    bar.set_label("vorticity (U/D)\n(false colour, zero at the centre)")
    fig.tight_layout()
    return fig


def draw_wake_signal(wakes: dict) -> Figure:
    """The cross-stream velocity at the probe against time, at both
    Reynolds numbers."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    shedding, steady = wakes["shedding"], wakes["steady"]
    ax.plot(
        shedding.t,
        shedding.probe,
        color=FIGURE_COLOURS[0],
        label=f"Re = {SHEDDING_RE:.0f}",
    )
    ax.plot(
        steady.t,
        steady.probe,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label=f"Re = {STEADY_RE:.0f}",
    )
    ax.axvspan(
        DURATION - WINDOW,
        DURATION,
        color=FIGURE_COLOURS[2],
        alpha=0.12,
        label="window of the frequency",
    )
    ax.set_xlabel("time (D/U)")
    ax.set_ylabel("cross-stream velocity (U)")
    ax.legend(frameon=False, loc="lower left", fontsize="small")
    fig.tight_layout()
    return fig


def blockage_run(experiment: Experiment) -> None:
    """Exercise 1: the same shedding in a box eight diameters wide."""
    narrow = cylinder_wake(
        SHEDDING_RE, CELLS_PER_DIAMETER, NARROW_WIDTH, duration=DURATION
    )
    late = narrow.t > DURATION - WINDOW
    frequency, _ = shedding_frequency(narrow.t[late], narrow.probe[late])
    experiment.number("narrow-strouhal", frequency, ".3f")
    experiment.number("narrow-blockage", 1 / NARROW_WIDTH, ".3f")


# region: wire
WIRE_DIAMETER = 1e-3  # m
WIND = 1.5  # m/s
AIR_NU = 1.5e-5  # m^2/s
# endregion: wire


def wire_tone(experiment: Experiment, computed: float) -> None:
    """Exercise 2: the tone a thin wire sings in a light wind."""
    reynolds = WIND * WIRE_DIAMETER / AIR_NU
    experiment.number("wire-re", reynolds, ".0f")
    experiment.number(
        "wire-roshko", roshko_strouhal(reynolds) * WIND / WIRE_DIAMETER, ".0f"
    )
    experiment.number("wire-computed", computed * WIND / WIRE_DIAMETER, ".0f")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    shear = shear_layer_run(experiment)
    experiment.number(
        "shear-order",
        fitted_order(1.0 / np.array(shear_cells[:-1]), shear["differences"]),
        ".1f",
    )
    experiment.number("round-off", ROUND_OFF, ".0e")
    experiment.figure("fig-shear-layer", partial(draw_shear_layer, shear))

    wakes = wake_run(experiment)
    experiment.figure(
        "fig-karman-street", partial(draw_karman_street, wakes["shedding"])
    )
    experiment.figure("fig-wake-signal", partial(draw_wake_signal, wakes))

    blockage_run(experiment)
    wire_tone(experiment, float(experiment["strouhal"]))
    return experiment


if __name__ == "__main__":
    main(run)
