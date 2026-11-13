#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$script_dir/lib/fingerprint.sh"
source "$script_dir/lib/guardrails.sh"
source "$script_dir/lib/planning.sh"

usage() {
  echo "Usage: $0 [<base-branch>] [--fail-on-protected]"
  echo "       $0 --commits <base-commit> <head-commit> [--fail-on-protected]"
  echo "       $0 --planning [<base-branch>]"
  echo
  echo "Reports which changes of a feature need the owner's approval before a merge:"
  echo "changes to ADRs, to the files of the workflow and its gate, and to the paths"
  echo "that .agents/policies/guardrails.conf lists. The rules are read from the base"
  echo "branch as it is now, not from the feature."
  echo
  echo "Without --commits it checks the current worktree against the point where it"
  echo "left its base branch (default: main), with uncommitted and untracked files."
  echo "With --commits it compares two commits, as CI does for a pull request."
  echo
  echo "The first line of the output is 'level: none', 'level: sensitive', or"
  echo "'level: protected'. It exits 0, or 3 with --fail-on-protected when the level"
  echo "is protected."
  echo
  echo "--planning reports whether this worktree changes, against its base branch"
  echo "(default: main), a document that only the planning may change: the"
  echo "description, the requirements, a change request, the roadmap, or the planning"
  echo "approval. Such a change is allowed only when the recorded planning approval"
  echo "is current for it, as after ./scripts/finish-planning.sh or its --amend;"
  echo "otherwise it exits 1, so the approval never becomes stale unnoticed (Issue"
  echo "#512). CI runs it as the check planning-drift."
  exit 2
}

fail() {
  echo "Error: $*" >&2
  exit 2
}

fail_on_protected=0
arguments=()
for argument in "$@"; do
  case "$argument" in
    --fail-on-protected) fail_on_protected=1 ;;
    *) arguments+=("$argument") ;;
  esac
done
set -- ${arguments[@]+"${arguments[@]}"}

root="$(git rev-parse --show-toplevel)"

# --planning: no silent drift of the approved planning.
if [[ "${1:-}" == "--planning" ]]; then
  [[ $# -le 2 && "$fail_on_protected" -eq 0 ]] || usage
  [[ "${2:-}" != --* ]] || usage
  lines="$(feature_base "$root" "${2:-main}")" ||
    fail "could not determine the base of this worktree: ${2:-main}. The planning documents cannot be compared."
  from="$(printf '%s\n' "$lines" | sed -n 2p)"
  if [[ ! -f "$root/$PLANNING_APPROVAL_FILE" ]] &&
    ! git -C "$root" cat-file -e "$from:$PLANNING_APPROVAL_FILE" 2>/dev/null; then
    echo "planning: no approved planning to compare with."
    exit 0
  fi
  changes="$(guardrails_changed "$root" "$from" "" "${PLANNING_PRODUCT_SCOPE[@]}" "$PLANNING_APPROVAL_FILE" | sort -u)"
  if [[ -z "$changes" ]]; then
    echo "planning: no planning-only document changed."
    exit 0
  fi
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/check-guardrails-planning.XXXXXX")"
  status=0
  reason="$(planning_approval_status "$root" "$scratch")" || status=$?
  rm -rf "$scratch"
  echo "planning: this branch changes documents that only the planning may change:"
  printf '%s\n' "$changes" | sed 's/^/  /'
  if [[ "$status" -eq 0 ]]; then
    echo "The planning approval is current for them (a planning cycle or an amendment)."
    exit 0
  fi
  echo "Error: the planning approval is not current for these changes: $reason" >&2
  echo "A note of a decision the owner already took: ./scripts/finish-planning.sh --amend \"<reason>\"" >&2
  echo "Anything else: a change cycle, ./scripts/start-planning.sh <name> --change <file>" >&2
  exit 1
fi

if [[ "${1:-}" == "--commits" ]]; then
  [[ $# -eq 3 ]] || usage
  git -C "$root" rev-parse --verify --quiet "$2^{commit}" >/dev/null || fail "unknown commit: $2"
  git -C "$root" rev-parse --verify --quiet "$3^{commit}" >/dev/null || fail "unknown commit: $3"
  from="$(git -C "$root" merge-base "$2" "$3")" || fail "the commits $2 and $3 share no history."
  to="$3"
  rules="$2"
else
  [[ $# -le 1 ]] || usage
  [[ "${1:-}" != --* ]] || usage
  lines="$(feature_base "$root" "${1:-main}")" || fail "could not determine the base of this worktree: ${1:-main}"
  from="$(printf '%s\n' "$lines" | sed -n 2p)"
  to=""
  rules="$(guardrails_rules_refs "$root" "${1:-main}")"
fi

# The rules of the base as it is now; the diff from where the feature left it.
findings="$(guardrails_classify "$root" "$rules" "$from" "$to")"
level="$(printf '%s\n' "$findings" | guardrails_level)"
echo "level: $level"
if [[ -n "$findings" ]]; then
  printf '%s\n' "$findings" | sort -u | awk -F '\t' '{ printf "%s: %s (%s)\n", $1, $2, $3 }'
fi
case "$level" in
  protected) echo "The owner's approval is needed before this is merged." ;;
  sensitive) echo "No approval is needed for these paths; the independent review looks at them." ;;
esac
[[ "$level" != "protected" || "$fail_on_protected" -eq 0 ]] || exit 3
