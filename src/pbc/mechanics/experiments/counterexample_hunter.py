"""The experiment of the lesson "A counterexample hunter".

An agent that hunts for a counterexample to a claim about the energy drift
of an integrator (``pbc.agents.hunter_lab``): the bounds of its one tool,
the replay of two recorded hunts, and the judge that decides from the
recomputed results, not from what the agent says; then physical constraints
as hunts for a counterexample to a closed form of the oscillator's motion
(``pbc.verification.constraints``), on the exact motion and on four closed
forms that are wrong on purpose. Run it as a program to
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
from pbc.mechanics.dynamics import State
from pbc.mechanics.oscillator import energy, harmonic_motion
from pbc.verification.constraints import (
    CHECKS,
    SCALINGS,
    TOLERANCE,
    WEAK,
    Case,
    conservation,
    examine,
    symmetry,
)
from pbc.verification.faulty_motion import EXERCISE, GALLERY

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


# --- Physical constraints as hunts for a counterexample (SA7). ---

# The exact motion and the four closed forms that are wrong on purpose.
CANDIDATES = (
    ("exact motion", harmonic_motion),
    *((g.name, g.motion) for g in GALLERY),
)
# The start of the second case, at a ratio k / m of one per second squared.
UNIT_RATIO = (Case(mass=1.0, k=1.0, x0=0.12, v0=-0.45),)


def constraint_rows():
    """One row per candidate: the outcome of each check."""
    return [
        (name, *(f.outcome for f in examine(motion))) for name, motion in CANDIDATES
    ]


def _witness_row(name, finding):
    case = finding.case
    return (
        name,
        finding.check,
        finding.trial,
        case.mass,
        case.k,
        case.x0,
        case.v0,
        finding.deviation,
    )


def witness_rows(candidates):
    """One row per counterexample: the candidate, the check, the trial, the
    case, and the relative deviation."""
    return [
        _witness_row(name, f)
        for name, motion in candidates
        for f in examine(motion)
        if f.counterexample
    ]


WITNESS_COLUMNS = [
    ("candidate", "", ""),
    ("check", "", ""),
    ("trial", "", ""),
    ("m", "kg", "g"),
    ("k", "N/m", "g"),
    ("x0", "m", "g"),
    ("v0", "m/s", "g"),
    ("relative deviation", "", ".2f"),
]


def draw_constraint_witnesses() -> Figure:
    """Two witnesses, each beside what its constraint demands: the energy of
    the frequency in hertz against the exact motion's, and the arctangent's
    motion from the mirrored start against the mirror image of its motion
    from the start."""
    hertz = conservation(GALLERY[3].motion)
    mirror = symmetry(GALLERY[1].motion)
    demanded = {"linestyle": "--", "color": FIGURE_COLOURS[0]}
    wrong = {"linestyle": "-", "color": FIGURE_COLOURS[1]}
    with figure_style():
        fig, (top, bottom) = plt.subplots(2, 1, figsize=figsize("pair", legend=3))
        case = hertz.case
        t = np.linspace(0.0, case.times()[-1], 400)
        for motion, style in ((harmonic_motion, demanded), (GALLERY[3].motion, wrong)):
            e = energy(motion(case.start(), case.mass, case.k, t), case.mass, case.k)
            top.plot(t, e / e[0], **style)
        top.set_xlabel("time (s)")
        top.set_ylabel("energy over its\nstarting value")
        top.set_title("Conservation: frequency in hertz")

        case = mirror.case
        t = np.linspace(0.0, case.times()[-1], 400)
        motion = GALLERY[1].motion
        forward = motion(case.start(), case.mass, case.k, t)
        mirrored = motion(State(0.0, -case.x0, -case.v0), case.mass, case.k, t)
        bottom.plot(
            t, -forward.x[:, 0], **demanded, label="what the constraint demands"
        )
        bottom.plot(t, mirrored.x[:, 0], **wrong, label="the wrong candidate")
        bottom.plot(0.0, -case.x0, "ko", markersize=4, label="the mirrored start")
        bottom.set_xlabel("time (s)")
        bottom.set_ylabel("position (m)")
        bottom.set_title("The mirror: phase from the arctangent")
        fig.legend(*bottom.get_legend_handles_labels(), loc="outside lower center")
    return finish(fig)


def unit_ratio():
    """The checks that find the missing square root at k / m = 1 s⁻²."""
    found = examine(GALLERY[0].motion, UNIT_RATIO)
    return ", ".join(f.check for f in found if f.counterexample)


def constraints_on_the_page(experiment: Experiment) -> None:
    """The numbers, tables, and figure of the section on physical
    constraints."""
    experiment.number("constraint-tolerance", TOLERANCE, ".0e")
    experiment.number("constraint-scalings", len(SCALINGS), "d")
    experiment.number("constraint-weak", WEAK, ".0e")
    experiment.number("unit-ratio-checks", unit_ratio())
    experiment.table(
        "constraint-outcomes",
        constraint_rows(),
        [("candidate", "", ""), *((check, "", "") for check in CHECKS)],
        "The outcome of each check on each candidate: a counterexample, or"
        " none found in the trials of the check.",
    )
    experiment.table(
        "constraint-witnesses",
        witness_rows(CANDIDATES),
        WITNESS_COLUMNS,
        "The first counterexample each check found: the candidate, the trial,"
        " the case, and the relative deviation from what the constraint"
        " demands, to two decimals (the tolerance is far below).",
    )
    experiment.figure("fig-constraint-witnesses", draw_constraint_witnesses)
    experiment.table(
        "constraint-exercise",
        witness_rows([(EXERCISE.name, EXERCISE.motion)]),
        WITNESS_COLUMNS,
        "The counterexamples the checks find to the candidate of the exercise.",
    )


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
    constraints_on_the_page(experiment)
    return experiment


if __name__ == "__main__":
    main(run)
