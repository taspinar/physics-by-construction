"""The experiment of "Discrepancies, ablations, and follow-up experiments"
(mechanics 25, RR6 of Issue #594): the review of the slow-throw claim, its
discriminating tests, the ablation, the revised claim, and a revision of the
prose that resolves no request for evidence (acceptance criterion 2)."""

from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.agents.projectile_lab import DRAG
from pbc.agents.specification import SUPPORTED, UNDECIDED
from pbc.mechanics.drag import drag_constant
from pbc.mechanics.experiments import discrepancies_and_follow_up_experiments as lab
from pbc.mechanics.experiments.generating_and_selecting_research_ideas import (
    SLOW_THROW,
)
from pbc.research import followup

MODULE = "pbc.mechanics.experiments.discrepancies_and_follow_up_experiments"
PAGE = "mechanics/25-discrepancies-and-follow-up-experiments"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("follow-up")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def reviewed():
    return lab.follow_up()


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_new_actions_change_one_thing_of_the_throw():
    # The coefficient action at the projectile lesson's coefficient is the
    # throw with drag itself, run for run.
    assert drag_constant(lab.AIR, lab.COEFFICIENT, lab.AREA) == pytest.approx(
        DRAG, rel=1e-12
    )
    as_run = lab.run_route(SLOW_THROW)
    same = lab.run_route(lab.with_coefficient(lab.COEFFICIENT))
    assert [r.value for r in same.runs] == pytest.approx(
        [r.value for r in as_run.runs], rel=1e-12
    )
    fourth = lab.run_route(lab.with_action("range_fourth_order"))
    assert fourth.bracket == as_run.bracket
    assert [r.value for r in fourth.runs] != [r.value for r in as_run.runs]


def test_the_tests_decide_as_the_page_says(reviewed):
    log, records = reviewed
    assert records["fourth-order"].verdict == SUPPORTED
    assert records["top-of-range"].verdict == UNDECIDED
    assert records["top-at-half-degree"].verdict == UNDECIDED
    assert records["below-the-top"].verdict == SUPPORTED
    low, _, high = records["top-at-half-degree"].bracket
    assert low < 43.0 < high and high - low <= 0.5
    assert followup.verify_log(log.entries) == []


def test_the_statuses_of_the_findings(reviewed):
    log, _ = reviewed
    assert {f.key: followup.status(log, f.key) for f in lab.FINDINGS} == {
        "integrator": followup.RESOLVED,
        "coefficient": followup.RESOLVED,
        "wording": followup.REWORDED,
        "real-ball": followup.OPEN,
    }


def test_a_revision_of_the_prose_alone_resolves_no_request_for_evidence():
    # Criterion 2, on the review of the page: the same findings, answered by
    # a revision that cites no test.
    alone = lab.prose_only()
    for finding in lab.FINDINGS:
        expected = (
            followup.REWORDED if finding.kind == followup.WORDING else followup.OPEN
        )
        assert followup.status(alone, finding.key) == expected


def test_the_test_at_the_bottom_of_the_range_is_refused():
    assert followup.discriminates(lab.bottom_of_range()) == [
        "both explanations predict 'supported'"
    ]
    assert "does not discriminate" in lab.refused_test()
    assert lab.old_record_as_evidence().endswith("the record is not new evidence")


def test_the_ablation_and_the_reason_of_the_hypothesis():
    rows = {name: lab.run_route(spec) for name, _, spec in lab.ABLATION}
    claimed = rows["the claim as run"].bracket
    for same in ("fourth-order method", "time step halved", "coefficient 0.4"):
        assert rows[same].bracket == claimed
    assert rows["drag removed"].bracket[1] == pytest.approx(45.0)
    # The best angle falls as the coefficient grows, at the coefficients run.
    best = [rows[f"coefficient {cd}"].bracket[1] for cd in ("0.4", "0.8", "1.0")]
    assert best == sorted(best, reverse=True) and best[0] > best[-1]
    # The stated reason holds at the claim's coefficient and not at 0.8.
    assert lab.drag_over_weight(lab.COEFFICIENT) < 0.2 < lab.drag_over_weight(0.8)


def test_a_changed_entry_is_found(reviewed):
    log, _ = reviewed
    assert lab.tampered(log) == ["entry 10: its digest does not match its content"]
