"""The harness has no code path that evaluates model output as code, runs a
shell command, or opens a network connection other than the live client's
request (ADR 004). A review reads the code; these tests keep it that way."""

import ast
from pathlib import Path

import pytest

AGENTS = Path(__file__).parents[2] / "src" / "pbc" / "agents"
SOURCES = sorted(AGENTS.rglob("*.py"))

# Modules that run programs, open connections, or load code from data.
FORBIDDEN_IMPORTS = {
    "subprocess", "os", "socket", "ssl", "http", "urllib", "requests", "httpx",
    "aiohttp", "ftplib", "smtplib", "telnetlib", "xmlrpc", "ctypes", "pickle",
    "shelve", "marshal", "multiprocessing", "shutil", "webbrowser", "code",
    "codeop", "runpy", "pty",
}  # fmt: skip
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open", "input"}
# A provider SDK is imported only in the modules of pbc.agents.clients, one
# SDK per module: the client of its provider (#615). The local client speaks
# the OpenAI-compatible API through the openai SDK.
CLIENTS = AGENTS / "clients"
CLIENT_SDKS = {
    CLIENTS / "openai.py": "openai",
    CLIENTS / "anthropic.py": "anthropic",
    CLIENTS / "local.py": "openai",
}
SDKS = set(CLIENT_SDKS.values())
# The environment variables each client module reads, all of its own
# provider, through ``pbc.agents.secrets`` (a key with
# ``Secret.from_environment``, a setting with ``read_setting``). No other
# module reads one.
CLIENT_VARIABLES = {
    CLIENTS / "openai.py": {"OPENAI_API_KEY"},
    CLIENTS / "anthropic.py": {"ANTHROPIC_API_KEY", "PBC_ANTHROPIC_MODEL"},
    CLIENTS / "local.py": {"PBC_LOCAL_BASE_URL", "PBC_LOCAL_MODEL"},
}
READERS = {"from_environment", "read_setting"}
# importlib selects the provider module from a configuration string; model
# output never reaches it.
IMPORTLIB_MODULE = AGENTS / "providers.py"
# The key is read from the environment in exactly one module, through
# ``os.environ`` and nothing else of ``os``.
ENVIRONMENT_MODULE = AGENTS / "secrets.py"
# Files are read and written only to load and save a replay fixture.
FILE_METHODS = {"read_text", "write_text", "read_bytes", "write_bytes", "open"}
FILE_MODULES = {AGENTS / "replay.py"}


def imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module


def test_the_agent_package_exists_and_is_scanned():
    assert len(SOURCES) >= 8


@pytest.mark.parametrize(
    "source", SOURCES, ids=lambda p: p.relative_to(AGENTS).as_posix()
)
def test_no_dangerous_import_or_call(source):
    tree = ast.parse(source.read_text())
    for module in imports(tree):
        root = module.split(".")[0]
        if root == "os" and source == ENVIRONMENT_MODULE:
            continue
        assert root not in FORBIDDEN_IMPORTS, f"{source.name} imports {module}"
        if root in SDKS:
            assert CLIENT_SDKS.get(source) == root, (
                f"{source.name} imports the provider SDK {root}"
            )
        if root == "importlib":
            assert source == IMPORTLIB_MODULE
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                assert function.id not in FORBIDDEN_CALLS, (
                    f"{source.name}:{node.lineno} calls {function.id}"
                )
            if isinstance(function, ast.Attribute) and function.attr in FILE_METHODS:
                assert source in FILE_MODULES, (
                    f"{source.name}:{node.lineno} reads or writes a file"
                )


def test_the_only_dynamic_attribute_access_is_not_on_model_data():
    """``getattr`` and ``setattr`` could turn a model-chosen name into a call."""
    for source in SOURCES:
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"getattr", "setattr", "globals", "vars"}, (
                    f"{source.name}:{node.lineno} calls {node.func.id}"
                )


def test_the_environment_module_uses_only_os_environ():
    tree = ast.parse(ENVIRONMENT_MODULE.read_text())
    used = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    }
    assert used == {"environ"}


def variables_read(tree: ast.Module) -> list[str | None]:
    """The names of the environment variables ``tree`` hands to a reader of
    ``pbc.agents.secrets``, each as its text or through a module-level name
    bound to it; None for an argument that is neither."""
    bound = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = (
            function.attr
            if isinstance(function, ast.Attribute)
            else (function.id if isinstance(function, ast.Name) else None)
        )
        if name not in READERS:
            continue
        for value in [*node.args, *(keyword.value for keyword in node.keywords)]:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                found.append(value.value)
            elif isinstance(value, ast.Name):
                found.append(bound.get(value.id))
            else:
                found.append(None)
    return found


def test_the_clients_are_the_modules_of_their_package():
    assert sorted(CLIENT_SDKS) == sorted(
        p for p in CLIENTS.glob("*.py") if p.name != "__init__.py"
    )
    assert set(CLIENT_VARIABLES) == set(CLIENT_SDKS)


@pytest.mark.parametrize(
    "source", SOURCES, ids=lambda p: p.relative_to(AGENTS).as_posix()
)
def test_only_a_client_reads_the_environment_and_only_its_own_variables(source):
    read = variables_read(ast.parse(source.read_text()))
    if source in CLIENT_VARIABLES:
        assert read, f"{source.name} reads no variable of its provider"
        assert set(read) <= CLIENT_VARIABLES[source], (source.name, read)
    else:
        assert read == [], f"{source.name} reads the environment: {read}"


def test_the_scan_of_environment_reads_sees_a_planted_read():
    planted = ast.parse(
        'KEY = "OPENAI_API_KEY"\n'
        "a = Secret.from_environment(KEY)\n"
        'b = read_setting("PBC_LOCAL_MODEL")\n'
        "c = read_setting(name=other)\n"
    )
    assert variables_read(planted) == ["OPENAI_API_KEY", "PBC_LOCAL_MODEL", None]
