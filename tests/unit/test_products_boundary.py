"""The boundary of the Part B products (invariants I33 and I34, extending the
boundary test of I32 and I24, ``test_skills_boundary.py``): no build step,
check, or CI job installs an optional dependency group, imports a driver,
starts a product, or contacts a model, an instrument, or the network.

- The CI workflow, its runner preparation, the scripts, and the checks of
  ``scripts/verify.conf`` install no optional group (no ``--extra``, no
  ``--all-extras``, no ``pip install``), and the default environment holds
  none of the optional groups' packages.
- No check, script, workflow, or page starts a product: none names
  ``pbc.products.physics_lab``, and no page imports ``pbc.products`` (the
  capstone page of F145, which executes the deterministic simulator route,
  is the first that may, and changes this test with it).
- The one check that touches the products, ``starters``, runs the starter
  checks, which read the repository's own history and start no product.
- ``pbc.instruments`` and the product package import no network client, no
  process launcher, no provider SDK, and no device driver; the standard
  library's HTTP server only in the local interface, which binds to the
  loopback interface; a provider client only lazily, in the command line,
  for a learner's own live recording.
"""

import ast
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from support import verify_conf

ROOT = Path(__file__).parents[2]
PACKAGES = (ROOT / "src/pbc/instruments", ROOT / "src/pbc/products/physics_lab")
SOURCES = sorted(p for d in PACKAGES for p in d.rglob("*.py"))
STARTER = ROOT / "products/physics-lab/starter"

# What the build, the checks, and CI are made of.
MACHINERY_GLOBS = (
    ".github/**/*.yml",
    "scripts/*.sh",
    "scripts/lib/*.sh",
    "scripts/*.conf",
)
INSTALLS = re.compile(r"--extra\b|--all-extras|\bpip3? install\b|uv pip\b")
STARTS = re.compile(r"pbc\.products\.physics_lab|pbc/products/physics_lab")

# Device drivers and measurement frameworks the products may use only behind
# an optional group (F140), and the network and process modules.
DRIVERS = {
    "pyvisa", "serial", "usb", "pydwf", "dwf", "redpitaya", "rp", "bluesky",
    "ophyd", "qcodes", "nidaqmx", "pymeasure",
}  # fmt: skip
FORBIDDEN = DRIVERS | {
    "socket", "ssl", "urllib.request", "http.client", "requests", "httpx",
    "aiohttp", "subprocess", "multiprocessing", "ctypes", "pickle", "openai",
    "anthropic", "webbrowser", "pbc.agents.clients",
}  # fmt: skip
# The local interface is the one module with a server, bound to loopback.
SERVER = {"http.server": {"interface.py"}}
# A live provider is loaded only lazily, inside the command line's function.
LAZY = {"pbc.agents.providers": {"__main__.py"}}


def machinery() -> list[Path]:
    return sorted({p for g in MACHINERY_GLOBS for p in ROOT.glob(g) if p.is_file()})


def module_level_imports(tree: ast.Module):
    for node in tree.body:
        yield from _names(node)


def all_imports(tree: ast.Module):
    for node in ast.walk(tree):
        yield from _names(node)


def _names(node):
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield alias.name
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        yield node.module


def forbidden(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN)


def test_the_scan_sees_the_machinery_and_the_sources():
    names = {p.relative_to(ROOT).as_posix() for p in machinery()}
    assert {".github/workflows/ci.yml", "scripts/verify.conf"} <= names
    assert ".github/actions/prepare/action.yml" in names
    assert {p.name for p in SOURCES} >= {"contract.py", "interface.py", "agent.py"}


def test_no_build_step_check_or_ci_job_installs_an_optional_group():
    found = {
        p.relative_to(ROOT).as_posix(): m.group(0)
        for p in machinery()
        if (m := INSTALLS.search(p.read_text(errors="replace")))
    }
    assert found == {}


def test_the_default_environment_holds_no_optional_group():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    optional = project["project"]["optional-dependencies"]
    assert "physics-lab" in optional
    default = project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    names = {re.split(r"[<>=\[ ;]", d, maxsplit=1)[0] for d in default}
    for group, requirements in optional.items():
        for requirement in requirements:
            name = re.split(r"[<>=\[ ;]", requirement, maxsplit=1)[0]
            assert name not in names, (group, name)


def test_no_check_script_workflow_or_page_starts_a_product():
    pages = [p for p in (ROOT / "site").rglob("*") if p.suffix in {".qmd", ".py"}]
    found = [
        p.relative_to(ROOT).as_posix()
        for p in [*machinery(), *pages]
        if STARTS.search(p.read_text(errors="replace"))
    ]
    assert found == []
    importing = [
        p.relative_to(ROOT).as_posix()
        for p in pages
        if re.search(r"\bpbc\.products\b|\bpbc\.instruments\b", p.read_text())
    ]
    assert importing == []


def test_the_one_product_check_is_the_starter_check():
    commands = verify_conf.checks()
    touching = [
        name
        for name, command in commands.items()
        if "pbc.products" in command or "products/" in command
    ]
    assert touching == ["starters"]
    assert commands["starters"] == "uv run --locked python -m pbc.products.starters"


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_the_instrument_and_product_code_imports_no_driver_network_or_model(path):
    tree = ast.parse(path.read_text())
    imports = set(all_imports(tree))
    assert {i for i in imports if forbidden(i)} == set()
    for module, allowed in {**SERVER, **LAZY}.items():
        if module in imports:
            assert path.name in allowed, (path.name, module)
    for module in LAZY:
        assert module not in set(module_level_imports(tree)), path.name


def test_the_starter_imports_no_driver_network_or_model():
    for path in sorted(STARTER.rglob("*.py")):
        tree = ast.parse(path.read_text())
        assert {i for i in module_level_imports(tree) if forbidden(i)} == set()
        assert "pbc.agents.providers" not in set(module_level_imports(tree))


def test_importing_the_product_loads_no_provider_driver_or_server():
    probe = (
        "import sys\n"
        "import pbc.instruments, pbc.instruments.simulated, pbc.instruments.recorded\n"
        "import pbc.products.physics_lab.workflow, pbc.products.physics_lab.__main__\n"
        "print('\\n'.join(sorted(sys.modules)))\n"
    )
    loaded = set(
        subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, check=True
        ).stdout.split()
    )
    bad = {m for m in loaded if m.split(".")[0] in DRIVERS | {"openai", "anthropic"}}
    assert bad == set()
    assert "http.server" not in loaded
    assert "pbc.agents.clients" not in loaded
    assert not any(m.startswith("pbc.agents.clients.") for m in loaded)
