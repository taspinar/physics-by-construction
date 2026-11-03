"""The pilot of the evidence contract on one existing task (F137): the agent
against the baseline of EV3 on the projectile environment
(``pbc.discovery.benchmark``, protocol ``f81-projectile-1``).

The candidates are two committed frozen runs, the agent told the form of the
law (``projectile-full``, fixture on the EV2 page) and the plain model without
a ``measure`` tool (``plain-projectile``, fixture on the EV3 page), and the
baseline ``grid + least squares``, which the evaluator runs itself. Every
evaluation replays the candidate's fixture with ``benchmark.replay_cell``
(ADR 004: each tool call executed again, a recorded result that differs
fails) and scores it with the existing judge (``score_transcript``). What the
run recorded about itself (its cost record, its last message) is stored as
the candidate's report, labelled unverified.

The pilot reads the fixtures under ``root`` and writes nothing there; no
model, credential, or network is used. It changes no lesson's output: no
page imports this module.
"""

import json
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from pbc.agents.replay import ReplayMismatch
from pbc.discovery import benchmark
from pbc.discovery.benchmark import Cell, baseline_entry, replay_cell
from pbc.evidence.records import (
    COMPLETED,
    FAILED,
    INCONCLUSIVE,
    INVALID,
    MISSING,
    RAW,
    Artifact,
    Attempt,
    CandidateReport,
    Claim,
    Evaluation,
    FinalEvaluation,
    Ledger,
    RunRecord,
    digest_files,
    digest_value,
)

ROOT = Path(__file__).parents[3]
LESSONS = Path("site") / "lessons" / "agents-llm"
HOMES = {
    "EV2": LESSONS / "12-interactive-discovery-benchmarks",
    "EV3": LESSONS / "13-agent-versus-non-agent-baselines",
}
PROTOCOL = "projectile"
# The frozen runs that are candidates, by their name in ``benchmark.RUNS``.
CANDIDATES = {
    "projectile-full": Cell("projectile-full", "EV2"),
    "plain-projectile": Cell("plain-projectile", "EV3"),
}
BASELINE = "grid + least squares"

EVALUATOR = "pbc.evidence.pilot development evaluation, version 1"
FINAL_EVALUATOR = "pbc.evidence.pilot final evaluation, version 1"

# The isolation the pilot's evaluations actually have (requirements,
# "Security and privacy constraints"; ADR 022 decision 6).
ISOLATION = (
    "The candidate saw the system prompt, the task, and the tool"
    " specifications its fixture records, and the results of its own tool"
    " calls; the hidden gravity and the held-out settings reach no prompt,"
    " tool, or result (invariant I27).",
    "The hidden gravity and the held-out settings are in this repository"
    " (pbc.discovery.benchmark.PROTOCOLS): a candidate that can read the"
    " repository can read them. The evaluation is not private and cannot show"
    " that an informed candidate never saw them.",
    "The final evaluation scores on the protocol's held-out settings, the"
    " same as the development evaluation: it binds the result to the frozen"
    " candidate and its version, and is not an unseen test.",
    "Access to hidden values during a run and prior knowledge of the public"
    " problem are separate; the recording model's prior knowledge of"
    " projectile motion is not measured.",
    "Every tool result is recomputed by replay; a fixture whose recorded"
    " results were edited does not replay and is invalid.",
)


def protocol():
    return benchmark.PROTOCOLS[PROTOCOL]


def code_identity() -> str:
    """The digest of the evaluator's code: the sources of ``pbc.agents``,
    ``pbc.discovery``, and ``pbc.evidence``."""
    src = Path(__file__).parents[2]
    files = [
        p
        for package in ("agents", "discovery", "evidence")
        for p in (src / "pbc" / package).rglob("*.py")
    ]
    return digest_files(files, src)


def configuration_identity() -> str:
    """The digest of the protocol, hidden world included: it says which
    configuration was evaluated. A digest of a small hidden value can be
    inverted by trying values, so a sealed evaluation keeps it from the
    candidate; here the world is public anyway (``ISOLATION``)."""
    return digest_value(asdict(protocol()))


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "system": platform.system(),
    }


def run_record() -> RunRecord:
    p = protocol()
    task = benchmark.task_of("projectile-full")[1]
    return RunRecord(
        task=task,
        hypothesis=(
            "An agent that probes the system recovers g within the tolerance;"
            " a plain model without a probe does not; the grid baseline does."
        ),
        assumptions=(
            "The range follows the drag-free law of the environment, with"
            " Gaussian noise of the stated standard deviation.",
            "One seed per run; a run is one recorded model session.",
            "A claim is scored by its relative root-mean-square error on the"
            " held-out settings against the noise-free law.",
        ),
        protocol_version=p.version,
        split={
            "probed": "settings within the controls' bounds, chosen by the candidate",
            "held out": "settings beyond the bounds, the judge's configuration",
        },
        seeds=p.seeds,
        budgets={"probes": p.budget, "steps": p.max_steps},
        code=code_identity(),
        configuration=configuration_identity(),
        environment=environment(),
    )


def fixture(candidate: str, root: Path = ROOT) -> Path:
    """Where the fixture of ``candidate`` is under ``root``."""
    cell = CANDIDATES[candidate]
    return root / HOMES[cell.home] / benchmark.RUNS[cell.run].fixture


def _final_text(path: Path) -> str | None:
    try:
        steps = json.loads(path.read_text(encoding="utf-8"))["steps"]
        return str(steps[-1]["text"])
    except OSError, ValueError, KeyError, IndexError, TypeError:
        return None


def _evaluate(
    candidate: str, label: str, root: Path, evaluator: str
) -> tuple[str, tuple[str, ...], Artifact, Evaluation | None]:
    """Replay and score ``candidate``: its status, diagnostics, artifact,
    and evaluation (``None`` when its artifact is missing)."""
    path = fixture(candidate, root)
    artifact = Artifact.of("replay fixture", path, root, RAW)
    p = protocol()

    def evaluation(correct, metrics, resources) -> Evaluation:
        return Evaluation(
            label,
            evaluator,
            correct,
            metrics,
            resources,
            (artifact,),
            code_identity(),
            configuration_identity(),
        )

    if artifact.sha256 is None:
        return MISSING, (f"no replay fixture at {artifact.path}",), artifact, None
    try:
        _, transcript, score = replay_cell(CANDIDATES[candidate], path.parent)
    except (ReplayMismatch, ValueError, KeyError, TypeError) as error:
        diagnostic = f"{type(error).__name__}: {str(error).splitlines()[0]}"
        return INVALID, (diagnostic,), artifact, evaluation(None, {}, {})
    calls = sum(len(s.message.tool_calls) for s in transcript.steps)
    resources = {
        "probes": score.probes,
        "refused": score.refused,
        "model_messages": len(transcript.steps),
        "tool_calls": calls,
    }
    metrics = {"held_out_error": score.held_out_error, "tolerance": p.tolerance}
    if score.claim is None:
        status, notes, correct = FAILED, ("no claim submitted",), False
    elif not transcript.finished and score.held_out_error <= p.tolerance:
        # The claim is within the tolerance, but the run stopped at the step
        # limit: the protocol counts only a finished run as recovering.
        notes = ("the run reached the step limit with a claim within tolerance",)
        status, correct = INCONCLUSIVE, None
    else:
        status, notes, correct = COMPLETED, (), score.recovered
    return status, notes, artifact, evaluation(correct, metrics, resources)


def evaluate_attempt(
    ledger: Ledger,
    attempt_id: str,
    candidate: str,
    root: Path = ROOT,
    prior: tuple[str, ...] = (),
    reported: dict[str, Any] | None = None,
    claims_correct: bool | None = None,
) -> Attempt:
    """Record an attempt of ``candidate``, its evaluation, and its own
    report: the cost record and last message of the run, with ``reported``
    (what the candidate says beside them, never evaluated) and the
    correctness it claims."""
    status, notes, artifact, evaluation = _evaluate(
        candidate, attempt_id, root, EVALUATOR
    )
    attempt = Attempt(
        attempt_id, candidate, ledger.cycle, status, notes, (artifact,), prior
    )
    ledger.add_attempt(attempt)
    if evaluation is not None:
        ledger.add_evaluation(evaluation)
    info = benchmark.RUNS[CANDIDATES[candidate].run].info
    details = {
        "cost": asdict(info.cost),
        "final message": _final_text(fixture(candidate, root)),
        **(reported or {}),
    }
    ledger.add_report(CandidateReport(attempt_id, claims_correct, details))
    return attempt


def evaluate_baseline(ledger: Ledger, attempt_id: str) -> Attempt:
    """Run the grid baseline as the evaluator and record it as an attempt:
    it has no artifact of its own, its identity is the code and the
    configuration of its evaluation."""
    p = protocol()
    result = next(r for r in benchmark.baselines(PROTOCOL) if r.name == BASELINE)
    entry = baseline_entry(p, result)
    status = COMPLETED if result.claim is not None else FAILED
    attempt = Attempt(attempt_id, BASELINE, ledger.cycle, status)
    ledger.add_attempt(attempt)
    ledger.add_evaluation(
        Evaluation(
            attempt_id,
            EVALUATOR,
            entry.recovered,
            {"held_out_error": result.held_out_error, "tolerance": p.tolerance},
            {"probes": result.probes},
            (),
            code_identity(),
            configuration_identity(),
        )
    )
    return attempt


def freeze(ledger: Ledger, candidate: str, version: str, root: Path = ROOT):
    """Freeze ``candidate`` by the digest of its fixture."""
    artifact = Artifact.of("replay fixture", fixture(candidate, root), root, RAW)
    return ledger.freeze(candidate, version, (artifact,))


def final_evaluation(
    ledger: Ledger, candidate: str, root: Path = ROOT
) -> FinalEvaluation:
    """Evaluate the frozen ``candidate`` of the current cycle once, by the
    final evaluator, and record it (``Ledger.add_final`` refuses a second
    one, and one of a changed candidate)."""
    frozen = ledger.frozen_of(candidate, ledger.cycle)
    if frozen is None:
        raise ValueError(f"{candidate} is not frozen in cycle {ledger.cycle}")
    label = f"final evaluation of {candidate}, version {frozen.version}"
    status, notes, _, evaluation = _evaluate(candidate, label, root, FINAL_EVALUATOR)
    if evaluation is None:  # the artifact went missing after the freeze
        evaluation = Evaluation(
            label,
            FINAL_EVALUATOR,
            None,
            {},
            {},
            frozen.artifacts,
            code_identity(),
            configuration_identity(),
        )
    final = FinalEvaluation(
        candidate,
        frozen.version,
        frozen.cycle,
        frozen.digest,
        evaluation,
        ISOLATION,
        status,
        notes,
    )
    ledger.add_final(final, root)
    return final


CLAIMS = (
    (
        "agent-recovers",
        "The agent told the form of the law recovers g within the tolerance.",
        {"agent": True},
    ),
    (
        "plain-fails-baseline-recovers",
        "Without a probe the plain model does not recover g; the grid"
        " baseline with the same budget of probes does.",
        {"plain": False, "baseline": True},
    ),
)
SCOPE = (
    "the projectile environment under protocol f81-projectile-1, seed 0, one"
    " recorded run per candidate; not other environments, prompts, or models"
)


def run_pilot(root: Path = ROOT) -> Ledger:
    """The pilot: the three candidates evaluated, the two claims of EV3
    linked to them, and the agent frozen as version 1 with its final
    evaluation."""
    ledger = Ledger(run_record())
    ids = {"agent": "agent-1", "plain": "plain-1", "baseline": "baseline-1"}
    evaluate_attempt(ledger, ids["agent"], "projectile-full", root)
    evaluate_attempt(ledger, ids["plain"], "plain-projectile", root)
    evaluate_baseline(ledger, ids["baseline"])
    sources = (
        "docs/discovery-protocol.md",
        (HOMES["EV3"] / "index.qmd").as_posix(),
    )
    for id_, text, runs in CLAIMS:
        linked = {ids[k]: v for k, v in runs.items()}
        ledger.add_claim(Claim(id_, text, SCOPE, linked, sources))
    freeze(ledger, "projectile-full", "1", root)
    final_evaluation(ledger, "projectile-full", root)
    return ledger
