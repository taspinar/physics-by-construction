"""The experiment of the lesson "A counterexample hunter".

An agent that hunts for a counterexample to a claim about the energy drift
of an integrator (``pbc.agents.hunter_lab``): the bounds of its one tool,
the replay of two recorded hunts, and the judge that decides from the
recomputed results, not from what the agent says. Run it as a program to
write the figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.counterexample_hunter out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.hunter_lab``.
"""

from dataclasses import replace
from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from pbc.agents import ModelMessage, Step, ToolCall
from pbc.agents.display import AllowlistDisplay, RunDisplay, VerdictDisplay
from pbc.agents.hunter import judge
from pbc.agents.hunter_lab import (
    BUDGET,
    FALSE_CLAIM,
    MAX_STEPS,
    OPEN_CLAIM,
    TOOL,
    replay_hunt,
    tools,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, figsize, figure_style, finish

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.hunter_lab"

# The recorded hunts, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/02-a-counterexample-hunter"
# region: good
good = {"method": "velocity Verlet", "steps_per_period": 32, "periods": 5}
# endregion: good


def bounds():
    """Seven experiments that a model might ask for, through the
    allowlist."""
    allowlist = tools()
    attempts = [
        ("a valid experiment", good),
        ("a method that is not in the list", {**good, "method": "os.system"}),
        ("a method that is not even text", {**good, "method": ["velocity Verlet"]}),
        ("zero steps per period", {**good, "steps_per_period": 0}),
        ("a million periods", {**good, "periods": 1_000_000}),
        ("a fractional number of steps", {**good, "steps_per_period": 32.5}),
        ("an extra argument", {**good, "code": "1+1"}),
    ]
    for label, arguments in attempts:
        result = allowlist.dispatch(ToolCall("x", TOOL, arguments))
        outcome = (
            f"{result.content['max_energy_drift']:.4f}"
            if result.ok
            else result.content["error"]
        )
        print(f"{label}: {outcome}")


def budget():
    """The same experiment until the budget runs out."""
    allowlist = tools()
    for number in range(1, BUDGET + 2):
        result = allowlist.dispatch(ToolCall(str(number), TOOL, good))
        if not result.ok:
            print(f"experiment {number}: {result.content['error']}")


def with_last_text(run, text):
    *earlier, last = run.steps
    message = ModelMessage(text, last.message.tool_calls)
    return replace(run, steps=(*earlier, Step(message, last.results)))


def what_the_agent_says(transcript, open_transcript):
    """Exercise 1: the judge on a silent agent with a real counterexample and
    on a boasting agent without one."""
    silent = with_last_text(transcript, "")
    boasting = with_last_text(
        open_transcript,
        "Counterexample found: Verlet at 16 steps per period drifts by 90 per cent.",
    )
    print(
        "silent agent, real counterexample:",
        judge(FALSE_CLAIM, silent, tools()).outcome,
    )
    print(
        "boasting agent, no counterexample:",
        judge(OPEN_CLAIM, boasting, tools()).outcome,
    )


def forged_results(open_transcript):
    """Exercise 2: the judge on results that the agent forged."""
    forged = replace(
        open_transcript,
        steps=tuple(
            Step(
                step.message,
                tuple(
                    replace(r, content={"max_energy_drift": 0.9}) if r.ok else r
                    for r in step.results
                ),
            )
            for step in open_transcript.steps
        ),
    )
    print("forged results:", judge(OPEN_CLAIM, forged, tools()).outcome)


def draw_hunt(transcript, open_transcript) -> Figure:
    """The drift of the two methods against the step, with the limits of the
    claims and the experiments the agent ran."""
    function = tools().tool(TOOL).function
    steps = np.array([16, 20, 24, 32, 48, 64, 100, 150, 200])
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for method, claim, colour in (
            ("symplectic Euler", FALSE_CLAIM, FIGURE_COLOURS[1]),
            ("velocity Verlet", OPEN_CLAIM, FIGURE_COLOURS[0]),
        ):
            drift = [function(method, int(n), 50)["max_energy_drift"] for n in steps]
            ax.loglog(steps, drift, color=colour, label=method)
            ax.axhline(
                claim.limit, color=colour, linestyle="--", linewidth=LINE["guide"]
            )
        for hunt in (transcript, open_transcript):
            for step in hunt.steps:
                for call, result in zip(
                    step.message.tool_calls, step.results, strict=True
                ):
                    if result.ok and call.arguments["periods"] == 50:
                        ax.plot(
                            call.arguments["steps_per_period"],
                            result.content["max_energy_drift"],
                            "ko",
                            markersize=4,
                        )
        # At this width the labels of the log axis's minor ticks run into
        # each other: four labelled steps instead.
        ax.set_xticks([20, 50, 100, 200], labels=["20", "50", "100", "200"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("steps per period")
        ax.set_ylabel("largest energy drift")
        ax.legend()
    return finish(fig)


def smallest_counterexample():
    """Exercise 3: the smallest number of steps per period at which
    symplectic Euler keeps the false claim over twenty periods."""
    function = tools().tool(TOOL).function
    smallest = next(
        n
        for n in range(16, 201)
        if FALSE_CLAIM.holds_on(function("symplectic Euler", n, 20)["max_energy_drift"])
    )
    print(
        smallest,
        f"{function('symplectic Euler', smallest, 20)['max_energy_drift']:.4f}",
    )
    print(
        smallest - 1,
        f"{function('symplectic Euler', smallest - 1, 20)['max_energy_drift']:.4f}",
    )


def stricter_claim(open_transcript):
    """Exercise 4: the judge on the open hunt against a stricter claim."""
    stricter = replace(OPEN_CLAIM, limit=0.035)
    new_verdict = judge(stricter, open_transcript, tools())
    print(new_verdict.outcome, new_verdict.witness)
    print("original claim:", judge(OPEN_CLAIM, open_transcript, tools()).outcome)


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.display("allowlist", AllowlistDisplay(tools()))
    experiment.number("false-claim", FALSE_CLAIM.statement)
    experiment.number("open-claim", OPEN_CLAIM.statement)
    experiment.number("tool", TOOL)
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    with experiment.capture("bounds"):
        bounds()
    with experiment.capture("budget"):
        budget()

    # region: replay
    recording, transcript, verdict = replay_hunt("false", LESSON)
    open_recording, open_transcript, open_verdict = replay_hunt("open", LESSON)
    # endregion: replay
    experiment.display("false-run", RunDisplay(recording, transcript, authored=True))
    experiment.display("false-verdict", VerdictDisplay(verdict))
    experiment.display(
        "open-run", RunDisplay(open_recording, open_transcript, authored=True)
    )
    experiment.display("open-verdict", VerdictDisplay(open_verdict))

    with experiment.capture("what-the-agent-says"):
        what_the_agent_says(transcript, open_transcript)
    with experiment.capture("forged-results"):
        forged_results(open_transcript)
    experiment.figure("fig-hunt", partial(draw_hunt, transcript, open_transcript))
    with experiment.capture("smallest-counterexample"):
        smallest_counterexample()
    with experiment.capture("stricter-claim"):
        stricter_claim(open_transcript)
    return experiment


if __name__ == "__main__":
    main(run)
