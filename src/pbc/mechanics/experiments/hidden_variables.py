"""The experiment of the lesson "Hidden forces and unobserved variables".

A language model probes a fall under gravity and two effects it cannot see,
a constant force against the fall and linear drag
(``pbc.discovery.latent_lab``); the build scores its law at masses and times
it never probed: the baselines without a model, the ambiguity of an
observational record taken at one mass, the experiment that resolves it,
and the replay of the recorded run, its score, and the hypotheses fitted to
its own readings. Run it as a program to write the figure and numbers of
the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.hidden_variables out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.latent_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison, environment_allowlist
from pbc.discovery.latent_lab import (
    BUDGET,
    CONDITION,
    DRAGS,
    FORCES,
    MASSES,
    MAX_STEPS,
    RECORD_MASS,
    RECORD_TIMES,
    TIMES,
    TOLERANCE,
    baselines,
    disambiguating_experiment,
    environment,
    judge_hypotheses,
    probes,
    record,
    recovered,
    replay_run,
    rivals,
    with_readings_at,
)
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.latent_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/19-hidden-variables"
PARAMETERS = ("g", "hidden_force", "drag")


def the_baselines(experiment: Experiment):
    """The baselines without a model with the protocol's budget, scored at
    the held-out masses and times; record the table and return them."""
    results = baselines()
    experiment.table(
        "d11-baselines",
        [
            (
                b.name,
                *(
                    (b.claim or {}).get(p) if b.claim and "g" in b.claim else None
                    for p in PARAMETERS
                ),
                b.held_out_error,
                "yes" if b.success else "no",
                "yes" if recovered(b) else "no",
            )
            for b in results
        ],
        [
            ("method", "", ""),
            ("g", "m/s^2", ".4g"),
            ("hidden force", "N", ".3g"),
            ("drag", "kg/s", ".3g"),
            ("held-out error", "relative", ".2g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
        ],
        "The baselines without a model, scored at masses and times outside"
        " the bounds. Sparse identification states a sum of terms, so its"
        " parameters are empty.",
    )
    return results


def _verdicts(experiment: Experiment, name: str, data, caption: str) -> None:
    experiment.table(
        name,
        [
            (
                v.hypothesis,
                v.chi2,
                v.dof,
                "yes" if v.consistent else "no",
                "yes" if v.identifiable else "no",
                v.held_out_error,
            )
            for v in judge_hypotheses(data)
        ],
        [
            ("hypothesis", "", ""),
            ("chi-square", "", ".3g"),
            ("degrees of freedom", "", "d"),
            ("consistent with the noise", "", ""),
            ("parameters determined", "", ""),
            ("held-out error of its best fit", "relative", ".2g"),
        ],
        caption,
    )


def the_ambiguity(experiment: Experiment):
    """The observational record fitted by each hypothesis, and the laws it
    cannot tell apart; record the table and numbers, return the record and
    the laws."""
    data = record()
    _verdicts(
        experiment,
        "d11-record",
        data,
        "Each hypothesis about the latent effects fitted to the observational"
        " record, readings at one mass and short times.",
    )
    laws = rivals(data)
    experiment.number("record-mass", RECORD_MASS, "g")
    experiment.number("record-readings", len(RECORD_TIMES))
    experiment.number("record-last-time", RECORD_TIMES[-1], "g")
    experiment.number("candidate-laws", len(FORCES) * len(DRAGS))
    experiment.number("rival-laws", len(laws))
    return data, laws


def the_experiment(experiment: Experiment, data, laws):
    """The setting where the rival laws disagree most, and the hypotheses
    fitted again with readings there; record the tables and numbers, return
    the disagreement and the setting."""
    chosen, spread = disambiguating_experiment(laws)
    experiment.number("chosen-mass", chosen["mass"], "g")
    experiment.number("chosen-time", chosen["time"], "g")
    experiment.number("chosen-spread", spread[(chosen["mass"], chosen["time"])], ".0f")
    experiment.number("record-spread", spread[(RECORD_MASS, max(TIMES))], ".0f")
    more = with_readings_at(data, chosen["mass"])
    _verdicts(
        experiment,
        "d11-resolved",
        more,
        "The same hypotheses fitted to the record with readings added at the"
        " chosen mass, one at each time of the experiment.",
    )
    experiment.number("rival-laws-after", len(rivals(more)))
    return spread, chosen


def draw_disambiguation(spread, chosen) -> Figure:
    """The disagreement of the rival laws against the mass, one line style
    and marker per time, the chosen setting marked."""
    styles = (("-", "o"), ("--", "s"), (":", "^"), ("-.", "D"))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for (line, marker), colour, t in zip(
        styles, [FIGURE_COLOURS[i] for i in (0, 1, 4, 3)], TIMES, strict=True
    ):
        ax.plot(
            MASSES,
            [spread[(m, t)] for m in MASSES],
            linestyle=line,
            marker=marker,
            color=colour,
            label=f"time {t:g} s",
        )
    ax.plot(
        [chosen["mass"]],
        [spread[(chosen["mass"], chosen["time"])]],
        linestyle="none",
        marker="*",
        markersize=16,
        color=FIGURE_COLOURS[2],
        label="chosen experiment",
    )
    ax.axvline(
        RECORD_MASS, color=FIGURE_COLOURS[2], linestyle=":", label="mass of the record"
    )
    ax.set_yscale("log")
    ax.set_xlabel("mass of the body (kg)")
    ax.set_ylabel("disagreement of the rival laws (noise standard deviations)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    fig.tight_layout()
    return fig


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d11-score",
        [
            ("probes used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            *((f"claimed {p}", f"{score.claim[p]:.4g}") for p in PARAMETERS),
            ("held-out error", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone.",
    )


def the_agents_readings(experiment: Experiment, transcript) -> None:
    """The hypotheses fitted to exactly the agent's readings; record the
    table and numbers."""
    data = probes(transcript)
    _verdicts(
        experiment,
        "d11-agent-readings",
        data,
        "Each hypothesis fitted to the agent's own readings.",
    )
    experiment.number("agent-masses", len({s["mass"] for s in data.settings}))
    experiment.number("agent-lightest", min(s["mass"] for s in data.settings), "g")
    experiment.number("agent-longest", max(s["time"] for s in data.settings), "g")


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines at the held-out settings; record the table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d11-comparison",
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
        "The agent and the baselines, with the same budget, at the held-out"
        " masses and times.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("condition", CONDITION)
    experiment.number("sigma", environment().observation.sigma, "g")
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment()))
    )
    results = the_baselines(experiment)
    data, laws = the_ambiguity(experiment)
    spread, chosen = the_experiment(experiment, data, laws)
    experiment.figure(
        "fig-disambiguation", partial(draw_disambiguation, spread, chosen)
    )

    # region: replay
    recording, transcript, score = replay_run(LESSON)
    # endregion: replay
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    experiment.number("outcome", score.outcome)
    experiment.number("probes", score.probes)
    score_table(experiment, score)
    the_agents_readings(experiment, transcript)
    beside_the_baselines(experiment, score, results)
    return experiment


if __name__ == "__main__":
    main(run)
