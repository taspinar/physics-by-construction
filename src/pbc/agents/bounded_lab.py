"""Lesson SA5, second part: a bounded experiment agent (F143).

The question of the first part, the best launch angle of the tennis ball
with drag (``pbc.agents.projectile_lab``), asked again under a written
protocol: choose a converged time step, search for the best angle to within
one degree, recover from a run that fails, spend at most ``BUDGET`` runs,
and stop on the protocol's own rule. One tool, ``range_with_drag``, with
the bounds of the first part. Its ``FAIL_AT``-th accepted run fails: the
failure is injected in the tool, not announced in the prompt, and a failed
run costs one unit of the budget like any other.

Whether a run followed the protocol is computed from its tool calls and
their recomputed results (``check_protocol``), never from the agent's
words. ``scripted_route`` executes the same protocol as a program through
the same allowlist, with the same failure, and needs no model.

Run it live on your machine (needs ``OPENAI_API_KEY`` and the optional
dependency)::

    uv run --extra openai python -m pbc.agents.bounded_lab
"""

import argparse
import datetime
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import ToolCall, ToolResult
from pbc.agents.projectile_lab import ANGLE, DRAG, MASS, SPEED, TIME_STEP, TOLERANCE
from pbc.agents.replay import Recording, load_recording, replay, save_recording
from pbc.agents.secrets import Secret, redact
from pbc.agents.tools import Allowlist, Tool
from pbc.mechanics.projectile import projectile_range

BUDGET = 10  # simulation runs per run of the agent, failed ones included
MAX_STEPS = 8  # model messages per run
FAIL_AT = 3  # the third accepted run fails
# A time step dt is used when the ranges at dt and dt / 2 differ by less
# than this fraction of the range.
CONVERGED = 0.001
FAILURE = "the simulation worker stopped before it returned a result"

# The protocol the agent is given, step by step, and the script follows.
PROTOCOL = (
    ("plan", "Before the first run, state your plan in one or two sentences."),
    (
        "time step",
        "Choose the time step: run the same throw at a step dt and at dt / 2,"
        " and use dt only if the two ranges differ by less than 0.1 per cent;"
        " otherwise halve dt and compare again.",
    ),
    (
        "search",
        "At that step, find an angle, in whole degrees, whose range is larger"
        " than the ranges one degree below and one degree above it.",
    ),
    (
        "recovery",
        "A run that fails gives no result. You may repeat it once. Never use a"
        " value you did not receive.",
    ),
    (
        "stop",
        f"You have {BUDGET} simulation runs, failed ones included. Stop as soon"
        " as the search is met, or when the budget is spent, and say which.",
    ),
)

SYSTEM = (
    "You are a careful experimenter. You can only use the tool you are given."
    " Follow the protocol of the task step by step. Report your conclusion in"
    " plain text and give the evidence for it."
)
TASK = (
    "A tennis ball is thrown at 25 m/s from the ground, with air drag. Find the"
    " launch angle, to within one degree, at which it lands furthest away."
    " Follow this protocol:\n"
    + "\n".join(f"{n}. {text}" for n, (_, text) in enumerate(PROTOCOL, start=1))
)

FIXTURE = "site/lessons/agents-llm/01-an-agent-runs-an-experiment/replay-bounded.json"
REPLAY_FILE = "replay-bounded.json"  # the fixture, next to the page
RECORD_COMMAND = (
    "uv run --extra openai python -m pbc.agents.bounded_lab --record"
    " (with OPENAI_API_KEY set)"
)


def failing(function: Callable[..., Mapping[str, float]], fail_at: int):
    """``function``, except that its ``fail_at``-th call raises instead of
    returning: the injected failure. The allowlist calls it only for a run
    that passed validation and the budget, so the count is of accepted
    runs."""
    calls = 0

    def wrapped(**arguments: float) -> Mapping[str, float]:
        nonlocal calls
        calls += 1
        if calls == fail_at:
            raise RuntimeError(FAILURE)
        return function(**arguments)

    return wrapped


def _range_with_drag(speed: float, angle: float, dt: float) -> dict[str, float]:
    return {"range_m": projectile_range(speed, angle, MASS, DRAG, dt)}


def tools(budget: int = BUDGET, fail_at: int = FAIL_AT) -> Allowlist:
    """The allowlist of the second part: one tool, the bounds of the first
    part, a budget of runs, and one injected failure."""
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
                function=failing(_range_with_drag, fail_at),
            ),
        ),
        budget=budget,
    )


@dataclass(frozen=True)
class Run:
    """One tool call and its result, in the order they happened."""

    call: ToolCall
    result: ToolResult
    message: int  # the model message (or the script's step) that asked


def runs_of(transcript: Transcript) -> tuple[Run, ...]:
    """The tool calls of ``transcript`` with their results, in order."""
    return tuple(
        Run(call, result, number)
        for number, step in enumerate(transcript.steps)
        for call, result in zip(step.message.tool_calls, step.results, strict=True)
    )


def _failed(run: Run) -> bool:
    return not run.result.ok and run.result.content.get("error") == FAILURE


def _over_budget(run: Run) -> bool:
    return not run.result.ok and "budget" in str(run.result.content.get("error"))


def _setting(call: ToolCall) -> tuple[float, float, float] | None:
    arguments = call.arguments
    if not isinstance(arguments, dict):
        return None
    try:
        return (
            float(arguments["speed"]),
            float(arguments["angle"]),
            float(arguments["dt"]),
        )
    except KeyError, TypeError, ValueError:
        return None


@dataclass(frozen=True)
class Check:
    """One step of the protocol, checked from the runs."""

    step: str
    met: bool
    evidence: str


@dataclass(frozen=True)
class Outcome:
    """What the runs establish under the protocol: the time step it chose,
    the best angle it found, and the runs used."""

    dt: float | None
    angle: float | None
    runs: int


def check_protocol(
    runs: Sequence[Run], stopped_by_itself: bool
) -> tuple[tuple[Check, ...], Outcome]:
    """Check the steps of the protocol after the plan from ``runs`` alone:
    the settings asked for and the results received, never the words."""
    received = {}  # setting -> range, for the runs that returned one
    for entry in runs:
        setting = _setting(entry.call)
        if entry.result.ok and setting is not None:
            received[setting] = float(entry.result.content["range_m"])

    converged = sorted(
        dt
        for (speed, angle, dt), coarse in received.items()
        if (fine := received.get((speed, angle, dt / 2))) is not None
        and abs(coarse - fine) < CONVERGED * fine
    )
    dt = converged[-1] if converged else None
    peaks = sorted(
        angle
        for (speed, angle, step), value in received.items()
        if step == dt
        and value > received.get((speed, angle - 1, step), float("inf"))
        and value > received.get((speed, angle + 1, step), float("inf"))
    )
    angle = peaks[0] if peaks else None

    failed = [entry for entry in runs if _failed(entry)]
    settings = [_setting(entry.call) for entry in runs]
    repeats = [settings.count(_setting(entry.call)) - 1 for entry in failed]
    spent = sum(entry.result.ok or _failed(entry) for entry in runs)
    over = sum(_over_budget(entry) for entry in runs)
    met_at = next(
        (
            entry.message
            for n, entry in enumerate(runs)
            if angle is not None and _found(runs[: n + 1], dt, angle)
        ),
        None,
    )
    after = sum(entry.message > met_at for entry in runs) if met_at is not None else 0

    checks = (
        Check(
            "time step",
            dt is not None,
            f"dt = {dt:g} s agrees with dt / 2 within {CONVERGED:.1%}"
            if dt is not None
            else "no step was compared with its half",
        ),
        Check(
            "search",
            angle is not None,
            f"{angle:g} degrees beats both neighbours at dt = {dt:g} s"
            if angle is not None
            else "no angle beats both of its neighbours at the chosen step",
        ),
        Check(
            "recovery",
            bool(failed) and all(n <= 1 for n in repeats),
            "; ".join(
                f"the run at {_setting(entry.call)[1]:g} degrees, dt ="
                f" {_setting(entry.call)[2]:g} s failed and was repeated"
                f" {n} time(s)"
                for entry, n in zip(failed, repeats, strict=True)
            )
            if failed
            else "no run failed",
        ),
        Check(
            "budget",
            spent <= BUDGET and over == 0,
            f"{spent} of {BUDGET} runs spent, {over} refused for the budget",
        ),
        Check(
            "stop",
            stopped_by_itself and met_at is not None and after == 0,
            "stopped by itself, no run after the search was met"
            if stopped_by_itself and met_at is not None and after == 0
            else f"stopped by itself: {stopped_by_itself}; runs after the"
            f" search was met: {after}",
        ),
    )
    return checks, Outcome(dt, angle, spent)


def _found(runs: Sequence[Run], dt: float | None, angle: float) -> bool:
    got = {
        _setting(r.call)[1]: r.result.content["range_m"]
        for r in runs
        if r.result.ok and _setting(r.call) is not None and _setting(r.call)[2] == dt
    }
    return {angle - 1, angle, angle + 1} <= set(got) and got[angle] > max(
        got[angle - 1], got[angle + 1]
    )


class BudgetSpent(RuntimeError):
    """The allowlist refused a run: the budget is spent."""


def scripted_route(
    allowlist: Allowlist, speed: float = 25.0, angle: float = 40.0, dt: float = 0.01
) -> tuple[tuple[Run, ...], str]:
    """The protocol as a program, through ``allowlist``: compare dt with
    dt / 2 at ``angle`` and halve until they agree, then climb one degree at
    a time to an angle that beats both neighbours. A failed run is repeated
    once. Returns the runs and how the route stopped."""
    runs: list[Run] = []

    def simulate(at_angle: float, step: float) -> float | None:
        for _ in range(2):  # a failed run is repeated once
            arguments = {"speed": speed, "angle": at_angle, "dt": step}
            call = ToolCall(f"script-{len(runs) + 1}", "range_with_drag", arguments)
            result = allowlist.dispatch(call)
            runs.append(Run(call, result, len(runs)))
            if result.ok:
                return float(result.content["range_m"])
            if _over_budget(runs[-1]):
                raise BudgetSpent(result.content["error"])
        return None

    try:
        while True:
            coarse, fine = simulate(angle, dt), simulate(angle, dt / 2)
            if coarse is None or fine is None:
                return tuple(runs), "a run failed twice: no result"
            if abs(coarse - fine) < CONVERGED * fine:
                break
            dt /= 2
        ranges = {angle: coarse}
        while True:
            for neighbour in (angle - 1, angle + 1):
                if neighbour not in ranges:
                    ranges[neighbour] = simulate(neighbour, dt)
                    if ranges[neighbour] is None:
                        return tuple(runs), "a run failed twice: no result"
            best = max((angle - 1, angle, angle + 1), key=ranges.__getitem__)
            if best == angle:
                return tuple(runs), f"search met: {angle:g} degrees at dt = {dt:g} s"
            angle = best
    except BudgetSpent:
        return tuple(runs), "budget spent before the search was met: no answer"


def replay_recording(recording: Recording) -> Transcript:
    """Replay ``recording`` against the current code of the lesson, with a
    fresh allowlist: the same budget and the same injected failure."""
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
    """Load ``replay-bounded.json`` from ``directory`` and replay it."""
    recording = load_recording(directory / REPLAY_FILE)
    return recording, replay_recording(recording)


def _show(step: Step, *secrets: Secret) -> None:
    if step.message.text:
        print(redact(step.message.text, *secrets))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        line = f"  {call.name}({call.arguments}) -> {dict(result.content)}"
        print(redact(line, *secrets))


def main(argv: list[str] | None = None) -> int:
    """The live entry point: ask the model, print the run and its protocol
    check, optionally record."""
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
    checks, _ = check_protocol(runs_of(transcript), transcript.finished)
    for check in checks:
        print(f"{check.step}: {'met' if check.met else 'not met'} ({check.evidence})")
    if options.record:
        today = datetime.date.today().isoformat()
        save_recording(Path(FIXTURE), transcript, today, *client.secrets)
        print(f"\nRecorded to {FIXTURE}. Review it before you commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
