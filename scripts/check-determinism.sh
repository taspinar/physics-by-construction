#!/usr/bin/env bash

set -euo pipefail

# Builds the site a second time and requires the result to be byte-identical
# to the first build.
#
# Usage: check-determinism.sh [<source-directory> [<first-build-directory>]]
#
# The second build runs from a fresh copy of the sources in another
# directory, at a later time, and without Quarto's project cache. Output that
# depends on the build time, the location of the checkout, file timestamps,
# or a cache therefore differs and fails the check.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() {
  echo "Error: $*" >&2
  exit 1
}

source_dir="${1:-$root/site}"
[[ -f "$source_dir/_quarto.yml" ]] || fail "no Quarto project in $source_dir"
first="${2:-$source_dir/_site}"
[[ -d "$first" ]] ||
  fail "no first build in $first; run ./scripts/build-site.sh before this check."

tmp="$(mktemp -d "${TMPDIR:-/tmp}/determinism.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

cp -R "$source_dir" "$tmp/site"
rm -rf "$tmp/site/_site" "$tmp/site/.quarto"

"$root/scripts/build-site.sh" "$tmp/site" "$tmp/second" >"$tmp/build.log" 2>&1 || {
  cat "$tmp/build.log" >&2
  fail "the second build failed."
}

if ! diff -r "$first" "$tmp/second" >"$tmp/diff.log"; then
  # Name the files; a byte-level diff of HTML or images is not readable.
  diff -rq "$first" "$tmp/second" >&2 || true
  fail "two builds of the same sources differ. Remove the build-time value (time, path, random identifier) from the pages named above."
fi

echo "Two builds are byte-identical ($(find "$first" -type f | wc -l | tr -d ' ') files)."
