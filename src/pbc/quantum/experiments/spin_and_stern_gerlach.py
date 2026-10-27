"""The experiment of the lesson "Spin and Stern-Gerlach measurements".

Silver atoms through a modelled Stern-Gerlach magnet
(``pbc.quantum.spin``): the pattern on the screen of a quantum spin against
a classical magnetic moment of the same atoms, the probabilities of a
measurement at an angle sampled atom by atom against the Born rule, and
magnets in a row. Every random draw takes a fixed seed. Run it as a program
to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.quantum.experiments.spin_and_stern_gerlach out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.spin import (
    ELECTRON_MOMENT,
    born_angle,
    deflection,
    direction,
    filters,
    probability,
    sample_outcomes,
    spin_state,
    standard_error,
)

# region: setup
# A modelled apparatus with given values, SI units: not a historical magnet.
GRADIENT = 1000.0  # T/m, the field gradient along z in the magnet
LENGTH = 0.035  # m, the length of the magnet
DRIFT = 0.10  # m, from the end of the magnet to the screen
SPEED = 550.0  # m/s, every atom (a velocity-selected beam)
BEAM = 3e-5  # m, the standard deviation of the beam's height at the magnet
SEED = 20261027
# endregion: setup

# region: screen
atoms = 20_000  # each with a spin in a random direction, as from an oven
# endregion: screen

# region: angles
angles_degrees = np.arange(0, 181, 15)  # the analyser from the prepared spin
per_angle = 1_000  # atoms at each angle
# endregion: angles

# region: sequence
sequence_atoms = 20_000
# The angle of each magnet's axis from z, in the x-z plane (degree).
sequences = {"z, z, z": [0, 0, 0], "z, x, z": [0, 90, 0]}
# endregion: sequence

MM = 1e3  # millimetres per metre, for the page


def random_directions(count: int, rng: np.random.Generator) -> np.ndarray:
    """The polar angles of ``count`` directions spread evenly over the sphere:
    cos(theta) uniform on [-1, 1]."""
    return np.arccos(rng.uniform(-1.0, 1.0, count))


def screen_run(experiment: Experiment):
    """The same atoms on the screen twice: as quantum spins, whose moment
    along z is +mu or -mu with the Born probabilities, and as classical
    magnets, whose moment along z is mu cos(theta); record the table."""
    rng = np.random.default_rng(SEED)
    theta = random_directions(atoms, rng)
    start = rng.normal(0.0, BEAM, atoms)
    spot = float(deflection(ELECTRON_MOMENT, GRADIENT, LENGTH, DRIFT, SPEED))

    # The electron's moment points against its spin: spin up goes down.
    up = rng.random(atoms) < born_angle(theta)
    quantum = start + np.where(up, -spot, spot)
    classical = start - spot * np.cos(theta)

    rows = []
    for name, z, centre in (
        ("quantum spin", quantum, 0.0),
        ("classical moment", classical, 0.5),
    ):
        upper = np.mean(z > 0)
        size = np.mean(np.abs(z))
        middle = np.mean(np.abs(z) < spot / 2)
        rows.append((name, upper, size * MM, middle, centre))
    se_fraction = float(standard_error(0.5, atoms))
    assert all(abs(row[1] - 0.5) < 4 * se_fraction for row in rows)
    assert abs(rows[0][2] / (spot * MM) - 1) < 4 * BEAM / spot / np.sqrt(atoms) + 1e-3
    # |cos(theta)| is uniform on [0, 1], with the standard deviation 1 / sqrt(12).
    assert abs(rows[1][2] / (spot * MM) - 0.5) < 4 / np.sqrt(12 * atoms) + 1e-3
    assert rows[0][3] == 0.0
    assert abs(rows[1][3] - 0.5) < 4 * se_fraction

    experiment.table(
        "screen",
        rows,
        [
            ("model of the atom", "", ""),
            ("fraction above the axis", "", ".4f"),
            ("mean distance from the axis", "mm", ".3f"),
            ("fraction within half a deflection of the axis", "", ".4f"),
            ("predicted", "", ".1f"),
        ],
        "The same sampled atoms on the screen as quantum spins and as classical "
        "moments: the fraction above the axis, the mean distance from it, and "
        "the fraction that lands closer to it than half the full deflection.",
    )
    return quantum, classical, spot


def draw_screen(quantum, classical, spot) -> Figure:
    """Histograms of the heights on the screen, quantum and classical."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    edges = np.linspace(-1.5 * spot, 1.5 * spot, 121) * MM
    ax.hist(
        classical * MM,
        bins=edges,
        density=True,
        histtype="stepfilled",
        color=FIGURE_COLOURS[2],
        alpha=0.35,
        label="classical moment, any direction",
    )
    ax.hist(
        quantum * MM,
        bins=edges,
        density=True,
        histtype="step",
        color=FIGURE_COLOURS[0],
        linewidth=1.5,
        label="quantum spin, two outcomes",
    )
    for sign in (-1, 1):
        ax.axvline(
            sign * spot * MM,
            color=FIGURE_COLOURS[1],
            linestyle=":",
            label="predicted deflection" if sign == 1 else None,
        )
    ax.set_xlabel("height on the screen (mm)")
    ax.set_ylabel("atoms per unit height (1/mm)")
    ax.legend(loc="upper center", fontsize="small")
    return fig


def angles_run(experiment: Experiment):
    """Atoms prepared with spin up along z, measured along a direction at
    each angle from z: the fraction +1 against cos^2(theta / 2); record the
    table."""
    rng = np.random.default_rng(SEED + 1)
    prepared = spin_state(0.0)
    theta = np.radians(angles_degrees)
    counts = np.array(
        [sample_outcomes(prepared, direction(t), per_angle, rng) for t in theta]
    )
    fractions = counts / per_angle
    born = np.array([probability(prepared, direction(t)) for t in theta])
    assert np.allclose(born, born_angle(theta), atol=1e-15)
    errors = standard_error(born, per_angle)
    shown = errors > 0
    deviations = np.zeros_like(fractions)
    deviations[shown] = (fractions[shown] - born[shown]) / errors[shown]
    assert np.all(fractions[~shown] == born[~shown].round())
    assert np.all(np.abs(deviations) < 3.5)

    experiment.table(
        "angles",
        list(zip(angles_degrees, fractions, born, errors, deviations, strict=True)),
        [
            ("angle of the analyser", "degree", "d"),
            ("fraction +1", "", ".3f"),
            ("Born probability", "", ".3f"),
            ("standard error", "", ".3f"),
            ("difference in standard errors", "", "+.2f"),
        ],
        "Atoms with spin up along z measured along a direction at an angle from "
        "z, a thousand at each angle: the fraction with the outcome +1, the "
        "Born probability, the standard error of a fraction of that many atoms, "
        "and the difference between the two in standard errors.",
    )
    return fractions, errors, np.max(np.abs(deviations))


def draw_angles(fractions, errors) -> Figure:
    """The sampled fractions with their standard errors on the Born curve."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    theta = np.linspace(0, 180, 181)
    ax.plot(
        theta,
        born_angle(np.radians(theta)),
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="Born rule cos^2(theta / 2)",
    )
    ax.errorbar(
        angles_degrees,
        fractions,
        yerr=errors,
        fmt="o",
        color=FIGURE_COLOURS[0],
        markerfacecolor="none",
        capsize=3,
        label="sampled atoms, one standard error",
    )
    ax.set_xticks(np.arange(0, 181, 30))
    ax.set_xlabel("angle theta of the analyser from the spin (degree)")
    ax.set_ylabel("fraction with the outcome +1")
    ax.legend(fontsize="small")
    return fig


def sequence_run(experiment: Experiment):
    """Unpolarised atoms through three magnets in a row, the beam of -1
    blocked after each: the fraction of the atoms reaching each magnet that
    pass it; record the table."""
    rng = np.random.default_rng(SEED + 2)
    rows = []
    for name, tilts in sequences.items():
        axes = [direction(np.radians(tilt)) for tilt in tilts]
        reached = np.zeros(3, dtype=int)
        passed = np.zeros(3, dtype=int)
        for theta in random_directions(sequence_atoms, rng):
            outcomes = filters(spin_state(theta), axes, rng)
            reached[: len(outcomes)] += 1
            passed[: len(outcomes)] += np.array(outcomes) == 1
        # The first magnet passes half of an unpolarised beam; each later one
        # measures the spin the one before it prepared.
        predicted = [0.5, *born_angle(np.radians(np.diff(tilts)))]
        for k in range(3):
            fraction = passed[k] / reached[k]
            rows.append((name, k + 1, reached[k], fraction, predicted[k]))
            if 0 < predicted[k] < 1:
                error = standard_error(predicted[k], reached[k])
                assert abs(fraction - predicted[k]) < 4 * error
            else:
                assert fraction == predicted[k]

    experiment.table(
        "sequence",
        rows,
        [
            ("magnets", "", ""),
            ("magnet", "", "d"),
            ("atoms reaching it", "", "d"),
            ("fraction passing (+1)", "", ".4f"),
            ("predicted", "", ".2f"),
        ],
        "Unpolarised atoms through three magnets in a row, along the axes named, "
        "the atoms with the outcome -1 blocked after each: how many reach each "
        "magnet and the fraction of them that pass it.",
    )
    return rows


def slow_beam():
    """Exercise 1: the deflection at half the speed and at the speed, per
    the deflection at the speed of the example."""
    base = deflection(ELECTRON_MOMENT, GRADIENT, LENGTH, DRIFT, SPEED)
    slow = deflection(ELECTRON_MOMENT, GRADIENT, LENGTH, DRIFT, SPEED / 2)
    return float(slow / base)


def mean_spin():
    """Exercise 2: the mean outcome along a direction at 60 degrees from the
    spin, from 4000 sampled atoms, against cos(theta)."""
    rng = np.random.default_rng(SEED + 3)
    count, theta = 4_000, np.radians(60)
    plus = sample_outcomes(spin_state(0.0), direction(theta), count, rng)
    mean = (2 * plus - count) / count
    error = 2 * standard_error(born_angle(theta), count)
    return mean, float(np.cos(theta)), float(error)


def how_many():
    """Exercise 3: the atoms needed for a standard error of 0.01 at 90
    degrees, and the spread of the fraction over 500 repeated runs of that
    many atoms."""
    rng = np.random.default_rng(SEED + 4)
    p = 0.5
    needed = round(p * (1 - p) / 0.01**2)
    fractions = rng.binomial(needed, p, 500) / needed
    return needed, float(np.sqrt(np.mean((fractions - p) ** 2)))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    quantum, classical, spot = screen_run(experiment)
    experiment.figure("fig-screen", partial(draw_screen, quantum, classical, spot))
    experiment.number("spot", spot * MM, ".3f")
    experiment.number("moment", ELECTRON_MOMENT, ".4e")

    fractions, errors, worst = angles_run(experiment)
    experiment.figure("fig-angles", partial(draw_angles, fractions, errors))
    experiment.number("worst-deviation", worst, ".1f")

    sequence_run(experiment)

    experiment.number("slow-ratio", slow_beam(), ".1f")
    mean, expected, error = mean_spin()
    experiment.number("mean-spin", mean, ".3f")
    experiment.number("mean-expected", expected, ".3f")
    experiment.number("mean-error", error, ".3f")
    needed, spread = how_many()
    experiment.number("needed", needed, "d")
    experiment.number("spread", spread, ".4f")
    return experiment


if __name__ == "__main__":
    main(run)
