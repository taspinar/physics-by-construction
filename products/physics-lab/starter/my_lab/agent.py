"""The bounded agent route of my lab, in the harness of Physics by
Construction (ADR 004): the agent reaches the instrument only through the
allowlisted, validated ``measure`` operation, and its run is verified by
replaying a recorded trace.

Record a trace live with your own key (``uv sync --extra live``; the key
in the environment, never in a file):

    uv run python -m my_lab.agent --provider openai --out fixtures/starter-agent.json

or with the deterministic scripted policy that needs no model:

    uv run python -m my_lab.agent --scripted --out fixtures/starter-agent.json
"""

import argparse
import time
from pathlib import Path

from my_lab.sweep import make_instrument
from pbc.agents.loop import Transcript, run
from pbc.agents.replay import load_recording, replay, save_recording
from pbc.products.physics_lab.agent import (
    SYSTEM,
    TOLERANCE,
    ScriptedClient,
    measurement_tools,
)
from pbc.products.physics_lab.protocol import Config, Measurement

CONFIG = Config(low_hz=1_000.0, high_hz=25_000.0, agent_budget=12, seed=360)


def task(config: Config = CONFIG) -> str:
    """What the agent is asked to do.

    YOUR WORK: change the task, then record the trace again; a replay fails
    when the task differs from the recorded one.
    """
    return (
        "Locate the resonance of the circuit, where the phase of the response"
        f" is -90 degrees, between {config.low_hz:g} Hz and {config.high_hz:g} Hz"
        f" with at most {config.agent_budget} measurements at"
        f" {config.amplitude_v:g} V, and report its frequency in Hz."
    )


def replay_trace(path: Path, config: Config = CONFIG) -> list[Measurement]:
    """Replay the trace at ``path`` on a fresh bench; every recorded call is
    executed again and must give the recorded result."""
    measurements: list[Measurement] = []
    instrument = make_instrument(config.seed)
    replay(
        load_recording(path),
        measurement_tools(instrument, config, measurements),
        system=SYSTEM,
        task=task(config),
        tolerance=TOLERANCE,
        max_steps=config.agent_budget + 1,
        rerecord="uv run python -m my_lab.agent --scripted --out " + str(path),
    )
    instrument.output_off()
    return measurements


def record(
    path: Path, client, placeholder: bool, config: Config = CONFIG
) -> Transcript:
    instrument = make_instrument(config.seed)
    tools = measurement_tools(instrument, config, [])
    transcript = run(client, tools, SYSTEM, task(config), config.agent_budget + 1)
    instrument.output_off()
    save_recording(
        path,
        transcript,
        time.strftime("%Y-%m-%d"),
        *client.secrets,
        placeholder=placeholder,
    )
    return transcript


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="python -m my_lab.agent")
    parser.add_argument("--out", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--provider")
    source.add_argument("--scripted", action="store_true")
    arguments = parser.parse_args()
    if arguments.scripted:
        client, placeholder = ScriptedClient(CONFIG), True
    else:
        from pbc.agents.providers import load_client

        client, placeholder = load_client(arguments.provider), False
    steps = record(arguments.out, client, placeholder).steps
    print(f"recorded {len(steps)} steps to {arguments.out}")
