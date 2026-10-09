#!/usr/bin/env bash

set -euo pipefail

# Builds the site sources of a base revision and of the working tree, and
# requires every built lesson page to be identical, apart from the footer and
# the embedded commit.
#
# Usage: compare-lessons.sh [<base-revision>]
#
# The base defaults to the merge base with main. Not part of verify.sh: it
# needs the history of the base revision, which CI's shallow checkout lacks.
# Run it for a change that must leave the lesson pages as they are, and record
# the result in the pull request.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() {
  echo "Error: $*" >&2
  exit 1
}

base="${1:-$(git -C "$root" merge-base HEAD main)}"
git -C "$root" rev-parse --verify --quiet "$base^{commit}" >/dev/null ||
  fail "unknown revision $base"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/compare-lessons.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

mkdir "$tmp/base-src"
git -C "$root" archive "$base" site | tar -x -C "$tmp/base-src"
cp -R "$root/site" "$tmp/head-src"
rm -rf "$tmp/head-src/_site" "$tmp/head-src/.quarto"

"$root/scripts/build-site.sh" "$tmp/base-src/site" "$tmp/base" >"$tmp/base.log" 2>&1 ||
  { cat "$tmp/base.log" >&2; fail "the build of $base failed."; }
"$root/scripts/build-site.sh" "$tmp/head-src" "$tmp/head" >"$tmp/head.log" 2>&1 ||
  { cat "$tmp/head.log" >&2; fail "the build of the working tree failed."; }

# Drop the footer and replace any full commit hash.
normalise() {
  perl -0pe 's{<footer\b.*?</footer>}{}sg; s/\b[0-9a-f]{40}\b/COMMIT/g' "$1"
}

count=0
differ=0
while IFS= read -r page; do
  count=$((count + 1))
  if [[ ! -f "$tmp/head/$page" ]] ||
    ! diff -q <(normalise "$tmp/base/$page") <(normalise "$tmp/head/$page") >/dev/null; then
    echo "differs: $page" >&2
    differ=$((differ + 1))
  fi
done < <(cd "$tmp/base" && find lessons -name index.html | sort)

[[ "$count" -gt 0 ]] || fail "no lesson page in the build of $base."
[[ "$differ" -eq 0 ]] || fail "$differ of $count lesson pages differ from $base."
echo "Lesson pages: $count compared with $base, $differ differ (footer excluded, commit normalised)."
