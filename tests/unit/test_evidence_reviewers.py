"""The evaluation of reviewers (``pbc.evidence.reviewers``): the four
outcomes of a decision, counted apart; rules that decide from recomputed
checks; ablations; the cause of a wrong decision; and regressions."""

from pbc.agents.review_lab import CASES, Verdict
from pbc.evidence.reviewers import (
    CORRECT_ACCEPTANCE,
    CORRECT_REJECTION,
    FALSE_ALARM,
    MISSED_ERROR,
    NO_DECISION,
    ablate,
    agreement,
    any_failure_rule,
    applies,
    cause,
    classify,
    contract_rule,
    energy_only_rule,
    outcomes,
    regressions,
    tally,
)

RK4 = next(n for n, c in CASES.items() if c.name == "Runge-Kutta 4")
EULER = next(n for n, c in CASES.items() if c.name == "explicit Euler as symplectic")
CLOCK = next(n for n, c in CASES.items() if c.name == "verlet with a stopped clock")


def v(reviewer, case, check, passed):
    return Verdict(reviewer, case, check, 0.0, 1.0, passed)


def test_the_four_outcomes_and_no_decision():
    assert classify(True, True) == MISSED_ERROR
    assert classify(True, False) == CORRECT_REJECTION
    assert classify(False, True) == CORRECT_ACCEPTANCE
    assert classify(False, False) == FALSE_ALARM
    assert classify(False, None) == NO_DECISION


def test_missed_errors_and_false_alarms_are_counted_over_their_own_cases():
    reject_all = outcomes({n: False for n in CASES})
    t = tally(reject_all)
    assert (t.missed, t.faulty, t.false_alarms, t.correct) == (0, 5, 3, 3)
    accept_all = tally(outcomes({n: True for n in CASES}))
    assert (accept_all.missed, accept_all.false_alarms) == (5, 0)
    assert tally(outcomes({})).undecided == len(CASES)


def test_the_energy_check_applies_only_to_a_claim_of_bounded_energy():
    assert not applies("bounded-energy", CASES[RK4])
    assert applies("bounded-energy", CASES[EULER])
    assert applies("clock", CASES[RK4])


def test_the_contract_rule_ignores_a_failure_the_claim_does_not_include():
    found = [
        v("physics", RK4, "bounded-energy", False),
        v("physics", RK4, "limits", True),
    ]
    assert any_failure_rule(found)[RK4] is False
    assert contract_rule(found)[RK4] is True
    assert contract_rule(found)[EULER] is None  # no check was run on it


def test_the_energy_only_rule_sees_only_the_energy_check():
    found = [
        v("numerics", CLOCK, "clock", False),
        v("physics", CLOCK, "bounded-energy", True),
    ]
    assert energy_only_rule(found)[CLOCK] is True
    assert contract_rule(found)[CLOCK] is False


def test_an_ablation_drops_a_reviewer_or_a_check():
    found = [v("numerics", CLOCK, "clock", False), v("physics", CLOCK, "limits", True)]
    assert ablate(found, contract_rule)[CLOCK] == CORRECT_REJECTION
    assert ablate(found, contract_rule, ["physics"])[CLOCK] == MISSED_ERROR
    assert ablate(found, contract_rule, without_check="clock")[CLOCK] == MISSED_ERROR
    assert ablate(found, contract_rule, ["nobody"])[CLOCK] == NO_DECISION


def test_the_cause_of_a_decision_is_read_from_the_checks_run():
    unseen = [v("physics", CLOCK, "limits", True)]
    assert cause(CLOCK, MISSED_ERROR, unseen).startswith("no check")
    seen = [v("numerics", CLOCK, "clock", False)]
    assert cause(CLOCK, MISSED_ERROR, seen).startswith("a failing check was run")
    outside = [v("physics", RK4, "bounded-energy", False)]
    assert (
        cause(RK4, FALSE_ALARM, outside)
        == "the only failing check is one the claim does not include"
    )
    assert cause(RK4, FALSE_ALARM, []) == "rejected although every check run passed"
    rk4_faulty = next(n for n, c in CASES.items() if c.name == "rk4 with equal weights")
    energy = [v("physics", rk4_faulty, "bounded-energy", False)]
    assert cause(rk4_faulty, MISSED_ERROR, energy).startswith("only a check")
    assert cause(rk4_faulty, CORRECT_REJECTION, energy).startswith(
        "rejected, and no check"
    )
    assert cause(CLOCK, CORRECT_REJECTION, seen) == ""


def test_agreement_and_regressions_compare_outcomes_case_by_case():
    frozen = {1: CORRECT_ACCEPTANCE, 2: CORRECT_REJECTION, 3: MISSED_ERROR}
    now = {1: FALSE_ALARM, 2: CORRECT_REJECTION, 3: CORRECT_REJECTION}
    assert agreement(frozen, now) == 1
    found = regressions(frozen, now)
    assert [(r.case, r.worse) for r in found] == [(1, True), (3, False)]
