"""The experiment of the lesson "Symbolic regression for physical laws".

The period of a simulated pendulum, measured over its length, the gravity,
its mass, and its amplitude, and an exhaustive search over power laws of
the four (``pbc.discovery.symbolic``): the recovery of the small-angle law
from clean data, its test on held-out pendulums, a variable the data do not
vary, a law outside the grammar, and the noise at which the search stops
finding the law. Run it as a program to write the figures and numbers of
the page:

    uv run --locked --no-dev python -m pbc.mechanics.experiments.symbolic_regression out
"""

from collections import Counter
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.symbolic import PowerLaw, Search, noise_floor, power_law_search
from pbc.experiment import Experiment, main
from pbc.mechanics.dynamics import State, newton, simulate
from pbc.mechanics.integrators import rk4_step
from pbc.mechanics.pendulum import pendulum_force, pendulum_period

# region: world
LENGTHS = (0.2, 2.0)  # m
GRAVITIES = (1.6, 25.0)  # m/s², from the Moon to Jupiter
MASSES = (0.1, 2.0)  # kg
AMPLITUDES = (0.02, 0.1)  # rad
SAMPLES = 24
RESOLUTION = 1e-3  # the relative resolution of a period without added noise
SEED = 0
# endregion: world
# region: law
TRUE_SHAPE = (0.5, -0.5, 0.0, 0.0)  # L^(1/2) g^(-1/2): the small-angle law
TOLERANCE = 0.005  # relative, on the constant 2 pi
# endregion: law
# region: held-out
HELD_OUT = (  # length (m), gravity (m/s²), amplitude (rad)
    (5.0, 9.81, 0.05),
    (20.0, 3.7, 0.05),
    (1.0, 9.81, 0.3),
    (1.0, 9.81, 0.8),
    (1.0, 9.81, 1.5),
)
# endregion: held-out
# region: noise
NOISE_LEVELS = (0.001, 0.01, 0.03, 0.1, 0.2, 0.3, 0.5)  # relative
SEEDS = 20
# endregion: noise
EARTH = 9.80665  # m/s²
WIDE_AMPLITUDES = (0.02, 1.2)  # rad


def simulated_period(
    length: float, gravity: float, mass: float, amplitude: float
) -> float:
    """The period in s of a pendulum released from rest at ``amplitude``
    (rad), simulated with the fourth-order Runge-Kutta method at 400 steps
    per small-angle period: twice the time until the bob is at rest on the
    other side, where its velocity changes sign."""
    acceleration = newton(mass, pendulum_force(mass, length, gravity))
    steps = 400
    dt = 2 * np.pi * np.sqrt(length / gravity) / steps
    motion = simulate(
        State(0.0, [length * amplitude], [0.0]),
        acceleration,
        dt,
        4 * steps,
        step=rk4_step,
        until=lambda state: state.v[0] > 0,
    )
    v_before, v_after = motion.v[-2, 0], motion.v[-1, 0]
    half_period = motion.t[-2] + dt * v_before / (v_before - v_after)
    return float(2 * half_period)


def pendulums(
    seed: int = SEED,
    gravities: tuple[float, float] = GRAVITIES,
    amplitudes: tuple[float, float] = AMPLITUDES,
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """``SAMPLES`` pendulums drawn uniformly within the ranges, and their
    simulated periods (s)."""
    rng = np.random.default_rng(seed)
    variables = {
        "L": rng.uniform(*LENGTHS, SAMPLES),
        "g": rng.uniform(*gravities, SAMPLES),
        "m": rng.uniform(*MASSES, SAMPLES),
        "theta0": rng.uniform(*amplitudes, SAMPLES),
    }
    periods = np.array(
        [simulated_period(*p) for p in zip(*variables.values(), strict=True)]
    )
    return variables, periods


def right_form(search: Search) -> bool:
    """Did the search choose the form of the small-angle law?"""
    return search.chosen is not None and search.chosen.exponents == TRUE_SHAPE


def recovered(search: Search) -> bool:
    """Did the search choose the small-angle law, with its constant within
    the tolerance of 2 pi?"""
    return (
        right_form(search) and abs(search.chosen.constant / (2 * np.pi) - 1) < TOLERANCE
    )


def clean_search(experiment: Experiment) -> tuple[dict, np.ndarray, Search]:
    """The search on the clean periods; record the best form of each
    complexity."""
    variables, periods = pendulums()
    search = power_law_search(variables, periods, RESOLUTION)
    experiment.table(
        "pareto",
        [
            (
                f.complexity,
                f.formula(),
                f.chi2,
                "yes" if f.chi2 <= search.limit else "no",
            )
            for f in search.pareto()
        ],
        columns=[
            ("complexity", "", "d"),
            ("best form (period in s)", "", "s"),
            ("chi-square", "", ".3g"),
            ("consistent", "", "s"),
        ],
        caption="The best power law of each complexity on the clean periods, with"
        " the chi-square at the stated resolution, to three significant digits.",
    )
    return variables, periods, search


def simulated_check(variables: dict, periods: np.ndarray) -> float:
    """The largest relative difference between the simulated periods and the
    exact period of the pendulum (``pendulum_period``)."""
    exact = [
        pendulum_period(length, amplitude, gravity)
        for length, gravity, amplitude in zip(
            variables["L"], variables["g"], variables["theta0"], strict=True
        )
    ]
    return float(np.max(np.abs(periods / np.array(exact) - 1)))


def held_out(experiment: Experiment, form: PowerLaw) -> list[float]:
    """The chosen form against pendulums outside the probed ranges; record
    the table and return the relative errors."""
    rows, errors = [], []
    for length, gravity, amplitude in HELD_OUT:
        period = simulated_period(length, gravity, 1.0, amplitude)
        predicted = float(
            form.predict({"L": length, "g": gravity, "m": 1.0, "theta0": amplitude})
        )
        errors.append(predicted / period - 1)
        rows.append((length, gravity, amplitude, period, predicted, 100 * errors[-1]))
    experiment.table(
        "held-out",
        rows,
        columns=[
            ("length", "m", "g"),
            ("gravity", "m/s²", "g"),
            ("amplitude", "rad", "g"),
            ("simulated period", "s", ".4f"),
            ("predicted period", "s", ".4f"),
            ("error", "%", ".2f"),
        ],
        caption="The chosen form on held-out pendulums of mass 1 kg: two outside"
        " the probed lengths and gravities at small amplitude, three at"
        " amplitudes beyond the probed ones. Periods to four decimals.",
    )
    return errors


def earth_only(experiment: Experiment) -> tuple[Search, float]:
    """The search on pendulums that all swing at the gravity of the Earth;
    record the forms the data cannot tell apart, and return the search and
    the error of its choice on the Moon."""
    variables, periods = pendulums(gravities=(EARTH, EARTH))
    search = power_law_search(variables, periods, RESOLUTION)
    experiment.table(
        "earth-rivals",
        [
            (f.formula(), f.chi2)
            for f in sorted(search.rivals, key=lambda f: (f.complexity, f.exponents))
        ],
        columns=[("form (period in s)", "", "s"), ("chi-square", "", ".3f")],
        caption="Every form within one unit of chi-square of the best, on pendulums"
        " that all swing at the gravity of the Earth; chi-square to three decimals.",
    )
    moon = {"L": 1.0, "g": 1.62, "m": 1.0, "theta0": 0.05}
    period = simulated_period(1.0, 1.62, 1.0, 0.05)
    error = float(search.chosen.predict(moon)) / period - 1
    return search, error


def wide_amplitudes() -> Search:
    """The search on pendulums released at amplitudes up to 1.2 rad, where
    the period depends on the amplitude in a way no power law follows."""
    variables, periods = pendulums(amplitudes=WIDE_AMPLITUDES)
    return power_law_search(variables, periods, RESOLUTION)


def noisy_periods(periods: np.ndarray, noise: float, seed: int) -> np.ndarray:
    """The periods with a relative noise of standard deviation ``noise``: each
    multiplied by exp(noise times a standard normal draw)."""
    rng = np.random.default_rng(1000 + seed)
    return periods * np.exp(noise * rng.standard_normal(periods.size))


def noise_sweep(
    experiment: Experiment, variables: dict, periods: np.ndarray
) -> list[tuple[float, int, int, int]]:
    """The search at each noise level on ``SEEDS`` noisy copies of the clean
    periods; record how often it chooses the form of the law, how far its
    constant then is from 2 pi, and what it chooses otherwise."""
    outcomes = []
    rows = []
    for noise in NOISE_LEVELS:
        searches = [
            power_law_search(variables, noisy_periods(periods, noise, seed), noise)
            for seed in range(SEEDS)
        ]
        right = [s.chosen for s in searches if right_form(s)]
        empty = sum(s.chosen is None for s in searches)
        others = Counter(
            s.chosen.shape
            for s in searches
            if s.chosen is not None and not right_form(s)
        )
        wrong = sum(others.values())
        common = others.most_common(1)[0][0] if others else ""
        scatter = (
            100
            * float(
                np.sqrt(np.mean([(f.constant / (2 * np.pi) - 1) ** 2 for f in right]))
            )
            if right
            else None
        )
        outcomes.append((noise, len(right), wrong, empty))
        rows.append(
            (
                100 * noise,
                len(right),
                scatter,
                100 * noise / np.sqrt(SAMPLES),
                wrong,
                common,
            )
        )
    experiment.table(
        "noise-sweep",
        rows,
        columns=[
            ("noise", "%", "g"),
            (f"form of the law chosen (of {SEEDS})", "", "d"),
            ("error of its constant", "%", ".2f"),
            ("expected error of the constant", "%", ".2f"),
            ("another form chosen", "", "d"),
            ("most frequent other form", "", "s"),
        ],
        caption=f"The search on {SEEDS} noisy copies of the periods at each noise"
        " level, the noise known to the search. The error of the constant is the"
        " root-mean-square relative error of 2 pi over the copies where the form"
        " of the law was chosen; the expected error is the noise divided by the"
        " square root of the number of pendulums. Errors to two decimals.",
    )
    return outcomes


def simplest_rival(search: Search) -> PowerLaw:
    """Of the forms simpler than the chosen one, the one the least noise
    makes consistent."""
    simpler = [f for f in search.forms if f.complexity < search.chosen.complexity]
    return min(simpler, key=lambda f: noise_floor(search, f))


def draw_pareto(search: Search) -> Figure:
    """The best chi-square of each complexity, the limit of consistency, and
    the chosen form."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8), constrained_layout=True)
    front = search.pareto()
    ax.semilogy(
        [f.complexity for f in front],
        [f.chi2 for f in front],
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="-",
        label="best form of each complexity",
    )
    ax.axhline(
        search.limit,
        color=FIGURE_COLOURS[1],
        linestyle="--",
        label="limit of consistency",
    )
    chosen = search.chosen
    ax.semilogy(
        [chosen.complexity],
        [chosen.chi2],
        linestyle="none",
        marker="*",
        markersize=16,
        color=FIGURE_COLOURS[2],
        label="chosen: " + chosen.shape,
    )
    for form in front:
        ax.annotate(
            "constant" if form.shape == "1" else form.shape,
            (form.complexity, form.chi2),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )
    ax.set_xticks(range(max(f.complexity for f in front) + 1))
    ax.set_xlabel("complexity of the form")
    ax.set_ylabel("chi-square (dimensionless)")
    ax.legend(loc="upper right", fontsize=8)
    return fig


def draw_noise_sweep(
    outcomes: list[tuple[float, int, int, int]], floor: float
) -> Figure:
    """How often the search chooses the form of the law, and how often
    another form, against the noise; the predicted level where a simpler form
    passes."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6), constrained_layout=True)
    noise = [100 * o[0] for o in outcomes]
    ax.semilogx(
        noise,
        [o[1] / SEEDS for o in outcomes],
        color=FIGURE_COLOURS[0],
        marker="o",
        linestyle="-",
        label="form of the law chosen",
    )
    ax.semilogx(
        noise,
        [o[2] / SEEDS for o in outcomes],
        color=FIGURE_COLOURS[1],
        marker="s",
        linestyle="--",
        label="another form chosen",
    )
    ax.axvline(
        100 * floor,
        color=FIGURE_COLOURS[2],
        linestyle=":",
        label="predicted: a simpler form passes",
    )
    ax.set_xlabel("relative noise of the period (%)")
    ax.set_ylabel(f"fraction of {SEEDS} noisy copies")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="center left", fontsize=8)
    return fig


def units_filter(search: Search) -> list[PowerLaw]:
    """The consistent forms of ``search`` that have the units of a time:
    with L in m, g in m/s², m in kg, and the amplitude without a unit, the
    metres cancel when the exponents of L and g add to zero, the seconds
    remain when the exponent of g is -1/2, and the kilograms cancel when the
    exponent of m is zero."""
    return [
        f
        for f in search.consistent()
        if f.exponents[0] + f.exponents[1] == 0
        and f.exponents[1] == -0.5
        and f.exponents[2] == 0
    ]


def more_samples(experiment: Experiment) -> None:
    """Exercise: the noise sweep with four times as many pendulums."""
    rng = np.random.default_rng(7)
    count = 4 * SAMPLES
    variables = {
        "L": rng.uniform(*LENGTHS, count),
        "g": rng.uniform(*GRAVITIES, count),
        "m": rng.uniform(*MASSES, count),
        "theta0": rng.uniform(*AMPLITUDES, count),
    }
    periods = np.array(
        [simulated_period(*p) for p in zip(*variables.values(), strict=True)]
    )
    rows = []
    for noise in (0.1, 0.2, 0.3, 0.5):
        hits = sum(
            right_form(
                power_law_search(variables, noisy_periods(periods, noise, s), noise)
            )
            for s in range(SEEDS)
        )
        rows.append((100 * noise, hits))
    experiment.table(
        "more-samples",
        rows,
        columns=[
            ("noise", "%", "g"),
            (f"form of the law chosen (of {SEEDS})", "", "d"),
        ],
        caption=f"The search on {count} pendulums instead of {SAMPLES}.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    variables, periods, search = clean_search(experiment)
    chosen = search.chosen
    experiment.number("samples", SAMPLES)
    experiment.number("forms", len(search.forms))
    experiment.number("simulation-error", simulated_check(variables, periods), ".0e")
    experiment.number("chosen", chosen.formula())
    experiment.number("constant", chosen.constant, ".4f")
    experiment.number("two-pi", 2 * np.pi, ".4f")
    experiment.number(
        "constant-error", 100 * abs(chosen.constant / (2 * np.pi) - 1), ".2f"
    )
    experiment.number("tolerance", 100 * TOLERANCE, "g")
    experiment.number(
        "recovered", "recovered" if recovered(search) else "not recovered"
    )
    experiment.number("limit", search.limit, ".1f")
    experiment.number("dof", search.dof)
    experiment.number("consistent-forms", len(search.consistent()))
    experiment.figure("fig-pareto", partial(draw_pareto, search))

    errors = held_out(experiment, chosen)
    experiment.number("held-out-small", 100 * max(abs(e) for e in errors[:2]), ".2f")
    experiment.number("held-out-large", 100 * abs(errors[-1]), ".0f")

    earth, moon_error = earth_only(experiment)
    experiment.number("earth-rivals", len(earth.rivals))
    experiment.number("earth-chosen", earth.chosen.formula())
    experiment.number("moon-error", 100 * abs(moon_error), ".0f")
    in_units = units_filter(earth)
    experiment.number("units-forms", len(in_units))
    experiment.number(
        "units-chosen", min(in_units, key=lambda f: f.complexity).formula()
    )

    wide = wide_amplitudes()
    experiment.number("wide-reason", wide.reason)
    experiment.number("wide-best", wide.forms[0].formula())

    outcomes = noise_sweep(experiment, variables, periods)
    experiment.number("levels", len(NOISE_LEVELS))
    experiment.number("seeds", SEEDS)
    sure = max(noise for noise, right, _, _ in outcomes if right == SEEDS)
    experiment.number("sure-noise", 100 * sure, "g")
    rival = simplest_rival(search)
    floor = noise_floor(search, rival)
    experiment.number("rival", rival.shape)
    experiment.number("floor", 100 * floor, ".0f")
    experiment.figure("fig-noise-sweep", partial(draw_noise_sweep, outcomes, floor))

    more_samples(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
