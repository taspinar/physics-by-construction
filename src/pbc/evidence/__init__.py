"""The minimal capstone evidence contract (F137; ADR 022 decision 6;
``docs/discovery-protocol.md``, "The evidence contract").

``records`` holds the records and the evaluator's ledger: the task, the
attempts with their status and artifacts, the evaluations the evaluator
recomputed, the candidates' own reports apart from them and labelled
unverified, the claims with their evidence status, the frozen candidate and
its versioned final evaluation, and the check that a changed artifact
invalidates what depended on it. ``pilot`` is the contract on one existing
task, the agent against the baseline of EV3.
"""

from pbc.evidence.records import (
    ATTEMPT_STATUSES,
    COMPLETED,
    EVIDENCE_STATUSES,
    FAILED,
    INCONCLUSIVE,
    INDEPENDENTLY_CHECKED,
    INVALID,
    MISSING,
    NOT_EVALUATED,
    UNVERIFIED,
    Artifact,
    Attempt,
    CandidateReport,
    Claim,
    ContractError,
    Cycle,
    Evaluation,
    FinalEvaluation,
    FrozenCandidate,
    Invalidation,
    Ledger,
    RunRecord,
    Summary,
    candidate_digest,
    check,
    claim_status,
    digest_file,
    digest_value,
    load,
    save,
    summary,
)

__all__ = [
    "ATTEMPT_STATUSES",
    "COMPLETED",
    "EVIDENCE_STATUSES",
    "FAILED",
    "INCONCLUSIVE",
    "INDEPENDENTLY_CHECKED",
    "INVALID",
    "MISSING",
    "NOT_EVALUATED",
    "UNVERIFIED",
    "Artifact",
    "Attempt",
    "CandidateReport",
    "Claim",
    "ContractError",
    "Cycle",
    "Evaluation",
    "FinalEvaluation",
    "FrozenCandidate",
    "Invalidation",
    "Ledger",
    "RunRecord",
    "Summary",
    "candidate_digest",
    "check",
    "claim_status",
    "digest_file",
    "digest_value",
    "load",
    "save",
    "summary",
]
