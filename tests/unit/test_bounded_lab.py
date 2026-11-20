"""The bounded lab of SA5 (``pbc.agents.bounded_lab``, Issue #580): the
injected failure, the budget, the protocol check from the runs, the
scripted route, and the replay of the recorded run (acceptance criterion
2)."""

from pathlib import Path

import pytest

from pbc.agents import ToolCall
from pbc.agents.bounded_lab import (
    BUDGET,
    FAIL_AT,
    FAILURE,
    PROTOCOL,
    REPLAY_FILE,
    TASK,
    Run,
    check_protocol,
    replay_fixture,
    runs_of,
    scripted_route,
    tools,
)
from pbc.agents.messages import ToolResult

LESSON = (
    Path(__file__).parents[2] / "site/lessons/agents-llm/01-an-agent-runs-an-experiment"
)


def call(angle, dt, n=0):
    return ToolCall(f"c{n}", "range_with_drag", {"speed": 25, "angle": angle, "dt": dt})


def test_the_failure_is_the_configured_accepted_run_and_costs_budget():
    allowlist = tools()
    rejected = allowlist.dispatch(call(40, 0.0))  # invalid: costs nothing
    assert not rejected.ok
    results = [allowlist.dispatch(call(40, 0.01, n)) for n in range(BUDGET + 1)]
    assert [r.ok for r in results].index(False) == FAIL_AT - 1
    assert results[FAIL_AT - 1].content == {"error": FAILURE}
    assert sum(r.ok for r in results) == BUDGET - 1
    assert "budget" in results[-1].content["error"]


def test_the_task_states_every_step_of_the_protocol():
    for _, text in PROTOCOL:
        assert text in TASK


def _runs(settings_and_results):
    return tuple(
        Run(call(a, dt, n), ToolResult(f"c{n}", "range_with_drag", ok, content), n)
        for n, (a, dt, ok, content) in enumerate(settings_and_results)
    )


def ok(value):
    return (True, {"range_m": value})


FAILED = (False, {"error": FAILURE})


def test_the_check_reads_the_runs_and_finds_the_step_and_the_angle():
    runs = _runs([
        (40, 0.01, *ok(35.79)), (40, 0.005, *ok(35.76)), (39, 0.01, *FAILED),
        (39, 0.01, *ok(35.76)), (41, 0.01, *ok(35.78)),
    ])  # fmt: skip
    checks, outcome = check_protocol(runs, stopped_by_itself=True)
    assert all(c.met for c in checks)
    assert (outcome.dt, outcome.angle, outcome.runs) == (0.01, 40, 5)


def test_a_step_that_has_not_converged_is_not_chosen():
    runs = _runs([(40, 0.02, *ok(35.85)), (40, 0.01, *ok(35.79))])
    checks, outcome = check_protocol(runs, stopped_by_itself=True)
    assert outcome.dt is None
    assert not checks[0].met


def test_a_failed_run_repeated_twice_breaks_the_recovery_rule():
    runs = _runs([
        (40, 0.01, *ok(35.79)), (40, 0.005, *ok(35.76)), (39, 0.01, *FAILED),
        (39, 0.01, *FAILED), (39, 0.01, *ok(35.76)), (41, 0.01, *ok(35.78)),
    ])  # fmt: skip
    checks, _ = check_protocol(runs, stopped_by_itself=True)
    assert {c.step: c.met for c in checks}["recovery"] is False


def test_a_run_after_the_search_was_met_breaks_the_stopping_rule():
    runs = _runs([
        (40, 0.01, *ok(35.79)), (40, 0.005, *ok(35.76)), (39, 0.01, *FAILED),
        (39, 0.01, *ok(35.76)), (41, 0.01, *ok(35.78)), (42, 0.01, *ok(35.75)),
    ])  # fmt: skip
    checks, _ = check_protocol(runs, stopped_by_itself=True)
    assert {c.step: c.met for c in checks}["stop"] is False
    checks, _ = check_protocol(runs[:5], stopped_by_itself=False)
    assert {c.step: c.met for c in checks}["stop"] is False


def test_the_scripted_route_meets_the_protocol_and_repeats_the_failed_run():
    runs, stopped = scripted_route(tools())
    checks, _ = check_protocol(runs, stopped_by_itself=True)
    assert all(c.met for c in checks)
    assert stopped.startswith("search met")
    failed = [n for n, r in enumerate(runs) if not r.result.ok]
    assert failed == [FAIL_AT - 1]
    assert runs[FAIL_AT].call.arguments == runs[FAIL_AT - 1].call.arguments


def test_the_scripted_route_with_too_small_a_budget_gives_no_answer():
    runs, stopped = scripted_route(tools(budget=4))
    assert stopped == "budget spent before the search was met: no answer"
    _, outcome = check_protocol(runs, stopped_by_itself=True)
    assert outcome.angle is None


def test_the_recorded_run_replays_meets_the_failure_and_reaches_the_script(
    tmp_path,
):
    """Criterion 2: the replayed trace meets the injected failure, recovers,
    and stops by itself; the scripted route reaches the same protocol."""
    recording, transcript = replay_fixture(LESSON)
    assert not recording.placeholder
    assert (LESSON / REPLAY_FILE).is_file()
    runs = runs_of(transcript)
    assert any(r.result.content.get("error") == FAILURE for r in runs)
    assert transcript.finished
    checks, agent = check_protocol(runs, transcript.finished)
    assert all(c.met for c in checks), checks
    script_runs, _ = scripted_route(tools())
    _, script = check_protocol(script_runs, stopped_by_itself=True)
    assert (agent.dt, agent.angle) == (script.dt, script.angle)


@pytest.mark.parametrize("budget", [0, -1])
def test_a_budget_below_one_is_refused(budget):
    with pytest.raises(ValueError):
        tools(budget=budget)
