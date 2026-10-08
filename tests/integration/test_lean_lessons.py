"""Every theorem a lesson displays is compiled, and uses no axiom of the
project and no ``sorry``.

The Lean check (test_lean_check.py) fails on a ``sorry`` or an axiom anywhere
in ``lean/``. This test starts from the other end: the regions that the
lesson pages show are found in the lesson sources, each declaration in them
is looked up in the compiled modules, and the axioms it depends on are
listed.
"""

import re
import subprocess

import pytest
from support import lesson_checks
from support.paths import LEAN_PROJECT, REPO_ROOT

from pbc.authoring.lean import anchored_lines

STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

_ASSIGNMENT = re.compile(r'^(\w+)\s*=\s*"(PhysicsByConstruction[\w.]*)"', re.MULTILINE)
_EXCERPT = re.compile(r'lean_excerpt\(\s*([\w.]+|"[\w.]+")\s*,\s*"(\w+)"')
_DECLARATION = re.compile(
    r"^(?:noncomputable\s+)?(?:theorem|lemma|def)\s+([\w.']+)", re.MULTILINE
)


def displayed_regions() -> list[tuple[str, str, str]]:
    """Return (page, module, anchor) for every Lean excerpt of every lesson."""
    regions = []
    for page in lesson_checks.lesson_pages(REPO_ROOT):
        text = page.read_text(encoding="utf-8")
        modules = dict(_ASSIGNMENT.findall(text))
        for reference, anchor in _EXCERPT.findall(text):
            module = (
                reference.strip('"')
                if reference.startswith('"')
                else modules[reference]
            )
            regions.append((page.relative_to(REPO_ROOT).as_posix(), module, anchor))
    return regions


def test_the_lessons_display_lean_proofs():
    # Without regions, the tests below would pass on nothing.
    assert displayed_regions()


def declared_names(module: str, anchor: str) -> list[str]:
    file = LEAN_PROJECT / f"{module.replace('.', '/')}.lean"
    region, _ = anchored_lines(file.read_text(encoding="utf-8"), anchor)
    return _DECLARATION.findall("\n".join(region))


def test_every_displayed_region_declares_something():
    for page, module, anchor in displayed_regions():
        assert declared_names(module, anchor), f"{page}: {module}:{anchor}"


@pytest.fixture(scope="module")
def axioms_report(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The output of ``#print axioms`` for every displayed declaration."""
    imports = set()
    commands = []
    for _, module, anchor in displayed_regions():
        imports.add(module)
        namespace = module.rsplit(".", 1)[0]
        commands += [
            f"#print axioms {namespace}.{name}"
            for name in declared_names(module, anchor)
        ]
    source = "\n".join(
        [*(f"import {module}" for module in sorted(imports)), "", *commands, ""]
    )
    file = tmp_path_factory.mktemp("axioms") / "Displayed.lean"
    file.write_text(source)
    result = subprocess.run(
        ["lake", "env", "lean", str(file)],
        cwd=LEAN_PROJECT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_every_displayed_declaration_is_compiled_without_sorry_or_axioms(
    axioms_report: str,
):
    expected = {
        f"{module.rsplit('.', 1)[0]}.{name}"
        for _, module, anchor in displayed_regions()
        for name in declared_names(module, anchor)
    }
    # Lean wraps long lines, so the report is read as running text.
    report = " ".join(axioms_report.split())
    reported = {}
    for found in re.finditer(
        r"'([\w.']+)' "
        r"(?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])",
        report,
    ):
        axioms = {a.strip() for a in (found.group(2) or "").split(",") if a.strip()}
        reported[found.group(1)] = axioms

    assert set(reported) == expected, axioms_report
    for name, axioms in reported.items():
        assert axioms <= STANDARD_AXIOMS, (
            f"{name} depends on {axioms - STANDARD_AXIOMS}"
        )
