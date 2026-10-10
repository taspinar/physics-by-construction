#!/usr/bin/env bash
# Learner-side download of a full dataset, by the URLs, filenames, and checksums
# of its card in data/registry/ (ADR 007).
#
#   ./scripts/fetch-data.sh <dataset>
#
# The files go to data/downloads/<dataset>/, which Git ignores. Files are fetched
# one at a time, with a pause between them, and each is checked against the
# card's digest; a file that does not match is removed and the script fails.
# The build, verification, and CI never run this script and refuse to: with CI
# set it exits without a request (invariant I20).
#
# Environment: PBC_FETCH_DELAY seconds between files (default 2); PBC_PYTHON
# the command that runs Python with the repository's environment (default
# 'uv run --locked python'); PBC_REGISTRY and PBC_DOWNLOADS replace
# data/registry and data/downloads (the tests use them).
set -euo pipefail

cd "$(dirname "$0")/.."

dataset="${1:-}"
if [ -z "$dataset" ] || [ "$#" -ne 1 ]; then
    echo "usage: ./scripts/fetch-data.sh <dataset>   (a card name in data/registry/)" >&2
    exit 2
fi
if [ -n "${CI:-}" ]; then
    echo "fetch-data.sh is a learner-side download and does not run in CI." >&2
    exit 2
fi

python_cmd="${PBC_PYTHON:-uv run --locked python}"

# digest <algorithm> <file>
digest() {
    case "$1" in
        md5) if command -v md5sum >/dev/null 2>&1; then md5sum "$2" | cut -d' ' -f1; else md5 -q "$2"; fi ;;
        sha256) if command -v sha256sum >/dev/null 2>&1; then sha256sum "$2" | cut -d' ' -f1; else shasum -a 256 "$2" | cut -d' ' -f1; fi ;;
        *) echo "unknown digest algorithm $1" >&2; return 1 ;;
    esac
}

# shellcheck disable=SC2086
rows="$($python_cmd -m pbc.data.card downloads "$dataset")"

dest="${PBC_DOWNLOADS:-data/downloads}/$dataset"
mkdir -p "$dest"
first=1
while IFS=$'\t' read -r url algorithm expected filename; do
    [ -n "$url" ] || continue
    target="$dest/$filename"
    if [ -f "$target" ] && [ "$(digest "$algorithm" "$target")" = "$expected" ]; then
        echo "have $target"
        continue
    fi
    [ "$first" -eq 1 ] || sleep "${PBC_FETCH_DELAY:-2}"
    first=0
    echo "fetching $url"
    curl --fail --silent --show-error --location --retry 2 --retry-delay 5 \
        --user-agent "physics-by-construction fetch-data (learner download)" \
        --output "$target.part" "$url"
    actual="$(digest "$algorithm" "$target.part")"
    if [ "$actual" != "$expected" ]; then
        rm -f "$target.part"
        echo "$filename: $algorithm is $actual, the card says $expected; the file was removed" >&2
        exit 1
    fi
    mv "$target.part" "$target"
    echo "ok   $target"
done <<< "$rows"
