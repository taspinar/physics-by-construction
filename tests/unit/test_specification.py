"""The experiment specification and its scripted route
(``pbc.agents.specification``): a specification is refused, before anything
runs, when it lacks a stopping condition or a unit; the route does only what
the specification permits, stops at its budget, and gives a verdict only
when the success criteria are met."""

import copy

import numpy as np
import pytest

from pbc.agents.specification import (
    ACTION_REFUSED,
    AT_THE_EDGE,
    BUDGET_SPENT,
    CRITERIA_MET,
    NO_VERDICT,
    PARTS,
    REFUTED,
    SUPPORTED,
    UNDECIDED,
    Action,
    Laboratory,
    Prediction,
    SpecificationRejected,
    execute,
    parse,
    verdict,
)
from pbc.agents.tools import Parameter, Tool

PEAK = 31.3  # degrees: where the hill of the test laboratory is highest


class Hill:
    """A laboratory with one action: the height of a hill at an angle, with
    a small error proportional to the step ``h``. It counts its calls."""

    def __init__(self, peak: float = PEAK, drift: float = 0.0):
        self.peak, self.drift, self.calls = peak, drift, []

    def height(self, angle: float, h: float) -> dict[str, float]:
        self.calls.append((angle, h))
        if angle == 13.0:
            raise ValueError("the hill is closed at 13 degrees")
        peak = self.peak + self.drift * h
        return {"height_m": 100.0 - (angle - peak) ** 2 + h}

    def laboratory(self) -> Laboratory:
        tool = Tool(
            name="height",
            description="the height of the hill",
            parameters=(
                Parameter("angle", "direction in degrees", 0.0, 90.0),
                Parameter("h", "step in m", 0.01, 1.0),
            ),
            function=self.height,
        )
        return Laboratory(
            (Action(tool, units={"angle": "deg", "h": "m"}, returns={"height_m": "m"}),)
        )


def written() -> dict:
    return {
        "question": "In which direction is the hill highest?",
        "hypothesis": {
            "statement": "The summit lies north of north-east.",
            "prediction": {
                "quantity": "angle",
                "relation": "below",
                "value": 45.0,
                "unit": "deg",
            },
        },
        "variables": {
            "angle": {"role": "varied", "unit": "deg", "low": 10.0, "high": 50.0},
            "h": {"role": "numerical", "unit": "m", "value": 0.1},
        },
        "observable": {"name": "height_m", "unit": "m", "goal": "largest"},
        "actions": ["height"],
        "success": {"resolution": {"value": 1.0, "unit": "deg"}, "stable": True},
        "stopping": {"max_runs": 40},
    }


def problems(data, laboratory=None) -> list[tuple[str, str]]:
    with pytest.raises(SpecificationRejected) as refused:
        parse(data, laboratory or Hill().laboratory())
    return [(p.part, p.message) for p in refused.value.problems]


def without(part: str, *path: str) -> dict:
    data = written()
    target = data
    for key in (part, *path[:-1]) if path else ():
        target = target[key]
    del target[path[-1] if path else part]
    return data


def test_the_written_specification_has_every_part_and_is_accepted():
    assert tuple(written()) == PARTS
    spec = parse(written(), Hill().laboratory())
    assert spec.varied.name == "angle" and spec.numerical.name == "h"
    assert spec.measure == "height" and spec.max_runs == 40


def test_parsing_executes_nothing():
    hill = Hill()
    parse(written(), hill.laboratory())
    assert hill.calls == []


@pytest.mark.parametrize("part", PARTS)
def test_a_specification_without_a_part_is_rejected_naming_the_part(part):
    hill = Hill()
    found = problems(without(part), hill.laboratory())
    assert part in {p for p, _ in found}
    assert hill.calls == []


def test_a_specification_without_a_stopping_condition_is_rejected():
    assert ("stopping", "the part is missing: there is no stopping condition") in (
        problems(without("stopping"))
    )
    for budget in (None, 0, -3, 2.5, True, "many"):
        data = written()
        data["stopping"] = {} if budget is None else {"max_runs": budget}
        found = problems(data)
        assert [p for p, _ in found] == ["stopping"], budget
        assert "a stopping condition is missing" in found[0][1]


@pytest.mark.parametrize(
    ("part", "path", "what"),
    [
        ("variables", ("angle", "unit"), "angle has no unit"),
        ("variables", ("h", "unit"), "h has no unit"),
        ("observable", ("unit",), "the observable has no unit"),
        ("hypothesis", ("prediction", "unit"), "the prediction has no unit"),
        ("success", ("resolution", "unit"), "the resolution has no unit"),
    ],
)
def test_a_quantity_without_a_unit_is_rejected(part, path, what):
    assert problems(without(part, *path)) == [(part, what)]


def test_an_empty_unit_is_no_unit():
    data = written()
    data["variables"]["angle"]["unit"] = "  "
    assert ("variables", "angle has no unit") in problems(data)


def test_a_unit_that_is_not_the_actions_is_rejected_not_converted():
    data = written()
    data["variables"]["angle"].update(unit="rad", low=0.2, high=0.9)
    data["hypothesis"]["prediction"].update(unit="rad", value=0.785)
    data["success"]["resolution"].update(unit="rad", value=0.02)
    found = problems(data)
    assert found == [
        (
            "variables",
            "angle is in rad, but height takes it in deg; convert it yourself",
        )
    ]
    # ... and a number in another unit is not compared with the bounds
    data = written()
    data["variables"]["h"].update(unit="mm", value=100.0)
    assert problems(data) == [
        ("variables", "h is in mm, but height takes it in m; convert it yourself")
    ]
    data = written()
    data["observable"]["unit"] = "cm"
    assert problems(data) == [
        ("observable", "height_m is specified in cm, but height returns it in m")
    ]


def test_every_problem_is_reported_not_only_the_first():
    data = without("stopping")
    del data["variables"]["h"]["unit"]
    data["actions"] = ["height", "dig"]
    parts = [p for p, _ in problems(data)]
    assert parts == ["variables", "actions", "stopping"]


def test_what_the_laboratory_does_not_permit_is_rejected():
    data = written()
    data["variables"]["angle"]["high"] = 120.0
    assert problems(data) == [
        ("variables", "angle = 120 is outside what height permits, 0 to 90")
    ]
    data = written()
    data["actions"] = ["os.system"]
    assert ("actions", "'os.system' is not an action of the laboratory") in (
        problems(data)
    )
    data = written()
    data["variables"]["wind"] = {"role": "fixed", "unit": "m/s", "value": 3.0}
    assert problems(data) == [("variables", "height takes no number called wind")]
    data = written()
    del data["variables"]["h"]
    data["success"]["stable"] = False
    assert problems(data) == [("variables", "height takes h, which is not specified")]
    data = written()
    data["variables"]["h"]["value"] = 0.015
    assert problems(data) == [
        ("success", "stable halves h to 0.0075, which height does not permit")
    ]


def test_a_prediction_must_be_one_a_result_can_contradict():
    data = written()
    del data["hypothesis"]["prediction"]
    assert problems(data) == [
        ("hypothesis", "a prediction that a result can contradict is missing")
    ]
    data = written()
    data["hypothesis"]["prediction"]["quantity"] = "height_m"
    assert [p for p, _ in problems(data)] == ["hypothesis"]
    data = written()
    data["hypothesis"]["prediction"]["relation"] = "near"
    assert [p for p, _ in problems(data)] == ["hypothesis"]


def test_an_unknown_part_and_a_wrong_shape_are_rejected():
    data = written()
    data["notes"] = "stop when it looks right"
    assert problems(data) == [
        ("specification", "'notes' is not a part of a specification")
    ]
    assert problems("find the summit") == [("specification", "must be a mapping")]
    data = written()
    data["variables"] = {}
    assert problems(data)[0] == (
        "variables",
        "exactly one varied variable is needed, got 0",
    )


def test_the_route_brackets_the_optimum_within_the_resolution():
    hill = Hill()
    record = execute(parse(written(), hill.laboratory()), hill.laboratory())
    low, best, high = record.bracket
    assert record.stop == CRITERIA_MET
    assert record.criteria == {"resolved": True, "stable": True}
    assert low < PEAK < high and high - low <= 1.0
    assert abs(best - PEAK) <= 0.5
    assert record.verdict == SUPPORTED
    assert [run.number for run in record.runs] == list(range(1, len(record.runs) + 1))
    assert [run.stage for run in record.runs[:9]] == ["scan"] * 9
    assert [run.stage for run in record.runs[-3:]] == ["check"] * 3


def test_the_route_calls_only_what_the_specification_permits():
    hill = Hill()
    data = written()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert len(hill.calls) == len(record.runs) <= data["stopping"]["max_runs"]
    angles = np.array([angle for angle, _ in hill.calls])
    assert angles.min() >= 10.0 and angles.max() <= 50.0
    assert {h for _, h in hill.calls} == {0.1, 0.05}
    assert [h for _, h in hill.calls[-3:]] == [0.05] * 3


def test_a_hypothesis_the_result_contradicts_is_refuted():
    data = written()
    data["hypothesis"]["prediction"]["value"] = 25.0
    hill = Hill()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert record.stop == CRITERIA_MET and record.verdict == REFUTED


def test_a_value_inside_the_bracket_is_undecided():
    data = written()
    data["hypothesis"]["prediction"]["value"] = PEAK
    hill = Hill()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert record.verdict == UNDECIDED


@pytest.mark.parametrize(
    ("relation", "value", "expected"),
    [
        ("below", 12.0, SUPPORTED),
        ("below", 11.0, UNDECIDED),
        ("below", 10.0, REFUTED),
        ("below", 9.0, REFUTED),
        ("above", 9.0, SUPPORTED),
        ("above", 10.5, UNDECIDED),
        ("above", 11.0, REFUTED),
        ("above", 12.0, REFUTED),
    ],
)
def test_the_verdict_compares_the_whole_bracket(relation, value, expected):
    prediction = Prediction("angle", relation, value, "deg")
    assert verdict(prediction, (10.0, 10.5, 11.0)) == expected


def test_the_route_stops_at_the_budget_and_gives_no_verdict():
    data = written()
    data["stopping"]["max_runs"] = 12
    hill = Hill()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert record.stop == BUDGET_SPENT and record.verdict == NO_VERDICT
    assert len(record.runs) == len(hill.calls) == 12
    assert record.criteria == {"resolved": False, "stable": False}


def test_an_answer_that_moves_with_the_numerical_variable_gives_no_verdict():
    hill = Hill(drift=20.0)  # the summit moves by one degree when h is halved
    record = execute(parse(written(), hill.laboratory()), hill.laboratory())
    assert record.stop == CRITERIA_MET
    assert record.criteria == {"resolved": True, "stable": False}
    assert record.verdict == NO_VERDICT


def test_a_refused_action_stops_the_route():
    data = written()
    data["variables"]["angle"].update(low=5.0, high=37.0)  # the scan passes 13
    hill = Hill()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert record.stop == ACTION_REFUSED and record.verdict == NO_VERDICT
    assert record.refusal == "the hill is closed at 13 degrees"
    assert len(record.runs) == 2 and record.bracket is None


def test_an_optimum_at_the_edge_of_the_range_is_not_an_answer():
    data = written()
    data["variables"]["angle"].update(low=40.0, high=80.0)
    hill = Hill()
    record = execute(parse(data, hill.laboratory()), hill.laboratory())
    assert record.stop == AT_THE_EDGE and record.verdict == NO_VERDICT


def test_the_smallest_value_is_found_when_that_is_the_goal():
    data = written()
    data["observable"]["goal"] = "smallest"
    hill = Hill()
    lab = hill.laboratory()
    valley = Tool(
        name="height",
        description="the depth of a valley",
        parameters=lab.actions[0].tool.parameters,
        function=lambda angle, h: {"height_m": (angle - PEAK) ** 2 + h},
    )
    lab = Laboratory((Action(valley, lab.actions[0].units, lab.actions[0].returns),))
    record = execute(parse(data, lab), lab)
    assert record.stop == CRITERIA_MET and record.bracket[0] < PEAK < record.bracket[2]


def test_the_specification_is_not_changed_by_parsing_or_running():
    data = written()
    before = copy.deepcopy(data)
    hill = Hill()
    execute(parse(data, hill.laboratory()), hill.laboratory())
    assert data == before


def test_an_action_declares_the_unit_of_every_argument():
    tool = Hill().laboratory().actions[0].tool
    with pytest.raises(ValueError, match="a unit is needed"):
        Action(tool, units={"angle": "deg"}, returns={"height_m": "m"})
    with pytest.raises(ValueError, match="returns nothing"):
        Action(tool, units={"angle": "deg", "h": "m"}, returns={})


def test_the_record_carries_the_identity_of_the_specification_it_ran():
    # Issue #606: the execution, not the caller, sets the identity: the
    # digest of the data parsed. Another specification gives another one.
    from pbc.evidence.records import digest_value

    hill = Hill()
    spec = parse(written(), hill.laboratory())
    assert spec.digest == digest_value(written())
    assert execute(spec, hill.laboratory()).specification == spec.digest
    other = written()
    other["success"]["resolution"]["value"] = 0.5
    assert parse(other, hill.laboratory()).digest != spec.digest
