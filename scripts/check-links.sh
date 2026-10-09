#!/usr/bin/env bash

set -euo pipefail

# On-demand maintenance check of the external links in the reference register
# (site/references.yaml, ADR 009). Opens every URL, so it needs a network
# connection. It is not in scripts/verify.conf and has no CI job: the build
# and reading never depend on another site.
#
# Usage: ./scripts/check-links.sh [--register FILE] [--timeout SECONDS]

script_dir="${BASH_SOURCE[0]%/*}"
[[ "$script_dir" != "${BASH_SOURCE[0]}" ]] || script_dir="."
root="$(cd "$script_dir/.." && pwd -P)"

cd "$root"
exec uv run --locked python "$root/scripts/lib/check_links.py" "$@"
