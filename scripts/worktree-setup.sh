#!/usr/bin/env bash

set -euo pipefail

# Prepares a new feature worktree; scripts/start-feature.sh runs it there
# before the agent starts, with the primary checkout as its argument.
#
# Lean's packages and the unpacked Mathlib build cache are about 8 GB in
# lean/.lake/, which Git ignores, so a new worktree would fetch and unpack them
# again. They are copied from the primary checkout instead. On macOS (APFS)
# and on Linux file systems with reflinks the copy shares its disk space with
# the original. When the worktree pins another Mathlib, Lean fetches the
# difference in the first build.

primary="${1:?usage: worktree-setup.sh <primary-checkout>}"

if [[ -d lean/.lake ]]; then
  echo "lean/.lake already exists here; nothing to prepare."
  exit 0
fi
if [[ ! -d "$primary/lean/.lake" ]]; then
  echo "No lean/.lake in $primary to copy; the first verification run fetches Mathlib."
  exit 0
fi

echo "Copying lean/.lake from $primary..."
case "$(uname -s)" in
  Darwin) cp -Rc "$primary/lean/.lake" lean/.lake ;;
  *) cp -R --reflink=auto "$primary/lean/.lake" lean/.lake ;;
esac
echo "Copied lean/.lake."
