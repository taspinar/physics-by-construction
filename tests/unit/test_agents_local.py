"""The client of a local open-weights model (#615), without a network,
without a server, and without the SDK: a stand-in records what the client
hands the SDK and returns a chat completion of the provider's shape."""

import sys
import types

import pytest

from pbc.agents.clients import local
from pbc.agents.messages import UserTurn
from pbc.agents.projectile_lab import tools
from pbc.agents.providers import load_client


class FakeSDK:
    """The part of the openai SDK the client uses: ``OpenAI(...)``,
    ``DefaultHttpxClient(...)``, and ``chat.completions.create(...)``."""

    def __init__(self):
        self.setup = None
        self.http_options = None
        self.responses = []
        self.requests = []

    def DefaultHttpxClient(self, **options):
        self.http_options = options
        return "http-client"

    def OpenAI(self, **options):
        self.setup = options
        sdk = self

        def create(**request):
            sdk.requests.append(request)
            data = sdk.responses.pop(0)
            return types.SimpleNamespace(model_dump=lambda: data)

        completions = types.SimpleNamespace(create=create)
        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=completions)
        )


@pytest.fixture
def sdk(monkeypatch):
    fake = FakeSDK()
    module = types.ModuleType("openai")
    module.OpenAI = fake.OpenAI
    module.DefaultHttpxClient = fake.DefaultHttpxClient
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.delenv(local.BASE_URL_VARIABLE, raising=False)
    monkeypatch.setenv(local.MODEL_VARIABLE, "qwen3:8b")
    return fake


# --- The address rule. ---


@pytest.mark.parametrize(
    "address",
    [
        "http://localhost:11434/v1",
        "http://LOCALHOST:1234/v1",
        "http://127.0.0.1:8080/v1",
        "http://127.10.20.30/v1",
        "https://[::1]:8443/v1",
        "http://localhost",
    ],
)
def test_a_loopback_address_is_accepted(address):
    assert local.loopback_base_url(address) == address


@pytest.mark.parametrize(
    "address",
    [
        "http://192.168.1.20:11434/v1",
        "http://0.0.0.0:11434/v1",
        "http://example.com/v1",
        "https://api.openai.com/v1",
        "http://[2001:db8::1]/v1",
        "http://localhost.example.com/v1",
        # a user part, a query, or a fragment could hide the real host
        "http://localhost@example.com/v1",
        "http://127.0.0.1:80@example.com/v1",
        "http://localhost:11434/v1?next=http://example.com",
        "http://localhost:11434/v1#x",
        "ftp://localhost/v1",
        "localhost:11434",
        "",
    ],
)
def test_any_other_address_is_refused(address):
    with pytest.raises(local.ProviderError):
        local.loopback_base_url(address)


# --- The client with the stand-in SDK. ---


def test_load_client_builds_the_client_for_the_local_server(sdk):
    client = load_client("local")
    assert isinstance(client, local.LocalClient)
    assert client.model == "qwen3:8b"
    assert client.base_url == local.DEFAULT_BASE_URL
    assert client.secrets == ()
    assert client.prices_eur_per_mtok == (0.0, 0.0)
    assert sdk.setup["base_url"] == local.DEFAULT_BASE_URL
    # a placeholder key, never a provider's; no proxy of the environment
    assert sdk.setup["api_key"] == local.PLACEHOLDER_KEY
    assert sdk.setup["http_client"] == "http-client"
    assert sdk.http_options == {"trust_env": False, "follow_redirects": False}
    assert callable(client.complete)


def test_the_address_and_the_model_come_from_the_variables_or_the_arguments(
    sdk, monkeypatch
):
    monkeypatch.setenv(local.BASE_URL_VARIABLE, "http://127.0.0.1:1234/v1")
    client = local.make_client()
    assert client.base_url == "http://127.0.0.1:1234/v1"
    client = local.make_client("llama3.2", "http://[::1]:8080/v1")
    assert (client.model, client.base_url) == ("llama3.2", "http://[::1]:8080/v1")


def test_complete_sends_the_chat_request_and_counts_the_usage(sdk):
    sdk.responses.append(
        {
            "choices": [
                {
                    "message": {
                        "content": "measuring",
                        "tool_calls": [
                            {
                                "id": "c1",
                                "function": {
                                    "name": "range_without_drag",
                                    "arguments": '{"speed": 10, "angle": 45}',
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 812, "completion_tokens": 33},
        }
    )
    sdk.responses.append({"choices": [{"message": {"content": "done"}}]})
    client = local.make_client()
    message = client.complete("system", [UserTurn("task")], tools().specs())
    assert message.text == "measuring"
    assert message.tool_calls[0].arguments == {"speed": 10, "angle": 45}
    assert client.last_usage == {"input_tokens": 812, "output_tokens": 33}
    assert sdk.requests[0]["model"] == "qwen3:8b"
    assert [m["role"] for m in sdk.requests[0]["messages"]] == ["system", "user"]
    # a server that reports no usage: nothing is counted
    assert client.complete("system", [UserTurn("task")], ()).text == "done"
    assert client.last_usage is None


# --- Missing pieces and a refused address. ---


def test_no_model_configured_is_refused_with_the_variable(sdk, monkeypatch):
    monkeypatch.delenv(local.MODEL_VARIABLE)
    with pytest.raises(local.ProviderError, match=local.MODEL_VARIABLE):
        load_client("local")
    assert sdk.setup is None


def test_a_remote_address_is_refused_before_the_sdk_is_set_up(sdk, monkeypatch):
    monkeypatch.setenv(local.BASE_URL_VARIABLE, "https://api.example.com/v1")
    with pytest.raises(local.ProviderError, match="not a loopback address"):
        load_client("local")
    assert sdk.setup is None
    with pytest.raises(local.ProviderError, match="not a loopback address"):
        local.LocalClient("m", "http://10.0.0.2/v1", sdk)


def test_a_missing_sdk_names_the_group(sdk, monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(local.ProviderError, match="uv sync --extra openai"):
        load_client("local")
