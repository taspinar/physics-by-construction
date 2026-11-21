"""The experiment of "From a question or publication to a research plan"
(mechanics 23, RR2 of Issue #585): the plan template refuses a plan without
withheld tests or stopping conditions, and the scripted route executes the
replication and the original plan (acceptance criterion 3)."""

import copy
from pathlib import Path

import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.agents.specification import NO_VERDICT, SUPPORTED, UNDECIDED, execute, parse
from pbc.mechanics.experiments import from_question_to_research_plan as lab
from pbc.mechanics.experiments.experiment_specification import (
    SPECIFICATION,
    laboratory,
)
from pbc.research import plan as research

MODULE = "pbc.mechanics.experiments.from_question_to_research_plan"
PAGE = "mechanics/23-from-question-to-research-plan"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("research-plan")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def replication():
    return lab.run_plan(lab.REPLICATION)


@pytest.fixture(scope="module")
def original():
    return lab.run_plan(lab.ORIGINAL)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_no_two_tables_share_a_caption(results):
    # The page's tables are found by their captions: the stage tables of the
    # two plans name their plan, or the second would stand for the first.
    captions = [" ".join(t["caption"].split()) for t in results[1]["tables"].values()]
    assert len(set(captions)) == len(captions)
    assert "replication plan" in results[1]["tables"]["replication-stages"]["caption"]
    assert "original plan" in results[1]["tables"]["original-stages"]["caption"]


def test_both_plans_have_the_seven_parts():
    assert tuple(lab.REPLICATION) == research.PLAN_PARTS
    assert tuple(lab.ORIGINAL) == research.PLAN_PARTS


def test_the_template_refuses_a_plan_without_withheld_tests_or_stopping():
    assert [p for p, _ in lab.refusal(lab.without("withheld", lab.ORIGINAL))] == [
        "withheld"
    ]
    assert [p for p, _ in lab.refusal(lab.without("stopping", lab.ORIGINAL))] == [
        "stopping"
    ]
    assert lab.refusal(lab.seen_by_the_search(lab.ORIGINAL)) == [
        ("withheld", "finer scan is not withheld: the route uses dt = 0.002")
    ]
    assert lab.refusal(lab.ORIGINAL) == [] and lab.refusal(lab.REPLICATION) == []


def test_the_replication_reproduces_the_published_record(replication):
    assert replication.as_registered and replication.stop == research.COMPLETED
    assert all(replication.criteria.values())
    assert replication.verdict == SUPPORTED == lab.REPLICATION["source"]["verdict"]
    lab_ = laboratory()
    published = execute(parse(copy.deepcopy(SPECIFICATION), lab_), lab_)
    assert replication.record.runs == published.runs
    low, _, high = replication.record.bracket
    assert high < 44.0 and low <= replication.withheld[0].best <= high


def test_the_original_plan_is_supported_with_every_criterion(original):
    assert original.as_registered and all(original.criteria.values())
    assert research.PUBLISHED_VERDICT not in original.criteria
    assert original.verdict == SUPPORTED
    low, _, high = original.record.bracket
    assert low > 43.0 and high < 45.0
    assert original.control.passed and original.withheld[0].passed
    # Every run of every stage, within the plan's budget.
    assert original.runs == 20 + 20 + 20 + 33
    assert original.runs <= lab.ORIGINAL["stopping"]["max_runs"]


def test_the_grid_with_the_same_budget_misses_the_bracket(original):
    low, _, high = original.record.bracket
    assert len(original.grid.settings) == len(original.record.runs)
    assert not low <= original.grid.best <= high


def test_the_route_never_sees_the_withheld_time_step(original, replication):
    for record in (original, replication):
        steps = {run.arguments["dt"] for run in record.record.runs}
        assert steps == {0.004, 0.002}
        assert record.withheld[0].test.numerical not in steps


def test_a_moved_bound_is_a_deviation():
    deviation = lab.moved_prediction()
    assert not deviation.as_registered
    assert deviation.status == research.NOT_REGISTERED
    assert lab.record_bound(deviation) == 43.5


def test_the_exercises(original):
    medium = lab.run_plan(lab.medium_throw())
    assert medium.verdict == UNDECIDED and all(medium.criteria.values())
    low, _, high = medium.record.bracket
    assert low <= 43.0 <= high
    control = lab.run_plan(lab.wrong_control())
    assert control.stop == research.CONTROL_FAILED
    assert control.verdict == NO_VERDICT and control.record is None
