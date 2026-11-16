"""The experiment of the lesson "Numerical integrators".

Explicit Euler, symplectic Euler, velocity Verlet, and classical Runge-Kutta
(``pbc.mechanics.integrators``) on the mass on a spring: their state after
three periods, their order, their energy over short and long runs, their
cost, and the data of the integrator explorer. Run it as a program to write
the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.numerical_integrators out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g

from pbc.authoring import diagrams
from pbc.experiment import Experiment, main
from pbc.mechanics.drag import fall_with_linear_drag, linear_drag
from pbc.mechanics.dynamics import State, newton, simulate, weight
from pbc.mechanics.explorer import STEPS_PER_PERIOD, explorer_data
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import angular_frequency, energy, harmonic_motion, spring

# region: setup
mass = 0.5  # kg
k = 2.0  # spring constant, N/m
omega = angular_frequency(mass, k)
period = 2 * np.pi / omega
released = State(t=0.0, x=1.0, v=0.0)
oscillator = newton(mass, spring(k))
# endregion: setup

# region: coarse
coarse, coarse_periods = 50, 3
# endregion: coarse
# region: step-counts
step_counts = [25 * 2**i for i in range(6)]
# endregion: step-counts
# The energy over twenty periods at twenty steps per period, and the long run.
# region: twenty-periods
n_periods, n = 20, 20
z = omega * period / n
dt = period / n
long_n, long_periods = 32, 1000
# endregion: twenty-periods

# The colours and line styles of the explorer's figure.
LINE_STYLES = [
    ("#b34700", "-"),
    ("#005a9c", (0, (7, 4))),
    ("#00734f", (0, (2, 4))),
    ("#6a3d9a", (0, (9, 4, 2, 4))),
]
default = STEPS_PER_PERIOD.index(16)


def draw_update_orderings() -> Figure:
    """The data flow of explicit and of symplectic Euler, as a sketch."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0))
    orderings = (
        ("Explicit Euler", 0, False),
        ("Symplectic Euler", 1, True),
    )
    for ax, (name, colour, velocity_first) in zip(axes, orderings, strict=True):
        diagrams.frame(ax, (-0.2, 4.4), (-0.7, 3.2))
        diagrams.text(ax, (2.1, 3.0), name, colour=colour)
        left, right = 0.4, 3.8
        diagrams.state_box(
            ax, (left, 2.0), "$x_n$", width=1.0, height=0.7, colour=colour
        )
        diagrams.state_box(
            ax, (left, 0.4), "$v_n$", width=1.0, height=0.7, colour=colour
        )
        diagrams.state_box(
            ax, (right, 2.0), "$x_{n+1}$", width=1.0, height=0.7, colour=colour
        )
        diagrams.state_box(
            ax, (right, 0.4), "$v_{n+1}$", width=1.0, height=0.7, colour=colour
        )
        diagrams.arrow(ax, (left + 0.5, 2.0), (right - 0.5, 2.0), colour=colour)
        diagrams.arrow(ax, (left + 0.5, 0.4), (right - 0.5, 0.4), colour=colour)
        diagrams.arrow(
            ax, (left + 0.45, 1.7), (right - 0.45, 0.7), colour=colour, linestyle="--"
        )
        if velocity_first:
            diagrams.arrow(ax, (right, 0.75), (right, 1.65), colour=colour)
            diagrams.text(
                ax, (right + 0.1, 1.2), "new\nvelocity", ha="left", colour=colour
            )
        else:
            diagrams.arrow(ax, (left + 0.45, 0.7), (right - 0.45, 1.7), colour=colour)
            diagrams.text(
                ax, (right + 0.1, 1.2), "old\nvelocity", ha="left", colour=colour
            )
        diagrams.text(
            ax, (2.1, -0.4), "dashed: the force, from $x_n$", colour="#57606a"
        )
    fig.tight_layout()
    return fig


def methods(experiment: Experiment) -> None:
    """Record the table of the four methods, as INTEGRATORS gives them."""
    experiment.table(
        "methods",
        [(i.name, i.step.__name__, i.order, i.evaluations) for i in INTEGRATORS],
        columns=[
            ("method", "", ""),
            ("stepper", "", ""),
            ("order", "", "d"),
            ("evaluations per step", "", "d"),
        ],
        caption="The four methods of the lesson, as the list INTEGRATORS gives them.",
    )


def counted(acceleration):
    """The acceleration function, and a list that grows by one per call."""
    calls = []

    def counting(t, x, v):
        calls.append(1)
        return acceleration(t, x, v)

    return counting, calls


def run_method(
    integrator, steps_per_period, n_periods, start=released, acceleration=oscillator
):
    """Simulate n_periods with the integrator; the trajectory and the number
    of calls."""
    counting, calls = counted(acceleration)
    trajectory = simulate(
        start,
        counting,
        period / steps_per_period,
        round(n_periods * steps_per_period),
        step=integrator.step,
    )
    return trajectory, len(calls)


def after_three_periods(experiment: Experiment) -> dict:
    """The state after three periods at fifty steps per period for each
    method; record the table and return the final energy of each."""
    final = {}
    rows = []
    for integrator in INTEGRATORS:
        trajectory, calls = run_method(integrator, coarse, coarse_periods)
        relative = energy(trajectory, mass, k)
        final[integrator.name] = relative[-1] / relative[0]
        rows.append(
            (
                integrator.name,
                trajectory.x[-1, 0],
                trajectory.v[-1, 0],
                final[integrator.name],
                calls,
            )
        )
    exact_end = harmonic_motion(released, mass, k, coarse_periods * period)
    rows.append(("exact", exact_end.x[0, 0], exact_end.v[0, 0], 1.0, None))

    experiment.table(
        "state-after-three-periods",
        rows,
        columns=[
            ("method", "", ""),
            ("x", "m", ".3f"),
            ("v", "m/s", ".3f"),
            ("energy / initial", "", ".6f"),
            ("calls", "", "d"),
        ],
        caption="State after three periods at fifty steps per period, to three "
        "decimals; energy to six decimals.",
    )
    return final


def draw_integrators_phase_space() -> Figure:
    """Three periods in phase space for each method, against the exact
    ellipse."""
    exact_orbit = harmonic_motion(released, mass, k, np.linspace(0.0, period, 200))

    fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.4), sharex=True, sharey=True)
    for ax, integrator in zip(axes.flat, INTEGRATORS, strict=True):
        trajectory, _ = run_method(integrator, coarse, coarse_periods)
        ax.plot(
            exact_orbit.x[:, 0],
            exact_orbit.v[:, 0],
            color="#00429d",
            linestyle=":",
            label="exact",
        )
        ax.plot(trajectory.x[:, 0], trajectory.v[:, 0], color="#93003a", linewidth=0.8)
        ax.set_title(integrator.name, fontsize=10)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-7.0, 7.0)
        ax.set_aspect(1 / omega)
    for ax in axes[1]:
        ax.set_xlabel("position (m)")
    for ax in axes[:, 0]:
        ax.set_ylabel("velocity (m/s)")
    fig.tight_layout()
    return fig


def state_error(trajectory):
    """Largest distance from the exact state in the plane (x, v / omega), in m."""
    exact = harmonic_motion(released, mass, k, trajectory.t)
    dx = trajectory.x - exact.x
    dv = (trajectory.v - exact.v) / omega
    return np.max(np.sqrt(np.sum(dx**2 + dv**2, axis=1)))


def error_orders(experiment: Experiment) -> dict:
    """The largest error over two periods for each method and step count,
    with the observed order; record the table and return the errors."""
    errors = {
        integrator.name: np.array(
            [state_error(run_method(integrator, n, 2)[0]) for n in step_counts]
        )
        for integrator in INTEGRATORS
    }

    columns = [("steps per period", "", "d")]
    for integrator in INTEGRATORS:
        columns += [(f"{integrator.name} error", "m", ".2e"), ("order", "", ".2f")]
    rows = []
    for i, n in enumerate(step_counts):
        row = [n]
        for integrator in INTEGRATORS:
            error = errors[integrator.name]
            row += [error[i], np.log2(error[i - 1] / error[i]) if i else None]
        rows.append(row)

    experiment.table(
        "error-orders",
        rows,
        columns=columns,
        caption="Largest error over two periods for each method, with the "
        "observed order from the previous row.",
    )
    return errors


def draw_integrators_convergence(errors: dict) -> Figure:
    """The largest error against the time step for the four methods."""
    steps = period / np.array(step_counts)
    styles = {
        "explicit Euler": ("o", "-"),
        "symplectic Euler": ("s", "--"),
        "velocity Verlet": ("^", "-."),
        "Runge-Kutta 4": ("D", ":"),
    }

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for integrator in INTEGRATORS:
        marker, linestyle = styles[integrator.name]
        ax.loglog(
            steps,
            errors[integrator.name],
            color="#93003a",
            marker=marker,
            linestyle=linestyle,
            markersize=4,
            label=integrator.name,
        )
    for slope, anchor in ((1, 1.5), (2, 0.15), (4, 1.5e-3)):
        ax.loglog(
            steps,
            anchor * (steps / steps[0]) ** slope,
            color="#555555",
            linestyle=":",
            linewidth=0.8,
        )
        ax.annotate(
            f"slope {slope}",
            (steps[-1], anchor * (steps[-1] / steps[0]) ** slope),
            textcoords="offset points",
            xytext=(4, -8),
            fontsize=8,
            color="#555555",
        )
    ax.set_xlabel("time step (s)")
    ax.set_ylabel("largest error over two periods (m)")
    ax.legend(loc="lower right")
    return fig


def draw_integrators_energy() -> Figure:
    """The energy over twenty periods at twenty steps per period."""
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 5.6), sharex=True)
    for ax, integrator in zip(axes.flat, INTEGRATORS, strict=True):
        trajectory, _ = run_method(integrator, n, n_periods)
        relative = energy(trajectory, mass, k)
        ax.plot(
            trajectory.t / period,
            relative / relative[0],
            color="#93003a",
            linewidth=0.8,
        )
        if integrator.name == "explicit Euler":
            ax.set_yscale("log")
        ax.set_title(integrator.name, fontsize=10)
    for ax in axes[1]:
        ax.set_xlabel("time (periods)")
    for ax in axes[:, 0]:
        ax.set_ylabel("energy / initial energy")
    fig.tight_layout()
    return fig


def relative_energy(trajectory):
    e = energy(trajectory, mass, k)
    return e / e[0]


def ratios(trajectory):
    e = energy(trajectory, mass, k)
    return e[1:] / e[:-1]


def spread(values):
    """Largest relative deviation from the first value."""
    return np.max(np.abs(values / values[0] - 1))


def energy_formulas(experiment: Experiment):
    """The energy formulas of the lesson against the runs of the
    figure; record the table and return the runs and modified energies."""
    results = {
        integrator.name: run_method(integrator, n, n_periods)[0]
        for integrator in INTEGRATORS
    }
    euler, symplectic, verlet, rk4 = (results[i.name] for i in INTEGRATORS)
    modified_se = (
        0.5
        * mass
        * (
            symplectic.v[:, 0] ** 2
            + omega**2 * symplectic.x[:, 0] ** 2
            - omega**2 * dt * symplectic.x[:, 0] * symplectic.v[:, 0]
        )
    )
    modified_vv = (
        0.5
        * mass
        * (
            verlet.v[:, 0] ** 2
            + omega**2 * (1 - omega**2 * dt**2 / 4) * verlet.x[:, 0] ** 2
        )
    )
    rk4_factor = 1 - z**6 / 72 + z**8 / 576

    experiment.table(
        "energy-formulas",
        [
            (
                "explicit Euler",
                "ratio per step",
                ratios(euler)[0],
                1 + z**2,
                np.max(np.abs(ratios(euler) - (1 + z**2))),
            ),
            (
                "Runge-Kutta 4",
                "ratio per step",
                ratios(rk4)[0],
                rk4_factor,
                np.max(np.abs(ratios(rk4) - rk4_factor)),
            ),
            ("symplectic Euler", "modified energy", None, None, spread(modified_se)),
            ("velocity Verlet", "modified energy", None, None, spread(modified_vv)),
        ],
        columns=[
            ("method", "", ""),
            ("quantity", "", ""),
            ("computed", "", ".8f"),
            ("derived", "", ".8f"),
            ("largest deviation", "", ".1e"),
        ],
        caption="The energy formulas derived in the lesson against the runs of the "
        "figure: the per-step energy ratio, and how far the modified energy "
        "strays from constant.",
    )
    return symplectic, verlet, modified_se, modified_vv, rk4_factor


def long_run_energy_bands(experiment: Experiment):
    """A thousand periods at thirty-two steps per period for the methods
    after explicit Euler; record the table and return the largest state
    error and the lowest energy of each."""
    long_runs, long_lowest = {}, {}
    rows = []
    for integrator in INTEGRATORS[1:]:
        trajectory, calls = run_method(integrator, long_n, long_periods)
        relative = relative_energy(trajectory)
        long_runs[integrator.name] = state_error(trajectory)
        long_lowest[integrator.name] = np.min(relative)
        rows.append(
            (
                integrator.name,
                np.min(relative),
                np.max(relative),
                relative[-1],
                long_runs[integrator.name],
                calls,
            )
        )

    experiment.table(
        "long-run-energy-bands",
        rows,
        columns=[
            ("method", "", ""),
            ("lowest energy / initial", "", ".5f"),
            ("highest energy / initial", "", ".5f"),
            ("energy / initial at the end", "", ".5f"),
            ("largest state error", "m", ".3f"),
            ("calls", "", "d"),
        ],
        caption="A thousand periods at thirty-two steps per period: the range of "
        "the energy, and the largest distance from the exact state.",
    )
    return long_runs, long_lowest


def calls_for_one_millimetre(experiment: Experiment, errors: dict) -> dict:
    """The steps each method needs for an error of one millimetre over two
    periods, predicted from its order; record the table and return the
    calls of each."""
    tolerance = 1e-3  # m

    cost = {}
    rows = []
    for integrator in INTEGRATORS:
        finest_error = errors[integrator.name][-1]
        needed = int(
            np.ceil(
                step_counts[-1] * (finest_error / tolerance) ** (1 / integrator.order)
            )
        )
        trajectory, calls = run_method(integrator, needed, 2)
        cost[integrator.name] = calls
        rows.append((integrator.name, needed, state_error(trajectory), calls))

    experiment.table(
        "calls-for-one-millimetre",
        rows,
        columns=[
            ("method", "", ""),
            ("steps per period", "", "d"),
            ("error", "m", ".1e"),
            ("calls over two periods", "", "d"),
        ],
        caption="Steps predicted from the order for an error of one millimetre "
        "over two periods, with the error reached and the calls it took.",
    )
    return cost


def draw_integrator_explorer(explorer: dict) -> Figure:
    """The explorer's figure without scripts: position and energy over five
    periods at the default step count."""
    runs = {run["name"]: run["series"] for run in explorer["integrators"]}
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6.4, 5.2), sharex=True)
    top.plot(
        np.array(explorer["exact"]["t"]) / period,
        explorer["exact"]["x"],
        color="#444444",
        linewidth=1.0,
        label="exact",
    )
    for (color, style), integrator in zip(LINE_STYLES, INTEGRATORS, strict=True):
        series = runs[integrator.name][default]
        t = np.arange(len(series["x"])) / series["steps_per_period"]
        top.plot(
            t,
            series["x"],
            color=color,
            linestyle=style,
            linewidth=1.4,
            label=integrator.name,
        )
        bottom.plot(t, series["e"], color=color, linestyle=style, linewidth=1.4)
    top.set_ylim(-1.5, 1.5)
    top.set_ylabel("position (m)")
    top.legend(loc="upper right", fontsize=7, ncol=3)
    bottom.set_yscale("log")
    bottom.set_ylabel("energy / initial energy")
    bottom.set_xlabel("time (periods)")
    fig.tight_layout()
    return fig


def explorer_tables(experiment: Experiment, explorer: dict) -> None:
    """Record what the explorer can show as three tables, one row per step
    count."""
    runs = {run["name"]: run["series"] for run in explorer["integrators"]}
    for name, title, key, spec, unit in [
        (
            "explorer-final-energy",
            "Energy after five periods relative to the initial energy",
            "final_energy",
            ".4g",
            "",
        ),
        (
            "explorer-max-error",
            "Largest position error over five periods",
            "max_error",
            ".2e",
            "m",
        ),
        (
            "explorer-calls",
            "Evaluations of the acceleration over five periods",
            "calls",
            "d",
            "",
        ),
    ]:
        experiment.table(
            name,
            [
                (n, *(series[j][key] for series in runs.values()))
                for j, n in enumerate(STEPS_PER_PERIOD)
            ],
            columns=[("steps per period", "", "d")]
            + [(method, unit, spec) for method in runs],
            caption=f"{title}, for each step count of the figure.",
        )


def stability_limits(experiment: Experiment) -> None:
    """Exercise 1: the energy after one hundred steps near the stability
    limits; record the table."""
    rows = []
    for steps_per_period in (3.5, 3.0, 2.2):
        row = [steps_per_period, 2 * np.pi / steps_per_period]
        for integrator in INTEGRATORS:
            trajectory = simulate(
                released,
                oscillator,
                period / steps_per_period,
                100,
                step=integrator.step,
            )
            row.append(relative_energy(trajectory)[-1])
        rows.append(row)

    experiment.table(
        "stability-limits",
        rows,
        columns=[("steps per period", "", ".1f"), ("omega dt", "", ".3f")]
        + [(f"{i.name}, energy / initial", "", ".2e") for i in INTEGRATORS],
        caption="Energy relative to the start after one hundred steps, at three "
        "steps near the stability limits.",
    )


def throw_with_drag(experiment: Experiment) -> None:
    """Exercise 2: the position error of a throw with linear drag after two
    seconds, for velocity Verlet and Runge-Kutta; record the table."""
    drag_mass, b = 0.5, 0.25  # kg, kg/s: time constant 2 s
    thrown = State(t=0.0, x=[0.0, 0.0], v=[12.0, 15.0])
    with_drag = newton(drag_mass, weight(drag_mass, [0.0, -g]), linear_drag(b))
    duration = 2.0  # s
    exact_throw = fall_with_linear_drag(thrown, drag_mass, b, [0.0, -g], duration)

    previous = {}
    rows = []
    for n_steps in (20, 40, 80, 160, 320):
        row = [n_steps]
        for integrator in INTEGRATORS[2:]:
            trajectory = simulate(
                thrown, with_drag, duration / n_steps, n_steps, step=integrator.step
            )
            error = np.linalg.norm(trajectory.x[-1] - exact_throw.x[0])
            order = (
                np.log2(previous[integrator.name] / error)
                if integrator.name in previous
                else None
            )
            previous[integrator.name] = error
            row += [error, order]
        rows.append(row)

    experiment.table(
        "throw-with-drag",
        rows,
        columns=[("steps", "", "d")]
        + [
            column
            for integrator in INTEGRATORS[2:]
            for column in (
                (f"{integrator.name} error", "m", ".2e"),
                ("order", "", ".2f"),
            )
        ],
        caption="Position error after two seconds of a throw with linear drag, "
        "with the observed order.",
    )


def equal_cost(experiment: Experiment) -> dict:
    """Exercise 3: the largest error over two periods when every method has
    two hundred calls per period; record the table."""
    budget = 200  # calls per period
    equal_cost = {}
    rows = []
    for integrator in INTEGRATORS:
        steps_per_period = budget // integrator.evaluations
        trajectory, calls = run_method(integrator, steps_per_period, 2)
        equal_cost[integrator.name] = state_error(trajectory)
        rows.append(
            (integrator.name, steps_per_period, calls, equal_cost[integrator.name])
        )

    experiment.table(
        "equal-cost",
        rows,
        columns=[
            ("method", "", ""),
            ("steps per period", "", "d"),
            ("calls", "", "d"),
            ("largest error", "m", ".1e"),
        ],
        caption="Largest error over two periods when every method has the same "
        "number of calls per period.",
    )
    return equal_cost


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("stability-steps", 2 * np.pi / (2 * np.sqrt(2)), ".1f")
    experiment.figure("fig-update-orderings", draw_update_orderings)
    methods(experiment)

    final = after_three_periods(experiment)
    experiment.number("omega", omega, ".0f")
    experiment.number("period", period, ".3f")
    experiment.number("euler-final", final["explicit Euler"], ".1f")
    experiment.number("verlet-departure", abs(final["velocity Verlet"] - 1), ".1e")
    experiment.number("rk4-loss-ppm", 1e6 * (1 - final["Runge-Kutta 4"]), ".1f")
    experiment.figure("fig-integrators-phase-space", draw_integrators_phase_space)

    errors = error_orders(experiment)
    experiment.number(
        "euler-over-symplectic",
        errors["explicit Euler"][0] / errors["symplectic Euler"][0],
        ".0f",
    )
    experiment.figure(
        "fig-integrators-convergence", partial(draw_integrators_convergence, errors)
    )

    experiment.number("omega-dt-20", 2 * np.pi / 20, ".3f")
    experiment.figure("fig-integrators-energy", draw_integrators_energy)
    symplectic, verlet, modified_se, modified_vv, rk4_factor = energy_formulas(
        experiment
    )
    experiment.number(
        "modified-spread", max(spread(modified_se), spread(modified_vv)), ".0e"
    )
    experiment.number("symplectic-lowest", np.min(relative_energy(symplectic)), ".4f")
    experiment.number("symplectic-highest", np.max(relative_energy(symplectic)), ".4f")
    experiment.number("z", z, ".2f")
    experiment.number("verlet-lowest", np.min(relative_energy(verlet)), ".4f")
    experiment.number("verlet-highest", np.max(relative_energy(verlet)), ".4f")
    experiment.number("verlet-band", z**2 / 4, ".3f")
    experiment.number("rk4-loss-per-step-ppm", 1e6 * (1 - rk4_factor), ".1f")
    experiment.number("long-n", long_n)
    experiment.number(
        "euler-digits",
        f"{int(1000 * 32 * np.log10(1 + (2 * np.pi / 32) ** 2))}",
    )

    long_runs, long_lowest = long_run_energy_bands(experiment)
    cost = calls_for_one_millimetre(experiment, errors)
    for name, label in (
        ("Runge-Kutta 4", "rk4"),
        ("velocity Verlet", "verlet"),
        ("symplectic Euler", "symplectic"),
        ("explicit Euler", "euler"),
    ):
        experiment.number(f"cost-{label}", cost[name])
    experiment.number("omega-dt-4", 2 * np.pi / 4, ".1f")

    # region: explorer
    explorer = explorer_data(mass=mass, k=k)
    experiment.widget("integrator-explorer", explorer)
    # endregion: explorer
    experiment.figure(
        "fig-integrator-explorer", partial(draw_integrator_explorer, explorer)
    )
    experiment.number("default-steps", STEPS_PER_PERIOD[default])
    explorer_tables(experiment, explorer)

    stability_limits(experiment)
    experiment.number("verlet-long-error", long_runs["velocity Verlet"], ".2f")
    experiment.number(
        "verlet-lowest-per-cent", 100 * (1 - long_lowest["velocity Verlet"]), ".1f"
    )
    throw_with_drag(experiment)

    errors_at_equal_cost = equal_cost(experiment)
    experiment.number(
        "symplectic-over-verlet",
        errors_at_equal_cost["symplectic Euler"]
        / errors_at_equal_cost["velocity Verlet"],
        ".0f",
    )
    experiment.number(
        "verlet-over-rk4",
        errors_at_equal_cost["velocity Verlet"] / errors_at_equal_cost["Runge-Kutta 4"],
        ".0f",
    )
    return experiment


if __name__ == "__main__":
    main(run)
