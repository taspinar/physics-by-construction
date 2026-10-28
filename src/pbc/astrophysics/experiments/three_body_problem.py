"""The experiment of the lesson "The three-body problem".

Three bodies under their mutual gravity (``pbc.astrophysics.three_body``,
on the N-body code of ``pbc.mechanics.nbody``): Lagrange's triangle against
its exact rigid rotation, the growth of a small disturbance of it against
Routh's linear-stability prediction, and Burrau's Pythagorean problem, with
its conserved quantities, two tolerances, and nearby starts. Run it as a
program to write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.three_body_problem out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.astrophysics.three_body import (
    adaptive,
    escaper,
    lagrange_growth_rate,
    lagrange_libration,
    lagrange_triangle,
    pythagorean_start,
    rigid_rotation,
    routh_beta,
    shape_departure,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.nbody import angular_momentum, gravity, total_energy
from pbc.mechanics.particles import unstack
from pbc.verification.estimates import convergence_table

# region: setup
G = 1.0  # units of the problem: G = 1, masses and lengths of order one
# endregion: setup

# region: triangle
masses = [1.0, 2.0, 3.0]
side = 1.0
steps_per_period = [50, 100, 200, 400]
# endregion: triangle

# region: stability
small = [0.01, 0.03, 0.06, 0.1, 0.2, 0.5, 1.0]  # masses (1, q, q)
nudge = 1e-8  # the first body moved along x
periods = 8
# endregion: stability

# region: pythagorean
until = 70.0
tolerances = [1e-12, 1e-13]
shifted = 1e-6  # the first body moved along x in the nearby start
# endregion: pythagorean


def bound(value, limit):
    """A value at the level of round-off is shown as below ``limit``."""
    return f"{value:.1e}" if value > limit else f"below {limit:.0e}"


def triangle_run(experiment: Experiment):
    """One period of Lagrange's triangle of masses 1, 2, 3 with the
    classical Runge-Kutta method at four steps, against the exact rotation;
    record the table and return the rows and the finest run."""
    start, omega = lagrange_triangle(G, masses, side)
    period = 2 * np.pi / omega
    acceleration = gravity(G, masses)
    steps, errors, energy, momentum = [], [], [], []
    for n in steps_per_period:
        run = simulate(start, acceleration, period / n, n, step=rk4_step)
        exact = rigid_rotation(start, omega, run.t)
        errors.append(np.max(np.abs(run.x - exact)))
        steps.append(period / n)
        e, ell = total_energy(G, masses, run), angular_momentum(masses, run)
        energy.append(np.max(np.abs(e / e[0] - 1)))
        momentum.append(np.max(np.abs(ell / ell[0] - 1)))
    rows = convergence_table(steps, errors)
    assert rows[-1][2] is not None and abs(rows[-1][2] - 4) < 0.2

    experiment.table(
        "triangle",
        [
            (n, h, error, order, e, bound(ell, 1e-12))
            for n, (h, error, order), e, ell in zip(
                steps_per_period, rows, energy, momentum, strict=True
            )
        ],
        [
            ("steps per period", "", "d"),
            ("time step", "", ".4f"),
            ("largest position error", "", ".2e"),
            ("observed order", "", ".2f"),
            ("largest relative energy change", "", ".1e"),
            ("largest relative angular momentum change", "", ""),
        ],
        "One period of Lagrange's triangle of masses 1, 2, and 3 with side 1 "
        "(G = 1), simulated with the classical Runge-Kutta method, against the "
        "exact rigid rotation, and the conserved quantities along each run.",
    )
    return rows, period


def stability_scan(experiment: Experiment):
    """For masses (1, q, q), the growth rate of a small disturbance of the
    triangle, fitted to the departure from equilateral, against Routh's
    prediction; record the table and return the betas, the measured and the
    predicted rates (in units of omega), and the runs of the smallest and
    the largest q."""
    rows, curves = [], {}
    for q in small:
        m = [1.0, q, q]
        start, omega = lagrange_triangle(G, m, side)
        x = start.x.copy()
        x[0] += nudge
        period = 2 * np.pi / omega
        times = np.linspace(0, periods * period, 1601)
        run = adaptive(G, m, State(0.0, x, start.v), times, 1e-12)
        departure = shape_departure(run.x)
        # The fit runs over the stretch where the disturbance is small but
        # well above its start, after the first transient.
        window = (departure > 1e2 * nudge) & (departure < 1e-2)
        measured = (
            np.polyfit(times[window], np.log(departure[window]), 1)[0] / omega
            if window.sum() > 50
            else 0.0
        )
        predicted = lagrange_growth_rate(m, omega) / omega
        rows.append((q, routh_beta(m), 27 * routh_beta(m), measured, predicted))
        curves[q] = (times / period, departure)
    for _, _, k, measured, predicted in rows:
        if k < 1:
            assert measured == 0.0
        else:
            assert abs(measured / predicted - 1) < 0.02

    experiment.table(
        "stability",
        rows,
        [
            ("small mass q", "", ".2f"),
            ("Routh's beta", "", ".4f"),
            ("27 beta", "", ".3f"),
            ("measured growth rate / omega", "", ".4f"),
            ("predicted growth rate / omega", "", ".4f"),
        ],
        "Lagrange's triangle of masses 1, q, and q, the first body moved by "
        "1e-8: the growth rate of its departure from equilateral, fitted over "
        "eight periods, against Routh's prediction; zero where the departure "
        "never grows past a hundred times its start.",
    )
    return rows, curves


def draw_stability(rows, curves) -> Figure:
    """Left: the departure from equilateral over time for a stable and an
    unstable triangle. Right: the growth rate against 27 beta, measured and
    predicted."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(6.4, 3.4))
    for q, colour, line in ((small[0], 0, "-"), (small[-1], 1, "--")):
        t, departure = curves[q]
        left.semilogy(
            t,
            departure,
            color=FIGURE_COLOURS[colour],
            linestyle=line,
            label=f"q = {q:g}",
        )
    left.set_xlabel("time (periods)")
    left.set_ylabel("departure from equilateral")
    left.legend(fontsize="small", loc="upper left")

    # The prediction of three_body.lagrange_growth_rate, as a function of 27 beta.
    k = np.linspace(0.3, 9.2, 400)
    predicted = 0.5 * np.sqrt(np.sqrt(np.maximum(k, 1)) - 1)
    right.plot(
        k,
        predicted,
        color=FIGURE_COLOURS[0],
        linestyle="--",
        linewidth=1,
        label="Routh's prediction",
    )
    right.plot(
        [row[2] for row in rows],
        [row[3] for row in rows],
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        label="measured",
    )
    right.axvline(1.0, color="#57606a", linestyle=":", linewidth=1)
    right.text(1.15, 0.62, "27 beta = 1", fontsize="small")
    right.set_xlabel("27 beta")
    right.set_ylabel("growth rate / omega")
    right.legend(fontsize="small", loc="lower right")
    fig.tight_layout()
    return fig


def pythagorean_runs(experiment: Experiment):
    """The Pythagorean problem to t = 70 at two tolerances, and from a start
    moved by 1e-6; record the table and return the times and the runs."""
    m, start = pythagorean_start()
    times = np.linspace(0.0, until, 7001)
    runs = [adaptive(G, m, start, times, tol) for tol in tolerances]
    x = start.x.copy()
    x[0] += shifted
    runs.append(adaptive(G, m, State(0.0, x, start.v), times, tolerances[0]))

    rows, outcomes = [], []
    for name, run in zip(
        ("tolerance 1e-12", "tolerance 1e-13", "start moved by 1e-6"),
        runs,
        strict=True,
    ):
        energy = total_energy(G, m, run)
        momentum = angular_momentum(m, run)
        k, outer, inner = escaper(G, m, unstack(run.x[-1], 3), unstack(run.v[-1], 3))
        outcomes.append((k, outer, inner))
        rows.append(
            (
                name,
                np.max(np.abs(energy / energy[0] - 1)),
                bound(np.max(np.abs(momentum)), 1e-10),
                k + 1,
                outer,
                inner,
            )
        )
    assert outcomes[0][0] == outcomes[1][0] == 0
    assert all(o[1] > 0 and o[2] < 0 for o in outcomes[:2])

    experiment.table(
        "pythagorean",
        rows,
        [
            ("run", "", ""),
            ("largest relative energy change", "", ".1e"),
            ("largest total angular momentum", "", ""),
            ("body outside the tightest pair", "", "d"),
            ("its energy against the pair", "", ".1f"),
            ("energy of the pair", "", ".1f"),
        ],
        "Burrau's Pythagorean problem (G = 1) integrated by DOP853 to t = 70: "
        "the conserved quantities, and at the end the body outside the most "
        "tightly bound pair, with its energy relative to the pair.",
    )
    return times, runs, outcomes


def divergence(experiment: Experiment, times, runs):
    """The times at which the run at the tighter tolerance, and the run
    from the moved start, first differ from the reference run by 1e-6,
    1e-3, and 0.1; record the table and return the two separations."""
    reference = runs[0]
    separations = [np.max(np.abs(run.x - reference.x), axis=1) for run in runs[1:]]
    thresholds = [1e-4, 1e-2, 1e-1]
    rows = []
    for threshold in thresholds:
        rows.append(
            (
                threshold,
                *(times[np.argmax(s > threshold)] for s in separations),
            )
        )
    for s in separations:
        assert all(np.any(s > threshold) for threshold in thresholds)

    experiment.table(
        "divergence",
        rows,
        [
            ("separation", "", ".0e"),
            ("first time, tolerance 1e-13 against 1e-12", "", ".1f"),
            ("first time, start moved by 1e-6", "", ".1f"),
        ],
        "The first time at which a run's largest coordinate differs from the "
        "reference run (tolerance 1e-12) by more than the separation.",
    )
    return separations


def draw_pythagorean(times, run) -> Figure:
    """The paths of the three bodies of the Pythagorean problem in two
    stretches of time: the first encounters, from the start (filled
    markers), and the escape, to the end (open markers)."""
    bodies = unstack(run.x, 3)
    stretches = ((0.0, 20.0, 0), (50.0, until, -1))
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.6))
    styles = ("-", "--", ":")
    markers = ("o", "s", "^")
    for ax, (begin, end, mark) in zip(axes, stretches, strict=True):
        inside = (times >= begin) & (times <= end)
        for k, (mass, line, marker) in enumerate(
            zip((3, 4, 5), styles, markers, strict=True)
        ):
            ax.plot(
                bodies[inside, k, 0],
                bodies[inside, k, 1],
                color=FIGURE_COLOURS[k],
                linestyle=line,
                linewidth=0.8,
                label=f"mass {mass}",
            )
            ax.plot(
                bodies[inside, k, 0][mark],
                bodies[inside, k, 1][mark],
                color=FIGURE_COLOURS[k],
                marker=marker,
                markersize=7,
                markerfacecolor=None if mark == 0 else "white",
                linestyle="",
            )
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_title(f"t from {begin:g} to {end:g}", fontsize="small")
        ax.set_xlabel("x (units of the problem)")
    axes[0].set_ylabel("y (units of the problem)")
    axes[0].legend(fontsize="small", loc="upper left")
    fig.tight_layout()
    return fig


def draw_divergence(times, runs, separations) -> Figure:
    """The separation of the two other runs from the reference run, and the
    relative energy error of the reference run, against time, log scale."""
    m, _ = pythagorean_start()
    energy = total_energy(G, m, runs[0])
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.semilogy(
        times[1:],
        separations[0][1:],
        color=FIGURE_COLOURS[0],
        label="tolerance 1e-13 against 1e-12",
    )
    ax.semilogy(
        times[1:],
        separations[1][1:],
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="start moved by 1e-6",
    )
    ax.semilogy(
        times[1:],
        np.abs(energy[1:] / energy[0] - 1),
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="relative energy error, reference run",
    )
    ax.set_xlabel("time (units of the problem)")
    ax.set_ylabel("largest coordinate difference, energy error")
    ax.legend(fontsize="small", loc="lower right")
    return fig


def critical_mass_ratio():
    """Exercise 1: the mass ratio mu = m2 / (m1 + m2) of a star and a planet
    above which a third body of negligible mass at the corner of the
    triangle is unstable: 27 mu (1 - mu) = 1."""
    return (1 - np.sqrt(23 / 27)) / 2


def trojan_libration():
    """Exercise 2: the Sun, Jupiter, and a Trojan body of 1e-9 solar masses
    at Lagrange's corner, the Trojan's position and velocity turned forward
    by 0.01 AU along Jupiter's orbit; the period of its slow libration,
    measured from the angle between the Trojan and Jupiter as seen from the
    Sun, against the predicted one, in years, and the full swing of the
    angle in degrees."""
    g = 4 * np.pi**2  # AU³ / (M_sun yr²)
    m = [1.0, 9.547e-4, 1e-9]
    radius = 5.2
    start, omega = lagrange_triangle(g, m, radius)
    x, v = unstack(start.x, 3), unstack(start.v, 3)
    turn = 0.01 / radius
    rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
    x[2], v[2] = rotation @ x[2], rotation @ v[2]
    times = np.linspace(0.0, 600.0, 6001)
    run = adaptive(g, m, State(0.0, x.reshape(-1), v.reshape(-1)), times, 1e-11)
    bodies = unstack(run.x, 3)
    jupiter, trojan = bodies[:, 1] - bodies[:, 0], bodies[:, 2] - bodies[:, 0]
    angle = np.arctan2(
        jupiter[:, 0] * trojan[:, 1] - jupiter[:, 1] * trojan[:, 0],
        np.sum(jupiter * trojan, axis=1),
    )
    # The slow libration is the strongest peak of the spectrum of the angle
    # below the orbital frequency.
    deviation = angle - angle.mean()
    spectrum = np.abs(np.fft.rfft(deviation * np.hanning(len(deviation))))
    frequencies = np.fft.rfftfreq(len(times), times[1] - times[0])
    slow = (frequencies > 0) & (frequencies < 0.5 * omega / (2 * np.pi))
    k = np.flatnonzero(slow)[np.argmax(spectrum[slow])]
    # A parabola through the logarithm of the peak and its neighbours
    # refines the frequency.
    a, b, c = np.log(spectrum[k - 1 : k + 2])
    peak = frequencies[k] + 0.5 * (a - c) / (a - 2 * b + c) * frequencies[1]
    predicted = 2 * np.pi / lagrange_libration(m, omega)[0]
    return 1 / peak, predicted, np.degrees(np.ptp(angle))


def loose_tolerance():
    """Exercise 3: the Pythagorean problem at the tolerance 1e-6; its largest
    relative energy error and, at the end, the body outside the tightest
    pair with the two energies."""
    m, start = pythagorean_start()
    times = np.linspace(0.0, until, 7001)
    run = adaptive(G, m, start, times, 1e-6)
    energy = total_energy(G, m, run)
    k, outer, inner = escaper(G, m, unstack(run.x[-1], 3), unstack(run.v[-1], 3))
    return np.max(np.abs(energy / energy[0] - 1)), k + 1, outer, inner


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()

    rows, period = triangle_run(experiment)
    experiment.number("triangle-period", period, ".4f")
    experiment.number("triangle-order", rows[-1][2], ".2f")
    experiment.number("triangle-beta", 27 * routh_beta(masses), ".3f")

    stability, curves = stability_scan(experiment)
    experiment.figure("fig-stability", partial(draw_stability, stability, curves))
    unstable = [row for row in stability if row[2] > 1]
    gap = max(abs(measured / predicted - 1) for *_, measured, predicted in unstable)
    experiment.number("rate-gap", 100 * gap, ".1f")
    experiment.number("equal-rate", stability[-1][3], ".4f")
    e_folds = np.exp(2 * np.pi * stability[-1][3])
    experiment.number("equal-factor", e_folds, ".0f")

    times, runs, outcomes = pythagorean_runs(experiment)
    experiment.figure("fig-pythagorean", partial(draw_pythagorean, times, runs[0]))
    separations = divergence(experiment, times, runs)
    experiment.figure(
        "fig-divergence", partial(draw_divergence, times, runs, separations)
    )
    experiment.number("moved-final", separations[1][-1], ".0f")
    energy = total_energy(G, pythagorean_start()[0], runs[0])
    experiment.number(
        "pythagorean-energy", np.max(np.abs(energy / energy[0] - 1)), ".0e"
    )
    experiment.number("escaper", outcomes[0][0] + 1)

    experiment.number("critical-mu", critical_mass_ratio(), ".5f")
    measured, predicted, swing = trojan_libration()
    experiment.number("libration-measured", measured, ".0f")
    experiment.number("libration-predicted", predicted, ".0f")
    experiment.number("libration-swing", swing, ".1f")
    drift, body, outer, inner = loose_tolerance()
    experiment.number("loose-energy", drift, ".0e")
    experiment.number("loose-body", body)
    experiment.number("loose-outer", outer, ".2f")
    experiment.number("loose-inner", inner, ".2f")
    return experiment


if __name__ == "__main__":
    main(run)
