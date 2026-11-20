"""The part of the experiment of lesson D8 (MD4) that tests the choice of
state variables (F147; ``pbc.discovery.state_selection``).

Two equal masses on springs, coupled by a third spring; the camera tracks
the first mass only. The equation search on the state of that mass, its
position and velocity, returns a short equation that is wrong, and nothing
in the regression says so. The state test finds moments at which the
position and the velocity of the first mass nearly agree and its
acceleration does not; the search on the state of both masses keeps exactly
the true terms. The experiment of the lesson
(``pbc.mechanics.experiments.discovering_differential_equations``) calls
``extend``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp

from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.equations import central_differences
from pbc.discovery.state_selection import (
    APART,
    RADIUS,
    SMOOTHNESS,
    Found,
    search,
    state_test,
)
from pbc.experiment import Experiment
from pbc.figure_language import figsize, figure_style, finish
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.integrators import rk4_step

# region: coupled
STIFFNESS = 4.0  # k / m of each mass's own spring, 1/s²
COUPLING = 1.5  # k_c / m of the spring between the masses, 1/s²
DT = 0.01  # s, the sampling interval
DURATION = 10.0  # s
# x1 (m), v1 (m/s), x2 (m), v2 (m/s): four starts, as for the damped oscillator
STARTS = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 2.0, 0.0, 0.0),
    (-0.5, 1.0, 1.0, 0.0),
    (2.0, -1.0, 0.0, 1.0),
)
HELD_OUT = (3.0, -2.0, -1.0, 0.0)  # outside every training orbit
DEGREE = 3  # every product of the state's variables up to the third power
# endregion: coupled
ONE_MASS = ("x1", "v1")
TWO_MASSES = ("x1", "v1", "x2", "v2")
TRUE = {"x1": -(STIFFNESS + COUPLING), "x2": COUPLING}


def coupled(t: float, x: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The true accelerations (m/s²) of the two masses."""
    return np.array(
        [
            -(STIFFNESS + COUPLING) * x[0] + COUPLING * x[1],
            -(STIFFNESS + COUPLING) * x[1] + COUPLING * x[0],
        ]
    )


def recorded(start) -> tuple[np.ndarray, np.ndarray]:
    """The positions (m) of both masses every ``DT`` over ``DURATION``,
    simulated with the fourth-order Runge-Kutta method from ``start``."""
    x1, v1, x2, v2 = start
    motion = simulate(
        State(0.0, [x1, x2], [v1, v2]),
        coupled,
        DT,
        round(DURATION / DT),
        step=rk4_step,
    )
    return motion.x[:, 0], motion.x[:, 1]


def samples() -> tuple[np.ndarray, ...]:
    """The state of both masses and their accelerations at every interior
    sample of the four orbits, from central differences of the positions,
    with the orbit and the time (s) of each sample."""
    states, first, second, orbits, times = [], [], [], [], []
    for orbit, start in enumerate(STARTS):
        one, two = (central_differences(x, DT) for x in recorded(start))
        states.append(np.column_stack([one.x, one.v, two.x, two.v]))
        first.append(one.a)
        second.append(two.a)
        orbits.append(np.full(len(one.a), orbit))
        times.append(DT * np.arange(1, len(one.a) + 1))
    return (
        np.vstack(states),
        np.concatenate(first),
        np.concatenate(second),
        np.concatenate(orbits),
        np.concatenate(times),
    )


def integrate_state(accelerations, start, t: np.ndarray) -> np.ndarray:
    """The position of the first mass at the times ``t`` (s) under the found
    equations ``accelerations``, one per tracked mass, each a function of the
    state's values, from the matching entries of ``start``."""
    count = len(accelerations)

    def rate(_: float, y: np.ndarray) -> np.ndarray:
        values = y.reshape(1, -1)
        a = [float(f(values)[0]) for f in accelerations]
        velocities = y[1::2]
        out = np.empty_like(y)
        out[0::2] = velocities
        out[1::2] = a
        return out

    y0 = np.array(start[: 2 * count], dtype=float)
    solution = solve_ivp(rate, (t[0], t[-1]), y0, t_eval=t, rtol=1e-10, atol=1e-12)
    if not solution.success:
        raise RuntimeError(f"the integration failed: {solution.message}")
    return solution.y[0]


def two_states(
    values, a1, a2, orbits, times
) -> dict[str, tuple[list[Found], object, float]]:
    """The search and the state test on the state of the first mass and on
    the state of both, with the largest error of the first mass's position
    from the held-out start over the duration. ``values`` holds x1, v1, x2,
    v2 at every sample, ``a1`` and ``a2`` the accelerations of the masses,
    ``orbits`` and ``times`` the orbit and the time (s) of each sample."""
    t = np.arange(round(DURATION / DT) + 1) * DT
    truth = recorded(HELD_OUT)[0]
    found = {}
    for names, targets in ((ONE_MASS, (a1,)), (TWO_MASSES, (a1, a2))):
        columns = values[:, : len(names)]
        equations = [search(names, columns, a, DEGREE) for a in targets]
        test = state_test(columns, a1, orbits, times)
        path = integrate_state([e.acceleration for e in equations], HELD_OUT, t)
        found[names] = (equations, test, float(np.max(np.abs(path - truth))))
    return found


def draw_missing_state(t: np.ndarray, paths: dict[str, np.ndarray]) -> Figure:
    """The position of the first mass from the held-out start: the truth and
    the motion of the found equations of each state."""
    styles = ("-", "--", ":")
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=3))
        for i, (label, path) in enumerate(paths.items()):
            ax.plot(t, path, color=FIGURE_COLOURS[i], linestyle=styles[i], label=label)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("position of the\nfirst mass (m)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def extend(experiment: Experiment):
    """The choice of state variables, for the lesson's page;
    returns the drawing of its figure, which the lesson's experiment
    records."""
    values, a1, a2, orbits, times = samples()
    found = two_states(values, a1, a2, orbits, times)
    size = np.sqrt((a1**2).mean())
    rows = []
    for names, (equations, test, error) in found.items():
        first = equations[0]
        rows.append(
            (
                ", ".join(names),
                first.formula(),
                100 * first.residual / size,
                test.pairs,
                test.largest,
                error,
            )
        )
    experiment.table(
        "state-selection",
        rows,
        columns=[
            ("state", "", "s"),
            ("found equation of the first mass", "", "s"),
            ("residual", "% of rms acceleration", ".2g"),
            ("pairs from separate visits", "", "d"),
            ("largest acceleration difference", "rms acceleration", ".2g"),
            ("largest held-out error", "m", ".2g"),
        ],
        caption="The search and the state test on two choices of state, on the"
        " four orbits of the coupled masses: the equation found for the"
        " acceleration of the first mass, the root-mean-square of its residual,"
        " the pairs of samples closer than the radius of the test from separate"
        f" visits (different orbits, or one orbit at least {APART:g} s apart),"
        " the largest difference of their accelerations, and the largest error"
        " of the first"
        " mass's position from the held-out start over ten seconds, to two"
        " significant digits.",
    )
    (one, one_test, one_error), (two, two_test, two_error) = found.values()
    experiment.number("radius", RADIUS, "g")
    experiment.number("apart", APART, "g")
    experiment.number("two-mass-pairs", two_test.pairs, "d")
    experiment.number("smoothness-limit", SMOOTHNESS * RADIUS, "g")
    experiment.number("one-mass-found", one[0].formula())
    experiment.number("one-mass-terms", len(one[0].coefficients))
    experiment.number("one-mass-test", "passes" if one_test.passes else "fails")
    experiment.number("one-mass-largest", one_test.largest, ".2f")
    experiment.number("two-mass-test", "passes" if two_test.passes else "fails")
    experiment.number("two-mass-found", two[0].formula())
    experiment.number(
        "two-mass-recovered",
        "keeps exactly the true terms"
        if set(two[0].coefficients) == set(TRUE)
        and all(abs(two[0].coefficients[k] / c - 1) < 1e-3 for k, c in TRUE.items())
        else "does not keep exactly the true terms",
    )
    if one_test.witness is not None:
        i, j = one_test.witness
        experiment.number("witness-x", values[i, 0], ".3f")
        experiment.number("witness-v", values[i, 1], ".3f")
        experiment.number("witness-a-first", a1[i], ".2f")
        experiment.number("witness-a-second", a1[j], ".2f")
        experiment.number("witness-x2-first", values[i, 2], ".2f")
        experiment.number("witness-x2-second", values[j, 2], ".2f")
    experiment.number("one-mass-held-out", one_error, ".2g")
    experiment.number("two-mass-held-out", two_error, ".1e")
    t = np.arange(round(DURATION / DT) + 1) * DT
    paths = {
        "true motion": recorded(HELD_OUT)[0],
        "found equation, state x1, v1": integrate_state(
            [one[0].acceleration], HELD_OUT, t
        ),
        "found equations, state of both masses": integrate_state(
            [e.acceleration for e in two], HELD_OUT, t
        ),
    }
    return partial(draw_missing_state, t, paths)
