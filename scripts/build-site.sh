#!/usr/bin/env bash

set -euo pipefail

# Builds the website with Quarto in the locked Python environment. Every page
# is executed; nothing is read from an earlier build.
#
# Usage: build-site.sh [<source-directory> [<output-directory>]]
#
# The defaults build site/ into site/_site, which Git ignores.
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

log="$(mktemp "${TMPDIR:-/tmp}/build-site.XXXXXX")"
trap 'rm -f "$log"' EXIT

uv run --locked --project "$root" \
  quarto render "$source_dir" --output-dir "$output_dir" 2>&1 | tee "$log"

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

echo "Site built in $output_dir"
