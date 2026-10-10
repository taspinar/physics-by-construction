"""Lesson A2: an agent hunts for a counterexample to a claim about an
integrator.

The agent may call one function of ``pbc`` through the allowlist below, with
bounded arguments and a budget of experiments: the largest drift of the energy
of the course's oscillator under one of its four integrators. Two claims are
put to it. The harness, not the agent, decides what was found
(``pbc.agents.hunter``).

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.hunter_lab --claim false

Record the replay fixture of a claim from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.hunter_lab --claim false --record
"""

import argparse
import datetime
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.hunter import FalsifiableClaim, Verdict, judge
from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Choice, Parameter, Tool
from pbc.mechanics.dynamics import simulate
from pbc.mechanics.integrators import INTEGRATORS
from pbc.mechanics.oscillator import energy
from pbc.verification.checks import MASS, OSCILLATOR, PERIOD, RELEASED, K
from pbc.verification.estimates import invariant_drift

METHODS = {integrator.name: integrator.step for integrator in INTEGRATORS}

SYSTEM = (
    "You are a careful experimenter who tries to refute claims. You can only"
    " use the tools you are given, and only a limited number of experiments."
    " A counterexample is an experiment, inside the domain of the claim, whose"
    " result breaks it: name the experiment's arguments and result. If you"
    " find none, say that you found none and what you tried. Do not say that"
    " the claim is true because your experiments did not refute it."
)
BUDGET = 8  # experiments per claim
MAX_STEPS = 12  # model messages per run
# A recomputed tool result may differ from the recorded one by this much
# (relative and absolute): the simulation is deterministic, so this covers the
# last digits that differ between machines.
TOLERANCE = 1e-6

# The domain of both claims: the oscillator of the course, steps and periods
# inside the bounds of the tool.
STEPS = (16, 200)
PERIODS = (1, 50)
TOOL = "oscillator_energy_drift"
RESULT = "max_energy_drift"

FALSE_CLAIM = FalsifiableClaim(
    statement=(
        "Symplectic Euler keeps the energy of the oscillator within 5 per cent"
        " of its initial value, for every step of 16 to 200 steps per period and"
        " every run of 1 to 50 periods"
    ),
    tool=TOOL,
    fixed={"method": "symplectic Euler"},
    ranges={"steps_per_period": STEPS, "periods": PERIODS},
    result=RESULT,
    limit=0.05,
    budget=BUDGET,
)
OPEN_CLAIM = FalsifiableClaim(
    statement=(
        "Velocity Verlet keeps the energy of the oscillator within 4 per cent"
        " of its initial value, for every step of 16 to 200 steps per period and"
        " every run of 1 to 50 periods"
    ),
    tool=TOOL,
    fixed={"method": "velocity Verlet"},
    ranges={"steps_per_period": STEPS, "periods": PERIODS},
    result=RESULT,
    limit=0.04,
    budget=BUDGET,
)


@dataclass(frozen=True)
class Hunt:
    """One claim put to the agent: the claim, the task text, the fixture."""

    claim: FalsifiableClaim
    task: str
    fixture: str  # the file next to the page


def _task(claim: FalsifiableClaim) -> str:
    return (
        f"Claim: {claim.statement}. Here the energy drift of a run is the"
        " largest relative deviation of the energy from its initial value over"
        f" the run. Try to refute the claim with at most {claim.budget}"
        " experiments of the tool, all inside the domain of the claim."
    )


HUNTS = {
    "false": Hunt(FALSE_CLAIM, _task(FALSE_CLAIM), "replay-false.json"),
    "open": Hunt(OPEN_CLAIM, _task(OPEN_CLAIM), "replay-open.json"),
}

LESSON = "site/lessons/agents-llm/02-a-counterexample-hunter"
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.hunter_lab --claim {name}"
    " --record (with OPENAI_API_KEY set)"
)


def _energy_drift(method: str, steps_per_period: int, periods: int) -> dict[str, float]:
    steps = steps_per_period * periods
    trajectory = simulate(
        RELEASED, OSCILLATOR, PERIOD / steps_per_period, steps, step=METHODS[method]
    )
    with np.errstate(over="ignore", invalid="ignore"):
        values = energy(trajectory, MASS, K)
    if not np.all(np.isfinite(values)):
        raise ValueError("the energy of the run is not finite")
    return {RESULT: invariant_drift(values)}


def tools() -> Allowlist:
    """The allowlist of the lesson: one function, bounded, with a budget of
    experiments. A new allowlist has a fresh budget."""
    return Allowlist(
        (
            Tool(
                name=TOOL,
                description=(
                    "Simulate the harmonic oscillator of the course (mass"
                    f" {MASS:g} kg, spring {K:g} N/m, released from rest at 1 m)"
                    " with one integrator and return the largest relative"
                    " deviation of its energy from the initial energy over the"
                    " run. The step is the period divided by steps_per_period."
                ),
                parameters=(
                    Choice("method", "the integrator", tuple(METHODS)),
                    Parameter(
                        "steps_per_period",
                        "time steps in one period of the oscillation",
                        4,
                        200,
                        integer=True,
                    ),
                    Parameter("periods", "periods to simulate", 1, 50, integer=True),
                ),
                function=_energy_drift,
            ),
        ),
        budget=BUDGET,
    )


def replay_hunt(
    name: str, directory: Path = Path()
) -> tuple[Recording, Transcript, Verdict]:
    """Load the fixture of hunt ``name`` from ``directory``, replay it against
    the current code, and judge the replayed experiments."""
    hunt = HUNTS[name]
    recording = load_recording(directory / hunt.fixture)
    allowlist = tools()
    transcript = replay(
        recording,
        allowlist,
        system=SYSTEM,
        task=hunt.task,
        tolerance=TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=RECORD_COMMAND.format(name=name),
    )
    return recording, transcript, judge(hunt.claim, transcript, allowlist)


def _show(step: Step, *secrets: Secret) -> None:
    """Print a step; the loop removed the key already, this redacts once more."""
    if step.message.text:
        print(redact(step.message.text, *secrets))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(
            redact(
                f"  {call.name}({call.arguments}) -> {dict(result.content)}", *secrets
            )
        )


def main(argv: list[str] | None = None) -> int:
    """The live entry point: ask the model, print the run and the verdict,
    optionally record. The key is the client's business, not this module's."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--claim", choices=sorted(HUNTS), required=True)
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write the run to {LESSON}/<fixture> as the replay fixture",
    )
    options = parser.parse_args(argv)
    hunt = HUNTS[options.claim]
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Task: {hunt.task}\nModel: {client.model}\n")
    allowlist = tools()
    transcript = run(
        client,
        allowlist,
        SYSTEM,
        hunt.task,
        MAX_STEPS,
        on_step=lambda step: _show(step, *client.secrets),
    )
    verdict = judge(hunt.claim, transcript, allowlist)
    print(f"\nVerdict (recomputed, not the model's words): {verdict.outcome}")
    if verdict.witness is not None:
        print(f"  {dict(verdict.witness.arguments)} gives {verdict.witness.value:.4g}")
    if options.record:
        today = datetime.date.today().isoformat()
        path = Path(LESSON) / hunt.fixture
        save_recording(path, transcript, today, *client.secrets)
        print(f"\nRecorded to {path}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
