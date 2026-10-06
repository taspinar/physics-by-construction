"""The Lean check fails on a module that does not compile, on 'sorry', and on
an axiom declared by the project.

Each case is a throwaway Lake project with the configuration of the real one.
It shares the real project's packages, so Mathlib is neither downloaded nor
built again.
"""

import shutil
from pathlib import Path

import pytest
from support.checks import output, run_check
from support.paths import LEAN_PROJECT


@pytest.fixture
def lean_project(tmp_path: Path) -> Path:
    packages = LEAN_PROJECT / ".lake" / "packages"
    assert packages.is_dir(), (
        "the Lean packages are not fetched yet; run ./scripts/check-lean.sh first"
    )
    for name in ("lakefile.toml", "lake-manifest.json", "lean-toolchain"):
        shutil.copy(LEAN_PROJECT / name, tmp_path / name)
    (tmp_path / ".lake").mkdir()
    (tmp_path / ".lake" / "packages").symlink_to(packages, target_is_directory=True)
    (tmp_path / "PhysicsByConstruction").mkdir()
    return tmp_path


def test_fails_on_a_module_that_does_not_compile(lean_project: Path):
    (lean_project / "PhysicsByConstruction" / "Broken.lean").write_text(
        "theorem broken : (1 : Nat) = 1 := by\n  exact rfl rfl\n"
    )

    result = run_check("lean-build", lean_project)

    assert result.returncode != 0
    assert "Broken.lean" in output(result) and "build failed" in output(result)


def test_fails_on_sorry_and_on_a_project_axiom(lean_project: Path):
    # Both files compile; only the audit after the build can reject them.
    (lean_project / "PhysicsByConstruction" / "Unproved.lean").write_text(
        "theorem unproved (n : Nat) : n + 0 = n := by\n  sorry\n"
    )
    (lean_project / "PhysicsByConstruction" / "Assumed.lean").write_text(
        "axiom energyIsConserved : ∀ n : Nat, n = n\n\n"
        "theorem usesIt : (2 : Nat) = 2 := energyIsConserved 2\n"
    )

    result = run_check("lean-build", lean_project)

    assert result.returncode != 0
    assert "Build completed successfully" in output(result)
    assert "'unproved' uses 'sorry'" in output(result)
    assert "'energyIsConserved' is declared as an axiom" in output(result)
    assert "'usesIt' depends on axiom 'energyIsConserved'" in output(result)
