#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$script_dir/lib/review-data.sh"
source "$script_dir/lib/fingerprint.sh"
source "$script_dir/lib/planning.sh"

usage() {
  echo "Usage:"
  echo "  $0                     Check the planning and record your approval (planning worktree)."
  echo "  $0 --check             Report whether the recorded approval still matches the documents."
  echo "  $0 --amend \"<reason>\"  Approve a small technical amendment without a review round."
  echo
  echo "--check exits 0 when the approval is current, 1 when it is missing or stale,"
  echo "and 2 on an error."
  echo
  echo "--amend is for a change to an approved planning that touches only"
  echo "docs/architecture.md and the ADRs in docs/decisions/, such as amending one"
  echo "decision, or that only adds dated notes of decisions you already took to"
  echo "docs/PROJECT_REQUIREMENTS.md or docs/roadmap.md. A note is a new paragraph"
  echo "that begins with"
  echo "  *Note of the owner's decision of YYYY-MM-DD (<URL of your comment>).*"
  echo "and changes no existing line. It runs in a planning worktree or in a feature"
  echo "worktree, so the feature's pull request carries the amendment. It shows the"
  echo "change, asks for your approval, and adds the amendment to the existing"
  echo "approval. Anything else, also a new or changed requirement, needs a change"
  echo "cycle:"
  echo "  ./scripts/start-planning.sh <name> --change <file>"
  exit 2
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

root="$(git rev-parse --show-toplevel)"
review_data_require_jq
tmp_work="$(mktemp -d "${TMPDIR:-/tmp}/finish-planning.XXXXXX")"
trap 'rm -rf "$tmp_work"' EXIT

amend_reason=""
case "$#:${1:-}" in
  0:) ;;
  2:--amend)
    [[ "$2" =~ [^[:space:]] ]] || fail "--amend requires a reason."
    [[ "$2" != *$'\n'* ]] || fail "the reason of an amendment must be a single line."
    amend_reason="$2"
    ;;
  1:--check)
    status=0
    reason_file="$tmp_work/approval-reason"
    planning_approval_status "$root" "$tmp_work" >"$reason_file" || status=$?
    reason="$(<"$reason_file")"
    case "$status" in
      0)
        if [[ -z "$PLANNING_APPROVAL_UPDATED_SINCE" ]]; then
          echo "Current: $PLANNING_APPROVAL_FILE matches the planning documents."
        else
          echo "Current: the description, the requirements, the change requests, and the roadmap are as approved."
          echo "The architecture or the ADRs were updated since the approval, by:"
          planning_feature_updates "$root" "$PLANNING_APPROVAL_UPDATED_SINCE" HEAD | sed 's/^/  /'
          if ! git -C "$root" diff --quiet HEAD -- docs/architecture.md docs/decisions 2>/dev/null; then
            echo "  (and uncommitted changes in this working tree)"
          fi
        fi
        ;;
      1) echo "Not approved: $reason"; echo "Finish the planning again with ./scripts/finish-planning.sh in a planning worktree." ;;
      *) echo "Error: $reason" >&2 ;;
    esac
    exit "$status"
    ;;
  *) usage ;;
esac

branch="$(git branch --show-current)"
if [[ -n "$amend_reason" ]]; then
  # A feature amends the planning it changes in its own pull request.
  [[ "$branch" == planning/* || "$branch" == feature/* ]] ||
    fail "finish-planning.sh --amend must run in a planning or a feature worktree (branch planning/<name> or feature/<issue>-<name>). Current branch: $branch"
else
  [[ "$branch" == planning/* ]] ||
    fail "finish-planning.sh must run in a planning worktree (branch planning/<name>). Current branch: $branch"
fi
name="${branch#planning/}"
name="${name#feature/}"

# planning_base_ref: the base branch the planning is compared with.
planning_base_ref() {
  if git -C "$root" rev-parse --verify --quiet "origin/main^{commit}" >/dev/null; then
    echo "origin/main"
  elif git -C "$root" rev-parse --verify --quiet "main^{commit}" >/dev/null; then
    echo "main"
  fi
}

# An amendment: a change to an approved planning that touches only the
# architecture and the ADRs, approved by the human without a review round.
amend() {
  local base_ref
  local base
  local base_approval
  local recorded
  local base_tree
  local changed
  local path
  local status
  local outside=""
  local files=""
  local fingerprint
  local answer=""
  local approval="$root/$PLANNING_APPROVAL_FILE"
  local approved_commit
  local feature_updates=""
  local entry
  local notes=""
  local note_errors
  local document

  base_ref="$(planning_base_ref)"
  [[ -n "$base_ref" ]] || fail "neither origin/main nor main exists."
  # The amendment is judged against the base branch as it is now, so fetch it
  # when there is a remote; a failed fetch leaves the local state in use.
  [[ "$base_ref" != "origin/main" ]] || git -C "$root" fetch -q origin main 2>/dev/null || true
  base="$(git -C "$root" merge-base HEAD "$base_ref")" ||
    fail "could not determine the merge base of HEAD and $base_ref."
  [[ "$base" == "$(git -C "$root" rev-parse "$base_ref^{commit}")" ]] ||
    fail "$branch does not contain the latest $base_ref. Bring it up to date first (git merge $base_ref), so the amendment is shown and approved against the current planning."

  # The planning that is amended must have been approved as it is on the base
  # branch; an amendment does not repair a missing or stale approval.
  base_approval="$(git -C "$root" show "$base:$PLANNING_APPROVAL_FILE" 2>/dev/null || true)"
  recorded="$(printf '%s\n' "$base_approval" | sed -n 's/^Planning fingerprint: \([0-9a-f]\{40,64\}\)$/\1/p')"
  [[ "$(printf '%s' "$recorded" | grep -c . || true)" -eq 1 ]] ||
    fail "$base_ref has no planning approval to amend. Approve the planning with a review first."
  [[ $'\n'"$base_approval"$'\n' == *$'\n'"Status: Approved"$'\n'* ]] ||
    fail "$PLANNING_APPROVAL_FILE on $base_ref does not record an approval."
  GIT_INDEX_FILE="$tmp_work/base.index" git -C "$root" read-tree --empty
  git -C "$root" ls-tree -r "$base" -- "${PLANNING_SCOPE[@]}" |
    GIT_INDEX_FILE="$tmp_work/base.index" git -C "$root" update-index --index-info
  base_tree="$(GIT_INDEX_FILE="$tmp_work/base.index" git -C "$root" write-tree)"
  if [[ "$base_tree" != "$recorded" ]]; then
    # Features may have updated the architecture or the ADRs on the base
    # since; the approval is still current when nothing else changed.
    approved_commit="$(planning_approval_commit "$root" "$tmp_work" "$recorded" "$base")"
    [[ -n "$approved_commit" ]] &&
      [[ "$(planning_tree_at "$root" "$tmp_work" "$approved_commit" "${PLANNING_PRODUCT_SCOPE[@]}")" == \
      "$(planning_tree_at "$root" "$tmp_work" "$base" "${PLANNING_PRODUCT_SCOPE[@]}")" ]] ||
      fail "the planning on $base_ref changed after its approval, so there is no current approval to amend. Approve it with a review first."
    feature_updates="$(planning_feature_updates "$root" "$approved_commit" "$base")"
  fi

  [[ -f "$approval" && ! -L "$approval" ]] && git -C "$root" diff --quiet "$base" -- "$PLANNING_APPROVAL_FILE" ||
    fail "$PLANNING_APPROVAL_FILE differs from $base_ref. The script updates it; restore it first."

  # What changed in the planning documents, including uncommitted and
  # untracked files.
  fingerprint="$(fingerprint_files "$root" "$tmp_work" "${PLANNING_SCOPE[@]}")" ||
    fail "could not compute the fingerprint of the planning documents."
  changed="$(GIT_INDEX_FILE="$tmp_work/fingerprint-files.index" git -C "$root" diff --cached --no-renames --name-status "$base" -- "${PLANNING_SCOPE[@]}")"
  [[ -n "$changed" ]] || fail "no planning document differs from $base_ref; there is nothing to amend."

  while IFS=$'\t' read -r status path; do
    case "$path" in
      docs/architecture.md) ;;
      docs/PROJECT_REQUIREMENTS.md | docs/roadmap.md)
        # Only dated notes of decisions the owner already took (Issue #512).
        document="$tmp_work/base-$(basename "$path")"
        git -C "$root" show "$base:$path" >"$document" 2>/dev/null || rm -f "$document"
        note_errors="$(planning_note_errors "$document" "$root/$path")"
        if [[ "$status" != "M" || -n "$note_errors" ]]; then
          outside+="  $status $path"$'\n'
          [[ -z "$note_errors" ]] || outside+="$(printf '%s\n' "$note_errors" | sed 's/^/      /')"$'\n'
        fi
        ;;
      docs/decisions/*.md)
        [[ "${path#docs/decisions/}" != */* && "$status" != "D" ]] || outside+="  $status $path"$'\n'
        ;;
      *) outside+="  $status $path"$'\n' ;;
    esac
    files+="${files:+, }$path"
  done <<<"$changed"
  if [[ -n "$outside" ]]; then
    echo "Error: an amendment may change only docs/architecture.md, add or edit ADRs in docs/decisions/," >&2
    echo "and add dated notes of owner decisions to the requirements or the roadmap" >&2
    echo "(a new paragraph beginning with \"*Note of the owner's decision of YYYY-MM-DD (<URL of the comment>).*\")." >&2
    echo "These changes need a review:" >&2
    printf '%s' "$outside" >&2
    echo "Start a change cycle instead: ./scripts/start-planning.sh <name> --change <file>" >&2
    exit 1
  fi
  echo "Amendment to the approved planning on $branch:"
  echo
  GIT_INDEX_FILE="$tmp_work/fingerprint-files.index" git -C "$root" --no-pager diff --cached --no-color "$base" -- "${PLANNING_SCOPE[@]}"
  echo
  echo "Reason: $amend_reason"
  echo "Changed: $files"
  notes="$(planning_added_notes "$root" "$base" docs/PROJECT_REQUIREMENTS.md docs/roadmap.md)"
  if [[ -n "$notes" ]]; then
    echo
    echo "Notes of owner decisions that this amendment adds; check each against the comment it cites:"
    printf '%s\n' "$notes" | sed 's/^/  /'
  fi
  echo
  echo "No agent reviews an amendment; your approval is the only check."
  printf "Approve this amendment? [y/N] "
  read -r answer || true
  case "$answer" in
    y | Y | yes | YES) ;;
    *)
      echo "Declined; the planning approval was not changed."
      exit 0
      ;;
  esac

  [[ "$(fingerprint_files "$root" "$tmp_work" "${PLANNING_SCOPE[@]}")" == "$fingerprint" ]] ||
    fail "a planning document changed while you were deciding; the amendment was not recorded."

  entry="- $(date -u +'%Y-%m-%dT%H:%M:%SZ'), $branch: $amend_reason (changed: $files). Approved by the project owner with \`finish-planning.sh --amend\`, without an independent planning review."
  {
    sed "s/^Planning fingerprint: .*/Planning fingerprint: $fingerprint/" "$approval"
    if ! grep -Fqx "## Amendments after the approval" "$approval"; then
      echo
      echo "## Amendments after the approval"
      echo
      echo "The review rounds above cover the planning as it was first approved. Each"
      echo "amendment below changed only the architecture or the ADRs, or added dated"
      echo "notes of decisions the owner had already taken."
      echo
    fi
    if [[ -n "$feature_updates" ]]; then
      # The fingerprint now also covers what merged work changed since the
      # approval; the record says which commits those were.
      echo "- $(date -u +'%Y-%m-%dT%H:%M:%SZ'): before the amendment below, merged work had updated the architecture or the ADRs since the approval, each change under its own review:"
      printf '%s\n' "$feature_updates" | sed 's/^/  - /'
    fi
    printf '%s\n' "$entry"
    [[ -z "$notes" ]] || printf '%s\n' "$notes" | sed 's/^/  - Note: /'
  } >"$tmp_work/approval"
  cp "$tmp_work/approval" "$approval"

  echo
  echo "Recorded the amendment in $PLANNING_APPROVAL_FILE."
  echo
  if [[ "$branch" == feature/* ]]; then
    echo "Next: the amendment is part of this feature. finish-feature.sh commits it with"
    echo "the feature, and the feature's pull request carries it. A later change to a"
    echo "planning document of the amendment makes it stale; run --amend again then."
    return 0
  fi
  echo "Next steps:"
  echo "  ./scripts/verify.sh"
  echo "  git add ${files//, / } $PLANNING_APPROVAL_FILE"
  echo "  git commit -m \"Amend planning: $name\""
  echo "  git push -u origin \"$branch\""
  echo
  echo "Open the planning PR and merge it; then, from the primary checkout:"
  echo "  ./scripts/cleanup-worktree.sh $branch"
}

# 1. The planning documents exist and the requirements are approved.
for required in docs/PROJECT_REQUIREMENTS.md docs/architecture.md docs/roadmap.md; do
  [[ -f "$root/$required" && ! -L "$root/$required" && -s "$root/$required" ]] ||
    fail "required planning document is missing or empty: $required"
done
grep -Fqx "Status: Approved" "$root/docs/PROJECT_REQUIREMENTS.md" ||
  fail "the project requirements are not approved."

# An amendment replaces the review of steps 2 to 4 by its own checks.
if [[ -n "$amend_reason" ]]; then
  amend
  exit 0
fi

# 2. The latest planning review exists, is valid, and is current.
shopt -s nullglob
reviews=("$root/.agents/reviews/planning-${name}-review-"[0-9][0-9].json)
shopt -u nullglob
[[ "${#reviews[@]}" -gt 0 ]] || fail "no planning review exists. Run ./scripts/review-planning.sh first."
latest="${reviews[${#reviews[@]}-1]}"
latest_relative="${latest#"$root"/}"
review_errors="$(review_artifact_errors "$latest")"
[[ -z "$review_errors" ]] || fail "the latest planning review is invalid: ${review_errors//$'\n'/; }"
[[ "$(jq -r '.kind' "$latest")" == "planning" && "$(jq -r '.branch' "$latest")" == "$branch" ]] ||
  fail "$latest_relative is not a planning review of $branch."

current=0
review_is_current "$root" "$tmp_work" "$latest" || current=$?
case "$current" in
  0) ;;
  1)
    review_stale_notice "$root" "$tmp_work" "$latest"
    fail "the latest planning review ($latest_relative) is stale: a planning document changed after it. Run ./scripts/review-planning.sh again."
    ;;
  *) fail "could not compute the fingerprint of the planning documents." ;;
esac

# Every rejected, deferred, or escalated decision of every round, oldest first.
shopt -s nullglob
revisions=("$root/.agents/reviews/planning-${name}-review-"[0-9][0-9]-revision.json)
shopt -u nullglob
decisions_file="$tmp_work/decisions.json"
if [[ "${#revisions[@]}" -gt 0 ]]; then
  jq -s '[.[] | .review_round as $round | .decisions[]
          | select(.decision != "ADOPT") | . + {round: $round}]' "${revisions[@]}" >"$decisions_file"
else
  echo '[]' >"$decisions_file"
fi

round="$(jq -r '.round' "$latest")"
verdict="$(jq -r '.verdict' "$latest")"

# Show every finding that was not adopted before any refusal, so the reasons
# are visible.
if [[ "$(jq 'length' "$decisions_file")" -gt 0 ]]; then
  echo "Findings that were not adopted:"
  jq -r '.[] | "- Round \(.round), \(.decision): \(.finding_id) [\(.severity)] \(.title)\n  Rationale: \(.rationale)"' "$decisions_file"
  echo
fi

# 3. The latest round is resolved: no critical or major finding, every finding
#    decided, nothing adopted but not yet applied, and nothing escalated. A
#    suggestion needs no revision round (Issue #512): it is listed in the
#    approval for the next cycle, decided or not, adopted or not.
blocking="$(jq '[.findings[] | select(.severity == "critical" or .severity == "major")] | length' "$latest")"
[[ "$blocking" -eq 0 ]] ||
  fail "the latest planning review (round $round) has $blocking critical or major finding(s). Revise with ./scripts/revise-planning.sh and review again."

revision="${latest%.json}-revision.json"
if [[ "$(jq '[.findings[] | select(.severity != "suggestion")] | length' "$latest")" -gt 0 ]]; then
  [[ -f "$revision" ]] ||
    fail "the findings of round $round have no revision decisions. Run ./scripts/revise-planning.sh --review $latest_relative."
  revision_errors="$(revision_artifact_errors "$revision" "$latest")"
  [[ -z "$revision_errors" ]] || fail "the revision of round $round is invalid: ${revision_errors//$'\n'/; }"
  [[ "$(jq '[.decisions[] | select(.decision == "ADOPT" and .severity != "suggestion")] | length' "$revision")" -eq 0 ]] ||
    fail "round $round has adopted findings that are not applied yet. Run ./scripts/revise-planning.sh --review $latest_relative and review again."
elif [[ -f "$revision" ]]; then
  revision_errors="$(revision_artifact_errors "$revision" "$latest")"
  [[ -z "$revision_errors" ]] || fail "the revision of round $round is invalid: ${revision_errors//$'\n'/; }"
fi

# The suggestions of the latest round, for the approval and the next cycle.
suggestions="$(jq -r '.findings[] | select(.severity == "suggestion") | "- \(.id) \(.title). \(.recommendation)"' "$latest")"
if [[ -n "$suggestions" ]]; then
  echo "Suggestions of round $round, which need no revision round; the approval lists them"
  echo "for the next cycle:"
  printf '%s\n' "$suggestions"
  echo
fi

# The notes of owner decisions that this planning adds to the requirements and
# the roadmap (Issue #512): the reviser may add them instead of escalating.
# Check each against the comment it cites before you approve.
notes=""
notes_base_ref="$(planning_base_ref)"
if [[ -n "$notes_base_ref" ]] && notes_base="$(git -C "$root" merge-base HEAD "$notes_base_ref" 2>/dev/null)"; then
  notes="$(planning_added_notes "$root" "$notes_base" docs/PROJECT_REQUIREMENTS.md docs/roadmap.md)"
fi
if [[ -n "$notes" ]]; then
  echo "Notes of owner decisions that this planning adds; check each against the comment it cites:"
  printf '%s\n' "$notes" | sed 's/^/  /'
  echo
fi

escalated_now="$(jq --argjson round "$round" '[.[] | select(.round == $round and .decision == "ESCALATE")] | length' "$decisions_file")"
[[ "$escalated_now" -eq 0 ]] ||
  fail "round $round has $escalated_now escalated finding(s). Resolve them through Project Grill and a new review round, or decide that they do not apply."

# 4. Escalations of earlier rounds need an explicit resolution by the human;
#    a newer review alone does not resolve them.
earlier_escalations="$(jq -r --argjson round "$round" '
  .[] | select(.round < $round and .decision == "ESCALATE") | "- Round \(.round): \(.finding_id) \(.title)"
' "$decisions_file")"
if [[ -n "$earlier_escalations" ]]; then
  echo "Escalated in earlier rounds:"
  printf '%s\n' "$earlier_escalations"
  printf "Was each of these resolved, by changing the requirements through Project Grill or by deciding that it does not apply? [y/N] "
  resolved=""
  read -r resolved || true
  case "$resolved" in
    y | Y | yes | YES) ;;
    *) fail "the escalated findings of earlier rounds are not resolved." ;;
  esac
  echo
fi

# 5. Ask for approval of exactly the reviewed planning.
reviewed_fingerprint="$(jq -r '.reviewed_tree' "$latest")"
echo "Planning ready for approval:"
echo "  Branch:        $branch"
echo "  Final review:  $latest_relative (round $round, ${verdict//_/ })"
echo

printf "Approve this planning? [y/N] "
approval=""
read -r approval || true
case "$approval" in
  y | Y | yes | YES) ;;
  *)
    echo "Declined; the planning approval was not recorded."
    exit 0
    ;;
esac

# 6. Record the approval for the reviewed planning, and only if it did not
#    change while you were deciding.
fingerprint="$(fingerprint_files "$root" "$tmp_work" "${PLANNING_SCOPE[@]}")" ||
  fail "could not compute the fingerprint of the planning documents."
[[ "$fingerprint" == "$reviewed_fingerprint" ]] ||
  fail "a planning document changed after the final review; the approval was not recorded. Run ./scripts/review-planning.sh again."

# What merged work changed in the architecture and the ADRs since the
# previous approval: this approval covers those changes too, so it names them.
previous_updates=""
recorded_updates="$(planning_recorded_updates "$root/$PLANNING_APPROVAL_FILE")"
if [[ -f "$root/$PLANNING_APPROVAL_FILE" ]]; then
  previous_recorded="$(sed -n 's/^Planning fingerprint: \([0-9a-f]\{40,64\}\)$/\1/p' "$root/$PLANNING_APPROVAL_FILE" | head -n 1)"
  if [[ -n "$previous_recorded" ]]; then
    previous_commit="$(planning_approval_commit "$root" "$tmp_work" "$previous_recorded")"
    [[ -z "$previous_commit" ]] ||
      previous_updates="$(planning_feature_updates "$root" "$previous_commit" HEAD)"
  fi
fi
{
  echo "# Planning Approval"
  echo
  echo "Status: Approved"
  echo "Approved at: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "Planning branch: $branch"
  [[ ! -f "$root/docs/changes/$name.md" ]] || echo "Change request: docs/changes/$name.md"
  echo "Final review: round $round, ${verdict//_/ }, by $(jq -r '"\(.reviewer.agent) (\(.reviewer.model))"' "$latest")"
  echo "Planning fingerprint: $fingerprint"
  echo
  echo "Recorded by \`scripts/finish-planning.sh\`. The approval covers these planning"
  echo "documents. A change to the description, the requirements, a change request, or the"
  echo "roadmap makes it stale; the architecture and the ADRs may be updated by features"
  echo "(\`./scripts/finish-planning.sh --check\`):"
  echo
  for path in "${PLANNING_SCOPE[@]}"; do
    echo "- \`$path\`"
  done
  echo
  if [[ -n "$previous_updates" || -n "$recorded_updates" ]]; then
    echo "## Updates by merged work"
    echo
    echo "These commits changed the architecture or the ADRs between approvals, each"
    echo "under its own review. This approval covers the documents including them."
    echo
    [[ -z "$recorded_updates" ]] || printf '%s\n' "$recorded_updates"
    [[ -z "$previous_updates" ]] || printf '%s\n' "$previous_updates" | sed 's/^/- /'
    echo
  fi
  echo "## Review rounds"
  echo
  for review in "${reviews[@]}"; do
    jq -r '"- Round \(.round): \(.verdict | gsub("_"; " ")), \(.findings | length) finding(s), by \(.reviewer.agent) (\(.reviewer.model))"' "$review"
  done
  echo
  if [[ -n "$earlier_escalations" ]]; then
    echo "## Escalations confirmed as resolved"
    echo
    printf '%s\n' "$earlier_escalations"
    echo
  fi
  if [[ -n "$notes" ]]; then
    echo "## Notes of owner decisions"
    echo
    echo "Added in this cycle; each records a decision the owner had already taken, with"
    echo "the URL of the comment, and changes no requirement."
    echo
    printf '%s\n' "$notes" | sed 's/^/- /'
    echo
  fi
  if [[ -n "$suggestions" ]]; then
    echo "## Suggestions for the next cycle"
    echo
    echo "Suggestions of the final review round; they needed no revision round."
    echo
    printf '%s\n' "$suggestions"
    echo
  fi
  echo "## Findings that were not adopted"
  echo
  if [[ "$(jq 'length' "$decisions_file")" -eq 0 ]]; then
    echo "None."
  else
    jq -r '.[] | "- Round \(.round), \(.decision): \(.finding_id) [\(.severity)] \(.title). \(.rationale)"' "$decisions_file"
  fi
} >"$root/$PLANNING_APPROVAL_FILE"

echo
echo "Recorded the approval in $PLANNING_APPROVAL_FILE."
echo
echo "Next steps:"
echo "  ./scripts/verify.sh"
to_add=()
for path in "${PLANNING_SCOPE[@]}"; do
  [[ ! -e "$root/$path" ]] || to_add+=("$path")
done
echo "  git add ${to_add[*]} $PLANNING_APPROVAL_FILE"
if [[ -f "$root/docs/changes/$name.md" ]]; then
  echo "  git commit -m \"Plan change: $name\""
else
  echo "  git commit -m \"Plan project bootstrap\""
fi
echo "  git push -u origin \"$branch\""
echo
echo "Open the planning PR; $PLANNING_APPROVAL_FILE summarizes the review rounds and the"
echo "findings that were not adopted for its description. After the merge, from the"
echo "primary checkout:"
echo "  ./scripts/cleanup-worktree.sh $branch    # removes this worktree and updates main"
echo "  ./scripts/create-feature-issue.sh <feature-id>    # for example F01"
