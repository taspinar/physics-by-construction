"""The experiment of the lesson "Equations from noisy trajectories".

The damped oscillator of the lesson "Discovering differential equations",
its positions with measurement noise added, and the same regression with
two ways to differentiate them: central differences and a Savitzky-Golay
filter (``pbc.discovery.equations``). It measures how the error of a second
difference depends on the time step with and without noise, how often each
way recovers the equation at each noise level over seeded copies, and how
the window of the filter trades noise for bias. Run it as a program to
write the figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.equations_from_noisy_trajectories out
"""

from collections.abc import Callable
from functools import cache, partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.equations import (
    Derivatives,
    Equation,
    central_differences,
    combine,
    polynomial_library,
    savitzky_golay,
    sparse_regression,
)
from pbc.experiment import Experiment, main
from pbc.mechanics.dynamics import State, simulate
from pbc.mechanics.experiments.discovering_differential_equations import (
    DEGREE,
    DT,
    DURATION,
    OMEGA2,
    STARTS,
    TOLERANCE,
    TRUE,
    damped,
    recovered,
)
from pbc.mechanics.integrators import rk4_step

# region: noise
NOISE_LEVELS = (1e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1)  # m
SEEDS = 10
WINDOW = 41  # samples: 0.4 s at the sampling interval of 0.01 s
ORDER = 3  # the degree of the polynomial in the window
# endregion: noise
# region: steps
FINE = 0.001  # s, the step of the reference simulation
STRIDES = (1, 2, 5, 10, 20, 50, 100, 200)  # sampling intervals, in fine steps
STEP_NOISE = (0.0, 1e-7, 1e-5)  # m
# endregion: steps
WINDOWS = (11, 21, 41, 61, 81)
WINDOW_NOISE = (0.0, 1e-3, 1e-2, 3e-2, 1e-1)  # m


@cache
def sampled(x0: float, v0: float, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """The positions (m) and velocities (m/s) every ``dt`` over the duration
    of the damped motion from ``x0`` and ``v0`` (fourth-order Runge-Kutta at
    that step), simulated once for each start and step; the arrays are shared,
    so callers do not change them."""
    motion = simulate(
        State(0.0, [x0], [v0]),
        lambda t, x, v: damped(x, v),
        dt,
        round(DURATION / dt),
        step=rk4_step,
    )
    return motion.x[:, 0], motion.v[:, 0]


def noisy(x: np.ndarray, noise: float, rng: np.random.Generator) -> np.ndarray:
    """``x`` with Gaussian noise of standard deviation ``noise`` (m) added."""
    return x + noise * rng.standard_normal(x.size)


def step_errors() -> dict[float, list[float]]:
    """The root-mean-square error (m/s²) of the central second difference
    against the true acceleration, for each sampling interval and noise."""
    x, v = sampled(*STARTS[0], FINE)
    errors = {}
    for noise in STEP_NOISE:
        rng = np.random.default_rng(5)
        measured = noisy(x, noise, rng)
        errors[noise] = []
        for stride in STRIDES:
            dt = stride * FINE
            data = central_differences(measured[::stride], dt)
            truth = damped(x[::stride][1:-1], v[::stride][1:-1])
            errors[noise].append(float(np.sqrt(((data.a - truth) ** 2).mean())))
    return errors


def draw_step_errors(errors: dict[float, list[float]]) -> Figure:
    """Log-log error of the second difference against the step, one curve
    per noise, with the slope of truncation and the predicted noise of the
    noisiest record as references."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    steps = np.array(STRIDES) * FINE
    styles = [("o", "-", 0), ("s", "--", 1), ("^", "-.", 3)]
    for (noise, error), (marker, line, colour) in zip(
        errors.items(), styles, strict=True
    ):
        ax.loglog(
            steps,
            error,
            marker=marker,
            linestyle=line,
            color=FIGURE_COLOURS[colour],
            label="no noise" if noise == 0 else f"noise {noise:g} m",
        )
    clean = errors[0.0]
    ax.loglog(
        steps,
        clean[-1] * (steps / steps[-1]) ** 2,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="slope 2 (truncation)",
    )
    top = max(errors)
    ax.loglog(
        steps,
        np.sqrt(6) * top / steps**2,
        color=FIGURE_COLOURS[2],
        linestyle=(0, (1, 4)),
        linewidth=2.5,
        label=f"predicted noise for {top:g} m",
    )
    ax.set_ylim(min(clean) / 3, max(max(e) for e in errors.values()) * 3)
    ax.set_xlabel("sampling interval (s)")
    ax.set_ylabel("error of the acceleration (m/s²)")
    ax.legend(loc="upper center", fontsize=8, ncols=2)
    return fig


Differentiator = Callable[[np.ndarray, float], Derivatives]


def differentiators(window: int = WINDOW) -> dict[str, Differentiator]:
    return {
        "central differences": central_differences,
        "Savitzky-Golay": partial(savitzky_golay, window=window, order=ORDER),
    }


def fits(differentiate: Differentiator, noise: float, dt: float = DT) -> list[Equation]:
    """The equation the regression finds, for each seed, from the four orbits
    with noise added to their positions."""
    orbits = [sampled(*s, dt)[0] for s in STARTS]
    terms = polynomial_library(DEGREE)
    found = []
    for seed in range(SEEDS):
        rng = np.random.default_rng(seed)
        data = combine([differentiate(noisy(x, noise, rng), dt) for x in orbits])
        found.append(sparse_regression(terms, data))
    return found


def trials(differentiate: Differentiator, noise: float, dt: float = DT) -> list[bool]:
    """Whether the regression recovers the equation, for each seed."""
    return [recovered(e) for e in fits(differentiate, noise, dt)]


def coefficient_error(equation: Equation) -> float:
    """The largest relative error of a coefficient of the true equation; a
    term the regression dropped is an error of one."""
    return max(abs(equation.coefficients.get(t, 0.0) / c - 1) for t, c in TRUE.items())


def sweep(
    experiment: Experiment,
) -> tuple[dict[str, list[int]], dict[str, list[float]]]:
    """Recoveries and the median coefficient error of both differentiators at
    every noise level; record the table."""
    counts: dict[str, list[int]] = {}
    errors: dict[str, list[float]] = {}
    for name, d in differentiators().items():
        found = [fits(d, noise) for noise in NOISE_LEVELS]
        counts[name] = [sum(recovered(e) for e in f) for f in found]
        errors[name] = [
            float(np.median([coefficient_error(e) for e in f])) for f in found
        ]
    experiment.table(
        "sweep",
        [
            (
                noise,
                *(counts[name][i] for name in counts),
                *(errors[name][i] for name in errors),
            )
            for i, noise in enumerate(NOISE_LEVELS)
        ],
        columns=[
            ("noise", "m", "g"),
            (f"central differences (of {SEEDS})", "", "d"),
            (f"Savitzky-Golay (of {SEEDS})", "", "d"),
            ("central differences, median error", "", ".1e"),
            ("Savitzky-Golay, median error", "", ".1e"),
        ],
        caption=f"How often the regression recovers the equation from {SEEDS}"
        " noisy copies of the four orbits, at each noise of the positions, and"
        " the median over the copies of the largest relative error of a"
        " coefficient of the true equation (one when a term is dropped).",
    )
    return counts, errors


def draw_sweep(counts: dict[str, list[int]], errors: dict[str, list[float]]) -> Figure:
    """The fraction of copies recovered and the median coefficient error
    against the noise, for both differentiators, with the tolerance."""
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6.4, 5.6), sharex=True, constrained_layout=True
    )
    styles = list(zip(("o", "s"), ("-", "--"), FIGURE_COLOURS, strict=False))
    for name, (marker, line, colour) in zip(counts, styles, strict=False):
        style = {"marker": marker, "linestyle": line, "color": colour, "label": name}
        top.semilogx(NOISE_LEVELS, np.array(counts[name]) / SEEDS, **style)
        bottom.loglog(NOISE_LEVELS, errors[name], **style)
    bottom.axhline(TOLERANCE, color="0.3", linestyle=":", label="tolerance")
    top.set_ylabel(f"fraction of {SEEDS} copies recovered")
    top.set_ylim(-0.05, 1.05)
    top.legend(loc="lower left", fontsize=8)
    bottom.set_xlabel("noise of the positions (m)")
    bottom.set_ylabel("median coefficient error (relative)")
    bottom.legend(loc="lower right", fontsize=8)
    return fig


def last_success(counts: list[int]) -> float:
    """The largest noise at which every copy was recovered."""
    return max(n for n, c in zip(NOISE_LEVELS, counts, strict=True) if c == SEEDS)


def windows(experiment: Experiment) -> None:
    """Recoveries of the Savitzky-Golay filter for each window and noise;
    record the table."""
    rows = []
    for window in WINDOWS:
        d = differentiators(window)["Savitzky-Golay"]
        rows.append(
            (window, window * DT, *(sum(trials(d, noise)) for noise in WINDOW_NOISE))
        )
    experiment.table(
        "windows",
        rows,
        columns=[
            ("window", "samples", "d"),
            ("window", "s", ".2f"),
            *((f"noise {noise:g} m", "", "d") for noise in WINDOW_NOISE),
        ],
        caption=f"How often, of {SEEDS} copies, the Savitzky-Golay filter of each"
        " window leads to the equation, at each noise of the positions.",
    )


def clean_bias(window: int) -> float:
    """The largest relative error of a coefficient found from clean
    positions through the filter of ``window`` samples."""
    terms = polynomial_library(DEGREE)
    d = differentiators(window)["Savitzky-Golay"]
    data = combine([d(sampled(*s, DT)[0], DT) for s in STARTS])
    found = sparse_regression(terms, data).coefficients
    true = {"x": -OMEGA2, "v": damped(0.0, 1.0)}
    return max(abs(found.get(t, 0.0) / c - 1) for t, c in true.items())


def drowned(noise: float) -> float:
    """The noise (m/s²) of the central second difference at the sampling
    interval, for a noise of the positions ``noise`` (m): the three samples
    of the difference add their noise with weights 1, -2, 1."""
    return float(np.sqrt(6) * noise / DT**2)


def finer_sampling(experiment: Experiment) -> None:
    """Exercise: half the sampling interval, with the window of the filter
    kept at the same duration."""
    dt = DT / 2
    rows = []
    for noise in (3e-4, 3e-2, 1e-1):
        rows.append(
            (
                noise,
                sum(trials(central_differences, noise)),
                sum(trials(central_differences, noise, dt)),
                sum(trials(differentiators(WINDOW)["Savitzky-Golay"], noise)),
                sum(
                    trials(differentiators(2 * WINDOW - 1)["Savitzky-Golay"], noise, dt)
                ),
            )
        )
    experiment.table(
        "finer-sampling",
        rows,
        columns=[
            ("noise", "m", "g"),
            ("central, 0.01 s", "", "d"),
            ("central, 0.005 s", "", "d"),
            ("filter, 0.01 s", "", "d"),
            ("filter, 0.005 s", "", "d"),
        ],
        caption=f"Recoveries, of {SEEDS} copies, at the sampling interval of the"
        " lesson and at half of it; the filter keeps a window of 0.4 s.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    errors = step_errors()
    experiment.figure("fig-step-errors", partial(draw_step_errors, errors))
    best = {noise: STRIDES[int(np.argmin(e))] * FINE for noise, e in errors.items()}
    experiment.table(
        "best-steps",
        [(noise, best[noise], min(errors[noise])) for noise in STEP_NOISE],
        columns=[
            ("noise", "m", "g"),
            ("best sampling interval", "s", "g"),
            ("its error", "m/s²", ".1e"),
        ],
        caption="The sampling interval with the smallest error of the acceleration"
        " for each noise, and that error to two significant digits.",
    )

    counts, coefficient_errors = sweep(experiment)
    experiment.figure("fig-sweep", partial(draw_sweep, counts, coefficient_errors))
    central = last_success(counts["central differences"])
    filtered = last_success(counts["Savitzky-Golay"])
    experiment.number("central-last", central, "g")
    experiment.number("filter-last", filtered, "g")
    first_fail = min(n for n in NOISE_LEVELS if n > central)
    experiment.number("central-fail", first_fail, "g")
    experiment.number("central-drowned", drowned(first_fail), ".0f")
    x, v = sampled(*STARTS[0], DT)
    experiment.number(
        "rms-acceleration", float(np.sqrt((damped(x, v) ** 2).mean())), ".1f"
    )
    experiment.number("window", WINDOW)
    experiment.number("window-seconds", WINDOW * DT, ".1f")
    experiment.number("bias-window", 100 * clean_bias(WINDOW), ".1f")
    experiment.number("bias-wide", 100 * clean_bias(WINDOWS[-2]), ".1f")
    experiment.number("wide-window", WINDOWS[-2])
    windows(experiment)
    rng = np.random.default_rng(0)
    data = combine(
        [
            savitzky_golay(
                noisy(sampled(*s, DT)[0], NOISE_LEVELS[-1], rng), DT, WINDOW, ORDER
            )
            for s in STARTS
        ]
    )
    experiment.number(
        "loudest", sparse_regression(polynomial_library(DEGREE), data).formula(3)
    )
    experiment.number("loudest-noise", NOISE_LEVELS[-1], "g")
    finer_sampling(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
