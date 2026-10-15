#!/usr/bin/env bash

set -euo pipefail

# Builds the website with Quarto in the locked Python environment. Without a
# base every page is executed; nothing is read from an earlier build.
#
# Usage: build-site.sh [<source-directory> [<output-directory>]]
#
# The defaults build site/ into site/_site, which Git ignores.
#
# The build writes the executed results of its pages to <source>/_freeze (the
# store, which Git ignores) and, for site/, the input digests of the lessons to
# site/_digests.json, and the checksums of the built pages to <source>/_pages.json:
# these files make the base of a later run.
# When ./scripts/verify.sh --base selected the lessons to execute
# (.agents/verification/selection.json), the build starts from the store entries
# of the unchanged lessons of that base; every other page executes (ADR 014,
# decisions 3, 6 and 9). The time of each page goes to <source>/_timings.json.
#
# A lesson shard (./scripts/verify.sh --shard, ADR 014 decision 11) renders only
# the lesson pages of its share that the run executes, one page after the other,
# each as the reproduction of the lesson renders it, and restores only the
# entries of its share from the base. What the shard holds is its part of the
# store and of the site; the assembly renders the one site from the parts.
#
# The build fails when a page fails to execute or an equation cannot be
# converted to MathML.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() {
  echo "Error: $*" >&2
  exit 1
}

source_dir="${1:-$root/site}"
[[ -f "$source_dir/_quarto.yml" ]] || fail "no Quarto project in $source_dir"
source_dir="$(cd "$source_dir" && pwd -P)"
output_dir="${2:-$source_dir/_site}"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd -P)"

# The selection of this run, when ./scripts/verify.sh --base made one. Only the
# site of this repository reads it, unless PBC_STORE_SELECTION names a file (the
# determinism check does, for its copy of the sources).
selection_file="${PBC_STORE_SELECTION:-}"
if [[ -z "$selection_file" && "$source_dir" == "$root/site" ]]; then
  selection_file="$root/.agents/verification/selection.json"
fi
selection_args=()
if [[ -n "$selection_file" && -f "$selection_file" ]]; then
  selection_args=(--selection "$selection_file")
fi
# The lesson shard of this run, likewise: the determinism check names it for its
# copy of the sources.
shard_file="${PBC_SHARD_FILE:-}"
if [[ -z "$shard_file" && "$source_dir" == "$root/site" ]]; then
  shard_file="$root/.agents/verification/shard.json"
fi
shard_args=()
if [[ -n "$shard_file" && -f "$shard_file" ]]; then
  shard_args=(--shard-file "$shard_file")
fi
uv run --locked --project "$root" \
  python -m pbc.authoring.store prepare --site "$source_dir" \
  ${selection_args[@]+"${selection_args[@]}"} ${shard_args[@]+"${shard_args[@]}"} ||
  fail "the store of the build could not be prepared."
if [[ "$source_dir" == "$root/site" ]]; then
  uv run --locked --project "$root" \
    python -m pbc.authoring.store digests --root "$root" --out "$source_dir/_digests.json" ||
    fail "the input digests of the lessons could not be written."
fi

log="$(mktemp "${TMPDIR:-/tmp}/build-site.XXXXXX")"
trap 'rm -f "$log"' EXIT

# The profile makes Quarto write the store and replay an entry that exists.
render() {
  if [[ ${#shard_args[@]} -eq 0 ]]; then
    QUARTO_PROFILE=store uv run --locked --project "$root" \
      quarto render "$source_dir" --output-dir "$output_dir" 2>&1
    return
  fi
  # A lesson shard: the pages of its share that this run executes.
  local pages=() page index=0 listing
  listing="$(uv run --locked --project "$root" python -m pbc.authoring.shards \
    --root "$root" render-list --site "$source_dir" --shard-file "$shard_file" \
    ${selection_args[@]+"${selection_args[@]}"})" || return 1
  while IFS= read -r page; do
    [[ -z "$page" ]] || pages+=("$page")
  done <<<"$listing"
  # Quarto renders a single page into what the directory holds: start from nothing,
  # as a render of the whole project does, so no page of an earlier build stays.
  rm -rf "${output_dir:?}"/*
  echo "Lesson shard: ${#pages[@]} page(s) to render."
  for page in ${pages[@]+"${pages[@]}"}; do
    index=$((index + 1))
    echo "[$index/${#pages[@]}] $page"
    QUARTO_PROFILE=store uv run --locked --project "$root" \
      quarto render "$source_dir/$page" --output-dir "$output_dir" 2>&1 || return 1
  done
}
render |
  uv run --locked --project "$root" \
    python -m pbc.authoring.store timings --out "$source_dir/_timings.json" |
  tee "$log"

# Pandoc only warns about an equation it cannot convert and leaves the TeX
# source in the page.
if grep -Fq "Could not convert TeX math" "$log"; then
  fail "an equation could not be converted to MathML; see the warning above."
fi

# Quarto stamps every sitemap entry with the time of the build. Drop the
# stamp, so two builds of the same sources are byte-identical.
if [[ -f "$output_dir/sitemap.xml" ]]; then
  grep -v '<lastmod>' "$output_dir/sitemap.xml" >"$log"
  cp "$log" "$output_dir/sitemap.xml"
fi

# The record of the built pages, with the build commit normalised, which a later
# run compares its own pages with (ADR 014 decision 3).
uv run --locked --project "$root" \
  python -m pbc.authoring.pages --site-dir "$output_dir" --out "$source_dir/_pages.json" ||
  fail "the record of the built pages could not be written."

echo "Site built in $output_dir"
