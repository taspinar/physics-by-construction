"""The counterexample hunter: the claim format, the verdict, and the boundary
of its allowlist (Issue #87, ADR 004)."""

import math
from dataclasses import replace
from pathlib import Path

import pytest

from pbc.agents import Allowlist, ModelMessage, Step, ToolCall, ToolResult, Transcript
from pbc.agents.display import RunDisplay, VerdictDisplay
from pbc.agents.hunter import (
    COUNTEREXAMPLE,
    INCONCLUSIVE,
    FalsifiableClaim,
    judge,
)
from pbc.agents.hunter_lab import (
    BUDGET,
    FALSE_CLAIM,
    HUNTS,
    OPEN_CLAIM,
    RESULT,
    TOOL,
    replay_hunt,
    tools,
)

LESSON = (
    Path(__file__).parents[2]
    / "site"
    / "lessons"
    / "agents-llm"
    / "02-a-counterexample-hunter"
)
GOOD = {"method": "velocity Verlet", "steps_per_period": 32, "periods": 5}


def call(arguments, id="c"):
    return ToolCall(id=id, name=TOOL, arguments=arguments)


def transcript_of(*experiments, text="done"):
    """A transcript whose accepted calls are ``experiments``. The recorded
    results are lies: the judge must not read them."""
    calls = tuple(call(a, id=str(i)) for i, a in enumerate(experiments))
    results = tuple(
        ToolResult(str(i), TOOL, True, {RESULT: 0.0}) for i in range(len(calls))
    )
    return Transcript(
        model="m",
        system="s",
        task="t",
        steps=(Step(ModelMessage(text, calls), results),),
        finished=True,
    )


SYMPLECTIC = {"method": "symplectic Euler", "periods": 20}


# --- the allowlist of the hunt ------------------------------------------------


def test_a_valid_experiment_runs():
    result = tools().dispatch(call(GOOD))
    assert result.ok
    assert 0 < result.content[RESULT] < 0.01


@pytest.mark.parametrize(
    "arguments",
    [
        {**GOOD, "method": "os.system"},
        {**GOOD, "method": "velocity verlet"},
        {**GOOD, "method": ["velocity Verlet"]},
        {**GOOD, "method": None},
        {**GOOD, "method": 1},
        {**GOOD, "steps_per_period": 3},
        {**GOOD, "steps_per_period": 201},
        {**GOOD, "steps_per_period": 32.5},
        {**GOOD, "steps_per_period": True},
        {**GOOD, "steps_per_period": "32"},
        {**GOOD, "periods": 0},
        {**GOOD, "periods": 51},
        {**GOOD, "periods": 10**30},
        {**GOOD, "periods": float("nan")},
        {**GOOD, "code": "1 + 1"},
        {"method": "velocity Verlet"},
        [],
        "velocity Verlet",
    ],
)
def test_a_call_outside_the_bounds_is_rejected_and_costs_nothing(arguments):
    allowlist = tools()
    result = allowlist.dispatch(call(arguments))
    assert not result.ok
    # A rejected call costs nothing of the budget.
    for number in range(BUDGET):
        assert allowlist.dispatch(call(GOOD, id=str(number))).ok


def test_the_budget_refuses_the_call_beyond_it_unexecuted():
    runs = []

    def counted(x):
        runs.append(x)
        return {"y": 1.0}

    from pbc.agents import Parameter, Tool

    allowlist = Allowlist(
        (Tool("t", "d", (Parameter("x", "x", 0, 9),), counted),), budget=2
    )
    outcomes = [
        allowlist.dispatch(ToolCall(str(i), "t", {"x": i})).ok for i in range(4)
    ]
    assert outcomes == [True, True, False, False]
    assert runs == [0, 1]


def test_the_budget_must_be_positive():
    with pytest.raises(ValueError):
        Allowlist((), budget=0)


def test_a_fresh_allowlist_has_a_fresh_budget():
    for allowlist in (tools(), tools()):
        assert all(allowlist.dispatch(call(GOOD, id=str(i))).ok for i in range(BUDGET))
        assert not allowlist.dispatch(call(GOOD, id="late")).ok


def test_the_function_refuses_a_run_that_is_not_finite(monkeypatch):
    from pbc.agents import hunter_lab
    from pbc.mechanics.dynamics import State

    def broken(state, acceleration, dt):
        return State(t=state.t + dt, x=state.x * math.nan, v=state.v)

    monkeypatch.setitem(hunter_lab.METHODS, "velocity Verlet", broken)
    result = tools().dispatch(call(GOOD))
    assert not result.ok
    assert "not finite" in result.content["error"]


# --- the claim ----------------------------------------------------------------


def test_the_domain_fixes_the_method_and_bounds_the_rest():
    claim = FALSE_CLAIM
    assert claim.covers({**SYMPLECTIC, "steps_per_period": 16})
    assert claim.covers({**SYMPLECTIC, "steps_per_period": 200})
    assert not claim.covers({**SYMPLECTIC, "steps_per_period": 15})
    assert not claim.covers({**SYMPLECTIC, "steps_per_period": 32, "periods": 51})
    assert not claim.covers(
        {"method": "velocity Verlet", "steps_per_period": 32, "periods": 10}
    )


def test_the_predicate_is_an_upper_limit():
    assert FALSE_CLAIM.holds_on(0.05)
    assert not FALSE_CLAIM.holds_on(0.0500001)


def test_the_claims_agree_with_the_budget_of_the_allowlist():
    assert {h.claim.budget for h in HUNTS.values()} == {tools().budget} == {BUDGET}
    for hunt in HUNTS.values():
        assert hunt.claim.tool == TOOL
        assert str(hunt.claim.budget) in hunt.task


# --- the verdict --------------------------------------------------------------


def test_a_recomputed_counterexample_is_numerically_verified():
    run = transcript_of({**SYMPLECTIC, "steps_per_period": 32})
    verdict = judge(FALSE_CLAIM, run, tools())
    assert verdict.outcome == COUNTEREXAMPLE
    assert verdict.claim_type == "numerically-verified"
    assert verdict.witness.value == pytest.approx(0.1088617, rel=1e-5)
    assert verdict.tested == 1


def test_the_first_counterexample_in_the_order_of_the_run_is_the_witness():
    run = transcript_of(
        {**SYMPLECTIC, "steps_per_period": 200},
        {**SYMPLECTIC, "steps_per_period": 64},
        {**SYMPLECTIC, "steps_per_period": 16},
    )
    verdict = judge(FALSE_CLAIM, run, tools())
    assert verdict.witness.arguments["steps_per_period"] == 64
    assert verdict.tested == 3


def test_no_counterexample_is_inconclusive_and_has_no_claim_type():
    run = transcript_of(
        {"method": "velocity Verlet", "steps_per_period": 16, "periods": 50}
    )
    verdict = judge(OPEN_CLAIM, run, tools())
    assert verdict.outcome == INCONCLUSIVE
    assert verdict.claim_type is None
    assert verdict.witness is None
    assert verdict.closest.value == pytest.approx(0.03855, rel=1e-3)


def test_an_empty_hunt_is_inconclusive():
    verdict = judge(OPEN_CLAIM, transcript_of(), tools())
    assert (verdict.outcome, verdict.tested, verdict.closest) == (
        INCONCLUSIVE,
        0,
        None,
    )


def test_what_the_agent_writes_does_not_decide():
    holding = transcript_of(
        {"method": "velocity Verlet", "steps_per_period": 16, "periods": 50},
        text="Counterexample found! The drift is 90 per cent.",
    )
    assert judge(OPEN_CLAIM, holding, tools()).outcome == INCONCLUSIVE
    silent = transcript_of({**SYMPLECTIC, "steps_per_period": 32}, text="")
    assert judge(FALSE_CLAIM, silent, tools()).outcome == COUNTEREXAMPLE


def test_a_call_the_allowlist_could_not_have_accepted_is_not_evidence():
    run = transcript_of({**SYMPLECTIC, "steps_per_period": 32, "periods": 60})
    assert judge(FALSE_CLAIM, run, tools()).outcome == INCONCLUSIVE


def test_the_recorded_results_are_not_read():
    # transcript_of records a drift of 0 for every call: a counterexample is
    # found anyway, because the judge runs the experiment again.
    run = transcript_of({**SYMPLECTIC, "steps_per_period": 32})
    assert judge(FALSE_CLAIM, run, tools()).outcome == COUNTEREXAMPLE


def test_an_experiment_outside_the_domain_is_not_evidence():
    run = transcript_of(
        {"method": "explicit Euler", "steps_per_period": 16, "periods": 5},
        {**SYMPLECTIC, "steps_per_period": 8},
        {**SYMPLECTIC, "steps_per_period": 32, "periods": 60},
    )
    verdict = judge(FALSE_CLAIM, run, tools())
    assert verdict.outcome == INCONCLUSIVE
    assert verdict.tested == 0


def test_a_rejected_call_is_not_evidence():
    arguments = {**SYMPLECTIC, "steps_per_period": 32}
    run = transcript_of(arguments)
    step = run.steps[0]
    refused = replace(step.results[0], ok=False, content={"error": "no"})
    run = replace(run, steps=(Step(step.message, (refused,)),))
    assert judge(FALSE_CLAIM, run, tools()).outcome == INCONCLUSIVE


def test_only_the_budget_of_the_claim_counts():
    spent = [{**SYMPLECTIC, "steps_per_period": 200}] * BUDGET
    run = transcript_of(*spent, {**SYMPLECTIC, "steps_per_period": 32})
    assert judge(FALSE_CLAIM, run, tools()).outcome == INCONCLUSIVE


def test_a_value_that_is_not_finite_is_not_evidence():
    nan_claim = FalsifiableClaim(
        "s", TOOL, {"method": "velocity Verlet"}, {}, RESULT, 0.0, 3
    )
    allowlist = tools()
    tool = allowlist.tool(TOOL)
    broken = replace(tool, function=lambda **_: {RESULT: math.nan})
    run = transcript_of(GOOD)
    assert judge(nan_claim, run, Allowlist((broken,))).outcome == INCONCLUSIVE


# --- what the page prints -----------------------------------------------------


def test_a_counterexample_is_displayed_as_a_numerically_verified_claim():
    run = transcript_of({**SYMPLECTIC, "steps_per_period": 32})
    text = VerdictDisplay(judge(FALSE_CLAIM, run, tools()))._repr_markdown_()
    assert 'type="numerically-verified"' in text
    assert "counterexample, recomputed by this build" in text
    assert "0.108862" in text


def test_an_inconclusive_hunt_is_labelled_and_carries_no_claim_type():
    run = transcript_of(
        {"method": "velocity Verlet", "steps_per_period": 16, "periods": 50}
    )
    text = VerdictDisplay(judge(OPEN_CLAIM, run, tools()))._repr_markdown_()
    assert "Verdict: inconclusive" in text
    assert "{.claim" not in text
    assert "numerically-verified" not in text
    assert "does not show that it is true" in text


# --- the recorded hunts, replayed without a credential ------------------------


@pytest.mark.parametrize(
    ("name", "outcome"), [("false", COUNTEREXAMPLE), ("open", INCONCLUSIVE)]
)
def test_the_recorded_hunts_replay_to_their_verdicts(name, outcome, monkeypatch):
    for variable in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    recording, run, verdict = replay_hunt(name, LESSON)
    assert verdict.outcome == outcome
    assert run.finished
    assert not recording.placeholder


def test_the_hunt_that_cannot_be_settled_spends_its_budget():
    _, run, verdict = replay_hunt("open", LESSON)
    refused = [
        r
        for s in run.steps
        for r in s.results
        if not r.ok and "budget" in str(r.content)
    ]
    assert verdict.tested == BUDGET
    assert len(refused) == 1


def test_a_change_of_the_claim_text_fails_the_replay():
    from pbc.agents import ReplayMismatch, hunter_lab

    original = hunter_lab.HUNTS["false"]
    hunter_lab.HUNTS["false"] = replace(original, task=original.task + " Be quick.")
    try:
        with pytest.raises(ReplayMismatch, match="record the run again"):
            replay_hunt("false", LESSON)
    finally:
        hunter_lab.HUNTS["false"] = original


def test_authored_fixtures_are_not_called_recorded_runs():
    recording, transcript, _ = replay_hunt("false", LESSON)
    text = RunDisplay(recording, transcript, authored=True)._repr_markdown_()
    assert "Authored example, not a recorded model run" in text
    assert "(recorded)" not in text
    assert "Recorded run" not in text
