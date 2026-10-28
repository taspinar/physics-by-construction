"""The experiment of the lesson "Open quantum systems and decoherence".

A qubit with decay and dephasing, its density matrix advanced by the
Lindblad equation (``pbc.quantum.open_systems``): Ramsey fringes that fade
against the closed form, the trace and the positivity of rho under three
integrators, and their convergence. Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.quantum.experiments.open_quantum_systems out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.authoring import FIGURE_COLOURS
from pbc.experiment import Experiment, main
from pbc.quantum.bell import SINGLET, density
from pbc.quantum.open_systems import (
    choi,
    coherence_time,
    euler_step,
    evolve,
    exact_qubit,
    expectation,
    exponential_step,
    partial_trace,
    plus_x,
    purity,
    qubit,
    ramsey,
    random_phase_coherence,
    rk4_step,
    smallest_eigenvalue,
    trace,
)
from pbc.quantum.spin import SIGMA_X, SIGMA_Y, SIGMA_Z
from pbc.verification.estimates import fitted_order

# region: setup
# Units: hbar = 1, frequencies and rates in units of the detuning Delta.
DETUNING = 1.0  # Delta, the precession of the phase
DECAY = 0.05  # gamma = 1 / T1
DEPHASING = 0.10  # gamma_phi
G = qubit(DETUNING, DECAY, DEPHASING)
START = plus_x()  # the qubit along +x, as after the first Ramsey pulse
# endregion: setup

# region: ramsey
ramsey_step = 0.1
ramsey_end = 40.0
# endregion: ramsey

# region: integrators
long_end = 60.0
steps = [0.5, 3.0]
INTEGRATORS = {
    "explicit Euler": euler_step,
    "Runge-Kutta, fourth order": rk4_step,
    "exponential": exponential_step,
}
# endregion: integrators

# region: convergence
convergence_end = 10.0
convergence_steps = [0.1, 0.05, 0.025, 0.0125, 0.00625]
# endregion: convergence

ROUND_OFF = 1e-12


def below(value: float, bound: float = ROUND_OFF) -> str:
    """A size set by round-off is not shown as a number: only that it is
    smaller than ``bound``."""
    if abs(value) >= bound:
        raise ValueError(f"{value!r} is not below {bound!r}")
    return f"below {bound:.0e}"


def shown(value: float, spec: str) -> str:
    """``value`` in ``spec``, or "zero to round-off" when it is below
    ``ROUND_OFF`` in size."""
    return "zero to round-off" if abs(value) < ROUND_OFF else format(value, spec)


def bloch(states) -> np.ndarray:
    """The Bloch vector (<sigma_x>, <sigma_y>, <sigma_z>) of each rho."""
    return np.stack([expectation(states, s) for s in (SIGMA_X, SIGMA_Y, SIGMA_Z)], -1)


def ramsey_run(experiment: Experiment):
    """The qubit started along +x, advanced by the exponential integrator:
    the probability of +x, the population, and the purity against the
    closed form; record the table."""
    count = round(ramsey_end / ramsey_step)
    times = np.arange(count + 1) * ramsey_step
    states = evolve(START, exponential_step(G, ramsey_step), count)
    exact = exact_qubit(START, times, DETUNING, DECAY, DEPHASING)
    t2 = coherence_time(DECAY, DEPHASING)
    fringe = (1 + expectation(states, SIGMA_X)) / 2
    gap = np.max(np.abs(states - exact))
    assert gap < ROUND_OFF
    assert np.max(np.abs(fringe - ramsey(times, DETUNING, t2))) < ROUND_OFF

    shown_times = [0.0, 5.0, 10.0, 20.0, 40.0]
    index = [round(t / ramsey_step) for t in shown_times]
    experiment.table(
        "ramsey",
        [
            (
                times[i],
                fringe[i],
                ramsey(times[i], DETUNING, t2),
                np.real(states[i, 0, 0]),
                np.exp(-DECAY * times[i]) / 2,
                purity(states[i]),
            )
            for i in index
        ],
        [
            ("time t", "1 / Delta", ".0f"),
            ("probability of +x", "", ".6f"),
            ("closed form", "", ".6f"),
            ("excited population", "", ".6f"),
            ("closed form", "", ".6f"),
            ("purity tr(rho^2)", "", ".4f"),
        ],
        "The qubit started along +x and advanced by the exponential integrator: "
        "the probability of the outcome +1 along x, the population of the "
        "excited state, each against its closed form, and the purity.",
    )
    return times, fringe, t2, gap


def draw_ramsey(times, fringe, t2) -> Figure:
    """The probability of +x against time, computed and closed form, with
    the fringe of the isolated qubit and the envelope."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    fine = np.linspace(0, times[-1], 801)
    ax.plot(
        fine,
        ramsey(fine, DETUNING, np.inf),
        color=FIGURE_COLOURS[2],
        linewidth=0.8,
        label="isolated qubit, no environment",
    )
    ax.plot(
        fine,
        (1 + np.exp(-fine / t2)) / 2,
        color=FIGURE_COLOURS[1],
        linestyle=":",
        label="envelope (1 + exp(-t / T2)) / 2",
    )
    ax.plot(
        times,
        fringe,
        color=FIGURE_COLOURS[0],
        linewidth=1.8,
        label="Lindblad, exponential integrator",
    )
    ax.plot(
        fine[::20],
        ramsey(fine[::20], DETUNING, t2),
        "o",
        color=FIGURE_COLOURS[1],
        markerfacecolor="none",
        markersize=4,
        label="closed form",
    )
    ax.set_ylim(-0.02, 1.3)
    ax.set_xlabel("time t (units of 1 / Delta)")
    ax.set_ylabel("probability of +1 along x")
    ax.legend(fontsize="small", ncol=2, loc="upper center")
    return fig


def integrators_run(experiment: Experiment):
    """Each integrator at two steps over a long run: the trace, the smallest
    eigenvalue of rho, the length of the Bloch vector, and the smallest
    eigenvalue of the Choi matrix of one step; record the table."""
    rows, lengths = [], {}
    for dt in steps:
        count = round(long_end / dt)
        exact = exact_qubit(
            START, np.arange(count + 1) * dt, DETUNING, DECAY, DEPHASING
        )
        for name, make in INTEGRATORS.items():
            step = make(G, dt)
            states = evolve(START, step, count)
            drift = np.max(np.abs(trace(states) - 1))
            lowest = np.min(smallest_eigenvalue(states[1:]))
            length = np.linalg.norm(bloch(states), axis=-1)
            completely = smallest_eigenvalue(choi(step))
            error = np.max(np.abs(states - exact))
            assert drift < ROUND_OFF
            rows.append(
                (
                    name,
                    dt,
                    below(drift),
                    shown(lowest, ".3g"),
                    np.max(length[1:]),
                    shown(completely, ".3g"),
                    error,
                )
            )
            lengths[name, dt] = length
            if name == "exponential":
                assert lowest > 0 and completely > -ROUND_OFF and error < ROUND_OFF
    found = {(row[0], row[1]): row for row in rows}
    assert found["explicit Euler", 0.5][3] != "zero to round-off"
    assert float(found["explicit Euler", 0.5][3]) < 0
    assert float(found["Runge-Kutta, fourth order", 0.5][3]) > 0
    assert float(found["Runge-Kutta, fourth order", 3.0][3]) < 0

    experiment.table(
        "integrators",
        rows,
        [
            ("integrator", "", ""),
            ("step dt", "1 / Delta", ".1f"),
            ("largest |tr(rho) - 1|", "", ""),
            ("smallest eigenvalue of rho", "", ""),
            ("longest Bloch vector", "", ".3g"),
            ("smallest eigenvalue of the Choi matrix of a step", "", ""),
            ("largest error", "", ".2e"),
        ],
        "The qubit advanced to t = 60 by each integrator at two steps: the "
        "largest drift of the trace, the smallest eigenvalue of rho after the "
        "start, the longest Bloch vector, the smallest eigenvalue of the Choi "
        "matrix of one step (negative: the step is not completely positive), and "
        "the largest error against the closed form.",
    )
    return lengths


def draw_lengths(lengths) -> Figure:
    """The length of the Bloch vector against time for the three
    integrators at the step 0.5, with the surface of the Bloch ball."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    dt = steps[0]
    styles = [("-", "o"), ("--", "s"), (":", "^")]
    for colour, (line, marker), name in zip(
        FIGURE_COLOURS, styles, INTEGRATORS, strict=False
    ):
        length = lengths[name, dt]
        t = np.arange(length.size) * dt
        ax.semilogy(
            t,
            length,
            color=colour,
            linestyle=line,
            marker=marker,
            markevery=10,
            markerfacecolor="none",
            label=name,
        )
    ax.axhline(1.0, color=FIGURE_COLOURS[2], linewidth=1)
    ax.text(
        long_end,
        1.15,
        "surface of the Bloch ball: beyond it rho is not positive",
        fontsize="small",
        ha="right",
    )
    ax.set_xlabel("time t (units of 1 / Delta)")
    ax.set_ylabel("length of the Bloch vector (log scale)")
    ax.legend(fontsize="small", loc="upper left", bbox_to_anchor=(0, 0.9))
    return fig


def convergence_run(experiment: Experiment):
    """The error at t = 10 of each integrator as the step is halved;
    record the table."""
    exact = exact_qubit(START, [convergence_end], DETUNING, DECAY, DEPHASING)[0]
    errors = {name: [] for name in INTEGRATORS}
    for dt in convergence_steps:
        count = round(convergence_end / dt)
        for name, make in INTEGRATORS.items():
            final = evolve(START, make(G, dt), count)[-1]
            errors[name].append(np.max(np.abs(final - exact)))
    orders = {
        name: fitted_order(convergence_steps, errors[name])
        for name in ("explicit Euler", "Runge-Kutta, fourth order")
    }
    assert abs(orders["explicit Euler"] - 1) < 0.15
    assert abs(orders["Runge-Kutta, fourth order"] - 4) < 0.05
    assert max(errors["exponential"]) < ROUND_OFF

    experiment.table(
        "convergence",
        [
            (
                dt,
                errors["explicit Euler"][i],
                errors["Runge-Kutta, fourth order"][i],
                below(errors["exponential"][i]),
            )
            for i, dt in enumerate(convergence_steps)
        ],
        [
            ("step dt", "1 / Delta", ".5g"),
            ("explicit Euler", "", ".3e"),
            ("Runge-Kutta, fourth order", "", ".3e"),
            ("exponential", "", ""),
        ],
        "The largest error of rho at t = 10 against the closed form, for each "
        "integrator, as the step is halved.",
    )
    return errors, orders


def draw_convergence(errors) -> Figure:
    """The error against the step, log-log, with reference slopes."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    h = np.array(convergence_steps)
    for colour, marker, name in zip(
        FIGURE_COLOURS,
        ["o", "s"],
        ("explicit Euler", "Runge-Kutta, fourth order"),
        strict=False,
    ):
        ax.loglog(
            h, errors[name], marker, color=colour, markerfacecolor="none", label=name
        )
    for order, anchor, name in (
        (1, "explicit Euler", "slope one"),
        (4, "Runge-Kutta, fourth order", "slope four"),
    ):
        reference = 0.5 * errors[anchor][-1] * (h / h[-1]) ** order
        ax.loglog(h, reference, color=FIGURE_COLOURS[2], linestyle=":", linewidth=1)
        ax.text(h[0], reference[0], f" {name}", va="center", fontsize="small")
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(h, [f"{v:g}" for v in h])
    ax.set_xlim(h[-1] * 0.8, h[0] * 2.2)
    ax.set_xlabel("step dt (units of 1 / Delta)")
    ax.set_ylabel("largest error of rho at t = 10")
    ax.legend(fontsize="small", loc="lower right")
    return fig


def phase_kicks():
    """Exercise 1: two thousand pure qubits with random phase kicks; their
    mean coherence against exp(-gamma_phi t), in standard errors."""
    rng = np.random.default_rng(20261029)
    times = np.linspace(0.0, 20.0, 41)[1:]
    mean, error = random_phase_coherence(times, DEPHASING, 2_000, rng)
    deviation = np.abs(mean.real - np.exp(-DEPHASING * times)) / error
    return float(np.max(deviation)), float(np.max(np.abs(mean.imag)))


def half_of_a_singlet():
    """Exercise 2: the state of one spin of the singlet and its purity, and
    the purity of the pair."""
    pair = density(SINGLET)
    one = partial_trace(pair, keep=0)
    return float(np.max(np.abs(one - np.eye(2) / 2))), purity(one), purity(pair)


def pure_decay():
    """Exercise 3: without dephasing, the coherence at t = T1 against
    exp(-1/2), which is T2 = 2 T1."""
    g = qubit(0.0, DECAY, 0.0)
    t1 = 1 / DECAY
    final = evolve(START, exponential_step(g, t1 / 100), 100)[-1]
    return float(np.abs(final[0, 1]) / 0.5), float(np.exp(-0.5))


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    times, fringe, t2, gap = ramsey_run(experiment)
    experiment.figure("fig-ramsey", partial(draw_ramsey, times, fringe, t2))
    experiment.number("t1", 1 / DECAY, ".0f")
    experiment.number("t2", t2, ".0f")
    experiment.number("ramsey-gap", below(gap))

    lengths = integrators_run(experiment)
    experiment.figure("fig-bloch-length", partial(draw_lengths, lengths))
    rate = 1 / t2
    experiment.number(
        "euler-growth", np.hypot(1 - rate * steps[0], DETUNING * steps[0]), ".3f"
    )

    errors, orders = convergence_run(experiment)
    experiment.figure("fig-convergence", partial(draw_convergence, errors))
    experiment.number("order-euler", orders["explicit Euler"], ".2f")
    experiment.number("order-rk4", orders["Runge-Kutta, fourth order"], ".2f")

    worst, imaginary = phase_kicks()
    experiment.number("kick-worst", worst, ".1f")
    experiment.number("kick-imaginary", imaginary, ".3f")
    gap_one, purity_one, purity_pair = half_of_a_singlet()
    experiment.number("singlet-gap", below(gap_one))
    experiment.number("purity-one", purity_one, ".3f")
    experiment.number("purity-pair", purity_pair, ".3f")
    ratio, expected = pure_decay()
    experiment.number("decay-ratio", ratio, ".6f")
    experiment.number("decay-expected", expected, ".6f")
    return experiment


if __name__ == "__main__":
    main(run)
