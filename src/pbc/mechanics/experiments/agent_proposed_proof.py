"""The experiment of the lesson "A proof an agent proposed".

The numbers around the Lean theorem that the hard-sphere collision rule
conserves the kinetic energy when the direction has unit length
(``lean/PhysicsByConstruction/Mechanics/CollisionEnergy.lean``): the replay of
two authored hunts for a counterexample (``pbc.agents.proof_lab``) and their
verdicts, the hunt's experiments beside the change of energy that the Lean
identity ``collision_energy_change`` gives, sampled collisions against the same
identity, and a collision without approach. The theorems themselves are checked
by the Lean build, ``./scripts/check-lean.sh``; the coding agent of the lesson
runs on the learner's machine and nowhere here. Run it as a program to write the
figure and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.agent_proposed_proof out

The live hunt, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.proof_lab
--claim any`` (or ``--claim unit``).
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents.display import AllowlistDisplay, RunDisplay, VerdictDisplay
from pbc.agents.loop import Transcript
from pbc.agents.proof_lab import (
    ANY_DIRECTION,
    ANY_TOOL,
    BUDGET,
    LIMIT,
    MAX_STEPS,
    ROUND_OFF,
    UNIT_DIRECTION,
    UNIT_TOOL,
    replay_hunt,
    tools,
)
from pbc.authoring import FIGURE_COLOURS
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main
from pbc.figure_language import LINE, MUTED, figsize, figure_style, finish
from pbc.mechanics.particles import hard_sphere_collision

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.proof_lab"

# The authored hunts, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/lean/06-a-proof-an-agent-proposed"
# Every sampled collision lies within this distance of the identity's curve,
# written before the sample was drawn; the build refuses a run that does not.
DEVIATION_BOUND = 1e-10


def kinetic_energy(m1, m2, v1, v2) -> float:
    """The total kinetic energy (J) of two spheres, masses in kg and
    velocities in m/s."""
    return 0.5 * m1 * (v1 @ v1) + 0.5 * m2 * (v2 @ v2)


def rule_change(m1, m2, v1, v2, n) -> float:
    """The relative change of the total kinetic energy in one collision of the
    rule, computed by the program: positive when energy is gained."""
    w1, w2 = hard_sphere_collision(m1, v1, m2, v2, n)
    before = kinetic_energy(m1, m2, v1, v2)
    return (kinetic_energy(m1, m2, w1, w2) - before) / before


def identity_change(m1, m2, v1, v2, n) -> float:
    """The same relative change from the right-hand side of the Lean identity
    ``collision_energy_change``: 2 m1 m2 / (m1 + m2) s² (n · n - 1), with s
    the component of the relative velocity along n, over the energy before."""
    s = (v1 - v2) @ n
    change = 2.0 * m1 * m2 / (m1 + m2) * s**2 * (n @ n - 1.0)
    return change / kinetic_energy(m1, m2, v1, v2)


def hunt_experiments(transcript: Transcript):
    """The accepted experiments of a replayed hunt with a direction given by
    its components, as (m1, m2, v1, v2, n)."""
    found = []
    for step in transcript.steps:
        for call, result in zip(step.message.tool_calls, step.results, strict=True):
            if result.ok and call.name == ANY_TOOL:
                a = call.arguments
                found.append(
                    (
                        a["m1"],
                        a["m2"],
                        np.array([a["v1x"], a["v1y"]]),
                        np.array([a["v2x"], a["v2y"]]),
                        np.array([a["nx"], a["ny"]]),
                    )
                )
    return found


def instance_rows(transcript: Transcript):
    """One row per experiment of the first hunt: the direction, its length,
    the change the program computed, and the change of the identity."""

    def shown(change: float) -> float:
        return change if abs(change) > ROUND_OFF else 0.0

    return [
        (
            n[0],
            n[1],
            float(np.linalg.norm(n)),
            shown(rule_change(m1, m2, v1, v2, n)),
            shown(identity_change(m1, m2, v1, v2, n)),
        )
        for m1, m2, v1, v2, n in hunt_experiments(transcript)
    ]


def sampled_collisions(count: int = 400, seed: int = 11):
    """Random planar collisions with directions of length 0.2 to 1.6: the
    length of each direction and the change of energy the program computed,
    divided by 2 m1 m2 / (m1 + m2) s². Collisions whose approach s is below
    0.2 m/s are not drawn, so that the division is not by a small number."""
    rng = np.random.default_rng(seed)
    lengths, normalised = [], []
    while len(lengths) < count:
        m1, m2 = rng.uniform(0.1, 10.0, size=2)
        v1, v2 = rng.uniform(-5.0, 5.0, size=(2, 2))
        angle = rng.uniform(0.0, 2.0 * np.pi)
        length = rng.uniform(0.2, 1.6)
        n = length * np.array([np.cos(angle), np.sin(angle)])
        s = (v1 - v2) @ n
        if abs(s) < 0.2:
            continue
        w1, w2 = hard_sphere_collision(m1, v1, m2, v2, n)
        change = kinetic_energy(m1, m2, w1, w2) - kinetic_energy(m1, m2, v1, v2)
        lengths.append(length)
        normalised.append(change / (2.0 * m1 * m2 / (m1 + m2) * s**2))
    return np.array(lengths), np.array(normalised)


def largest_deviation() -> float:
    """The largest distance of a sampled collision from the identity's curve."""
    lengths, normalised = sampled_collisions()
    return float(np.max(np.abs(normalised - (lengths**2 - 1.0))))


def draw_energy_change(transcript: Transcript) -> Figure:
    """The normalised change of the kinetic energy against the length of the
    direction: sampled collisions of the program, the curve of the Lean
    identity, and the experiments of the first hunt."""
    lengths, normalised = sampled_collisions()
    grid = np.linspace(0.2, 1.6, 200)
    with figure_style():
        fig, ax = plt.subplots(figsize=figsize("line"))
        ax.plot(
            lengths,
            normalised,
            "o",
            color=FIGURE_COLOURS[0],
            markersize=2.5,
            alpha=0.6,
            label="sampled collisions (program)",
        )
        ax.plot(
            grid,
            grid**2 - 1.0,
            "--",
            color=FIGURE_COLOURS[1],
            linewidth=LINE["model"],
            label="|n|² - 1 (Lean identity)",
        )
        for index, (m1, m2, v1, v2, n) in enumerate(hunt_experiments(transcript)):
            s = (v1 - v2) @ n
            w1, w2 = hard_sphere_collision(m1, v1, m2, v2, n)
            change = kinetic_energy(m1, m2, w1, w2) - kinetic_energy(m1, m2, v1, v2)
            ax.plot(
                np.linalg.norm(n),
                change / (2.0 * m1 * m2 / (m1 + m2) * s**2),
                "kD",
                markersize=6,
                label="experiments of the first hunt" if index == 0 else None,
            )
        ax.axvline(1.0, color=MUTED, linestyle=":", linewidth=LINE["guide"])
        ax.axhline(0.0, color=MUTED, linestyle=":", linewidth=LINE["guide"])
        ax.set_xlabel("length of the direction |n| (dimensionless)")
        ax.set_ylabel("change of kinetic energy\nover 2 m₁m₂/(m₁+m₂) s²")
        ax.legend(loc="lower right")
    return finish(fig)


# region: no_approach
m1, m2 = 1.0, 2.0  # kg
v1 = np.array([3.0, 0.0])  # m/s
v2 = np.array([-1.0, 0.0])
n = np.array([0.0, 2.0])  # across the relative velocity, length 2
# endregion: no_approach


def without_approach():
    """The collision of ``energy_without_approach``: the spheres do not
    approach along n, which has length 2."""
    print(f"approach along n: {(v1 - v2) @ n:.1f} m/s")
    change = rule_change(m1, m2, v1, v2, n)
    print(f"relative change of the kinetic energy: {change:.1f}")
    w1, w2 = hard_sphere_collision(m1, v1, m2, v2, n)
    print(f"velocities unchanged: {bool(np.allclose(w1, v1) and np.allclose(w2, v2))}")


def opposite_direction():
    """Exercise: the velocities after the collision of the region above with a
    unit direction n along x and with -n."""
    rows = []
    for direction in (np.array([1.0, 0.0]), np.array([-1.0, 0.0])):
        w1, w2 = hard_sphere_collision(m1, v1, m2, v2, direction)
        rows.append((direction[0], w1[0], w1[1], w2[0], w2[1]))
    return rows


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.display("allowlist", AllowlistDisplay(tools()))
    experiment.number("any-claim", ANY_DIRECTION.statement)
    experiment.number("unit-claim", UNIT_DIRECTION.statement)
    experiment.number("any-tool", ANY_TOOL)
    experiment.number("unit-tool", UNIT_TOOL)
    experiment.number("budget", BUDGET)
    experiment.number("max-steps", MAX_STEPS)
    experiment.number("limit", LIMIT, ".0e")
    experiment.number("round-off", ROUND_OFF, ".0e")

    # region: replay
    any_recording, any_transcript, any_verdict = replay_hunt("any", LESSON)
    unit_recording, unit_transcript, unit_verdict = replay_hunt("unit", LESSON)
    # endregion: replay
    experiment.display(
        "any-run", RunDisplay(any_recording, any_transcript, authored=True)
    )
    experiment.display("any-verdict", VerdictDisplay(any_verdict))
    experiment.display(
        "unit-run", RunDisplay(unit_recording, unit_transcript, authored=True)
    )
    experiment.display("unit-verdict", VerdictDisplay(unit_verdict))

    experiment.table(
        "hunt-instances",
        instance_rows(any_transcript),
        [
            ("n_x", "", "g"),
            ("n_y", "", "g"),
            ("|n|", "", ".3f"),
            ("change computed by the program", "", ".4f"),
            ("change given by the identity", "", ".4f"),
        ],
        "The relative change of the total kinetic energy in the experiments of"
        " the first hunt, as the program computes it and as the right-hand side"
        " of collision_energy_change gives it; positive is a gain.",
    )
    deviation = largest_deviation()
    if not deviation < DEVIATION_BOUND:
        raise ValueError(f"a sampled collision is {deviation:g} off the identity")
    experiment.number("deviation-bound", DEVIATION_BOUND, ".0e")
    experiment.number("samples", len(sampled_collisions()[0]))
    experiment.figure("fig-energy-change", partial(draw_energy_change, any_transcript))
    with experiment.capture("without-approach"):
        without_approach()
    experiment.table(
        "opposite-direction",
        opposite_direction(),
        [
            ("n_x", "", "g"),
            ("v1'_x", "m/s", ".4f"),
            ("v1'_y", "m/s", ".4f"),
            ("v2'_x", "m/s", ".4f"),
            ("v2'_y", "m/s", ".4f"),
        ],
        "The velocities after the collision of the example with n along x and with -n.",
    )
    return experiment


if __name__ == "__main__":
    main(run)
