#!/usr/bin/env bash

set -euo pipefail

# Hands the site that one CI job built to the jobs that check it (ADR 012).
#
# Usage: fetch-built-site.sh --record <directory>
#        fetch-built-site.sh <directory>
#
# --record runs in the job that built the site. It writes into <directory>
# the checksum of every file of site/_site (site-files.sha256) and a copy of
# the Lean build record that the pages show (pbc-build-record.json). The job
# uploads that directory beside the Pages artifact of the site.
#
# Without --record the script runs in a job that checks the site. <directory>
# holds what the job downloaded: artifact.tar, the archive of the Pages
# artifact, and the two files above. The script unpacks the archive to
# site/_site, requires that the files are exactly the recorded ones with the
# recorded content, and puts the Lean build record where a build reads it.
# A missing, extra, or changed file stops the job before any check runs, so
# every job checks the site that is published.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
site="${PBC_SITE_DIR:-$root/site/_site}"
record="${PBC_BUILD_RECORD:-$root/lean/.lake/pbc-build-record.json}"
list_name="site-files.sha256"
record_name="pbc-build-record.json"

fail() {
  echo "Error: $*" >&2
  exit 1
}

if command -v sha256sum >/dev/null 2>&1; then
  sum=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  sum=(shasum -a 256)
else
  fail "sha256sum or shasum is required."
fi

# The checksum and the path of every file of a directory, sorted by path.
checksums() {
  (cd "$1" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 "${sum[@]}")
}

if [[ "${1:-}" == "--record" ]]; then
  [[ $# -eq 2 ]] || fail "usage: $0 --record <directory>"
  [[ -f "$site/index.html" ]] || fail "no built site in $site."
  [[ -f "$record" ]] || fail "no Lean build record in $record."
  mkdir -p "$2"
  checksums "$site" >"$2/$list_name"
  cp "$record" "$2/$record_name"
  echo "Recorded $(wc -l <"$2/$list_name" | tr -d ' ') files of the built site."
  exit 0
fi

[[ $# -eq 1 ]] || fail "usage: $0 [--record] <directory>"
from="$1"
for file in artifact.tar "$list_name" "$record_name"; do
  [[ -f "$from/$file" ]] || fail "$from/$file is missing."
done
[[ -s "$from/$list_name" ]] || fail "$from/$list_name is empty."

rm -rf "$site"
mkdir -p "$site"
tar -xf "$from/artifact.tar" -C "$site"

tmp="$(mktemp -d "${TMPDIR:-/tmp}/built-site.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
checksums "$site" >"$tmp/found"
if ! diff "$from/$list_name" "$tmp/found" >"$tmp/diff"; then
  # '<' is a recorded file that is missing or changed, '>' one that was found.
  cat "$tmp/diff" >&2
  fail "the unpacked site is not the site that was built."
fi

mkdir -p "$(dirname "$record")"
cp "$from/$record_name" "$record"
echo "The built site is in $site ($(wc -l <"$tmp/found" | tr -d ' ') files, as recorded)."
