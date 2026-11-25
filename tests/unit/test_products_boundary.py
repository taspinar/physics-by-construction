"""The boundary of the Part B products (invariants I33 and I34, extending the
boundary test of I32 and I24, ``test_skills_boundary.py``): no build step,
check, or CI job installs an optional dependency group, imports a driver,
starts a product, or contacts a model, an instrument, or the network.

- The CI workflow, its runner preparation, the scripts, and the checks of
  ``scripts/verify.conf`` install no optional group (no ``--extra``, no
  ``--all-extras``, no ``pip install``), and the default environment holds
  none of the optional groups' packages.
- No check, script, or workflow starts a product: none names
  ``pbc.products.physics_lab``. No page imports ``pbc.products`` but the
  capstone page of F145 (SA9), which executes the deterministic simulator
  route and the recorded replay: it, its experiment, and the module that
  shows the pilot's record name only the product modules of
  ``CAPSTONE_PRODUCT_MODULES`` (the protocols, the campaign, the export,
  the evaluator, the agent's tools replayed from a fixture), never the
  command line, the interface, a provider client, or the live mode.
- A page may run the instrument contract on its simulated and recorded
  adapters (the lessons of slots SA3 and SA4, F142, and the campaign of
  SA6, F143): it names only the contract and those adapters, the contract
  tests, and the channel adapter, never the live mode, and the experiment it
  runs is held to the import rule of ``pbc.instruments`` itself. (Before
  F142 no page could name ``pbc.instruments`` at all.)
- The one check that touches the products, ``starters``, runs the starter
  checks, which read the repository's own history and start no product.
- ``pbc.instruments`` and the product package import no network client, no
  process launcher, no provider SDK, and no device driver; the standard
  library's HTTP server only in the local interface, which binds to the
  loopback interface; a provider client only lazily, in the command line,
  for a learner's own live recording. The one exception for a device is
  F140's live adapter, ``pbc.instruments.analog_discovery``: the only
  module that may import ``ctypes`` (to load the vendor's SDK library, which
  the learner installs) and ``subprocess`` (to start its own watchdog, the
  same module run as a separate process, which switches the generator off
  when the program that holds the device dies), and imported only lazily,
  by the command line, for a learner's own live run.
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
# The live adapter of F140 loads the vendor's SDK library by ctypes
# and starts its watchdog, itself run as a separate process (python -m).
DEVICE = {"ctypes": {"analog_discovery.py"}, "subprocess": {"analog_discovery.py"}}
# A live provider and the live adapter are loaded only lazily, inside the
# command line's function.
LAZY = {
    "pbc.agents.providers": {"__main__.py"},
    "pbc.instruments.analog_discovery": {"__main__.py"},
}


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


# The capstone page of F145 (SA9), its experiment, and its library module:
# the one page that runs the product, on the simulator and the recorded
# adapter only.
CAPSTONE_PAGE = "site/lessons/agents-llm/25-autonomous-physics-lab/index.qmd"
CAPSTONE_EXPERIMENT = "src/pbc/electromagnetism/experiments/autonomous_physics_lab.py"
CAPSTONE_LIBRARY = "src/pbc/electromagnetism/pilot_record.py"
CAPSTONE_FILES = {CAPSTONE_PAGE, CAPSTONE_EXPERIMENT, CAPSTONE_LIBRARY}
# The product modules they may name: never __main__ (the command line, with
# the live mode and the recording), interface or campaign_interface (the
# local server), or agent (the slice's agent with its live recording).
CAPSTONE_PRODUCT_MODULES = {
    f"pbc.products.physics_lab.{name}"
    for name in (
        "agent_campaign", "bench", "campaign", "estimates", "lab", "nonlinear",
        "protocol", "quality", "resonance", "ringdown", "transient", "workflow",
    )
}  # fmt: skip


def product_modules(source: str) -> set[str]:
    """The modules of ``pbc.products`` that ``source`` imports
    (``from pbc.products.physics_lab import lab`` imports
    ``pbc.products.physics_lab.lab``) or names in its text by a dotted name
    below the package. A Quarto page is read by its Python cells."""
    cells = re.findall(r"```\{python\}\n(.*?)```", source, re.DOTALL)
    trees = [ast.parse(cell) for cell in cells] if cells else [ast.parse(source)]
    named = set(re.findall(r"\bpbc\.products\.physics_lab\.\w+", source))
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                named |= {
                    a.name for a in node.names if a.name.startswith("pbc.products")
                }
            elif (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and (node.module or "").startswith("pbc.products")
            ):
                named |= {f"{node.module}.{a.name}" for a in node.names}
    # A name imported from a module (a class or a constant of it) stands for
    # that module.
    modules = set()
    for name in named:
        parts = name.split(".")
        module = ".".join(parts[:4])
        modules.add(module if len(parts) >= 4 else name)
    return modules


def test_no_check_script_workflow_or_page_starts_a_product():
    pages = [p for p in (ROOT / "site").rglob("*") if p.suffix in {".qmd", ".py"}]
    found = [
        p.relative_to(ROOT).as_posix()
        for p in machinery()
        if STARTS.search(p.read_text(errors="replace"))
    ]
    assert found == []
    importing = [
        p.relative_to(ROOT).as_posix()
        for p in pages
        if re.search(r"\bpbc\.products\b", p.read_text())
    ]
    assert importing == [CAPSTONE_PAGE]


@pytest.mark.parametrize("name", sorted(CAPSTONE_FILES))
def test_the_capstone_names_only_the_simulator_route_of_the_product(name):
    source = (ROOT / name).read_text()
    assert product_modules(source) <= CAPSTONE_PRODUCT_MODULES, name
    assert not re.search(r"\bLIVE\b", source), name


# What the capstone's product modules may never reach, at any depth.
CAPSTONE_UNREACHABLE = {
    "pbc.products.physics_lab.__main__",
    "pbc.products.physics_lab.interface",
    "pbc.products.physics_lab.campaign_interface",
    "pbc.agents.providers",
    "pbc.agents.clients",
    "pbc.instruments.analog_discovery",
}


def test_the_capstone_modules_reach_no_command_line_server_or_provider():
    """Following the top-level imports of the product modules the capstone
    names, through the product package, reaches no command line, no local
    server, no provider client, and no live adapter: what the page runs is
    the simulated and recorded route."""
    seen, todo = set(), sorted(CAPSTONE_PRODUCT_MODULES)
    while todo:
        module = todo.pop()
        if module in seen:
            continue
        seen.add(module)
        path = ROOT / "src" / f"{module.replace('.', '/')}.py"
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "pbc.products.physics_lab"
            ):
                names = [f"{node.module}.{a.name}" for a in node.names]
            else:
                names = list(_names(node))
            for name in names:
                assert not any(
                    name == u or name.startswith(u + ".") for u in CAPSTONE_UNREACHABLE
                ), (module, name)
                assert not forbidden(name), (module, name)
                if name.startswith("pbc.products.physics_lab."):
                    todo.append(".".join(name.split(".")[:4]))
    assert seen >= CAPSTONE_PRODUCT_MODULES


def test_the_capstone_product_names_are_read():
    planted = "from pbc.products.physics_lab import (\n    lab,\n    interface,\n)\n"
    assert product_modules(planted) == {
        "pbc.products.physics_lab.lab",
        "pbc.products.physics_lab.interface",
    }
    assert not product_modules(planted) <= CAPSTONE_PRODUCT_MODULES


# A page may run the instrument contract on its simulated and recorded
# adapters (F142, the lessons of slots SA3 and SA4): these modules and no
# other part of pbc.instruments, and never the live mode, whose adapter is
# F140's and optional.
PAGE_INSTRUMENT_MODULES = {
    "pbc.instruments",
    "pbc.instruments.contract",
    "pbc.instruments.simulated",
    "pbc.instruments.recorded",
    "pbc.instruments.conformance",
    "pbc.instruments.channels",
}
INSTRUMENT_PAGES = {
    "site/lessons/electromagnetism/10-simulators-and-instruments/index.qmd",
    "site/lessons/electromagnetism/11-measurement-quality/index.qmd",
    CAPSTONE_PAGE,
}
EXPERIMENTS = sorted((ROOT / "src/pbc").glob("*/experiments/*.py"))


def test_a_page_runs_only_the_simulated_and_recorded_instrument_contract():
    pages = [p for p in (ROOT / "site").rglob("*") if p.suffix in {".qmd", ".py"}]
    named = {
        p.relative_to(ROOT).as_posix(): set(
            re.findall(r"\bpbc\.instruments(?:\.\w+)*", p.read_text())
        )
        for p in pages
    }
    named = {page: modules for page, modules in named.items() if modules}
    assert set(named) == INSTRUMENT_PAGES
    for page, modules in named.items():
        assert modules <= PAGE_INSTRUMENT_MODULES, (page, modules)
        assert not re.search(r"\bLIVE\b", (ROOT / page).read_text()), page


@pytest.mark.parametrize(
    "path",
    [p for p in EXPERIMENTS if "pbc.instruments" in p.read_text()],
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_an_experiment_on_the_contract_imports_no_driver_network_or_model(path):
    """An experiment a page runs on the instrument contract is held to the
    rule of the contract's own package, and uses neither the live mode nor
    a product."""
    tree = ast.parse(path.read_text())
    imports = set(all_imports(tree))
    assert {i for i in imports if forbidden(i)} == set()
    assert {i for i in imports if i.startswith("pbc.instruments")} <= (
        PAGE_INSTRUMENT_MODULES
    )
    if path.relative_to(ROOT).as_posix() == CAPSTONE_EXPERIMENT:
        # The capstone's: the product's simulator route only (above).
        assert product_modules(path.read_text()) <= CAPSTONE_PRODUCT_MODULES
    else:
        assert not any(i.startswith("pbc.products") for i in imports)
    assert not re.search(r"\bLIVE\b", path.read_text())


def test_the_experiments_on_the_contract_are_the_four_lessons():
    """SA3 and SA4 (F142), SA6 (F143), whose campaign runs on the simulated
    adapter, and the capstone SA9 (F145); each is held to the rule of the
    test above."""
    using = {
        p.relative_to(ROOT).as_posix()
        for p in EXPERIMENTS
        if "pbc.instruments" in p.read_text()
    }
    assert using == {
        "src/pbc/electromagnetism/experiments/simulators_and_instruments.py",
        "src/pbc/electromagnetism/experiments/measurement_quality.py",
        "src/pbc/electromagnetism/experiments/measurement_campaigns.py",
        CAPSTONE_EXPERIMENT,
    }


def imports_the_contract(tree: ast.Module) -> bool:
    return any(
        name == "pbc.instruments" or name.startswith("pbc.instruments.")
        for name in all_imports(tree)
    )


def library_modules_on_the_contract() -> list[Path]:
    """The library modules under src/pbc that import pbc.instruments, by
    their import statements: neither the contract's own package and the
    product (held to the rule above), nor an experiment (held to the rule
    of the experiments). A page or an experiment runs the contract through
    such a module (SA6 through pbc.electromagnetism.campaign, F143)."""
    own = {p for d in PACKAGES for p in d.rglob("*.py")}
    return [
        path
        for path in sorted((ROOT / "src/pbc").rglob("*.py"))
        if path not in own
        and path not in EXPERIMENTS
        and imports_the_contract(ast.parse(path.read_text()))
    ]


def breaks_the_experiment_rule(source: str, capstone: bool = False) -> list[str]:
    """What breaks the import rule of an experiment on the contract (the
    test of the experiments above) in ``source``: a forbidden import, a
    module of pbc.instruments a page may not run, a product (for the
    capstone's module: a product module outside its simulator route), the
    live mode."""
    imports = set(all_imports(ast.parse(source)))
    found = sorted(i for i in imports if forbidden(i))
    found += sorted(
        i
        for i in imports
        if i.startswith("pbc.instruments") and i not in PAGE_INSTRUMENT_MODULES
    )
    if capstone:
        found += sorted(product_modules(source) - CAPSTONE_PRODUCT_MODULES)
    else:
        found += sorted(i for i in imports if i.startswith("pbc.products"))
    if re.search(r"\bLIVE\b", source):
        found.append("LIVE")
    return found


def test_the_library_modules_on_the_contract_are_derived_and_include_the_campaign():
    found = {p.relative_to(ROOT).as_posix() for p in library_modules_on_the_contract()}
    assert "src/pbc/electromagnetism/campaign.py" in found
    # a module that names the contract only in its text imports nothing
    assert "src/pbc/electromagnetism/measurement.py" not in found


@pytest.mark.parametrize(
    "path",
    library_modules_on_the_contract(),
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_a_library_module_on_the_contract_imports_no_driver_network_or_model(path):
    """A library module that runs the contract for a page is held to the
    import rule of the experiments on the contract (#584)."""
    capstone = path.relative_to(ROOT).as_posix() == CAPSTONE_LIBRARY
    assert breaks_the_experiment_rule(path.read_text(), capstone) == []


def test_a_forbidden_import_in_a_library_module_on_the_contract_is_found():
    source = (ROOT / "src/pbc/electromagnetism/campaign.py").read_text()
    assert breaks_the_experiment_rule(source) == []
    for planted, expected in (
        ("import pyvisa\n", "pyvisa"),
        ("from urllib.request import urlopen\n", "urllib.request"),
        ("import subprocess\n", "subprocess"),
        (
            "from pbc.agents.clients.openai import OpenAIClient\n",
            "pbc.agents.clients.openai",
        ),
        ("from pbc.instruments.live import LiveInstrument\n", "pbc.instruments.live"),
        ("from pbc.products.physics_lab import workflow\n", "pbc.products.physics_lab"),
    ):
        assert expected in breaks_the_experiment_rule(planted + source), planted
    capstone = (ROOT / CAPSTONE_LIBRARY).read_text()
    assert breaks_the_experiment_rule(capstone, capstone=True) == []
    for planted, expected in (
        ("from pbc.products.physics_lab import interface\n", "interface"),
        ("import pbc.products.physics_lab.__main__\n", "__main__"),
        ("from pbc.instruments import LIVE\n", "LIVE"),
    ):
        found = breaks_the_experiment_rule(planted + capstone, capstone=True)
        assert any(expected in f for f in found), planted


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
    allowed_here = {m for m, files in DEVICE.items() if path.name in files}
    assert {i for i in imports if forbidden(i)} - allowed_here == set()
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
    assert "pbc.instruments.analog_discovery" not in loaded
    assert "http.server" not in loaded
    assert "pbc.agents.clients" not in loaded
    assert not any(m.startswith("pbc.agents.clients.") for m in loaded)
