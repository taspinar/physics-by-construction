"""A key set in the environment appears nowhere it should not."""

import json
import logging
import sys
import traceback
import types

import pytest

from pbc.agents import ModelMessage, Secret, ToolCall, redact, run, save_recording
from pbc.agents.clients import openai as provider
from pbc.agents.projectile_lab import main, tools
from pbc.agents.providers import load_client
from pbc.agents.secrets import MissingKey, redact_data

KEY = "sk-test-0123456789abcdefSECRET"


class Boom(Exception):
    """An SDK error that, like some, echoes the request headers."""


class FakeSdk:
    """Stands in for the openai package; no network."""

    def __init__(self, behaviour, constructor_fails=False):
        self.behaviour = behaviour
        self.constructor_fails = constructor_fails

    def OpenAI(self, api_key, timeout, max_retries):
        if self.constructor_fails:
            raise Boom(f"invalid configuration: api_key={api_key!r}")
        sdk = self

        class Completions:
            def create(self, **request):
                return sdk.behaviour(api_key, request)

        class Chat:
            completions = Completions()

        class Client:
            chat = Chat()

        return Client()


def failing(api_key, request):
    raise Boom(f"401 for header Authorization: Bearer {api_key}")


class Response:
    def __init__(self, data):
        self.data = data

    def model_dump(self):
        return self.data


def echoing(api_key, request):
    """A model that repeats the key it should never have seen."""
    return Response(
        {
            "choices": [
                {"message": {"content": f"my key is {api_key}", "tool_calls": []}}
            ]
        }
    )


def echoing_in_calls(api_key, request):
    """A model that puts the key into every field of its tool calls."""
    return Response(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": f"call-{api_key}",
                                "function": {
                                    "name": f"range_without_drag_{api_key}",
                                    "arguments": json.dumps(
                                        {"speed": api_key, "angle": [api_key]}
                                    ),
                                },
                            },
                            {
                                "id": "c2",
                                "function": {
                                    "name": "range_without_drag",
                                    "arguments": json.dumps(
                                        {"speed": 25, "angle": 40, api_key: 1}
                                    ),
                                },
                            },
                        ],
                    }
                }
            ]
        }
    )


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setenv(provider.KEY_VARIABLE, KEY)
    return Secret.from_environment(provider.KEY_VARIABLE)


def test_a_secret_hides_itself(secret):
    for text in (str(secret), repr(secret), f"{secret}", f"{[secret]}"):
        assert KEY not in text
    with pytest.raises(TypeError):
        import pickle

        pickle.dumps(secret)


def test_a_missing_key_names_the_variable_and_nothing_else(monkeypatch):
    monkeypatch.delenv(provider.KEY_VARIABLE, raising=False)
    with pytest.raises(MissingKey, match=provider.KEY_VARIABLE):
        Secret.from_environment(provider.KEY_VARIABLE)


def test_redact_replaces_every_occurrence(secret):
    assert KEY not in redact(f"a {KEY} b {KEY}", secret)


def test_a_failing_request_leaks_the_key_nowhere(secret, caplog, capsys):
    client = provider.OpenAIClient(secret, FakeSdk(failing))
    with caplog.at_level(logging.DEBUG), pytest.raises(provider.ProviderError) as info:
        run(client, tools(), "s", "t", max_steps=1)
    error = info.value
    shown = "".join(traceback.format_exception(error))
    for text in (str(error), repr(error), shown, caplog.text, repr(client)):
        assert KEY not in text
    out = capsys.readouterr()
    assert KEY not in out.out + out.err
    assert "401" in str(error)  # the useful part of the message survives


def test_an_sdk_that_fails_to_set_up_leaks_the_key_nowhere(secret, caplog, capsys):
    with caplog.at_level(logging.DEBUG), pytest.raises(provider.ProviderError) as info:
        provider.OpenAIClient(secret, FakeSdk(echoing, constructor_fails=True))
    error = info.value
    shown = "".join(traceback.format_exception(error))
    for text in (str(error), repr(error), shown, caplog.text):
        assert KEY not in text
    out = capsys.readouterr()
    assert KEY not in out.out + out.err
    assert "invalid configuration" in str(error)


def test_a_key_repeated_by_the_model_reaches_no_transcript(secret):
    """The returned transcript, not only a saved one, holds no key (ADR 004)."""
    seen = []
    client = provider.OpenAIClient(secret, FakeSdk(echoing))
    transcript = run(client, tools(), "s", "t", max_steps=1, on_step=seen.append)
    assert transcript.steps[0].message.text == "my key is [redacted]"
    for text in (repr(transcript), str(transcript), repr(seen)):
        assert KEY not in text


def test_a_key_repeated_in_tool_calls_reaches_no_transcript_or_request(secret):
    requests = []

    def behaviour(api_key, request):
        requests.append(request)
        return echoing_in_calls(api_key, request)

    client = provider.OpenAIClient(secret, FakeSdk(behaviour))
    transcript = run(client, tools(), "s", "t", max_steps=2)
    step = transcript.steps[0]
    assert step.message.tool_calls[0].id == "call-[redacted]"
    assert step.message.tool_calls[0].name == "range_without_drag_[redacted]"
    assert step.message.tool_calls[0].arguments == {
        "speed": "[redacted]",
        "angle": ["[redacted]"],
    }
    assert "[redacted]" in step.message.tool_calls[1].arguments
    assert not any(result.ok for result in step.results)
    # Neither the transcript nor the next request to the provider has it.
    assert KEY not in repr(transcript)
    assert KEY not in json.dumps(requests[1])


def test_a_key_repeated_by_the_model_is_not_written_to_a_recording(
    secret, tmp_path, capsys
):
    client = provider.OpenAIClient(secret, FakeSdk(echoing))
    transcript = run(client, tools(), "s", "t", max_steps=1)
    path = tmp_path / "replay.json"
    save_recording(path, transcript, "2026-01-01", secret)
    assert KEY not in path.read_text()
    assert json.loads(path.read_text())["steps"][0]["text"] == "my key is [redacted]"


def test_redact_data_reaches_every_text_in_nested_data(secret):
    data = {KEY: [KEY, 1, {"k": f"x{KEY}y"}], "n": 2.5, "b": True, "none": None}
    assert redact_data(data, secret) == {
        "[redacted]": ["[redacted]", 1, {"k": "x[redacted]y"}],
        "n": 2.5,
        "b": True,
        "none": None,
    }


def test_the_command_line_entry_point_prints_no_key(secret, monkeypatch, capsys):
    monkeypatch.setattr(
        "pbc.agents.clients.openai.make_client",
        lambda: provider.OpenAIClient(secret, FakeSdk(echoing)),
    )
    assert main([]) == 0
    out = capsys.readouterr()
    assert KEY not in out.out + out.err


def test_the_command_line_prints_no_key_when_the_sdk_fails_to_set_up(
    secret, monkeypatch, capsys
):
    monkeypatch.setattr(
        "pbc.agents.clients.openai.make_client",
        lambda: provider.OpenAIClient(secret, FakeSdk(echoing, constructor_fails=True)),
    )
    assert main([]) == 1
    out = capsys.readouterr()
    assert KEY not in out.out + out.err
    assert "could not be set up" in out.err


def test_the_command_line_without_a_key_fails_cleanly(monkeypatch, capsys):
    monkeypatch.delenv(provider.KEY_VARIABLE, raising=False)
    assert main([]) == 1
    assert provider.KEY_VARIABLE in capsys.readouterr().err


OTHER_VARIABLE = "OTHER_PROVIDER_API_KEY"
OTHER_KEY = "other-9876543210zyxwvuSECRET"


class OtherClient:
    """A client of another provider: it echoes its own key, as a model might."""

    model = "other-model"

    def __init__(self, secret):
        self.secrets = (secret,)
        self._secret = secret

    def complete(self, system, conversation, tools):
        if len(conversation) > 1:
            return ModelMessage("done")
        return ModelMessage(
            f"my key is {self._secret.reveal()}",
            (ToolCall("c1", "range_without_drag", {"speed": 25, "angle": 40}),),
        )


@pytest.fixture
def other_provider(monkeypatch):
    """Provider ``other`` installed, selected, and the only key set is its own."""
    module = types.ModuleType("pbc.agents.clients.other")
    module.make_client = lambda: OtherClient(Secret.from_environment(OTHER_VARIABLE))
    monkeypatch.setitem(sys.modules, "pbc.agents.clients.other", module)
    monkeypatch.setattr("pbc.agents.providers.PROVIDER", "other")
    monkeypatch.delenv(provider.KEY_VARIABLE, raising=False)
    monkeypatch.setenv(OTHER_VARIABLE, OTHER_KEY)


def test_switching_provider_needs_only_that_providers_key(
    other_provider, tmp_path, monkeypatch, capsys
):
    """One client module and one configuration value; no OpenAI key is read,
    and it is the selected provider's key that is redacted."""
    fixture = tmp_path / "replay.json"
    monkeypatch.setattr("pbc.agents.projectile_lab.FIXTURE", str(fixture))
    assert main(["--record"]) == 0
    out = capsys.readouterr()
    assert "Model: other-model" in out.out
    assert "my key is [redacted]" in out.out
    assert OTHER_KEY not in out.out + out.err
    assert OTHER_KEY not in fixture.read_text()
    assert json.loads(fixture.read_text())["model"] == "other-model"


def test_switching_provider_without_its_key_names_its_own_variable(
    other_provider, monkeypatch, capsys
):
    monkeypatch.delenv(OTHER_VARIABLE)
    assert main([]) == 1
    err = capsys.readouterr().err
    assert OTHER_VARIABLE in err
    assert provider.KEY_VARIABLE not in err


def test_load_client_accepts_only_a_plain_provider_name():
    for name in ("../x", "a.b", "OpenAI", "os; rm", ""):
        with pytest.raises(ValueError, match="not a provider name"):
            load_client(name)
