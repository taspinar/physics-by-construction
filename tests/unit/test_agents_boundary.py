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
# The provider SDK is imported in exactly one module.
SDK = "openai"
SDK_MODULE = AGENTS / "clients" / "openai.py"
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
        if root == SDK:
            assert source == SDK_MODULE, f"{source.name} imports the provider SDK"
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
