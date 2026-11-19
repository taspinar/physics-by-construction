"""The evaluation of reviewers on controlled cases (F150, lesson AE6;
``docs/discovery-protocol.md``, "Reviewer evaluation").

The cases are those of ``pbc.agents.review_lab.CASES``: steppers whose truth
is known. A decision on a case is classified against that truth: a faulty
case accepted is a missed error, a correct case rejected a false alarm. Two
kinds of reviewer are evaluated the same way: the recorded reviewers of the
panel, by the decisions their traces hold, and rules that decide from the
recomputed checks of those traces, by which the evaluator's own choices
(which checks count, which reviewers sit on the panel) are measured too.

Nothing here reads a model's words, and nothing calls a model.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from pbc.agents.review_lab import CASES, Case, Verdict

CORRECT_ACCEPTANCE = "correct acceptance"
CORRECT_REJECTION = "correct rejection"
MISSED_ERROR = "missed error"
FALSE_ALARM = "false alarm"
NO_DECISION = "no decision"
OUTCOMES = (
    CORRECT_ACCEPTANCE,
    CORRECT_REJECTION,
    MISSED_ERROR,
    FALSE_ALARM,
    NO_DECISION,
)


def classify(faulty: bool, accepted: bool | None) -> str:
    """The outcome of one decision on a case whose truth is known."""
    if accepted is None:
        return NO_DECISION
    if faulty:
        return MISSED_ERROR if accepted else CORRECT_REJECTION
    return CORRECT_ACCEPTANCE if accepted else FALSE_ALARM


def outcomes(
    decided: Mapping[int, bool], cases: Mapping[int, Case] = CASES
) -> dict[int, str]:
    """The outcome of every case, ``no decision`` where none was recorded."""
    return {n: classify(c.faulty, decided.get(n)) for n, c in cases.items()}


@dataclass(frozen=True)
class Tally:
    """The outcomes of one reviewer or rule over the cases: missed errors
    of the faulty cases, false alarms of the correct ones, and cases left
    undecided, each with its denominator."""

    missed: int
    faulty: int
    false_alarms: int
    correct: int
    undecided: int


def tally(found: Mapping[int, str], cases: Mapping[int, Case] = CASES) -> Tally:
    return Tally(
        missed=sum(o == MISSED_ERROR for o in found.values()),
        faulty=sum(c.faulty for c in cases.values()),
        false_alarms=sum(o == FALSE_ALARM for o in found.values()),
        correct=sum(not c.faulty for c in cases.values()),
        undecided=sum(o == NO_DECISION for o in found.values()),
    )


def applies(check: str, case: Case) -> bool:
    """Whether ``check`` tests something ``case`` claims: the bounded-energy
    check applies only to a method that claims a bounded energy
    (``pbc.verification.checks.verify``); every other check always does."""
    return check != "bounded-energy" or case.claim.bounded_energy


# A rule turns the recomputed verdicts of the panel into a decision on each
# case: True accepts it, None leaves it undecided (no check was run on it).
Rule = Callable[[Iterable[Verdict], Mapping[int, Case]], dict[int, bool | None]]


def _decide(
    verdicts: Iterable[Verdict],
    cases: Mapping[int, Case],
    counts: Callable[[Verdict, Case], bool],
) -> dict[int, bool | None]:
    found: dict[int, bool | None] = {}
    for number, case in cases.items():
        mine = [v for v in verdicts if v.candidate == number]
        if not mine:
            found[number] = None
            continue
        found[number] = not any(not v.passed and counts(v, case) for v in mine)
    return found


def any_failure_rule(
    verdicts: Iterable[Verdict], cases: Mapping[int, Case] = CASES
) -> dict[int, bool | None]:
    """AI4's rule (``review_lab.resolve``): a failed recomputed check
    rejects, whatever the case claims."""
    return _decide(list(verdicts), cases, lambda v, case: True)


def contract_rule(
    verdicts: Iterable[Verdict], cases: Mapping[int, Case] = CASES
) -> dict[int, bool | None]:
    """The contract's rule: a failed check rejects only when it tests
    something the case claims (``applies``)."""
    return _decide(list(verdicts), cases, lambda v, case: applies(v.check, case))


def energy_only_rule(
    verdicts: Iterable[Verdict], cases: Mapping[int, Case] = CASES
) -> dict[int, bool | None]:
    """A rule fitted to AI4's two pieces, where the bounded-energy check is
    the only one that tells them apart: reject when it fails, accept
    otherwise."""
    return _decide(list(verdicts), cases, lambda v, case: v.check == "bounded-energy")


# region: ablation
def ablate(
    verdicts: Iterable[Verdict],
    rule: Rule,
    reviewers: Iterable[str] | None = None,
    without_check: str | None = None,
    cases: Mapping[int, Case] = CASES,
) -> dict[int, str]:
    """The outcomes of ``rule`` on the verdicts of ``reviewers`` only (all
    when ``None``), without the verdicts of ``without_check``: what the panel
    decides when a reviewer or a check is removed."""
    kept = [
        v
        for v in verdicts
        if (reviewers is None or v.reviewer in reviewers) and v.check != without_check
    ]
    decided = rule(kept, cases)
    return {n: classify(cases[n].faulty, decided[n]) for n in cases}


# endregion: ablation


def cause(
    number: int,
    outcome: str,
    verdicts: Iterable[Verdict],
    cases: Mapping[int, Case] = CASES,
) -> str:
    """Why a decision on case ``number`` went wrong, from the recomputed
    checks the reviewer ran on it: for a missed error, whether a check it ran
    failed (seen and accepted), only a check that does not apply to the
    claim failed, or none did (not seen by its checks); for a
    false alarm, whether the only failures were of checks that do not apply
    to the claim, or no check failed at all; for a correct rejection, whether
    it rested on no check that applies (right, for a reason the evidence
    does not give); otherwise empty."""
    case = cases[number]
    mine = [v for v in verdicts if v.candidate == number]
    failed = [v for v in mine if not v.passed]
    if outcome == MISSED_ERROR:
        if any(applies(v.check, case) for v in failed):
            return "a failing check was run, and the case accepted"
        if failed:
            return "only a check the claim does not include failed"
        return "no check the reviewer ran fails on this fault"
    if outcome == FALSE_ALARM:
        if failed and not any(applies(v.check, case) for v in failed):
            return "a check failed that the claim does not include"
        if not failed:
            return "rejected although every check run passed"
        return "a failing check applies"
    if outcome == CORRECT_REJECTION and not any(applies(v.check, case) for v in failed):
        return "rejected, but on no check the claim includes"
    return ""


def agreement(first: Mapping[int, str], second: Mapping[int, str]) -> int:
    """The cases on which two repeats of a reviewer reached the same
    outcome."""
    return sum(first[n] == second[n] for n in first)


@dataclass(frozen=True)
class Regression:
    """A case whose outcome changed between a frozen evaluation and the
    current one."""

    case: int
    was: str
    now: str

    @property
    def worse(self) -> bool:
        good = (CORRECT_ACCEPTANCE, CORRECT_REJECTION)
        return self.was in good and self.now not in good


def regressions(
    frozen: Mapping[int, str], current: Mapping[int, str]
) -> list[Regression]:
    """Every case whose outcome differs between ``frozen`` and ``current``,
    in case order."""
    return [
        Regression(n, frozen[n], current[n])
        for n in sorted(frozen)
        if frozen[n] != current.get(n)
    ]
