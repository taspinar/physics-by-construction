"""The experiment of the lesson "The quantum harmonic oscillator".

The lowest eigenstates of the finite-difference Hamiltonian of the
oscillator (``pbc.quantum.eigenstates``) against the exact spectrum
(n + 1/2) hbar omega and the Hermite functions: the levels, their
convergence at order two with the predicted coefficient, and the walls that
are too close. Run it as a program to write the figures and numbers of the
page:

    uv run --locked --no-dev \\
        python -m pbc.quantum.experiments.quantum_harmonic_oscillator out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.eigenstates import (
    box_energy,
    eigenstates,
    hermite_functions,
    oscillator_energy,
    oscillator_potential,
    oscillator_shift,
    quartic_moment,
)
from pbc.quantum.schrodinger import grid_energy, line
from pbc.verification.estimates import fitted_order

# region: setup
# Units: hbar = m = omega = 1, so V = x^2 / 2 and E_n = n + 1/2.
HALF = 8.0  # the walls stand at -8 and +8
COUNT = 6  # the levels computed, n = 0 to 5
# endregion: setup

# region: levels
cells = 320  # h = 0.05
# endregion: levels

# region: convergence
cell_counts = [40, 80, 160, 320, 640]  # h from 0.4 to 0.025
shown = [0, 2, 5]
# endregion: convergence

# region: walls
halves = [2.0, 3.0, 4.0, 5.0, 6.0]
wall_spacing = 0.02
# endregion: walls


def below(value: float, bound: float) -> str:
    """A gap set by round-off is not shown as a number: only that it is
    smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def levels_run(experiment: Experiment):
    """The six lowest levels on the grid against n + 1/2 and the predicted
    shift, and the largest gap to the Hermite functions; record the table."""
    grid = line(-HALF, HALF, cells)
    energies, vectors = eigenstates(oscillator_potential(grid.x), grid.h, COUNT)
    n = np.arange(COUNT)
    exact = oscillator_energy(n)
    predicted = oscillator_shift(n, grid.h)
    reference = hermite_functions(COUNT, grid.x)
    gaps = np.max(np.abs(vectors.T - reference), axis=1)
    assert np.all(np.abs((energies - exact) / predicted - 1) < 1e-3)
    assert np.all(gaps < 2e-3)

    experiment.table(
        "levels",
        list(zip(n, energies, exact, energies - exact, predicted, gaps, strict=True)),
        [
            ("n", "", "d"),
            ("energy on the grid", "", ".6f"),
            ("exact level", "", ".1f"),
            ("error", "", ".3e"),
            ("predicted error", "", ".3e"),
            ("largest gap to the Hermite function", "", ".1e"),
        ],
        "The six lowest levels of the oscillator on the grid of the example, in "
        "units of hbar omega, against the exact levels, the predicted error of "
        "each, and the largest gap of its eigenfunction to the Hermite function.",
    )
    return grid, energies, vectors, reference


def draw_levels(grid, energies, vectors, reference) -> Figure:
    """The potential, the levels, and the eigenfunctions drawn at the height
    of their level, computed and exact."""
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    x = grid.x
    ax.plot(
        x,
        oscillator_potential(x),
        color=FIGURE_COLOURS[2],
        linewidth=1.5,
        label="potential x^2 / 2",
    )
    for j, energy in enumerate(energies):
        turning = np.sqrt(2 * energy)
        ax.hlines(
            energy,
            -turning,
            turning,
            color=FIGURE_COLOURS[2],
            linestyle=":",
            linewidth=1,
        )
        ax.plot(
            x,
            energy + 0.4 * vectors[:, j],
            color=FIGURE_COLOURS[0],
            label="grid eigenfunction" if j == 0 else None,
        )
        ax.plot(
            x,
            energy + 0.4 * reference[j],
            color=FIGURE_COLOURS[1],
            linestyle="--",
            linewidth=1,
            label="Hermite function" if j == 0 else None,
        )
        ax.text(4.0, energy + 0.08, f"n = {j}", va="bottom")
    ax.set_xlim(-5, 5)
    ax.set_ylim(0, 7.2)
    ax.set_xlabel("position x (units of sqrt(hbar / m omega))")
    ax.set_ylabel("energy (units of hbar omega)")
    ax.legend(loc="upper center", ncol=3, fontsize="small")
    return fig


def convergence(experiment: Experiment):
    """The error of three levels as h is halved, and its ratio to the
    predicted error; record the table."""
    spacings, errors = [], []
    for n_cells in cell_counts:
        grid = line(-HALF, HALF, n_cells)
        energies, _ = eigenstates(oscillator_potential(grid.x), grid.h, COUNT)
        spacings.append(grid.h)
        errors.append(energies - oscillator_energy(np.arange(COUNT)))
    errors = np.array(errors)
    orders = [fitted_order(spacings, np.abs(errors[:, n])) for n in shown]
    ratios = errors / np.array(
        [oscillator_shift(np.arange(COUNT), h) for h in spacings]
    )
    assert all(abs(p - 2) < 0.05 for p in orders)
    assert np.all(np.abs(ratios[-1] - 1) < 1e-3)

    experiment.table(
        "convergence",
        [
            (h, *(errors[i, n] for n in shown), ratios[i, shown[-1]])
            for i, h in enumerate(spacings)
        ],
        [
            ("spacing h", "", ".3f"),
            *((f"error of level {n}", "", ".3e") for n in shown),
            (f"error of level {shown[-1]} / predicted", "", ".4f"),
        ],
        "The error of three levels as the spacing is halved, and the ratio of the "
        "error of the highest of them to its predicted error.",
    )
    return np.array(spacings), errors, orders


def draw_convergence(spacings, errors) -> Figure:
    """The size of the error of three levels against h, log-log, with the
    predicted error."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    markers = ["o", "s", "^"]
    h = np.geomspace(spacings[-1], spacings[0], 50)
    for colour, marker, n in zip(FIGURE_COLOURS, markers, shown, strict=False):
        ax.loglog(
            spacings,
            np.abs(errors[:, n]),
            marker,
            color=colour,
            markerfacecolor="none",
            label=f"level {n}, grid",
        )
        ax.loglog(
            h,
            np.abs(oscillator_shift(n, h)),
            color=colour,
            linestyle="--",
            linewidth=1,
            label=f"level {n}, predicted",
        )
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(spacings, [f"{v:g}" for v in spacings])
    ax.set_xlabel("spacing h (units of sqrt(hbar / m omega))")
    ax.set_ylabel("size of the error (units of hbar omega)")
    ax.legend(fontsize="small", ncol=2)
    return fig


def walls_run(experiment: Experiment):
    """The error of four levels as the walls move in; record the table."""
    rows = []
    for half in halves:
        grid = line(-half, half, round(2 * half / wall_spacing))
        energies, _ = eigenstates(oscillator_potential(grid.x), grid.h, 4)
        rows.append((half, *(energies - oscillator_energy(np.arange(4)))))
    grid_error = oscillator_shift(np.arange(4), wall_spacing)
    assert np.all(np.abs(np.array(rows[-1][1:]) / grid_error - 1) < 1e-2)

    experiment.table(
        "walls",
        rows,
        [
            ("half-width of the box", "", ".1f"),
            *((f"error of level {n}", "", ".2e") for n in range(4)),
        ],
        "The error of the four lowest levels with the walls at plus and minus the "
        "half-width, on a fine grid of fixed spacing.",
    )
    return rows, grid_error


def square_well():
    """Exercise 1: an empty box of length 2; its four lowest levels against
    the grid's energy of the sine modes and the exact well."""
    length = 2.0
    grid = line(0.0, length, 200)
    energies, _ = eigenstates(np.zeros_like(grid.x), grid.h, 4)
    n = np.arange(1, 5)
    return (
        energies,
        grid_energy(n * np.pi / length, grid.h),
        box_energy(n, length),
    )


def quartic():
    """Exercise 2: the shift of three levels by 0.001 x^4, per unit strength,
    against <x^4>_n."""
    strength = 1e-3
    grid = line(-HALF, HALF, 640)
    base, _ = eigenstates(oscillator_potential(grid.x), grid.h, 3)
    shifted, _ = eigenstates(
        oscillator_potential(grid.x) + strength * grid.x**4, grid.h, 3
    )
    return (shifted - base) / strength, quartic_moment(np.arange(3))


def richardson():
    """Exercise 3: level 5 at h = 0.1 and 0.05, and the combination
    (4 E(h/2) - E(h)) / 3."""
    values = []
    for n_cells in (160, 320):
        grid = line(-HALF, HALF, n_cells)
        values.append(eigenstates(oscillator_potential(grid.x), grid.h, COUNT)[0][5])
    combined = (4 * values[1] - values[0]) / 3
    return values, combined


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    grid, energies, vectors, reference = levels_run(experiment)
    experiment.figure(
        "fig-levels", partial(draw_levels, grid, energies, vectors, reference)
    )
    experiment.number("ground", energies[0], ".6f")
    experiment.number("spacing-gap", np.max(np.abs(np.diff(energies) - 1)), ".4f")

    spacings, errors, orders = convergence(experiment)
    experiment.figure("fig-convergence", partial(draw_convergence, spacings, errors))
    for n, order in zip(shown, orders, strict=True):
        experiment.number(f"order-{n}", order, ".2f")

    _, grid_error = walls_run(experiment)
    experiment.number("grid-error-3", grid_error[3], ".2e")

    box, discrete, exact = square_well()
    experiment.number("well-gap", below(np.max(np.abs(box / discrete - 1)), 1e-10))
    experiment.number("well-exact-gap", np.max(np.abs(box / exact - 1)) * 100, ".2f")
    shifts, moments = quartic()
    for n in range(3):
        experiment.number(f"quartic-{n}", shifts[n], ".3f")
        experiment.number(f"moment-{n}", moments[n], ".3f")
    values, combined = richardson()
    experiment.number("richardson-coarse", values[0] - 5.5, ".2e")
    experiment.number("richardson-fine", values[1] - 5.5, ".2e")
    experiment.number("richardson-combined", combined - 5.5, ".1e")
    return experiment


if __name__ == "__main__":
    main(run)
