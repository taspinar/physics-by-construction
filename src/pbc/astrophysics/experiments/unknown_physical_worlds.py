"""The experiment of the lesson "Unknown physical worlds".

A language model places three bodies at rest in a world whose pair forces
are hidden (``pbc.discovery.world_lab``); the build starts the bodies in
motion from starts nobody probed and scores the motion its claim predicts:
the baselines without a model (least squares of the family, sparse
identification over whole powers, Newton's gravity), the replay of the
recorded run and its score, the fit to the agent's own readings, and the
prediction error in time. Run it as a program to write the figure and
numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.astrophysics.experiments.unknown_physical_worlds out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.world_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison
from pbc.discovery.world_lab import (
    BUDGET,
    CONDITION,
    MAX_STEPS,
    SEED,
    TOLERANCE,
    agent_probes,
    allowlist,
    baselines,
    recovered,
    replay_run,
    world,
)
from pbc.discovery.worlds import (
    COUPLINGS,
    MASSES,
    PAIRS,
    family_force,
    fit_family,
    random_configurations,
    terms_force,
)
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.world_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/15-unknown-physical-worlds"
PARAMETERS = (*COUPLINGS, "exponent")
CURVE_TIMES = tuple(float(t) for t in np.linspace(0.1, 4.0, 40))  # s
BUDGETS = (2, 3, 4, 6, 12)  # configurations, the exercise


def the_baselines(experiment: Experiment):
    """The baselines without a model with the protocol's budget, scored on
    the motion; record the tables and return them."""
    results = baselines()
    experiment.table(
        "d5-baselines",
        [
            (
                b.name,
                b.claim.get("exponent") if b.claim and "exponent" in b.claim else None,
                b.held_out_error,
                "yes" if b.success else "no",
                "yes" if recovered(b) else "no",
                b.reason or "fit consistent with the noise",
            )
            for b in results
        ],
        [
            ("method", "", ""),
            ("exponent", "", ".4g"),
            ("prediction error", "relative", ".2g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The baselines without a model, fitted to random configurations and"
        " scored on the motion from the held-out starts.",
    )
    sparse = results[1].claim or {}
    experiment.table(
        "d5-sparse",
        list(sparse.items()),
        [("term kept", "", ""), ("coefficient", "N m^n", ".4g")],
        "The terms that sparse identification kept, by pair and power of the distance.",
    )
    return results


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d5-score",
        [
            ("configurations used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            *((f"claimed {p}", f"{score.claim[p]:.4g}") for p in PARAMETERS),
            ("prediction error", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone,"
        " on the motion from starts it never probed.",
    )


def the_agents_readings(experiment: Experiment, transcript, score) -> None:
    """The family fitted to exactly the agent's readings, beside its claim;
    record the table."""
    data = agent_probes(transcript)
    fit = fit_family(world(), data, "the agent's readings, least squares")
    experiment.table(
        "d5-agent-readings",
        [(p, fit.claim[p], score.claim[p]) for p in PARAMETERS],
        [
            ("parameter", "", ""),
            ("fit to its readings", "", ".4g"),
            ("claimed", "", ".4g"),
        ],
        "The family fitted to the agent's own readings by weighted least"
        " squares, beside its claim.",
    )
    experiment.number("agent-fit-consistent", "yes" if fit.success else "no")
    experiment.number("agent-fit-error", fit.held_out_error, ".2g")
    experiment.number("agent-readings", 6 * len(data))


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines scored on the motion; record the table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d5-comparison",
        [
            (
                r["who"],
                r["probes"],
                r["held_out_error"],
                "yes" if r["recovered"] else "no",
            )
            for r in rows
        ],
        [
            ("method", "", ""),
            ("configurations", "", "d"),
            ("prediction error", "relative", ".2g"),
            ("recovered", "", ""),
        ],
        "The agent and the baselines, with the same budget, scored on the motion.",
    )


def errors_in_time(score, results) -> dict[str, np.ndarray]:
    """The relative position error of each claim at ``CURVE_TIMES``: the
    agent's and every baseline's."""
    w = world()
    forces = {"agent": family_force(score.claim)}
    for b in results:
        if b.claim:
            name = b.name.removeprefix("random + ")
            forces[name] = (
                family_force(b.claim) if "exponent" in b.claim else terms_force(b.claim)
            )
    return {name: w.error_in_time(f, CURVE_TIMES) for name, f in forces.items()}


def draw_predictive_test(curves) -> Figure:
    """The relative position error of each claim against time, on the
    held-out starts, with the tolerance."""
    styles = (("-", "o"), ("--", "s"), (":", "^"), ("-.", "D"))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for (name, errors), colour, (line, marker) in zip(
        curves.items(), (FIGURE_COLOURS[i] for i in (1, 0, 4, 3)), styles, strict=False
    ):
        ax.plot(
            CURVE_TIMES,
            errors,
            linestyle=line,
            marker=marker,
            markevery=5,
            color=colour,
            label=name,
        )
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.set_yscale("log")
    ax.set_xlabel("time since the held-out start (s)")
    ax.set_ylabel("position error / size of the system")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    fig.tight_layout()
    return fig


def coupling_ratios(experiment: Experiment, score) -> None:
    """Exercise: each claimed coupling over the product of the masses of its
    pair, which gravity would make the same for every pair; record the
    table."""
    experiment.table(
        "coupling-ratios",
        [
            (
                name,
                MASSES[i] * MASSES[j],
                score.claim[name],
                score.claim[name] / (MASSES[i] * MASSES[j]),
            )
            for name, (i, j) in zip(COUPLINGS, PAIRS, strict=True)
        ],
        [
            ("pair", "", ""),
            ("product of the masses", "kg^2", ".3g"),
            ("claimed coupling", "N m^p", ".3g"),
            ("coupling over the product", "", ".3g"),
        ],
        "The agent's couplings over the products of the masses of their pairs.",
    )


def budget_scan(experiment: Experiment) -> None:
    """Exercise: least squares of the family on random configurations with
    smaller budgets; record the table."""
    rows = []
    for budget in BUDGETS:
        w = world(budget)
        result = fit_family(w, random_configurations(w, SEED))
        rows.append(
            (
                budget,
                6 * budget,
                "yes" if result.success else "no",
                result.held_out_error,
                "yes" if recovered(result) else "no",
            )
        )
    experiment.table(
        "budget-scan",
        rows,
        [
            ("configurations", "", "d"),
            ("readings", "", "d"),
            ("fit consistent", "", ""),
            ("prediction error", "relative", ".2g"),
            ("recovered", "", ""),
        ],
        "Least squares of the family on random configurations, with budgets"
        " from two to twelve.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("condition", CONDITION)
    experiment.display("allowlist", AllowlistDisplay(allowlist()))
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
    curves = errors_in_time(score, results)
    experiment.figure("fig-predictive-test", partial(draw_predictive_test, curves))
    coupling_ratios(experiment, score)
    budget_scan(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
