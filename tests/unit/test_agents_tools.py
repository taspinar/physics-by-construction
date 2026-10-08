"""The allowlist boundary: what a model may and may not make the harness do."""

import math

import pytest

from pbc.agents import Allowlist, ModelMessage, Parameter, Tool, ToolCall, run
from pbc.agents.loop import MAX_CALLS_PER_MESSAGE
from pbc.agents.projectile_lab import tools


def call(name, arguments, id="c1"):
    return ToolCall(id=id, name=name, arguments=arguments)


@pytest.fixture
def counting():
    """An allowlist with one tool that counts how often it really ran."""
    runs = []

    def double(x):
        runs.append(x)
        return {"y": 2 * x}

    allowlist = Allowlist(
        (Tool("double", "doubles", (Parameter("x", "a number", 0, 10),), double),)
    )
    return allowlist, runs


def test_a_valid_call_runs_the_function(counting):
    allowlist, runs = counting
    result = allowlist.dispatch(call("double", {"x": 4}))
    assert result.ok
    assert dict(result.content) == {"y": 8}
    assert runs == [4]


@pytest.mark.parametrize(
    "name",
    [
        "os.system",
        "__import__",
        "eval",
        "exec",
        "open",
        "subprocess.run",
        "double ",
        "DOUBLE",
        "",
        None,
        ["double"],
    ],
)
def test_a_tool_outside_the_allowlist_is_rejected_unexecuted(counting, name):
    allowlist, runs = counting
    result = allowlist.dispatch(call(name, {"x": 1}))
    assert not result.ok
    assert "not an allowed tool" in result.content["error"]
    assert runs == []


@pytest.mark.parametrize(
    ("arguments", "reason"),
    [
        ({"x": 11}, "between 0 and 10"),
        ({"x": -0.001}, "between 0 and 10"),
        # JSON allows an integer too large for a float; it is refused, not
        # converted (converting it raises OverflowError).
        ({"x": 10**400}, "between 0 and 10"),
        ({"x": -(10**400)}, "between 0 and 10"),
        ({"x": math.inf}, "finite"),
        ({"x": math.nan}, "finite"),
        ({"x": "5"}, "must be a number"),
        ({"x": True}, "must be a number"),
        ({"x": None}, "must be a number"),
        ({"x": [1]}, "must be a number"),
        ({}, "missing arguments: x"),
        ({"x": 1, "code": "print(1)"}, "unknown arguments: code"),
        ("x=1", "must be an object"),
        (None, "must be an object"),
        ([1], "must be an object"),
    ],
)
def test_arguments_outside_their_bounds_are_rejected_unexecuted(
    counting, arguments, reason
):
    allowlist, runs = counting
    result = allowlist.dispatch(call("double", arguments))
    assert not result.ok
    assert reason in result.content["error"]
    assert runs == []


def test_an_integer_parameter_rejects_a_float():
    parameter = Parameter("n", "a count", 1, 5, integer=True)
    assert parameter.validate(3) == 3
    with pytest.raises(ValueError, match="integer"):
        parameter.validate(3.0)


def test_model_text_is_never_evaluated(counting, tmp_path):
    """Code in a tool name, an argument, or the text is data."""
    allowlist, runs = counting
    marker = tmp_path / "marker"
    code = f"__import__('pathlib').Path({str(marker)!r}).write_text('x')"
    attempts = [
        call("double", {"x": code}),
        call(code, {"x": 1}),
        call("double", {"x": 1, code: 1}),
    ]
    for attempt in attempts:
        assert not allowlist.dispatch(attempt).ok
    assert not marker.exists()
    assert runs == []


def test_a_function_that_refuses_its_input_gives_an_error_result():
    def refuse(x):
        raise ValueError("no such thing")

    allowlist = Allowlist((Tool("t", "d", (Parameter("x", "x", 0, 1),), refuse),))
    result = allowlist.dispatch(call("t", {"x": 0.5}))
    assert (result.ok, dict(result.content)) == (False, {"error": "no such thing"})


def test_a_bug_in_a_tool_is_not_hidden():
    def bug(x):
        raise ZeroDivisionError

    allowlist = Allowlist((Tool("t", "d", (Parameter("x", "x", 0, 1),), bug),))
    with pytest.raises(ZeroDivisionError):
        allowlist.dispatch(call("t", {"x": 0.5}))


def test_duplicate_tool_names_are_refused():
    tool = Tool("t", "d", (), lambda: {})
    with pytest.raises(ValueError, match="duplicate"):
        Allowlist((tool, tool))


def test_specs_describe_the_bounds_to_the_model():
    (spec,) = (s for s in tools().specs() if s.name == "range_with_drag")
    dt = spec.parameters["properties"]["dt"]
    assert (dt["minimum"], dt["maximum"]) == (0.001, 0.05)
    assert spec.parameters["additionalProperties"] is False
    assert spec.parameters["required"] == ["speed", "angle", "dt"]


class Scripted:
    model = "scripted"
    secrets = ()

    def __init__(self, messages):
        self.messages = list(messages)
        self.seen = []

    def complete(self, system, conversation, tools):
        self.seen.append(list(conversation))
        return self.messages.pop(0)


def test_the_loop_stops_at_the_step_limit(counting):
    allowlist, _ = counting
    again = ModelMessage("again", (call("double", {"x": 1}),))
    transcript = run(Scripted([again] * 5), allowlist, "s", "t", max_steps=3)
    assert len(transcript.steps) == 3
    assert not transcript.finished


def test_the_loop_ends_when_the_model_requests_no_tool(counting):
    allowlist, _ = counting
    messages = [
        ModelMessage("go", (call("double", {"x": 1}),)),
        ModelMessage("done"),
    ]
    client = Scripted(messages)
    transcript = run(client, allowlist, "s", "t", max_steps=5)
    assert transcript.finished
    assert len(transcript.steps) == 2
    # The second request carries the task, the message, and its result.
    assert [type(turn).__name__ for turn in client.seen[1]] == [
        "UserTurn",
        "ModelMessage",
        "ToolResult",
    ]


def test_calls_beyond_the_limit_per_message_are_not_run(counting):
    allowlist, runs = counting
    many = ModelMessage(
        "many",
        tuple(
            call("double", {"x": 1}, id=f"c{i}")
            for i in range(MAX_CALLS_PER_MESSAGE + 2)
        ),
    )
    transcript = run(Scripted([many]), allowlist, "s", "t", max_steps=1)
    assert len(runs) == MAX_CALLS_PER_MESSAGE
    assert [r.ok for r in transcript.steps[0].results].count(False) == 2
