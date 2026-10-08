"""Lesson A1: an agent finds the best launch angle of a ball with drag.

The experiment is the tennis ball of the projectile lesson. The agent may call
exactly two functions of ``pbc`` through the allowlist below, each with
bounded arguments. It cannot change the ball, run code, or touch a file.

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.projectile_lab

Record the replay fixture of the lesson from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.projectile_lab --record
"""

import argparse
import datetime
import sys
from pathlib import Path

import numpy as np

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.mechanics.drag import drag_constant
from pbc.mechanics.projectile import drag_free_range, projectile_range

# The ball: the tennis ball of lesson M3.
MASS = 0.058  # kg
DIAMETER = 0.067  # m
DRAG = drag_constant(1.2, 0.5, np.pi * (DIAMETER / 2) ** 2)  # kg/m

SYSTEM = (
    "You are a careful experimenter. You can only use the tools you are given."
    " Numerical results depend on the time step dt: check that a result has"
    " converged before you trust it. Report your conclusion in plain text and"
    " give the evidence for it."
)
TASK = (
    "A tennis ball is thrown at 25 m/s from the ground, with air drag. Find the"
    " launch angle, to within one degree, at which it lands furthest away, and"
    " say by how much that range exceeds the range at 45 degrees. Use as few"
    " simulation runs as you can."
)
MAX_STEPS = 12  # model messages per run
# A recomputed tool result may differ from the recorded one by this much, in
# relative and in absolute terms. The simulation is deterministic, so the
# allowance covers the last digits that differ between machines.
TOLERANCE = 1e-6

FIXTURE = "site/lessons/agents-llm/01-an-agent-runs-an-experiment/replay.json"
REPLAY_FILE = "replay.json"  # the fixture, next to the page that uses it
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.projectile_lab --record"
    " (with OPENAI_API_KEY set)"
)


def _range_with_drag(speed: float, angle: float, dt: float) -> dict[str, float]:
    return {"range_m": projectile_range(speed, angle, MASS, DRAG, dt)}


def _range_without_drag(speed: float, angle: float) -> dict[str, float]:
    return {"range_m": float(drag_free_range(speed, angle))}


SPEED = Parameter("speed", "launch speed in m/s", 1.0, 50.0)
ANGLE = Parameter("angle", "launch angle in degrees above the horizontal", 1.0, 89.0)
TIME_STEP = Parameter(
    "dt", "simulation time step in s (smaller is slower)", 0.001, 0.05
)


def tools() -> Allowlist:
    """The allowlist of the lesson: two functions, every argument bounded."""
    return Allowlist(
        (
            Tool(
                name="range_with_drag",
                description=(
                    "Simulate the throw of the tennis ball with quadratic air"
                    " drag and return the horizontal distance in metres at which"
                    " it lands. The result depends on dt."
                ),
                parameters=(SPEED, ANGLE, TIME_STEP),
                function=_range_with_drag,
            ),
            Tool(
                name="range_without_drag",
                description=(
                    "The exact range in metres of the same throw in vacuum,"
                    " v^2 sin(2 angle) / g."
                ),
                parameters=(SPEED, ANGLE),
                function=_range_without_drag,
            ),
        )
    )


def replay_recording(recording: Recording) -> Transcript:
    """Replay ``recording`` against the current code of the lesson."""
    return replay(
        recording,
        tools(),
        system=SYSTEM,
        task=TASK,
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RECORD_COMMAND,
    )


def replay_fixture(directory: Path = Path()) -> tuple[Recording, Transcript]:
    """Load ``replay.json`` from ``directory`` and replay it."""
    recording = load_recording(directory / REPLAY_FILE)
    return recording, replay_recording(recording)


def _show(step: Step, *secrets: Secret) -> None:
    """Print a step. The loop has removed the key from the message already;
    the printed line is redacted once more, in case."""
    if step.message.text:
        print(redact(step.message.text, *secrets))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        line = f"  {call.name}({call.arguments}) -> {dict(result.content)}"
        print(redact(line, *secrets))


def main(argv: list[str] | None = None) -> int:
    """The live entry point: ask the model, print the run, optionally record.

    Only the client of ``PROVIDER`` knows which key it needs: the entry point
    reads no environment variable and takes the secrets from the client.
    """
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write the run to {FIXTURE} as the replay fixture",
    )
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Task: {TASK}\nModel: {client.model}\n")
    transcript = run(
        client,
        tools(),
        SYSTEM,
        TASK,
        MAX_STEPS,
        on_step=lambda step: _show(step, *client.secrets),
    )
    if options.record:
        today = datetime.date.today().isoformat()
        save_recording(Path(FIXTURE), transcript, today, *client.secrets)
        print(f"\nRecorded to {FIXTURE}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
