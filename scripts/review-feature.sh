#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$script_dir/lib/agent.sh"
source "$script_dir/lib/review-data.sh"
source "$script_dir/lib/fingerprint.sh"
source "$script_dir/lib/verification.sh"
source "$script_dir/lib/review-run.sh"
source "$script_dir/lib/guardrails.sh"
source "$script_dir/lib/completion.sh"
source "$script_dir/lib/risk.sh"
source "$script_dir/lib/review-chain.sh"

fail() {
  echo "Error: $*" >&2
  exit 1
}

# --unverified "<reason>" reviews although verification fails. --changes
# reviews only what changed since the previous round. --feedback reviews an
# intermediate round of a Level 3 change on the feedback of a partial run.
unverified_reason=""
changes_only=0
feedback=0
arguments=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--unverified" ]]; then
    [[ $# -ge 2 && "$2" =~ [^[:space:]] ]] || fail "--unverified requires a reason."
    unverified_reason="$2"
    shift 2
  elif [[ "$1" == "--feedback" ]]; then
    feedback=1
    shift
  elif [[ "$1" == "--changes" ]]; then
    changes_only=1
    shift
  else
    arguments+=("$1")
    shift
  fi
done

agent_parse_args ${arguments[@]+"${arguments[@]}"}
if [[ "${#AGENT_POSITIONAL[@]}" -lt 1 || "${#AGENT_POSITIONAL[@]}" -gt 2 ]]; then
  echo "Usage: $0 <issue-number> [base-branch] [--agent <agent>] [--model <model>] [--changes] [--feedback | --unverified \"<reason>\"]"
  echo
  echo "The agent and model come from role 'reviewer' in .agents/agents.conf"
  echo "unless --agent and --model are given."
  echo
  echo "The review starts only when ./scripts/verify.sh --targeted passes for the"
  echo "current content (the tier an ordinary change needs; the targeted run refuses"
  echo "a change that needs the full run); a pass that was already recorded for it,"
  echo "of any tier, is reused. --unverified"
  echo "reviews anyway, for a review that must help diagnose a failure; the reason"
  echo "is recorded in the review."
  echo
  echo "A Level 3 change (ADR 020 decisions 1 and 5) is reviewed on the full run:"
  echo "./scripts/verify.sh --reuse. Its intermediate rounds may use --feedback"
  echo "instead, which runs ./scripts/verify.sh --only for the groups default, code,"
  echo "and integration-other as quick feedback and records it as such; that is never"
  echo "evidence, and finish-feature.sh takes no review made on feedback or with"
  echo "--unverified as the final review."
  echo
  echo "Every round reviews the complete feature. --changes makes a later round"
  echo "review only what changed since the previous round, with that round's"
  echo "findings and their triage: cheaper after a small fix, but it does not look"
  echo "at the rest of the feature again. Under a completion/v2 record it does so"
  echo "only when the reach of the changes is certain and the change is Level 1 or"
  echo "2 (ADR 020 decision 4); otherwise the round reviews the complete feature and"
  echo "says why. Every round gives the disposition of every earlier open finding."
  echo
  echo "Examples:"
  echo "  $0 2"
  echo "  $0 2 --changes"
  echo "  $0 2 develop"
  echo "  $0 2 --agent codex --model gpt-6-astra"
  exit 1
fi

issue="${AGENT_POSITIONAL[0]}"
base="${AGENT_POSITIONAL[1]:-main}"
[[ "$feedback" -eq 0 || -z "$unverified_reason" ]] || fail "--feedback and --unverified exclude each other."

[[ "$issue" =~ ^[0-9]+$ ]] || fail "issue number must be numeric: $issue"

root="$(git rev-parse --show-toplevel)"
branch="$(git branch --show-current)"
slug="${branch//\//-}"

reviews_dir="$root/.agents/reviews"
prompt_file="$root/.agents/prompts/reviewer.md"
schema_file="$root/.agents/schemas/feature-review.schema.json"

# Ensure we're reviewing the expected feature branch.
if [[ "$branch" != feature/${issue}-* ]]; then
  echo "Error: current branch does not look like feature/${issue}-*" >&2
  echo "Current branch: $branch" >&2
  exit 1
fi

agent_resolve "$root" reviewer "$AGENT_CLI_PROVIDER" "$AGENT_CLI_MODEL"
agent="$AGENT_PROVIDER"
model="$AGENT_MODEL"

[[ -f "$prompt_file" ]] || fail "reviewer prompt not found: $prompt_file"
[[ -f "$schema_file" ]] || fail "review schema not found: $schema_file"
review_data_require_jq

command -v gh >/dev/null 2>&1 || fail "GitHub CLI 'gh' is not installed."
gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated. Run: gh auth login"

# The local base branch or origin/<base>, whichever knows where the feature
# left its base; see feature_base.
git -C "$root" rev-parse --verify --quiet "$base^{commit}" >/dev/null ||
  git -C "$root" rev-parse --verify --quiet "origin/$base^{commit}" >/dev/null ||
  fail "base branch not found locally or on origin: $base"
feature_base_lines="$(feature_base "$root" "$base")" ||
  fail "could not determine the merge base of HEAD and $base."
base_ref="$(printf '%s\n' "$feature_base_lines" | sed -n 1p)"
merge_base="$(printf '%s\n' "$feature_base_lines" | sed -n 2p)"

# Determine next review number.
review_number=1
previous_review=""
while true; do
  candidate="$reviews_dir/${slug}-review-$(printf "%02d" "$review_number")"
  if [[ ! -e "$candidate.json" && ! -e "$candidate.md" ]]; then
    out="$candidate"
    break
  fi
  # A round without JSON, such as a review from before JSON artifacts, is not
  # an input for the re-review.
  if [[ -f "$candidate.json" ]]; then
    previous_review="$candidate.json"
  fi
  review_number=$((review_number + 1))
done
review_relative=".agents/reviews/$(basename "$out")"

# --changes builds on the previous round. What can be refused without the
# content is refused here, before the verification runs.
if [[ "$changes_only" -eq 1 ]]; then
  [[ -n "$previous_review" ]] ||
    fail "--changes needs a previous round, and this is round 1. Run a complete review first."
  previous_errors="$(review_artifact_errors "$previous_review")"
  [[ -z "$previous_errors" ]] ||
    fail "the previous review is invalid, so --changes cannot build on it: ${previous_errors//$'\n'/; }"
  previous_round="$(jq -r '.round' "$previous_review")"
  previous_tree="$(jq -r '.reviewed_tree' "$previous_review")"
  git -C "$root" cat-file -e "$previous_tree^{tree}" 2>/dev/null ||
    fail "the content that round $previous_round reviewed is no longer available, so the changes since then cannot be determined. Run a complete review, without --changes."
  [[ "$(jq -r '.merge_base' "$previous_review")" == "$merge_base" ]] ||
    fail "the base of the branch changed since round $previous_round, so the feature differs in more than your changes. Run a complete review, without --changes."
fi

# A reviewer cannot run the checks, so the review starts only on content that
# passes them, in the tier the change needs (ADR 017 decision 7). A pass
# recorded for exactly this content, of any tier, is reused; the review
# records the tier, the base, and the selection.
tmp_work="$(mktemp -d "${TMPDIR:-/tmp}/review-feature.XXXXXX")"
trap 'rm -rf "$tmp_work"' EXIT

# The risk level before this round (ADR 020 decision 1): the diff, the
# completion record, and the rounds before. A Level 3 change of a
# completion/v2 record is reviewed on the full run, or, in an intermediate
# round, on the feedback of a partial run (ADR 020 decision 5).
guardrail_rules="$(guardrails_rules_refs "$root" "$base")"
risk_assess "$root" "$guardrail_rules" "$merge_base" "$issue" "$previous_review" ||
  fail "could not derive the risk level of the change."
level3=0
[[ "$RISK_ENFORCED" -ne 1 || "$RISK_REQUIRED" -ne 3 ]] || level3=1
[[ "$feedback" -eq 0 || "$level3" -eq 1 ]] ||
  fail "--feedback is for the intermediate rounds of a Level 3 change, and this change is level $RISK_REQUIRED$([[ "$RISK_ENFORCED" -eq 1 ]] || echo " under the earlier contract (completion/$RISK_SCHEMA)"); it is reviewed on the tier it needs."
# Level 3 keeps a full review in every round (ADR 020 decision 4).
if [[ "$changes_only" -eq 1 && "$level3" -eq 1 ]]; then
  echo "The change is Level 3, which keeps a review of the complete feature in every round (ADR 020 decision 4): this round reviews the complete feature, not only the changes."
  changes_only=0
fi

verified_tree=""
if [[ -n "$unverified_reason" ]]; then
  echo "Reviewing without verification: $unverified_reason"
  verification="$(jq -n --arg reason "$unverified_reason" '{status: "not-verified", reason: $reason}')"
elif [[ "$feedback" -eq 1 ]]; then
  feedback_groups="$(risk_feedback_groups "$root")"
  echo "An intermediate round of a Level 3 change: the partial run of the groups ${feedback_groups//,/, } as feedback, never as evidence."
  verified_tree="$(fingerprint_worktree "$root" "$tmp_work")" ||
    fail "could not compute the fingerprint of the working tree."
  (cd "$root" && ./scripts/verify.sh --only "$feedback_groups") || {
    echo "Error: the partial run failed; the review was not started. Fix the failing check, or review anyway with --unverified \"<reason>\"." >&2
    exit 4
  }
  verification="$(jq -n --arg groups "$feedback_groups" --arg at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    '{status: "feedback", groups: $groups, ran_at: $at}')"
elif [[ "$level3" -eq 1 ]]; then
  echo "The change is Level 3: checking that the full verification passes for the content under review..."
  verified_tree="$(fingerprint_worktree "$root" "$tmp_work")" ||
    fail "could not compute the fingerprint of the working tree."
  (cd "$root" && ./scripts/verify.sh --reuse) || {
    echo "Error: verification failed; the review was not started. Fix the failing check, or review an intermediate round with --feedback." >&2
    exit 4
  }
  verification="$(jq -n --arg at "$(verification_field "$root" verified-at)" --arg tier "$(verification_tier "$root")" \
    '{status: "passed", verified_at: (if $at == "" then (now | todate) else $at end), tier: (if $tier == "" then "full" else $tier end)}')"
else
  echo "Checking that verification passes for the content under review..."
  # The content as it is before the checks run. The review below must cover
  # exactly this content, so a check that changes a file is detected.
  verified_tree="$(fingerprint_worktree "$root" "$tmp_work")" ||
    fail "could not compute the fingerprint of the working tree."
  # Status 4 tells a caller that the verification failed, apart from every
  # other reason for which no review was stored.
  (cd "$root" && ./scripts/verify.sh --reuse --targeted) || {
    echo "Error: verification failed; the review was not started. Fix the failing check, or review anyway with --unverified \"<reason>\"." >&2
    exit 4
  }
  verification="$(jq -n --arg at "$(verification_field "$root" verified-at)" \
    --arg tier "$(verification_tier "$root")" \
    --arg base "$(verification_field "$root" base)" \
    --arg selection "$(verification_field "$root" selection)" \
    '{status: "passed", verified_at: (if $at == "" then (now | todate) else $at end)}
     + (if $tier == "" then {} else {tier: $tier} end)
     + (if $base == "" then {} else {base: $base} end)
     + (if $selection == "" then {} else {selection: $selection} end)')"
fi
echo

# The reviewer is read-only and has no network access, so the script supplies
# the Issue and the complete diff.
issue_context="$(gh issue view "$issue" \
  --json title,body \
  --template 'Title: {{.title}}{{"\n\n"}}{{.body}}')" ||
  fail "could not read GitHub Issue #$issue."

head_before="$(git -C "$root" rev-parse HEAD)"
# The fingerprint of the reviewed content, including uncommitted and untracked
# files; the diff below is built from the same snapshot.
tree_before="$(fingerprint_worktree "$root" "$tmp_work")" ||
  fail "could not compute the fingerprint of the working tree."
cp "$tmp_work/fingerprint.index" "$tmp_work/index.before"
# The approval requests are no part of the fingerprint, but the reviewer reads
# them in the diff: without them, the requests of the base would show as
# deleted and the feature's own request would be missing.
if [[ -e "$root/$RISK_APPROVALS_DIR" ]]; then
  GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" add -A -- "$RISK_APPROVALS_DIR" >/dev/null ||
    fail "could not add the approval requests to the diff for the review."
fi
[[ -z "$verified_tree" || "$tree_before" == "$verified_tree" ]] ||
  fail "the content changed while verification ran, so the pass does not cover what would be reviewed. A check may modify a file; the review was not started."
# What the review fingerprints: the content with the completion record and
# the handoff note of the Issue, which Git ignores (ADR 020 decision 4), so
# that a change to either after the review makes it stale.
record_paths=()
while IFS= read -r record_path; do
  record_paths+=("$record_path")
done < <(fingerprint_issue_records "$issue")
reviewed_tree="$(fingerprint_with_records "$root" "$tmp_work" "${record_paths[@]}")" ||
  fail "could not compute the fingerprint of the reviewed content."
# The findings of the earlier rounds that are still open, by their stable
# identifiers; this round gives the disposition of each.
review_chain_open "$root" "$slug" "$review_number" >"$tmp_work/open.json" ||
  fail "could not determine the open findings of the earlier rounds."

review_paths=(. ":(exclude).agents/reviews" ":(exclude).agents/triage")
context_file="$tmp_work/context.md"
report_file="$tmp_work/result.json"

if GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" diff --cached --quiet "$merge_base" -- "${review_paths[@]}"; then
  fail "no changes to review between $base_ref and the working tree."
fi

# A review of changes only builds on the previous round: it needs that round's
# reviewed content and the same base, and something must have changed.
scope='{"kind": "full"}'
if [[ "$changes_only" -eq 1 ]]; then
  ! git -C "$root" diff --quiet "$previous_tree" "$reviewed_tree" ||
    fail "nothing changed since round $previous_round; there is nothing for --changes to review."
fi
# A review of changes only when the reach of the delta is certain (ADR 020
# decision 4): the chain back to a review of the complete feature holds, and
# the delta is bounded. Otherwise the round reviews the complete feature.
if [[ "$changes_only" -eq 1 && "$RISK_ENFORCED" -eq 1 ]]; then
  unbounded=""
  if chain="$(review_chain_baseline "$root" "$previous_review" 2>"$tmp_work/chain-reason")"; then
    unbounded="$(review_delta_unbounded "$root" "$guardrail_rules" "$(printf '%s\n' "$chain" | sed -n 1p)" \
      "$previous_tree" "$reviewed_tree" "$tmp_work/open.json")"
  else
    unbounded="$(cat "$tmp_work/chain-reason")"
  fi
  if [[ -n "$unbounded" ]]; then
    echo "The reach of the changes since round $previous_round is not certain, so this round reviews the complete feature (ADR 020 decision 4):"
    printf '%s\n' "$unbounded" | sed 's/^/  - /'
    echo
    changes_only=0
  fi
fi
compared_tree="$(git -C "$root" rev-parse "$merge_base^{tree}")" ||
  fail "could not read the tree of the merge base."
if [[ "$changes_only" -eq 1 ]]; then
  compared_tree="$previous_tree"
  scope="$(jq -n --argjson round "$previous_round" --arg tree "$previous_tree" \
    '{kind: "changes", since_round: $round, base_tree: $tree}')"
fi

if [[ "$changes_only" -eq 1 ]]; then
  # Only an approved triage that belongs to the previous review may tell the
  # reviewer that a finding was deferred or accepted. With any other triage
  # every finding counts as to be fixed.
  previous_triage="$(review_latest_triage "$root" "$previous_review")"
  if [[ -n "$previous_triage" && -n "$(triage_artifact_errors "$previous_triage" "$previous_review")" ]]; then
    echo "Note: ${previous_triage#"$root"/} is not a valid, approved triage of round $previous_round; its decisions are not used."
    previous_triage=""
  fi
  {
    echo "# Review context for Issue #$issue: changes since round $previous_round"
    echo
    echo "## GitHub Issue #$issue"
    echo
    printf '%s\n' "$issue_context"
    echo
    echo "## Findings of round $previous_round and what was decided about them"
    echo
    if [[ "$(jq '.findings | length' "$previous_review")" -eq 0 ]]; then
      echo "Round $previous_round had no findings."
    elif [[ -n "$previous_triage" ]]; then
      jq -r --slurpfile triage "$previous_triage" '
        ($triage[0].decisions | map({(.finding_id): .}) | add // {}) as $decisions
        | .findings[]
        | "### \(.id) [\(.severity)] \(.title)\n\n" +
          "Decision: \($decisions[.id].decision // "none recorded")" +
          (if $decisions[.id].rationale then " (\($decisions[.id].rationale))" else "" end) + "\n\n" +
          "Evidence: \(.evidence)\n\nRecommended action: \(.recommendation)\n"' "$previous_review"
    else
      echo "The findings were not triaged; treat each one as to be fixed."
      echo
      jq -r '.findings[] | "### \(.id) [\(.severity)] \(.title)\n\nEvidence: \(.evidence)\n\nRecommended action: \(.recommendation)\n"' "$previous_review"
    fi
    echo
    echo "## Files changed since round $previous_round"
    echo
    git -C "$root" diff --stat --no-color "$previous_tree" "$reviewed_tree"
    echo
    echo "## Diff since round $previous_round: from the content that round reviewed to the current content"
    echo
    git -C "$root" diff --no-color "$previous_tree" "$reviewed_tree"
  } >"$context_file"
else
  # A measured dataset sample is a table of numbers that the reviewer cannot
  # usefully read and that can exceed the length of its input (Issue #312): a
  # sample under data/samples/ larger than the threshold is left out of the
  # diff and listed by path, size, and sha256 from the reviewed content. It
  # stays in the reviewed tree and the fingerprint.
  sample_dir="data/samples"
  sample_limit=65536
  if command -v sha256sum >/dev/null 2>&1; then
    sample_sum=(sha256sum)
  else
    sample_sum=(shasum -a 256)
  fi
  diff_paths=("${review_paths[@]}")
  omitted_samples=()
  while IFS= read -r -d '' sample; do
    sample_size="$(GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" cat-file -s ":$sample")" ||
      fail "could not read the size of $sample."
    [[ "$sample_size" -gt "$sample_limit" ]] || continue
    sample_digest="$(GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" cat-file blob ":$sample" |
      "${sample_sum[@]}" | cut -d' ' -f1)" ||
      fail "could not compute the sha256 of $sample."
    diff_paths+=(":(exclude,literal)$sample")
    omitted_samples+=("$(printf '%s\t%s\t%s' "$sample" "$sample_size" "$sample_digest")")
  done < <(GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" diff --cached --name-only -z --no-renames \
    --diff-filter=d "$merge_base" -- "$sample_dir")
  {
    echo "# Review context for Issue #$issue"
    echo
    echo "## GitHub Issue #$issue"
    echo
    printf '%s\n' "$issue_context"
    echo
    echo "## Changed files"
    echo
    GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" diff --cached --stat --no-color "$merge_base" -- "${diff_paths[@]}"
    echo
    echo "## Complete diff against $base_ref, including uncommitted and untracked changes"
    echo
    GIT_INDEX_FILE="$tmp_work/index.before" git -C "$root" diff --cached --no-color "$merge_base" -- "${diff_paths[@]}"
    if [[ "${#omitted_samples[@]}" -gt 0 ]]; then
      echo
      echo "## Dataset samples not shown in the diff"
      echo
      echo "These files under $sample_dir/ are larger than $sample_limit bytes. They are part"
      echo "of the reviewed content and of every verification; the diff above leaves them"
      echo "out. Path, size in bytes, and sha256 in the reviewed content:"
      echo
      for omitted in "${omitted_samples[@]}"; do
        IFS=$'\t' read -r sample sample_size sample_digest <<<"$omitted"
        echo "- $sample: $sample_size bytes, sha256 $sample_digest"
      done
    fi
  } >"$context_file"
fi

# The merge approval gate: what the feature changes that needs the owner's
# approval or a closer look, by the rules of its base. The reviewer is told,
# and the artifact records it.
guardrail_findings="$(guardrails_classify "$root" "$guardrail_rules" "$merge_base" | sort -u)"
guardrails="$(printf '%s\n' "$guardrail_findings" |
  jq -Rn --arg level "$(printf '%s\n' "$guardrail_findings" | guardrails_level)" \
    '{level: $level, findings: [inputs | select(length > 0) | split("\t") | {kind: .[0], path: .[1], reason: .[2]}]}')"
{
  echo
  echo "## Merge approval gate"
  echo
  echo "By the rules of the base branch, for the complete feature against its base:"
  echo
  if [[ -z "$guardrail_findings" ]]; then
    echo "No protected or sensitive path is changed."
  else
    printf '%s\n' "$guardrail_findings" | awk -F '\t' '{ printf "- %s: %s (%s)\n", $1, $2, $3 }'
  fi
  echo
  echo "Look at the sensitive and protected changes in particular, and classify the"
  echo "impact of the whole feature on the architecture in architecture_impact."
  if [[ "$changes_only" -eq 1 ]]; then
    echo
    echo "Round $previous_round and the rounds it builds on classified the impact as:"
    echo "$(guardrails_review_level "$previous_review")."
    echo "You see only what changed since then, so classify that. The heaviest"
    echo "classification of the rounds counts: this round cannot lower an earlier one."
  fi
} >>"$context_file"

# The risk level the scripts derive, and what the reviewer assesses with the
# impact classification (ADR 020 decision 1).
{
  echo
  echo "## Risk level"
  echo
  echo "Derived by the scripts for the content under review, before your assessment:"
  echo
  risk_statement_lines review
  echo
  echo "Assess every escalation trigger of ADR 020 decision 1, also those no script"
  echo "can detect (a changed or removed published scientific claim, security,"
  echo "verification guarantees), and give the level you assess in"
  echo "architecture_impact.risk_level and the triggers the change hits in"
  echo "architecture_impact.escalation_triggers. A trigger the completion record"
  echo "does not name is a major finding. Your level can only raise the derived one."
  echo
  echo "The script has compared the line 'Tree:' of the approval request with the"
  echo "content tree (checked by the script, above). Report a finding about that"
  echo "line only if the statement above lists the error."
  case "$RISK_SCHEMA" in
    completion/v1)
      echo
      if git -C "$root" show "$merge_base:scripts/lib/completion.sh" 2>/dev/null | grep -Fq 'completion/v2'; then
        echo "The completion record uses completion/v1, but the base of this feature"
        echo "already knew completion/v2: the feature started under ADR 020, and a v1"
        echo "record escapes its rules. Report that as a major finding."
      else
        echo "The completion record uses completion/v1: the feature started before"
        echo "ADR 020 was delivered and finishes under the contract it started with."
      fi
      ;;
  esac
} >>"$context_file"

# The disposition of every earlier open finding (ADR 020 decision 4).
{
  echo
  echo "## Earlier findings that are open"
  echo
  if [[ "$(jq 'length' "$tmp_work/open.json")" -eq 0 ]]; then
    echo "No finding of an earlier round is open: return an empty dispositions list."
  else
    echo "Give, in dispositions, every one of these by its stable identifier, exactly"
    echo "once: resolved or accepted, with the evidence in the current files, or open."
    echo "A finding that is still open is carried on by a finding of this review that"
    echo "names it in continues, with the severity it has now."
    echo
    jq -r '.[] | "### \(.id) [\(.severity)] \(.title)\n\nEvidence: \(.evidence)\n"' "$tmp_work/open.json"
  fi
} >>"$context_file"

# What the implementer says about how far the Issue is done. It is given to
# the reviewer as a claim to check, in a review of the complete feature: the
# scripts only read the status, and only a reviewer can tell whether the code
# and the tests support it.
if [[ "$changes_only" -eq 0 ]]; then
  completion_file="$(completion_record "$root" "$issue")"
  handoff_left="$(handoff_remaining "$root/.agents/handoffs/$issue.md")"
  {
    echo
    echo "## Completion record of the implementer"
    echo
    echo "This is the implementer's own statement, not evidence. Check every"
    echo "acceptance criterion of the Issue against the diff and the tests, whatever"
    echo "the record says, and report a criterion that is not met, or a claim that"
    echo "the code does not support, as a finding (reviewer contract, 'Completion')."
    echo
    if [[ -f "$completion_file" ]]; then
      echo "$COMPLETION_DIR/$issue.json:"
      echo
      sed 's/^/    /' "$completion_file"
    else
      echo "The implementer wrote no completion record ($COMPLETION_DIR/$issue.json)."
    fi
    if [[ -n "$handoff_left" ]]; then
      echo
      echo "The handoff note lists remaining work:"
      echo
      printf '%s\n' "$handoff_left" | sed 's/^/- /'
    fi
  } >>"$context_file"
fi

echo "Preparing independent review:"
echo "  Issue:    #$issue"
echo "  Verified: $(jq -r 'if .status == "passed" then "\(.tier // "full") run" + (if .base then ", base \(.base)" else "" end) elif .status == "feedback" then "feedback of the partial run \(.groups), not evidence" else "not verified" end' <<<"$verification")"
echo "  Level:    $RISK_REQUIRED (by the $RISK_BY)"
echo "  Branch:   $branch"
echo "  Base:     $base_ref"
echo "  Agent:    $agent"
echo "  Model:    $model"
echo "  Output:   $review_relative.json"
if [[ -n "$previous_review" ]]; then
  echo "  Previous: .agents/reviews/$(basename "$previous_review")"
fi
if [[ "$changes_only" -eq 1 ]]; then
  echo "  Scope:    only the changes since round $previous_round"
fi
echo

if [[ "$changes_only" -eq 1 ]]; then
  START_PROMPT="Read and follow .agents/prompts/reviewer.md.

Your assigned work item is GitHub Issue #${issue}.

This is a review of changes only: follow the \"Review of changes only\"
section of your contract. Round ${previous_round} reviewed the feature as it
was then. Standard input contains the Issue, the findings of round
${previous_round} with what was decided about each, and the diff from the
content that round reviewed to the current content. Read the files in the
repository for surrounding context.

Read the matching .agents/plans/${issue}-*.md if one exists."
else
  START_PROMPT="Read and follow .agents/prompts/reviewer.md.

Your assigned work item is GitHub Issue #${issue}.

Standard input contains the Issue title and body, the implementer's
completion record, the list of changed files,
and the complete diff of the current implementation against ${base_ref},
including uncommitted and untracked changes. Review that complete diff. Read
the files in the repository for surrounding context.

Read the matching .agents/plans/${issue}-*.md if one exists."

  if [[ -n "$previous_review" ]]; then
    START_PROMPT+="

This is a re-review.

Read the previous review (JSON):
.agents/reviews/$(basename "$previous_review")

Give the disposition of every earlier open finding that standard input lists, but perform an independent review of the complete current implementation. Do not limit the review to the previous findings."
  fi
fi

START_PROMPT+="

You have read-only access. Do not modify, create, or delete any file.
Return the review as JSON that matches the supplied schema. The calling
script validates and stores it."

echo "Starting $agent reviewer ($model) with read-only permissions..."
echo

# The result classifies the impact and gives the disposition of every earlier
# open finding.
feature_result_errors() {
  feature_review_result_errors "$1"
  if review_data_is_json "$1" && jq -e 'type == "object"' "$1" >/dev/null 2>&1; then
    review_chain_disposition_errors "$1" "$tmp_work/open.json"
  fi
}
review_run_reviewer "$agent" "$model" "$root" "$START_PROMPT" "$context_file" "$schema_file" "$report_file" "$tmp_work" \
  feature_result_errors

metadata="$(jq -n \
  --argjson issue "$issue" \
  --argjson round "$review_number" \
  --arg branch "$branch" \
  --arg base "$base_ref" \
  --arg merge_base "$merge_base" \
  --arg head "$head_before" \
  --arg tree "$reviewed_tree" \
  --arg compared "$compared_tree" \
  --argjson records "$(printf '%s\n' "${record_paths[@]}" | jq -R . | jq -s .)" \
  --arg agent "$agent" \
  --arg model "$model" \
  --arg created_at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --argjson verification "$verification" \
  --argjson scope "$scope" \
  --argjson guardrails "$guardrails" \
  '{
    schema: "review/v1",
    kind: "feature",
    guardrails: $guardrails,
    verification: $verification,
    scope: $scope,
    issue: $issue,
    round: $round,
    branch: $branch,
    base: $base,
    merge_base: $merge_base,
    head: $head,
    compared_tree: $compared,
    reviewed_tree: $tree,
    reviewed_paths: null,
    record_paths: $records,
    dispositions: [],
    reviewer: {agent: $agent, model: $model},
    created_at: $created_at
  }')"
review_store "$report_file" "$out" "$metadata"

# The decision of the gate for the reviewed content: the rules on the diff
# and the classification of this review, with the rounds it builds on. The
# level, now with this review's assessment, is recorded with the content it
# applies to; a Level 3 change and a requested lowering need the owner.
approval_lines="$(guardrails_decision "$root" "$guardrail_rules" "$merge_base" "$out.json")"
risk_assess "$root" "$guardrail_rules" "$merge_base" "$issue" "$out.json" ||
  fail "could not derive the risk level of the reviewed content."
if [[ "$RISK_ENFORCED" -eq 1 && ( "$RISK_REQUIRED" -eq 3 || -n "$RISK_REQUESTED" ) ]]; then
  [[ "$(printf '%s\n' "$approval_lines" | sed -n 1p)" == "owner" ]] || approval_lines="owner"
  [[ "$RISK_REQUIRED" -ne 3 ]] || approval_lines+=$'\n'"the risk level is 3, by the $RISK_BY (ADR 020 decision 1)"
  [[ -z "$RISK_REQUESTED" ]] ||
    approval_lines+=$'\n'"a lowering from level $RISK_REQUIRED to level $RISK_REQUESTED is requested in $RISK_REQUEST; only the owner authorizes it"
fi
risk="$(jq -n --argjson required "$RISK_REQUIRED" --arg by "$RISK_BY" --argjson path "$RISK_PATH_MIN" \
  --arg path_reasons "$RISK_PATH_REASONS" --arg triggers "$RISK_TRIGGERS" --arg named "$RISK_NAMED_TRIGGERS" \
  --arg schema "$RISK_SCHEMA" --arg stated "$RISK_RECORDED" --arg assessed "$RISK_REVIEWED" \
  --arg request "$RISK_REQUEST" --arg requested "$RISK_REQUESTED" --arg tree "$RISK_TREE" --arg errors "$RISK_ERRORS" '
  def lines: split("\n") | map(select(length > 0));
  {required: $required, by: $by, path_minimum: $path, path_reasons: ($path_reasons | lines),
   triggers: ($triggers | lines), named_triggers: ($named | lines), record_schema: $schema,
   stated: (if $stated == "" then null else ($stated | tonumber) end),
   assessed: (if $assessed == "" then null else ($assessed | tonumber) end),
   approval_request: (if $request == "" then null else $request end),
   requested: (if $requested == "" then null else ($requested | tonumber) end),
   tree: $tree, problems: ($errors | lines)}')"
jq --arg lines "$approval_lines" --argjson risk "$risk" '
  ($lines | split("\n") | map(select(length > 0))) as $l
  | .merge_approval = {required: ($l[0] == "owner"), reasons: $l[1:]}
  | .risk = $risk' "$out.json" >"$out.json.tmp"
mv "$out.json.tmp" "$out.json"
echo "  Risk level: $RISK_REQUIRED, by the $RISK_BY${RISK_REQUESTED:+; level $RISK_REQUESTED requested in $RISK_REQUEST, a request only}"
if [[ -n "$RISK_ERRORS" ]]; then
  echo "  The level is not consistent; finish-feature.sh will refuse the commit until it is:"
  printf '%s\n' "$RISK_ERRORS" | sed 's/^/    - /'
fi
if [[ "$(jq -r '.merge_approval.required' "$out.json")" == "true" ]]; then
  echo "  Merge approval: required from the owner"
  jq -r '.merge_approval.reasons[] | "    - \(.)"' "$out.json"
fi
echo "  $review_relative.json  (source of truth)"
echo "  $review_relative.md    (generated report)"
echo
if [[ "$(jq '.findings | length' "$out.json")" -gt 0 ]]; then
  echo "Next: triage the findings:"
  echo "  ./scripts/triage-review.sh $review_relative.json"
else
  echo "Next: the review has no findings; finish the feature:"
  echo "  ./scripts/finish-feature.sh $issue \"<commit summary>\""
fi
