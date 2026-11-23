"""The search of the lesson "A proof an agent proposed": an agent hunts for a
counterexample to a conjecture about the kinetic energy of a collision, before
anyone tries to prove it (Issue #609, on the hunter of ``pbc.agents.hunter``).

The agent may call two functions through the allowlist below. Both collide two
spheres in a plane with the rule of the momentum lesson
(``pbc.mechanics.particles.hard_sphere_collision``) and return the relative
change of the total kinetic energy. The first takes the direction of the line
of centres as two components, of any length; the second as an angle, so that
it always has unit length. The harness, not the agent, decides what was found.

This is a harness agent of ADR 004: it calls functions and writes text; it
writes no code and no proof. The proof of the lesson is a Lean module of the
repository, and the coding agent of the lesson works on the learner's machine
(ADR 010); nothing here invokes one.

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.proof_lab --claim any

Record the replay fixture of a claim from a live run (maintainer)::

    uv run --extra openai python -m pbc.agents.proof_lab --claim any --record
"""

import argparse
import datetime
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.hunter import FalsifiableClaim, Verdict, judge
from pbc.agents.hunter_lab import SYSTEM
from pbc.agents.loop import Step, Transcript, run
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.mechanics.particles import hard_sphere_collision

BUDGET = 6  # experiments per claim
MAX_STEPS = 8  # model messages per run
# A recomputed tool result may differ from the recorded one by this much
# (relative and absolute). The result is a relative change of energy: of
# order one for a direction of the wrong length, and at round-off, about
# 1e-16, for a unit one, where the absolute part decides.
TOLERANCE = 1e-9
# The limit of both claims, written before the hunts: a relative change of
# the kinetic energy above it is not round-off of a computation in doubles,
# whose own relative error is about 1e-16 per operation.
LIMIT = 1e-9
# A relative change below this is round-off of the arithmetic in doubles,
# which differs between machines in its last digits: the tools report it as
# zero, so that no page shows it as a number.
ROUND_OFF = 1e-12

ANY_TOOL = "energy_change_any_direction"
UNIT_TOOL = "energy_change_unit_direction"
RESULT = "relative_energy_change"

MASSES = (0.1, 10.0)  # kg
SPEEDS = (-5.0, 5.0)  # m/s, each component
COMPONENTS = (-1.0, 1.0)  # each component of the direction
ANGLES = (0.0, 360.0)  # degrees

_COMMON = {
    "m1": MASSES,
    "m2": MASSES,
    "v1x": SPEEDS,
    "v1y": SPEEDS,
    "v2x": SPEEDS,
    "v2y": SPEEDS,
}

ANY_DIRECTION = FalsifiableClaim(
    statement=(
        "The collision rule of two hard spheres conserves the total kinetic"
        " energy, to a relative change of at most 1e-9, for all masses from 0.1"
        " to 10 kg, all planar velocities with components from -5 to 5 m/s, and"
        " every direction n of the line of centres with components from -1 to 1"
    ),
    tool=ANY_TOOL,
    fixed={},
    ranges={**_COMMON, "nx": COMPONENTS, "ny": COMPONENTS},
    result=RESULT,
    limit=LIMIT,
    budget=BUDGET,
)
UNIT_DIRECTION = FalsifiableClaim(
    statement=(
        "The collision rule of two hard spheres conserves the total kinetic"
        " energy, to a relative change of at most 1e-9, for all masses from 0.1"
        " to 10 kg, all planar velocities with components from -5 to 5 m/s, and"
        " every direction n of unit length"
    ),
    tool=UNIT_TOOL,
    fixed={},
    ranges={**_COMMON, "angle": ANGLES},
    result=RESULT,
    limit=LIMIT,
    budget=BUDGET,
)


@dataclass(frozen=True)
class Hunt:
    """One claim put to the agent: the claim, the task text, the fixture."""

    claim: FalsifiableClaim
    task: str
    fixture: str  # the file next to the page


def _task(claim: FalsifiableClaim, tool: str) -> str:
    return (
        f"Claim: {claim.statement}. The relative change is the absolute"
        " difference of the total kinetic energy after and before the"
        " collision, divided by the energy before. Try to refute the claim with"
        f" at most {claim.budget} experiments of the tool {tool}, all inside"
        " the domain of the claim."
    )


HUNTS = {
    "any": Hunt(ANY_DIRECTION, _task(ANY_DIRECTION, ANY_TOOL), "replay-any.json"),
    "unit": Hunt(UNIT_DIRECTION, _task(UNIT_DIRECTION, UNIT_TOOL), "replay-unit.json"),
}

LESSON = "site/lessons/lean/06-a-proof-an-agent-proposed"
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.proof_lab --claim {name}"
    " --record (with OPENAI_API_KEY set)"
)


def energy_change(
    m1: float,
    m2: float,
    v1: np.ndarray,
    v2: np.ndarray,
    n: np.ndarray,
) -> float:
    """The relative change of the total kinetic energy of two spheres, masses
    ``m1`` and ``m2`` (kg) and velocities ``v1`` and ``v2`` (m/s), in one
    collision of the rule of the momentum lesson along ``n``, a direction of
    any length. A change below ``ROUND_OFF`` is returned as zero. Raises
    ``ValueError`` when the energy before is zero, for which a relative change
    has no meaning."""
    before = 0.5 * m1 * (v1 @ v1) + 0.5 * m2 * (v2 @ v2)
    if before == 0.0:
        raise ValueError("the kinetic energy before the collision is zero")
    w1, w2 = hard_sphere_collision(m1, v1, m2, v2, n)
    after = 0.5 * m1 * (w1 @ w1) + 0.5 * m2 * (w2 @ w2)
    change = float(abs(after - before) / before)
    return change if change >= ROUND_OFF else 0.0


def _any_direction(m1, m2, v1x, v1y, v2x, v2y, nx, ny) -> dict[str, float]:
    v1, v2 = np.array([v1x, v1y]), np.array([v2x, v2y])
    return {RESULT: energy_change(m1, m2, v1, v2, np.array([nx, ny]))}


def _unit_direction(m1, m2, v1x, v1y, v2x, v2y, angle) -> dict[str, float]:
    v1, v2 = np.array([v1x, v1y]), np.array([v2x, v2y])
    theta = math.radians(angle)
    n = np.array([math.cos(theta), math.sin(theta)])
    return {RESULT: energy_change(m1, m2, v1, v2, n)}


def _common() -> tuple[Parameter, ...]:
    return (
        Parameter("m1", "mass of the first sphere in kg", *MASSES),
        Parameter("m2", "mass of the second sphere in kg", *MASSES),
        Parameter("v1x", "velocity of the first sphere along x in m/s", *SPEEDS),
        Parameter("v1y", "velocity of the first sphere along y in m/s", *SPEEDS),
        Parameter("v2x", "velocity of the second sphere along x in m/s", *SPEEDS),
        Parameter("v2y", "velocity of the second sphere along y in m/s", *SPEEDS),
    )


_DESCRIPTION = (
    "Collide two spheres in a plane with the hard-sphere rule of the course,"
    " v1' = v1 - 2 m2 / (m1 + m2) ((v1 - v2) . n) n and"
    " v2' = v2 + 2 m1 / (m1 + m2) ((v1 - v2) . n) n, and return the absolute"
    " change of the total kinetic energy divided by the energy before. A"
    f" change below {ROUND_OFF:g}, round-off of the arithmetic, is returned as 0."
)


def tools() -> Allowlist:
    """The allowlist of the lesson: two functions, bounded, with a budget of
    experiments. A new allowlist has a fresh budget."""
    return Allowlist(
        (
            Tool(
                name=ANY_TOOL,
                description=_DESCRIPTION
                + " The direction n is given by its two components, as they"
                " are, without normalisation.",
                parameters=(
                    *_common(),
                    Parameter(
                        "nx", "component of the direction n along x", *COMPONENTS
                    ),
                    Parameter(
                        "ny", "component of the direction n along y", *COMPONENTS
                    ),
                ),
                function=_any_direction,
            ),
            Tool(
                name=UNIT_TOOL,
                description=_DESCRIPTION
                + " The direction n is the unit vector at the given angle from"
                " the x axis.",
                parameters=(
                    *_common(),
                    Parameter("angle", "angle of the direction n in degrees", *ANGLES),
                ),
                function=_unit_direction,
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
