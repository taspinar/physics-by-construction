"""The experiment of the lesson "An experimental design agent".

An agent that chooses the readings of a drag experiment
(``pbc.agents.design_lab``): the score of a design, the replay of two
recorded campaigns on a full and on a slow rig, and the judge that decides
between linear and quadratic drag from the recomputed readings. Run it as a
program to write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.experimental_design_agent out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.design_lab``.
"""

from dataclasses import replace
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents import ModelMessage, Step
from pbc.agents.design import design_score, judge
from pbc.agents.design_lab import (
    BUDGET,
    MAX_STEPS,
    RIGS,
    THRESHOLD,
    TOOL,
    linear,
    quadratic,
    replay_rig,
    tools,
)
from pbc.agents.display import AllowlistDisplay, AssessmentDisplay, RunDisplay
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main
from pbc.figure_language import figsize, figure_style, finish
from pbc.mechanics.experiments import design_strategies

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.design_lab"

# The recorded campaigns, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/04-an-experimental-design-agent"
# region: design
design = RIGS["full"].design
# endregion: design


def three_designs():
    """The score of three designs of four readings against the threshold."""
    designs = {
        "one low speed, several times": [(1, 0.5), (1, 1), (1, 2), (1, 3)],
        "several times near the calibration run": [
            (10, 1.5),
            (10, 2),
            (10, 2.5),
            (10, 3),
        ],
        "several start speeds at one time": [(20, 3), (10, 3), (5, 3), (2, 3)],
    }
    for label, pairs in designs.items():
        points = [{"initial_speed": v, "time": t} for v, t in pairs]
        print(f"{label}: score {design_score(design, points):.3g}")
    print(f"threshold: {THRESHOLD:g}")


def with_last_text(transcript, text):
    *earlier, last = transcript.steps
    message = ModelMessage(text, last.message.tool_calls)
    return replace(transcript, steps=(*earlier, Step(message, last.results)))


def what_the_agent_says(full_run, slow_run):
    """Exercise 1: the judge on a boasting agent on the slow rig and on a
    silent agent on the full rig."""
    boasting = with_last_text(
        slow_run, "Quadratic drag is confirmed: chi-square 900 against 12."
    )
    silent = with_last_text(full_run, "")
    rig = RIGS["slow"]
    print(
        "boasting agent, slow rig:",
        judge(rig.design, boasting, tools(rig.maximum_speed)).outcome,
    )
    print(
        "silent agent, full rig:",
        judge(RIGS["full"].design, silent, tools()).outcome,
    )


def forged_results(full_run):
    """Exercise 2: the judge on readings the agent forged."""
    forged = replace(
        full_run,
        steps=tuple(
            Step(
                step.message,
                tuple(
                    replace(r, content={"speed": 3.0}) if r.ok else r
                    for r in step.results
                ),
            )
            for step in full_run.steps
        ),
    )
    print("forged results:", judge(RIGS["full"].design, forged, tools()).outcome)


def draw_design(assessment) -> Figure:
    """The fraction of the start speed left after three seconds, the two
    fitted models and the readings of the campaign."""
    fits = {f.model.name: f.fit for f in assessment.fits}
    speeds = np.linspace(0.5, 20, 100)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(
            speeds,
            quadratic(speeds, 3.0, fits["quadratic drag"].value("k")) / speeds,
            label="quadratic drag, fitted",
        )
        ax.plot(
            speeds,
            linear(speeds, 3.0, fits["linear drag"].value("g")) / speeds,
            label="linear drag, fitted",
        )
        for m in assessment.measurements:
            if m.arguments["time"] == 3.0:
                ax.plot(
                    m.arguments["initial_speed"],
                    m.value / m.arguments["initial_speed"],
                    "ko",
                    markersize=4,
                )
        ax.set_xlabel("start speed (m/s)")
        ax.set_ylabel("fraction of the start\nspeed left after 3 s")
        ax.set_ylim(0, 1.05)
        ax.legend()
    return finish(fig)


def a_fifth_reading():
    """Exercise 3: the score of the best design with and without a fifth
    reading."""
    base = [(20, 3), (10, 3), (5, 3), (2, 3)]
    for label, pairs in (("four", base), ("five", [*base, (15, 3)])):
        points = [{"initial_speed": v, "time": t} for v, t in pairs]
        print(label, f"{design_score(design, points):.4g}")


def slow_difference(slow_assessment):
    """Exercise 4: the difference of the two models on the slow rig."""
    print(f"{slow_assessment.difference:.3g}")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.display("allowlist", AllowlistDisplay(tools()))
    experiment.number("tool", TOOL)
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    with experiment.capture("three-designs"):
        three_designs()

    # region: replay
    recording, full_run, assessment = replay_rig("full", LESSON)
    slow_recording, slow_run, slow_assessment = replay_rig("slow", LESSON)
    # endregion: replay
    experiment.display("full-run", RunDisplay(recording, full_run, authored=True))
    experiment.display("full-assessment", AssessmentDisplay(assessment))
    experiment.display("slow-run", RunDisplay(slow_recording, slow_run, authored=True))
    experiment.display("slow-assessment", AssessmentDisplay(slow_assessment))

    with experiment.capture("what-the-agent-says"):
        what_the_agent_says(full_run, slow_run)
    with experiment.capture("forged-results"):
        forged_results(full_run)
    experiment.figure("fig-design", partial(draw_design, assessment))
    with experiment.capture("a-fifth-reading"):
        a_fifth_reading()
    with experiment.capture("slow-difference"):
        slow_difference(slow_assessment)
    experiment.figure("fig-strategies", design_strategies.extend(experiment))
    return experiment


if __name__ == "__main__":
    main(run)
