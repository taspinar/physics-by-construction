#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$script_dir/lib/review-data.sh"
source "$script_dir/lib/fingerprint.sh"
source "$script_dir/lib/planning.sh"
source "$script_dir/lib/guardrails.sh"
source "$script_dir/lib/completion.sh"
source "$script_dir/lib/verification.sh"
source "$script_dir/lib/risk.sh"
source "$script_dir/lib/review-chain.sh"

usage() {
  echo "Usage: $0 <issue-number> \"<commit summary>\" [--no-review \"<reason>\"] [--unattended] [--partial]"
  echo
  echo "Run in the feature worktree. Checks that the feature is complete, that"
  echo "verification passes, and that the latest independent review is current,"
  echo "resolved, and covers the complete feature, then commits the feature with an"
  echo "editable, structured message. It never pushes or merges."
  echo
  echo "Complete means: the implementer's completion record (.agents/completion/"
  echo "<issue>.json) says complete with evidence for every acceptance criterion,"
  echo "and the handoff note lists no remaining work. A record whose only unmet"
  echo "criteria are pending for a later gate (CI, the owner's approval, or a"
  echo "measurement after the merge) is ready for a pull request: it is committed"
  echo "as it is, and the pull request does not close the Issue (ADR 020 decision"
  echo "2). --partial commits other work that is not complete, as your explicit"
  echo "choice: the commit message says what remains, and publish-feature.sh then"
  echo "opens a draft pull request that does not close the Issue."
  echo
  echo "The commit message records the risk level of the change (ADR 020 decision"
  echo "1) and what it requires. With a completion/v2 record, a stated level below"
  echo "the derived one is refused unless the approval request"
  echo "(.agents/approvals/<issue>.md) names the lowering the owner asked for, a"
  echo "Level 3 change by trigger or assessment needs that request, and a Level 3"
  echo "change needs a full verification of this content and a latest review made"
  echo "on a fully verified tree."
  echo
  echo "The review follows the level (ADR 020 decision 4), with a completion/v2"
  echo "record: a Level 1 change needs no review, which the message records; a"
  echo "Level 2 change is committed on a chain of reviews that begins with a review"
  echo "of the complete feature, builds every review of changes on the round right"
  echo "before it, ends at exactly this content, and leaves no finding open; a Level"
  echo "3 change on a review of the complete feature in every round, the latest"
  echo "made on its full verification."
  echo "With a completion/v1 record the latest review covers the complete feature."
  echo
  echo "--no-review is only for changes that .agents/policies/autonomy.md classifies"
  echo "as low risk; the reason is recorded in the commit message. With a"
  echo "completion/v2 record it is refused at Level 1, which needs no review, and"
  echo "at Level 3."
  echo
  echo "The list of changes in the message comes from .agents/summaries/<issue>.md,"
  echo "which the implementer writes. --unattended commits that message as it is,"
  echo "without opening an editor, and refuses when that summary is missing."
  exit 1
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

unattended=0
partial=0
arguments=()
for argument in "$@"; do
  case "$argument" in
    --unattended) unattended=1 ;;
    --partial) partial=1 ;;
    *) arguments+=("$argument") ;;
  esac
done
set -- ${arguments[@]+"${arguments[@]}"}

[[ $# -eq 2 || ( $# -eq 4 && "$3" == "--no-review" ) ]] || usage
issue="$1"
summary="$2"
no_review_reason="${4:-}"

[[ "$issue" =~ ^[0-9]+$ ]] || fail "issue number must be numeric: $issue"
[[ "$summary" =~ [^[:space:]] ]] || fail "the commit summary is empty."
[[ $# -eq 2 || "$no_review_reason" =~ [^[:space:]] ]] || fail "--no-review requires a reason."

root="$(git rev-parse --show-toplevel)"
branch="$(git branch --show-current)"
[[ "$branch" == feature/${issue}-* ]] ||
  fail "finish-feature.sh must run on feature/${issue}-*. Current branch: $branch"

[[ -n "$(git -C "$root" status --porcelain)" ]] || fail "there are no changes to commit."
review_data_require_jq

# The completion gate: a feature is committed as done only when the
# implementer's completion record says so and nothing contradicts it. The
# record is a claim; the review of the complete feature, checked below, is
# what confirms it against the code.
completion_file="$(completion_record "$root" "$issue")"
if [[ -f "$completion_file" ]]; then
  git -C "$root" check-ignore -q "$COMPLETION_DIR/$issue.json" ||
    fail "Git does not ignore $COMPLETION_DIR/$issue.json, so it would be committed. Add '$COMPLETION_DIR/' to .gitignore, or take over the template's .gitignore with ./scripts/sync-template.sh."
fi
gate="$(completion_gate "$root" "$issue")"
gate_status="$(printf '%s\n' "$gate" | sed -n 1p)"
gate_reasons="$(printf '%s\n' "$gate" | sed 1d)"
refuse_incomplete() {
  echo "Error: $1" >&2
  [[ -z "$gate_reasons" ]] || printf '%s\n' "$gate_reasons" | sed 's/^/  - /' >&2
  echo "$2" >&2
  echo "Nothing was committed." >&2
  exit 1
}
case "$gate_status" in
  complete)
    [[ "$partial" -eq 0 ]] ||
      fail "--partial was given, but the completion gate passes: the feature is complete. Run without --partial."
    ;;
  pending)
    # Ready for a pull request (ADR 020 decision 2): what is not met waits
    # for CI, the owner, or the merge. No exception is needed for that.
    [[ "$partial" -eq 0 ]] ||
      fail "--partial was given, but the only unmet criteria are pending for later gates, so the feature is ready for a pull request. Run without --partial."
    ;;
  partial | blocked)
    [[ "$partial" -eq 1 ]] ||
      refuse_incomplete "the feature is not complete ($gate_status):" \
        "Continue the work with ./scripts/start-feature.sh $issue --resume. To commit the work as it is, as your own choice, add --partial: the pull request then stays a draft and does not close Issue #$issue."
    # The commit message is made from the record. A record that says complete
    # while the handoff note lists remaining work would be committed as
    # complete, so the record has to say what is left first.
    [[ "$(jq -r '.status' "$completion_file")" != "complete" ]] ||
      refuse_incomplete "the completion record says complete, so the work cannot be committed as partial:" \
        "Correct $COMPLETION_DIR/$issue.json first: the status partial or blocked, the criteria that are not met, and what remains. Then run again with --partial."
    ;;
  missing)
    refuse_incomplete "the completion gate does not pass:" \
      "The implementer writes the completion record (.agents/prompts/implementer.md, 'Completion'); resume it with ./scripts/start-feature.sh $issue --resume, or write the record yourself."
    ;;
  *)
    refuse_incomplete "the completion record cannot be used:" \
      "Correct $COMPLETION_DIR/$issue.json (.agents/prompts/implementer.md, 'Completion'), or resume the implementer with ./scripts/start-feature.sh $issue --resume."
    ;;
esac
completion_lines="$(completion_commit_lines "$root" "$issue")"
if [[ "$gate_status" == "pending" ]]; then
  completion_lines+=$'\n\n'"Readiness: ready for a pull request; Issue #$issue stays open until these criteria are met:"
  completion_lines+=$'\n'"$(printf '%s\n' "$gate_reasons" | sed 's/^/- /')"
fi

# A feature keeps the architecture and the ADRs up to date, but it does not
# change what the product is or which features it gets, nor the approval
# itself: that makes the planning approval stale and needs a planning cycle.
# Checked in a project with an approved planning, on the feature's base or
# in the working tree.
feature_merge_base=""
feature_base_ref=""
latest=""
feature_base_branch="$(git -C "$root" config --get "branch.$branch.workflow-base" || true)"
if feature_base_lines="$(feature_base "$root" "${feature_base_branch:-main}")"; then
  feature_merge_base="$(printf '%s\n' "$feature_base_lines" | sed -n 2p)"
  feature_base_ref="$(guardrails_rules_refs "$root" "${feature_base_branch:-main}")"
  if [[ -f "$root/$PLANNING_APPROVAL_FILE" ]] ||
    git -C "$root" cat-file -e "$feature_merge_base:$PLANNING_APPROVAL_FILE" 2>/dev/null; then
    planning_changes="$(
      git -C "$root" diff --name-only "$feature_merge_base" -- "${PLANNING_PRODUCT_SCOPE[@]}" "$PLANNING_APPROVAL_FILE"
      git -C "$root" ls-files --others --exclude-standard -- "${PLANNING_PRODUCT_SCOPE[@]}" "$PLANNING_APPROVAL_FILE"
    )"
    if [[ -n "$planning_changes" ]]; then
      echo "Error: this feature changes planning documents that only a planning cycle may change:" >&2
      printf '%s\n' "$planning_changes" | sort -u | sed 's/^/  /' >&2
      echo "Take these changes out of the feature, and make them through a change cycle:" >&2
      echo "  ./scripts/start-planning.sh <name> --change <file>" >&2
      echo "The architecture and the ADRs may be updated in a feature. Nothing was committed." >&2
      exit 1
    fi
  fi
elif [[ -f "$root/$PLANNING_APPROVAL_FILE" ]] || git -C "$root" cat-file -e "HEAD:$PLANNING_APPROVAL_FILE" 2>/dev/null; then
  fail "could not determine the base of $branch, so it cannot be checked that the feature leaves the approved planning as it is. Nothing was committed."
fi

# The risk level of the change (ADR 020 decision 1), derived from the diff
# against the base, the completion record, and the latest review. A
# completion/v2 record is held to its rules; the level of a completion/v1
# record, of a feature started before ADR 020, is only recorded.
slug="${branch//\//-}"
shopt -s nullglob
reviews=("$root/.agents/reviews/${slug}-review-"[0-9][0-9].json)
shopt -u nullglob
latest_candidate=""
[[ "${#reviews[@]}" -eq 0 ]] || latest_candidate="${reviews[${#reviews[@]}-1]}"
risk_known=0
if [[ -n "$feature_merge_base" ]] && risk_assess "$root" "$feature_base_ref" "$feature_merge_base" "$issue" "$latest_candidate"; then
  risk_known=1
elif [[ "$(jq -r '.schema' "$completion_file" 2>/dev/null)" == "completion/v2" ]]; then
  fail "the risk level of the change cannot be derived (the base of the feature could not be determined). Nothing was committed."
fi
level3=0
enforced=0
if [[ "$risk_known" -eq 1 && "$RISK_ENFORCED" -eq 1 ]]; then
  enforced=1
  if [[ -n "$RISK_ERRORS" ]]; then
    echo "Error: the risk level of the change is not consistent (ADR 020 decision 1):" >&2
    printf '%s\n' "$RISK_ERRORS" | sed 's/^/  - /' >&2
    echo "No agent lowers a required level. Nothing was committed." >&2
    exit 1
  fi
  [[ "$RISK_REQUIRED" -ne 3 ]] || level3=1
fi

# 1. Verification passes, in the tier the change needs (ADR 017 decision 7):
# the targeted run for an ordinary change, which the implementer runs last
# and which refuses a change that needs the full run or the run with a base.
# A pass that was already recorded for exactly this content, of any tier, by
# the implementer, apply-triage.sh, or review-feature.sh, is not repeated.
# A Level 3 change is accepted on a complete verification of its final tree
# (ADR 020 decision 5): the full run, or its recorded pass for exactly this
# content. Partial runs of the fix rounds were feedback, never evidence.
echo "Checking repository verification..."
if [[ "$level3" -eq 1 ]]; then
  echo "The change is Level 3: its final tree needs the full verification."
  (cd "$root" && ./scripts/verify.sh --reuse) || fail "verification failed; nothing was committed."
  [[ "$(verification_tier "$root")" == "full" ]] ||
    fail "a Level 3 change needs a full verification of its final tree, and the recorded pass is a $(verification_tier "$root") run. Nothing was committed."
else
  (cd "$root" && ./scripts/verify.sh --reuse --targeted) || fail "verification failed; nothing was committed."
fi
echo
# What the commit message says about it: the tier of the recorded pass and,
# for a run with a base, the base and the selection.
verification_lines="- ./scripts/verify.sh passed"
case "$(verification_tier "$root")" in
  targeted)
    verification_lines="- ./scripts/verify.sh --targeted passed (the targeted run: no site built locally; CI builds and checks the site)"
    ;;
  base)
    verification_lines="- ./scripts/verify.sh --base passed (every check, against a base)"
    ;;
esac
if [[ -n "$(verification_field "$root" base)" ]]; then
  verification_lines+=$'\n'"- base: $(verification_field "$root" base)"
fi
if [[ -n "$(verification_field "$root" selection)" ]]; then
  verification_lines+=$'\n'"- selection: $(verification_field "$root" selection)"
fi

# 2. The latest review is current and resolved, unless explicitly skipped.
if [[ -n "$no_review_reason" ]]; then
  [[ "$level3" -eq 0 ]] ||
    fail "the change is Level 3, which keeps a full independent review (ADR 020 decision 4): --no-review is refused. Nothing was committed."
  # Level 1 needs no review by the rule of the level, never as an exception.
  [[ "$enforced" -eq 0 || "$RISK_REQUIRED" -ne 1 ]] ||
    fail "the change is Level 1, which needs no independent review (ADR 020 decision 4) and records that as the rule of the level: --no-review is refused. Run ./scripts/finish-feature.sh without it. Nothing was committed."
  review_line="Review: no independent review (low risk: $no_review_reason)"
elif [[ "$enforced" -eq 1 && "$RISK_REQUIRED" -eq 1 && "${#reviews[@]}" -eq 0 ]]; then
  # Level 1 needs no independent review (ADR 020 decision 4); that is the
  # rule of the level, not an exception. A review that exists is checked as
  # at Level 2.
  review_line="Review: none required (Level 1: documentation and process files only; ADR 020 decision 4)"
else
  [[ "${#reviews[@]}" -gt 0 ]] ||
    fail "no review of this feature exists. Run ./scripts/review-feature.sh $issue, or use --no-review for a low-risk change."
  latest="${reviews[${#reviews[@]}-1]}"
  latest_relative="${latest#"$root"/}"

  errors="$(review_artifact_errors "$latest")"
  [[ -z "$errors" ]] || fail "the latest review is invalid: ${errors//$'\n'/; }"
  [[ "$(jq -r '.kind // "feature"' "$latest")" == "feature" && "$(jq -r '.issue' "$latest")" == "$issue" ]] ||
    fail "$latest_relative is not a review of Issue #$issue."

  tmp_work="$(mktemp -d "${TMPDIR:-/tmp}/finish-feature.XXXXXX")"
  trap 'rm -rf "$tmp_work"' EXIT
  current=0
  review_is_current "$root" "$tmp_work" "$latest" || current=$?
  case "$current" in
    0) ;;
    1)
      review_stale_notice "$root" "$tmp_work" "$latest"
      fail "the latest review ($latest_relative) is stale: the code changed after it. Run ./scripts/review-feature.sh $issue again."
      ;;
    *) fail "could not compute the fingerprint of the working tree." ;;
  esac

  # The review that a commit rests on covers the complete feature, or, at
  # Level 1 or 2 under a completion/v2 record, is the end of a chain that
  # begins with one (ADR 020 decision 4), checked below. Under a
  # completion/v1 record a round that reviewed only changes confirms fixes;
  # whether the Issue is done is judged on the whole diff against the Issue.
  [[ "$(jq -r '.scope.kind // "full"' "$latest")" != "changes" || ( "$enforced" -eq 1 && "$level3" -eq 0 ) ]] ||
    fail "the latest review (round $(jq -r '.round' "$latest")) covers only the changes since round $(jq -r '.scope.since_round' "$latest"). A feature is committed on a review of the complete feature: run ./scripts/review-feature.sh $issue (without --changes)."

  # The final review of a Level 3 change is made on the tree the full run
  # verified, after it (ADR 020 decision 5): a review made with --unverified
  # or on the feedback of a partial run is not the final one.
  if [[ "$level3" -eq 1 ]]; then
    review_verification="$(jq -r 'if (.verification | type) != "object" then "none"
      elif .verification.status == "passed" then (.verification.tier // "full") else .verification.status end' "$latest")"
    [[ "$review_verification" == "full" ]] ||
      fail "the change is Level 3, and the latest review (round $(jq -r '.round' "$latest")) was not made on a fully verified tree (its verification: $review_verification). Run the full ./scripts/verify.sh, then ./scripts/review-feature.sh $issue without --unverified or --feedback."
    # Level 3 keeps a review of the complete feature in every round (ADR 020
    # decision 4), not only in the latest one.
    for review in "${reviews[@]}"; do
      [[ "$(jq -r '.scope.kind // "full"' "$review")" != "changes" ]] ||
        fail "the change is Level 3, which keeps a review of the complete feature in every round (ADR 020 decision 4), and round $(jq -r '.round' "$review") covers only the changes since round $(jq -r '.scope.since_round' "$review"). Nothing was committed."
    done
  fi

  round="$(jq -r '.round' "$latest")"
  verdict="$(jq -r '.verdict | gsub("_"; " ")' "$latest")"
  blocking="$(jq '[.findings[] | select(.severity == "critical" or .severity == "major")] | length' "$latest")"
  [[ "$blocking" -eq 0 ]] ||
    fail "the latest review (round $round) has $blocking critical or major finding(s). Triage, fix, and review again."

  # Every round with findings needs an approved triage that was published on
  # the Issue; only the latest round may not have FIX_NOW findings left, since
  # a newer, current review confirms the fixes of earlier rounds. At Level 1
  # or 2 under a completion/v2 record, an earlier round without a triage
  # whose findings a later review of the chain all gives as resolved or
  # accepted needs none: the chain, checked below, closes them (Issue #326).
  # Level 3 keeps the triage of every round with the owner's approval.
  triage_note=""
  dispositioned_rounds=()
  for review in "${reviews[@]}"; do
    [[ "$(jq '.findings | length' "$review")" -gt 0 ]] || continue
    review_round="$(jq -r '.round' "$review")"
    triage="$(review_latest_triage "$root" "$review")"
    if [[ -z "$triage" && "$enforced" -eq 1 && "$level3" -eq 0 && "$review" != "$latest" ]] &&
      review_chain_dispositioned "$root" "$slug" "$review"; then
      dispositioned_rounds+=("$review_round")
      continue
    fi
    [[ -n "$triage" ]] ||
      fail "the findings of round $review_round are not triaged. Run ./scripts/triage-review.sh ${review#"$root"/}."
    triage_relative="${triage#"$root"/}"
    errors="$(triage_artifact_errors "$triage" "$review")"
    [[ -z "$errors" ]] || fail "the triage of round $review_round is invalid: ${errors//$'\n'/; }"
    # Every finding of a Level 3 change keeps the full triage with the
    # owner's approval (ADR 020 decision 4).
    [[ "$level3" -eq 0 || "$(jq -r '.mechanical // false' "$triage")" != "true" ]] ||
      fail "the change is Level 3, and the triage of round $review_round was made mechanically; every finding of a Level 3 change keeps the full triage with the owner's approval. Run ./scripts/triage-review.sh ${review#"$root"/} again."
    [[ "$(jq -r '.published_at // empty' "$triage")" != "" ]] ||
      fail "the triage of round $review_round was not published on Issue #$issue. Run ./scripts/triage-review.sh --publish $triage_relative."
    if [[ "$review" == "$latest" ]]; then
      [[ "$(jq '[.decisions[] | select(.decision == "FIX_NOW")] | length' "$triage")" -eq 0 ]] ||
        fail "round $review_round has FIX_NOW findings. Apply them with ./scripts/apply-triage.sh $triage_relative and review again."
    fi
    triage_note="; triage published on #$issue"
  done
  if [[ "${#dispositioned_rounds[@]}" -gt 0 ]]; then
    triage_note+="; the findings of round $(IFS=,; printf '%s' "${dispositioned_rounds[*]}" | sed 's/,/, /g') given their disposition by a later review, without a triage"
  fi

  # The chain of reviews (ADR 020 decision 4): from a review of the complete
  # feature, contiguous, every review of changes bounded, every earlier open
  # finding given its disposition, and no finding open.
  chain_note=""
  if [[ "$enforced" -eq 1 ]]; then
    errors="$(review_chain_errors "$root" "$feature_base_ref" "$slug" "$latest")"
    if [[ -n "$errors" ]]; then
      echo "Error: the chain of reviews does not hold (ADR 020 decision 4):" >&2
      printf '%s\n' "$errors" | sed 's/^/  - /' >&2
      echo "A gap, a break, or a review of changes whose reach is not certain needs a review of the complete feature: run ./scripts/review-feature.sh $issue. An open finding is fixed and given its disposition in the next review. Nothing was committed." >&2
      exit 1
    fi
    if [[ "$(jq -r '.scope.kind // "full"' "$latest")" == "changes" ]]; then
      chain_note="; reviews of changes since round $(jq -r '.round' "$(review_chain_baseline "$root" "$latest" | sed -n 1p)"), a review of the complete feature, with every finding given its disposition"
    fi
  fi
  review_line="Review: round $round, $verdict, by $(jq -r '"\(.reviewer.agent) (\(.reviewer.model))"' "$latest")$chain_note$triage_note"
fi

# 3. Show the manual steps the implementer recorded for this feature.
manual_steps="- none"
manual_file="$root/.agents/manual-steps/$issue.md"
if [[ -f "$manual_file" ]] && grep -q '[^[:space:]]' "$manual_file"; then
  manual_steps="$(grep '[^[:space:]]' "$manual_file")"
  echo "This feature needs these manual steps from you:"
  printf '%s\n' "$manual_steps" | sed 's/^/  /'
  echo
fi

# The implementer's summary of the changes. Lines that are not list items are
# left out, so the message keeps its shape.
changes="- TODO: summarize the main changes"
summary_file="$root/.agents/summaries/$issue.md"
if [[ -f "$summary_file" ]]; then
  git -C "$root" check-ignore -q ".agents/summaries/$issue.md" ||
    fail "Git does not ignore .agents/summaries/$issue.md, so it would be committed. Add '.agents/summaries/' to .gitignore, or take over the template's .gitignore with ./scripts/sync-template.sh."
fi
if [[ -f "$summary_file" ]] && grep -q '^[[:space:]]*- [^[:space:]]' "$summary_file"; then
  changes="$(grep '^[[:space:]]*- [^[:space:]]' "$summary_file" | sed 's/^[[:space:]]*//')"
elif [[ "$unattended" -eq 1 ]]; then
  # Nobody edits the message of an unattended commit, so it would go out
  # without saying what changed.
  fail "the implementer supplied no summary of the changes (.agents/summaries/$issue.md), and an unattended commit is not edited. Resume the implementer with ./scripts/start-feature.sh $issue --resume, or write the summary. Nothing was committed."
fi

# The merge approval gate: whether the owner must approve the merge of this
# feature. The rules are checked on the diff, by the rules of the base; the
# independent reviewer classified the impact. The heaviest of the two decides,
# and a missing classification gives no permission.
if [[ -n "$feature_merge_base" ]]; then
  approval_lines="$(guardrails_decision "$root" "$feature_base_ref" "$feature_merge_base" "$latest")"
else
  approval_lines="owner"$'\n'"the base of the feature could not be determined, so the gate could not check the diff"
fi
# The owner approves a Level 3 change and authorizes every lowering (ADR 020
# decision 3), as an approving review of the exact head by the owner's
# identity at the merge gate. Nothing here can give that approval.
if [[ "$risk_known" -eq 1 && "$RISK_ENFORCED" -eq 1 ]]; then
  risk_reasons=""
  [[ "$RISK_REQUIRED" -ne 3 ]] || risk_reasons+="the risk level is 3, by the $RISK_BY (ADR 020 decision 1)"$'\n'
  [[ -z "$RISK_REQUESTED" ]] ||
    risk_reasons+="a lowering from level $RISK_REQUIRED to level $RISK_REQUESTED is requested in $RISK_REQUEST; only the owner authorizes it"$'\n'
  if [[ -n "$risk_reasons" ]]; then
    # The gate's own reason for 'none' no longer holds.
    [[ "$(printf '%s\n' "$approval_lines" | sed -n 1p)" == "owner" ]] || approval_lines="owner"
    approval_lines+=$'\n'"${risk_reasons%$'\n'}"
  fi
fi
# A criterion pending for the owner's approval is cleared only by that
# approval at the merge gate, at any level (ADR 020 decision 2).
if [[ "$gate_status" == "pending" ]] && printf '%s\n' "$gate_reasons" | grep -q '^pending (owner_approval): '; then
  [[ "$(printf '%s\n' "$approval_lines" | sed -n 1p)" == "owner" ]] || approval_lines="owner"
  approval_lines+=$'\n'"a criterion is pending for the owner's approval (ADR 020 decision 2)"
fi
if [[ "$(printf '%s\n' "$approval_lines" | sed -n 1p)" == "owner" ]]; then
  merge_approval="- required from the project owner, for exactly this commit"
  echo "This feature needs the owner's approval before it is merged:"
  printf '%s\n' "$approval_lines" | sed '1d; s/^/  - /'
  echo "The pull request can be opened; no script or agent may merge it."
  echo
else
  merge_approval="- not required"
fi
merge_approval+=$'\n'"$(printf '%s\n' "$approval_lines" | sed '1d; s/^/- /')"
if [[ "$(printf '%s\n' "$approval_lines" | sed -n 1p)" == "owner" ]]; then
  # How the owner gives it (ADR 020 decision 3). No file, flag, comment,
  # record, or statement of an agent counts.
  merge_approval+=$'\n'"- given only as the owner's identity's approving review of exactly the head of the pull request, which GitHub enforces at the merge (or, until that identity exists, the owner's own word naming the head); ./scripts/merge-feature.sh $issue merges only on GitHub's decision"
fi
if [[ -n "$latest" ]]; then
  merge_approval+=$'\n'"- decided for the reviewed content $(jq -r '.reviewed_tree' "$latest")"
fi

# The level, as derived for this content: required, path minimum, triggers,
# stated, assessed, and requested (ADR 020 decision 1). publish-feature.sh
# copies it into the pull request.
risk_block=""
if [[ "$risk_known" -eq 1 ]]; then
  risk_block=$'\n'"Risk level:"$'\n'"$(risk_statement_lines)"$'\n'
fi

# 4. Stage everything and commit with an editable, structured message.
git -C "$root" add -A
echo "Changes to commit:"
git -C "$root" status --short
echo

message_file="$(mktemp "${TMPDIR:-/tmp}/finish-feature-message.XXXXXX")"
trap 'rm -f "$message_file"; [[ -z "${tmp_work:-}" ]] || rm -rf "$tmp_work"' EXIT
cat >"$message_file" <<EOF
$summary

Issue: #$issue

Changes:
$changes

$completion_lines

Verification:
$verification_lines

Manual steps:
$manual_steps

$review_line

Merge approval:
$merge_approval
$risk_block
Refs #$issue
EOF

commit_options=(--edit)
[[ "$unattended" -eq 0 ]] || commit_options=(--quiet)
if ! git -C "$root" commit "${commit_options[@]}" -F "$message_file"; then
  echo "Error: the commit was not created. The changes remain staged." >&2
  exit 1
fi

echo
echo "Committed $(git -C "$root" rev-parse --short HEAD) on $branch."
echo
if [[ "$gate_status" == "complete" ]]; then
  echo "Next: push the branch and open the pull request; follow its checks there:"
elif [[ "$gate_status" == "pending" ]]; then
  echo "The feature is ready for a pull request; criteria are pending for later gates."
  echo "Next: push the branch and open the pull request, which does not close Issue #$issue:"
else
  echo "The work is committed as $gate_status. Next: push the branch; the pull request is"
  echo "opened as a draft and does not close Issue #$issue:"
fi
echo "  ./scripts/publish-feature.sh $issue"
echo "After the merge, from the primary checkout: ./scripts/cleanup-worktree.sh $issue"
