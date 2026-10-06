#!/usr/bin/env bash

set -euo pipefail

# First check of ./scripts/verify.sh. Reports every missing prerequisite of
# the supported-machine contract with a fix hint, so that a missing tool is
# not first seen as an obscure failure inside a later check.
#
# Installs no system packages and needs no administrator rights. It checks
# only what verification needs; doctor.sh also checks the tools of the
# agentic development workflow.

script_dir="${BASH_SOURCE[0]%/*}"
[[ "$script_dir" != "${BASH_SOURCE[0]}" ]] || script_dir="."
root="$(cd "$script_dir/.." && pwd -P)"
source "$script_dir/lib/prerequisites.sh"

echo "== Verification preflight =="

check_git
check_jq
check_uv
check_elan
if have uv; then
  # Installs the locked Python environment when it is missing or out of date.
  check_browser uv run --locked --project "$root" python
fi

echo
if [[ "$failed" -ne 0 ]]; then
  echo "Prerequisites are missing. Complete the one-time setup in docs/development.md, then run verification again." >&2
  exit 1
fi

echo "All prerequisites of verification are available."
