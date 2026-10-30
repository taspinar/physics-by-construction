"""The experiment of the lesson "A prediction and its explanation".

A model predicts four quantities of a particle falling with linear drag,
with an interval, a unit, and an explanation chosen from candidate relations
(``pbc.agents.explanation_lab``). The recorded run is replayed; the build
tests each prediction against the exact solution and each explanation by its
unit, its dimensions, its physics, its support of the prediction, and its
interval. Two baselines without a model: a curve fit to the plotted points
and dimensional analysis. Run it as a program to write the figures and
numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.interpretable_physics_explanations out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.explanation_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.explanation_lab import (
    AGREEMENT,
    PICTURE,
    PREDICTION_TOLERANCE,
    QUESTIONS,
    curve_fit_baseline,
    dimensional_baseline,
    examine,
    explain_sheet,
    replay_fixture,
    tested,
    verified,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.explanation_lab"

# The recorded run, next to the page that shows it.
LESSON = (
    REPOSITORY_ROOT / "site/lessons/agents-llm/17-interpretable-physics-explanations"
)


def _yes(passed: bool | None) -> str:
    return "none" if passed is None else ("yes" if passed else "no")


def explanation_rows(found):
    """One row per question: what the model said, apart from what the build
    verified, and each test."""
    return [
        (
            t.asked.number,
            f"{t.value:g} [{t.low:g}, {t.high:g}] {t.unit}",
            t.relation,
            f"{t.truth:.4g} {t.asked.unit}",
            _yes(t.prediction),
            _yes(t.unit_right),
            _yes(t.dimensions),
            _yes(t.physics),
            _yes(t.support),
            _yes(t.covers),
        )
        for t in found
    ]


def baseline_rows(found, fit, forms):
    """One row per question: the verified result, the model, the curve fit,
    and the relations dimensional analysis leaves."""
    rows = []
    for t in found:
        n = t.asked.number
        close = abs(fit[n] - t.truth) <= PREDICTION_TOLERANCE * abs(t.truth)
        left = forms[n]
        rows.append(
            (
                n,
                f"{t.truth:.4g}",
                f"{t.value:g}",
                f"{fit[n]:.4g} ({'within' if close else 'outside'})",
                left[0] if len(left) == 1 else f"not identified: {len(left)} left",
            )
        )
    return rows


def draw_intervals(found, fit) -> Figure:
    """Each prediction and its interval over the verified result, with the
    curve fit's prediction and the tolerance of a prediction."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    x = np.arange(len(found))
    ax.axhspan(
        1 - PREDICTION_TOLERANCE,
        1 + PREDICTION_TOLERANCE,
        color=FIGURE_COLOURS[2],
        alpha=0.15,
        label="tolerance of a prediction",
    )
    ax.axhline(1.0, color=FIGURE_COLOURS[2], linestyle=":", linewidth=0.8)
    ratio = [t.value / t.truth for t in found]
    below = [(t.value - t.low) / t.truth for t in found]
    above = [(t.high - t.value) / t.truth for t in found]
    ax.errorbar(
        x - 0.1,
        ratio,
        yerr=[below, above],
        fmt="o",
        color=FIGURE_COLOURS[0],
        capsize=4,
        label="model: prediction and its interval",
    )
    ax.scatter(
        x + 0.1,
        [fit[t.asked.number] / t.truth for t in found],
        marker="s",
        color=FIGURE_COLOURS[1],
        label="curve fit to the plotted points",
        zorder=3,
    )
    ax.set_xticks(x, [f"Q{t.asked.number}" for t in found])
    ax.set_xlabel("question")
    ax.set_ylabel("prediction over the verified result")
    ax.set_ylim(0.4, 1.2)
    ax.legend(fontsize=8, loc="lower left")
    return fig


def constructed_examples():
    """Exercise 1: two answers written for the exercise, not by a model,
    tested like the recorded ones."""
    q4 = QUESTIONS[3]
    truth = verified()[4]
    answers = (
        {
            "value": round(truth, 1),
            "low": round(truth, 1) - 1.0,
            "high": round(truth, 1) + 1.0,
            "unit": "m/s",
            "relation": "v = g t",
        },
        {
            "value": 30.0,
            "low": 28.0,
            "high": 32.0,
            "unit": "m/s",
            "relation": "v = (m g / b) (1 - exp(-b t / m))",
        },
        {
            "value": round(truth, 1),
            "low": round(truth, 1) - 1.0,
            "high": round(truth, 1) + 1.0,
            "unit": "m/s",
            "relation": "v = (m g / b) (1 - exp(-t))",
        },
    )
    return [
        (
            k,
            f"{a['value']:g} [{a['low']:g}, {a['high']:g}] {a['unit']}",
            a["relation"],
            *(
                _yes(getattr(t, name))
                for name in ("prediction", "dimensions", "physics", "support")
            ),
        )
        for k, a in enumerate(answers, start=1)
        for t in [examine(q4, truth, a)]
    ]


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-explanation-picture", PICTURE.draw)

    # region: replay
    recording, transcript = replay_fixture(LESSON)
    found = tested(transcript)
    # endregion: replay
    experiment.display("allowlist", AllowlistDisplay(explain_sheet()))
    experiment.display("run", RunDisplay(recording, transcript))
    experiment.number("recorded", recording.recorded)
    experiment.number("prediction-tolerance", 100 * PREDICTION_TOLERANCE, ".0f")
    experiment.number("agreement", AGREEMENT, ".0e")
    experiment.number("questions", len(QUESTIONS), "d")
    experiment.number("predictions-right", sum(t.prediction for t in found), "d")
    experiment.number(
        "explanations-right",
        sum(
            bool(t.unit_right and t.dimensions and t.physics and t.support)
            for t in found
        ),
        "d",
    )

    experiment.table(
        "ai7-explanations",
        explanation_rows(found),
        [
            ("question", "", "d"),
            ("the model's prediction [interval]", "", ""),
            ("the model's explanation", "", ""),
            ("verified result", "", ""),
            ("prediction", "", ""),
            ("unit", "", ""),
            ("dimensions", "", ""),
            ("physics", "", ""),
            ("support", "", ""),
            ("interval", "", ""),
        ],
        "What the recorded model said (its prediction, interval, unit, and the"
        " relation it chose) beside the verified result the build computed from"
        " the exact solution, and each test the build ran on the prediction and"
        " on the explanation.",
    )
    fit, forms = curve_fit_baseline(), dimensional_baseline()
    experiment.table(
        "ai7-baselines",
        baseline_rows(found, fit, forms),
        [
            ("question", "", "d"),
            ("verified result", "", ""),
            ("model", "", ""),
            ("curve fit", "", ""),
            ("dimensional analysis", "", ""),
        ],
        "The verified result, the model's prediction, the prediction of a curve"
        " fitted to the plotted points (within or outside the tolerance), and"
        " the candidate relations that pass the scaling test.",
    )
    experiment.figure("fig-explanation-intervals", partial(draw_intervals, found, fit))
    experiment.table(
        "ai7-examples",
        constructed_examples(),
        [
            ("answer", "", "d"),
            ("prediction [interval]", "", ""),
            ("explanation", "", ""),
            ("prediction", "", ""),
            ("dimensions", "", ""),
            ("physics", "", ""),
            ("support", "", ""),
        ],
        "Three answers to the question of the velocity after four seconds,"
        " written for the exercise, tested as the recorded ones are.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
