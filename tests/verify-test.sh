#!/usr/bin/env bash

set -euo pipefail

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

# Independent of the caller's VERIFY_JOBS (a full verification may run with
# any limit): every run below uses the default of verify.sh unless the test
# sets VERIFY_JOBS for it.
unset VERIFY_JOBS

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/verify-test.XXXXXX")"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  echo "verify test failed: $*" >&2
  exit 1
}

mkdir -p "$tmp/bin"
printf '#!/usr/bin/env bash\necho "ruff $*" >>"$MOCK_TOOL_LOG"\nexit "${MOCK_RUFF_EXIT:-0}"\n' >"$tmp/bin/ruff"
printf '#!/usr/bin/env bash\necho "pytest $*" >>"$MOCK_TOOL_LOG"\nexit "${MOCK_PYTEST_EXIT:-0}"\n' >"$tmp/bin/pytest"
chmod +x "$tmp/bin/ruff" "$tmp/bin/pytest"

# Creates an isolated project that contains only verify.sh and the given config.
setup_project() {
  local label="$1"
  local project="$tmp/$label"

  mkdir -p "$project/scripts"
  cp "$source_root/scripts/verify.sh" "$project/scripts/verify.sh"
  if [[ $# -gt 1 ]]; then
    printf '%s\n' "${@:2}" >"$project/scripts/verify.conf"
  fi
  printf '%s\n' "$project"
}

run_verify() {
  local project="$1"

  PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
    "$project/scripts/verify.sh" ${2+"$2"} >"$project/out.log" 2>&1
}

expect_failure() {
  local project="$1"
  local description="$2"

  if run_verify "$project"; then
    cat "$project/out.log" >&2
    fail "expected failure: $description"
  fi
}

# All required checks pass.
project="$(setup_project pass "# stack checks" "" "lint: ruff check ." "tests: pytest")"
run_verify "$project" || {
  cat "$project/out.log" >&2
  fail "passing checks were reported as a failure"
}
[[ "$(grep -c . "$project/tools.log")" -eq 2 ]] || fail "not every configured check ran"

# A failing linter fails verification, and later checks still run.
project="$(setup_project lint-fails "lint: ruff check ." "tests: pytest")"
MOCK_RUFF_EXIT=1 expect_failure "$project" "ruff failure must propagate"
grep -Fq "pytest" "$project/tools.log" || fail "checks after a failure did not run"
grep -Eq "FAIL +lint" "$project/out.log" || fail "failed check was not identified"

# A failing test run fails verification.
project="$(setup_project tests-fail "lint: ruff check ." "tests: pytest")"
MOCK_PYTEST_EXIT=3 expect_failure "$project" "pytest failure must propagate"
grep -Eq "FAIL +tests" "$project/out.log" || fail "failed test check was not identified"

# A failure inside a pipeline or before a later command is not masked.
project="$(setup_project pipeline "lint: ruff check . | cat")"
MOCK_RUFF_EXIT=1 expect_failure "$project" "pipeline failure must propagate"

project="$(setup_project sequence "lint: ruff check .; pytest")"
MOCK_RUFF_EXIT=1 expect_failure "$project" "failure before a later command must propagate"

# A required check whose tool is missing fails and names the check and tool.
project="$(setup_project missing-tool "lint: ruff check ." "types: mypy .")"
expect_failure "$project" "missing required tool must fail"
grep -F "types" "$project/out.log" | grep -F "mypy" >/dev/null ||
  fail "missing tool message did not name the check and tool"

# A required check script that is not executable fails.
project="$(setup_project not-executable "suite: ./suite.sh")"
printf '#!/usr/bin/env bash\nexit 0\n' >"$project/suite.sh"
expect_failure "$project" "non-executable check script must fail"

# Checks run from the repository root, regardless of the caller's directory.
project="$(setup_project cwd "marker: test -f scripts/verify.conf")"
mkdir -p "$project/nested"
(cd "$project/nested" && run_verify "$project") ||
  fail "checks did not run from the repository root"

# Missing, empty, malformed, and duplicate configuration is rejected.
project="$(setup_project no-config)"
expect_failure "$project" "missing configuration must fail"

project="$(setup_project empty-config "# no checks" "")"
expect_failure "$project" "configuration without checks must fail"

project="$(setup_project malformed "lint ruff check .")"
expect_failure "$project" "malformed check line must fail"
[[ ! -e "$project/tools.log" ]] || fail "checks ran despite malformed configuration"

project="$(setup_project duplicate "lint: ruff check ." "lint: pytest")"
expect_failure "$project" "duplicate check name must fail"

# The workflow self-tests live in their own file and run only when a workflow
# file differs from the base branch.
setup_workflow_project() {
  local project

  project="$(setup_project "$1" "lint: ruff check .")"
  mkdir -p "$project/tools" "$project/src"
  printf 'paths: tools .gitignore scripts/verify-workflow.conf\nself-test: pytest\n' \
    >"$project/scripts/verify-workflow.conf"
  printf 'one\n' >"$project/tools/tool.sh"
  printf 'one\n' >"$project/src/app.txt"
  git -C "$project" init -q -b main
  git -C "$project" config user.name "Test User"
  git -C "$project" config user.email "test@example.com"
  git -C "$project" add -A
  git -C "$project" commit -qm "Initial commit"
  git -C "$project" checkout -q -b feature/1-change
  printf '%s\n' "$project"
}

self_tests_ran() {
  grep -Fq "pytest" "$1/tools.log"
}

expect_skipped() {
  local project="$1"
  local description="$2"

  rm -f "$project/tools.log"
  run_verify "$project" || {
    cat "$project/out.log" >&2
    fail "verification failed: $description"
  }
  grep -Fq "ruff" "$project/tools.log" || fail "the project checks did not run: $description"
  if self_tests_ran "$project"; then fail "the self-tests ran although $description"; fi
  grep -Eq "^SKIP +workflow self-tests \(1 checks\)" "$project/out.log" ||
    fail "the skipped self-tests were not reported: $description"
}

expect_ran() {
  local project="$1"
  local description="$2"

  rm -f "$project/tools.log"
  run_verify "$project" ${3+"$3"} || {
    cat "$project/out.log" >&2
    fail "verification failed: $description"
  }
  self_tests_ran "$project" || fail "the self-tests did not run although $description"
  if grep -Fq "SKIP" "$project/out.log"; then fail "a skip was reported although $description"; fi
}

project="$(setup_workflow_project workflow-unchanged)"
expect_skipped "$project" "nothing changed"
printf 'two\n' >>"$project/src/app.txt"
printf 'new\n' >"$project/src/new.txt"
expect_skipped "$project" "only project files changed"
git -C "$project" add -A
git -C "$project" commit -qm "Change the project"
expect_skipped "$project" "only project files were committed"
expect_ran "$project" "--all was given" --all

project="$(setup_workflow_project workflow-uncommitted)"
printf 'two\n' >>"$project/tools/tool.sh"
expect_ran "$project" "a workflow file has an uncommitted change"

project="$(setup_workflow_project workflow-untracked)"
printf 'new\n' >"$project/tools/new.sh"
expect_ran "$project" "a workflow file is new and untracked"

# A path entry can name a single file in the repository root.
project="$(setup_workflow_project workflow-root-file)"
printf 'build/\n' >"$project/.gitignore"
expect_ran "$project" "a guarded file in the repository root is new"

project="$(setup_workflow_project workflow-committed)"
git -C "$project" rm -q tools/tool.sh
git -C "$project" commit -qm "Remove a workflow file"
expect_ran "$project" "a workflow file was removed in a commit"

# A path entry can exclude a file from a guarded directory.
project="$(setup_workflow_project workflow-excluded)"
printf 'paths: tools :(exclude)tools/tool.sh\nself-test: pytest\n' >"$project/scripts/verify-workflow.conf"
git -C "$project" commit -qam "Exclude a file"
git -C "$project" branch -q -f main
printf 'two\n' >>"$project/tools/tool.sh"
expect_skipped "$project" "only an excluded file changed"
printf 'new\n' >"$project/tools/other.sh"
expect_ran "$project" "another file in the guarded directory is new"

# Without a base branch the change cannot be determined, so the self-tests run.
project="$(setup_workflow_project workflow-no-base)"
git -C "$project" branch -q -D main
expect_ran "$project" "there is no base branch"

project="$(setup_project workflow-no-repository "lint: ruff check .")"
printf 'paths: tools\nself-test: pytest\n' >"$project/scripts/verify-workflow.conf"
expect_ran "$project" "the project is not a Git repository"

# A failing self-test fails verification, and a self-test file without paths
# or without checks is rejected.
project="$(setup_workflow_project workflow-fails)"
printf 'two\n' >>"$project/tools/tool.sh"
MOCK_PYTEST_EXIT=1 expect_failure "$project" "a failing self-test must propagate"
grep -Eq "FAIL +self-test" "$project/out.log" || fail "the failed self-test was not identified"

project="$(setup_workflow_project workflow-no-paths)"
printf 'self-test: pytest\n' >"$project/scripts/verify-workflow.conf"
expect_failure "$project" "self-tests without paths must fail"

project="$(setup_workflow_project workflow-no-checks)"
printf 'paths: tools\n' >"$project/scripts/verify-workflow.conf"
expect_failure "$project" "a self-test file without checks must fail"

project="$(setup_workflow_project workflow-duplicate)"
printf 'paths: tools\nlint: pytest\n' >"$project/scripts/verify-workflow.conf"
expect_failure "$project" "a check name used in both files must fail"

# A run in which every check passed is recorded for the content it verified,
# and --reuse skips a second run on exactly that content.
setup_recorded_project() {
  local project

  project="$(setup_project "$1" "lint: ruff check .")"
  mkdir -p "$project/scripts/lib" "$project/src"
  cp "$source_root/scripts/lib/fingerprint.sh" "$source_root/scripts/lib/verification.sh" "$project/scripts/lib/"
  printf '*.log\n.agents/verification/\n' >"$project/.gitignore"
  printf 'one\n' >"$project/src/app.txt"
  git -C "$project" init -q -b main
  git -C "$project" config user.name "Test User"
  git -C "$project" config user.email "test@example.com"
  git -C "$project" add -A
  git -C "$project" commit -qm "Initial commit"
  printf '%s\n' "$project"
}

record="/.agents/verification/passed"

# run_checks <project> <description> [option...]: the checks must really run.
expect_checks_ran() {
  local project="$1"
  local description="$2"

  shift 2
  rm -f "$project/tools.log"
  PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
    "$project/scripts/verify.sh" "$@" >"$project/out.log" 2>&1 || {
    cat "$project/out.log" >&2
    fail "verification failed: $description"
  }
  grep -Fq "ruff" "$project/tools.log" 2>/dev/null || fail "the checks did not run although $description"
}

expect_reused() {
  local project="$1"
  local description="$2"

  shift 2
  rm -f "$project/tools.log"
  PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
    "$project/scripts/verify.sh" "$@" >"$project/out.log" 2>&1 || {
    cat "$project/out.log" >&2
    fail "a reused verification failed: $description"
  }
  [[ ! -e "$project/tools.log" ]] || fail "the checks ran again although $description"
  grep -Fq "already passed" "$project/out.log" || fail "the reuse was not reported: $description"
}

project="$(setup_recorded_project recorded)"
expect_checks_ran "$project" "nothing was recorded yet" --reuse
[[ -f "$project$record" ]] || fail "a passed run was not recorded"
[[ -z "$(git -C "$project" status --porcelain)" ]] || fail "the record changed the working tree"
expect_reused "$project" "the content is unchanged" --reuse
expect_checks_ran "$project" "--reuse was not given"
printf 'two\n' >>"$project/src/app.txt"
expect_checks_ran "$project" "a tracked file changed" --reuse
expect_reused "$project" "the changed content was verified" --reuse
printf 'new\n' >"$project/src/new.txt"
expect_checks_ran "$project" "an untracked file was added" --reuse
git -C "$project" add -A
git -C "$project" commit -qm "Commit the same content"
expect_reused "$project" "the same content was only committed" --reuse

# A failing run records nothing and removes an earlier record.
if MOCK_RUFF_EXIT=1 run_verify "$project"; then fail "a failing run returned success"; fi
[[ ! -e "$project$record" ]] || fail "a failing run left a record"
expect_checks_ran "$project" "the last run failed" --reuse

# A run whose check changes a file verified no single content.
project="$(setup_recorded_project self-modifying)"
printf 'touch: date >>src/app.txt\n' >"$project/scripts/verify.conf"
run_verify "$project" || fail "a run whose check changes a file failed"
[[ ! -e "$project$record" ]] || fail "a run that changed the content was recorded"

# Without the ignore rule the record would become part of the content, so
# none is written.
project="$(setup_recorded_project not-ignored)"
printf '*.log\n' >"$project/.gitignore"
git -C "$project" commit -qam "Drop the ignore rule"
expect_checks_ran "$project" "no record can be kept" --reuse
[[ ! -e "$project$record" ]] || fail "a record was written where Git does not ignore it"
expect_checks_ran "$project" "no record can be kept" --reuse

# A record made without the workflow self-tests does not cover --all.
project="$(setup_workflow_project recorded-workflow)"
mkdir -p "$project/scripts/lib"
cp "$source_root/scripts/lib/fingerprint.sh" "$source_root/scripts/lib/verification.sh" "$project/scripts/lib/"
printf 'paths: tools\nself-test: pytest\n' >"$project/scripts/verify-workflow.conf"
printf '*.log\n.agents/verification/\n' >"$project/.gitignore"
git -C "$project" add -A
git -C "$project" commit -qm "Keep verification records"
git -C "$project" branch -q -f main
expect_checks_ran "$project" "nothing was recorded yet" --reuse
if self_tests_ran "$project"; then fail "the self-tests ran although no workflow file changed"; fi
expect_reused "$project" "the content is unchanged" --reuse
# --reuse-only makes the same decision and runs nothing (Issue #389): status
# 0 where --reuse would reuse, 3 where it would run, here because the record
# was made without the self-tests that --all requires.
reuse_only() {
  reuse_status=0
  rm -f "$project/tools.log"
  PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
    "$project/scripts/verify.sh" --reuse-only "$@" >"$project/out.log" 2>&1 || reuse_status=$?
  [[ ! -e "$project/tools.log" ]] || fail "--reuse-only ran a check"
}
reuse_only
[[ "$reuse_status" -eq 0 ]] || fail "--reuse-only did not take the pass that --reuse takes"
reuse_only --all
[[ "$reuse_status" -eq 3 ]] || fail "--reuse-only took a pass made without the self-tests that --all requires"
grep -Fq "nothing was run" "$project/out.log" || fail "--reuse-only did not say that it ran nothing"
reuse_only --targeted
[[ "$reuse_status" -eq 1 ]] || fail "--reuse-only was accepted together with --targeted"
expect_checks_ran "$project" "the record does not include the self-tests" --reuse --all
self_tests_ran "$project" || fail "--all with --reuse did not run the self-tests"
expect_reused "$project" "the self-tests were included in the record" --reuse --all
expect_reused "$project" "a complete record covers a plain run" --reuse
reuse_only --all
[[ "$reuse_status" -eq 0 ]] || fail "--reuse-only did not take a record that includes the self-tests"

project="$(setup_project unknown-option "lint: ruff check .")"
if PATH="$tmp/bin:/usr/bin:/bin" "$project/scripts/verify.sh" --everything >"$project/out.log" 2>&1; then
  fail "an unknown option was accepted"
fi
[[ ! -e "$project/tools.log" ]] || fail "checks ran despite an unknown option"

# Groups: a check may name one, and --only runs the checks of the named
# groups. run_with <project> [option...] runs verify.sh with a fresh tool log.
# It runs the groups one after the other (VERIFY_JOBS=1) unless the caller
# sets VERIFY_JOBS, so that the tests of the selection and the tiers can
# compare the order of the commands; the groups at the same time are tested
# below, against this order.
run_with() {
  local project="$1"

  shift
  rm -f "$project/tools.log"
  VERIFY_JOBS="${VERIFY_JOBS:-1}" PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
    "$project/scripts/verify.sh" "$@" >"$project/out.log" 2>&1
}

# ran <project>: the commands that ran, on one line.
ran() {
  [[ -e "$1/tools.log" ]] || return 0
  tr '\n' ';' <"$1/tools.log"
}

project="$(setup_project groups "lint [code]: ruff check ." "tests[code]: pytest unit" \
  "slow  [e2e-1]: pytest e2e" "plain: ruff plain")"

# Without --only every check runs, as before.
run_with "$project" || fail "a configuration with groups failed"
[[ "$(ran "$project")" == "ruff check .;pytest unit;pytest e2e;ruff plain;" ]] ||
  fail "not every check ran without --only: $(ran "$project")"

run_with "$project" --groups || fail "--groups failed"
[[ "$(tr '\n' ',' <"$project/out.log")" == "code,e2e-1,default," ]] ||
  fail "--groups did not print the groups in the order of their first check: $(cat "$project/out.log")"
[[ ! -e "$project/tools.log" ]] || fail "--groups ran a check"

run_with "$project" --only code || fail "--only with one group failed"
[[ "$(ran "$project")" == "ruff check .;pytest unit;" ]] || fail "--only code ran: $(ran "$project")"
grep -Fq "Not a verification" "$project/out.log" || fail "a partial run did not say that it is not a verification"
if grep -Fq "Verification passed" "$project/out.log"; then fail "a partial run reported a passed verification"; fi

# A check without a group is in 'default', and several groups run in the
# order of the file, not of the option.
run_with "$project" --only default,code || fail "--only with two groups failed"
[[ "$(ran "$project")" == "ruff check .;pytest unit;ruff plain;" ]] || fail "--only default,code ran: $(ran "$project")"

if run_with "$project" --only code,nope; then fail "an unknown group was accepted"; fi
grep -Fq "no check is in the group 'nope'" "$project/out.log" || fail "the unknown group was not named"
[[ ! -e "$project/tools.log" ]] || fail "a check ran although a group was unknown"
if run_with "$project" --only; then fail "--only without a group was accepted"; fi
if run_with "$project" --only "Code"; then fail "a group name with a capital was accepted"; fi
if run_with "$project" --only code --reuse; then fail "--only was accepted together with --reuse"; fi
grep -Fq "nothing to reuse" "$project/out.log" || fail "the refusal of --reuse did not say why"

# A failing check of a selected group fails the partial run; a failing check
# of another group does not.
if MOCK_PYTEST_EXIT=1 run_with "$project" --only code; then fail "a failing check of the group passed"; fi
MOCK_PYTEST_EXIT=1 run_with "$project" --only default || fail "a failing check of another group failed the run"

# A malformed group is a malformed line.
project="$(setup_project bad-group "lint [Code]: ruff check .")"
expect_failure "$project" "a group name with a capital must fail"
project="$(setup_project empty-group "lint []: ruff check .")"
expect_failure "$project" "an empty group must fail"

# A partial run is never a verification: it records nothing, whichever
# groups it runs, and it leaves a record of a complete run alone. A failing
# partial run removes the record, like any failing run.
project="$(setup_recorded_project partial)"
printf '%s\n' "lint [code]: ruff check ." "tests: pytest" >"$project/scripts/verify.conf"
git -C "$project" commit -qam "Give a check a group"
for group in code default code,default; do
  run_with "$project" --only "$group" || fail "--only $group failed"
  [[ ! -e "$project$record" ]] || fail "a partial run of '$group' recorded a passed verification"
done
run_with "$project" --reuse || fail "a complete run failed"
[[ "$(ran "$project")" == "ruff check .;pytest ;" ]] || fail "--reuse took partial runs for a verification: $(ran "$project")"
[[ -f "$project$record" ]] || fail "a complete run was not recorded"
before="$(cat "$project$record")"
run_with "$project" --only code || fail "a partial run after a complete one failed"
[[ "$(cat "$project$record")" == "$before" ]] || fail "a passing partial run changed the record of a complete run"
if MOCK_RUFF_EXIT=1 run_with "$project" --only code; then fail "a failing partial run returned success"; fi
[[ ! -e "$project$record" ]] || fail "a failing partial run left the record of a passed verification"

# The workflow self-tests have groups too, and keep their own rule: they run
# when a workflow file changed, or with --all.
project="$(setup_workflow_project workflow-groups)"
printf '%s\n' "lint [code]: ruff check ." >"$project/scripts/verify.conf"
printf '%s\n' "paths: scripts" "selftest [workflow]: pytest selftest" >"$project/scripts/verify-workflow.conf"
git -C "$project" add -A
git -C "$project" commit -qm "Group the checks"
git -C "$project" branch -f main HEAD
run_with "$project" --groups || fail "--groups failed with workflow self-tests"
[[ "$(tr '\n' ',' <"$project/out.log")" == "code,workflow," ]] || fail "--groups left out the group of a self-test"
run_with "$project" --only workflow || fail "--only workflow failed"
[[ ! -e "$project/tools.log" ]] || fail "--only ran a self-test although no workflow file changed"
grep -Fq "SKIP  workflow self-tests" "$project/out.log" || fail "the skipped self-tests were not reported"
run_with "$project" --all --only workflow || fail "--all --only workflow failed"
[[ "$(ran "$project")" == "pytest selftest;" ]] || fail "--all --only workflow ran: $(ran "$project")"
run_with "$project" --all --only code || fail "--all --only code failed"
[[ "$(ran "$project")" == "ruff check .;" ]] || fail "--all --only code ran a self-test: $(ran "$project")"

# A check name is unique across both files, also when the two checks name
# different groups: the name identifies the check in the summary.
project="$(setup_workflow_project same-name-groups)"
printf '%s\n' "lint [code]: ruff check ." >"$project/scripts/verify.conf"
printf '%s\n' "paths: scripts" "lint [workflow]: pytest selftest" >"$project/scripts/verify-workflow.conf"
if run_with "$project" --all; then fail "the same check name in both files, in different groups, was accepted"; fi
grep -Fq "duplicate check name" "$project/out.log" || fail "the duplicate name was not reported"
[[ ! -e "$project/tools.log" ]] || fail "a check ran although a check name is used twice"
if run_with "$project" --groups; then fail "--groups accepted a duplicate check name"; fi

# The tiers (ADR 017 decision 7). A project without the entry 'targeted:' has
# one tier: --targeted runs every check, and --reuse --targeted reuses a pass.
project="$(setup_recorded_project one-tier)"
printf '%s\n' "lint [code]: ruff check ." "tests: pytest" >"$project/scripts/verify.conf"
git -C "$project" commit -qam "Two groups, one tier"
run_with "$project" --targeted || fail "--targeted failed in a project with one tier"
[[ "$(ran "$project")" == "ruff check .;pytest ;" ]] || fail "--targeted without the entry did not run every check: $(ran "$project")"
grep -Fq "one tier" "$project/out.log" || fail "the one tier was not reported"
grep -Fq "tier: full" "$project$record" || fail "the run was not recorded as a full run: $(cat "$project$record")"
run_with "$project" --reuse --targeted || fail "--reuse --targeted failed"
[[ ! -e "$project/tools.log" ]] || fail "--reuse --targeted ran the checks again"
grep -Fq "a full run" "$project/out.log" || fail "the reused tier was not reported"

# With the entry, the targeted run performs the groups it names after the
# selection against the base, and records the tier, the base, and the
# selection. The selection is made by the project's module, faked here, and
# the base is retrieved by scripts/fetch-base.sh, faked here.
setup_tiered_project() {
  local project

  project="$(setup_recorded_project "$1")"
  printf '%s\n' "targeted: default,code" "lint [code]: ruff check ." "plain: ruff plain" \
    "build [build]: pytest build" >"$project/scripts/verify.conf"
  cat >"$project/scripts/fetch-base.sh" <<'FETCH'
#!/usr/bin/env bash
mkdir -p "$1"
if [[ "${MOCK_BASE:-accepted}" == accepted ]]; then
  echo "Base accepted: the artifact of the push run 77 on main, whose job verify succeeded."
  printf 'accepted=true\nrun-id=%s\n' "${MOCK_RUN:-77}" >>"$GITHUB_OUTPUT"
else
  echo "No base: no run offers a base. Every lesson is executed and checked."
  printf 'accepted=false\nrun-id=\n' >>"$GITHUB_OUTPUT"
fi
FETCH
  chmod +x "$project/scripts/fetch-base.sh"
  git -C "$project" add -A
  git -C "$project" commit -qm "Tiers"
  printf '%s\n' "$project"
}
# The fake selection module: 'uv run --locked python -m pbc.authoring.selection
# --root <root> --base <base> [--tier targeted]' writes the selection and
# prints its summary; MOCK_SELECTION is 'selective', 'full', or 'new'.
cat >"$tmp/bin/uv" <<'UV'
#!/usr/bin/env bash
echo "uv $*" >>"$MOCK_TOOL_LOG"
root=""; tier=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) root="$2"; shift ;;
    --tier) tier="$2"; shift ;;
  esac
  shift
done
mkdir -p "$root/.agents/verification"
printf '{"format": 1, "mode": "%s"}\n' "${MOCK_SELECTION:-selective}" >"$root/.agents/verification/selection.json"
case "${MOCK_SELECTION:-selective}" in
  selective) echo "selective run against base abc: ${MOCK_LESSONS:-1} of 2 lessons executed, 1 restored" ;;
  full) echo "full run, base abc: the checks changed since the base (identity differs) (2 of 2 lessons executed)"
        [[ "$tier" != targeted ]] || { echo "CI will run everything: the checks changed. The targeted run does not select; run the full ./scripts/verify.sh."; exit 3; } ;;
  new) echo "selective run against base abc: 1 of 2 lessons executed, 1 restored"
       [[ "$tier" != targeted ]] || { echo "1 new lesson(s) change what other pages display; run ./scripts/verify.sh --base."; exit 3; } ;;
esac
UV
chmod +x "$tmp/bin/uv"

project="$(setup_tiered_project tiered)"
# verify.sh resolves its root, so the paths it passes on are the resolved ones.
resolved="$(cd "$project" && pwd -P)"
selection_call="uv run --locked python -m pbc.authoring.selection --root $resolved --base $resolved/.agents/verification/base"
run_with "$project" --targeted || {
  cat "$project/out.log" >&2
  fail "the targeted run failed"
}
[[ "$(ran "$project")" == "$selection_call --tier targeted;ruff check .;ruff plain;" ]] ||
  fail "the targeted run did not perform exactly the selection and the groups of its entry: $(ran "$project")"
grep -Fq "Base accepted" "$project/out.log" || fail "the base was not retrieved"
grep -Fq "Verification passed (targeted run)" "$project/out.log" || fail "the targeted pass was not reported"
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "targeted" ]] || fail "the tier was not recorded: $(cat "$project$record")"
[[ "$(sed -n 's/^base: //p' "$project$record")" == "run 77" ]] || fail "the base was not recorded: $(cat "$project$record")"
grep -Fq "selection: selective run against base abc" "$project$record" || fail "the selection was not recorded"
run_with "$project" --reuse --targeted || fail "--reuse --targeted failed after a targeted pass"
[[ "$(ran "$project")" == "$selection_call --tier targeted;" ]] ||
  fail "a recorded targeted pass was reused without the current selection, or a check ran again: $(ran "$project")"
grep -Fq "against this base and selection" "$project/out.log" || fail "the reuse did not say that base and selection match"
# Main advanced (another base) with the tree unchanged: the pass does not stand.
MOCK_RUN=78 run_with "$project" --reuse --targeted || fail "--reuse --targeted failed on a newer base"
[[ "$(ran "$project")" == "$selection_call --tier targeted;ruff check .;ruff plain;" ]] ||
  fail "a targeted pass of an older base was reused: $(ran "$project")"
grep -Fq "another base or selection" "$project/out.log" || fail "the rerun was not explained"
[[ "$(sed -n 's/^base: //p' "$project$record")" == "run 78" ]] || fail "the new base was not recorded: $(cat "$project$record")"
# The same base, a different selection: rerun.
MOCK_LESSONS=2 run_with "$project" --reuse --targeted || fail "--reuse --targeted failed on another selection"
[[ "$(ran "$project")" == "$selection_call --tier targeted;ruff check .;ruff plain;" ]] ||
  fail "a targeted pass of another selection was reused: $(ran "$project")"
# No acceptable base: the pass does not stand, CI will run everything.
if MOCK_BASE=none run_with "$project" --reuse --targeted; then fail "a targeted pass was reused without a base"; fi
[[ "$(ran "$project")" == "" ]] || fail "a check ran without a base: $(ran "$project")"
MOCK_LESSONS=1 MOCK_RUN=77 run_with "$project" --targeted || fail "the targeted run failed"
run_with "$project" --reuse || fail "--reuse after a targeted pass failed"
[[ "$(ran "$project")" == "ruff check .;ruff plain;pytest build;" ]] || fail "--reuse took a targeted pass for a full verification: $(ran "$project")"
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "full" ]] || fail "the full run was not recorded as such"

# Without an acceptable base, or when the selection names a full run or a new
# lesson, the targeted run reports what CI will run and verifies nothing.
if MOCK_BASE=none run_with "$project" --targeted; then fail "the targeted run passed without a base"; fi
grep -Fq "CI will run everything" "$project/out.log" || fail "the missing base was not reported as a full run of CI"
grep -Fq "REFUSED  targeted-run" "$project/out.log" || fail "the refusal was not in the summary"
[[ "$(ran "$project")" == "" ]] || fail "a check ran without a base: $(ran "$project")"
# A refusal says nothing about the content: the record of the full run stands.
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "full" ]] || fail "a refused targeted run changed the record of the full run"
if MOCK_SELECTION=full run_with "$project" --targeted; then fail "the targeted run passed on a full selection"; fi
grep -Fq "run the full ./scripts/verify.sh" "$project/out.log" || fail "the full run was not named"
[[ "$(ran "$project")" == "$selection_call --tier targeted;" ]] ||
  fail "a check ran on a full selection: $(ran "$project")"
if MOCK_SELECTION=new run_with "$project" --targeted; then fail "the targeted run passed on a new lesson"; fi
grep -Fq "run ./scripts/verify.sh --base" "$project/out.log" || fail "the run with a base was not named"

# --base without a directory retrieves the base; without one it is a full run.
MOCK_BASE=none run_with "$project" --base || fail "--base without a base failed"
[[ "$(ran "$project")" == "ruff check .;ruff plain;pytest build;" ]] || fail "--base without a base did not run every check: $(ran "$project")"
grep -Fq "full run" "$project/out.log" || fail "the full run was not reported"
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "full" ]] || fail "the run without a base was not recorded as full"
run_with "$project" --base || fail "--base with a retrieved base failed"
[[ "$(ran "$project")" == "$selection_call;ruff check .;ruff plain;pytest build;" ]] ||
  fail "--base did not select and run every check: $(ran "$project")"
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "base" ]] || fail "the run with a base was not recorded as such"

# The entry is checked: a group without a check, a duplicate, a group on it.
if run_with "$project" --targeted --only code; then fail "--targeted was accepted with --only"; fi
if run_with "$project" --targeted --base; then fail "--targeted was accepted with --base without a directory"; fi
printf '%s\n' "targeted: code,nope" "lint [code]: ruff check ." >"$project/scripts/verify.conf"
if run_with "$project" --targeted; then fail "a targeted entry naming an unknown group was accepted"; fi
grep -Fq "'nope'" "$project/out.log" || fail "the unknown group of the entry was not named"
run_with "$project" || fail "a plain run failed because of the targeted entry"
printf '%s\n' "targeted: code" "targeted: default" "lint [code]: ruff check ." >"$project/scripts/verify.conf"
expect_failure "$project" "a duplicate targeted entry must fail"
printf '%s\n' "targeted [code]: code" "lint [code]: ruff check ." >"$project/scripts/verify.conf"
expect_failure "$project" "a targeted entry with a group must fail"
printf '%s\n' "targeted: Code" "lint [code]: ruff check ." >"$project/scripts/verify.conf"
expect_failure "$project" "a targeted entry with a malformed group must fail"
# The tiers with the groups at the same time: the selection first, then the
# same checks as one after the other, and the same record.
project="$(setup_tiered_project tiered-parallel)"
resolved="$(cd "$project" && pwd -P)"
selection_call="uv run --locked python -m pbc.authoring.selection --root $resolved --base $resolved/.agents/verification/base"
for option in --targeted --base; do
  VERIFY_JOBS=4 run_with "$project" "$option" || {
    cat "$project/out.log" >&2
    fail "$option with the groups at the same time failed"
  }
  expected_call="$selection_call"
  expected_checks="$(printf '%s\n' "ruff check ." "ruff plain")"
  expected_tier="base"
  if [[ "$option" == --targeted ]]; then
    expected_call="$selection_call --tier targeted"
    expected_tier="targeted"
  else
    expected_checks="$(printf '%s\n' "pytest build" "ruff check ." "ruff plain")"
  fi
  [[ "$(head -n 1 "$project/tools.log")" == "$expected_call" ]] ||
    fail "$option at the same time did not select first: $(ran "$project")"
  [[ "$(tail -n +2 "$project/tools.log" | sort)" == "$expected_checks" ]] ||
    fail "$option at the same time ran other checks: $(ran "$project")"
  grep -Fq "run at the same time" "$project/out.log" || fail "$option did not run its groups at the same time"
  [[ "$(sed -n 's/^tier: //p' "$project$record")" == "$expected_tier" ]] ||
    fail "$option at the same time was not recorded as such: $(cat "$project$record")"
done
rm -f "$tmp/bin/uv"

# The groups at the same time (Issue #430). run_jobs <jobs> <project>
# [option...] runs verify.sh with VERIFY_JOBS=<jobs>.
run_jobs() {
  local jobs="$1"

  shift
  VERIFY_JOBS="$jobs" run_with "$@"
}

# summary <project>: the summary of the last run, from its heading on.
summary() {
  sed -n '/^== Verification summary ==$/,$p' "$1/out.log"
}

project="$(setup_project parallel "a1 [a]: ruff a1" "b1 [b]: pytest b1" "a2 [a]: ruff a2" \
  "c1 [c]: ruff c1" "plain: pytest plain" "after [c]: a1")"
logs="$project/.agents/verification/logs"

# The same checks run as one after the other, and the summary is the same, in
# the order of the file; inside a group the checks keep that order.
run_jobs 1 "$project" || fail "the groups one after the other failed"
sequential_runs="$(sort "$project/tools.log")"
sequential_summary="$(summary "$project")"
grep -Fq "one after the other (VERIFY_JOBS=1)" "$project/out.log" || fail "VERIFY_JOBS=1 did not say that the groups run one after the other"
[[ ! -d "$logs" ]] || fail "the groups one after the other wrote group logs"
run_jobs 4 "$project" || {
  cat "$project/out.log" >&2
  fail "the groups at the same time failed"
}
[[ "$(sort "$project/tools.log")" == "$sequential_runs" ]] ||
  fail "the groups at the same time ran other checks: $(ran "$project")"
[[ "$(summary "$project")" == "$sequential_summary" ]] ||
  fail "the summary of the groups at the same time differs: $(summary "$project")"
[[ "$(grep -E '^ruff a[12]$' "$project/tools.log" | tr '\n' ';')" == "ruff a1;ruff a2;" ]] ||
  fail "the checks of a group did not keep the order of the file: $(ran "$project")"
for group in a b c default; do
  [[ -f "$logs/$group.log" ]] || fail "the group $group has no log"
done
grep -Fq -- "-- a2: ruff a2" "$logs/a.log" || fail "the log of the group a misses its check"
if grep -Fq -- "-- b1" "$logs/a.log"; then fail "the log of the group a holds a check of another group"; fi
grep -Fq "at most 4 at a time" "$project/out.log" || fail "the parallel run did not say its limit"
grep -Fq "Verification passed." "$project/out.log" || fail "the parallel run did not report the pass"
VERIFY_JOBS=4 run_with "$project" --groups || fail "--groups failed with an entry 'after'"
[[ "$(tr '\n' ',' <"$project/out.log")" == "a,b,c,default," ]] ||
  fail "an entry 'after' changed the groups: $(cat "$project/out.log")"

# A failure in one group of a parallel wave fails the run; the other groups
# still run, and every log remains.
if MOCK_PYTEST_EXIT=1 run_jobs 4 "$project"; then fail "a failing group of a parallel wave passed the run"; fi
grep -Eq "^FAIL +b1 \(exit 1\)$" "$project/out.log" || fail "the failing check of the wave was not named"
grep -Eq "^PASS +c1$" "$project/out.log" || fail "a group beside the failing one did not pass"
[[ "$(sort "$project/tools.log")" == "$sequential_runs" ]] || fail "a failure stopped other checks: $(ran "$project")"
for group in a b c default; do
  [[ -f "$logs/$group.log" ]] || fail "the log of the group $group did not remain after a failure"
done
grep -Fq "failed with status 1" "$logs/b.log" || fail "the log of the failing group does not say so"
grep -Fq "Verification failed." "$project/out.log" || fail "the failing parallel run did not report the failure"

# The groups really run at the same time: each check waits for the other to
# have started, which one after the other never happens.
waiter() {
  printf '%s [%s]: touch %s.started; n=0; while [ ! -e %s.started ]; do n=$((n + 1)); [ "$n" -lt 30 ] || exit 1; sleep 0.1; done' "$1" "$1" "$1" "$2"
}
project="$(setup_project overlap "$(waiter x y)" "$(waiter y x)")"
run_jobs 2 "$project" || {
  cat "$project/out.log" >&2
  fail "two independent groups did not run at the same time"
}
rm -f "$project"/*.started
if run_jobs 1 "$project"; then fail "VERIFY_JOBS=1 ran two groups at the same time"; fi

# A group that waits for a check starts only after that check finished, and
# does not wait for the rest of the check's group: here 'later' of the group
# b needs the group e to have run while it waits.
project="$(setup_project depends "build [b]: sleep 1; touch built" \
  'later [b]: sleep 0; n=0; while [ ! -e checked ]; do n=$((n + 1)); [ "$n" -lt 30 ] || exit 1; sleep 0.1; done' \
  "e2e [e]: test -e built && touch checked" "after [e]: build")"
run_jobs 4 "$project" || {
  cat "$project/out.log" >&2
  fail "a group that waits for a check did not start after it, or waited for its whole group"
}
# Without the entry the group starts at once, and the same check fails.
rm -f "$project/built" "$project/checked"
printf '%s\n' "build [b]: sleep 1; touch built" "e2e [e]: test -e built" >"$project/scripts/verify.conf"
if run_jobs 4 "$project"; then fail "a group without an entry 'after' waited for another"; fi
grep -Eq "^FAIL +e2e" "$project/out.log" || fail "the check that started too early did not fail"

# A check of a group outside the run is not waited for (--only, where CI
# prepares the group's input), and a dependent group of a failed check still
# runs, as it would one after the other.
printf '%s\n' "build [b]: false" "e2e [e]: ruff e2e" "other [o]: ruff other" "after [e]: build" >"$project/scripts/verify.conf"
run_jobs 4 "$project" --only e,o || fail "a group waited for a check outside the run"
[[ "$(sort "$project/tools.log" | tr '\n' ';')" == "ruff e2e;ruff other;" ]] || fail "--only e,o ran: $(ran "$project")"
if run_jobs 4 "$project"; then fail "a failing prerequisite passed the run"; fi
grep -Fq "ruff e2e" "$project/tools.log" || fail "the group after a failed check did not run"

# VERIFY_JOBS limits the groups that run at the same time.
counter() {
  printf '%s [%s]: mkdir -p running && touch running/%s && ls running | wc -l >>counts && sleep 0.5 && rm running/%s' "$1" "$1" "$1" "$1"
}
project="$(setup_project limit "$(counter p)" "$(counter q)" "$(counter r)")"
run_jobs 2 "$project" || {
  cat "$project/out.log" >&2
  fail "a run limited to two groups failed"
}
[[ "$(grep -c . "$project/counts")" -eq 3 ]] || fail "not every group of the limited run ran"
[[ "$(sort -n "$project/counts" | tail -n 1 | tr -d ' ')" -le 2 ]] ||
  fail "more groups ran at the same time than VERIFY_JOBS allows: $(tr '\n' ' ' <"$project/counts")"

# A TERM to the run stops the groups still running and the processes they
# started, and the run fails.
sleeper() {
  printf "%s [%s]: sh -c 'echo \$\$ >%s.pid; exec sleep 30'" "$1" "$1" "$1"
}
project="$(setup_project interrupt "$(sleeper s)" "$(sleeper t)")"
VERIFY_JOBS=4 PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
  "$project/scripts/verify.sh" >"$project/out.log" 2>&1 &
verify_pid=$!
n=0
until [[ -s "$project/s.pid" && -s "$project/t.pid" ]]; do
  n=$((n + 1))
  [[ "$n" -lt 100 ]] || fail "the groups of the interrupted run did not start"
  sleep 0.1
done
kill -TERM "$verify_pid"
interrupt_status=0
wait "$verify_pid" || interrupt_status=$?
[[ "$interrupt_status" -ne 0 ]] || fail "an interrupted run passed"
for check in s t; do
  if kill -0 "$(cat "$project/$check.pid")" 2>/dev/null; then
    kill "$(cat "$project/$check.pid")" 2>/dev/null || true
    fail "the check $check kept running after the run was stopped"
  fi
done

# A group whose process disappears without finishing (here its check kills
# it with SIGKILL, so it writes no end marker) fails the run with a message
# that names the group and the signal; the run ends, a group that waits for
# its check never starts, and a group beside it still runs. The run gets a
# time limit, so that a scheduler that waits for the marker alone fails the
# test instead of hanging it. The group process is the check's ancestor whose
# parent is verify.sh: how many processes lie between differs by bash (bash 5
# replaces the subshell of run_checks with the check's shell, bash 3.2 does
# not), so the check walks up to it from verify.sh's pid, which the test
# writes, and never kills verify.sh itself.
project="$(setup_project killed \
  'doomed [k]: until [ -s verify.pid ]; do sleep 0.1; done; v="$(cat verify.pid)"; p="$PPID"; while q="$(ps -o ppid= -p "$p" | tr -d " ")"; [ "$q" != "$v" ]; do [ "${q:-1}" -gt 1 ] || exit 3; p="$q"; done; kill -KILL "$p"; sleep 1' \
  "next [k]: ruff next" "dependent [d]: ruff dependent" "beside [o]: pytest beside" \
  "after [d]: doomed")"
rm -f "$project/tools.log" "$project/verify.pid"
VERIFY_JOBS=4 PATH="$tmp/bin:/usr/bin:/bin" MOCK_TOOL_LOG="$project/tools.log" \
  "$project/scripts/verify.sh" >"$project/out.log" 2>&1 &
verify_pid=$!
printf '%s\n' "$verify_pid" >"$project/verify.pid.tmp" && mv "$project/verify.pid.tmp" "$project/verify.pid"
n=0
while kill -0 "$verify_pid" 2>/dev/null; do
  n=$((n + 1))
  if [[ "$n" -ge 200 ]]; then
    kill -TERM "$verify_pid" 2>/dev/null || true
    wait "$verify_pid" 2>/dev/null || true
    fail "the run did not end after a group process was killed: $(tail -n 5 "$project/out.log" | tr '\n' ' ')"
  fi
  sleep 0.1
done
killed_status=0
wait "$verify_pid" || killed_status=$?
[[ "$killed_status" -ne 0 ]] || fail "a run whose group process was killed passed"
grep -Fq "the process of the group k was killed by signal 9 (KILL)" "$project/out.log" ||
  fail "the killed group was not named with its signal: $(cat "$project/out.log")"
grep -Eq "^FAIL +doomed \(the process of the group k was killed by signal 9" "$project/out.log" ||
  fail "the summary does not fail the check of the killed group"
grep -Eq "^FAIL +dependent \(not started: the group d waits for 'doomed' of the group k" "$project/out.log" ||
  fail "the summary does not say that the dependent group did not start"
grep -Eq "^PASS +beside$" "$project/out.log" || fail "the group beside the killed one did not pass"
grep -Fq "Verification failed." "$project/out.log" || fail "the run with a killed group did not report the failure"
grep -Fq "killed by signal 9" "$project/.agents/verification/logs/k.log" ||
  fail "the log of the killed group does not say how it ended"
if grep -Fq "ruff dependent" "$project/tools.log" 2>/dev/null; then fail "the dependent group of a killed group started"; fi
if grep -Fq "ruff next" "$project/tools.log" 2>/dev/null; then fail "the killed group went on with its next check"; fi
grep -Fq "pytest beside" "$project/tools.log" || fail "the group beside the killed one did not run"

# VERIFY_JOBS is a whole number of at least 1.
for jobs in 0 x -1 "2 3"; do
  if run_jobs "$jobs" "$project"; then fail "VERIFY_JOBS='$jobs' was accepted"; fi
  grep -Fq "VERIFY_JOBS must be" "$project/out.log" || fail "VERIFY_JOBS='$jobs' was not explained"
done

# The entries 'after' are checked: a group, checks of scripts/verify.conf in
# other groups, and no circle.
bad_after() {
  local description="$1"

  shift
  printf '%s\n' "$@" >"$project/scripts/verify.conf"
  rm -f "$project/tools.log"
  if run_jobs 4 "$project"; then fail "an entry 'after' with $description was accepted"; fi
  [[ ! -e "$project/tools.log" ]] || fail "checks ran despite an entry 'after' with $description"
}
bad_after "no group" "a1 [a]: ruff a1" "b1 [b]: ruff b1" "after: a1"
bad_after "an unknown group" "a1 [a]: ruff a1" "after [nope]: a1"
grep -Fq "'nope'" "$project/out.log" || fail "the unknown group of 'after' was not named"
bad_after "an unknown check" "a1 [a]: ruff a1" "b1 [b]: ruff b1" "after [b]: nope"
grep -Fq "'nope'" "$project/out.log" || fail "the unknown check of 'after' was not named"
bad_after "a check of its own group" "a1 [a]: ruff a1" "a2 [a]: ruff a2" "after [a]: a1"
bad_after "a malformed check list" "a1 [a]: ruff a1" "b1 [b]: ruff b1" "after [b]: a1 b1"
bad_after "a circle" "a1 [a]: ruff a1" "b1 [b]: ruff b1" "after [a]: b1" "after [b]: a1"
grep -Fq "wait for each other" "$project/out.log" || fail "the circle of 'after' was not named"

# A parallel run is recorded like one after the other, and its logs, which
# Git ignores, do not change the content it verified.
project="$(setup_recorded_project recorded-parallel)"
printf '%s\n' "lint [a]: ruff check ." "tests [b]: pytest" >"$project/scripts/verify.conf"
git -C "$project" add -A
git -C "$project" commit -qm "Two groups"
VERIFY_JOBS=4 expect_checks_ran "$project" "nothing was recorded yet" --reuse
[[ -f "$project/.agents/verification/logs/a.log" ]] || fail "the recorded parallel run wrote no group log"
[[ "$(sed -n 's/^tier: //p' "$project$record")" == "full" ]] || fail "the parallel run was not recorded as a full run"
VERIFY_JOBS=4 expect_reused "$project" "the parallel run verified this content" --reuse

# The self-tests give the same result beside other groups as alone. A pipe
# into 'grep -q' does not: grep ends at its first match, and when the writer
# still has output (bash writes printf's lines one by one), the writer dies of
# SIGPIPE and, under pipefail, the assertion fails although it holds. Loaded by
# groups at the same time, this failed risk-level, risk-workflow and
# merge-feature (#430). The workflow scripts under scripts/ take their
# decisions the same way, and there a missed match fails open: merge-feature.sh
# dropped a reason why the merge needs the owner's approval (#452). A pipe
# that goes on at the next line counts too. A here-string or a captured
# variable reads the input to the end; 'grep ... >/dev/null' does not with GNU
# grep, which stops at the first match when its output is /dev/null.
pipe_grep_q='(^|[^|])\|[[:space:]]*grep[[:space:]]+(-[A-Za-z-]+[[:space:]]+)*-[A-Za-z]*q'
# quiet_pipes <file>...: '<file>:<line>:<command>' for each such pipe; a line
# that ends in a pipe is joined to the next, and comment lines are skipped.
quiet_pipes() {
  awk 'FNR == 1 { held = "" }
    /^[[:space:]]*#/ { next }
    { line = held $0 }
    line ~ /(^|[^|])[|][[:space:]]*$/ { held = line " "; next }
    { held = ""; print FILENAME ":" FNR ":" line }' "$@" | grep -E "$pipe_grep_q" || true
}
found_quiet_pipes="$(cd "$source_root" && quiet_pipes tests/*.sh scripts/*.sh scripts/lib/*.sh)"
[[ -z "$found_quiet_pipes" ]] ||
  fail "a self-test or a workflow script pipes into 'grep -q', which fails under load; use a here-string or a captured variable: $found_quiet_pipes"
# The guard itself finds such a pipe, also one that goes on at the next line,
# and not 'grep -q' after '||', on a here-string, or in a comment (the q is
# spliced in, so that these lines are no such pipe).
q=q
printf '%s\n' "printf x | grep -F$q a || fail" "log_of r | grep -E$q b" "git log |" "  grep -v c |" "  grep -F$q d && echo" \
  >"$tmp/quiet.sh"
[[ "$(quiet_pipes "$tmp/quiet.sh" | grep -c .)" -eq 3 ]] || fail "the guard against 'grep -q' in a pipe finds no such pipe"
[[ "$(quiet_pipes "$tmp/quiet.sh" | sed -n 3p)" == "$tmp/quiet.sh:5:git log |   grep -v c |   grep -F$q d && echo" ]] ||
  fail "the guard against 'grep -q' in a pipe does not report the joined lines of a pipe at its last line"
printf '%s\n' "grep -F$q a f || grep -F$q b f" "printf x | grep -F a >/dev/null" "grep -F$q a <<<\"\$x\"" "# x | grep -F$q a" \
  "x |" "  # a comment" "  sort" "grep -F$q a f" >"$tmp/quiet.sh"
[[ -z "$(quiet_pipes "$tmp/quiet.sh")" ]] || fail "the guard against 'grep -q' in a pipe finds a grep that reads to the end"

echo "verify tests passed"
