"""The experiment of the lesson "Three reviewers".

Three reviewers, each with its own allowlist of checks
(``pbc.agents.review_lab``), review two pieces of code that claim to be
symplectic Euler; their recorded runs are replayed and their verdicts are
taken from the recomputed checks. Run it as a program to write the figure
and numbers of the page:

    uv run --locked --no-dev \\
        python -m pbc.mechanics.experiments.scientific_review out

The live run, which asks a model and needs its key, is a separate command
behind the optional dependency ``openai``: the module ``LIVE``, run with
``uv run --locked --no-dev --extra openai python -m pbc.agents.review_lab``.
"""

from functools import partial

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pbc.agents import ModelMessage, ReplayMismatch, ToolCall
from pbc.agents import investigation as inv
from pbc.agents import run as run_agent
from pbc.agents.display import RunDisplay
from pbc.agents.review_lab import (
    CANDIDATES,
    CLAIM,
    MAX_STEPS,
    PANEL_DIRECTORY,
    REVIEWERS,
    TOLERANCE,
    ReviewDisplay,
    Verdict,
    replay_fixtures,
    replay_reviewer,
    resolve,
    verdicts,
)
from pbc.authoring import diagrams
from pbc.authoring.repository import REPOSITORY_ROOT
from pbc.experiment import Experiment, main
from pbc.verification import checks, oscillator_error, verify

# The live run of the lesson: a model, its key, and the extra openai.
LIVE = "pbc.agents.review_lab"

# The recorded reviews, next to the page that shows them.
LESSON = REPOSITORY_ROOT / "site/lessons/agents-llm/03-three-reviewers"
# The recorded panel sessions of lesson AE6, replayed where they are.
PANEL = REPOSITORY_ROOT / PANEL_DIRECTORY


class Boaster:
    model = "a reviewer that does not tell the truth"
    secrets = ()

    def __init__(self):
        self.messages = [
            ModelMessage(
                "I will check the energy.",
                (ToolCall("1", "check_bounded_energy", {"candidate": 2}),),
            ),
            ModelMessage("Piece 2 passes every check, with a wide margin."),
        ]

    def complete(self, system, conversation, tools):
        return self.messages.pop(0)


def boasting_reviewer():
    """Exercise 1: a reviewer that runs one check and then claims the
    opposite of its result."""
    physics = REVIEWERS[0]
    transcript = run_agent(
        Boaster(), physics.allowlist, physics.system, physics.task, MAX_STEPS
    )
    print("what it said: ", transcript.steps[-1].message.text)
    for v in verdicts(physics, transcript):
        print(
            f"what it ran:   {v.check} on piece {v.candidate}:",
            "passed" if v.passed else "FAILED",
            f"(measured {v.measured:.1e}, tolerance {v.tolerance})",
        )


def stricter_check(replays):
    """Exercise 2: the replay of the physics reviewer against a check whose
    tolerance has changed."""
    physics = REVIEWERS[0]
    original = checks.EXACT
    checks.EXACT = 1e-30
    try:
        replay_reviewer(physics, replays["physics"][0])
    except ReplayMismatch as mismatch:
        print(mismatch)
    finally:
        checks.EXACT = original


def draw_review_evidence(replays) -> Figure:
    """The error of the two pieces against the steps per period, with the
    experiments the evidence reviewer ran."""
    counts = np.array([20, 40, 80, 160, 320, 640])
    colors = {1: "#00429d", 2: "#93003a"}
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for piece, build in CANDIDATES.items():
        ax.loglog(
            counts,
            [oscillator_error(build, n) for n in counts],
            color=colors[piece],
            label=f"piece {piece}",
        )
        asked = {}
        for step in replays["evidence"][1].steps:
            for call, result in zip(step.message.tool_calls, step.results, strict=True):
                if (
                    result.ok
                    and call.name == "oscillator_error"
                    and call.arguments["candidate"] == piece
                ):
                    asked[call.arguments["steps_per_period"]] = result.content["error"]
        ax.loglog(list(asked), list(asked.values()), "o", color=colors[piece])
    ax.set_xlabel("time steps per period")
    ax.set_ylabel("error")
    ax.legend()
    return fig


def every_check():
    """Exercise 3: every check of the claim on both pieces, without a
    reviewer."""
    for piece, build in CANDIDATES.items():
        for finding in verify(build, CLAIM):
            print(
                f"piece {piece}  {'pass' if finding.passed else 'FAIL'}"
                f"  {finding.check:18} {finding.detail}"
            )


def a_conflict():
    """Exercise 4: two reviewers that disagree on one check."""
    found = [
        Verdict("physics", 1, "limits", 7e-15, 1e-12, True),
        Verdict("evidence", 1, "limits", 3e-3, 1e-12, False),
    ]
    resolution = resolve(found, 1)
    print("rejected:", resolution.rejected, "| conflicts:", resolution.conflicts)


def role_interfaces(experiment: Experiment) -> None:
    """Record the table of what each role may read and write."""
    experiment.table(
        "role-interfaces",
        [
            (item.role, ", ".join(item.reads), ", ".join(item.writes))
            for item in inv.INTERFACES
        ],
        columns=[("role", "", "s"), ("may read", "", "s"), ("may write", "", "s")],
        caption="The interface of each role of the investigation: the fields of"
        " the board it may read and the one it may write.",
    )


def investigate(transcripts) -> inv.Board:
    """The extraction, the implementation, and the replayed review, written
    to one board in that order."""
    board = inv.Board()
    inv.extract(board, inv.EXTRACTION)
    inv.implement(board)
    inv.review(board, transcripts)
    return board


def human_step(board: inv.Board) -> None:
    """The human accepts piece 1, tries to accept piece 2, and sends piece 2
    back with its failed check as the reason."""
    inv.steer(board, inv.Steering(inv.ACCEPT, 1, "every check of its claim passed"))
    try:
        inv.steer(board, inv.Steering(inv.ACCEPT, 2, "the order is right"))
    except inv.OutOfBounds as refusal:
        print(f"refused: {refusal}")
    failed = ", ".join(inv.failed_checks(board, 2))
    inv.steer(board, inv.Steering(inv.SEND_BACK, 2, f"{failed} failed"))
    for piece in CANDIDATES:
        print(f"piece {piece}: {inv.decision(board, piece)}")


def implementer_reads_the_verdicts(board: inv.Board) -> None:
    """An implementer that asks for the reviewers' verdicts."""
    try:
        board.read("implementation", "verdicts")
    except inv.OutOfBounds as refusal:
        print(f"refused: {refusal}")


def vote_against_checks(experiment: Experiment) -> int:
    """The recorded panel sessions' decisions on the three tied cases,
    counted as votes in every panel, beside the recomputed checks; record
    the table and return the number of majorities that accept a faulty
    case."""
    decided, found = inv.panel(PANEL)
    tied = (1, 4, 6)
    rows = []
    wrong = 0
    for sessions in inv.panels():
        cells = []
        for case in tied:
            accept, reject, outcome = inv.votes(decided, case, sessions)
            wrong += outcome == "accept"
            cells.append(f"{accept} to {reject}: {outcome}")
        checks = sorted({inv.checked(found, case, sessions) for case in tied})
        rows.append((", ".join(sessions), *cells, " and ".join(checks)))
    experiment.table(
        "vote-against-checks",
        rows,
        columns=[
            ("panel", "", "s"),
            ("case 1, accept to reject", "", "s"),
            ("case 4, accept to reject", "", "s"),
            ("case 6, accept to reject", "", "s"),
            ("recomputed checks, all three", "", "s"),
        ],
        caption="The decisions of the recorded panel sessions of lesson AE6 on"
        " the three faulty cases where four sessions tie, counted as votes, for"
        " the panel of four and each panel of three, and the decision of the"
        " recomputed checks the same sessions ran.",
    )
    return wrong


def draw_investigation_roles() -> Figure:
    """The roles of the investigation and what each hands on, as a sketch."""
    fig, ax = diagrams.canvas(6.4, 3.6, (-0.6, 13.0), (-1.0, 5.4))
    top, bottom = 4.0, 0.8
    boxes = {
        "extraction": ((3.3, top), "extraction\n(scripted)", 1),
        "implementation": ((7.0, top), "implementation\n(scripted)", 1),
        "review": ((10.9, top), "review\n(3 models)", 0),
        "build": ((10.9, bottom), "build\n(recomputes)", 2),
        "human": ((6.6, bottom), "human", 2),
    }
    for centre, label, colour in boxes.values():
        diagrams.state_box(ax, centre, label, width=2.8, height=1.1, colour=colour)
    diagrams.text(ax, (-0.5, top), "handover", ha="left")
    diagrams.arrow(ax, (1.5, top), (1.9, top), colour=1)
    for left, right, label in (
        ("extraction", "implementation", "claim"),
        ("implementation", "review", "pieces"),
    ):
        (x0, y), (x1, _) = boxes[left][0], boxes[right][0]
        diagrams.arrow(ax, (x0 + 1.4, y), (x1 - 1.4, y), colour=1)
        diagrams.text(ax, ((x0 + x1) / 2, y + 0.8), label)
    diagrams.arrow(ax, (10.9, top - 0.55), (10.9, bottom + 0.55), colour=1)
    diagrams.text(ax, (11.1, 2.4), "tool calls", ha="left")
    diagrams.arrow(ax, (9.5, bottom), (8.0, bottom), colour=1)
    diagrams.text(ax, (8.75, bottom - 0.8), "failed checks")
    diagrams.arrow(ax, (5.2, bottom), (3.4, bottom), colour=2)
    diagrams.text(ax, (3.2, bottom), "decision", ha="right")
    diagrams.text(ax, (4.3, bottom - 0.8), "accept")
    diagrams.arrow(
        ax, (6.6, bottom + 0.55), (7.0, top - 0.55), colour=2, linestyle="--"
    )
    diagrams.text(ax, (7.1, 2.4), "send back", ha="left")
    fig.tight_layout()
    return fig


def narrowed_claim(transcripts) -> None:
    """Exercise 3: the human narrows the claim of piece 2 to first order for
    a run of two periods, then accepts it."""
    board = investigate(transcripts)
    inv.steer(
        board,
        inv.Steering(
            inv.NARROW, 2, "used for runs of two periods", drop="bounded_energy"
        ),
    )
    inv.steer(board, inv.Steering(inv.ACCEPT, 2, "first order holds"))
    print(f"piece 2: {inv.decision(board, 2)}")
    found = board.read("human", "verdicts")
    kept = [v for v in found if v.candidate == 2 and not v.passed]
    print(f"failed checks still in the record: {sorted({v.check for v in kept})}")


def run() -> Experiment:
    """Everything the lesson's page shows."""
    experiment = Experiment()
    experiment.number("claim", f"{CLAIM}")

    # region: replay
    replays = replay_fixtures(LESSON)
    review = ReviewDisplay(
        {name: transcript for name, (_, transcript) in replays.items()}
    )
    growth = next(
        v.measured
        for v in review.verdicts
        if v.candidate == 2 and v.check == "bounded-energy"
    )
    # endregion: replay
    for name in ("physics", "numerics", "evidence"):
        experiment.display(f"{name}-run", RunDisplay(*replays[name]))
    experiment.display("review", review)
    experiment.number("growth", growth, ".1e")
    experiment.number("tolerance", TOLERANCE, "g")

    with experiment.capture("boasting-reviewer"):
        boasting_reviewer()
    with experiment.capture("stricter-check"):
        stricter_check(replays)
    experiment.figure("fig-review-evidence", partial(draw_review_evidence, replays))
    with experiment.capture("every-check"):
        every_check()
    with experiment.capture("a-conflict"):
        a_conflict()

    transcripts = {name: transcript for name, (_, transcript) in replays.items()}
    role_interfaces(experiment)
    experiment.figure("fig-investigation-roles", draw_investigation_roles)
    board = investigate(transcripts)
    with experiment.capture("implementer-reads-the-verdicts"):
        implementer_reads_the_verdicts(board)
    with experiment.capture("human-step"):
        human_step(board)
    experiment.number("wrong-majorities", vote_against_checks(experiment))
    experiment.number("panel-votes", 3 * len(inv.panels()))
    with experiment.capture("narrowed-claim"):
        narrowed_claim(transcripts)
    return experiment


if __name__ == "__main__":
    main(run)
