"""Lesson AE2's tasks beyond a number: a diagram task and a drawn world
(F149; ``docs/discovery-protocol.md``).

**The diagram task.** Two pictures of the benchmark's own kinds of system,
drawn by the build from ``pbc.mechanics``: three drag-free trajectories of
one launch speed and a wall (picture A), and a mass on a spring released at
two amplitudes (picture B). Nine questions in four categories: reading a
value off a picture, a concept, the physical tool (what the apparatus can do
and where it is informative), and a counterfactual. They are answered
through the tool ``answer`` of ``pbc.agents.vision`` and scored by the build
against a key it computes from the same physics that draws the pictures.
The task describes the pictures without giving an answer; the launch speed,
the wall, and the period are only on the pictures.

**The drawn world.** A world of the central-force box whose strength and
exponent the judge draws from a stated distribution, with three held-out
settings also drawn, beyond the bounds of the probes. The agent is told
nothing of the form (condition ``none``). The distribution and the seed of
the draw are the judge's configuration. The seed and the drawn values reach
no prompt, tool, or page; the page states only the distribution.

The runs are replay fixtures on the page of AE2; their records, the
``TraceInfo`` of each, are kept here and checked against the fixtures by a
test.
"""

import argparse
import datetime
import json
import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from scipy.constants import g as EARTH

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import Picture
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.vision import Question, Source, answer_sheet
from pbc.authoring import FIGURE_COLOURS
from pbc.discovery.baselines import BaselineResult, least_squares, random_probe
from pbc.discovery.force_lab import BUDGET, MAX_STEPS, SEED, TOLERANCE, Run
from pbc.discovery.protocol import (
    PROMPT_VERSION,
    CostRecord,
    Protocol,
    Score,
    TraceInfo,
    prompt_sha,
    prompts,
    score_transcript,
)
from pbc.discovery.tools import environment_allowlist
from pbc.figure_language import LINE, figsize, figure_style, finish
from pbc.mechanics.dynamics import State, newton, weight
from pbc.mechanics.oscillator import angular_frequency, harmonic_motion
from pbc.mechanics.projectile import drag_free_range, launch

DIRECTORY = "site/lessons/agents-llm/12-interactive-discovery-benchmarks"

# Who recorded the runs of F149, and when.
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-11-19"

# ---------------------------------------------------------------------------
# The diagram task

# Picture A: one launch speed, three angles, a wall; Earth's gravity.
LAUNCH_SPEED = 20.0  # m/s
ANGLES = (20.0, 45.0, 70.0)  # degrees above the horizontal
WALL_DISTANCE = 30.0  # m from the launcher
WALL_HEIGHT = 5.0  # m
FAR = 45.0  # m, the distance question 1 asks about
LOWEST, HIGHEST = 10.0, 80.0  # degrees, the angles the launcher allows
# Picture B: a mass on a spring of public stiffness, two amplitudes.
SPRING_MASS = 1.0  # kg
SPRING_PERIOD = 1.5  # s
SPRING_STIFFNESS = SPRING_MASS * (2.0 * math.pi / SPRING_PERIOD) ** 2  # N/m
AMPLITUDES = (0.5, 1.0)  # m
WINDOW = 3.0  # s, the times the spring's measure tool allows

ITEM_STEPS = 6  # model messages per run
ITEM_TOLERANCE = 1e-9  # the acknowledgements are exact


def flight(angle: float, g: float = EARTH, points: int = 400) -> np.ndarray:
    """Positions, shape (points, 2), of a ball launched from the ground at
    ``LAUNCH_SPEED`` and ``angle`` (degrees) until it lands, under its weight
    alone: x0 + v t + a t^2 / 2 with the acceleration of Newton's second
    law, which is constant, so the motion is exact."""
    start = launch(LAUNCH_SPEED, angle)
    a = newton(1.0, weight(1.0, [0.0, -g]))(0.0, start.x, start.v)
    landed = -2.0 * start.v[1] / a[1]
    t = np.linspace(0.0, landed, points)[:, np.newaxis]
    return start.x + start.v * t + 0.5 * a * t**2


def height_at(angle: float, distance: float, g: float = EARTH) -> float:
    """The height in m of the ball of ``angle`` over the point ``distance``
    m from the launcher; negative when it has landed before it."""
    if distance > drag_free_range(LAUNCH_SPEED, angle, g):
        return -1.0
    path = flight(angle, g, 20001)
    return float(np.interp(distance, path[:, 0], path[:, 1]))


def spring_motion(amplitude: float, times: np.ndarray) -> np.ndarray:
    """The displacement in m of the spring's mass released at rest from
    ``amplitude`` m, at ``times`` (s)."""
    start = State(t=0.0, x=[amplitude], v=[0.0])
    return harmonic_motion(start, SPRING_MASS, SPRING_STIFFNESS, times).x[:, 0]


def draw_launcher() -> Figure:
    """Picture A: three trajectories of one launch speed, and the wall."""
    styles = ("-", "--", "-.")
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for k, angle in enumerate(ANGLES):
            path = flight(angle)
            ax.plot(
                path[:, 0],
                path[:, 1],
                linestyle=styles[k],
                color=FIGURE_COLOURS[k],
                linewidth=LINE["model"],
            )
            top = int(np.argmax(path[:, 1]))
            ax.annotate(
                f"{angle:g}°",
                path[top],
                xytext=(16 if angle == 45.0 else 0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
            )
        ax.add_patch(
            plt.Rectangle(
                (WALL_DISTANCE - 0.6, 0.0),
                1.2,
                WALL_HEIGHT,
                color=FIGURE_COLOURS[2],
                hatch="///",
                fill=False,
            )
        )
        ax.annotate(
            "wall",
            (WALL_DISTANCE + 0.8, WALL_HEIGHT),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
        )
        ax.text(0.5, 21.5, f"launch speed {LAUNCH_SPEED:g} m/s", va="bottom")
        ax.set_xlim(0.0, 50.0)
        ax.set_ylim(0.0, 24.0)
        ax.set_xticks(np.arange(0.0, 51.0, 10.0))
        ax.set_xlabel("distance from the launcher (m)")
        ax.set_ylabel("height (m)")
    return finish(fig, grid=True)


def draw_spring() -> Figure:
    """Picture B: the displacement of the spring's mass at two amplitudes."""
    times = np.linspace(0.0, WINDOW, 601)
    styles = ("--", "-")
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        for k, amplitude in enumerate(AMPLITUDES):
            ax.plot(
                times,
                spring_motion(amplitude, times),
                linestyle=styles[k],
                color=FIGURE_COLOURS[k],
                linewidth=LINE["model"],
                label=f"from {amplitude:g} m",
            )
        ax.axhline(0.0, color=FIGURE_COLOURS[2], linewidth=LINE["guide"])
        ax.set_xlim(0.0, WINDOW)
        ax.set_ylim(-1.2, 1.8)
        ax.set_xticks(np.arange(0.0, WINDOW + 0.01, 0.5))
        ax.set_xlabel("time since the release (s)")
        ax.set_ylabel("displacement (m)")
        ax.legend(loc="upper center", ncols=2, title="released at rest")
    return finish(fig, grid=True)


PICTURES = (
    Source(
        "A",
        "interactive-discovery-benchmarks",
        "fig-task-launcher",
        "three trajectories of balls launched from the ground at one speed and"
        " three angles, and a wall",
        draw_launcher,
    ),
    Source(
        "B",
        "interactive-discovery-benchmarks",
        "fig-task-spring",
        "the displacement against time of a mass on a spring, released from"
        " rest at two amplitudes",
        draw_spring,
    ),
)

YES_NO = ("yes", "no")
WHICH_ANGLE = (
    "the 20-degree trajectory",
    "the 45-degree trajectory",
    "the 70-degree trajectory",
    "none of them",
)
FACTORS = ("halved", "unchanged", "doubled", "four times larger")
DIRECTIONS = ("up", "down", "zero", "forward, along the motion")
WHEN = ("in the first second", "in the last second", "equally at every time")
SPEEDS = ("zero", "the largest it reaches", "half the largest it reaches")

QUESTIONS = (
    Question(
        1,
        "A",
        "property",
        f"Can this launcher, at its speed and at any angle from {LOWEST:g} to"
        f" {HIGHEST:g} degrees, land a ball more than {FAR:g} m away?",
        YES_NO,
    ),
    Question(
        2,
        "A",
        "spatial",
        "Which of the three drawn trajectories passes over the wall?",
        WHICH_ANGLE,
    ),
    Question(
        3,
        "A",
        "counterfactual",
        "If gravity were half as strong and the launch the same, the landing"
        " distance of the 45-degree trajectory would be:",
        FACTORS,
    ),
    Question(
        4,
        "A",
        "property",
        "Read the landing distance of the 20-degree trajectory.",
        unit="m",
        low=0.0,
        high=60.0,
    ),
    Question(
        5,
        "B",
        "property",
        "Read the period of the oscillation.",
        unit="s",
        low=0.0,
        high=3.0,
    ),
    Question(
        6,
        "B",
        "counterfactual",
        "If the mass were released from twice the larger amplitude, its period"
        " would be:",
        FACTORS,
    ),
    Question(
        7,
        "B",
        "property",
        f"An instrument reads the displacement at any time from 0 to {WINDOW:g}"
        " s, with the same noise at every time, and you want the frequency."
        " When does one reading tell you most about it?",
        WHEN,
    ),
    Question(
        8,
        "A",
        "property",
        "At the top of the 45-degree trajectory, which way does the ball accelerate?",
        DIRECTIONS,
    ),
    Question(
        9,
        "B",
        "property",
        "When the displacement passes through zero, the speed of the mass is:",
        SPEEDS,
    ),
)

# What each question asks of the one who answers it (lesson AE1).
CATEGORIES = ("reading", "concept", "physical tool", "counterfactual")
CATEGORY = {
    1: "physical tool",
    2: "physical tool",
    3: "counterfactual",
    4: "reading",
    5: "reading",
    6: "counterfactual",
    7: "physical tool",
    8: "concept",
    9: "concept",
}

ITEM_SHARED = (
    "You answer questions about two pictures of physical systems. Use the tool"
    " answer once per question; an answer cannot be changed and you are not"
    " told whether it is right. When you cannot tell, give your best estimate"
    " and say so in your message. When every question is answered, end with a"
    " short message that says which answers you read from a picture and which"
    " you inferred."
)
ITEM_SYSTEM_WITH_PICTURES = (
    ITEM_SHARED + " The two pictures, A and B, are attached to the task, in order."
)
ITEM_SYSTEM_WITHOUT_PICTURES = (
    ITEM_SHARED + " The pictures are not available to you: only their descriptions"
    " in the task. Answer from what you know."
)
ITEM_TASK = (
    "Two pictures are described below.\n"
    + "\n".join(f"Picture {s.label}: {s.caption}." for s in PICTURES)
    + "\n\nAnswer every question with the tool answer.\n"
    + "\n".join(q.prompt() for q in QUESTIONS)
)


def _nearest(options: tuple[float, ...], value: float) -> int:
    return 1 + int(np.argmin(np.abs(np.array(options) - value)))


def _period(amplitude: float) -> float:
    """The period of the spring's motion from ``amplitude``, measured from
    the motion: twice the time between the first two zero crossings."""
    times = np.linspace(0.0, WINDOW, 300001)
    x = spring_motion(amplitude, times)
    crossings = times[1:][np.diff(np.sign(x)) != 0]
    return float(2.0 * (crossings[1] - crossings[0]))


def diagram_key() -> dict[int, float]:
    """The answer to every question, computed from the physics that draws
    the pictures. Options are numbered from 1."""
    # region: launcher
    angles = np.linspace(LOWEST, HIGHEST, 7001)
    farthest = max(drag_free_range(LAUNCH_SPEED, a) for a in angles)
    over = [height_at(a, WALL_DISTANCE) > WALL_HEIGHT for a in ANGLES]
    if sum(over) > 1:
        raise ValueError("more than one drawn trajectory passes over the wall")
    halved = drag_free_range(LAUNCH_SPEED, 45.0, EARTH / 2) / drag_free_range(
        LAUNCH_SPEED, 45.0
    )
    # endregion: launcher
    top = launch(LAUNCH_SPEED, 45.0)
    accel = newton(1.0, weight(1.0, [0.0, -EARTH]))(0.0, top.x, top.v)
    direction = 2 if accel[1] < 0 and accel[0] == 0 else 1
    # region: spring
    ratio = _period(2.0 * max(AMPLITUDES)) / _period(max(AMPLITUDES))
    omega = angular_frequency(SPRING_MASS, SPRING_STIFFNESS)
    times = np.linspace(0.0, WINDOW, 3001)
    step = 1e-6 * omega

    def x_at(w: float) -> np.ndarray:
        start = State(t=0.0, x=[max(AMPLITUDES)], v=[0.0])
        return harmonic_motion(start, SPRING_MASS, SPRING_MASS * w**2, times).x[:, 0]

    sensitivity = ((x_at(omega + step) - x_at(omega - step)) / (2 * step)) ** 2
    first = float(np.mean(sensitivity[times <= 1.0]))
    last = float(np.mean(sensitivity[times >= WINDOW - 1.0]))
    # endregion: spring
    when = 1 if first > 2 * last else (2 if last > 2 * first else 3)
    motion = harmonic_motion(
        State(t=0.0, x=[1.0], v=[0.0]), SPRING_MASS, SPRING_STIFFNESS, times
    )
    zero = int(np.argmin(np.abs(motion.x[:, 0])))
    speed_ratio = abs(motion.v[zero, 0]) / np.max(np.abs(motion.v[:, 0]))
    return {
        1: 1 if farthest > FAR else 2,
        2: over.index(True) + 1 if any(over) else 4,
        3: _nearest((0.5, 1.0, 2.0, 4.0), halved),
        4: drag_free_range(LAUNCH_SPEED, 20.0),
        5: _period(max(AMPLITUDES)),
        6: _nearest((0.5, 1.0, 2.0, 4.0), ratio),
        7: when,
        8: direction,
        9: _nearest((0.0, 1.0, 0.5), speed_ratio),
    }


# The key as computed when the runs were recorded (judge configuration,
# never in a tool or a prompt). A test compares it with ``diagram_key``:
# when the physics of a picture changes, the runs answered another picture
# and must be recorded again.
RECORDED_KEY = {
    1: 2,
    2: 2,
    3: 3,
    4: 26.2184,
    5: 1.5000,
    6: 2,
    7: 2,
    8: 2,
    9: 2,
}


@dataclass(frozen=True)
class ItemRun:
    """One recorded run of the diagram task: with the pictures or without."""

    id: str
    title: str
    system: str
    with_pictures: bool
    fixture: str
    model_calls: int


ITEM_RUNS = (
    ItemRun(
        "pictures",
        "with the pictures",
        ITEM_SYSTEM_WITH_PICTURES,
        True,
        "replay-picturetask.json",
        4,
    ),
    ItemRun(
        "text",
        "without the pictures",
        ITEM_SYSTEM_WITHOUT_PICTURES,
        False,
        "replay-texttask.json",
        4,
    ),
)


def pictures() -> tuple[Picture, ...]:
    """The two pictures, drawn again by the build."""
    return tuple(source.picture() for source in PICTURES)


def item_record_command() -> str:
    return "uv run --extra openai python -m pbc.discovery.tasks items --record"


def replay_items(item: ItemRun, directory: Path) -> tuple[Recording, Transcript]:
    """Replay the recorded run ``item`` from ``directory`` with a fresh
    answer sheet."""
    recording = load_recording(directory / item.fixture)
    if (recording.model, recording.recorded) != (MODEL, RECORDED):
        raise ValueError(f"{item.fixture} is not the run recorded for F149")
    transcript = replay(
        recording,
        answer_sheet(QUESTIONS),
        system=item.system,
        task=ITEM_TASK,
        tolerance=ITEM_TOLERANCE,
        max_steps=ITEM_STEPS,
        rerecord=item_record_command(),
    )
    return recording, transcript


# ---------------------------------------------------------------------------
# The drawn world

# The judge's draw: the seed of the world the agent was given, and the
# distribution every world is drawn from. Public on the page: the
# distribution; never the values it gave.
WORLD_SEED = 1491  # the judge's configuration
STRENGTHS = (2.0, 50.0)  # N m^p/kg, drawn uniformly in its logarithm
EXPONENTS = (1.2, 3.8)  # drawn uniformly
EVALUATION_DISTANCES = (5.0, 12.0)  # m, beyond the probes' 4 m
EVALUATION_MASSES = (0.5, 5.0)  # kg
EVALUATION_CASES = 3
CONDITION = "none"  # told nothing of the form


def drawn_world(seed: int) -> tuple[dict[str, float], tuple[dict[str, float], ...]]:
    """A hidden world of the central-force box and its held-out settings,
    drawn with ``seed``: the strength uniformly in its logarithm, the
    exponent uniformly, and the evaluation cases beyond the probes' reach."""
    rng = np.random.default_rng(seed)
    world = {
        "strength": float(np.exp(rng.uniform(*np.log(STRENGTHS)))),
        "exponent": float(rng.uniform(*EXPONENTS)),
    }
    cases = tuple(
        {
            "distance": float(rng.uniform(*EVALUATION_DISTANCES)),
            "mass": float(rng.uniform(*EVALUATION_MASSES)),
        }
        for _ in range(EVALUATION_CASES)
    )
    return world, cases


def world_protocol(seed: int = WORLD_SEED) -> Protocol:
    """The protocol of the drawn world of ``seed``: the benchmark's budget,
    step limit, seed of the noise, and tolerance; the drawn world and
    cases."""
    world, cases = drawn_world(seed)
    return Protocol(
        version=f"f149-drawn-world-1-{seed}",
        environment="central-force",
        world=world,
        budget=BUDGET,
        seeds=(SEED,),
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        held_out=cases,
    )


PROTOCOL = world_protocol()
# The worlds the baselines are run on besides the agent's, for their spread.
OTHER_WORLDS = tuple(range(1, 21))
# The seeds of random selection on the agent's world, besides the
# benchmark's own.
PROBE_SEEDS = tuple(range(1, 21))


def world_prompts() -> tuple[str, str]:
    """The system prompt and the task of the drawn world: the condition
    ``none`` of ``pbc.discovery.prompts``."""
    return prompts(PROTOCOL.make(SEED), CONDITION)


WORLD_RUN = Run(
    "drawn-world",
    CONDITION,
    "replay-drawnworld.json",
    TraceInfo(
        protocol=PROTOCOL.version,
        environment=PROTOCOL.environment,
        condition=CONDITION,
        seed=SEED,
        prompt_version=PROMPT_VERSION,
        prompt_sha256="81719a6367550621d8800441da0491b122ed83ca909e9aee29cce35ad6cf93c7",
        model=MODEL,
        recorded=RECORDED,
        # The sub-agent's session reported no token counts and no price.
        cost=CostRecord(6, 17, None, None, None),
    ),
)


def world_record_command() -> str:
    return "uv run --extra openai python -m pbc.discovery.tasks world --record"


def replay_world(directory: Path) -> tuple[Recording, Transcript, Score]:
    """Replay the drawn-world run from ``directory`` and score it again."""
    from pbc.discovery.force_lab import replay_entry

    system, task = world_prompts()
    return replay_entry(
        WORLD_RUN,
        PROTOCOL,
        directory,
        system,
        task,
        environment_allowlist,
        world_record_command(),
    )


def world_baselines(
    protocol: Protocol = PROTOCOL, seed: int = SEED
) -> tuple[BaselineResult, ...]:
    """The baselines of ``pbc.discovery`` on a drawn world with its budget."""
    from pbc.discovery.baselines import run_baselines

    return run_baselines(protocol.make(SEED), seed)


def world_random_fit(protocol: Protocol, seed: int) -> BaselineResult:
    """Random selection with ``seed`` and least squares on a drawn world."""
    world = protocol.make(SEED)
    return least_squares(
        world, random_probe(world, seed), f"random + least squares, seed {seed}"
    )


def withheld_unreachable(protocol: Protocol = PROTOCOL) -> dict[str, bool]:
    """The checks that the drawn truth and the evaluation cases are out of
    the agent's reach (I27), each True when it holds:

    - the tools are ``measure`` and ``submit`` and nothing else;
    - no drawn value occurs in the prompt or the tool specifications;
    - ``measure`` refuses every evaluation case;
    - no public attribute of the world holds a drawn value.
    """
    world = protocol.make(SEED)
    allowlist = environment_allowlist(world)
    system, task = prompts(world, CONDITION)
    drawn = [*protocol.world.values()] + [
        v for case in protocol.held_out_settings() for v in case.values()
    ]
    shown = json.dumps([system, task, [str(s) for s in allowlist.specs()]])

    def mentions(value: float) -> bool:
        return any(f"{value:.{d}g}" in shown for d in (3, 4, 6, 12))

    def refused(case: Mapping[str, float]) -> bool:
        try:
            protocol.make(SEED).measure(**case)
        except ValueError:
            return True
        return False

    public = [
        getattr(world, name)
        for name in dir(world)
        if not name.startswith("_") and isinstance(getattr(world, name), (int, float))
    ]
    return {
        "tools": sorted(s.name for s in allowlist.specs()) == ["measure", "submit"],
        "prompt and tools": not any(mentions(v) for v in drawn),
        "evaluation cases refused": all(
            refused(c) for c in protocol.held_out_settings()
        ),
        "public attributes": not any(
            math.isclose(p, v, rel_tol=1e-9) for p in public for v in drawn
        ),
    }


# ---------------------------------------------------------------------------
# The live runs


def _show(step: Step) -> None:
    if step.message.text:
        print(step.message.text)
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(f"  {call.name}({call.arguments}) -> {dict(result.content)}")


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run the diagram task in both conditions
    (``items``) or the drawn world (``world``), print it, and optionally
    record it over its fixture in ``DIRECTORY``."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("task", choices=("items", "world"))
    parser.add_argument("--record", action="store_true")
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    today = datetime.date.today().isoformat()
    if options.task == "items":
        for item in ITEM_RUNS:
            print(f"\n== {item.title} ({client.model}) ==\n")
            transcript = run(
                client,
                answer_sheet(QUESTIONS),
                item.system,
                ITEM_TASK,
                ITEM_STEPS,
                on_step=_show,
                pictures=pictures() if item.with_pictures else (),
            )
            if options.record:
                path = Path(DIRECTORY) / item.fixture
                save_recording(path, transcript, today, *client.secrets)
                print(f"\nRecorded to {path}. Review it before you commit it.")
        return 0
    system, task = world_prompts()
    transcript = run(
        client,
        environment_allowlist(PROTOCOL.make(SEED)),
        system,
        task,
        PROTOCOL.max_steps,
        on_step=_show,
    )
    score = score_transcript(PROTOCOL, transcript, SEED)
    print(f"\nHeld-out error {score.held_out_error:.3g}: {score.outcome}\n")
    if options.record:
        path = Path(DIRECTORY) / WORLD_RUN.fixture
        save_recording(path, transcript, today, *client.secrets)
        print(
            f"Recorded to {path}. Review it, then set the model, the date, and"
            f" the cost in WORLD_RUN of {__name__}; the prompt SHA-256 is"
            f" {prompt_sha(system, task)}."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
