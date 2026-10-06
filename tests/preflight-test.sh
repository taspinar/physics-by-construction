#!/usr/bin/env bash

set -euo pipefail

# Tests the preflight check of verification: it reports every missing
# prerequisite of the supported-machine contract with a fix hint, and
# ./scripts/verify.sh fails on it as its first check.

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
bash_path="$(command -v bash)"
dirname_path="$(command -v dirname)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/preflight-test.XXXXXX")"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  echo "preflight test failed: $*" >&2
  exit 1
}

# An isolated project that contains only the scripts under test.
project="$tmp/project"
mkdir -p "$project/scripts/lib"
cp "$source_root/scripts/preflight.sh" "$source_root/scripts/verify.sh" "$project/scripts/"
cp "$source_root"/scripts/lib/*.sh "$project/scripts/lib/"

# Builds a bin directory that contains only the named fake tools, so that
# PATH can be restricted to it and a missing tool is really missing. The fake
# 'uv' stands in for the browser check and exits with MOCK_BROWSER_EXIT. Bash
# and dirname are the real ones; the scripts themselves need them.
make_bin() {
  local bin="$tmp/$1"
  shift

  mkdir -p "$bin"
  ln -s "$bash_path" "$bin/bash"
  ln -s "$dirname_path" "$bin/dirname"
  for tool in "$@"; do
    case "$tool" in
      uv)
        cat >"$bin/uv" <<FAKE
#!$bash_path
case "\$*" in
  "run --locked --project "*" python "*"/check_browser.py") exit "\${MOCK_BROWSER_EXIT:-0}" ;;
esac
echo "unexpected uv call: \$*" >&2
exit 97
FAKE
        ;;
      *)
        printf '#!%s\nexit 0\n' "$bash_path" >"$bin/$tool"
        ;;
    esac
    chmod +x "$bin/$tool"
  done
  printf '%s\n' "$bin"
}

run_preflight() {
  PATH="$1" "$bash_path" "$project/scripts/preflight.sh" >"$tmp/out.log" 2>&1
}

# Requires a non-zero exit and exactly the given number of FAILED lines.
expect_failures() {
  local bin="$1"
  local count="$2"

  if run_preflight "$bin"; then
    cat "$tmp/out.log" >&2
    fail "expected a failure"
  fi
  if [[ "$(grep -c '^FAILED' "$tmp/out.log")" -ne "$count" ]]; then
    cat "$tmp/out.log" >&2
    fail "expected $count FAILED line(s)"
  fi
}

# Requires a FAILED line matching the pattern whose next line, the fix hint,
# matches the hint pattern.
expect_hint() {
  local pattern="$1"
  local hint="$2"

  if ! grep -E -A1 "^FAILED +.*$pattern" "$tmp/out.log" | tail -n 1 | grep -Eq "^ +.*$hint"; then
    cat "$tmp/out.log" >&2
    fail "expected '$pattern' with a fix hint matching '$hint'"
  fi
}

# Everything available.
bin="$(make_bin all git jq uv elan lake)"
run_preflight "$bin" || {
  cat "$tmp/out.log" >&2
  fail "complete environment was reported as a failure"
}
if grep -q '^FAILED' "$tmp/out.log"; then
  fail "complete environment reported a problem"
fi

# Each missing tool fails and is identified with a fix hint.
bin="$(make_bin no-jq git uv elan lake)"
expect_failures "$bin" 1
expect_hint "jq is not installed" "[Ii]nstall jq"

bin="$(make_bin no-git jq uv elan lake)"
expect_failures "$bin" 1
expect_hint "git is not installed" "[Ii]nstall"

bin="$(make_bin no-uv git jq elan lake)"
expect_failures "$bin" 1
expect_hint "uv is not installed" "[Ii]nstall uv"

bin="$(make_bin no-elan git jq uv)"
expect_failures "$bin" 1
expect_hint "elan .*is not installed" "[Ii]nstall elan"

# A browser build that is absent, or present but unable to start, fails with
# the fix for that case.
bin="$(make_bin browser git jq uv elan lake)"
MOCK_BROWSER_EXIT=3 expect_failures "$bin" 1
expect_hint "browser build is not installed" "playwright install"

MOCK_BROWSER_EXIT=4 expect_failures "$bin" 1
expect_hint "browser build is installed but cannot start" "install-deps"

# Every missing prerequisite is reported in one run, not only the first.
bin="$(make_bin several git uv)"
MOCK_BROWSER_EXIT=3 expect_failures "$bin" 3
expect_hint "jq is not installed" "[Ii]nstall jq"
expect_hint "elan .*is not installed" "[Ii]nstall elan"
expect_hint "browser build is not installed" "playwright install"

# Verification runs the preflight as its first check, fails on a missing
# prerequisite, and shows the fix hint.
first_check="$(grep -Ev '^[[:space:]]*(#.*)?$' "$source_root/scripts/verify.conf" | head -n 1)"
[[ "$first_check" == "preflight: ./scripts/preflight.sh" ]] ||
  fail "the preflight is not the first check in scripts/verify.conf: $first_check"
printf '%s\n' "$first_check" >"$project/scripts/verify.conf"

run_verify() {
  PATH="$1" "$bash_path" "$project/scripts/verify.sh" >"$tmp/out.log" 2>&1
}

bin="$(make_bin verify-no-jq git uv elan lake)"
if run_verify "$bin"; then
  cat "$tmp/out.log" >&2
  fail "verification passed without jq"
fi
grep -Eq "^FAIL +preflight" "$tmp/out.log" || fail "verification did not fail on the preflight"
expect_hint "jq is not installed" "[Ii]nstall jq"

bin="$(make_bin verify-no-browser git jq uv elan lake)"
if MOCK_BROWSER_EXIT=3 run_verify "$bin"; then
  cat "$tmp/out.log" >&2
  fail "verification passed without the browser build"
fi
grep -Eq "^FAIL +preflight" "$tmp/out.log" || fail "verification did not fail on the preflight"
expect_hint "browser build is not installed" "playwright install"

bin="$(make_bin verify-all git jq uv elan lake)"
run_verify "$bin" || {
  cat "$tmp/out.log" >&2
  fail "verification failed on a complete environment"
}

echo "preflight tests passed"
