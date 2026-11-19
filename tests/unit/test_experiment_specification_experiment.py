"""The experiment of "From research question to experiment specification"
(mechanics 21): the scripted route executes the lesson's specification in
the build, and a specification without a stopping condition or a unit is
refused (acceptance criterion 2 of Issue #561)."""

import copy
from pathlib import Path

import numpy as np
import pytest
from support.experiments import assert_the_page_and_the_results_agree, run_entry_point

from pbc.agents import projectile_lab
from pbc.agents.specification import (
    BUDGET_SPENT,
    CRITERIA_MET,
    NO_VERDICT,
    PARTS,
    REFUTED,
    SUPPORTED,
    SpecificationRejected,
    execute,
    parse,
)
from pbc.mechanics.experiments import experiment_specification as lab
from pbc.mechanics.projectile import projectile_range

MODULE = "pbc.mechanics.experiments.experiment_specification"
PAGE = "mechanics/21-experiment-specification"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("experiment-specification")
    return directory, run_entry_point(MODULE, directory)


@pytest.fixture(scope="module")
def record():
    laboratory = lab.laboratory()
    return execute(parse(lab.SPECIFICATION, laboratory), laboratory)


def test_the_command_writes_what_the_page_shows(results):
    assert_the_page_and_the_results_agree(PAGE, *results)


def test_the_specification_of_the_lesson_has_the_seven_parts():
    assert tuple(lab.SPECIFICATION) == PARTS


def test_the_route_executes_the_specification_and_brackets_the_best_angle(record):
    assert record.stop == CRITERIA_MET
    assert record.criteria == {"resolved": True, "stable": True}
    assert record.verdict == SUPPORTED
    low, _, high = record.bracket
    assert high - low <= lab.SPECIFICATION["success"]["resolution"]["value"]
    # An independent reference: a scan of the simulation itself, finer than
    # the route's last step, at a quarter of its time step.
    angles = np.arange(30.0, 50.0, 0.0625)
    ranges = [
        projectile_range(25.0, a, projectile_lab.MASS, projectile_lab.DRAG, 0.001)
        for a in angles
    ]
    assert low < angles[int(np.argmax(ranges))] < high


def test_the_route_stays_inside_the_specification(record):
    variables = lab.SPECIFICATION["variables"]
    assert len(record.runs) <= lab.SPECIFICATION["stopping"]["max_runs"]
    for run in record.runs:
        assert set(run.arguments) == set(variables)
        assert variables["angle"]["low"] <= run.arguments["angle"]
        assert run.arguments["angle"] <= variables["angle"]["high"]
        assert run.arguments["speed"] == variables["speed"]["value"]
        halved = run.stage == "check"
        assert run.arguments["dt"] == variables["dt"]["value"] / (2 if halved else 1)
        # each recorded value is what the simulation gives for the arguments
        assert run.value == projectile_range(
            run.arguments["speed"],
            run.arguments["angle"],
            projectile_lab.MASS,
            projectile_lab.DRAG,
            run.arguments["dt"],
        )


def test_the_same_specification_refutes_its_hypothesis_without_drag():
    laboratory = lab.laboratory()
    record = execute(parse(lab.without_drag(), laboratory), laboratory)
    assert record.stop == CRITERIA_MET and record.verdict == REFUTED
    assert record.bracket[0] < 45.0 < record.bracket[2]
    changed = lab.without_drag()
    assert changed.pop("actions") == ["range_in_vacuum"]
    assert changed == {k: v for k, v in lab.SPECIFICATION.items() if k != "actions"}


@pytest.mark.parametrize(
    ("remove", "part", "message"),
    [
        (("stopping",), "stopping", "there is no stopping condition"),
        (("stopping", "max_runs"), "stopping", "a stopping condition is missing"),
        (("variables", "angle", "unit"), "variables", "angle has no unit"),
        (("variables", "dt", "unit"), "variables", "dt has no unit"),
        (("variables", "speed", "unit"), "variables", "speed has no unit"),
        (("observable", "unit"), "observable", "the observable has no unit"),
        (("success", "resolution", "unit"), "success", "the resolution has no unit"),
        (
            ("hypothesis", "prediction", "unit"),
            "hypothesis",
            "the prediction has no unit",
        ),
    ],
)
def test_without_a_stopping_condition_or_a_unit_it_is_rejected(remove, part, message):
    data = copy.deepcopy(lab.SPECIFICATION)
    target = data
    for key in remove[:-1]:
        target = target[key]
    del target[remove[-1]]
    with pytest.raises(SpecificationRejected) as rejected:
        parse(data, lab.laboratory())
    assert [p.part for p in rejected.value.problems] == [part]
    assert message in rejected.value.problems[0].message


def test_the_exercises_come_out_as_the_page_says(results):
    _, found = results
    numbers = found["numbers"]
    assert numbers["forty-verdict"] == SUPPORTED
    assert float(numbers["forty-high"]) < 40.0
    # the statement of the first exercise gives this bound of the first result
    assert float(numbers["drag-high"]) < 41.0
    assert numbers["short-stop"] == BUDGET_SPENT
    assert numbers["short-verdict"] == NO_VERDICT and numbers["short-runs"] == "12"
    assert [row[0] for row in found["tables"]["defects"]["rows"]] == [
        "variables",
        "variables",
        "stopping",
    ]
    assert [row[1] for row in found["tables"]["refusals"]["rows"]] == [
        "stopping",
        "variables",
        "variables",
    ]


def test_the_same_number_is_two_throws_in_two_units(results):
    _, found = results
    as_degrees = float(found["numbers"]["range-as-degrees"])
    as_radians = float(found["numbers"]["range-as-radians"])
    assert as_radians > 10.0 * as_degrees


def test_the_diagram_names_the_seven_parts():
    figure = lab.draw_specification_parts()
    words = " ".join(text.get_text() for text in figure.axes[0].texts).split()
    assert [word for word in words if word in PARTS] == list(PARTS)
