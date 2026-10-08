"""The request the live client builds and the response it reads, without a
network."""

import json

from pbc.agents import ModelMessage, ToolCall, ToolResult
from pbc.agents.clients import openai as provider
from pbc.agents.messages import UserTurn
from pbc.agents.projectile_lab import tools


def test_build_request_follows_the_conversation():
    call = ToolCall("c1", "range_without_drag", {"speed": 10, "angle": 45})
    conversation = [
        UserTurn("task"),
        ModelMessage("thinking", (call,)),
        ToolResult("c1", "range_without_drag", True, {"range_m": 10.19}),
    ]
    request = provider.build_request("m", "system", conversation, tools().specs())
    roles = [m["role"] for m in request["messages"]]
    assert roles == ["system", "user", "assistant", "tool"]
    assistant, tool = request["messages"][2:]
    function = assistant["tool_calls"][0]["function"]
    assert json.loads(function["arguments"]) == {"speed": 10, "angle": 45}
    assert tool["tool_call_id"] == "c1"
    assert json.loads(tool["content"]) == {"range_m": 10.19}
    assert request["model"] == "m"
    assert [t["function"]["name"] for t in request["tools"]] == [
        "range_with_drag",
        "range_without_drag",
    ]
    # The request carries no key; the SDK adds it.
    assert "key" not in json.dumps(request).lower().replace("keyword", "")


def test_parse_response_reads_text_and_calls():
    response = {
        "choices": [
            {
                "message": {
                    "content": "hello",
                    "tool_calls": [
                        {
                            "id": "c9",
                            "function": {
                                "name": "range_with_drag",
                                "arguments": '{"speed": 25, "angle": 40, "dt": 0.01}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    message = provider.parse_response(response)
    assert message.text == "hello"
    assert message.tool_calls == (
        ToolCall("c9", "range_with_drag", {"speed": 25, "angle": 40, "dt": 0.01}),
    )


def test_parse_response_keeps_invalid_arguments_for_the_allowlist_to_reject():
    response = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {"id": "c", "function": {"name": "t", "arguments": "{oops"}}
                    ],
                }
            }
        ]
    }
    message = provider.parse_response(response)
    assert message.text == ""
    assert message.tool_calls[0].arguments == "{oops"
    assert not tools().dispatch(message.tool_calls[0]).ok
