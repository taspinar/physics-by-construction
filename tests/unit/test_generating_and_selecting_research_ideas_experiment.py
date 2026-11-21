"""The experiment of "Generating and selecting research ideas" (mechanics
22, RR1 of Issue #585): the checks of the seven ideas, the selection by the
declared rule without self-ratings, and the archive."""

import dataclasses
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.agents.specification import execute, parse
from pbc.mechanics.experiments import generating_and_selecting_research_ideas as lab
from pbc.mechanics.experiments.experiment_specification import laboratory
from pbc.research.ideas import (
    DEFERRED,
    EXTENSION,
    REJECTED,
    REPLICATION,
    SELECTED,
    assess,
    select,
    verify_archive,
)

MODULE = "pbc.mechanics.experiments.generating_and_selecting_research_ideas"
PAGE = "mechanics/22-generating-and-selecting-research-ideas"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("research-ideas")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def found():
    return lab.assessments()


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_checks_remove_the_three_ideas_for_their_stated_reasons(found):
    assert not found["spin"].feasible
    assert found["spin"].falsifiable is None
    # The action the page names as the reason is the one the refusal names.
    (action,) = lab.SPIN["actions"]
    assert found["spin"].problems[0] == (
        f"actions: {action!r} is not an action of the laboratory"
    )
    assert found["below-sixty"].feasible and not found["below-sixty"].falsifiable
    hundredth = found["hundredth"]
    assert hundredth.falsifiable and (hundredth.runs, hundredth.budget) == (32, 20)
    assert {k for k, a in found.items() if not a.passed} == {
        "spin",
        "below-sixty",
        "hundredth",
    }


def test_the_removed_ideas_were_rated_four_or_five_for_feasibility(found):
    ratings = {i.key: i.self_ratings["feasibility"] for i in lab.IDEAS}
    assert all(ratings[k] >= 4 for k, a in found.items() if not a.passed)
    assert lab.by_self_rating() == "spin"


def test_the_contributions_come_from_the_archive_of_answers(found):
    assert found["slow-throw"].contribution == EXTENSION
    assert found["middle-throw"].contribution == EXTENSION
    assert found["replication"].contribution == REPLICATION
    assert found["fast-throw"].contribution == REPLICATION


def test_the_rule_selects_the_slow_throw_by_the_judgement_of_interest(found):
    assert select(found, lab.JUDGEMENTS) == "slow-throw"
    # Without the judgement the two equal extensions are ordered by key.
    assert select(found, {}) == "middle-throw"
    assert found["slow-throw"].runs == found["middle-throw"].runs


def test_no_self_rating_reaches_the_selection():
    rated = [
        dataclasses.replace(
            i, self_ratings={r: 6 - v for r, v in i.self_ratings.items()}
        )
        for i in lab.IDEAS
    ]
    lab_ = laboratory()
    found = {i.key: assess(i, lab_, lab.ANSWERED) for i in rated}
    assert select(found, lab.JUDGEMENTS) == "slow-throw"


def test_the_count_of_runs_is_the_routes(found):
    lab_ = laboratory()
    for idea in lab.IDEAS:
        if found[idea.key].feasible:
            record = execute(parse(dict(idea.draft), lab_), lab_)
            assert len(record.runs) == min(
                found[idea.key].runs, idea.draft["stopping"]["max_runs"]
            )


def test_the_archive_holds_every_idea_and_finds_the_tampering(found):
    kept = lab.archive(found, "slow-throw")
    decisions = {e.idea.key: e.decision for e in kept.entries}
    assert decisions == {
        "replication": DEFERRED,
        "spin": DEFERRED,
        "slow-throw": SELECTED,
        "below-sixty": REJECTED,
        "middle-throw": DEFERRED,
        "fast-throw": DEFERRED,
        "hundredth": REJECTED,
    }
    assert all(e.reason for e in kept.entries)
    assert all(e.revisit for e in kept.entries if e.decision != SELECTED)
    assert verify_archive(kept.entries) == []
    problems = lab.tampered(kept)
    assert "entry 2: the idea changed after it was archived" in problems
    assert "entry 6: the chain to the entry before is broken" in problems
    again = lab.readded(kept)
    assert len(again.entries) == 8 and verify_archive(again.entries) == []


def test_the_third_exercise_counts_twenty_two_runs():
    assert lab.half_degree() == 22
