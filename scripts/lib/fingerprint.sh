#!/usr/bin/env bash

# Content fingerprints of a working tree or of a set of files.
# Source this file; do not execute it.
#
# A fingerprint is the Git tree hash of the current file contents, including
# uncommitted and untracked changes. It depends on content only, so committing
# unchanged content keeps it valid, and any change to a covered file changes
# it. A review also covers the completion record and the handoff note of its
# Issue, which Git ignores (ADR 020 decision 4): fingerprint_with_records adds
# them, so that neither can change after the review without making it stale.
# Review and triage artifacts and the approval requests are never part of
# a fingerprint: correcting an approval request leaves a recorded verification
# and a review valid, and scripts/lib/risk.sh checks the request itself. The
# real Git index is not touched; objects may be written to the object
# database.

FINGERPRINT_EXCLUDES=(".agents/reviews" ".agents/triage" ".agents/approvals")

# feature_base <root> <base>
# Prints two lines: the ref of the base branch a feature is compared with,
# and the merge base of HEAD and that ref. A feature is created from
# origin/<base>, and the local <base> can be behind it or ahead of it, so of
# the two the one is used whose merge base with HEAD is the more recent:
# that is the point where the feature left its base. With a stale ref the
# merge base would lie further back, and everything merged since would count
# as the feature's own change. Fails when neither ref exists or shares
# history with HEAD.
feature_base() {
  local root="$1"
  local base="$2"
  local ref
  local found
  local best_ref=""
  local best=""

  for ref in "$base" "origin/$base"; do
    git -C "$root" rev-parse --verify --quiet "$ref^{commit}" >/dev/null || continue
    found="$(git -C "$root" merge-base HEAD "$ref" 2>/dev/null)" || continue
    if [[ -z "$best" ]] || { [[ "$found" != "$best" ]] && git -C "$root" merge-base --is-ancestor "$best" "$found"; }; then
      best="$found"
      best_ref="$ref"
    fi
  done
  [[ -n "$best" ]] || return 1
  printf '%s\n%s\n' "$best_ref" "$best"
}

# fingerprint_worktree <root> <scratch-dir>
# Prints the fingerprint of the whole working tree. Ignored files are left
# out unless Git already tracks them.
fingerprint_worktree() {
  local root="$1"
  local index="$2/fingerprint.index"
  local real_index
  local exclude_specs=()
  local path

  for path in "${FINGERPRINT_EXCLUDES[@]}"; do
    exclude_specs+=(":(exclude)$path")
  done

  # Start from the real index so tracked files that match an ignore rule stay
  # covered. The path may be relative to the repository root.
  rm -f "$index"
  real_index="$(cd "$root" && git rev-parse --git-path index)"
  if (cd "$root" && [[ -f "$real_index" ]]); then
    (cd "$root" && cp "$real_index" "$index") || return 1
  fi

  GIT_INDEX_FILE="$index" git -C "$root" rm -r -q --cached --ignore-unmatch -- "${FINGERPRINT_EXCLUDES[@]}" >/dev/null &&
    GIT_INDEX_FILE="$index" git -C "$root" add -A -- . "${exclude_specs[@]}" >/dev/null &&
    GIT_INDEX_FILE="$index" git -C "$root" write-tree
}

# fingerprint_issue_records <issue>
# Prints the Git-ignored files of an Issue that a review fingerprints, one
# per line: the completion record and the handoff note.
fingerprint_issue_records() {
  printf '%s\n' ".agents/completion/$1.json" ".agents/handoffs/$1.md"
}

# fingerprint_with_records <root> <scratch-dir> <path>...
# Prints the fingerprint of the whole working tree with the given files added
# although Git ignores them. A missing path is left out, so creating it
# changes the fingerprint.
fingerprint_with_records() {
  local root="$1"
  local index="$2/records.index"
  local tree
  local path
  local paths=()

  tree="$(fingerprint_worktree "$root" "$2")" || return 1
  shift 2
  for path in "$@"; do
    [[ ! -e "$root/$path" && ! -L "$root/$path" ]] || paths+=("$path")
  done
  if [[ "${#paths[@]}" -eq 0 ]]; then
    printf '%s\n' "$tree"
    return 0
  fi
  rm -f "$index"
  GIT_INDEX_FILE="$index" git -C "$root" read-tree "$tree" &&
    GIT_INDEX_FILE="$index" git -C "$root" add -f -- "${paths[@]}" >/dev/null &&
    GIT_INDEX_FILE="$index" git -C "$root" write-tree
}

# fingerprint_files <root> <scratch-dir> <path>...
# Prints the fingerprint of exactly the given repository-relative paths, which
# may be files, symlinks, or directories. A missing path is part of the
# fingerprint as absent. The excluded artifacts are excluded here too.
fingerprint_files() {
  local root="$1"
  local index="$2/fingerprint-files.index"
  local specs=()
  local path

  shift 2
  for path in "$@"; do
    if [[ -e "$root/$path" || -L "$root/$path" ]]; then
      specs+=("$path")
    fi
  done

  rm -f "$index"
  if [[ "${#specs[@]}" -gt 0 ]]; then
    for path in "${FINGERPRINT_EXCLUDES[@]}"; do
      specs+=(":(exclude)$path")
    done
    GIT_INDEX_FILE="$index" git -C "$root" add -f -- "${specs[@]}" >/dev/null || return 1
  fi
  GIT_INDEX_FILE="$index" git -C "$root" write-tree
}

# fingerprint_artifacts <root>
# Prints a hash of the review and triage artifacts and the approval requests,
# which every other fingerprint leaves out, so a run can detect that an agent
# changed them.
fingerprint_artifacts() {
  (
    cd "$1" || exit 1
    # A missing artifact directory is an empty set, not an error.
    { find "${FINGERPRINT_EXCLUDES[@]}" \( -type f -o -type l \) 2>/dev/null || true; } | LC_ALL=C sort |
      while IFS= read -r path; do
        if [[ -L "$path" ]]; then
          printf '%s symlink %s\n' "$path" "$(readlink "$path")"
        else
          printf '%s %s\n' "$path" "$(git hash-object -- "$path")"
        fi
      done
  ) | git hash-object --stdin
}

# fingerprint_review <root> <scratch-dir> <review-json>
# Prints the current fingerprint of what the review covers: the paths in
# reviewed_paths when the review lists them, otherwise the whole working tree
# with the files in record_paths, which a review made before ADR 020 decision
# 4 was delivered does not have.
fingerprint_review() {
  local root="$1"
  local scratch="$2"
  local review="$3"
  local paths=()
  local path

  if jq -e '(.reviewed_paths | type) == "array"' "$review" >/dev/null; then
    while IFS= read -r path; do
      paths+=("$path")
    done < <(jq -r '.reviewed_paths[]' "$review")
    fingerprint_files "$root" "$scratch" ${paths[@]+"${paths[@]}"}
  elif jq -e '(.record_paths | type) == "array"' "$review" >/dev/null; then
    while IFS= read -r path; do
      paths+=("$path")
    done < <(jq -r '.record_paths[]' "$review")
    fingerprint_with_records "$root" "$scratch" ${paths[@]+"${paths[@]}"}
  else
    fingerprint_worktree "$root" "$scratch"
  fi
}

# review_is_current <root> <scratch-dir> <review-json>
# Succeeds when the reviewed content is unchanged since the review.
review_is_current() {
  local current

  current="$(fingerprint_review "$1" "$2" "$3")" || return 2
  [[ "$current" == "$(jq -r '.reviewed_tree' "$3")" ]]
}

# review_stale_notice <root> <scratch-dir> <review-json>
# Prints to standard error which paths differ between the reviewed content and
# the current content, so a stale review can be traced to its cause. Prints
# nothing when that cannot be determined, for example because the reviewed
# tree is no longer in the object database.
review_stale_notice() {
  local reviewed
  local current
  local changed
  local total

  reviewed="$(jq -r '.reviewed_tree' "$3" 2>/dev/null)" || return 0
  git -C "$1" cat-file -e "$reviewed^{tree}" 2>/dev/null || return 0
  current="$(fingerprint_review "$1" "$2" "$3" 2>/dev/null)" || return 0
  changed="$(git -C "$1" diff-tree -r --name-status "$reviewed" "$current" 2>/dev/null)" || return 0
  [[ -n "$changed" ]] || return 0

  total="$(printf '%s\n' "$changed" | grep -c .)"
  {
    echo "Changed since the review (A added, M modified, D deleted):"
    # sed reads all of its input, so a long list cannot end the pipe early.
    printf '%s\n' "$changed" | sed -n '1,20s/^/  /p'
    [[ "$total" -le 20 ]] || echo "  ... and $((total - 20)) more"
  } >&2
}
