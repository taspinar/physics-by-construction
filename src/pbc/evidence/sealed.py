"""A final evaluation on a withheld split (F150, lesson AE4;
``docs/discovery-protocol.md``, "The sealed split").

The task is the spring of D2 (``pbc.discovery.force_lab``, protocol
``f66-prior-knowledge-1``): find the angular frequency from at most 20 noisy
displacements read in the first three seconds, scored on settings far later.
The candidates are D2's three recorded runs, told the form of the law, told
the names of its parameters, and told nothing. The development evaluator
replays each and scores it on the protocol's held-out settings; the
candidate with the smallest development error among those that recover is
selected and frozen; the final evaluator replays the frozen candidate once
and scores its claim on ``SEALED``, later times that no development
evaluation used.

The sealed split is part of the configuration whose digest the run record
holds before any development evaluation, so a change of it after the
selection shows. It is withheld from the candidates' tools and from the
selection; it is not secret: it is in this module (``ISOLATION``).

The module reads the fixtures under ``root`` and writes nothing there; no
model, credential, or network is used.
"""

from collections.abc import Mapping
from dataclasses import asdict, replace
from pathlib import Path

from pbc.agents.replay import ReplayMismatch
from pbc.discovery import force_lab
from pbc.discovery.protocol import Protocol, Score
from pbc.evidence.pilot import code_identity, environment
from pbc.evidence.records import (
    COMPLETED,
    FAILED,
    INCONCLUSIVE,
    INVALID,
    MISSING,
    RAW,
    Artifact,
    Attempt,
    ContractError,
    Evaluation,
    FinalEvaluation,
    Ledger,
    RunRecord,
    digest_value,
)

# The repository, found from this file when it is needed. It is not a
# constant of the module: the input digest of a page that imports a module
# cannot follow a constant naming the whole repository
# (``pbc.authoring.digest``); the pages that read the fixtures name their
# directories themselves.
_LEVELS = 3


def repository() -> Path:
    """The root of the repository that holds this module."""
    return Path(__file__).parents[_LEVELS]


def _root(root: Path | None) -> Path:
    return repository() if root is None else root


def __getattr__(name: str) -> Path:
    # ``ROOT``, the repository, as in ``pbc.evidence.pilot``.
    if name == "ROOT":
        return repository()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# The page that holds the candidates' fixtures, relative to the repository.
HOME = "site/lessons/agents-llm/06-prior-knowledge-in-discovery"
PROTOCOL: Protocol = force_lab.PROTOCOLS["prior-knowledge"]
SEED = force_lab.SEED

# The candidates by name, and the run of ``force_lab.RUNS`` each one is.
CANDIDATES = {
    "told the form": "prior-full",
    "told the names": "prior-partial",
    "told nothing": "prior-none",
}

# The withheld split: later times than the development held-out settings
# (5 to 12 s), at amplitudes inside the probe bounds. Fixed before any
# development evaluation; used by the final evaluation only.
SEALED: tuple[Mapping[str, float], ...] = (
    {"amplitude": 1.0, "time": 15.0},
    {"amplitude": 2.0, "time": 20.0},
    {"amplitude": 0.8, "time": 25.0},
)
SEALED_VERSION = "f150-sealed-1"

EVALUATOR = "pbc.evidence.sealed development evaluation, version 1"
FINAL_EVALUATOR = "pbc.evidence.sealed final evaluation on the sealed split, version 1"

ISOLATION = (
    "Each candidate saw the system prompt, the task, and the tool"
    " specifications its fixture records, and the results of its own tool"
    " calls; neither the development held-out settings nor the sealed split"
    " reach a prompt, a tool, or a result (invariant I27).",
    "The selection read the development evaluations only; the sealed split"
    " was scored once, for the frozen candidate, after the freeze.",
    "The sealed split and the hidden stiffness are in this repository"
    " (pbc.evidence.sealed, pbc.discovery.force_lab): they are withheld from"
    " the candidates' tools and from the selection, not secret from a reader"
    " of the source.",
    "The candidates were recorded before the sealed split was chosen; a"
    " candidate recorded after it could have been tuned to it by someone"
    " who read it.",
)


def sealed_protocol() -> Protocol:
    """The protocol of the final evaluation: the development protocol with
    the sealed split as its held-out settings."""
    return replace(PROTOCOL, version=SEALED_VERSION, held_out=SEALED)


def configuration_identity() -> str:
    """The digest of the development protocol and of the sealed split
    together: recorded before the development evaluations, it shows a
    change of either afterwards."""
    return digest_value(
        {"development": asdict(PROTOCOL), "sealed": [dict(s) for s in SEALED]}
    )


def run_record() -> RunRecord:
    return RunRecord(
        task=(
            "Find the angular frequency of a mass on a spring of hidden"
            " stiffness from at most 20 noisy readings of its displacement,"
            " each at a chosen amplitude and time since the release."
        ),
        hypothesis=(
            "The candidate selected on its development error recovers the"
            " angular frequency within the tolerance on the sealed split too."
        ),
        assumptions=(
            "The displacement follows the spring of the environment, released"
            " at rest, with Gaussian noise of the stated standard deviation.",
            "A claim is scored by its root-mean-square error, relative to the"
            " amplitude, against the noise-free motion.",
            "One recorded run per candidate, seed 0.",
        ),
        protocol_version=PROTOCOL.version,
        split={
            "probed": "times in the first seconds, chosen by the candidate",
            "development": "later times, the protocol's held-out settings",
            "sealed": "later times still, used once by the final evaluation",
        },
        seeds=PROTOCOL.seeds,
        budgets={"probes": PROTOCOL.budget, "steps": PROTOCOL.max_steps},
        code=code_identity(),
        configuration=configuration_identity(),
        environment=environment(),
    )


def fixture(candidate: str, root: Path | None = None) -> Path:
    """Where the fixture of ``candidate`` is under ``root``."""
    root = _root(root)
    return root / HOME / force_lab.RUNS[CANDIDATES[candidate]].fixture


def _replay(candidate: str, root: Path) -> tuple[str, tuple[str, ...], Score | None]:
    """Replay ``candidate``: its status, diagnostics, and score."""
    path = fixture(candidate, root)
    if not path.is_file():
        return MISSING, (f"no replay fixture at {path.relative_to(root)}",), None
    try:
        _, _, score = force_lab.replay_run(CANDIDATES[candidate], path.parent)
    except (ReplayMismatch, ValueError, KeyError, TypeError) as error:
        return INVALID, (f"{type(error).__name__}: {str(error).splitlines()[0]}",), None
    if score.claim is None:
        return FAILED, ("no claim submitted",), score
    if not score.recovered and score.held_out_error <= PROTOCOL.tolerance:
        # Within the tolerance, yet not recovered: the run stopped at the
        # step limit, and the protocol counts only a finished run.
        return INCONCLUSIVE, ("the run reached the step limit",), score
    return COMPLETED, (), score


def _evaluation(
    label: str,
    evaluator: str,
    score: Score | None,
    error: float | None,
    artifact: Artifact,
    status: str = COMPLETED,
) -> Evaluation:
    if score is None or error is None or status == INCONCLUSIVE:
        correct, metrics, resources = None, {}, {}
    else:
        correct = bool(error <= PROTOCOL.tolerance)
        metrics = {"held_out_error": error, "tolerance": PROTOCOL.tolerance}
        resources = {"probes": score.probes, "refused": score.refused}
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


def develop(ledger: Ledger, root: Path | None = None) -> None:
    """Replay every candidate and score it on the development split."""
    root = _root(root)
    for number, candidate in enumerate(CANDIDATES, start=1):
        attempt_id = f"development-{number}"
        status, notes, score = _replay(candidate, root)
        artifact = Artifact.of("replay fixture", fixture(candidate, root), root, RAW)
        error = None if score is None else score.held_out_error
        ledger.add_attempt(
            Attempt(attempt_id, candidate, ledger.cycle, status, notes, (artifact,))
        )
        if status != MISSING:
            ledger.add_evaluation(
                _evaluation(attempt_id, EVALUATOR, score, error, artifact, status)
            )


def select(ledger: Ledger) -> str:
    """The candidate with the smallest development error among those the
    development evaluator found correct. Reads no other evaluation."""
    found = [
        (e.metrics["held_out_error"], ledger.attempt(e.attempt).candidate)
        for e in ledger.evaluations
        if e.evaluator == EVALUATOR and e.correct
    ]
    if not found:
        raise ContractError("no candidate recovered the law in development")
    return min(found)[1]


def freeze(ledger: Ledger, candidate: str, version: str, root: Path | None = None):
    """Freeze ``candidate`` by the digest of its fixture."""
    root = _root(root)
    artifact = Artifact.of("replay fixture", fixture(candidate, root), root, RAW)
    return ledger.freeze(candidate, version, (artifact,))


def sealed_error(claim: Mapping[str, float]) -> float:
    """The judge's error of ``claim`` on the sealed split."""
    return sealed_protocol().make(SEED).held_out_error(claim)


def final_on_sealed(
    ledger: Ledger, candidate: str, root: Path | None = None
) -> FinalEvaluation:
    """The final evaluation of the frozen ``candidate``: replay its fixture
    once more, and score its claim on the sealed split."""
    root = _root(root)
    frozen = ledger.frozen_of(candidate, ledger.cycle)
    if frozen is None:
        raise ContractError(f"{candidate} is not frozen in cycle {ledger.cycle}")
    label = f"final evaluation of {candidate}, version {frozen.version}"
    status, notes, score = _replay(candidate, root)
    error = None if score is None or score.claim is None else sealed_error(score.claim)
    artifact = Artifact.of("replay fixture", fixture(candidate, root), root, RAW)
    final = FinalEvaluation(
        candidate,
        frozen.version,
        frozen.cycle,
        frozen.digest,
        _evaluation(label, FINAL_EVALUATOR, score, error, artifact, status),
        ISOLATION,
        status,
        notes,
    )
    ledger.add_final(final, root)
    return final


def run_sealed(root: Path | None = None) -> Ledger:
    """Development, selection, freeze as version 1, and the one final
    evaluation on the sealed split."""
    root = _root(root)
    ledger = Ledger(run_record())
    develop(ledger, root)
    chosen = select(ledger)
    freeze(ledger, chosen, "1", root)
    final_on_sealed(ledger, chosen, root)
    return ledger
