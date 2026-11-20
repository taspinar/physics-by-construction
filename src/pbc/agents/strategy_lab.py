"""Lesson MD8: four ways of choosing the readings, under one budget, scored
by the evaluator of the evidence contract (F147; ``pbc.evidence``, F137).

The question of the lesson A4 (``pbc.agents.design_lab``) on a medium rig:
a block of 2 kg slows down on a table, linear and quadratic drag compete,
and a launcher starts it at no more than ``MAXIMUM_SPEED``. On this rig a
good design of eight readings separates the models and a poor one may not.
Four strategies choose the readings, each through the same allowlist, with
the same budget and the same number of messages, and each is assessed by the
same judge (``pbc.agents.design.judge``) from the readings recomputed from
the arguments:

- **scripted**: a grid of start speeds and times fixed before any reading;
- **adaptive**: two opening readings, then each reading where the two
  models, fitted to the readings so far, disagree most (the classical
  sequential rule of model discrimination);
- **LLM**: a language model in a fresh session, one recorded session per
  seed (``RECORDINGS``);
- **hybrid**: the model's first ``HYBRID_OPENING`` readings of its session at
  the same seed, then the adaptive rule.

The instrument is the quadratic model of the hidden block plus Gaussian
noise drawn from a generator seeded by the seed of the attempt and the
arguments: the same seed and arguments give the same reading, and a replay
is exact. The seed is the instrument's; no strategy is told it.

Every attempt is recorded in a ``pbc.evidence`` ledger: the evaluator, not
the strategy, counts the readings and the messages, recomputes the outcome,
and decides whether the attempt is correct (discriminated, in favour of the
model the instrument follows). What a model session said about its result is
its own report, stored apart and labelled unverified.

Run the model on one seed live on your machine (needs a model and its key;
the optional dependency ``openai``)::

    uv run --extra openai python -m pbc.agents.strategy_lab --seed 1

With ``--record`` the run overwrites the fixture of its seed, stamped with
the live model and today's date. ``replay_session`` accepts only a fixture
of ``MODEL`` recorded on ``RECORDED``, so after a new recording set both
constants to the new session's (and record every seed again, since all five
must match), or the ledger counts the LLM and hybrid attempts as invalid.
"""

import argparse
import datetime
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from pbc.agents.design import (
    DISCRIMINATED,
    Assessment,
    ExperimentalDesign,
    Model,
    judge,
    measurements,
)
from pbc.agents.design_lab import (
    BUDGET,
    HIDDEN_C,
    LINEAR,
    MASS,
    MAX_STEPS,
    NOISE,
    NOMINAL,
    QUADRATIC,
    REPEATS,
    RESULT,
    SYSTEM,
    THRESHOLD,
    TIMES,
    TOOL,
)
from pbc.agents.loop import Step, Transcript, run
from pbc.agents.messages import ModelMessage, ToolCall, ToolResult, ToolSpec, Turn
from pbc.agents.replay import (
    Recording,
    ReplayMismatch,
    load_recording,
    replay,
    save_recording,
)
from pbc.agents.secrets import redact
from pbc.agents.tools import Allowlist, Parameter, Tool
from pbc.data.fit import fit_curve
from pbc.evidence.pilot import code_identity, environment
from pbc.evidence.records import (
    COMPLETED,
    FAILED,
    INVALID,
    Artifact,
    Attempt,
    CandidateReport,
    Evaluation,
    Ledger,
    RunRecord,
    digest_value,
)

# region: rig
MAXIMUM_SPEED = 4.0  # m/s, the fastest start of the medium rig's launcher
SEEDS = (1, 2, 3, 4, 5)  # the seeds of the instrument every strategy is run on
MORE_SEEDS = tuple(range(1, 41))  # the strategies without a model, again
# endregion: rig
# The readings of the model's session that the hybrid keeps before the
# adaptive rule takes over: half the budget.
HYBRID_OPENING = BUDGET // 2
# region: strategies
SCRIPTED = tuple((v, t) for v in (1.0, 2.0, 3.0, 4.0) for t in (3.0, 8.0))
OPENING = ((MAXIMUM_SPEED, 2.0), (1.0, 2.0))
CANDIDATE_SPEEDS = tuple(0.5 * n for n in range(1, 9))  # m/s
CANDIDATE_TIMES = (0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)  # s
# endregion: strategies

STRATEGIES = ("scripted", "adaptive", "LLM", "hybrid")
TRUE_MODEL = QUADRATIC.name  # the model the simulated instrument follows

STATEMENT = (
    "A block of 2 kg slides on a table and slows down; the launcher of this rig"
    f" cannot start it faster than {MAXIMUM_SPEED:g} m/s."
)
TASK = (
    f"{STATEMENT} Two models of the drag compete: linear drag, v = v0"
    " exp(-g t), and quadratic drag, v = v0 / (1 + k v0 t), with g and k"
    f" unknown. Each reading of the speed has a standard uncertainty of"
    f" {NOISE:g} m/s. Choose at most {BUDGET} measurements, with a start speed"
    f" of at most {MAXIMUM_SPEED:g} m/s, that tell the two models apart."
)
DESIGN = ExperimentalDesign(
    statement=STATEMENT,
    tool=TOOL,
    inputs=("initial_speed", "time"),
    result=RESULT,
    sigma=NOISE,
    models=(LINEAR, QUADRATIC),
    nominal=NOMINAL,
    threshold=THRESHOLD,
    budget=BUDGET,
)

LESSON = "site/lessons/agents-llm/04-an-experimental-design-agent"
# Who produced the recorded sessions, and when; each session saw only the
# system prompt, the task, and the tool, and chose every call itself.
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-11-20"
_NAMES = ("one", "two", "three", "four", "five")
RECORDINGS = {seed: f"replay-{_NAMES[seed - 1]}.json" for seed in SEEDS}
# A recomputed reading may differ from the recorded one by this much: it is a
# deterministic function of the seed and the arguments.
REPLAY_TOLERANCE = 1e-6


def reading(initial_speed: float, time: float, repeat: int, seed: int) -> float:
    """The medium rig's instrument at ``seed``: the speed (m/s) of the hidden
    block, quadratic drag, after ``time`` (s) from ``initial_speed`` (m/s),
    plus noise drawn from a generator seeded by the seed and the arguments."""
    key = [seed, round(initial_speed * 1000), round(time * 1000), repeat]
    noise = np.random.default_rng(key).normal(0.0, NOISE)
    return float(QUADRATIC.function(initial_speed, time, HIDDEN_C / MASS) + noise)


def tools(seed: int) -> Allowlist:
    """The allowlist of the medium rig at ``seed``: the tool of lesson A4,
    bounded by the launcher, with the budget of readings. A new allowlist has
    a fresh budget."""

    def measure(initial_speed: float, time: float, repeat: int) -> dict[str, float]:
        return {RESULT: reading(initial_speed, time, repeat, seed)}

    return Allowlist(
        (
            Tool(
                name=TOOL,
                description=(
                    f"Start a block of {MASS:g} kg on a table at a given speed"
                    " and read its speed after a given time, with an"
                    f" instrument whose noise is {NOISE:g} m/s. The same"
                    " arguments give the same reading; a new value of repeat"
                    " gives an independent reading."
                ),
                parameters=(
                    Parameter(
                        "initial_speed",
                        "speed at the start, in m/s",
                        0.5,
                        MAXIMUM_SPEED,
                    ),
                    Parameter("time", "time after the start, in s", *TIMES),
                    Parameter(
                        "repeat",
                        "number of the repetition, for an independent reading",
                        1,
                        REPEATS,
                        integer=True,
                    ),
                ),
                function=measure,
            ),
        ),
        budget=BUDGET,
    )


# A reading the strategy has seen: the arguments it sent and the speed.
Reading = tuple[Mapping[str, float], float]


def readings_so_far(conversation: Sequence[Turn]) -> list[Reading]:
    """The accepted readings of the tool in ``conversation``, in order."""
    calls: dict[str, ToolCall] = {}
    found: list[Reading] = []
    for turn in conversation:
        if isinstance(turn, ModelMessage):
            calls.update({str(c.id): c for c in turn.tool_calls})
        elif isinstance(turn, ToolResult) and turn.ok and turn.name == TOOL:
            call = calls[turn.call_id]
            found.append((dict(call.arguments), float(turn.content[RESULT])))
    return found


@dataclass
class PolicyClient:
    """A strategy without a model, put through the harness as a client: it
    reads the results of its earlier calls from the conversation, asks for
    one reading per message, and stops when ``choose`` returns nothing."""

    model: str
    choose: Callable[[list[Reading]], Mapping[str, float] | None]
    secrets: tuple = ()

    def complete(
        self, system: str, conversation: Sequence[Turn], tools: Sequence[ToolSpec]
    ) -> ModelMessage:
        seen = readings_so_far(conversation)
        point = self.choose(seen) if len(seen) < BUDGET else None
        if point is None:
            return ModelMessage("The readings are taken.")
        call = ToolCall(f"call-{len(seen) + 1}", TOOL, dict(point))
        return ModelMessage("", (call,))


def _point(speed: float, time: float, seen: list[Reading]) -> dict[str, float]:
    """The arguments of a reading at ``speed`` and ``time``, with the next
    repeat that ``seen`` has not used there."""
    used = sum(1 for a, _ in seen if (a["initial_speed"], a["time"]) == (speed, time))
    return {"initial_speed": speed, "time": time, "repeat": used + 1}


def scripted(seen: list[Reading]) -> dict[str, float] | None:
    """The fixed grid, in order, whatever the readings say."""
    if len(seen) >= len(SCRIPTED):
        return None
    return _point(*SCRIPTED[len(seen)], seen)


def fitted(model: Model, seen: list[Reading]) -> tuple[float, ...]:
    """The parameters of ``model`` fitted to the readings ``seen``."""
    speeds = np.array([a["initial_speed"] for a, _ in seen])
    times = np.array([a["time"] for a, _ in seen])
    values = np.array([v for _, v in seen])

    def curve(index: np.ndarray, *parameters: float) -> np.ndarray:
        return model.function(speeds, times, *parameters)

    fit = fit_curve(
        curve,
        np.arange(len(values), dtype=float),
        values,
        model.start,
        sigma=NOISE,
        bounds=model.bounds,
    )
    return tuple(float(p) for p in fit.params)


def adaptive(seen: list[Reading]) -> dict[str, float]:
    """Two opening readings; then the candidate where the two models, each
    fitted to the readings so far, predict speeds furthest apart, skipping a
    candidate whose repeats are used up."""
    if len(seen) < len(OPENING):
        return _point(*OPENING[len(seen)], seen)
    linear_fit = fitted(LINEAR, seen)
    quadratic_fit = fitted(QUADRATIC, seen)
    candidates = [(v, t) for v in CANDIDATE_SPEEDS for t in CANDIDATE_TIMES]
    speeds = np.array([v for v, _ in candidates])
    times = np.array([t for _, t in candidates])
    apart = np.abs(
        LINEAR.function(speeds, times, *linear_fit)
        - QUADRATIC.function(speeds, times, *quadratic_fit)
    )
    for i in np.argsort(-apart, kind="stable"):
        point = _point(*candidates[i], seen)
        if point["repeat"] <= REPEATS:
            return point
    raise RuntimeError("every candidate is used up")


def hybrid(opening: Sequence[Mapping[str, float]]):
    """The model's opening readings, as its session chose them at the same
    seed, then the adaptive rule."""

    def choose(seen: list[Reading]) -> Mapping[str, float]:
        if len(seen) < len(opening):
            return opening[len(seen)]
        return adaptive(seen)

    return choose


def run_policy(name: str, choose, seed: int) -> tuple[Transcript, Assessment]:
    """A strategy without a model at ``seed``, through the harness, the
    allowlist, and the judge of every strategy."""
    allowlist = tools(seed)
    client = PolicyClient(name, choose)
    transcript = run(client, allowlist, SYSTEM, TASK, MAX_STEPS)
    return transcript, judge(DESIGN, transcript, allowlist)


def record_command(seed: int) -> str:
    return (
        f"uv run --extra openai python -m pbc.agents.strategy_lab --seed {seed}"
        " --record (with OPENAI_API_KEY set)"
    )


def replay_session(
    seed: int, directory: Path
) -> tuple[Recording, Transcript, Assessment]:
    """The recorded session at ``seed``, replayed against the rig at that
    seed, and its assessment. Raises ``ReplayMismatch`` when a recomputed
    result differs from the recorded one, and ``ValueError`` when the fixture
    is not the session ``RECORDINGS`` names."""
    recording = load_recording(directory / RECORDINGS[seed])
    if (recording.model, recording.recorded) != (MODEL, RECORDED):
        raise ValueError(f"{RECORDINGS[seed]} is not the session recorded for it")
    allowlist = tools(seed)
    transcript = replay(
        recording,
        allowlist,
        system=SYSTEM,
        task=TASK,
        tolerance=REPLAY_TOLERANCE,
        max_steps=MAX_STEPS,
        rerecord=record_command(seed),
    )
    return recording, transcript, judge(DESIGN, transcript, allowlist)


def opening_of(transcript: Transcript, seed: int) -> list[dict[str, float]]:
    """The arguments of the first ``HYBRID_OPENING`` readings that count in
    the model's session at ``seed``, recomputed as the judge counts them."""
    found = measurements(DESIGN, transcript, tools(seed))
    return [dict(m.arguments) for m in found[:HYBRID_OPENING]]


# region: correct
def correct(assessment: Assessment) -> bool:
    """The evaluator's verdict: the readings discriminate the models, in
    favour of the model the instrument follows."""
    preferred = assessment.preferred
    return (
        assessment.outcome == DISCRIMINATED
        and preferred is not None
        and preferred.model.name == TRUE_MODEL
    )


# endregion: correct


def metrics(assessment: Assessment) -> dict[str, float]:
    """What the evaluator measures of an attempt, from the recomputed
    readings: the design score, the chi-square of linear drag minus that of
    quadratic drag (positive favours quadratic drag), and the relative
    standard uncertainty of the quadratic constant (``inf`` without a fit)."""
    found = {"design score": assessment.score}
    if assessment.fits is None:
        found["chi-square difference"] = math.nan
        found["relative uncertainty of k"] = math.inf
        return found
    fits = {f.model.name: f for f in assessment.fits}
    found["chi-square difference"] = fits[LINEAR.name].chi2 - fits[QUADRATIC.name].chi2
    k = fits[QUADRATIC.name].fit
    found["relative uncertainty of k"] = float(k.stderr[0] / abs(k.params[0]))
    return found


EVALUATOR = "pbc.agents.strategy_lab evaluation, version 1"


def run_record(seeds: Sequence[int]) -> RunRecord:
    return RunRecord(
        task=TASK,
        hypothesis=(
            "A strategy that chooses each reading from the readings before it"
            " separates the two models of drag more often, under the same"
            " budget, than a grid fixed in advance."
        ),
        assumptions=(
            "The instrument follows quadratic drag with a hidden constant and"
            " Gaussian noise of the stated standard deviation.",
            "Each strategy has the same allowlist, budget of readings, and"
            " number of messages; the seed of the instrument is told to none.",
            "An attempt is correct when the judge's outcome is a discrimination"
            " in favour of quadratic drag.",
            "The attempts of a strategy at different seeds are independent, so"
            " a count of correct attempts is binomial.",
        ),
        protocol_version="f147-medium-rig-1",
        split={
            "probed": "the readings each strategy chose, recomputed from the arguments",
            "held out": "nothing: the verdict is the judge's, on the readings",
        },
        seeds=tuple(seeds),
        budgets={"readings": BUDGET, "messages": MAX_STEPS},
        code=code_identity(),
        configuration=digest_value(
            {
                "maximum speed": MAXIMUM_SPEED,
                "noise": NOISE,
                "threshold": THRESHOLD,
                "scripted": SCRIPTED,
                "opening": OPENING,
                "candidates": [CANDIDATE_SPEEDS, CANDIDATE_TIMES],
                "hybrid opening": HYBRID_OPENING,
            }
        ),
        environment=environment(),
    )


def _evaluation(
    attempt: str, transcript: Transcript, assessment: Assessment, depends_on
) -> Evaluation:
    return Evaluation(
        attempt,
        EVALUATOR,
        correct(assessment),
        metrics(assessment),
        {
            "readings": len(assessment.measurements),
            "model messages": len(transcript.steps),
            "tool calls": sum(len(s.message.tool_calls) for s in transcript.steps),
        },
        depends_on,
        code_identity(),
        digest_value(DESIGN.statement),
    )


# region: evaluate
def ledger(directory: Path, seeds: Sequence[int] = SEEDS) -> Ledger:
    """Every strategy at every seed as an attempt, evaluated by the
    evaluator from the recomputed readings. The model's sessions, and the
    hybrid that opens with them, depend on the fixtures in ``directory``; a
    session that does not replay is an invalid attempt of both, kept in the
    record."""
    found = Ledger(run_record(seeds))
    for seed in seeds:
        for name, choose in (("scripted", scripted), ("adaptive", adaptive)):
            transcript, assessment = run_policy(name, choose, seed)
            status = COMPLETED if assessment.fits is not None else FAILED
            found.add_attempt(Attempt(f"{name}-{seed}", name, found.cycle, status))
            found.add_evaluation(
                _evaluation(f"{name}-{seed}", transcript, assessment, ())
            )
        if seed not in RECORDINGS:
            continue
        artifact = Artifact.of(
            "recorded session", directory / RECORDINGS[seed], directory
        )
        try:
            _, session, assessment = replay_session(seed, directory)
        except (ReplayMismatch, ValueError, OSError) as error:
            note = f"{type(error).__name__}: {str(error).splitlines()[0]}"
            for name in ("LLM", "hybrid"):
                found.add_attempt(
                    Attempt(
                        f"{name}-{seed}",
                        name,
                        found.cycle,
                        INVALID,
                        (note,),
                        (artifact,),
                    )
                )
            continue
        status = COMPLETED if assessment.fits is not None else FAILED
        found.add_attempt(
            Attempt(f"LLM-{seed}", "LLM", found.cycle, status, (), (artifact,))
        )
        found.add_evaluation(
            _evaluation(f"LLM-{seed}", session, assessment, (artifact,))
        )
        last = session.steps[-1].message.text if session.steps else ""
        found.add_report(CandidateReport(f"LLM-{seed}", None, {"last message": last}))
        transcript, assessment = run_policy(
            "hybrid", hybrid(opening_of(session, seed)), seed
        )
        status = COMPLETED if assessment.fits is not None else FAILED
        found.add_attempt(
            Attempt(f"hybrid-{seed}", "hybrid", found.cycle, status, (), (artifact,))
        )
        found.add_evaluation(
            _evaluation(f"hybrid-{seed}", transcript, assessment, (artifact,))
        )
    return found


# endregion: evaluate


def _show(step: Step) -> None:
    if step.message.text:
        print(redact(step.message.text))
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(f"  {call.name}({call.arguments}) -> {dict(result.content)}")


def main(argv: list[str] | None = None) -> int:
    """The live entry point: ask the model at one seed, print the run and
    the assessment, optionally record it over its fixture."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument(
        "--record",
        action="store_true",
        help=f"write the run to {LESSON}/<fixture> as the replay fixture",
    )
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Task: {TASK}\nModel: {client.model}\n")
    allowlist = tools(options.seed)
    transcript = run(client, allowlist, SYSTEM, TASK, MAX_STEPS, on_step=_show)
    assessment = judge(DESIGN, transcript, allowlist)
    print(f"\nAssessment (recomputed, not the model's words): {assessment.outcome}")
    print(f"  design score {assessment.score:.3g}; {assessment.reason}")
    if options.record:
        today = datetime.date.today().isoformat()
        path = Path(LESSON) / RECORDINGS[options.seed]
        save_recording(path, transcript, today, *client.secrets)
        print(
            f"\nRecorded to {path}. Review it before you commit it, and set"
            " MODEL and RECORDED to this session's: replays accept no other."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
