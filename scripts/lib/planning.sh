#!/usr/bin/env bash

# The planning documents and the planning approval.
# Source this file after fingerprint.sh; do not execute it.

# The planning scope: every document of the project planning. It names the
# optional description, the change requests of later change cycles, and the
# decisions directory even when they are absent, so adding, changing, or
# deleting any planning document changes its fingerprint.
PLANNING_SCOPE=(docs/PROJECT_DESCRIPTION.md docs/changes docs/PROJECT_REQUIREMENTS.md docs/architecture.md docs/roadmap.md docs/decisions)
PLANNING_APPROVAL_FILE="docs/PLANNING_APPROVAL.md"

# The part of the planning that only a planning cycle may change: what the
# product is and which features it gets. The rest of the scope, the
# architecture and the ADRs, is also kept up to date by features, which the
# Definition of Done asks for and a feature review covers.
PLANNING_PRODUCT_SCOPE=(docs/PROJECT_DESCRIPTION.md docs/changes docs/PROJECT_REQUIREMENTS.md docs/roadmap.md)

# planning_tree_at <root> <scratch> <commit> <path...>
# Prints the fingerprint of the given paths as they are in a commit; it is
# comparable with fingerprint_files of the same content in a working tree.
planning_tree_at() {
  local root="$1"
  local index="$2/planning-tree-at.index"
  local commit="$3"

  shift 3
  rm -f "$index"
  GIT_INDEX_FILE="$index" git -C "$root" read-tree --empty &&
    git -C "$root" ls-tree -r "$commit" -- "$@" |
    GIT_INDEX_FILE="$index" git -C "$root" update-index --index-info &&
    GIT_INDEX_FILE="$index" git -C "$root" write-tree
}

# planning_approval_commit <root> <scratch> <recorded-fingerprint> [<from>]
# Prints the commit that recorded the approval: the last commit before
# <from> (default HEAD) that changed the approval file, when the planning
# documents in that commit have the recorded fingerprint. Prints nothing
# when there is none, for example after the file was edited by hand.
planning_approval_commit() {
  local root="$1"
  local scratch="$2"
  local recorded="$3"
  local from="${4:-HEAD}"
  local commit

  commit="$(git -C "$root" log -1 --format=%H "$from" -- "$PLANNING_APPROVAL_FILE" 2>/dev/null)" || return 0
  [[ -n "$commit" ]] || return 0
  [[ "$(planning_tree_at "$root" "$scratch" "$commit" "${PLANNING_SCOPE[@]}" 2>/dev/null)" == "$recorded" ]] || return 0
  printf '%s\n' "$commit"
}

# planning_feature_updates <root> <from> <to>
# Lists the commits between two commits that changed the architecture or the
# ADRs, oldest first, one per line: "<hash> <subject>", followed by the Issue
# and the review that finish-feature.sh recorded in the commit message, when
# the commit has them.
planning_feature_updates() {
  local root="$1"
  local commit
  local body
  local issue
  local review

  git -C "$root" log --no-merges --reverse --format='%H' "$2..$3" -- docs/architecture.md docs/decisions |
    while IFS= read -r commit; do
      body="$(git -C "$root" log -1 --format=%b "$commit")"
      issue="$(printf '%s\n' "$body" | sed -n 's/^Issue: //p' | head -n 1)"
      review="$(printf '%s\n' "$body" | sed -n 's/^Review: //p' | head -n 1)"
      printf '%s' "$(git -C "$root" log -1 --format='%h %s' "$commit")"
      [[ -z "$issue" && -z "$review" ]] ||
        printf ' (%s%s%s)' "${issue:+Issue $issue}" "${issue:+${review:+; }}" "${review:+review: $review}"
      printf '\n'
    done
}

# planning_recorded_updates <approval-file>
# Prints the updates by merged work that an approval file already records, as
# list items, so that a later approval keeps them.
planning_recorded_updates() {
  [[ -f "$1" ]] || return 0
  awk '
    /^## / { section = $0; next }
    section == "## Updates by merged work" && /^- / { print; next }
    section == "## Amendments after the approval" && /^  - / { sub(/^  /, ""); print }
  ' "$1"
}

# planning_approval_status <root> <scratch-dir>
# Exits 0 when the recorded planning approval is current, 1 when it is missing
# or stale, and 2 when it is malformed. Prints the reason for a non-zero
# status.
#
# The approval is current when the planning documents are as approved. It is
# also current when only the architecture or the ADRs changed since the commit
# that recorded it: features keep those up to date, under their own review.
# PLANNING_APPROVAL_UPDATED_SINCE then holds that commit, and is empty
# otherwise. A change to the description, the requirements, a change request,
# or the roadmap always makes the approval stale.
planning_approval_status() {
  local root="$1"
  local scratch="$2"
  local approval="$root/$PLANNING_APPROVAL_FILE"
  local recorded
  local current

  if [[ ! -f "$approval" ]]; then
    echo "the planning has not been approved: $PLANNING_APPROVAL_FILE is missing."
    return 1
  fi
  grep -Fqx "Status: Approved" "$approval" || {
    echo "$PLANNING_APPROVAL_FILE does not record an approval."
    return 2
  }
  recorded="$(sed -n 's/^Planning fingerprint: \([0-9a-f]\{40,64\}\)$/\1/p' "$approval")"
  [[ "$(printf '%s' "$recorded" | grep -c .)" -eq 1 ]] || {
    echo "$PLANNING_APPROVAL_FILE must contain exactly one valid planning fingerprint."
    return 2
  }
  current="$(fingerprint_files "$root" "$scratch" "${PLANNING_SCOPE[@]}")" || {
    echo "could not compute the fingerprint of the planning documents."
    return 2
  }
  PLANNING_APPROVAL_UPDATED_SINCE=""
  [[ "$current" != "$recorded" ]] || return 0

  local approved
  local product_now
  local product_then

  approved="$(planning_approval_commit "$root" "$scratch" "$recorded")"
  if [[ -n "$approved" ]] && git -C "$root" diff --quiet "$approved" -- "$PLANNING_APPROVAL_FILE" 2>/dev/null; then
    product_now="$(fingerprint_files "$root" "$scratch" "${PLANNING_PRODUCT_SCOPE[@]}")" || product_now=""
    product_then="$(planning_tree_at "$root" "$scratch" "$approved" "${PLANNING_PRODUCT_SCOPE[@]}")" || product_then=""
    if [[ -n "$product_now" && "$product_now" == "$product_then" ]]; then
      PLANNING_APPROVAL_UPDATED_SINCE="$approved"
      return 0
    fi
    echo "the description, the requirements, a change request, or the roadmap changed after the planning was approved; only a planning cycle may change those."
    return 1
  fi
  echo "a planning document changed after the planning was approved."
  return 1
}

# Notes of owner decisions (Issue #512). A decision the owner already took,
# for example in a comment on an Issue, may be recorded in the requirements
# or the roadmap without a change cycle, as a dated note that cites the
# comment. Such a note never adds or changes a requirement: it is a pure
# insertion, and each of its paragraphs begins with the line
#
#   *Note of the owner's decision of YYYY-MM-DD (<URL of the comment>).* ...
#
# where the URL is that of a comment, a review, or a review comment on
# GitHub. The planning reviser may add such notes to the requirements
# (revise-planning.sh), and `finish-planning.sh --amend` approves notes in
# the requirements and the roadmap without a review round.
PLANNING_NOTE_PATTERN='^[[:space:]]*\*Note of the owner'"'"'s decision of [0-9]{4}-[0-9]{2}-[0-9]{2} \(https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(issues|pull)/[0-9]+#(issuecomment|discussion_r|pullrequestreview)-[0-9]+\)\.\*'

# planning_note_errors <old-file> <new-file>
# Prints one line per reason why <new-file> differs from <old-file> by more
# than added notes of owner decisions; prints nothing when it differs by such
# notes only, or not at all. A missing file counts as more than a note.
planning_note_errors() {
  local old="$1"
  local new="$2"
  local line
  local text
  local number=0
  local bad=0
  local open=0
  local hunk_pattern='^@@ -[0-9]+(,([0-9]+))? \+([0-9]+)(,[0-9]+)? @@'
  local heading_pattern='^[[:space:]]?[[:space:]]?[[:space:]]?#'
  local blank_pattern='^[[:space:]]*$'
  local in_hunk=0

  if [[ ! -f "$old" || ! -f "$new" ]]; then
    echo "the document was added or removed; only notes may be added to an existing document."
    return 0
  fi
  while IFS= read -r line; do
    if [[ "$line" =~ $hunk_pattern ]]; then
      in_hunk=1
      number="${BASH_REMATCH[3]}"
      open=0
      bad=0
      # An insertion has an empty old range: '-a,0'.
      if [[ "${BASH_REMATCH[2]}" != "0" ]]; then
        echo "line $number: existing text is changed or removed; a note may only be added."
        bad=1
      fi
      continue
    fi
    [[ "$in_hunk" -eq 1 ]] || continue
    case "$line" in
      +*)
        text="${line#+}"
        number=$((number + 1))
        [[ "$bad" -eq 0 ]] || continue
        if [[ "$text" =~ $blank_pattern ]]; then
          open=0
        elif [[ "$open" -eq 0 ]]; then
          open=1
          if [[ ! "$text" =~ $PLANNING_NOTE_PATTERN ]]; then
            echo "line $((number - 1)): added text that is not a dated note of an owner decision with the URL of the comment: ${text:0:120}"
            bad=1
          fi
        elif [[ "$text" =~ $heading_pattern ]]; then
          echo "line $((number - 1)): a note may not add a heading: ${text:0:120}"
          bad=1
        fi
        ;;
    esac
  done < <(git diff --no-index --no-color --no-ext-diff -U0 -- "$old" "$new" 2>/dev/null)
  return 0
}

# planning_added_notes <root> <base> <path...>
# Prints the first line of every note of an owner decision that the working
# tree at <root> adds to the given documents since <base>, one per line as
# '<path>:<line>: <first line>'.
planning_added_notes() {
  local root="$1"
  local base="$2"
  local line
  local text
  local path=""
  local number=0
  local hunk_pattern='^@@ -[0-9]+(,[0-9]+)? \+([0-9]+)(,[0-9]+)? @@'

  shift 2
  while IFS= read -r line; do
    case "$line" in
      "+++ "*) path="${line#+++ b/}" ;;
      "@@ "*) [[ ! "$line" =~ $hunk_pattern ]] || number="${BASH_REMATCH[2]}" ;;
      +*)
        text="${line#+}"
        if [[ "$text" =~ $PLANNING_NOTE_PATTERN ]]; then
          text="${text#"${text%%[![:space:]]*}"}"
          echo "$path:$number: $text"
        fi
        number=$((number + 1))
        ;;
    esac
  done < <(git -C "$root" diff --no-color --no-ext-diff -U0 "$base" -- "$@" 2>/dev/null)
  return 0
}
