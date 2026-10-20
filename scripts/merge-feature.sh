#!/usr/bin/env bash

set -euo pipefail

# The merge step of a feature (ADR 020 decision 3): it applies GitHub's
# decision and nothing else. A pull request that needs the owner's approval
# is merged only when GitHub reports it mergeable and the latest review of
# the owner's identity approves exactly its head: the one login that the line
# 'owner-identity:' of the base's .agents/policies/guardrails.conf names, a
# code owner of the base other than the agent's own login. Another code
# owner's review does not count. No flag, file, comment, review by the agent's
# login, completion record, or statement in the conversation counts.
#
# Whether the owner is needed is derived here from the diff against the base
# as well: its protected paths and its escalation triggers (scripts/lib/risk.sh).
# The risk lines of the commit message can only raise that, never lower it;
# the assessed level is read from the latest independent review of the
# feature, which must be of exactly the head. A change that is Level 3 by a
# trigger or an assessment, and that no protected path marks, is refused
# without its committed approval request.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$script_dir/lib/fingerprint.sh"
source "$script_dir/lib/guardrails.sh"
source "$script_dir/lib/risk.sh"

usage() {
  echo "Usage: $0 <issue-number>"
  echo
  echo "Run in the feature worktree after publish-feature.sh. Merges the pull request"
  echo "of the feature only on GitHub's decision: GitHub reports it mergeable (its"
  echo "required checks passed, its required reviews given), and it is merged at"
  echo "exactly the head this worktree has."
  echo
  echo "A pull request needs the owner's approval when its commit says so (the"
  echo "merge approval or the risk level of finish-feature.sh: Level 3, or a"
  echo "requested lowering), when a completion criterion of its commit is pending"
  echo "for the owner's approval (owner_approval), when it changes a protected path"
  echo "or an approval request (.agents/approvals/), when its diff shows an"
  echo "escalation trigger (derived here, whatever the commit says), when the latest"
  echo "review of the feature in this worktree assesses Level 3 or names a trigger,"
  echo "when that review is not of exactly the head (or no review exists and the"
  echo "commit does not say it was finished without one), or when its"
  echo "commit has no risk statement. A change that is Level 3 by a trigger or an"
  echo "assessment, without a protected path, also needs its committed approval"
  echo "request .agents/approvals/<issue-number>.md."
  echo "Then the latest review of the owner's identity must approve exactly the"
  echo "head: the one login that the line 'owner-identity: <login>' of"
  echo ".agents/policies/guardrails.conf of the base names, a code owner in"
  echo ".github/CODEOWNERS of the base other than the agent's own login. No other"
  echo "code owner's review counts. Until that identity exists, the owner merges"
  echo "such a pull request, as today; this script does not."
  echo
  echo "It takes no option: nothing given to it, written by an agent, or said in a"
  echo "conversation is the owner's approval."
  exit 2
}

fail() {
  echo "Error: $*" >&2
  exit 1
}

# refuse <reason>...: the merge gate says no; nothing was merged.
refuse() {
  echo "Not merged:" >&2
  printf '  - %s\n' "$@" >&2
  exit 3
}

# review_of_head <review-json>: succeeds when the review is a review of the
# feature whose reviewed content is exactly the head: unchanged since the
# review, and nothing in the worktree besides the head's content.
review_of_head() {
  local scratch
  local current=0

  [[ "$(jq -r '.issue' "$1" 2>/dev/null)" == "$issue" && "$(jq -r '.kind // "feature"' "$1" 2>/dev/null)" == "feature" ]] ||
    return 1
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/merge-feature.XXXXXX")"
  review_is_current "$root" "$scratch" "$1" || current=1
  rm -rf "$scratch"
  [[ "$current" -eq 0 ]] || return 1
  [[ -z "$(git -C "$root" status --porcelain --untracked-files=all -- . \
    ':(exclude).agents/reviews' ':(exclude).agents/triage')" ]]
}

[[ $# -eq 1 && "$1" =~ ^[0-9]+$ ]] || usage
issue="$1"

command -v gh >/dev/null 2>&1 || fail "GitHub CLI 'gh' is not installed."
command -v jq >/dev/null 2>&1 || fail "jq is required."

root="$(git rev-parse --show-toplevel)"
branch="$(git branch --show-current)"
[[ "$branch" == feature/${issue}-* ]] ||
  fail "merge-feature.sh must run on feature/${issue}-*. Current branch: $branch"

pr="$(gh pr view "$branch" --json number,url,state,isDraft,headRefOid,baseRefName,mergeStateStatus,reviewDecision,reviews)" ||
  fail "could not read the pull request of $branch from GitHub."
url="$(jq -r '.url' <<<"$pr")"
head="$(jq -r '.headRefOid' <<<"$pr")"
base_branch="$(jq -r '.baseRefName' <<<"$pr")"
[[ "$(jq -r '.state' <<<"$pr")" == "OPEN" ]] || fail "the pull request $url is not open."
[[ "$(jq -r '.isDraft' <<<"$pr")" != "true" ]] || refuse "the pull request $url is a draft: the work is not ready for a merge"
[[ "$head" == "$(git -C "$root" rev-parse HEAD)" ]] ||
  refuse "the head of $url is $head, and this worktree is at $(git -C "$root" rev-parse HEAD); publish the commit that was finished, or merge on GitHub"

# What the merge needs. The commit message of finish-feature.sh can only
# raise it; the paths of the diff are read here.
message="$(git -C "$root" log -1 --format=%B "$head")"
needs_owner=()
missing_request=""
if ! printf '%s\n' "$message" | grep -Fqx "Risk level:"; then
  needs_owner+=("the head commit has no risk statement of finish-feature.sh, so its level is unknown")
fi
if printf '%s\n' "$message" | grep -Fqx -- "- required from the project owner, for exactly this commit"; then
  needs_owner+=("the commit says that the merge needs the owner's approval")
fi
if printf '%s\n' "$message" | grep -Eq '^- required: level 3([^0-9]|$)'; then
  needs_owner+=("the change is Level 3")
fi
if printf '%s\n' "$message" | grep -Eq '^- requested: level [1-3]'; then
  needs_owner+=("a lowering of the level is requested, which only the owner authorizes")
fi
# A criterion pending for the owner's approval (ADR 020 decision 2) is
# cleared only here, by the identity's approval of the head, at any level.
if printf '%s\n' "$message" | grep -Eq '^- pending \(owner_approval\):'; then
  needs_owner+=("a completion criterion is pending for the owner's approval")
fi
rules="$(guardrails_rules_refs "$root" "$base_branch")"
merge_base=""
for ref in "origin/$base_branch" "$base_branch"; do
  merge_base="$(git -C "$root" merge-base "$ref" "$head" 2>/dev/null)" && break
done
if [[ -z "$merge_base" ]]; then
  needs_owner+=("the base of the pull request cannot be determined here")
else
  protected="$(guardrails_classify "$root" "$rules" "$merge_base" "$head" | awk -F '\t' '$1 == "protected" { print $2 }' | sort -u)"
  [[ -z "$protected" ]] ||
    needs_owner+=("it changes code-owned paths: $(printf '%s\n' "$protected" | head -n 5 | paste -sd ',' - | sed 's/,/, /g')")
  # The escalation triggers, derived from the diff itself: the risk lines of
  # the commit message can be written by hand and only raise the level.
  triggers="$(risk_triggers "$root" "$merge_base" "$head" | awk -F '\t' '{ printf "%s: %s\n", $1, $2 }' | sort -u)"
  [[ -z "$triggers" ]] ||
    needs_owner+=("the diff shows escalation triggers, so the change is Level 3: $(printf '%s\n' "$triggers" | head -n 5 | paste -sd ';' - | sed 's/;/; /g')")
  # The assessment, read from the latest review of the feature for exactly
  # the head (scripts/lib/risk.sh, risk_review_reading): the risk lines of
  # the commit message can be written by hand and cannot leave it out.
  shopt -s nullglob
  reviews=("$root/.agents/reviews/${branch//\//-}-review-"[0-9][0-9].json)
  shopt -u nullglob
  review_level3=0
  if [[ "${#reviews[@]}" -eq 0 ]]; then
    printf '%s\n' "$message" | grep -q '^Review: no independent review' ||
      needs_owner+=("no review of the feature is in this worktree, and the commit does not say that it was finished without one, so the assessed level of the head is unknown")
  else
    review="${reviews[${#reviews[@]}-1]}"
    if ! review_of_head "$review"; then
      needs_owner+=("the latest review ${review#"$root"/} is not a review of exactly the head $head, so the assessed level of the head is unknown")
    else
      if [[ "$(risk_review_reading "$review" level)" == 3 ]]; then
        review_level3=1
        needs_owner+=("the independent review ${review#"$root"/} assesses the change as Level 3")
      fi
      if [[ -n "$(risk_review_reading "$review" triggers)" ]]; then
        review_level3=1
        needs_owner+=("the independent review ${review#"$root"/} names escalation triggers, so the change is Level 3: $(risk_review_reading "$review" triggers | head -n 5 | paste -sd ';' - | sed 's/;/; /g')")
      fi
    fi
  fi
  # Level 3 by a trigger or an assessment that no protected path marks needs
  # the committed approval request, which makes GitHub require the review.
  path_minimum="$(risk_path_minimum "$root" "$rules" "$merge_base" "$head" | head -n 1)"
  request="$(approval_request_path "$issue")"
  level3_unmarked=0
  if [[ "$path_minimum" != 3 ]]; then
    [[ -z "$triggers" && "$review_level3" -eq 0 ]] || level3_unmarked=1
    if printf '%s\n' "$message" | grep -Eq '^- (required: level 3([^0-9]|$)|requested: level [1-3])'; then
      level3_unmarked=1
    fi
  fi
  if [[ "$level3_unmarked" -eq 1 ]] &&
    ! { git -C "$root" cat-file -e "$head:$request" 2>/dev/null &&
      [[ -n "$(git -C "$root" diff --name-only --no-renames "$merge_base" "$head" -- "$request")" ]]; }; then
    missing_request="the change is Level 3 by its triggers or its assessment, which no protected path marks, and the pull request does not commit the approval request $request, so GitHub does not require the owner's review (ADR 020 decision 3)"
    needs_owner+=("$missing_request")
  fi
fi

# GitHub's decision: the required checks and reviews of the ruleset.
merge_state="$(jq -r '.mergeStateStatus' <<<"$pr")"
case "$merge_state" in
  CLEAN | HAS_HOOKS) ;;
  *) refuse "GitHub does not report $url as mergeable (merge state $merge_state): a required check or review is missing, failed, or pending" ;;
esac

if [[ "${#needs_owner[@]}" -gt 0 ]]; then
  echo "This pull request needs the owner's approval:"
  printf '  - %s\n' "${needs_owner[@]}"
  agent_login="$(gh api user --jq '.login')" || fail "could not ask GitHub for the login this script runs with."
  # The owner's identity: the one login that the line 'owner-identity:' of
  # the gate configuration of the base names, which the code-owners file of
  # the base names too, and which is not the login the agent works with.
  # Another code owner (a team member, another account, a team) is not the
  # owner's identity.
  identity="$(git -C "$root" show "$merge_base:$GUARDRAILS_CONFIG" 2>/dev/null |
    sed -n 's/#.*$//; s/^owner-identity:[[:space:]]*@\{0,1\}//p' | tr -s '[:space:]' '\n' | grep . || true)"
  owners="$(git -C "$root" show "$merge_base:.github/CODEOWNERS" 2>/dev/null |
    sed 's/#.*$//' | tr -s '[:space:]' '\n' | sed -n 's/^@\([A-Za-z0-9-]*\)$/\1/p' | sort -fu)"
  [[ -n "$merge_base" ]] ||
    refuse "the base of the pull request cannot be determined here, so neither the owner's identity nor the code owners of $base_branch can be read" "the owner merges $url"
  until_then="until it exists, the owner merges $url, or says in the conversation that the agent may merge it, naming the head $head; no script takes that word as approval"
  if [[ -z "$identity" ]]; then
    refuse "the owner's identity does not exist yet: $GUARDRAILS_CONFIG of $base_branch has no line 'owner-identity: <login>' (ADR 020 decision 3)" "$until_then"
  fi
  [[ "$(printf '%s\n' "$identity" | wc -l | tr -d ' ')" -eq 1 && "$identity" =~ ^[A-Za-z0-9-]+$ ]] ||
    refuse "the line 'owner-identity:' of $GUARDRAILS_CONFIG of $base_branch must name exactly one GitHub login" "$until_then"
  if [[ "$(printf '%s' "$identity" | tr '[:upper:]' '[:lower:]')" == "$(printf '%s' "$agent_login" | tr '[:upper:]' '[:lower:]')" ]]; then
    refuse "the owner's identity does not exist yet: the configured identity $identity is the login this runs with, so GitHub cannot tell the owner's review from the agent's (ADR 020 decision 3)" "$until_then"
  fi
  printf '%s\n' "$owners" | grep -qixF -- "$identity" ||
    refuse "the owner's identity $identity is no code owner in .github/CODEOWNERS of $base_branch, so GitHub does not require its review (ADR 020 decision 3)" "$until_then"
  # GitHub reports no decision when the ruleset requires no review (a pull
  # request without code-owned paths, such as one pending only for the
  # owner's approval); the identity's review below decides then.
  case "$(jq -r '.reviewDecision // ""' <<<"$pr")" in
    APPROVED | "") ;;
    *) refuse "GitHub's review decision for $url is $(jq -r '.reviewDecision' <<<"$pr"), not APPROVED" ;;
  esac
  # The latest review of the identity that decides: approving or requesting
  # changes; a comment decides nothing.
  approving="$(jq -r --arg head "$head" --arg identity "$identity" '
    ($identity | ascii_downcase) as $who
    | [.reviews[]? | select((.author.login // "" | ascii_downcase) == $who)
                   | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED" or .state == "DISMISSED")]
    | group_by(.author.login | ascii_downcase) | map(last)
    | map(select(.state == "APPROVED" and .commit.oid == $head)) | .[0].author.login // empty' <<<"$pr")"
  problems=()
  [[ -z "$missing_request" ]] || problems+=("$missing_request; finish the feature with finish-feature.sh, which commits it")
  if [[ -z "$approving" ]]; then
    problems+=("the owner's identity $identity does not approve exactly the head $head of $url: it has to review it, and no other code owner's review counts (an approval of an earlier commit does not carry over)"
      "a lowering that the identity has not approved for this head is redone at the required level before the merge (ADR 020 decision 1)")
  fi
  [[ "${#problems[@]}" -eq 0 ]] || refuse "${problems[@]}"
  echo "The owner's identity $approving approves exactly the head $head."
fi

echo "Merging $url at $head..."
gh pr merge "$url" --merge --match-head-commit "$head" || fail "GitHub refused the merge of $url."
echo "Merged $url."
if ! printf '%s\n' "$message" | grep -q '^Completion: complete$'; then
  echo "Issue #$issue stays open: the feature is not complete, or criteria are pending for later gates."
fi
echo "After the merge, from the primary checkout: ./scripts/cleanup-worktree.sh $issue"
