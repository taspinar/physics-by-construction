"""The experiment of the lesson "Generalisation to unseen physical systems".

A language model probes a central force whose law has a hidden short-range
term (``pbc.discovery.generalisation_lab``); the build challenges its law,
and the baselines', on a suite of held-out worlds it never probed:
unprobed settings within the bounds, farther distances, heavier bodies,
orbits, and closer distances. It shows from the trace that no held-out
world was probed. Run it as a program to write the figure and numbers of
the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.generalisation_to_unseen_systems out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.generalisation_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison, environment_allowlist
from pbc.discovery.generalisation_lab import (
    BUDGET,
    CONDITION,
    MAX_STEPS,
    SCORED,
    TOLERANCE,
    WORLDS,
    baselines,
    environment,
    generalisation_of,
    period_sensitivity,
    probes,
    reach,
    recovered,
    replay_run,
)
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.generalisation_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/20-generalisation-to-unseen-systems"


def the_baselines(experiment: Experiment):
    """The baselines without a model with the protocol's budget; record the
    table and return them."""
    results = baselines()
    experiment.table(
        "d12-baselines",
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
            ("largest error of the scored worlds", "relative", ".2g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
        ],
        "The baselines without a model. Sparse identification states a sum of"
        " terms, so its parameters are empty.",
    )
    return results


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d12-score",
        [
            ("probes used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            *(
                (f"claimed {p}", f"{score.claim[p]:.4g}")
                for p in ("strength", "exponent")
            ),
            ("largest error of the scored worlds", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone.",
    )


def the_suite(experiment: Experiment, score, results) -> dict[str, dict[str, float]]:
    """The error of each claim in each held-out world; record the table and
    return the errors."""
    errors = {"agent": environment().generalisation_of(score.claim)}
    errors |= {b.name: generalisation_of(b) for b in results}
    experiment.table(
        "d12-suite",
        [(who, *(row[w] for w in WORLDS)) for who, row in errors.items()],
        [("claim", "", ""), *((w, "relative", ".2g") for w in WORLDS)],
        "The error of each claim in each held-out world: the force at the"
        " settings of a world, or the radial periods of the orbits. The last"
        " world is reported apart and is not scored.",
    )
    experiment.number(
        "closer-smallest", min(row["closer"] for row in errors.values()), ".2g"
    )
    experiment.number(
        "agent-worst-world", max(SCORED, key=lambda w: errors["agent"][w])
    )
    return errors


def orbit_sensitivity(experiment: Experiment, score) -> None:
    """How strongly the periods of the suite's orbits amplify an error of
    the strength, for the agent's claim and for an inverse square of the
    same strength from the same starts; record the table and numbers."""
    claimed = period_sensitivity(score.claim)
    square = period_sensitivity(score.claim | {"exponent": 2.0})
    experiment.table(
        "d12-sensitivity",
        [
            (f"orbit {i}", c, q)
            for i, (c, q) in enumerate(zip(claimed, square, strict=True), 1)
        ],
        [
            ("orbit", "", ""),
            ("the agent's claim", "|d ln T / d ln strength|", ".2f"),
            ("inverse square", "|d ln T / d ln strength|", ".2f"),
        ],
        "How strongly the radial period of each orbit of the suite amplifies"
        " a relative error of the strength, the start held fixed, nearest"
        " start first: for the agent's claim and for an inverse square of"
        " its strength.",
    )
    experiment.number("sensitivity-least", min(claimed), ".2f")
    experiment.number("sensitivity-most", max(claimed), ".2f")
    experiment.number("sensitivity-square-least", min(square), ".2f")
    experiment.number("sensitivity-square-most", max(square), ".2f")


def never_probed(experiment: Experiment, transcript) -> None:
    """How near the run's probes came to each held-out world that is a set
    of settings of the controls; record the table and numbers."""
    data = probes(transcript)
    found = reach(data)
    experiment.table(
        "d12-never-probed",
        [
            (
                r.world,
                r.settings,
                "yes" if r.outside_bounds else "no",
                r.nearest,
                r.probed,
            )
            for r in found
        ],
        [
            ("held-out world", "", ""),
            ("settings", "", "d"),
            ("all outside the bounds", "", ""),
            ("nearest probe", "ranges of the controls", ".2f"),
            ("settings probed", "", "d"),
        ],
        "From the trace: the nearest accepted probe of the run to each"
        " held-out world, the distance measured in units of each control's"
        " range. The orbits are no setting of the controls: no tool starts one.",
    )
    world = environment()
    inside = all(
        c.low <= s[c.name] <= c.high for s in data.settings for c in world.controls
    )
    experiment.number("probes-inside", "yes" if inside else "no")
    experiment.number("probes-on-held-out", sum(r.probed for r in found))


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines on the scored worlds; record the table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d12-comparison",
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
            ("largest error of the scored worlds", "relative", ".2g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The agent and the baselines, with the same budget, on the scored worlds.",
    )


def draw_generalisation(errors) -> Figure:
    """The error of each claim in each held-out world, grouped bars with a
    hatch per claim."""
    hatches = ("", "//", "..", "xx")
    colours = [FIGURE_COLOURS[i] for i in (0, 1, 4, 3)]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = np.arange(len(WORLDS))
    width = 0.8 / len(errors)
    for i, (who, row) in enumerate(errors.items()):
        ax.bar(
            x + (i - (len(errors) - 1) / 2) * width,
            [row[w] for w in WORLDS],
            width,
            color=colours[i],
            hatch=hatches[i],
            edgecolor="black",
            linewidth=0.5,
            label=who,
        )
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.axvline(len(WORLDS) - 1.5, color=FIGURE_COLOURS[2], linestyle=":")
    ax.set_xticks(x, WORLDS)
    ax.set_yscale("log")
    ax.set_xlabel("held-out world (the last is not scored)")
    ax.set_ylabel("error (relative)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
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
    never_probed(experiment, transcript)
    beside_the_baselines(experiment, score, results)
    errors = the_suite(experiment, score, results)
    orbit_sensitivity(experiment, score)
    experiment.figure("fig-generalisation", partial(draw_generalisation, errors))
    return experiment


if __name__ == "__main__":
    main(run)
