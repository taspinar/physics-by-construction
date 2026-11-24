"""A research plan declared before execution, refused without withheld tests
or stopping conditions, and executed by the scripted route
(``pbc.research.plan``, RR2; acceptance criterion 3 of Issue #585)."""

import copy
from dataclasses import replace

import numpy as np
import pytest

from pbc.agents import projectile_lab
from pbc.agents.specification import NO_VERDICT, SUPPORTED, execute, parse
from pbc.mechanics.experiments.experiment_specification import (
    SPECIFICATION,
    laboratory,
)
from pbc.mechanics.projectile import projectile_range
from pbc.research import plan as research

PLAN = {
    "kind": "original",
    "source": {"reference": "a test", "statement": "a question"},
    "specification": SPECIFICATION,
    "baselines": {
        "control": {"action": "range_in_vacuum", "answer": 45.0},
        "grid": {"runs": 20},
    },
    "withheld": [
        {"name": "finer", "numerical": 0.001, "span": 2.0, "fraction": 8, "runs": 33}
    ],
    "success": [research.ROUTE_MET, research.CONTROL_PASSED, research.WITHHELD_PASSED],
    "stopping": {"max_runs": 120, "stop_if_control_fails": True},
}


def problems(data) -> list[tuple[str, str]]:
    with pytest.raises(research.PlanRejected) as refused:
        research.check(data, laboratory())
    return [(p.part, p.message) for p in refused.value.problems]


def changed(**parts) -> dict:
    data = copy.deepcopy(PLAN)
    for part, value in parts.items():
        if value is None:
            del data[part]
        else:
            data[part] = value
    return data


@pytest.fixture(scope="module")
def record():
    lab = laboratory()
    return research.execute(research.check(PLAN, lab), lab, research.freeze(PLAN))


def test_the_plan_has_the_seven_parts_and_is_accepted():
    assert tuple(PLAN) == research.PLAN_PARTS
    plan = research.check(PLAN, laboratory())
    assert plan.withheld[0].numerical == 0.001 and plan.max_runs == 120


@pytest.mark.parametrize("withheld", [None, []])
def test_a_plan_without_withheld_tests_is_refused(withheld):
    found = problems(changed(withheld=withheld))
    assert [part for part, _ in found] == ["withheld"]
    assert "no withheld test" in found[0][1]


def test_a_plan_without_stopping_conditions_is_refused():
    assert problems(changed(stopping=None)) == [
        ("stopping", "the part is missing: there is no stopping condition")
    ]
    found = problems(changed(stopping={"max_runs": 120}))
    assert found[0][0] == "stopping" and "stop_if_control_fails" in found[0][1]
    found = problems(changed(stopping={"stop_if_control_fails": True}))
    assert found[0][0] == "stopping" and "max_runs" in found[0][1]


def test_both_missing_are_reported_together():
    found = problems(changed(withheld=None, stopping=None))
    assert {part for part, _ in found} == {"withheld", "stopping"}


@pytest.mark.parametrize("numerical", [0.004, 0.002])
def test_a_test_at_a_setting_the_route_uses_is_not_withheld(numerical):
    data = copy.deepcopy(PLAN)
    data["withheld"][0]["numerical"] = numerical
    assert problems(data) == [
        ("withheld", f"finer is not withheld: the route uses dt = {numerical:g}")
    ]


def test_a_withheld_test_outside_the_action_or_over_its_budget_is_refused():
    data = copy.deepcopy(PLAN)
    data["withheld"][0]["numerical"] = 0.0005
    assert "outside" in problems(data)[0][1]
    data = copy.deepcopy(PLAN)
    data["withheld"][0]["runs"] = 32
    assert problems(data) == [
        ("withheld", "finer needs 33 runs and has a budget of 32")
    ]


def test_a_budget_that_does_not_cover_the_stages_is_refused():
    found = problems(changed(stopping={"max_runs": 112, "stop_if_control_fails": True}))
    assert found == [
        (
            "stopping",
            "the stages need up to 113 runs and the plan's budget is 112",
        )
    ]


def test_the_specification_is_checked_by_sa1s_parse():
    spec = copy.deepcopy(SPECIFICATION)
    del spec["stopping"]
    found = problems(changed(specification=spec))
    message = "stopping: the part is missing: there is no stopping condition"
    assert ("specification", message) in found


def test_a_replication_names_its_published_verdict_and_reproduces_it():
    data = changed(kind="replication")
    found = problems(data)
    assert ("source", "a replication names the verdict it was published with") in found
    assert (
        "success",
        "the criterion 'published verdict reproduced' is missing",
    ) in found
    original = changed(success=[*PLAN["success"], research.PUBLISHED_VERDICT])
    assert (
        "success",
        "an original investigation has no published verdict",
    ) in problems(original)


def test_the_route_executes_the_plan_and_every_run_is_within_it(record):
    assert record.stop == research.COMPLETED and record.as_registered
    assert all(record.criteria.values()) and record.verdict == SUPPORTED
    lab = laboratory()
    alone = execute(parse(copy.deepcopy(SPECIFICATION), lab), lab)
    assert record.record.runs == alone.runs  # the route of SA1, unchanged
    assert record.runs == 20 + 20 + 20 + 33 <= PLAN["stopping"]["max_runs"]
    assert record.control.passed
    low, _, high = record.control.record.bracket
    assert low <= 45.0 <= high


def test_the_withheld_test_is_opened_once_at_its_own_time_step(record):
    (outcome,) = record.withheld
    route_steps = {run.arguments["dt"] for run in record.record.runs}
    assert 0.001 not in route_steps
    low, centre, high = record.record.bracket
    assert outcome.settings[0] == pytest.approx(centre - 2.0)
    assert len(outcome.settings) == 33
    # Independently: the simulation at the withheld time step.
    expected = [
        projectile_range(25.0, a, projectile_lab.MASS, projectile_lab.DRAG, 0.001)
        for a in outcome.settings
    ]
    assert list(outcome.values) == expected
    assert outcome.best == outcome.settings[int(np.argmax(expected))]
    assert low <= outcome.best <= high and outcome.passed


def test_a_failed_control_stops_the_plan_before_the_route():
    data = copy.deepcopy(PLAN)
    data["baselines"]["control"]["answer"] = 42.0
    lab = laboratory()
    found = research.execute(research.check(data, lab), lab, research.freeze(data))
    assert found.stop == research.CONTROL_FAILED
    assert found.record is None and found.withheld == ()
    assert found.verdict == NO_VERDICT and found.runs == 20


def test_a_plan_changed_after_the_freeze_is_a_deviation():
    frozen = research.freeze(PLAN)
    data = copy.deepcopy(PLAN)
    data["specification"]["hypothesis"]["prediction"]["value"] = 41.0
    lab = laboratory()
    found = research.execute(research.check(data, lab), lab, frozen)
    assert not found.as_registered
    assert found.status == research.NOT_REGISTERED
    assert research.freeze(PLAN) == frozen  # the digest is of the content


@pytest.mark.parametrize("runs", [1, 0])
def test_a_grid_baseline_of_fewer_than_two_runs_is_refused(runs):
    # An even grid spans the varied range from end to end: one run has no
    # spacing (#593), and execute would otherwise divide by zero.
    data = copy.deepcopy(PLAN)
    data["baselines"]["grid"]["runs"] = runs
    assert [part for part, _ in problems(data)] == ["baselines"]
    data["baselines"]["grid"]["runs"] = 2
    assert research.check(data, laboratory()).grid_runs == 2


def laboratory_up_to(high: float):
    """The laboratory of the lesson with the angle permitted up to ``high``
    degrees only: a range whose end lies near the route's best angle."""
    lab = laboratory()
    return type(lab)(
        tuple(
            replace(
                action,
                tool=replace(
                    action.tool,
                    parameters=tuple(
                        replace(p, high=high) if p.name == "angle" else p
                        for p in action.tool.parameters
                    ),
                ),
            )
            for action in lab.actions
        )
    )


def test_a_withheld_test_near_the_end_of_the_range_is_clipped_to_it():
    # The route's best angle lies within the withheld test's span of the end
    # of the varied range, which is also what the action permits (#593).
    data = copy.deepcopy(PLAN)
    data["specification"]["variables"]["angle"]["high"] = 42.0
    data["stopping"]["stop_if_control_fails"] = False  # 45 deg is out of range
    lab = laboratory_up_to(42.0)
    plan = research.check(data, lab)
    _, centre, _ = execute(plan.specification, lab).bracket
    (test,) = plan.withheld
    unclipped = test.settings(centre, plan.specification.resolution)
    assert max(unclipped) > 42.0
    # Unclipped, the scan makes a call the action refuses.
    with pytest.raises(RuntimeError, match="refused call"):
        research._scan(lab, plan.specification, unclipped, test.numerical)

    found = research.execute(plan, lab, research.freeze(data))
    (outcome,) = found.withheld
    assert found.stop == research.COMPLETED
    assert list(outcome.settings) == [s for s in unclipped if s <= 42.0]
    assert min(outcome.settings) >= 20.0 and max(outcome.settings) == 42.0
    assert found.runs == len(found.control.record.runs) + len(
        found.record.runs
    ) + 20 + len(outcome.settings)


def test_the_control_record_does_not_carry_the_identity_of_the_specification(
    record,
):
    # Issue #606: the control runs another action than the specification,
    # so its record names a specification of its own; the route's record
    # names the plan's specification, as SA1's route alone does.
    lab = laboratory()
    alone = execute(parse(copy.deepcopy(SPECIFICATION), lab), lab)
    assert record.record.specification == alone.specification != ""
    assert record.control.record.specification not in ("", alone.specification)
