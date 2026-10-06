#!/usr/bin/env bash

# Checks of the supported-machine contract (docs/development.md, "One-time
# setup"), shared by doctor.sh and preflight.sh. Source this file.
#
# Every check reports through ok or missing; missing sets 'failed' to 1.
# Uses only Bash builtins besides the tools it checks.

prerequisites_lib_dir="${BASH_SOURCE[0]%/*}"

failed=0

ok() {
  echo "OK       $1"
}

missing() {
  echo "FAILED   $1"
  echo "         $2"
  failed=1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

check_git() {
  if have git; then
    ok "git is installed"
  else
    missing "git is not installed" "Install Git: https://git-scm.com/downloads"
  fi
}

check_jq() {
  local jq_version

  if have jq; then
    # The workflow scripts are written for jq 1.6 and later.
    jq_version="$(jq --version 2>/dev/null || true)"
    if [[ "$jq_version" =~ ^jq-([0-9]+)\.([0-9]+) ]] &&
      ((BASH_REMATCH[1] < 1 || (BASH_REMATCH[1] == 1 && BASH_REMATCH[2] < 6))); then
      missing "jq $jq_version is too old" "Install jq 1.6 or later: 'brew install jq' or 'sudo apt-get install jq'"
    else
      ok "jq is installed"
    fi
  else
    missing "jq is not installed" "Install jq: 'brew install jq' or 'sudo apt-get install jq'"
  fi
}

check_uv() {
  if have uv; then
    ok "uv is installed"
  else
    missing "uv is not installed" "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
  fi
}

check_elan() {
  if ! have elan; then
    missing "elan (the Lean toolchain manager) is not installed" \
      "Install elan: https://lean-lang.org/install/manual/ and put ~/.elan/bin on your PATH"
  elif ! have lake; then
    missing "lake (the Lean build tool) is not on your PATH" "Put ~/.elan/bin on your PATH"
  else
    ok "elan and lake are installed"
  fi
}

# check_browser <python command...>
# Runs check_browser.py with the given Python command of the locked
# environment and reports whether the pinned browser build is installed and
# starts.
check_browser() {
  local detail
  local status=0

  detail="$("$@" "$prerequisites_lib_dir/check_browser.py" 2>&1)" || status=$?
  case "$status" in
    0) ok "the pinned browser build is installed and starts" ;;
    3)
      missing "the pinned browser build is not installed" \
        "Run: uv run --locked playwright install --only-shell chromium"
      ;;
    4)
      missing "the pinned browser build is installed but cannot start" \
        "On Linux, install its system libraries (needs administrator rights): uv run --locked playwright install-deps chromium"
      ;;
    *)
      missing "the pinned browser build could not be checked" \
        "Run: uv sync --locked && uv run --locked playwright install --only-shell chromium"
      ;;
  esac
  if [[ "$status" -ne 0 && -n "$detail" ]]; then
    echo "$detail"
  fi
}
