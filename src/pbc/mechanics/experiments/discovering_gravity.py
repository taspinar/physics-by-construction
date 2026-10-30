"""The experiment of the lesson "Discovering gravity from experiments".

A language model probes the attraction between two masses in a laboratory
whose law is hidden (``pbc.discovery.gravity_lab``); the build scores its
law on orbits it never probed: the baselines without a model, the replay of
the recorded run and its score, the fit to the agent's own readings, and
the scan of laws the laboratory cannot tell apart, scored on the orbits.
Run it as a program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.discovering_gravity out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m
pbc.discovery.gravity_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.discovery import comparison, environment_allowlist
from pbc.discovery.baselines import consistent
from pbc.discovery.gravity_lab import (
    BUDGET,
    CONDITION,
    MAX_STEPS,
    TOLERANCE,
    baselines,
    environment,
    fit_laboratory,
    probes,
    recovered,
    replay_run,
    sensitivity,
)
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.gravity_lab"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/14-discovering-gravity"
PARAMETERS = ("G", "source_power", "test_power", "exponent")
SHIFTS = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0)  # standard errors
FAR_SHIFTS = (3.0, 10.0, 30.0, 100.0)  # standard errors, the exercise


def the_baselines(experiment: Experiment):
    """The baselines without a model with the protocol's budget, scored on
    the orbits; record the table and return them."""
    results = baselines()
    experiment.table(
        "d4-baselines",
        [
            (
                b.name,
                *(
                    (b.claim or {}).get(p) if b.claim and "G" in b.claim else None
                    for p in PARAMETERS[1:]
                ),
                b.held_out_error,
                "yes" if b.success else "no",
                "yes" if recovered(b) else "no",
            )
            for b in results
        ],
        [
            ("method", "", ""),
            ("source power", "", ".4f"),
            ("test power", "", ".4f"),
            ("exponent", "", ".4f"),
            ("transfer error", "relative", ".2g"),
            ("fit consistent", "", ""),
            ("recovered", "", ""),
        ],
        "The baselines without a model, fitted in the laboratory and scored on"
        " the orbits. Sparse identification states a sum of terms, so its"
        " powers are empty.",
    )
    sparse = results[2].claim or {}
    experiment.table(
        "d4-sparse",
        [(term, value) for term, value in sparse.items()],
        [("term kept", "", ""), ("coefficient", "N m^n/kg^2", ".4g")],
        "The terms that sparse identification kept.",
    )
    return results


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    experiment.table(
        "d4-score",
        [
            ("probes used", f"{score.probes}"),
            ("calls refused", f"{score.refused}"),
            *((f"claimed {p}", f"{score.claim[p]:.4g}") for p in PARAMETERS),
            ("transfer error", f"{score.held_out_error:.3g}"),
            ("tolerance", f"{TOLERANCE:g}"),
            ("outcome", score.outcome),
        ],
        [("quantity", "", ""), ("value", "", "")],
        "The agent's run, scored again by the build from its tool calls alone,"
        " on orbits it never probed.",
    )


def the_agents_readings(experiment: Experiment, transcript, score):
    """The family fitted to exactly the agent's readings, beside its claim;
    record the table and return the readings and the fit."""
    data = probes(transcript)
    fit = fit_laboratory(data)
    experiment.table(
        "d4-agent-readings",
        [
            (
                p,
                float(fit.params[i]),
                float(fit.stderr[i]),
                score.claim[p],
                (score.claim[p] - float(fit.params[i])) / float(fit.stderr[i]),
            )
            for i, p in enumerate(PARAMETERS)
        ],
        [
            ("parameter", "", ""),
            ("fit to its readings", "", ".5g"),
            ("standard error", "", ".2g"),
            ("claimed", "", ".5g"),
            ("claim minus fit", "standard errors", ".2f"),
        ],
        "The family fitted to the agent's own readings by weighted least"
        " squares, beside its claim.",
    )
    experiment.number("agent-chi2", fit.chi2, ".3g")
    experiment.number("agent-dof", fit.dof)
    experiment.number(
        "agent-fit-consistent", "yes" if consistent(fit.chi2, fit.dof) else "no"
    )
    experiment.number(
        "agent-fit-transfer",
        environment().held_out_error(
            dict(zip(PARAMETERS, map(float, fit.params), strict=True))
        ),
        ".2g",
    )
    return data


def beside_the_baselines(experiment: Experiment, score, results) -> None:
    """The agent and the baselines scored on the orbits; record the table."""
    rows = comparison((score,), results, TOLERANCE)
    experiment.table(
        "d4-comparison",
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
            ("transfer error", "relative", ".2g"),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The agent and the baselines, with the same budget, scored on the orbits.",
    )


def the_scan(experiment: Experiment, data) -> dict:
    """Laws the agent's readings cannot tell apart: each parameter held a
    number of standard errors from the fit, the others refitted; record the
    table and return the scans."""
    scans = {p: sensitivity(data, p, SHIFTS) for p in PARAMETERS}
    rows = []
    for p, scan in scans.items():
        by_shift = {s.shift: s for s in scan}
        errors = [s.transfer_error for s in scan]
        rows.append(
            (
                p,
                by_shift[3.0].chi2_increase,
                min(errors),
                max(errors),
                max(errors) - min(errors),
            )
        )
    experiment.table(
        "d4-scan",
        rows,
        [
            ("parameter held", "", ""),
            ("chi-square increase at 3 standard errors", "", ".3g"),
            ("smallest transfer error", "relative", ".2g"),
            ("largest transfer error", "relative", ".2g"),
            ("spread", "relative", ".2g"),
        ],
        "Each parameter held from minus to plus three standard errors of the"
        " fit to the agent's readings, the others refitted, and each law scored"
        " on the orbits.",
    )
    return scans


def draw_transfer(scans) -> Figure:
    """The transfer error of the laws of the scan against the shift of the
    parameter held, one line style and marker per parameter."""
    styles = {
        "G": ("-", "o"),
        "source_power": ("--", "s"),
        "test_power": (":", "^"),
        "exponent": ("-.", "D"),
    }
    colours = dict(
        zip(PARAMETERS, [FIGURE_COLOURS[i] for i in (0, 1, 4, 3)], strict=True)
    )
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for p, scan in scans.items():
        line, marker = styles[p]
        colour = colours[p]
        ax.plot(
            [s.shift for s in scan],
            [s.transfer_error for s in scan],
            linestyle=line,
            marker=marker,
            color=colour,
            label=p.replace("_", " "),
        )
    ax.axhline(TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance")
    ax.set_yscale("log")
    ax.set_xlabel("parameter held from the fit (standard errors)")
    ax.set_ylabel("transfer error (relative)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=5)
    fig.tight_layout()
    return fig


def far_shifts(experiment: Experiment, data) -> None:
    """Exercise: the source power held further and further from the fit;
    record the table."""
    scan = sensitivity(data, "source_power", FAR_SHIFTS)
    experiment.table(
        "far-shifts",
        [
            (
                s.shift,
                s.chi2_increase,
                s.transfer_error,
                "yes" if s.transfer_error <= TOLERANCE else "no",
            )
            for s in scan
        ],
        [
            ("source power held at", "standard errors", ".0f"),
            ("chi-square increase", "", ".3g"),
            ("transfer error", "relative", ".2g"),
            ("within the tolerance", "", ""),
        ],
        "The source power held far from the fit to the agent's readings, the"
        " other parameters refitted.",
    )


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
    data = the_agents_readings(experiment, transcript, score)
    beside_the_baselines(experiment, score, results)
    scans = the_scan(experiment, data)
    experiment.figure("fig-transfer", partial(draw_transfer, scans))
    far_shifts(experiment, data)
    return experiment


if __name__ == "__main__":
    main(run)
