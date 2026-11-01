"""The experiment of the lesson "Scientific discovery under measurement noise".

A language model probes a central force through a faulty gauge, with noise,
a hidden zero offset, and faulty readings (``pbc.discovery.noise_lab``); the
build scores its law on distances it never probed: the baselines without a
model, the replay of the recorded run and its score, the calibrated robust
fit to the agent's own readings, the failure analysis of the gauge, and the
degradation of every baseline as the noise grows. Run it as a program to
write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discovery_under_noise out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.noise_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison, environment_allowlist
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

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.noise_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/18-discovery-under-noise"
# The noise levels and seeds of the degradation (N; one run per seed).
SIGMAS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
SEEDS = (0, 1, 2, 3, 4)


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


def draw_degradation(found) -> Figure:
    """The median held-out error of each baseline against the standard
    deviation of the noise: one colour, line style and marker per method,
    the random settings in a dotted line with open markers."""
    styles = dict(
        zip(METHODS, (("-", "o"), ("--", "s"), ("-", "^"), ("--", "D")), strict=True)
    )
    colours = dict(zip(METHODS, [FIGURE_COLOURS[i] for i in (0, 1, 4, 3)], strict=True))
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
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
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("standard deviation of the noise (N)")
    ax.set_ylabel("median held-out error (relative)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    fig.tight_layout()
    return fig


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
    return experiment


if __name__ == "__main__":
    main(run)
