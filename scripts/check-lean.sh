#!/usr/bin/env bash

set -euo pipefail

# Builds every Lean module of the project against Mathlib and audits the
# result: the check fails on a module that does not compile, on 'sorry', and
# on an axiom declared by the project.
#
# Usage: check-lean.sh [<lean-project-directory>]
#
# Mathlib always comes from its build cache. When the cache does not provide
# all of Mathlib, the check fails instead of compiling Mathlib from source.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
project="${1:-$root/lean}"
audit="$root/lean/AxiomAudit.lean"

fail() {
  echo "Error: $*" >&2
  exit 1
}

[[ -f "$project/lakefile.toml" ]] || fail "no Lean project in $project"
cd "$project"

echo "== Mathlib build cache =="
if ! lake build --no-build Mathlib; then
  echo "Mathlib is not built here yet; fetching its build cache."
  lake exe cache get
  lake build --no-build Mathlib ||
    fail "Mathlib is not complete after fetching its build cache. Verification never compiles Mathlib from source; check the network connection and run 'lake exe cache get' in $project."
fi

echo "== Lean build =="
lake build

echo "== Axiom audit =="
modules="$(find PhysicsByConstruction -name '*.lean' | LC_ALL=C sort |
  sed -e 's/\.lean$//' -e 's#/#.#g')"
[[ -n "$modules" ]] || fail "no Lean modules found in $project/PhysicsByConstruction"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/axiom-audit.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
{
  while IFS= read -r module; do
    printf 'import %s\n' "$module"
  done <<<"$modules"
  cat "$audit"
} >"$tmp/AxiomAudit.lean"
lake env lean "$tmp/AxiomAudit.lean"
