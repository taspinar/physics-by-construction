"""The experiment of the lesson "Reading physics from pictures".

Four verified figures of the site are the pictures of the task
(``pbc.agents.multimodal_lab``); eleven questions about them are answered by
a model with the pictures and by the same model without them. The recorded
runs are replayed and scored against a key the build computes from the
physics code (``pbc.agents.vision``). Run it as a program to write the
figures and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.multimodal_physics_reasoning out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.multimodal_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay
from pbc.agents.multimodal_lab import draw_strain, key
from pbc.agents.multimodal_questions import (
    CONDITIONS,
    QUESTIONS,
    euler,
    replay_fixtures,
    simulated_key,
)
from pbc.agents.vision import (
    KINDS,
    READING_TOLERANCE,
    answer_sheet,
    chance,
    score,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.electromagnetism.experiments import electric_fields_and_potential as fields
from pbc.experiment import Experiment, main
from pbc.mechanics.experiments import newtons_laws as falling

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.multimodal_lab"

# The recorded runs, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/16-multimodal-physics-reasoning"

# Stricter tolerances of the exercise, as fractions of the truth.
STRICTER = (0.10, 0.05, 0.02, 0.01)


def _shown(question, value) -> str:
    if value is None:
        return "none"
    if question.numeric:
        return f"{value:g} {question.unit}"
    return question.options[int(value) - 1]


def scored_runs(replays, truths):
    """The scored answers of each run, by condition."""
    return {c.id: score(QUESTIONS, truths, replays[c.id][1]) for c in CONDITIONS}


def answer_rows(scored, truths):
    """One row per question: the two runs' answers, the truth, and whether
    each answer is correct."""
    rows = []
    for k, q in enumerate(QUESTIONS):
        seen, unseen = scored["pictures"][k], scored["text"][k]
        rows.append(
            (
                q.number,
                q.picture,
                q.kind,
                _shown(q, seen.answer),
                "yes" if seen.correct else "no",
                _shown(q, unseen.answer),
                "yes" if unseen.correct else "no",
                _shown(q, truths[q.number]),
            )
        )
    return rows


def tally(scored, truths):
    """Correct answers by kind for each run, and the expected number for
    uniform guessing."""
    rows = []
    for condition in CONDITIONS:
        found = scored[condition.id]
        rows.append(
            (
                f"model {condition.title}",
                *(
                    f"{sum(s.correct for s in found if s.question.kind == kind)}"
                    for kind in KINDS
                ),
                f"{sum(s.correct for s in found)}",
            )
        )
    guesses = [(q, chance(q, truths[q.number])) for q in QUESTIONS]
    rows.append(
        (
            "uniform guessing (expected)",
            *(f"{sum(p for q, p in guesses if q.kind == kind):.2f}" for kind in KINDS),
            f"{sum(p for _, p in guesses):.2f}",
        )
    )
    return rows


def readings(replays, reference):
    """For each numeric question that ``reference`` answers, each run's
    distance from the truth, as a fraction of it."""
    asked = [one for one in QUESTIONS if one.number in reference and one.numeric]
    return {
        condition.id: {
            entry.question.number: abs(entry.answer - reference[entry.question.number])
            / abs(reference[entry.question.number])
            for entry in score(asked, reference, replays[condition.id][1])
            if entry.answer is not None
        }
        for condition in CONDITIONS
    }


def draw_readings(distances) -> Figure:
    """The distance of each numeric answer from the truth, for both runs,
    with the tolerance of the score."""
    numbers = sorted(distances["pictures"])
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    styles = {"pictures": ("o", 0, -0.12), "text": ("s", 1, 0.12)}
    for condition in CONDITIONS:
        marker, colour, shift = styles[condition.id]
        ax.scatter(
            np.arange(len(numbers)) + shift,
            [max(distances[condition.id][n], 1e-4) for n in numbers],
            marker=marker,
            s=45,
            color=FIGURE_COLOURS[colour],
            label=f"model {condition.title}",
            zorder=3,
        )
    ax.axhline(
        READING_TOLERANCE, color=FIGURE_COLOURS[2], linestyle="--", label="tolerance"
    )
    ax.set_yscale("log")
    ax.set_ylim(1e-4, 1.0)
    labels = {one.number: f"Q{one.number} ({one.picture})" for one in QUESTIONS}
    ax.set_xticks(np.arange(len(numbers)), [labels[n] for n in numbers])
    ax.set_xlabel("numeric question (picture)")
    ax.set_ylabel("distance from the truth (relative, log scale)")
    ax.legend(fontsize=8, loc="upper left")
    return fig


def stricter(scored, truths):
    """Exercise 1: the number of numeric answers each run gets right at
    stricter tolerances than the score's."""
    rows = []
    numeric = [q for q in QUESTIONS if q.numeric]
    for tolerance in STRICTER:
        counts = []
        for condition in CONDITIONS:
            given = {s.question.number: s.answer for s in scored[condition.id]}
            counts.append(
                sum(
                    given[q.number] is not None
                    and abs(given[q.number] - truths[q.number])
                    <= tolerance * abs(truths[q.number])
                    for q in numeric
                )
            )
        rows.append((100 * tolerance, *counts, len(numeric)))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.figure("fig-picture-a", falling.draw_forces_on_a_falling_particle)
    experiment.figure(
        "fig-picture-b", partial(falling.draw_fall_with_linear_drag, euler())
    )
    experiment.figure("fig-picture-c", fields.draw_dipole_field)
    experiment.figure("fig-picture-d", draw_strain)

    # region: replay
    truths = key()
    replays = replay_fixtures(LESSON)
    scored = scored_runs(replays, truths)
    # endregion: replay
    experiment.display("allowlist", AllowlistDisplay(answer_sheet(QUESTIONS)))
    for condition in CONDITIONS:
        experiment.display(f"run-{condition.id}", RunDisplay(*replays[condition.id]))
        experiment.number(
            f"correct-{condition.id}", sum(s.correct for s in scored[condition.id]), "d"
        )
    experiment.number("questions", len(QUESTIONS), "d")
    experiment.number("tolerance", 100 * READING_TOLERANCE, ".0f")
    experiment.number(
        "chance", sum(chance(q, truths[q.number]) for q in QUESTIONS), ".1f"
    )
    experiment.number("recorded", replays["pictures"][0].recorded)

    experiment.table(
        "ai6-answers",
        answer_rows(scored, truths),
        [
            ("question", "", "d"),
            ("picture", "", ""),
            ("kind", "", ""),
            ("with the pictures", "", ""),
            ("correct", "", ""),
            ("without the pictures", "", ""),
            ("correct", "", ""),
            ("recomputed truth", "", ""),
        ],
        "Every question with the answer of each recorded run, whether the"
        " build scores it correct, and the truth the build computed from the"
        " physics code of the lesson the picture comes from. Numbers are"
        " correct within the tolerance of a reading.",
    )
    experiment.table(
        "ai6-tally",
        tally(scored, truths),
        [
            ("answered by", "", ""),
            *((kind, "correct", "") for kind in KINDS),
            ("all", "correct", ""),
        ],
        "Correct answers by kind of question for the two recorded runs, and"
        " the expected number for a guesser that picks an option or a number"
        " in the stated range uniformly at random.",
    )
    # region: readings
    distances = readings(replay_fixtures(LESSON), simulated_key())
    # endregion: readings
    experiment.figure("fig-multimodal-readings", partial(draw_readings, distances))
    experiment.table(
        "ai6-stricter",
        stricter(scored, truths),
        [
            ("tolerance", "%", ".0f"),
            ("with the pictures", "correct", "d"),
            ("without the pictures", "correct", "d"),
            ("numeric questions", "", "d"),
        ],
        "The numeric answers each run gets right if the tolerance of a reading"
        " is made stricter. The score of the lesson uses the first row, fixed"
        " before the runs were recorded.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
