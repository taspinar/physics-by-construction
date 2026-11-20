"""The experiment of the lesson "Scientific discovery under measurement noise".

A language model probes a central force through a faulty gauge, with noise,
a hidden zero offset, and faulty readings (``pbc.discovery.noise_lab``); the
build scores its law on distances it never probed: the baselines without a
model, the replay of the recorded run and its score, the calibrated robust
fit to the agent's own readings, the failure analysis of the gauge, and the
degradation of every baseline as the noise grows; and, on a stated
synthetic gauge apart from the agent's, two explanations that the same
readings cannot separate, with the measurement that does. Run it as a
program to
write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discovery_under_noise out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.noise_lab``.
"""

import math
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.data.fit import FitResult, fit_curve
from pbc.data.inverse import profile
from pbc.discovery import comparison, environment_allowlist
from pbc.discovery.baselines import FIT_SIGMAS, consistent
from pbc.discovery.noise_lab import (
    BASELINES,
    BUDGET,
    CONDITION,
    GAUGES,
    MAX_STEPS,
    METHODS,
    REJECT_SIGMAS,
    SIGMA,
    TOLERANCE,
    baselines,
    calibrated_fit,
    degradation,
    environment,
    failure_analysis,
    probes,
    recovered,
    replay_run,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.noise_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/18-discovery-under-noise"
# The noise levels and seeds of the degradation (N; one run per seed).
SIGMAS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
SEEDS = (0, 1, 2, 3, 4)

# region: synthetic
# A synthetic gauge whose truth this page states, apart from the agent's
# hidden one: the inverse-square law read with an offset, no faults.
TRUTH = {"strength": 20.0, "exponent": 2.0, "offset": 0.15}  # N m²/kg, 1, N
MASS = 1.0  # kg, every reading of the first set
DISTANCES = np.linspace(2.0, 4.0, 12)  # m
NULL_DISTANCES = (2.0, 3.0)  # m, the readings at zero mass
FAR = 12.0  # m, where the law of each explanation is compared with the truth
SYNTHETIC_SEED = 0
# endregion: synthetic


def the_baselines(experiment: Experiment):
    """The baselines without a model with the protocol's budget, scored on
    the held-out distances; record the table and return them."""
    results = baselines()
    experiment.table(
        "d10-baselines",
        [
            (
                b.name,
                (b.claim or {}).get("strength"),
                (b.claim or {}).get("exponent"),
                b.held_out_error,
                "yes" if b.success else "no",
                "yes" if recovered(b) else "no",
            )
            for b in results
        ],
        [
            ("method", "", ""),
            ("strength", "N m^p/kg", ".4g"),
            ("exponent", "", ".4f"),
            ("held-out error", "relative", ".2g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
        ],
        "The baselines without a model on the faulty gauge, scored on the"
        " noise-free force at distances beyond the bounds. Sparse"
        " identification states a sum of terms, so its parameters are empty.",
    )
    return results


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d10-score",
        [
            ("probes used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            *(
                (f"claimed {p}", f"{score.claim[p]:.4g}")
                for p in ("strength", "exponent")
            ),
            ("held-out error", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone.",
    )


def the_agents_readings(experiment: Experiment, transcript, score) -> None:
    """The calibrated robust fit to exactly the agent's readings, beside its
    claim and the readings it would drop; record the table and numbers."""
    data = probes(transcript)
    found = calibrated_fit(environment(), data)
    claim = found.result.claim or {}
    experiment.table(
        "d10-agent-readings",
        [
            ("strength", claim.get("strength"), score.claim["strength"]),
            ("exponent", claim.get("exponent"), score.claim["exponent"]),
            ("held-out error", found.result.held_out_error, score.held_out_error),
        ],
        [
            ("quantity", "", ""),
            ("calibrated robust fit to its readings", "", ".4g"),
            ("the agent's claim", "", ".4g"),
        ],
        "The calibrated robust fit to the agent's own readings, beside its claim.",
    )
    experiment.number("agent-fit-consistent", "yes" if found.result.success else "no")
    experiment.number("agent-dropped", len(found.dropped))
    experiment.number(
        "agent-dropped-settings",
        len({tuple(sorted(data.settings[i].items())) for i in found.dropped}),
    )
    experiment.number("agent-readings", len(data.values))
    experiment.number("agent-null-readings", sum(s["mass"] == 0 for s in data.settings))


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines on the held-out distances; record the table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d10-comparison",
        [
            (
                r["who"],
                r["probes"],
                r["held_out_error"],
                "yes" if r["recovered"] else "no",
                r["note"],
            )
            for r in rows
        ],
        [
            ("method", "", ""),
            ("probes", "", "d"),
            ("held-out error", "relative", ".2g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The agent and the baselines, with the same budget, on the held-out distances.",
    )


def _verdict(result) -> str:
    outcome = "recovered" if recovered(result) else "fails"
    return f"{result.held_out_error:.2g} ({outcome})"


def the_failure_analysis(experiment: Experiment) -> None:
    """Every method on the grid of each failure of the gauge, at the
    lesson's noise; record the table."""
    table = failure_analysis()
    experiment.table(
        "d10-failures",
        [
            (
                gauge,
                *(_verdict(table[gauge][m]) for m in METHODS),
            )
            for gauge in GAUGES
        ],
        [("gauge", "", ""), *((m, "", "") for m in METHODS)],
        "The held-out error of each method on the grid of the protocol, for"
        " each failure of the gauge alone and together; a method recovers the"
        " law only when its fit is consistent with the noise and its error"
        " within the tolerance.",
    )


def the_degradation(experiment: Experiment):
    """Every baseline at each noise level over the seeds, the offset and the
    faults held; record the table and return the measurements."""
    found = degradation(SIGMAS, SEEDS)
    experiment.table(
        "d10-degradation",
        [
            (
                d.method,
                d.sigma,
                d.median,
                max(d.errors),
                f"{d.recovered} of {len(SEEDS)}",
            )
            for d in found
        ],
        [
            ("baseline", "", ""),
            ("noise", "N", "g"),
            ("median held-out error", "relative", ".2g"),
            ("largest held-out error", "relative", ".2g"),
            ("recovered", "seeds", ""),
        ],
        "Each baseline, every method on the grid of the gauge and two on"
        " random settings drawn anew for each seed, its offset and faults"
        " held, at six standard deviations of the noise, once for each of"
        " five seeds.",
    )
    return found


# region: explanations
def offset_gauge(distance, mass, strength, offset):
    """Explanation A: the inverse-square law, and a gauge that reads high
    by ``offset`` (N)."""
    return strength * mass * distance**-2.0 + offset


def shallower_law(distance, mass, strength, exponent):
    """Explanation B: a true gauge, and a law that falls more slowly than
    the inverse square."""
    return strength * mass * distance**-exponent


def law_and_offset(distance, mass, strength, exponent, offset):
    """The family that holds both: a free exponent and a free offset."""
    return strength * mass * distance**-exponent + offset


# endregion: explanations


def at_masses(model, masses: np.ndarray):
    """``model`` as a function of the distances alone, the masses of the
    readings fixed, as ``fit_curve`` and ``profile`` take it."""
    return lambda distance, *parameters: model(distance, masses, *parameters)


def synthetic_readings(
    distances: np.ndarray, masses: np.ndarray, seed: int = SYNTHETIC_SEED
) -> np.ndarray:
    """The readings (N) of the synthetic gauge at ``distances`` (m) with
    ``masses`` (kg), with the noise ``SIGMA``."""
    clean = law_and_offset(distances, masses, *TRUTH.values())
    rng = np.random.default_rng(seed)
    return clean + SIGMA * rng.standard_normal(clean.size)


def fit_both(
    distances: np.ndarray, masses: np.ndarray, y: np.ndarray
) -> tuple[FitResult, FitResult]:
    """Explanations A and B fitted to the readings ``y``."""
    a = fit_curve(
        at_masses(offset_gauge, masses),
        distances,
        y,
        [10.0, 0.0],
        sigma=SIGMA,
        names=("strength", "offset"),
    )
    b = fit_curve(
        at_masses(shallower_law, masses),
        distances,
        y,
        [10.0, 1.5],
        sigma=SIGMA,
        names=("strength", "exponent"),
    )
    return a, b


def far_error(law: float) -> float:
    """The relative error of a law's force at ``FAR`` on one kilogram,
    against the true law (without the offset)."""
    truth = TRUTH["strength"] * FAR ** -TRUTH["exponent"]
    return law / truth - 1


def _explanation_rows(a: FitResult, b: FitResult) -> list[tuple]:
    def row(name, fit, law):
        parameters = ", ".join(
            f"{n} {fit.value(n):.4g} ± {fit.stderr[k]:.2g}"
            for k, n in enumerate(fit.names)
        )
        return (
            name,
            parameters,
            fit.chi2,
            fit.dof,
            "yes" if consistent(fit.chi2, fit.dof) else "no",
            100 * far_error(law),
        )

    return [
        row("A: inverse square, gauge reads high", a, a.value("strength") * FAR**-2.0),
        row(
            "B: true gauge, shallower law",
            b,
            b.value("strength") * FAR ** -b.value("exponent"),
        ),
    ]


_EXPLANATION_COLUMNS = [
    ("explanation", "", "s"),
    ("fitted parameters ± standard error", "", "s"),
    ("chi-square", "", ".2f"),
    ("degrees of freedom", "", "d"),
    ("consistent", "", "s"),
    ("error of its law at 12 m", "%", ".1f"),
]


def equivalent_explanations(experiment: Experiment) -> dict:
    """Both explanations on the readings at one mass; record what each
    says, and return them with the correlation and the profile of the
    offset in the family that holds both, and the noise below which these
    readings would reject B."""
    masses = np.full(DISTANCES.size, MASS)
    y = synthetic_readings(DISTANCES, masses)
    a, b = fit_both(DISTANCES, masses, y)
    experiment.table(
        "explanations",
        _explanation_rows(a, b),
        _EXPLANATION_COLUMNS,
        caption=f"Two explanations fitted to the same {DISTANCES.size} readings"
        f" of the synthetic gauge, one mass, distances from 2 to 4 m, noise"
        f" {SIGMA:g} N. Strength in N m^p/kg, offset in N. The last column"
        " compares the law of each, without an offset, with the true law at"
        " 12 m. Chi-square to two decimals.",
    )
    family = at_masses(law_and_offset, masses)
    names = ("strength", "exponent", "offset")
    both = fit_curve(family, DISTANCES, y, [10.0, 1.5, 0.0], sigma=SIGMA, names=names)
    offsets = profile(
        family,
        DISTANCES,
        y,
        both.params,
        "offset",
        np.linspace(-0.3, 0.6, 91),
        sigma=SIGMA,
        names=names,
    )
    # The misfit of B on the noise-free readings is the chi-square it adds
    # to the noise: B is rejected once it exceeds the margin of the limit.
    noise_free = law_and_offset(DISTANCES, masses, *TRUTH.values())
    misfit = fit_curve(
        at_masses(shallower_law, masses),
        DISTANCES,
        noise_free,
        b.params,
        sigma=SIGMA,
        names=b.names,
    ).chi2
    margin = FIT_SIGMAS * math.sqrt(2 * b.dof)
    return {
        "y": y,
        "a": a,
        "b": b,
        "correlation": float(both.correlation[1, 2]),
        "profile": offsets,
        "misfit": misfit,
        "margin": margin,
        "separating-noise": SIGMA * math.sqrt(misfit / margin),
    }


def the_null_readings(experiment: Experiment) -> tuple[FitResult, FitResult]:
    """Both explanations on the same readings and ``NULL_DISTANCES``
    readings at zero mass, where the law vanishes and only the gauge reads."""
    distances = np.concatenate([DISTANCES, NULL_DISTANCES])
    masses = np.concatenate(
        [np.full(DISTANCES.size, MASS), np.zeros(len(NULL_DISTANCES))]
    )
    a, b = fit_both(distances, masses, synthetic_readings(distances, masses))
    experiment.table(
        "separated",
        _explanation_rows(a, b),
        _EXPLANATION_COLUMNS,
        caption=f"The same readings and {len(NULL_DISTANCES)} readings at zero"
        " mass, both explanations fitted again. Strength in N m^p/kg, offset"
        " in N; chi-square to two decimals.",
    )
    return a, b


def more_of_the_same(experiment: Experiment, noise: float) -> int:
    """Exercise: the number of readings at one mass, spread over the same
    distances, at which the misfit of B exceeds the margin of the limit at
    the noise ``noise``; record the table and return that number."""
    rows, enough = [], 0
    for count in (12, 48, 192, 768, 3072):
        distances = np.linspace(2.0, 4.0, count)
        masses = np.full(count, MASS)
        fit = fit_curve(
            at_masses(shallower_law, masses),
            distances,
            law_and_offset(distances, masses, *TRUTH.values()),
            [20.0, 1.9],
            sigma=noise,
            names=("strength", "exponent"),
        )
        margin = FIT_SIGMAS * math.sqrt(2 * fit.dof)
        rows.append((count, fit.chi2, margin, "yes" if fit.chi2 > margin else "no"))
        if not enough and fit.chi2 > margin:
            enough = count
    experiment.table(
        "more-of-the-same",
        rows,
        columns=[
            ("readings at one mass", "", "d"),
            ("misfit of B (chi-square)", "", ".1f"),
            ("margin of the limit", "", ".1f"),
            ("B rejected", "", "s"),
        ],
        caption=f"Explanation B on noise-free readings of the synthetic gauge"
        f" over 2 to 4 m, at the noise {noise:g} N: the chi-square its misfit"
        " adds, against the margin by which the limit exceeds the degrees of"
        " freedom. To one decimal.",
    )
    return enough


def draw_explanations(found: dict) -> Figure:
    """The readings and both explanations over a wider range of distances
    than was probed, and their difference in units of the noise."""
    a, b = found["a"], found["b"]
    distances = np.geomspace(1.5, 16.0, 200)
    with figure_style():
        fig, (top, bottom) = plt.subplots(
            2, 1, sharex=True, figsize=figsize("pair", legend=3)
        )
        for ax in (top, bottom):
            ax.axvspan(DISTANCES[0], DISTANCES[-1], color=FIGURE_COLOURS[2], alpha=0.12)
        top.errorbar(
            DISTANCES,
            found["y"],
            yerr=SIGMA,
            linestyle="none",
            marker="o",
            color=FIGURE_COLOURS[0],
            label="readings (bars: noise)",
        )
        top.plot(
            distances,
            offset_gauge(distances, MASS, *a.params),
            color=FIGURE_COLOURS[1],
            linestyle="--",
            label="A: inverse square, gauge reads high",
        )
        top.plot(
            distances,
            shallower_law(distances, MASS, *b.params),
            color=FIGURE_COLOURS[3],
            linestyle=":",
            label="B: true gauge, shallower law",
        )
        top.set_xscale("log")
        top.set_yscale("log")
        top.set_ylabel("reading on 1 kg (N)")
        difference = (
            shallower_law(distances, MASS, *b.params)
            - offset_gauge(distances, MASS, *a.params)
        ) / SIGMA
        bottom.plot(distances, difference, color=FIGURE_COLOURS[0], linestyle="-")
        bottom.axhspan(-1.0, 1.0, color=FIGURE_COLOURS[4], alpha=0.15)
        bottom.set_xlabel("distance (m), probed range shaded")
        bottom.set_ylabel("B minus A\n(units of the noise)")
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def draw_degradation(found) -> Figure:
    """The median held-out error of each baseline against the standard
    deviation of the noise: one colour, line style and marker per method,
    the random settings in a dotted line with open markers."""
    styles = dict(
        zip(METHODS, (("-", "o"), ("--", "s"), ("-", "^"), ("--", "D")), strict=True)
    )
    colours = dict(zip(METHODS, [FIGURE_COLOURS[i] for i in (0, 1, 4, 3)], strict=True))
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=len(BASELINES) + 1))
        for design, name in BASELINES:
            line, marker = styles[name]
            rows = [d for d in found if d.method == f"{design} + {name}"]
            random = design == "random"
            ax.plot(
                [d.sigma for d in rows],
                [d.median for d in rows],
                linestyle=":" if random else line,
                marker=marker,
                markerfacecolor="none" if random else colours[name],
                color=colours[name],
                label=f"{design} + {name}",
            )
        ax.axhline(
            TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance"
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("standard deviation of the noise (N)")
        ax.set_ylabel("median held-out\nerror (relative)")
        # Under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("condition", CONDITION)
    experiment.number("sigma", SIGMA, "g")
    experiment.number("reject-sigmas", REJECT_SIGMAS, "g")
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment()))
    )
    results = the_baselines(experiment)

    # region: replay
    recording, transcript, score = replay_run(LESSON)
    # endregion: replay
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    experiment.number("outcome", score.outcome)
    experiment.number("probes", score.probes)
    score_table(experiment, score)
    the_agents_readings(experiment, transcript, score)
    beside_the_baselines(experiment, score, results)
    the_failure_analysis(experiment)
    found = the_degradation(experiment)
    experiment.figure("fig-degradation", partial(draw_degradation, found))

    explanations = equivalent_explanations(experiment)
    a, b = explanations["a"], explanations["b"]
    experiment.number("synthetic-readings", DISTANCES.size)
    experiment.number("truth-strength", TRUTH["strength"], "g")
    experiment.number("truth-offset", TRUTH["offset"], "g")
    experiment.number("delta-chi2", abs(a.chi2 - b.chi2), ".2f")
    experiment.number(
        "a-far-error", 100 * abs(far_error(a.value("strength") * FAR**-2.0)), ".1f"
    )
    experiment.number(
        "b-far-error",
        100 * abs(far_error(b.value("strength") * FAR ** -b.value("exponent"))),
        ".0f",
    )
    experiment.number("b-exponent", b.value("exponent"), ".3f")
    experiment.number("b-exponent-error", b.stderr[1], ".3f")
    experiment.number(
        "b-exponent-off", (TRUTH["exponent"] - b.value("exponent")) / b.stderr[1], ".0f"
    )
    experiment.number("correlation", explanations["correlation"], ".2f")
    offsets = explanations["profile"]
    experiment.number("offset-low", offsets.low, ".2f")
    experiment.number("offset-high", offsets.high, ".2f")
    experiment.number("misfit", explanations["misfit"], ".1f")
    experiment.number("margin", explanations["margin"], ".1f")
    experiment.number("separating-noise", explanations["separating-noise"], ".3f")
    experiment.figure(
        "fig-equivalent-explanations", partial(draw_explanations, explanations)
    )
    a_null, b_null = the_null_readings(experiment)
    experiment.number("null-offset", a_null.value("offset"), ".3f")
    experiment.number("null-offset-error", a_null.stderr[1], ".3f")
    experiment.number("null-readings", len(NULL_DISTANCES))
    experiment.number("null-chi2-rise", b_null.chi2 - b.chi2, ".0f")
    experiment.number("enough-readings", more_of_the_same(experiment, SIGMA))
    return experiment


if __name__ == "__main__":
    main(run)
