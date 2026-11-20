"""Lesson AE5: repeated trials, perturbed observations, injected tool
failures, and the uncertainty of a rate (F150; ``docs/discovery-protocol.md``,
"Repeated trials").

The task is the spring of D2 (``pbc.discovery.force_lab``, protocol
``f66-prior-knowledge-1``) in the partial condition: the agent is told the
controls and the name of the parameter to report, not the form of the law.
D2's one recorded run in that condition failed. Here the same task is run
again, each trial a fresh session, under three variants, each its own
protocol version:

- ``repeated``: the environment as published, at other noise seeds;
- ``noisier``: the readings' noise ``NOISE_FACTOR`` times larger;
- ``failing``: every ``FAIL_EVERY``-th accepted ``measure`` call fails with
  an error and uses no probe.

The prompt, the tools' specifications, and the budget are those of D2 in
every variant: the agent is told of neither perturbation. Each trial's
record (``TRIALS``) holds its protocol, seed, prompt SHA-256, model, date,
and the cost the recording session reported; the build replays every trial
and recomputes its score, and measures no cost.

Run a trial live on your machine (needs a model and its key; the optional
dependency ``openai``)::

    uv run --extra openai python -m pbc.evidence.robustness repeated 1
"""

import argparse
import datetime
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from scipy import stats

from pbc.agents.loop import Transcript, run
from pbc.agents.replay import (
    Recording,
    ReplayMismatch,
    load_recording,
    save_recording,
)
from pbc.agents.replay import replay as replay_recording
from pbc.agents.tools import Allowlist
from pbc.discovery import force_lab
from pbc.discovery.baselines import (
    BaselineResult,
    grid_probe,
    least_squares,
    random_probe,
)
from pbc.discovery.environment import Environment, Observation, OscillatorEnvironment
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
from pbc.discovery.tools import MEASURE, SUBMIT, environment_allowlist
from pbc.evidence.pilot import code_identity, environment
from pbc.evidence.records import (
    COMPLETED,
    FAILED,
    INVALID,
    RAW,
    Artifact,
    Attempt,
    CandidateReport,
    Evaluation,
    Ledger,
    RunRecord,
    digest_value,
)

BASE: Protocol = force_lab.PROTOCOLS["prior-knowledge"]
CONDITION = "partial"
NOISE_FACTOR = 5
FAIL_EVERY = 3
FAILURE = "the instrument did not respond: nothing was measured, and no probe was used"
# The noise seeds of the baselines in every variant.
BASELINE_SEEDS = tuple(range(1, 21))


class NoisierOscillator(OscillatorEnvironment):
    """The spring of D2 read with ``NOISE_FACTOR`` times its noise. Same name,
    same hidden world, same noise draws, scaled."""

    observation = Observation(
        "displacement",
        "m",
        OscillatorEnvironment.observation.sigma * NOISE_FACTOR,
        "position at that time",
    )


@dataclass(frozen=True)
class VariantProtocol(Protocol):
    """A protocol whose environment is chosen by the variant, not by the
    registry of ``pbc.discovery``."""

    noisier: bool = False

    def make(self, seed: int) -> Environment:
        cls = NoisierOscillator if self.noisier else OscillatorEnvironment
        return cls(budget=self.budget, seed=seed, **self.world)


def failing_instrument(environment: Environment) -> Allowlist:
    """The tools of D2 over ``environment``, with a ``measure`` whose every
    ``FAIL_EVERY``-th call that passes validation fails: it raises, so the
    harness returns an error result, and the environment is not touched."""
    tools = environment_allowlist(environment)
    accepted = 0

    def measure(**controls: float) -> dict[str, float]:
        nonlocal accepted
        accepted += 1
        if accepted % FAIL_EVERY == 0:
            raise RuntimeError(FAILURE)
        return environment.measure(**controls)

    return Allowlist(
        (replace(tools.tool(MEASURE), function=measure), tools.tool(SUBMIT))
    )


@dataclass(frozen=True)
class Variant:
    """One variant of the task: its protocol and the tools of its runs."""

    name: str
    description: str
    protocol: VariantProtocol
    tools: Callable[[Environment], Allowlist]


def _protocol(version: str, seeds: tuple[int, ...], noisier: bool = False):
    return VariantProtocol(
        version=version,
        environment=BASE.environment,
        world=BASE.world,
        budget=BASE.budget,
        seeds=seeds,
        tolerance=BASE.tolerance,
        max_steps=BASE.max_steps,
        noisier=noisier,
    )


VARIANTS: dict[str, Variant] = {
    "repeated": Variant(
        "repeated",
        "the readings as published, other noise seeds",
        _protocol("f150-robust-repeated-1", (1, 2, 3, 4)),
        environment_allowlist,
    ),
    "noisier": Variant(
        "noisier",
        f"the readings' noise {NOISE_FACTOR} times larger",
        _protocol("f150-robust-noisier-1", (1, 2, 3), noisier=True),
        environment_allowlist,
    ),
    "failing": Variant(
        "failing",
        f"every {FAIL_EVERY}rd accepted measurement fails",
        _protocol("f150-robust-failing-1", (1, 2, 3)),
        failing_instrument,
    ),
}


def task() -> tuple[str, str]:
    """The system prompt and the task of every trial: D2's, partial."""
    return prompts(BASE.make(force_lab.SEED), CONDITION)


# Who produced the recordings, and when (the plan of Issue #574).
MODEL = "claude-opus-5-5 in a Claude Code session"
RECORDED = "2026-11-19"
DIRECTORY = "site/lessons/agents-llm/23-robustness-and-statistical-uncertainty"


# Fixture names hold letters only (``replay-<name>.json``).
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four"}


@dataclass(frozen=True)
class Trial:
    """One recorded trial: its variant, seed, fixture, and record."""

    variant: str
    seed: int
    info: TraceInfo

    @property
    def name(self) -> str:
        return f"{self.variant}-{self.seed}"

    @property
    def fixture(self) -> str:
        return f"replay-{self.variant}{_WORDS[self.seed]}.json"


def _trial(variant: str, seed: int, messages: int, calls: int) -> Trial:
    protocol = VARIANTS[variant].protocol
    return Trial(
        variant,
        seed,
        TraceInfo(
            protocol=protocol.version,
            environment=protocol.environment,
            condition=CONDITION,
            seed=seed,
            prompt_version=PROMPT_VERSION,
            prompt_sha256=prompt_sha(*task()),
            model=MODEL,
            recorded=RECORDED,
            # The sub-agent's session reported no token counts and no price.
            cost=CostRecord(messages, calls, None, None, None),
        ),
    )


# The recorded trials, with the model messages and tool calls each session
# reported.
TRIALS: dict[str, Trial] = {
    t.name: t
    for t in (
        _trial("repeated", 1, 5, 19),
        _trial("repeated", 2, 5, 19),
        _trial("repeated", 3, 5, 17),
        _trial("repeated", 4, 5, 18),
        _trial("noisier", 1, 7, 27),
        _trial("noisier", 2, 6, 23),
        _trial("noisier", 3, 6, 21),
        _trial("failing", 1, 7, 22),
        _trial("failing", 2, 6, 21),
        _trial("failing", 3, 6, 21),
    )
}


def record_command(name: str) -> str:
    trial = TRIALS[name]
    return (
        f"uv run --extra openai python -m {__name__} {trial.variant} {trial.seed}"
        " --record"
    )


def replay_trial(name: str, directory: Path) -> tuple[Recording, Transcript, Score]:
    """Replay trial ``name`` from ``directory`` with its variant's tools over a
    fresh environment of its seed, and score it again with the same tools.

    Raises ``ValueError`` when the fixture and the record disagree on the
    model, the date, or the prompt, and ``ReplayMismatch`` when a recomputed
    tool result differs from the recorded one."""
    trial = TRIALS[name]
    variant = VARIANTS[trial.variant]
    protocol = variant.protocol
    recording = load_recording(directory / trial.fixture)
    if (recording.model, recording.recorded) != (trial.info.model, trial.info.recorded):
        raise ValueError(f"{trial.fixture} is not the trial recorded as {name}")
    if prompt_sha(recording.system, recording.task) != trial.info.prompt_sha256:
        raise ValueError(f"{trial.fixture} was recorded with another prompt")
    system, text = task()
    transcript = replay_recording(
        recording,
        variant.tools(protocol.make(trial.seed)),
        system=system,
        task=text,
        tolerance=protocol.replay_tolerance,
        max_steps=protocol.max_steps,
        rerecord=record_command(name),
    )
    score = score_transcript(protocol, transcript, trial.seed, variant.tools)
    return recording, transcript, score


def failed_calls(transcript: Transcript) -> int:
    """The calls the instrument failed (not those the harness refused)."""
    return sum(
        1
        for step in transcript.steps
        for result in step.results
        if not result.ok and result.content.get("error") == FAILURE
    )


def success_interval(successes: int, trials: int, level: float = 0.95):
    """The exact (Clopper-Pearson) interval for a success rate from
    ``successes`` of ``trials``: every rate whose probability of giving a
    count at least as extreme is above ``(1 - level) / 2`` on that side."""
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError(
            f"need 0 <= successes <= trials >= 1, got {successes}, {trials}"
        )
    tail = (1.0 - level) / 2.0
    low = (
        0.0
        if successes == 0
        else stats.beta.ppf(tail, successes, trials - successes + 1)
    )
    high = (
        1.0
        if successes == trials
        else stats.beta.ppf(1.0 - tail, successes + 1, trials - successes)
    )
    return float(low), float(high)


def baseline(variant: str, method: str, seed: int) -> BaselineResult:
    """A baseline without a model on ``variant`` at noise seed ``seed``:
    ``"grid"`` or ``"random"`` probing and least squares. It is not run
    through the failing instrument: a baseline that retried every failed
    call would read what it reads on the published one, so on the
    ``"failing"`` variant it is the published baseline by construction, and
    the calls the retries would cost are computed by ``calls_for``, not
    run."""
    world = VARIANTS[variant].protocol.make(seed)
    data = grid_probe(world) if method == "grid" else random_probe(world, seed)
    return least_squares(VARIANTS[variant].protocol.make(seed), data, method)


def baseline_recovers(result: BaselineResult) -> bool:
    """As ``pbc.discovery.benchmark.baseline_entry``: a fit consistent with
    the noise whose claim is within the tolerance."""
    return bool(result.success and result.held_out_error <= BASE.tolerance)


def calls_for(readings: int) -> int:
    """The ``measure`` calls a method that retries every failure needs on the
    failing instrument to get ``readings`` readings."""
    calls = 0
    got = 0
    while got < readings:
        calls += 1
        if calls % FAIL_EVERY:
            got += 1
    return calls


def baseline_errors(variant: str, method: str) -> np.ndarray:
    """The held-out error of a baseline at every seed of ``BASELINE_SEEDS``."""
    return np.array(
        [baseline(variant, method, s).held_out_error for s in BASELINE_SEEDS]
    )


EVALUATOR = "pbc.evidence.robustness evaluation, version 1"


def run_record() -> RunRecord:
    _system, text = task()
    return RunRecord(
        task=text,
        hypothesis=(
            "The agent told the names recovers the angular frequency of the"
            " spring at a rate that does not depend on the run, and the"
            " perturbations the agent is not told of lower it."
        ),
        assumptions=(
            "Each trial is one recorded session of a fresh model, with the"
            " same prompt and tools.",
            "A trial is scored as in D2: its claim's root-mean-square error,"
            " relative to the amplitude, on the protocol's held-out settings.",
            "The trials of a variant are independent, so a count of recoveries"
            " is binomial.",
        ),
        protocol_version=", ".join(v.protocol.version for v in VARIANTS.values()),
        split={
            "probed": "times in the first seconds, chosen by the candidate",
            "held out": "later times, the protocol's held-out settings",
        },
        seeds=tuple(sorted({t.seed for t in TRIALS.values()})),
        budgets={"probes": BASE.budget, "steps": BASE.max_steps},
        code=code_identity(),
        configuration=digest_value(
            {
                name: {"protocol": asdict(v.protocol), "fail every": FAIL_EVERY}
                for name, v in VARIANTS.items()
            }
        ),
        environment=environment(),
    )


def ledger(directory: Path) -> Ledger:
    """Every trial as an attempt of its variant, replayed and scored by the
    evaluator; the cost the session recorded is the trial's own report."""
    found = Ledger(run_record())
    root = directory
    for name, trial in TRIALS.items():
        path = directory / trial.fixture
        artifact = Artifact.of("replay fixture", path, root, RAW)
        try:
            _, transcript, score = replay_trial(name, directory)
        except (ReplayMismatch, ValueError) as error:
            note = f"{type(error).__name__}: {str(error).splitlines()[0]}"
            found.add_attempt(
                Attempt(name, trial.variant, found.cycle, INVALID, (note,), (artifact,))
            )
            continue
        status = COMPLETED if score.claim is not None else FAILED
        found.add_attempt(
            Attempt(name, trial.variant, found.cycle, status, (), (artifact,))
        )
        found.add_evaluation(
            Evaluation(
                name,
                EVALUATOR,
                score.recovered,
                {"held_out_error": score.held_out_error, "tolerance": BASE.tolerance},
                {
                    "probes": score.probes,
                    "failed": failed_calls(transcript),
                    "refused": score.refused - failed_calls(transcript),
                    "model_messages": len(transcript.steps),
                    "tool_calls": sum(
                        len(s.message.tool_calls) for s in transcript.steps
                    ),
                },
                (artifact,),
                code_identity(),
                found.record.configuration,
            )
        )
        found.add_report(CandidateReport(name, None, {"cost": asdict(trial.info.cost)}))
    return found


def _show(step) -> None:
    if step.message.text:
        print(step.message.text)
    for call, result in zip(step.message.tool_calls, step.results, strict=False):
        print(f"  {call.name}({call.arguments}) -> {dict(result.content)}")


def main(argv: list[str] | None = None) -> int:
    """The live entry point: run one trial with the provider's model, print
    it and its score, and optionally record it over its fixture."""
    from pbc.agents.providers import PROVIDER, load_client

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("variant", choices=sorted(VARIANTS))
    parser.add_argument("seed", type=int)
    parser.add_argument("--record", action="store_true")
    options = parser.parse_args(argv)
    try:
        client = load_client(PROVIDER)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    variant = VARIANTS[options.variant]
    protocol = variant.protocol
    system, text = task()
    transcript = run(
        client,
        variant.tools(protocol.make(options.seed)),
        system,
        text,
        protocol.max_steps,
        on_step=_show,
    )
    score = score_transcript(protocol, transcript, options.seed, variant.tools)
    print(f"\nHeld-out error {score.held_out_error:.3g}: {score.outcome}\n")
    if options.record:
        today = datetime.date.today().isoformat()
        path = Path(f"replay-{options.variant}{_WORDS[options.seed]}.json")
        save_recording(path, transcript, today, *client.secrets)
        print(
            f"Recorded to {path}. Review it, then set the model, the date"
            f" ({today}), and the cost of the run in TRIALS of {__name__}."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
