"""The evaluation protocol, in code (``docs/discovery-protocol.md``).

A run of an agent is scored from its frozen trace alone. ``score_transcript``
takes the tool calls of the transcript, executes them again on a fresh
environment of the same seed and budget, and scores the last accepted claim on
the settings held out of the controls' bounds. What the agent wrote, and what
the recorded results were, play no part: the score is a function of the calls
and the environment, so a test recomputes it.

The cost record (model, calls, tokens, money) belongs to the run that produced
the trace; it is stored beside it and never measured by a build.
"""

import datetime
import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from pbc.agents.loop import MAX_CALLS_PER_MESSAGE, Transcript
from pbc.agents.replay import Recording, load_recording, save_recording
from pbc.agents.tools import Allowlist
from pbc.discovery.baselines import BaselineResult
from pbc.discovery.environment import ENVIRONMENTS, Environment
from pbc.discovery.tools import MEASURE, SUBMIT, environment_allowlist

CONDITIONS = ("full", "partial", "none")
PROMPT_VERSION = "1"
TRACE_FORMAT = 1


@dataclass(frozen=True)
class Protocol:
    """One benchmark: an environment, a hidden world, the budget, the seeds
    (one run each), and the held-out error that counts as recovering the law.

    ``world`` holds the constructor arguments that set the hidden truth, and
    ``held_out`` the settings a claim is scored on, the environment's own when
    it is ``None``. Both are the judge's configuration: they reach no prompt,
    tool, or page.
    """

    version: str
    environment: str
    world: Mapping[str, float]
    budget: int
    seeds: tuple[int, ...]
    tolerance: float
    max_steps: int
    replay_tolerance: float = 1e-9
    held_out: tuple[Mapping[str, float], ...] | None = None

    def make(self, seed: int) -> Environment:
        cls = ENVIRONMENTS[self.environment]
        environment = cls(budget=self.budget, seed=seed, **self.world)  # type: ignore[call-arg]
        if self.held_out is not None:
            environment._held_out = self.held_out
        return environment

    def held_out_settings(self) -> tuple[dict[str, float], ...]:
        """The settings a claim is scored on under this protocol."""
        settings = self.held_out
        if settings is None:
            settings = ENVIRONMENTS[self.environment]._held_out
        return tuple(dict(s) for s in settings)


def prompts(environment: Environment, condition: str) -> tuple[str, str]:
    """The system prompt and the task for a condition of prior knowledge.

    ``full`` states the controls and the form of the law, ``partial`` the
    controls and the names of the parameters to report, ``none`` only the
    controls and the observation. All three submit the same parameters, so the
    scores compare. Nothing of the hidden truth is in any of them."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {', '.join(CONDITIONS)}")
    o = environment.observation
    controls = "; ".join(
        f"{c.name} ({c.unit}) from {c.low:g} to {c.high:g}"
        for c in environment.controls
    )
    system = (
        "You study a physical system by measuring it. Use only the tools you are"
        f" given. You have {environment.budget} probes."
    )
    task = f"Set {controls}, and read {o.name} ({o.unit}), which has noise. "
    names = ", ".join(c.name for c in environment.claim)
    if condition == "full":
        task += f"The law has the form: {environment.family}. Find {names}. "
    elif condition == "partial":
        task += f"Find the law, and report {names} of it. "
    else:
        task += "Find the law that gives it, and report the parameters you choose. "
    task += "Then submit your claim. It is scored on settings you cannot probe."
    return system, task


def prompt_sha(system: str, task: str) -> str:
    return hashlib.sha256(f"{system}\n{task}".encode()).hexdigest()


@dataclass(frozen=True)
class CostRecord:
    """The cost of the run that produced a trace, as that run recorded it."""

    model_calls: int
    tool_calls: int
    # None when the run reported no count, as a Claude Code session does not.
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None  # None when the provider gave none


@dataclass(frozen=True)
class TraceInfo:
    """What versions a trace: the protocol, the condition, the seed, the
    prompt, and the model with the date and the cost of the run."""

    protocol: str
    environment: str
    condition: str
    seed: int
    prompt_version: str
    prompt_sha256: str
    model: str
    recorded: str  # YYYY-MM-DD
    cost: CostRecord


def save_trace(
    directory: Path,
    transcript: Transcript,
    info: TraceInfo,
    placeholder: bool = False,
) -> None:
    """Freeze a run: ``replay.json`` (``pbc.agents.replay``) and ``trace.json``."""
    directory.mkdir(parents=True, exist_ok=True)
    save_recording(
        directory / "replay.json", transcript, info.recorded, placeholder=placeholder
    )
    text = json.dumps({"format": TRACE_FORMAT, **asdict(info)}, indent=2)
    (directory / "trace.json").write_text(text + "\n", encoding="utf-8")


def load_trace(directory: Path) -> tuple[Recording, TraceInfo]:
    """Read a frozen trace, rejecting one that lacks a field or a date."""
    data = json.loads((directory / "trace.json").read_text(encoding="utf-8"))
    if data.pop("format", None) != TRACE_FORMAT:
        raise ValueError(f"{directory} is not a frozen trace of format {TRACE_FORMAT}")
    info = TraceInfo(**{**data, "cost": CostRecord(**data["cost"])})
    datetime.date.fromisoformat(info.recorded)
    return load_recording(directory / "replay.json"), info


@dataclass(frozen=True)
class Score:
    """The score of one run, recomputed."""

    seed: int
    probes: int  # accepted probes, at most the budget
    refused: int  # calls the harness refused
    claim: Mapping[str, float] | None
    held_out_error: float
    recovered: bool

    @property
    def outcome(self) -> str:
        if self.claim is None:
            return "no claim"
        return "recovered" if self.recovered else "not recovered"


def score_transcript(
    protocol: Protocol,
    transcript: Transcript,
    seed: int,
    tools: Callable[[Environment], Allowlist] = environment_allowlist,
) -> Score:
    """Score ``transcript`` by running its tool calls again with ``tools``
    (the run's own) on a fresh environment of ``seed``. The same calls give
    the same score."""
    environment = protocol.make(seed)
    allowlist = tools(environment)
    probes = refused = 0
    claim: dict[str, float] | None = None
    for step in transcript.steps:
        for number, call in enumerate(step.message.tool_calls):
            # The loop refuses the calls of a message beyond its limit unrun.
            if number >= MAX_CALLS_PER_MESSAGE:
                refused += 1
                continue
            result = allowlist.dispatch(call)
            if not result.ok:
                refused += 1
            elif call.name == MEASURE:
                probes += 1
            elif call.name == SUBMIT:
                claim = {k: float(v) for k, v in call.arguments.items()}
    error = math.inf if claim is None else environment.held_out_error(claim)
    recovered = transcript.finished and error <= protocol.tolerance
    return Score(seed, probes, refused, claim, error, recovered)


def comparison(
    scores: tuple[Score, ...], baselines: tuple[BaselineResult, ...], tolerance: float
) -> list[dict[str, object]]:
    """Rows for the page: the agent's runs and each baseline, with the
    held-out error and whether it recovered the law; failures stay in."""
    rows: list[dict[str, object]] = [
        {
            "who": f"agent, seed {s.seed}",
            "probes": s.probes,
            "held_out_error": s.held_out_error,
            "recovered": s.recovered,
            "note": s.outcome,
        }
        for s in scores
    ]
    rows += [
        {
            "who": b.name,
            "probes": b.probes,
            "held_out_error": b.held_out_error,
            "recovered": b.success and b.held_out_error <= tolerance,
            "note": b.reason or "fit consistent with the noise",
        }
        for b in baselines
    ]
    return rows
