"""The counterexample search of "A proof an agent proposed": the tools, their
bounds and budget, and the claims judged on transcripts (Issue #609, on the
hunter of Issue #87 and the harness of ADR 004)."""

import math

import numpy as np
import pytest

from pbc.agents import ModelMessage, Step, ToolCall, ToolResult, Transcript
from pbc.agents.hunter import COUNTEREXAMPLE, INCONCLUSIVE, judge
from pbc.agents.proof_lab import (
    ANY_DIRECTION,
    ANY_TOOL,
    BUDGET,
    LIMIT,
    RESULT,
    UNIT_DIRECTION,
    UNIT_TOOL,
    energy_change,
    tools,
)

COLLISION = {"m1": 1.0, "m2": 2.0, "v1x": 3.0, "v1y": 0.0, "v2x": -1.0, "v2y": 0.0}


def identity(m1, m2, v1, v2, n):
    """The relative change of the kinetic energy from the closed form of the
    Lean identity collision_energy_change, written here apart from the
    program: 2 m1 m2 / (m1 + m2) s^2 (n.n - 1) over the energy before."""
    s = sum((a - b) * c for a, b, c in zip(v1, v2, n, strict=True))
    nn = sum(c * c for c in n)
    before = 0.5 * m1 * sum(a * a for a in v1) + 0.5 * m2 * sum(b * b for b in v2)
    return abs(2 * m1 * m2 / (m1 + m2) * s * s * (nn - 1)) / before


def transcript_of(tool, *experiments):
    """A transcript of accepted calls of ``tool``. The recorded results are
    lies: the judge must not read them."""
    calls = tuple(ToolCall(str(i), tool, a) for i, a in enumerate(experiments))
    results = tuple(
        ToolResult(str(i), tool, True, {RESULT: 0.0}) for i in range(len(calls))
    )
    return Transcript(
        model="m",
        system="s",
        task="t",
        steps=(Step(ModelMessage("done", calls), results),),
        finished=True,
    )


@pytest.mark.parametrize(
    "n", [(1.0, 1.0), (0.5, 0.0), (-0.3, 0.9), (1.0, -1.0), (0.2, 0.0)]
)
def test_the_change_of_energy_is_the_identity_for_any_direction(n):
    v1, v2 = (3.0, 0.0), (-1.0, 0.0)
    found = energy_change(2.5, 0.4, np.array(v1), np.array(v2), np.array(n))
    assert found == pytest.approx(identity(2.5, 0.4, v1, v2, n), rel=1e-12)
    assert found > LIMIT


@pytest.mark.parametrize("angle", [0.0, 17.0, 90.0, 137.5, 222.2, 359.0])
def test_a_unit_direction_keeps_the_energy_to_round_off(angle):
    result = tools().tool(UNIT_TOOL).function(**COLLISION, angle=angle)
    assert result[RESULT] < 1e-14


def test_a_collision_without_energy_is_refused():
    with pytest.raises(ValueError, match="zero"):
        energy_change(1.0, 1.0, np.zeros(2), np.zeros(2), np.array([1.0, 0.0]))


@pytest.mark.parametrize(
    "arguments",
    [
        {**COLLISION, "nx": 2.0, "ny": 0.0},  # a component beyond the bounds
        {**COLLISION, "m1": 0.0, "nx": 1.0, "ny": 0.0},  # a mass below the bounds
        {**COLLISION, "nx": "1", "ny": 0.0},  # not a number
        {**COLLISION, "nx": 1.0, "ny": 0.0, "code": "1+1"},  # an extra argument
        {**COLLISION, "nx": 1.0},  # a missing argument
    ],
)
def test_the_allowlist_refuses_calls_outside_its_bounds(arguments):
    result = tools().dispatch(ToolCall("x", ANY_TOOL, arguments))
    assert not result.ok


def test_the_budget_refuses_the_experiment_after_the_last():
    allowlist = tools()
    arguments = {**COLLISION, "angle": 30.0}
    outcomes = [
        allowlist.dispatch(ToolCall(str(i), UNIT_TOOL, arguments)).ok
        for i in range(BUDGET + 1)
    ]
    assert outcomes == [True] * BUDGET + [False]


def test_a_direction_of_the_wrong_length_refutes_the_first_claim():
    unit = {**COLLISION, "nx": 1.0, "ny": 0.0}
    diagonal = {**COLLISION, "nx": 1.0, "ny": 1.0}
    transcript = transcript_of(ANY_TOOL, unit, diagonal)
    verdict = judge(ANY_DIRECTION, transcript, tools())
    assert verdict.outcome == COUNTEREXAMPLE
    assert verdict.witness.arguments["ny"] == 1.0
    assert verdict.witness.value == pytest.approx(
        identity(1.0, 2.0, (3.0, 0.0), (-1.0, 0.0), (1.0, 1.0))
    )
    assert verdict.claim_type == "numerically-verified"


def test_unit_directions_leave_the_second_claim_inconclusive():
    experiments = [{**COLLISION, "angle": a} for a in (0.0, 45.0, 89.0, 300.0)]
    verdict = judge(UNIT_DIRECTION, transcript_of(UNIT_TOOL, *experiments), tools())
    assert verdict.outcome == INCONCLUSIVE
    assert verdict.tested == len(experiments)
    assert verdict.claim_type is None


def test_the_first_tools_experiments_do_not_count_for_the_second_claim():
    transcript = transcript_of(ANY_TOOL, {**COLLISION, "nx": 1.0, "ny": 1.0})
    verdict = judge(UNIT_DIRECTION, transcript, tools())
    assert verdict.outcome == INCONCLUSIVE
    assert verdict.tested == 0


def test_the_limit_is_far_above_round_off_and_far_below_a_wrong_length():
    # A direction one per cent too long changes the energy by about two per
    # cent of the approach term: many orders of magnitude above the limit.
    slightly_long = energy_change(
        1.0, 1.0, np.array([1.0, 0.0]), np.zeros(2), np.array([1.01, 0.0])
    )
    assert slightly_long > 1e6 * LIMIT
    assert math.ulp(1.0) < 1e-6 * LIMIT
