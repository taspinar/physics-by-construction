"""The Lean check fails on a module that does not compile, on 'sorry', and on
an axiom declared by the project.

Each case is a throwaway Lake project with the configuration of the real one.
It shares the real project's packages, so Mathlib is neither downloaded nor
built again.
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from support.checks import output, run_check
from support.paths import LEAN_PROJECT, REPO_ROOT


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


def test_a_passed_check_records_what_compiled_the_proofs(lean_project: Path):
    module = lean_project / "PhysicsByConstruction" / "Sound.lean"
    module.write_text("theorem sound (n : Nat) : n + 0 = n := rfl\n")

    result = run_check("lean-build", lean_project)

    assert result.returncode == 0, output(result)
    record = json.loads((lean_project / ".lake" / "pbc-build-record.json").read_text())
    pinned = json.loads((LEAN_PROJECT / "lake-manifest.json").read_text())
    mathlib = next(p for p in pinned["packages"] if p["name"] == "mathlib")
    toolchain = (LEAN_PROJECT / "lean-toolchain").read_text().strip()
    assert record["toolchain"] == toolchain
    assert toolchain.endswith(f"v{record['lean']['version']}")
    assert record["mathlib"] == {"tag": mathlib["inputRev"], "rev": mathlib["rev"]}
    assert record["modules"] == {
        "PhysicsByConstruction.Sound": hashlib.sha256(module.read_bytes()).hexdigest()
    }


def test_a_failed_check_leaves_no_record_of_an_earlier_pass(lean_project: Path):
    module = lean_project / "PhysicsByConstruction" / "Changing.lean"
    module.write_text("theorem changing (n : Nat) : n + 0 = n := rfl\n")
    assert run_check("lean-build", lean_project).returncode == 0
    record = lean_project / ".lake" / "pbc-build-record.json"
    assert record.is_file()

    module.write_text("theorem changing (n : Nat) : n + 0 = n := by\n  sorry\n")
    result = run_check("lean-build", lean_project)

    assert result.returncode != 0
    assert not record.exists()


def test_a_relative_project_argument_keeps_the_record_in_that_project(
    lean_project: Path,
):
    # The check changes into the project; the record must still be the
    # project's own, not one resolved relative to the new working directory.
    relative = Path(os.path.relpath(lean_project, REPO_ROOT))
    assert not relative.is_absolute()
    module = lean_project / "PhysicsByConstruction" / "Relative.lean"
    module.write_text("theorem relative (n : Nat) : n + 0 = n := rfl\n")

    passed = run_check("lean-build", relative)

    assert passed.returncode == 0, output(passed)
    record = lean_project / ".lake" / "pbc-build-record.json"
    assert record.is_file()

    module.write_text("theorem relative (n : Nat) : n + 0 = n := by\n  sorry\n")
    failed = run_check("lean-build", relative)

    assert failed.returncode != 0
    assert not record.exists()
