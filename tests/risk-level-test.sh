#!/usr/bin/env bash

set -euo pipefail

# The risk level of a change (ADR 020 decision 1, scripts/lib/risk.sh): the
# path minimum, each mechanically detected escalation trigger, the stated and
# the assessed level, the refusals, and a lowering that is only ever a
# request. And the protected list of .agents/policies/guardrails.conf, which
# names the Level 3 paths: a change to each is reported as protected.

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/risk-level-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "risk level test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
source "$source_root/scripts/lib/fingerprint.sh"
source "$source_root/scripts/lib/guardrails.sh"
source "$source_root/scripts/lib/completion.sh"
source "$source_root/scripts/lib/risk.sh"

# setup_repo <label>: a project with the real gate configuration, a test
# module, a shell test, a Lean proof, a budget table, and a dependency file,
# on a feature branch of Issue 5 without changes.
setup_repo() {
  local repo="$tmp/$1"

  mkdir -p "$repo/docs" "$repo/src" "$repo/tests/unit" "$repo/.agents/policies" "$repo/scripts"
  copy_workflow "$repo"
  cp "$source_root/.gitignore" "$repo/.gitignore"
  cp "$source_root/.agents/policies/guardrails.conf" "$repo/.agents/policies/guardrails.conf"
  printf '# Guide\n' >"$repo/docs/guide.md"
  printf 'print("x")\n' >"$repo/src/code.py"
  cat >"$repo/tests/unit/test_code.py" <<'PY'
import pytest


def test_one():
    assert 1 + 1 == 2
    assert abs(0.1 + 0.2 - 0.3) < 1e-12
    assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9)


@pytest.mark.same_machine
def test_two():
    assert "a" < "b"
PY
  printf 'def test_three():\n    assert True\n' >"$repo/tests/unit/test_other.py"
  cat >"$repo/tests/thing-test.sh" <<'SH'
#!/usr/bin/env bash
fail() { echo "thing test failed: $*" >&2; exit 1; }
out="$(echo ok)"
[[ "$out" == "ok" ]] || fail "the output is $out"
grep -Fq "ok" <<<"$out" || exit 1
expect_line "ok"
echo "thing tests passed"
SH
  mkdir -p "$repo/lean/Proofs"
  cat >"$repo/lean/Proofs/Thing.lean" <<'LEAN'
-- The proofs of a lesson; `sorry` would fail the axiom audit.
theorem two_add_two : 2 + 2 = 4 := by
  rfl

@[simp] theorem zero_add' (n : Nat) : 0 + n = n := by
  simp

example : 1 + 1 = 2 := rfl

#guard 2 * 3 == 6
LEAN
  printf '# budgets\nlessons/a | 60 | slow\n' >"$repo/scripts/lesson-budgets.conf"
  printf '[project]\nname = "x"\n' >"$repo/pyproject.toml"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.name "Risk Test"
  git -C "$repo" config user.email "risk-test@example.com"
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" switch -q -c feature/5-thing
  printf '%s\n' "$repo"
}

# assess <repo> [review-json]: derives the level against main.
assess() {
  risk_assess "$1" "main" "$(git -C "$1" merge-base HEAD main)" 5 "${2:-}" || fail "the level of $1 could not be derived"
}

# record <repo> <level> [schema]: the implementer's completion record.
record() {
  mkdir -p "$1/.agents/completion"
  jq -n --argjson level "$2" --arg schema "${3:-completion/v2}" '{
    schema: $schema, status: "complete",
    criteria: [{criterion: "It works", status: "met", evidence: "a test"}], remaining: []
  } + (if $schema == "completion/v2" then
         {risk: {level: $level, triggers: [], rationale: "as derived"},
          criteria: [{criterion: "It works", gate: "implementation", status: "met", evidence: "a test"}]}
       else {} end)' >"$1/.agents/completion/5.json"
}

# request <repo> [<required> <requested>]: the approval request; with levels,
# a lowering request. It names the content tree as it is when it is written.
request() {
  local tree

  mkdir -p "$1/.agents/approvals" "$tmp/request"
  tree="$(risk_content_tree "$1" "$tmp/request" 5)" || fail "the content tree of $1 could not be derived"
  {
    echo "# Approval request: Issue #5"
    echo
    echo "Issue: #5"
    echo "Level: ${2:-3}"
    echo "Derived from: the triggers"
    echo "Tree: $tree (the content tree under review)"
    if [[ -n "${3:-}" ]]; then
      echo "Required level: $2"
      echo "Requested level: $3"
      echo "Reason: the narrowed tolerance makes the test stricter"
      echo "Owner's word: \"Lower #5 to Level 2\" (2026-10-19, in the session)"
    fi
  } >"$1/.agents/approvals/5.md"
}

expect() {
  # expect <description> <variable> <value>
  [[ "${!2}" == "$3" ]] || fail "$1: $2 is '${!2}' instead of '$3'"
}

expect_trigger() {
  # expect_trigger <description> <fragment>
  printf '%s\n' "$RISK_TRIGGERS" | grep -Fq "$2" || fail "$1: no trigger '$2' in: ${RISK_TRIGGERS:-none}"
  expect "$1" RISK_REQUIRED 3
  expect "$1" RISK_BY triggers
}

expect_error() {
  printf '%s\n' "$RISK_ERRORS" | grep -Fq "$2" || fail "$1: no refusal '$2' in: ${RISK_ERRORS:-none}"
}

# --- The path minimum.
repo="$(setup_repo docs)"
printf 'More.\n' >>"$repo/docs/guide.md"
printf '# Notes\n' >"$repo/NOTES.md"
assess "$repo"
expect "documentation only" RISK_PATH_MIN 1
expect "documentation only" RISK_REQUIRED 1

repo="$(setup_repo source)"
printf 'print("y")\n' >>"$repo/src/code.py"
assess "$repo"
expect "a source change" RISK_PATH_MIN 2

repo="$(setup_repo gate)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
assess "$repo"
expect "a change to the gate's library" RISK_PATH_MIN 3
printf '%s\n' "$RISK_PATH_REASONS" | grep -Fq "scripts/lib/completion.sh" || fail "the Level 3 path was not named"

# The approval request is no Level 3 path of the change it belongs to.
repo="$(setup_repo request-only)"
printf 'More.\n' >>"$repo/docs/guide.md"
request "$repo" 1
assess "$repo"
expect "a change whose only Level 3 path is its own approval request" RISK_PATH_MIN 1
expect "a change whose only Level 3 path is its own approval request" RISK_REQUIRED 1
[[ "$(guardrails_classify "$repo" main "$(git -C "$repo" merge-base HEAD main)" | guardrails_level)" == "protected" ]] ||
  fail "the approval request is not code-owned by the gate's list"

# --- Each mechanical trigger.
repo="$(setup_repo tolerance)"
sed -i.bak 's/rel=1e-9/rel=1e-6/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a widened tolerance" "tolerance or budget changed: tests/unit/test_code.py (assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9))"

# A tolerance added to a test that is already there can widen what it
# accepts; one in a new test weakens no test that is there (#269).
repo="$(setup_repo added-tolerance)"
printf '    assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a tolerance added to an existing test" "tolerance or budget changed: tests/unit/test_code.py (assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1))"

repo="$(setup_repo new-test-tolerance)"
printf '\n\ndef test_four():\n    assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect "a tolerance in a new test of an existing file" RISK_TRIGGERS ""
expect "a tolerance in a new test of an existing file" RISK_REQUIRED 2

repo="$(setup_repo new-test-file-tolerance)"
cat >"$repo/tests/unit/test_new.py" <<'PY'
import pytest

tolerance = 1e-9


def helper(x):
    return pytest.approx(x, abs=1e-9)


class TestThing:
    def test_sum(self):
        assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-6)
PY
assess "$repo"
expect "tolerances in a new test file" RISK_TRIGGERS ""
expect "tolerances in a new test file" RISK_REQUIRED 2

# A test method in a class is a test like a function (#269 review): a new
# one is exempt; a tolerance added to an existing one, or in a method that is
# no test, stays a reading.
repo="$(setup_repo new-class-test-tolerance)"
printf '\n\nclass TestFour:\n    def test_sum(self):\n        assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect "a tolerance in a new test method of a class" RISK_TRIGGERS ""
expect "a tolerance in a new test method of a class" RISK_REQUIRED 2

# class_fixture <repo>: an existing class-based test on main, below which
# the feature branch starts.
class_fixture() {
  git -C "$1" switch -q main
  printf '\n\nclass TestFive:\n    def test_sum(self):\n        assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-8)\n' >>"$1/tests/unit/test_code.py"
  git -C "$1" commit -qam "A class-based test"
  git -C "$1" switch -q feature/5-thing
  git -C "$1" merge -q --ff-only main
}

repo="$(setup_repo existing-class-test-widened)"
class_fixture "$repo"
sed -i.bak 's/rel=1e-8/rel=1e-3/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a tolerance widened in an existing test method of a class" \
  "tolerance or budget changed: tests/unit/test_code.py (assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-8))"

repo="$(setup_repo existing-class-test-added)"
class_fixture "$repo"
printf '        assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a tolerance added to an existing test method of a class" \
  "tolerance or budget changed: tests/unit/test_code.py (assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1))"

repo="$(setup_repo class-helper-tolerance)"
printf '\n\nclass TestSix:\n    def loose(self, x):\n        return pytest.approx(x, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a tolerance in a new method of a class that is no test" \
  "tolerance or budget changed: tests/unit/test_code.py (return pytest.approx(x, rel=0.1))"

# A new source file widens no check that is there: its tolerances are no
# reading (#297). The same line added to an existing source file stays one,
# and a new source file at a protected path keeps Level 3 by the path rule.
repo="$(setup_repo new-source-tolerance)"
mkdir -p "$repo/src/pbc/experiments"
cat >"$repo/src/pbc/experiments/refraction.py" <<'PY'
import numpy as np

ANGLE_TOLERANCE = 1e-6


def agrees(a, b):
    return np.isclose(a, b, rtol=1e-9)
PY
assess "$repo"
expect "tolerances in a new source file" RISK_TRIGGERS ""
expect "tolerances in a new source file" RISK_REQUIRED 2

repo="$(setup_repo existing-source-tolerance)"
printf 'agrees = np.isclose(a, b, rtol=1e-9)\n' >>"$repo/src/code.py"
assess "$repo"
expect_trigger "a tolerance added to an existing source file" "tolerance or budget changed: src/code.py (agrees = np.isclose(a, b, rtol=1e-9))"

repo="$(setup_repo new-protected-source-tolerance)"
mkdir -p "$repo/src/pbc/authoring"
printf 'agrees = np.isclose(a, b, rtol=1e-9)\n' >"$repo/src/pbc/authoring/digest.py"
assess "$repo"
expect "a tolerance in a new source file at a protected path" RISK_TRIGGERS ""
expect "a tolerance in a new source file at a protected path" RISK_PATH_MIN 3
expect "a tolerance in a new source file at a protected path" RISK_REQUIRED 3

# A new helper under tests/ that is no test file is no new test (#269 review).
repo="$(setup_repo new-support-tolerance)"
mkdir -p "$repo/tests/support"
printf 'tolerance = 1e-3\n' >"$repo/tests/support/limits.py"
assess "$repo"
expect_trigger "a tolerance in a new support module under tests/" "tolerance or budget changed: tests/support/limits.py (tolerance = 1e-3)"

# In the same added block as a new test, a tolerance below a helper def, or
# below an existing test that only moved, is no part of the new test.
repo="$(setup_repo new-test-then-helper)"
printf '\n\ndef test_four():\n    assert True\n\n\ndef loose(x):\n    return pytest.approx(x, rel=0.1)\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a tolerance in a helper after a new test" "tolerance or budget changed: tests/unit/test_code.py (return pytest.approx(x, rel=0.1))"

repo="$(setup_repo moved-test-tolerance)"
python3 - "$repo/tests/unit/test_code.py" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
text = text.replace("def test_one():\n    assert 1 + 1 == 2\n", "")
text = text.replace(
    "    assert abs(0.1 + 0.2 - 0.3) < 1e-12\n    assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9)\n",
    "",
)
text += (
    "\n\ndef test_four():\n    assert True\n\n\ndef test_one():\n    assert 1 + 1 == 2\n"
    "    assert abs(0.1 + 0.2 - 0.3) < 1e-12\n    assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9)\n"
    "    assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1)\n"
)
open(path, "w").write(text)
PY
assess "$repo"
expect_trigger "a tolerance added to an existing test that moved below a new test" \
  "tolerance or budget changed: tests/unit/test_code.py (assert 0.31 == pytest.approx(0.1 + 0.2, rel=0.1))"

# A tolerance widened or removed in an existing test stays a reading.
repo="$(setup_repo widened-tolerance)"
sed -i.bak 's/rel=1e-9/rel=1e-3/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a tolerance widened from rel=1e-9 to rel=1e-3" "tolerance or budget changed: tests/unit/test_code.py (assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9))"

repo="$(setup_repo removed-tolerance)"
sed -i.bak '/rel=1e-9/d' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a removed tolerance" "tolerance or budget changed: tests/unit/test_code.py (assert 0.3 == pytest.approx(0.1 + 0.2, rel=1e-9))"

repo="$(setup_repo budget)"
printf 'lessons/b | 90 | slower\n' >>"$repo/scripts/lesson-budgets.conf"
assess "$repo"
expect_trigger "a new budget exception" "tolerance or budget changed: scripts/lesson-budgets.conf (lessons/b | 90 | slower)"

repo="$(setup_repo skip)"
printf '\n@pytest.mark.skip(reason="slow")\ndef test_four():\n    assert False\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a new skip" "skip or expected failure added: tests/unit/test_code.py (@pytest.mark.skip(reason=\"slow\"))"

repo="$(setup_repo xfail)"
printf '\n@pytest.mark.xfail\ndef test_four():\n    assert False\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a new expected failure" "skip or expected failure added: tests/unit/test_code.py (@pytest.mark.xfail)"

repo="$(setup_repo assertion)"
sed -i.bak '/assert 1 + 1 == 2/d' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a removed assertion" "assertion removed or changed: tests/unit/test_code.py (assert 1 + 1 == 2)"

repo="$(setup_repo weakened)"
sed -i.bak 's/assert "a" < "b"/assert "a" <= "b"/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a weakened assertion" "assertion removed or changed: tests/unit/test_code.py (assert \"a\" < \"b\")"

repo="$(setup_repo test-function)"
python3 - "$repo/tests/unit/test_code.py" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
open(path, "w").write(text[: text.index("@pytest.mark.same_machine")])
PY
assess "$repo"
expect_trigger "a removed test function" "test removed: tests/unit/test_code.py (def test_two():)"

repo="$(setup_repo test-file)"
git -C "$repo" rm -q tests/unit/test_other.py
assess "$repo"
expect_trigger "a removed test file" "test removed: tests/unit/test_other.py (the test file is deleted)"

repo="$(setup_repo marker)"
sed -i.bak '/@pytest.mark.same_machine/d' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a removed marker" "marker changed: tests/unit/test_code.py (@pytest.mark.same_machine)"

# A marker that only structures new cases is no trigger (#243); one that
# selects, excludes, or relocates tests stays one, also beside it.
repo="$(setup_repo parametrize)"
printf '\n\n@pytest.mark.parametrize("n", [1, 2, 3])\ndef test_four(n):\n    assert n > 0\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect "an added parametrize" RISK_TRIGGERS ""
expect "an added parametrize" RISK_REQUIRED 2

repo="$(setup_repo added-marker)"
printf '\n\n@pytest.mark.same_machine\ndef test_four():\n    assert True\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "an added same_machine marker" "marker changed: tests/unit/test_code.py (@pytest.mark.same_machine)"

repo="$(setup_repo added-skipif)"
printf '\n\n@pytest.mark.skipif(True, reason="slow")\n@pytest.mark.parametrize("n", [1])\ndef test_four(n):\n    assert n\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "an added skipif beside a parametrize" "skip or expected failure added: tests/unit/test_code.py (@pytest.mark.skipif(True, reason=\"slow\"))"
printf '%s\n' "$RISK_TRIGGERS" | grep -Fq "parametrize" && fail "the parametrize beside a skipif was read as a trigger: $RISK_TRIGGERS"

repo="$(setup_repo parametrize-and-marker)"
printf '\n\npytestmark = [pytest.mark.parametrize("n", [1]), pytest.mark.same_machine]\n' >>"$repo/tests/unit/test_code.py"
assess "$repo"
expect_trigger "a same_machine marker on the line of a parametrize" \
  "marker changed: tests/unit/test_code.py (pytestmark = [pytest.mark.parametrize(\"n\", [1]), pytest.mark.same_machine])"

# A parametrize already on the base that loses a case stays a reading.
repo="$(setup_repo changed-parametrize)"
git -C "$repo" switch -q main
printf '\n\n@pytest.mark.parametrize("n", [1, 2, 3])\ndef test_four(n):\n    assert n > 0\n' >>"$repo/tests/unit/test_code.py"
git -C "$repo" commit -qam "Parametrize"
git -C "$repo" switch -q feature/5-thing
git -C "$repo" reset -q --hard main
sed -i.bak 's/\[1, 2, 3\]/[1, 2]/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a parametrize that drops a case" "marker changed: tests/unit/test_code.py (@pytest.mark.parametrize(\"n\", [1, 2, 3]))"

# A parametrize added to a test that is already on the base is risk-sensitive
# (#243, the owner's review of PR #249): it changes the cases the test runs.
# Giving the test a parameter changes its signature, which reads as a changed
# test; parametrizing an argument it already has changes no line of the test,
# so the added decorator itself is the reading.
repo="$(setup_repo parametrize-existing-signature)"
git -C "$repo" switch -q main
printf '\n\ndef test_five(n):\n    assert n > 0\n' >>"$repo/tests/unit/test_code.py"
git -C "$repo" commit -qam "A test with an argument"
git -C "$repo" switch -q feature/5-thing
git -C "$repo" reset -q --hard main
sed -i.bak 's/^def test_five(n):/@pytest.mark.parametrize("n", [1])\ndef test_five(n):/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a parametrize on an existing test, signature unchanged" \
  "marker changed: tests/unit/test_code.py (@pytest.mark.parametrize(\"n\", [1]))"

# The same added block adds a different new test before the existing one
# (the owner's review of PR #250): the decorator belongs to the existing test
# that follows it, not to the new test, so it still reads as a trigger.
repo="$(setup_repo parametrize-existing-after-new)"
git -C "$repo" switch -q main
printf '\n\ndef test_five(n):\n    assert n > 0\n' >>"$repo/tests/unit/test_code.py"
git -C "$repo" commit -qam "A test with an argument"
git -C "$repo" switch -q feature/5-thing
git -C "$repo" reset -q --hard main
python3 - "$repo/tests/unit/test_code.py" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
text = text.replace(
    "def test_five(n):",
    'def test_six():\n    assert True\n\n\n@pytest.mark.parametrize("n", [1])\ndef test_five(n):',
)
open(path, "w").write(text)
PY
assess "$repo"
expect_trigger "a parametrize on an existing test after a new test in the same block" \
  "marker changed: tests/unit/test_code.py (@pytest.mark.parametrize(\"n\", [1]))"

repo="$(setup_repo parametrize-existing-parameter)"
sed -i.bak 's/^def test_one():/@pytest.mark.parametrize("n", [1])\ndef test_one(n):/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
assess "$repo"
expect_trigger "a parametrize that gives an existing test a parameter" "test removed: tests/unit/test_code.py (def test_one():)"

repo="$(setup_repo dependency)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
assess "$repo"
expect_trigger "a changed dependency file" "dependency file changed: pyproject.toml"

# The same triggers in a shell test and a Lean proof.
repo="$(setup_repo shell-assertion)"
sed -i.bak '/|| fail "the output is/d' "$repo/tests/thing-test.sh" && rm "$repo/tests/thing-test.sh.bak"
assess "$repo"
expect_trigger "a removed shell assertion" \
  "assertion removed or changed: tests/thing-test.sh ([[ \"\$out\" == \"ok\" ]] || fail \"the output is \$out\")"

repo="$(setup_repo shell-weakened)"
sed -i.bak 's/grep -Fq "ok" <<<"$out" || exit 1/grep -q . <<<"$out" || exit 1/; s/^expect_line "ok"$/true/' \
  "$repo/tests/thing-test.sh" && rm "$repo/tests/thing-test.sh.bak"
assess "$repo"
expect_trigger "a weakened shell assertion" "assertion removed or changed: tests/thing-test.sh (grep -Fq \"ok\" <<<\"\$out\" || exit 1)"
expect_trigger "a removed shell expectation" "assertion removed or changed: tests/thing-test.sh (expect_line \"ok\")"

repo="$(setup_repo lean-theorem)"
sed -i.bak 's/^theorem two_add_two : 2 + 2 = 4 := by$/theorem two_add_two : 2 + 2 = 2 + 2 := by/' "$repo/lean/Proofs/Thing.lean" &&
  rm "$repo/lean/Proofs/Thing.lean.bak"
assess "$repo"
expect_trigger "a changed Lean statement" "assertion removed or changed: lean/Proofs/Thing.lean (theorem two_add_two : 2 + 2 = 4 := by)"

repo="$(setup_repo lean-removed)"
sed -i.bak '/^@\[simp\] theorem/,/^  simp$/d; /^example/d; /^#guard/d' "$repo/lean/Proofs/Thing.lean" &&
  rm "$repo/lean/Proofs/Thing.lean.bak"
assess "$repo"
expect_trigger "a removed Lean theorem" "assertion removed or changed: lean/Proofs/Thing.lean (@[simp] theorem zero_add' (n : Nat) : 0 + n = n := by)"
expect_trigger "a removed Lean example" "assertion removed or changed: lean/Proofs/Thing.lean (example : 1 + 1 = 2 := rfl)"
expect_trigger "a removed Lean check" "assertion removed or changed: lean/Proofs/Thing.lean (#guard 2 * 3 == 6)"

repo="$(setup_repo lean-sorry)"
sed -i.bak 's/^  rfl$/  sorry/' "$repo/lean/Proofs/Thing.lean" && rm "$repo/lean/Proofs/Thing.lean.bak"
printf '\naxiom free_lunch : 1 = 2\n' >>"$repo/lean/Proofs/Thing.lean"
assess "$repo"
expect_trigger "a new sorry" "skip or expected failure added: lean/Proofs/Thing.lean (sorry)"
expect_trigger "a new axiom" "skip or expected failure added: lean/Proofs/Thing.lean (axiom free_lunch : 1 = 2)"

# What strengthens or only moves tests is no trigger: a new test with its
# assertions, and an assertion moved unchanged.
repo="$(setup_repo no-trigger)"
printf '\ndef test_four():\n    assert 2 * 2 == 4\n' >>"$repo/tests/unit/test_other.py"
python3 - "$repo/tests/unit/test_code.py" <<'PY'
import sys
path = sys.argv[1]
lines = open(path).read().split("\n")
i = lines.index("    assert 1 + 1 == 2")
lines[i], lines[i + 1] = lines[i + 1], lines[i]
open(path, "w").write("\n".join(lines))
PY
# In a shell test and a Lean proof: a new assertion, a new theorem, a changed
# proof below the statement, and a comment that names sorry.
printf 'grep -Fq "o" <<<"$out" || fail "no o"\n' >>"$repo/tests/thing-test.sh"
sed -i.bak 's/^  rfl$/  decide/' "$repo/lean/Proofs/Thing.lean" && rm "$repo/lean/Proofs/Thing.lean.bak"
printf '\n/-- Proved without `sorry`. -/\ntheorem three : 1 + 2 = 3 := rfl\n' >>"$repo/lean/Proofs/Thing.lean"
assess "$repo"
[[ -z "$RISK_TRIGGERS" ]] || fail "a new test or a moved assertion was taken for a trigger: $RISK_TRIGGERS"
expect "new and moved tests" RISK_REQUIRED 2

# --- The stated and the assessed level: raise only.
repo="$(setup_repo stated)"
printf 'print("y")\n' >>"$repo/src/code.py"
record "$repo" 3
assess "$repo"
expect "a stated Level 3" RISK_REQUIRED 3
expect "a stated Level 3" RISK_BY assessment
expect_error "a Level 3 by assessment without its approval request" \
  "the change is Level 3 by its assessment, so it needs the committed approval request .agents/approvals/5.md"
request "$repo" 3
assess "$repo"
[[ -z "$RISK_ERRORS" ]] || fail "a Level 3 by assessment with its approval request was refused: $RISK_ERRORS"
request "$repo" 2
assess "$repo"
expect_error "a Level 3 approval request that states another level" \
  "the approval request .agents/approvals/5.md states level 2, but the change requires level 3"

repo="$(setup_repo reviewed)"
printf 'print("y")\n' >>"$repo/src/code.py"
record "$repo" 2
printf '{"architecture_impact": {"level": "minor", "rationale": "x", "checked_against": [], "risk_level": 3, "escalation_triggers": ["a published tolerance is widened"]}}\n' >"$tmp/review-01.json"
assess "$repo" "$tmp/review-01.json"
expect "the review's assessment" RISK_REVIEWED 3
expect "the review's assessment" RISK_REQUIRED 3
printf '%s\n' "$RISK_NAMED_TRIGGERS" | grep -Fq "named by the review: a published tolerance is widened" ||
  fail "the trigger the review named was not kept"
expect_error "a stated level below the review's reading" "the completion record states level 2, below the level 3"

# A stated level below the path minimum is refused, also with a request to
# lower it: the path minimum is never lowered.
repo="$(setup_repo below-paths)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 2
request "$repo" 3 2
assess "$repo"
expect_error "a stated level below the path minimum" "the completion record states level 2, below the path minimum 3"
expect_error "a lowering of the path minimum" "the approval request asks to lower the level to 2, below the path minimum 3"
expect "a lowering of the path minimum" RISK_REQUIRED 3

# A stated level below a trigger reading: refused without the request,
# recorded with both levels and the content with it; the change keeps level 3.
repo="$(setup_repo lowering)"
sed -i.bak 's/rel=1e-9/rel=1e-12/' "$repo/tests/unit/test_code.py" && rm "$repo/tests/unit/test_code.py.bak"
record "$repo" 2
assess "$repo"
expect_error "a stated level below a trigger reading, without a request" "the completion record states level 2, below the level 3 that the triggers give"
request "$repo" 3 2
assess "$repo"
[[ -z "$RISK_ERRORS" ]] || fail "a lowering of a trigger reading with its request was refused: $RISK_ERRORS"
expect "a requested lowering" RISK_REQUIRED 3
expect "a requested lowering" RISK_REQUESTED 2
statement="$(risk_statement_lines)"
for line in "- required: level 3, by the triggers" "- stated in the completion record: level 2" \
  "- derived for the content $RISK_TREE" "- content tree for the approval request (Tree:): $RISK_CONTENT_TREE"; do
  printf '%s\n' "$statement" | grep -Fqx -- "$line" || fail "the statement of a lowering lacks '$line': $statement"
done
printf '%s\n' "$statement" | grep -Fq "requested: level 2, in .agents/approvals/5.md: a request only. The change keeps level 3" ||
  fail "the statement does not record the requested level as a request: $statement"
# The request does not decide: what it states about the levels must agree
# with the record and the derivation, and it names the reason and the word.
request "$repo" 3 1
assess "$repo"
expect_error "a request that disagrees with the record" "the approval request asks for level 1, but the completion record states level 2"
request "$repo" 2 2
assess "$repo"
expect_error "a request that understates the required level" "the approval request names the required level '2', but the change requires level 3"
request "$repo" 3 2
sed -i.bak 's/^Level: 3$/Level: 2/' "$repo/.agents/approvals/5.md" && rm "$repo/.agents/approvals/5.md.bak"
assess "$repo"
expect_error "a lowering request whose level is not the required one" \
  "the approval request .agents/approvals/5.md states level 2, but the change requires level 3"
request "$repo" 3 2
sed -i.bak "/^Owner's word:/d" "$repo/.agents/approvals/5.md" && rm "$repo/.agents/approvals/5.md.bak"
assess "$repo"
expect_error "a lowering without the owner's word" "has no line 'Owner's word: ...'"

# The content tree an approval request names: the request is not part of
# it, nor of the worktree's fingerprint, so editing the request leaves both
# unchanged; every other file of the change, and the completion record and
# the handoff note that Git ignores, are part of it.
repo="$(setup_repo content-tree)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
mkdir -p "$repo/.agents/handoffs" "$repo/lessons"
printf '# Handoff\n' >"$repo/.agents/handoffs/5.md"
printf 'A lesson.\n' >"$repo/lessons/a.qmd"
request "$repo"
assess "$repo"
content="$RISK_CONTENT_TREE"
tree="$RISK_TREE"
[[ "$content" =~ ^[0-9a-f]{40}$ ]] || fail "the content tree is not a tree: '$content'"
sed -i.bak 's/^Tree: .*$/Tree: '"$content"'/' "$repo/.agents/approvals/5.md" && rm "$repo/.agents/approvals/5.md.bak"
assess "$repo"
expect "an edited approval request" RISK_CONTENT_TREE "$content"
expect "an edited approval request" RISK_TREE "$tree"
[[ -z "$RISK_ERRORS" ]] || fail "an approval request that names the content tree was refused: $RISK_ERRORS"
git -C "$repo" ls-tree -r --name-only "$content" | grep -Fqx ".agents/approvals/5.md" &&
  fail "the content tree holds the approval request"
for edit in scripts/lib/completion.sh lessons/a.qmd tests/unit/test_code.py .agents/completion/5.json .agents/handoffs/5.md; do
  cp "$repo/$edit" "$tmp/saved"
  printf '\n' >>"$repo/$edit"
  assess "$repo"
  [[ "$RISK_CONTENT_TREE" != "$content" ]] || fail "editing $edit did not change the content tree"
  cp "$tmp/saved" "$repo/$edit"
done
assess "$repo"
expect "the content restored" RISK_CONTENT_TREE "$content"

# The request leaves the fingerprint, so a script checks its tree: a request
# that names another tree is refused with the value to write, also after a
# change to the content it was written for; the tree in backticks is accepted.
sed -i.bak 's/^Tree: .*$/Tree: 0123abcd (the content tree under review)/' "$repo/.agents/approvals/5.md" &&
  rm "$repo/.agents/approvals/5.md.bak"
assess "$repo"
expect_error "a request that names another tree" \
  "the approval request .agents/approvals/5.md names tree 0123abcd, but the content tree is $content; state it on a line 'Tree: $content'"
sed -i.bak 's/^Tree: .*$/Tree: `'"$content"'`/' "$repo/.agents/approvals/5.md" && rm "$repo/.agents/approvals/5.md.bak"
assess "$repo"
[[ -z "$RISK_ERRORS" ]] || fail "an approval request that names the content tree in backticks was refused: $RISK_ERRORS"
printf 'A changed lesson.\n' >"$repo/lessons/a.qmd"
assess "$repo"
expect_error "a request written for earlier content" \
  "names tree $content, but the content tree is $RISK_CONTENT_TREE; state it on a line 'Tree: $RISK_CONTENT_TREE'"

# The earlier contract: the level is derived and recorded, nothing refused.
repo="$(setup_repo v1)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" 1 completion/v1
assess "$repo"
expect "a completion/v1 record" RISK_REQUIRED 3
expect "a completion/v1 record" RISK_ENFORCED 0
[[ -z "$RISK_ERRORS" ]] || fail "the rules of completion/v2 were applied to a completion/v1 record: $RISK_ERRORS"
statement="$(risk_statement_lines)"
printf '%s\n' "$statement" | grep -Fq "completion/v1, the contract of a feature started before ADR 020" ||
  fail "the statement does not say that the record is of the earlier contract"

# --- The protected list of guardrails.conf names the Level 3 paths of ADR
# 020 decision 1, and check-guardrails.sh reports a change to each of them.
check() {
  (cd "$1" && PATH="/usr/bin:/bin" ./scripts/check-guardrails.sh) >"$1.out" 2>&1 || {
    cat "$1.out" >&2
    fail "check-guardrails.sh failed in $1"
  }
}
specs="$(sed -n 's/^protected:[[:space:]]*//p' "$source_root/.agents/policies/guardrails.conf" | tr -s '[:space:]' '\n' | grep .)"
# Every Level 3 path of the decision but one is named here. The directory of
# the agent skills is the one: only the skills check may name it in the
# scripts and tests (ADR 019 decision 1, tests/unit/test_skills_boundary.py),
# so it is the one further path the file must hold, and the loop below shows
# that a change to it is reported as protected like every other.
expected=(docs/decisions docs/PROJECT_REQUIREMENTS.md docs/roadmap.md docs/architecture.md .github/workflows
  .github/CODEOWNERS scripts/lib scripts/check-guardrails.sh scripts/check-review.sh scripts/ci-aggregate.sh
  .agents/prompts .agents/schemas .agents/policies AGENTS.md .agents/agents.conf scripts/verify.conf scripts/verify.sh
  src/pbc/authoring/digest.py src/pbc/authoring/selection.py scripts/fetch-base.sh scripts/collect-base.sh
  src/pbc/authoring/provenance.py scripts/build-site.sh .agents/approvals
  ':(glob)scripts/*-feature.sh' ':(glob)scripts/*-planning.sh')
for path in "${expected[@]}"; do
  printf '%s\n' "$specs" | grep -Fqx -- "$path" || fail "guardrails.conf does not protect the Level 3 path $path"
done
[[ "$(printf '%s\n' "$specs" | grep -c .)" -eq $((${#expected[@]} + 1)) ]] ||
  fail "guardrails.conf protects $(printf '%s\n' "$specs" | grep -c .) paths, not the ${#expected[@]} named here and the directory of the agent skills"
repo="$(setup_repo listed)"
count=0
while IFS= read -r spec; do
  path="${spec#:(glob)}"
  path="${path//\*/x}"
  case "$path" in
    *.md | *.sh | *.py | *.conf | *CODEOWNERS) ;;
    *) path="$path/x-file" ;;
  esac
  git -C "$repo" reset -q --hard
  git -C "$repo" clean -qfd
  mkdir -p "$repo/$(dirname "$path")"
  printf '# changed\n' >>"$repo/$path"
  check "$repo"
  grep -Fq "protected: $path (" "$repo.out" || {
    cat "$repo.out" >&2
    fail "a change to $path (listed as $spec) is not reported as protected"
  }
  count=$((count + 1))
done <<<"$specs"
[[ "$count" -eq $((${#expected[@]} + 1)) ]] || fail "only $count protected paths were checked"
# Nothing a Level 1 or 2 change touches is on the list.
for path in docs/development.md site/lessons/x/index.qmd src/pbc/other.py tests/unit/test_x.py scripts/check-lean.sh \
  .agents/plans/5-thing.md pyproject.toml; do
  git -C "$repo" reset -q --hard
  git -C "$repo" clean -qfd
  mkdir -p "$repo/$(dirname "$path")"
  printf '# changed\n' >>"$repo/$path"
  check "$repo"
  if grep -Fq "protected: $path" "$repo.out"; then
    fail "the Level 1 or 2 path $path is reported as protected"
  fi
done

echo "risk level tests passed"
