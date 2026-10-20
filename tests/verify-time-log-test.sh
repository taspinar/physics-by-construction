#!/usr/bin/env bash

set -euo pipefail

# The time log of ./scripts/verify.sh (ADR 020 decision 7): one line per run
# with its five fields, in the Git directory every worktree of the clone
# shares, never committed, and read by no gate. And the partial run of an
# intermediate Level 3 round (ADR 020 decision 5): logged as feedback, never
# recorded as a verification.

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/verify-time-log-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "verify time log test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"

repo="$tmp/project"
mkdir -p "$repo"
copy_workflow "$repo"
rm -f "$repo/scripts/verify-workflow.conf"
cp "$source_root/.gitignore" "$repo/.gitignore"
printf 'quick [code]: true\nslow [build]: test ! -e fail-slow\n' >"$repo/scripts/verify.conf"
git -C "$repo" init -q -b main
git -C "$repo" config user.name "Log Test"
git -C "$repo" config user.email "log-test@example.com"
git -C "$repo" add .
git -C "$repo" commit -qm "Seed"
log="$repo/.git/verify-time.log"

run_verify() {
  status=0
  (cd "$1" && PATH="/usr/bin:/bin" ./scripts/verify.sh "${@:2}") >"$tmp/out" 2>&1 || status=$?
}

# last_line <field>: a field of the last line of the log, 1 to 5.
field() {
  tail -n 1 "$log" | awk -F ' [|] ' -v n="$1" '{ print $n }'
}

expect_line() {
  # expect_line <description> <tier> <result>
  [[ "$(tail -n 1 "$log" | awk -F ' [|] ' '{ print NF }')" -eq 5 ]] || fail "$1: the line has not five fields: $(tail -n 1 "$log")"
  [[ "$(field 1)" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z$ ]] || fail "$1: no UTC time stamp: $(field 1)"
  [[ "$(field 2)" == "$2" ]] || fail "$1: the tier is '$(field 2)' instead of '$2'"
  [[ "$(field 3)" =~ ^[0-9a-f]{40}$ ]] || fail "$1: no tree: $(field 3)"
  [[ "$(field 4)" =~ ^[0-9]+$ ]] || fail "$1: no duration in seconds: $(field 4)"
  [[ "$(field 5)" == "$3" ]] || fail "$1: the result is '$(field 5)' instead of '$3'"
}

run_verify "$repo"
[[ "$status" -eq 0 ]] || { cat "$tmp/out" >&2; fail "the full run failed"; }
expect_line "a full run" full passed
tree="$(field 3)"
[[ "$tree" == "$(sed -n 's/^tree: //p' "$repo/.agents/verification/passed")" ]] ||
  fail "the logged tree is not the content the run verified"

run_verify "$repo" --reuse
expect_line "a reused pass" full reused

# The partial run of an intermediate Level 3 round: feedback in the log, and
# no verification: the record of the full run stays exactly as it was, and a
# partial run of changed content records nothing.
record_before="$(cat "$repo/.agents/verification/passed")"
run_verify "$repo" --only code
[[ "$status" -eq 0 ]] || fail "the partial run failed"
expect_line "a partial run" only:code passed
[[ "$(cat "$repo/.agents/verification/passed")" == "$record_before" ]] || fail "a partial run changed the verification record"
printf 'more\n' >"$repo/notes.txt"
run_verify "$repo" --only code
expect_line "a partial run of changed content" only:code passed
[[ "$(sed -n 's/^tree: //p' "$repo/.agents/verification/passed")" == "$tree" ]] ||
  fail "a partial run recorded a verification of the changed content"
run_verify "$repo" --reuse
expect_line "the full run after the partial one" full passed
[[ "$(field 3)" != "$tree" ]] || fail "the full run after a change was not logged with the new tree"

touch "$repo/fail-slow"
run_verify "$repo"
[[ "$status" -ne 0 ]] || fail "a failing check passed"
expect_line "a failed run" full failed
rm "$repo/fail-slow"

# Every worktree of the clone writes the one log of the clone, outside its
# own files: nothing to commit, nothing in the fingerprint.
git -C "$repo" worktree add -q "$tmp/second" -b feature/3-x
run_verify "$tmp/second"
expect_line "a run in another worktree" full passed
[[ ! -e "$tmp/second/verify-time.log" && -z "$(git -C "$tmp/second" status --porcelain)" ]] ||
  fail "the log landed in the worktree's files"
[[ "$(grep -c . "$log")" -eq 7 ]] || fail "the log does not hold one line per run: $(cat "$log")"

# VERIFY_TIME_LOG names another place; a log that cannot be written changes
# nothing about the run.
VERIFY_TIME_LOG="$tmp/elsewhere/time.log" run_verify "$repo"
[[ "$(grep -c . "$tmp/elsewhere/time.log")" -eq 1 ]] || fail "VERIFY_TIME_LOG was not used"
printf 'a file\n' >"$tmp/blocker"
VERIFY_TIME_LOG="$tmp/blocker/time.log" run_verify "$repo"
[[ "$status" -eq 0 ]] || { cat "$tmp/out" >&2; fail "a log that cannot be written failed the run"; }

# No gate reads it: the script that writes it is the only one that names it,
# and it only appends.
readers="$(cd "$source_root" && grep -rlE 'verify-time\.log|VERIFY_TIME_LOG|time_log' scripts .github 2>/dev/null | grep -vx 'scripts/verify.sh' || true)"
[[ -z "$readers" ]] || fail "a script other than verify.sh names the time log: $readers"
if grep -E 'verify-time\.log|VERIFY_TIME_LOG|\$log\b' "$source_root/scripts/verify.sh" | grep -Eq '<[[:space:]]*"?\$log|cat "\$log|read .*\$log'; then
  fail "verify.sh reads the time log"
fi

echo "verify time log tests passed"
