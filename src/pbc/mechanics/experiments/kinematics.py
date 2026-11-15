"""The experiment of the lesson "Kinematics as a program".

A ball thrown straight up and a cart on a shaking table, simulated with
explicit Euler (``pbc.mechanics.kinematics``) and compared with the exact
motion. Run it as a program to write the figures and numbers of the page:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.kinematics out
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g  # standard gravity, m/s^2

from pbc.authoring.diagrams import arrow, canvas, state_box, text
from pbc.experiment import Experiment, main
from pbc.mechanics.kinematics import State, Trajectory, constant_acceleration, simulate

# region: setup
# Released above the ground (x in m) and moving upward (v in m/s).
launch = State(t=0.0, x=1.5, v=12.0)
dt = 0.1  # time step, s
n_steps = 24
# endregion: setup
duration = dt * n_steps  # s
# The time steps of the convergence study: the same duration, the number of
# steps doubled each time.
step_counts = [n_steps * 2**k for k in range(6)]

# The cart on a shaking table, from rest.
# region: cart
a0 = 3.0  # amplitude of the acceleration, m/s^2
omega = 2.0  # angular frequency, rad/s
rest = State(t=0.0, x=0.0, v=0.0)
# endregion: cart


def free_fall(t):
    return -g


def ball(t):
    return float(constant_acceleration(launch, -g, t).x)


def shaking(t):
    return a0 * np.cos(omega * t)


def cart(t):
    return rest.x + a0 / omega**2 * (1.0 - np.cos(omega * t))


def draw_state_and_update() -> Figure:
    """The state and the update rule, as a sketch."""
    fig, ax = canvas(6.4, 2.2, (0, 10), (0, 3.4))
    state_box(ax, (1.7, 1.7), "state $n$\n" r"$t_n,\ x_n,\ v_n$", width=3.0, height=1.5)
    state_box(
        ax,
        (8.3, 1.7),
        "state $n+1$\n" r"$t_{n+1},\ x_{n+1},\ v_{n+1}$",
        width=3.0,
        height=1.5,
        colour=1,
    )
    arrow(ax, (3.3, 1.7), (6.7, 1.7), colour=2)
    text(ax, (5.0, 2.35), "update rule", colour=2)
    text(ax, (5.0, 1.05), r"one time step $\Delta t$", colour=2)
    return fig


def thrown_ball(experiment: Experiment) -> tuple[Trajectory, Trajectory]:
    """Simulate the thrown ball and evaluate the exact motion at the same
    instants; record the table of every fourth step."""
    euler = simulate(launch, free_fall, dt, n_steps)
    exact = constant_acceleration(launch, -g, euler.t)

    experiment.table(
        "thrown-ball",
        [
            (euler.t[i], euler.x[i], exact.x[i], euler.v[i], exact.v[i])
            for i in range(0, n_steps + 1, 4)
        ],
        columns=[
            ("t", "s", ".1f"),
            ("x Euler", "m", ".3f"),
            ("x exact", "m", ".3f"),
            ("v Euler", "m/s", ".3f"),
            ("v exact", "m/s", ".3f"),
        ],
        caption="Height and velocity of the thrown ball, simulated and exact, "
        "every fourth step; positions and velocities to three decimals.",
    )
    return euler, exact


def draw_ball_thrown_up(euler: Trajectory) -> Figure:
    """The height of the ball: explicit Euler against the exact motion."""
    fine = np.linspace(0.0, euler.t[-1], 241)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        fine,
        constant_acceleration(launch, -g, fine).x,
        color="#00429d",
        label="exact",
    )
    ax.plot(
        euler.t,
        euler.x,
        color="#93003a",
        linestyle="--",
        marker="o",
        markersize=3,
        label=f"explicit Euler, time step {dt} s",
    )
    ax.set_xlabel("time (s)")
    ax.set_ylabel("height (m)")
    ax.legend()
    return fig


def final_error(acceleration, exact_position, n):
    """Error of the last simulated position, for n steps over the duration."""
    end = simulate(launch, acceleration, duration / n, n)
    return end.x[-1] - exact_position(end.t[-1])


def halving(experiment: Experiment) -> np.ndarray:
    """The error of the final height for each time step; record its table."""
    ball_errors = np.array([final_error(free_fall, ball, n) for n in step_counts])

    experiment.table(
        "halving",
        [
            (
                n,
                duration / n,
                ball_errors[i],
                ball_errors[i - 1] / ball_errors[i] if i else None,
            )
            for i, n in enumerate(step_counts)
        ],
        columns=[
            ("steps", "", "d"),
            ("time step", "s", ".6f"),
            ("error", "m", ".6f"),
            ("previous error / error", "", ".4f"),
        ],
        caption="Error of the final height of the thrown ball for each time "
        "step, to six decimals, and the ratio to the error before the halving.",
    )
    return ball_errors


def cart_error(n):
    end = simulate(rest, shaking, duration / n, n)
    return end.x[-1] - cart(end.t[-1])


def shaking_cart(experiment: Experiment) -> tuple[np.ndarray, np.ndarray]:
    """The error of the cart's final position for each time step, and the
    observed order; record their table."""
    cart_errors = np.array([cart_error(n) for n in step_counts])
    orders = np.log2(cart_errors[:-1] / cart_errors[1:])

    experiment.table(
        "shaking-cart",
        [
            (n, duration / n, cart_errors[i], orders[i - 1] if i else None)
            for i, n in enumerate(step_counts)
        ],
        columns=[
            ("steps", "", "d"),
            ("time step", "s", ".6f"),
            ("error", "m", ".6f"),
            ("observed order", "", ".3f"),
        ],
        caption="Error of the final position of the cart for each time step, "
        "to six decimals, and the observed order of the method to three decimals.",
    )
    return cart_errors, orders


def draw_error_against_time_step(
    ball_errors: np.ndarray, cart_errors: np.ndarray
) -> Figure:
    """The error of the final position against the time step, log-log."""
    steps = duration / np.array(step_counts)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.loglog(
        steps, np.abs(ball_errors), color="#00429d", marker="o", label="thrown ball"
    )
    ax.loglog(
        steps,
        np.abs(cart_errors),
        color="#93003a",
        marker="s",
        linestyle="--",
        label="cart on a shaking table",
    )
    ax.loglog(steps, steps, color="#555555", linestyle=":", label="slope 1")
    ax.set_xlabel("time step (s)")
    ax.set_ylabel("size of the error (m)")
    ax.legend()
    return fig


def steps_for_tolerance(tolerance):
    """Exercise 1: the largest time step whose error stays within
    ``tolerance`` (m), the whole number of steps it takes, and their error."""
    largest_step = 2 * tolerance / (g * duration)
    n_needed = int(np.ceil(duration / largest_step))
    error_needed = final_error(free_fall, ball, n_needed)
    return largest_step, n_needed, error_needed


# Exercise 2: an acceleration that grows linearly in time.
# region: jerk
jerk = 2.0  # m/s^3
end_time = 3.0  # s
# endregion: jerk


def growing(t):
    return jerk * t


def jerk_errors(n):
    end = simulate(rest, growing, end_time / n, n)
    return (
        end.v[-1] - jerk * end.t[-1] ** 2 / 2,
        end.x[-1] - jerk * end.t[-1] ** 3 / 6,
    )


def constant_jerk(experiment: Experiment) -> None:
    """Exercise 2: the velocity and position errors at ``end_time`` and the
    observed order; record their table."""
    counts = [30 * 2**k for k in range(5)]
    errors = np.array([jerk_errors(n) for n in counts])
    jerk_orders = np.log2(errors[:-1, 1] / errors[1:, 1])

    experiment.table(
        "constant-jerk",
        [
            (n, errors[i, 0], errors[i, 1], jerk_orders[i - 1] if i else None)
            for i, n in enumerate(counts)
        ],
        columns=[
            ("steps", "", "d"),
            ("velocity error", "m/s", ".6f"),
            ("position error", "m", ".6f"),
            ("observed order", "", ".3f"),
        ],
        caption="Velocity and position error of the cart with growing "
        "acceleration at t = 3 s, to six decimals, and the observed order.",
    )


def second_order_step(state, acceleration, dt):
    """Exercise 3: an Euler step that keeps the term of the acceleration in
    the position."""
    a = acceleration(state.t)
    return State(
        t=state.t + dt,
        x=state.x + state.v * dt + 0.5 * a * dt**2,
        v=state.v + a * dt,
    )


def improved_ball():
    """Exercise 3: the thrown ball with ``second_order_step``; the error of
    its final height."""
    state = launch
    for _ in range(n_steps):
        state = second_order_step(state, free_fall, dt)
    return state, state.x - ball(state.t)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-state-and-update", draw_state_and_update)

    euler, exact = thrown_ball(experiment)
    experiment.number("g", g)
    experiment.number("end-time", euler.t[-1], ".1f")
    experiment.number("ball-gap", euler.x[-1] - exact.x[-1], ".3f")
    experiment.number("predicted-lag", g * euler.t[-1] * dt / 2, ".3f")
    # The first step by hand: the state after one step, simulated and exact.
    experiment.number("one-step-time", euler.t[1], ".1f")
    experiment.number("one-step-x", euler.x[1], ".3f")
    experiment.number("one-step-exact-x", exact.x[1], ".3f")
    experiment.number("one-step-v", euler.v[1], ".3f")
    experiment.number("one-step-exact-v", exact.v[1], ".3f")
    experiment.number("one-step-gap", euler.x[1] - exact.x[1], ".3f")
    experiment.number("one-step-predicted", g * dt**2 / 2, ".3f")
    experiment.figure("fig-ball-thrown-up", partial(draw_ball_thrown_up, euler))

    ball_errors = halving(experiment)
    spacing = np.spacing(np.max(np.abs(euler.x)))  # resolution of a stored height, m
    experiment.number("last-ratio", ball_errors[-2] / ball_errors[-1], ".4f")
    experiment.number("spacing", spacing, ".1e")
    experiment.number("smallest-error", abs(ball_errors[-1]), ".1e")
    experiment.number("error-over-spacing", abs(ball_errors[-1]) / spacing, ".1e")

    cart_errors, orders = shaking_cart(experiment)
    experiment.number("last-order", orders[-1], ".3f")
    experiment.figure(
        "fig-error-against-time-step",
        partial(draw_error_against_time_step, ball_errors, cart_errors),
    )

    experiment.number("duration", duration, ".1f")
    largest_step, n_needed, error_needed = steps_for_tolerance(1e-3)
    experiment.number("largest-step-us", largest_step * 1e6, ".1f")
    experiment.number("steps-needed", n_needed)
    experiment.number("error-needed-mm", error_needed * 1e3, ".5f")
    experiment.number("n-steps", n_steps)

    constant_jerk(experiment)

    experiment.number("dt", dt)
    state, improved_error = improved_ball()
    experiment.number("improved-time", state.t, ".1f")
    experiment.number("improved-error", abs(improved_error), ".9f")
    experiment.number("first-error", ball_errors[0], ".3f")
    return experiment


if __name__ == "__main__":
    main(run)
