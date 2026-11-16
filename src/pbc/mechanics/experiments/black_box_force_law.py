"""The experiment of the lesson "Discovering a force law with controlled probes".

A language model probes a black-box central force and submits a law
(``pbc.discovery.force_lab``, run ``black-box``): the replay of the recorded
run, its score recomputed on the held-out settings, the fit of the family to
the agent's own readings, and the baselines without a model. Run it as a
program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.black_box_force_law out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.discovery.force_lab
black-box``.
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
from pbc.discovery import (
    CentralForceEnvironment,
    comparison,
    environment_allowlist,
    library,
    sparse_identification,
)
from pbc.discovery.baselines import grid_probe, least_squares
from pbc.discovery.force_lab import (
    BUDGET,
    MAX_STEPS,
    TOLERANCE,
    baselines,
    environment,
    fit_probes,
    probes,
    replay_run,
)
from pbc.experiment import Experiment, main
from pbc.figure_language import MUTED, figsize, figure_style, finish

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.discovery.force_lab black-box"

# The recorded run, next to the page that shows it.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/05-discovering-a-force-law"
RUN = "black-box"


def shown(error):
    # An exact match scores zero; the page prints no round-off digits.
    return "below 1e-12" if error < 1e-12 else f"{error:.3g}"


def score_table(experiment: Experiment, score) -> None:
    """The agent's run scored again from its tool calls; record the table."""
    claim = score.claim
    experiment.table(
        "d1-score",
        [
            ("probes used", score.probes, ""),
            ("calls refused", score.refused, ""),
            ("claimed strength", claim["strength"], "N m^p/kg"),
            ("claimed exponent", claim["exponent"], ""),
            ("held-out error", shown(score.held_out_error), "relative"),
            ("tolerance", TOLERANCE, "relative"),
            ("outcome", score.outcome, ""),
        ],
        [("quantity", "", ""), ("value", "", ""), ("unit", "", "")],
        "The agent's run scored again by the build from its tool calls alone.",
    )


def probe_fit(experiment: Experiment, transcript):
    """The family fitted to exactly the readings the agent saw; record the
    table and return the readings and the fitted law."""
    data = probes(RUN, transcript)
    fit = fit_probes(RUN, data)
    own = dict(zip(fit.names, map(float, fit.params), strict=True))
    experiment.table(
        "d1-probe-fit",
        [
            (name, value, error)
            for name, value, error in zip(
                fit.names, fit.params, fit.stderr, strict=True
            )
        ]
        + [("held-out error of this fit", environment(RUN).held_out_error(own), None)],
        [
            ("parameter", "", ""),
            ("fitted value", "", ".4g"),
            ("standard error", "", ".2g"),
        ],
        "The family fitted to the agent's four readings, as recomputed by the replay.",
    )
    return data, own


def beside_the_baselines(experiment: Experiment, score) -> None:
    """The agent's run beside three baselines without a model; record the
    table."""
    rows = comparison((score,), baselines(RUN), TOLERANCE)
    experiment.table(
        "d1-baselines",
        [
            (
                r["who"],
                r["probes"],
                shown(r["held_out_error"]),
                "yes" if r["recovered"] else "no",
                r["note"],
            )
            for r in rows
        ],
        [
            ("method", "", ""),
            ("probes", "", "d"),
            ("held-out error", "", ""),
            ("recovered", "", ""),
            ("note", "", ""),
        ],
        "The agent's run and three baselines without a model, on the same box"
        " with the same budget.",
    )


def draw_force_probes(data, own) -> Figure:
    """Force per unit mass against distance on logarithmic axes: the grid's
    readings, the agent's, and the law fitted to the agent's, extrapolated
    beyond the bounds."""
    grid = grid_probe(environment(RUN))
    distances = np.geomspace(1.0, 12.0, 100)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line", legend=4))
        # The grid's readings in the muted grey (the lighter grey of before
        # had less than 3:1 against the plate).
        ax.loglog(
            [s["distance"] for s in grid.settings],
            grid.values / np.array([s["mass"] for s in grid.settings]),
            "o",
            color=MUTED,
            markersize=4,
            label="grid baseline readings",
        )
        ax.loglog(
            [s["distance"] for s in data.settings],
            data.values / np.array([s["mass"] for s in data.settings]),
            "o",
            color=FIGURE_COLOURS[1],
            markersize=7,
            label="agent's readings",
        )
        inside = distances <= 4.0
        line = own["strength"] * distances ** -own["exponent"]
        ax.loglog(
            distances[inside],
            line[inside],
            color=FIGURE_COLOURS[0],
            label="fit to the agent's readings",
        )
        ax.loglog(
            distances[~inside],
            line[~inside],
            "--",
            color=FIGURE_COLOURS[0],
            label="extrapolated beyond the bounds",
        )
        ax.axvline(4.0, color=MUTED, linestyle=":")
        ax.set_xlabel("distance (m)")
        ax.set_ylabel("force per unit\nmass (N/kg)")
        # Four entries: under the plot, in one column.
        fig.legend(loc="outside lower center", ncols=1)
    return finish(fig)


def sparse_on_a_collinear_library(experiment: Experiment) -> None:
    """Exercise 1: least squares and sparse identification on a box of
    strength 9 and exponent 2; record the table."""
    own_box = CentralForceEnvironment(strength=9.0, exponent=2.0, budget=20)
    own_grid = grid_probe(own_box)
    results = [
        least_squares(own_box, own_grid, "grid + least squares"),
        sparse_identification(
            own_box, own_grid, library(own_box), name="grid + sparse identification"
        ),
    ]
    experiment.table(
        "own-box",
        [
            (
                r.name,
                "yes" if r.success else "no",
                r.reason or "fit consistent with the noise",
            )
            for r in results
        ],
        [("method", "", ""), ("success", "", ""), ("reason", "", "")],
        "Two baselines on a box with an inverse-square law of strength 9.",
    )


def slope_errors(experiment: Experiment) -> None:
    """Exercise 2: the error of the exponent from two readings, for a wide
    and a narrow pair of distances; record the table."""
    sigma = environment(RUN).observation.sigma

    def slope_error(f1, f2, r1, r2):
        return sigma * math.sqrt(1 / f1**2 + 1 / f2**2) / math.log(r2 / r1)

    wide, narrow = slope_error(100, 6, 1, 4), slope_error(100, 25, 1, 2)
    experiment.table(
        "slope-errors",
        [
            ("1 m and 4 m", wide),
            ("1 m and 2 m", narrow),
            ("ratio, narrow over wide", narrow / wide),
        ],
        [("pair of distances", "", ""), ("error of the exponent", "", ".2g")],
        "The error of the exponent from two readings, by the formula of the"
        " explanation.",
    )


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("tolerance", TOLERANCE, "g")
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("max-calls", MAX_CALLS_PER_MESSAGE)
    experiment.number("sigma", environment(RUN).observation.sigma, "g")
    experiment.display(
        "allowlist", AllowlistDisplay(environment_allowlist(environment(RUN)))
    )

    # region: replay
    recording, transcript, score = replay_run(RUN, LESSON)
    # endregion: replay
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    score_table(experiment, score)
    experiment.number("outcome", score.outcome)
    experiment.number("probes", score.probes)
    data, own = probe_fit(experiment, transcript)
    beside_the_baselines(experiment, score)
    experiment.figure("fig-force-probes", partial(draw_force_probes, data, own))
    sparse_on_a_collinear_library(experiment)
    slope_errors(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
