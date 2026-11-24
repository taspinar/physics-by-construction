"""The Claude client of the provider interface (#615), without a network,
without a key, and without the provider's SDK: a stand-in records what the
client hands the SDK and returns a response of the provider's shape."""

import base64
import json
import sys
import types

import pytest

from pbc.agents import ModelMessage, ToolCall, ToolResult
from pbc.agents.clients import anthropic as provider
from pbc.agents.loop import run
from pbc.agents.messages import Picture, UserTurn
from pbc.agents.projectile_lab import tools
from pbc.agents.providers import load_client
from pbc.agents.secrets import REDACTED, MissingKey

KEY = "sk-ant-test-0123456789abcdef"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


class FakeSDK:
    """The part of the SDK the client uses: ``Anthropic(...)`` and
    ``messages.create(...)``. Each ``create`` returns the next response."""

    def __init__(self, *responses, fail_with=None):
        self.responses = list(responses)
        self.fail_with = fail_with
        self.setup = None
        self.requests = []

    def Anthropic(self, **options):
        self.setup = options
        sdk = self

        def create(**request):
            sdk.requests.append(request)
            if sdk.fail_with is not None:
                raise sdk.fail_with
            data = sdk.responses.pop(0)
            return types.SimpleNamespace(model_dump=lambda: data)

        return types.SimpleNamespace(messages=types.SimpleNamespace(create=create))


def response(*blocks, stop="end_turn", usage=None, details=None):
    return {
        "content": list(blocks),
        "stop_reason": stop,
        "stop_details": details,
        "usage": usage
        if usage is not None
        else {"input_tokens": 10, "output_tokens": 5},
    }


def text(value):
    return {"type": "text", "text": value}


def tool_use(call_id, name, arguments):
    return {"type": "tool_use", "id": call_id, "name": name, "input": arguments}


@pytest.fixture
def sdk(monkeypatch):
    """The stand-in, installed as the module ``anthropic``, and the key in
    the client's own variable."""
    fake = FakeSDK()
    module = types.ModuleType("anthropic")
    module.Anthropic = fake.Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", module)
    monkeypatch.setenv(provider.KEY_VARIABLE, KEY)
    monkeypatch.delenv(provider.MODEL_VARIABLE, raising=False)
    return fake


# --- The request: the conversation in the provider's shape. ---


def test_build_request_follows_the_conversation():
    first = ToolCall("c1", "range_without_drag", {"speed": 10, "angle": 45})
    second = ToolCall("c2", "range_with_drag", {"speed": 10, "angle": 45})
    conversation = [
        UserTurn("task", (Picture("figure", PNG),)),
        ModelMessage("thinking aloud", (first, second)),
        ToolResult("c1", "range_without_drag", True, {"range_m": 10.19}),
        ToolResult("c2", "range_with_drag", False, {"error": "dt is missing"}),
        ModelMessage("done"),
    ]
    request = provider.build_request("m", "system", conversation, tools().specs())
    assert request["model"] == "m"
    assert request["system"] == "system"
    assert request["max_tokens"] == provider.MAX_TOKENS
    user, assistant, results, final = request["messages"]
    assert [m["role"] for m in request["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    # the picture, then the task
    image, task = user["content"]
    assert image["source"]["media_type"] == "image/png"
    assert base64.b64decode(image["source"]["data"]) == PNG
    assert task == {"type": "text", "text": "task"}
    # the text and both calls, with their arguments as objects
    assert assistant["content"][0] == {"type": "text", "text": "thinking aloud"}
    assert assistant["content"][1:] == [
        {
            "type": "tool_use",
            "id": "c1",
            "name": "range_without_drag",
            "input": {"speed": 10, "angle": 45},
        },
        {
            "type": "tool_use",
            "id": "c2",
            "name": "range_with_drag",
            "input": {"speed": 10, "angle": 45},
        },
    ]
    # both results in one user message; a refused call is an error result
    ok, refused = results["content"]
    assert ok["tool_use_id"] == "c1" and ok["is_error"] is False
    assert json.loads(ok["content"]) == {"range_m": 10.19}
    assert refused["tool_use_id"] == "c2" and refused["is_error"] is True
    assert json.loads(refused["content"]) == {"error": "dt is missing"}
    assert final["content"] == [{"type": "text", "text": "done"}]
    assert [t["name"] for t in request["tools"]] == [
        "range_with_drag",
        "range_without_drag",
    ]
    spec = next(s for s in tools().specs() if s.name == "range_with_drag")
    assert request["tools"][0]["input_schema"] == dict(spec.parameters)
    # The request carries no key; the SDK adds it.
    assert "key" not in json.dumps(request).lower()


def test_an_empty_assistant_turn_is_left_out_and_arguments_must_be_an_object():
    conversation = [
        UserTurn("task"),
        ModelMessage(""),
        UserTurn("again"),
        ModelMessage("", (ToolCall("c", "t", "{oops"),)),
    ]
    request = provider.build_request("m", "s", conversation, ())
    roles = [m["role"] for m in request["messages"]]
    assert roles == ["user", "user", "assistant"]
    assert request["messages"][2]["content"] == [
        {"type": "tool_use", "id": "c", "name": "t", "input": {}}
    ]


# --- The response: text, tool calls, refusal, usage. ---


def test_parse_response_reads_text_and_calls_and_drops_thinking():
    message = provider.parse_response(
        response(
            {"type": "thinking", "thinking": "", "signature": "s"},
            text("first"),
            tool_use("c9", "range_with_drag", {"speed": 25, "angle": 40, "dt": 0.01}),
            text("second"),
            stop="tool_use",
        )
    )
    assert message.text == "first\n\nsecond"
    assert message.tool_calls == (
        ToolCall("c9", "range_with_drag", {"speed": 25, "angle": 40, "dt": 0.01}),
    )


def test_a_refusal_ends_the_turn_without_calls_and_says_so():
    message = provider.parse_response(
        response(
            tool_use("c1", "range_with_drag", {}),
            stop="refusal",
            details={"type": "refusal", "category": "cyber", "explanation": None},
        )
    )
    assert message.tool_calls == ()
    assert message.text == "The provider declined to answer (cyber)."


def test_parse_usage_counts_cached_input_at_the_full_price():
    usage = {
        "input_tokens": 100,
        "output_tokens": 40,
        "cache_creation_input_tokens": 20,
        "cache_read_input_tokens": 5,
    }
    assert provider.parse_usage(response(usage=usage)) == {
        "input_tokens": 125,
        "output_tokens": 40,
    }
    nulls = {"input_tokens": 3, "output_tokens": 2, "cache_read_input_tokens": None}
    assert provider.parse_usage(response(usage=nulls)) == {
        "input_tokens": 3,
        "output_tokens": 2,
    }
    assert provider.parse_usage(response(usage={})) is None


# --- The client with the stand-in SDK. ---


def test_load_client_builds_the_client_with_the_key_and_the_default_model(sdk):
    client = load_client("anthropic")
    assert isinstance(client, provider.AnthropicClient)
    assert client.model == provider.MODEL
    assert [secret.name for secret in client.secrets] == [provider.KEY_VARIABLE]
    assert sdk.setup["api_key"] == KEY
    assert KEY not in repr(client)
    assert callable(client.complete)


def test_the_model_is_the_argument_else_the_variable(sdk, monkeypatch):
    monkeypatch.setenv(provider.MODEL_VARIABLE, "  claude-sonnet-5-5 ")
    assert provider.make_client().model == "claude-sonnet-5-5"
    assert provider.make_client("claude-haiku-5-5").model == "claude-haiku-5-5"


def test_complete_sends_the_request_and_counts_the_usage(sdk):
    sdk.responses.append(
        response(
            text("calling"),
            tool_use("c1", "range_without_drag", {"speed": 10, "angle": 45}),
            stop="tool_use",
            usage={"input_tokens": 321, "output_tokens": 54},
        )
    )
    client = provider.make_client()
    message = client.complete("system", [UserTurn("task")], tools().specs())
    assert message.tool_calls[0].name == "range_without_drag"
    assert client.last_usage == {"input_tokens": 321, "output_tokens": 54}
    assert sdk.requests[0]["model"] == provider.MODEL
    assert sdk.requests[0]["messages"][0]["content"] == [
        {"type": "text", "text": "task"}
    ]


def test_the_harness_removes_the_key_from_what_the_model_returns(sdk):
    sdk.responses += [
        response(
            text(f"the key is {KEY}"),
            tool_use("c1", "range_without_drag", {"speed": 10, "angle": 45}),
            stop="tool_use",
        ),
        response(text(f"again {KEY}")),
    ]
    transcript = run(provider.make_client(), tools(), "system", "task", 3)
    assert transcript.finished
    texts = [step.message.text for step in transcript.steps]
    assert texts == [f"the key is {REDACTED}", f"again {REDACTED}"]
    # the second request carried the redacted text, not the key
    assert KEY not in json.dumps(sdk.requests[1])


def test_an_sdk_error_is_raised_without_the_key_or_its_chain(sdk):
    sdk.fail_with = RuntimeError(f"401 for key {KEY}")
    client = provider.make_client()
    with pytest.raises(provider.ProviderError) as raised:
        client.complete("system", [UserTurn("task")], ())
    assert KEY not in str(raised.value)
    assert REDACTED in str(raised.value)
    assert raised.value.__cause__ is None and raised.value.__suppress_context__
    assert client.last_usage is None


# --- Missing pieces: a message that says what to do. ---


def test_a_missing_key_names_the_variable_and_the_group(sdk, monkeypatch):
    monkeypatch.delenv(provider.KEY_VARIABLE)
    with pytest.raises(MissingKey) as raised:
        load_client("anthropic")
    message = str(raised.value)
    assert provider.KEY_VARIABLE in message
    assert "uv sync --extra anthropic" in message
    assert sdk.setup is None


def test_a_missing_sdk_names_the_group_and_the_variable(sdk, monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)  # import fails
    with pytest.raises(provider.ProviderError) as raised:
        load_client("anthropic")
    message = str(raised.value)
    assert "uv sync --extra anthropic" in message
    assert provider.KEY_VARIABLE in message
    assert KEY not in message
