"""The experiment of the lesson "Unlearning a familiar law: a modified force".

A language model probes a central force whose exponent is not the inverse
square (``pbc.discovery.force_lab``, run ``modified``): the familiar law
fitted and rejected, the baselines without a model, the replay of the
recorded run and its score as it is, and the fits to the agent's own
readings. Run it as a program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.modified_force_law out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.discovery.force_lab
modified``.
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
from pbc.discovery import CentralForceEnvironment, comparison, environment_allowlist
from pbc.discovery.baselines import grid_probe
from pbc.discovery.force_lab import (
    BUDGET,
    MAX_STEPS,
    RUNS,
    TOLERANCE,
    baselines,
    environment,
    familiar_law,
    fit_familiar,
    fit_probes,
    probes,
    recovered,
    replay_run,
    task_of,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import MUTED, figsize, figure_style, finish

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.force_lab modified"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/07-a-modified-force-law"
RUN = "modified"


def same_task(experiment: Experiment) -> None:
    """Whether the agent was given what the agent of the force-law lesson
    was given; record the table."""
    same = task_of(RUNS[RUN].protocol, RUNS[RUN].condition) == task_of(
        RUNS["black-box"].protocol, RUNS["black-box"].condition
    )
    experiment.table(
        "d3-same-task",
        [
            (
                "the system prompt and the task are those of the force-law lesson",
                "yes" if same else "no",
            )
        ],
        [("check", "", ""), ("result", "", "")],
        "The agent was given word for word what the agent of the force-law"
        " lesson was given.",
    )


def the_familiar_law(experiment: Experiment):
    """The inverse-square law fitted to the grid's readings of the modified
    world; record the table and return the fit."""
    familiar = familiar_law(RUN)
    experiment.table(
        "d3-familiar",
        [
            ("probes", f"{familiar.probes}"),
            (
                "fitted strength, exponent held at two",
                f"{familiar.claim['strength']:.4g}",
            ),
            ("held-out error", f"{familiar.held_out_error:.3g}"),
            ("verdict", "rejected" if not familiar.success else "accepted"),
            ("reason", familiar.reason),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The inverse-square law fitted to the grid baseline's readings of the"
        " modified world.",
    )
    return familiar


def the_baselines(experiment: Experiment, familiar):
    """The baselines without a model, with the familiar law beside them;
    record the table and return the baselines."""
    results = baselines(RUN)
    experiment.table(
        "d3-baselines",
        [
            (
                b.name,
                b.claim.get("exponent") if b.claim else None,
                b.held_out_error,
                "yes" if b.success else "no",
                "yes" if recovered(b) else "no",
                b.reason or "fit consistent with the noise",
            )
            for b in (*results, familiar)
        ],
        [
            ("method", "", ""),
            ("claimed exponent", "", ".4g"),
            ("held-out error", "relative", ".3g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The baselines without a model on the modified world, with the familiar"
        " law beside them.",
    )
    return results


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d3-score",
        [
            ("probes used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            ("claimed strength", f"{score.claim['strength']:.4g}"),
            ("claimed exponent", f"{score.claim['exponent']:.4g}"),
            ("held-out error", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone.",
    )


def the_agents_readings(experiment: Experiment, transcript, score):
    """The free family and the familiar law fitted to exactly the agent's
    readings; record the two tables and return the readings and the free
    fit."""
    own_data = probes(RUN, transcript)
    own_fit = fit_probes(RUN, own_data)
    own_familiar = familiar_law(
        RUN, own_data, "the agent's readings, inverse-square law"
    )
    exponent, strength = float(own_fit.params[1]), float(own_fit.params[0])
    experiment.table(
        "d3-agent-readings",
        [
            ("free fit, exponent", exponent, float(own_fit.stderr[1])),
            ("free fit, strength", strength, float(own_fit.stderr[0])),
            (
                "agent's claimed exponent minus fit, in standard errors",
                (score.claim["exponent"] - exponent) / float(own_fit.stderr[1]),
                None,
            ),
            (
                "agent's claimed strength minus fit, in standard errors",
                (score.claim["strength"] - strength) / float(own_fit.stderr[0]),
                None,
            ),
        ],
        [("quantity", "", ""), ("value", "", ".4g"), ("standard error", "", ".2g")],
        "The agent's own readings: the free fit with its standard errors.",
    )
    experiment.table(
        "d3-agent-familiar",
        [
            (
                own_familiar.name,
                "accepted" if own_familiar.success else "rejected",
                own_familiar.reason or "fit consistent with the noise",
            )
        ],
        [("fit", "", ""), ("verdict", "", ""), ("reason", "", "")],
        "The familiar law fitted to the agent's own readings.",
    )
    return own_data, own_fit


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines on the modified world; record the
    table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d3-comparison",
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
            ("held-out error", "", ".3g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The agent and the baselines on the modified world, with the same budget.",
    )


def signature(data):
    """The force times the distance squared, per unit mass, of each reading."""
    return [
        v * s["distance"] ** 2 / s["mass"]
        for s, v in zip(data.settings, data.values, strict=True)
    ]


def draw_unlearning(results, familiar, own_data) -> Figure:
    """The signature of the modification: the readings of the grid and of
    the agent, the free fit, and the inverse-square fit."""
    grid = grid_probe(environment(RUN))
    free = {b.name: b for b in results}["grid + least squares"].claim
    r = np.linspace(1.0, 4.0, 100)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        # The grid's readings in the muted grey (the lighter grey of before
        # had less than 3:1 against the plate).
        ax.plot(
            [s["distance"] for s in grid.settings],
            signature(grid),
            "o",
            color=MUTED,
            markersize=4,
            label="grid baseline readings",
        )
        ax.plot(
            [s["distance"] for s in own_data.settings],
            signature(own_data),
            "o",
            color=FIGURE_COLOURS[1],
            markersize=7,
            label="agent's readings",
        )
        ax.plot(
            r,
            free["strength"] * r ** (2 - free["exponent"]),
            color=FIGURE_COLOURS[0],
            label="free fit",
        )
        ax.axhline(
            familiar.claim["strength"],
            color=MUTED,
            linestyle="--",
            label="inverse-square fit",
        )
        ax.set_xlabel("distance (m)")
        ax.set_ylabel("force × distance² per\nunit mass (N m²/kg)")  # noqa: RUF001
        # Four entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def small_modifications(experiment: Experiment) -> None:
    """Exercise 1: the inverse-square law fitted to worlds with slightly
    modified exponents; record the table."""
    rows = []
    for exponent in (2.002, 2.005, 2.01, 2.02, 2.05):
        world = CentralForceEnvironment(strength=12.0, exponent=exponent, budget=BUDGET)
        result = fit_familiar(world)
        rows.append(
            (
                exponent,
                "accepted" if result.success else "rejected",
                result.held_out_error,
                "yes" if result.held_out_error <= TOLERANCE else "no",
            )
        )
    experiment.table(
        "small-modifications",
        rows,
        [
            ("exponent of the world", "", ".4g"),
            ("chi-square test", "", ""),
            ("held-out error", "relative", ".3g"),
            ("within the tolerance", "", ""),
        ],
        "The inverse-square law fitted to worlds of your own with slightly"
        " modified exponents.",
    )


def two_point_exponent(experiment: Experiment, own_data, own_fit, score) -> None:
    """Exercise 2: the exponent from the agent's readings at 1 m and 4 m with
    a mass of 1 kg, beside its claim and the fit; record the table."""
    by_setting = {
        (s["distance"], s["mass"]): v
        for s, v in zip(own_data.settings, own_data.values, strict=True)
    }
    near, far = by_setting[(1.0, 1.0)], by_setting[(4.0, 1.0)]
    two_point = math.log(near / far) / math.log(4.0)
    experiment.table(
        "two-point",
        [
            ("from the two readings", two_point),
            ("agent's claim", score.claim["exponent"]),
            ("free fit to all its readings", float(own_fit.params[1])),
        ],
        [("estimate of the exponent", "", ""), ("value", "", ".4g")],
        "The exponent from two of the agent's readings, beside its claim and the fit.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment(RUN)))
    )
    same_task(experiment)
    familiar = the_familiar_law(experiment)
    results = the_baselines(experiment, familiar)

    # region: replay
    recording, transcript, score = replay_run(RUN, LESSON)
    # endregion: replay
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    score_table(experiment, score)
    experiment.number("outcome", score.outcome)
    experiment.number("probes", score.probes)
    own_data, own_fit = the_agents_readings(experiment, transcript, score)
    beside_the_baselines(experiment, score, results)
    experiment.figure(
        "fig-unlearning", partial(draw_unlearning, results, familiar, own_data)
    )
    small_modifications(experiment)
    two_point_exponent(experiment, own_data, own_fit, score)
    return experiment


if __name__ == "__main__":
    main(run)
