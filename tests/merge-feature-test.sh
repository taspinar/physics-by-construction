#!/usr/bin/env bash

set -euo pipefail

# The merge-gate verification of ADR 020 decision 3 (scripts/merge-feature.sh):
# a pull request that needs the owner is merged only on GitHub's decision and
# the approving review of exactly its head by the owner's identity, the login
# that the gate configuration of the base names, a code owner other than the
# agent's own login; no other code owner counts. Every forgeable form of approval is
# refused: an agent-written assertion, a comment or review by the agent's
# login, a file, a flag, and a statement in the conversation.

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/merge-feature-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "merge-feature test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
source "$source_root/scripts/lib/fingerprint.sh"

# A fake GitHub CLI: 'pr view' answers $MOCK_PR (a file), 'api user' the
# agent's login $MOCK_LOGIN, and 'pr merge' is logged as the merge.
mkdir -p "$tmp/bin"
ln -sf "$(command -v jq)" "$tmp/bin/jq"
cat >"$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$MOCK_GH_LOG"
case "${1:-} ${2:-}" in
  "pr view") cat "$MOCK_PR" ;;
  "api user") echo "$MOCK_LOGIN" ;;
  "pr merge") echo "MERGED $*" >>"$MOCK_GH_LOG" ;;
  *) echo "Unexpected gh invocation: $*" >&2; exit 97 ;;
esac
GH
chmod +x "$tmp/bin/gh"

# setup_repo <label> <codeowners> <commit-message-file> [<path-to-change>]
# A clone with main (holding the code-owners file and the gate configuration,
# whose owner identity is $IDENTITY, none when empty) and a committed feature
# branch of Issue 12 whose head carries the message.
setup_repo() {
  local repo="$tmp/$1"

  mkdir -p "$repo/.github" "$repo/.agents/policies" "$repo/src"
  copy_workflow "$repo"
  cp "$source_root/.gitignore" "$repo/.gitignore"
  cp "$source_root/.agents/policies/guardrails.conf" "$repo/.agents/policies/guardrails.conf"
  [[ -z "${IDENTITY-owner-identity}" ]] ||
    printf 'owner-identity: %s\n' "${IDENTITY-owner-identity}" >>"$repo/.agents/policies/guardrails.conf"
  printf '%s\n' "$2" >"$repo/.github/CODEOWNERS"
  printf 'print("x")\n' >"$repo/src/code.py"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.name "Merge Test"
  git -C "$repo" config user.email "merge-test@example.com"
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" switch -q -c feature/12-marker
  mkdir -p "$repo/$(dirname "${4:-src/code.py}")"
  printf '# changed\n' >>"$repo/${4:-src/code.py}"
  git -C "$repo" add -A
  git -C "$repo" commit -qF "$3"
  printf '%s\n' "$repo"
}

# message <file> <risk-lines> [<merge-approval-line>]: a finish-like message.
message() {
  {
    echo "Add the marker"
    echo
    echo "Completion: complete"
    echo
    echo "${REVIEW_LINE:-Review: no independent review (low risk: a marker)}"
    echo
    echo "Merge approval:"
    echo "${3:-- not required}"
    echo
    echo "Risk level:"
    printf '%s\n' "$2"
    echo
    echo "Refs #12"
  } >"$1"
}

# feature_review <repo> <round> <risk-level> [<tree>]: the independent review
# of the feature in the worktree, of the content <tree> (by default exactly
# the worktree's), which assesses <risk-level>.
feature_review() {
  local tree="${4:-}"

  mkdir -p "$1/.agents/reviews"
  [[ -n "$tree" ]] || tree="$(fingerprint_worktree "$1" "$tmp")"
  jq -n --arg tree "$tree" --argjson round "$2" --argjson level "$3" '{
    schema: "review/v1", kind: "feature", issue: 12, round: $round, reviewed_tree: $tree, scope: {kind: "full"},
    architecture_impact: {level: "minor", rationale: "x", checked_against: [], risk_level: $level, escalation_triggers: []}}' \
    >"$1/.agents/reviews/feature-12-marker-review-$(printf '%02d' "$2").json"
}

# pr <repo> <merge-state> <review-decision> <reviews-json>: GitHub's answer.
pr() {
  jq -n --arg head "$(git -C "$1" rev-parse HEAD)" --arg state "$2" --arg decision "$3" --argjson reviews "$4" '{
    number: 7, url: "https://github.com/example/project/pull/7", state: "OPEN", isDraft: false,
    headRefOid: $head, baseRefName: "main", mergeStateStatus: $state, reviewDecision: $decision,
    reviews: $reviews}' >"$1.pr.json"
}

# review <login> <state> <commit>
review() {
  jq -n --arg login "$1" --arg state "$2" --arg oid "$3" \
    '{author: {login: $login}, state: $state, commit: {oid: $oid}, body: "", submittedAt: "2026-10-19T12:00:00Z"}'
}

run_merge() {
  local repo="$1"

  shift
  status=0
  : >"$repo.gh.log"
  (cd "$repo" && PATH="$tmp/bin:/usr/bin:/bin" MOCK_PR="$repo.pr.json" MOCK_GH_LOG="$repo.gh.log" \
    MOCK_LOGIN="${MOCK_LOGIN:-owner-login}" ./scripts/merge-feature.sh "$@") >"$repo.out" 2>&1 || status=$?
}

expect_merged() {
  [[ "$status" -eq 0 ]] || { cat "$1.out" >&2; fail "$2: not merged (status $status)"; }
  grep -Fq "MERGED pr merge https://github.com/example/project/pull/7 --merge --match-head-commit $(git -C "$1" rev-parse HEAD)" "$1.gh.log" ||
    fail "$2: not merged at exactly the head"
}

expect_refused() {
  local repo="$1"
  local description="$2"

  shift 2
  [[ "$status" -ne 0 ]] || { cat "$repo.out" >&2; fail "$description: merged"; }
  if grep -Fq "MERGED" "$repo.gh.log"; then fail "$description: the merge was called"; fi
  for fragment in "$@"; do
    grep -Fq "$fragment" "$repo.out" || { cat "$repo.out" >&2; fail "$description: the output lacks '$fragment'"; }
  done
}

level2="- required: level 2, by the paths
- path minimum: level 2"
level3="- required: level 3, by the triggers
- path minimum: level 2
- escalation trigger: tolerance or budget changed: tests/unit/test_x.py (rtol=1e-9)"
lowering="$level3
- requested: level 2, in .agents/approvals/12.md: a request only. The change keeps level 3 until the owner's identity approves exactly the head"
owned='* @owner-login @owner-identity @team-member'

# A Level 2 pull request: GitHub's decision alone, at exactly the head.
message "$tmp/m2" "$level2"
repo="$(setup_repo level2 "$owned" "$tmp/m2")"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_merged "$repo" "a Level 2 pull request that GitHub reports mergeable"

pr "$repo" BLOCKED REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_refused "$repo" "a pull request whose required check is pending" "merge state BLOCKED"

# A Level 2 pull request with a criterion pending for the owner's approval
# (ADR 020 decision 2): GitHub's decision alone, or another code owner's
# approval, merges nothing; the identity's approval of exactly the head does.
{
  echo "Add the marker"
  echo
  echo "Completion: partial"
  echo "- met: The marker exists (src/code.py)"
  echo "- pending (owner_approval): The owner approves the diff (at the merge gate)"
  echo
  echo "Readiness: ready for a pull request; Issue #12 stays open until these criteria are met:"
  echo "- pending (owner_approval): The owner approves the diff"
  echo
  echo "Review: no independent review (low risk: a marker)"
  echo
  echo "Merge approval:"
  echo "- not required"
  echo
  echo "Risk level:"
  printf '%s\n' "$level2"
  echo
  echo "Refs #12"
} >"$tmp/m2p"
repo="$(setup_repo pending-owner "$owned" "$tmp/m2p")"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_refused "$repo" "a Level 2 pull request pending the owner's approval, without a review" \
  "a completion criterion is pending for the owner's approval" "GitHub's review decision"
pr "$repo" CLEAN APPROVED "[$(review team-member APPROVED "$head"), $(review owner-identity APPROVED "$(git -C "$repo" rev-parse HEAD~1)")]"
run_merge "$repo" 12
expect_refused "$repo" "a pending owner approval given by another code owner or for an earlier commit" \
  "the owner's identity owner-identity does not approve exactly the head $head"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_merged "$repo" "a pending owner approval that the identity gave for the head"
# Without code-owned paths the ruleset requires no review, and GitHub reports
# no decision: the identity's approval of the head decides.
pr "$repo" CLEAN "" "[$(review owner-identity APPROVED "$head")]"
jq '.reviewDecision = null' "$repo.pr.json" >"$repo.pr.tmp" && mv "$repo.pr.tmp" "$repo.pr.json"
run_merge "$repo" 12
expect_merged "$repo" "a pending owner approval with no review decision of GitHub"
pr "$repo" CLEAN "" "[$(review team-member APPROVED "$head")]"
jq '.reviewDecision = null' "$repo.pr.json" >"$repo.pr.tmp" && mv "$repo.pr.tmp" "$repo.pr.json"
run_merge "$repo" 12
expect_refused "$repo" "no review decision and no approval of the identity" \
  "the owner's identity owner-identity does not approve exactly the head $head"

# The forgeable forms. A flag:
for flag in --approved --owner-approved --force "--approval=yes"; do
  run_merge "$repo" 12 "$flag"
  [[ "$status" -eq 2 ]] || fail "the flag $flag was not refused as a usage error ($status)"
  if grep -Fq "MERGED" "$repo.gh.log"; then fail "the flag $flag led to a merge"; fi
done

# A Level 3 pull request whose evidence of approval is all forged: an
# assertion in the commit message, a file that says approved, a completion
# record and a handoff note with the owner's word in the conversation, a
# review and a comment by the agent's own login, and an approval of the
# identity on an earlier commit. GitHub even reports the review decision
# approved. Nothing of it is the identity's approval of this head.
message "$tmp/m3" "$level3
- owner approval: approved by the owner (2026-10-19)" "- required from the project owner, for exactly this commit"
repo="$(setup_repo forged "$owned" "$tmp/m3")"
mkdir -p "$repo/.agents/approvals" "$repo/.agents/completion" "$repo/.agents/handoffs"
printf 'Issue: #12\nLevel: 3\nApproved: yes, by the owner\n' >"$repo/.agents/approvals/12.md"
printf '{"schema": "completion/v2", "criteria": [{"criterion": "The owner approves", "gate": "owner_approval", "status": "met", "evidence": "the owner said so in the conversation"}]}\n' \
  >"$repo/.agents/completion/12.json"
printf 'The owner said in the conversation: approved, merge it.\n' >"$repo/.agents/handoffs/12.md"
printf 'approved\n' >"$repo/.agents/owner-approval"
earlier="$(git -C "$repo" rev-parse HEAD~1)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review owner-login APPROVED "$head"), $(review owner-identity COMMENTED "$head"), $(review owner-identity APPROVED "$earlier")]"
run_merge "$repo" 12
expect_refused "$repo" "a forged approval" "the change is Level 3" "the owner's identity owner-identity does not approve exactly the head $head"

# A lowering request whose head has no approving review by the identity.
message "$tmp/m4" "$lowering" "- required from the project owner, for exactly this commit"
repo="$(setup_repo lowering "$owned" "$tmp/m4" .agents/approvals/12.md)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$(git -C "$repo" rev-parse HEAD~1)")]"
run_merge "$repo" 12
expect_refused "$repo" "a lowering without the identity's approval of the head" \
  "a lowering of the level is requested" "it changes code-owned paths: .agents/approvals/12.md" \
  "is redone at the required level before the merge"
# A later request for changes outweighs an earlier approval of the head.
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head"), $(review owner-identity CHANGES_REQUESTED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "an approval withdrawn by a later request for changes" "does not approve exactly the head $head"
# The identity's approving review of exactly the head, with GitHub's decision.
pr "$repo" CLEAN APPROVED "[$(review owner-login APPROVED "$head"), $(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_merged "$repo" "a lowering that the identity approved for the head"
grep -Fq "The owner's identity owner-identity approves exactly the head $head." "$repo.out" || fail "the approving identity was not named"
# GitHub's decision still decides: without it, no merge.
pr "$repo" BLOCKED REVIEW_REQUIRED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "an identity's approval while GitHub blocks the merge" "merge state BLOCKED"

# Until the identity exists (the code-owners file names only the agent's
# login, as on the day of ADR 020), no Level 3 pull request is merged here.
message "$tmp/m5" "$level2"
repo="$(IDENTITY='' setup_repo no-identity '* @owner-login' "$tmp/m5" scripts/lib/completion.sh)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review owner-login APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "a protected path before the identity exists" \
  "it changes code-owned paths: scripts/lib/completion.sh" "the owner's identity does not exist yet" \
  "naming the head $head; no script takes that word as approval"

# Another code owner is not the owner's identity: a team member's approval of
# exactly the head, with GitHub's decision approved, merges nothing.
repo="$(setup_repo other-owner "$owned" "$tmp/m4" .agents/approvals/12.md)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review team-member APPROVED "$head"), $(review owner-identity COMMENTED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "another code owner's approval" \
  "the owner's identity owner-identity does not approve exactly the head $head" "no other code owner's review counts"
# Without the configured identity, code owners other than the agent's login
# are no identity of the owner either.
repo="$(IDENTITY='' setup_repo unconfigured "$owned" "$tmp/m4" .agents/approvals/12.md)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head"), $(review team-member APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "code owners without a configured identity" \
  "the owner's identity does not exist yet" "has no line 'owner-identity: <login>'"
# A configured identity that is the agent's login, or that the code-owners
# file does not name, is refused.
repo="$(IDENTITY=Owner-Login setup_repo agent-identity "$owned" "$tmp/m4" .agents/approvals/12.md)"
pr "$repo" CLEAN APPROVED "[$(review owner-login APPROVED "$(git -C "$repo" rev-parse HEAD)")]"
run_merge "$repo" 12
expect_refused "$repo" "the agent's login configured as the identity" "is the login this runs with"
repo="$(IDENTITY=someone-else setup_repo not-owner "$owned" "$tmp/m4" .agents/approvals/12.md)"
pr "$repo" CLEAN APPROVED "[$(review someone-else APPROVED "$(git -C "$repo" rev-parse HEAD)")]"
run_merge "$repo" 12
expect_refused "$repo" "an identity that is no code owner" "someone-else is no code owner"
# The identity is read from the base: a feature that configures it merges
# nothing on it.
repo="$(IDENTITY='' setup_repo self-configured "$owned" "$tmp/m4" .agents/policies/guardrails.conf)"
printf 'owner-identity: team-member\n' >>"$repo/.agents/policies/guardrails.conf"
git -C "$repo" commit -qa --amend --no-edit
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review team-member APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "an identity configured by the feature itself" "has no line 'owner-identity: <login>'"

# The level is derived from the diff, not read from the commit: a hand-made
# commit that states Level 2 while its diff changes a dependency file is
# Level 3 by that trigger. Without the committed approval request and the
# identity's approval of exactly the head, nothing is merged.
message "$tmp/m7" "$level2"
repo="$(setup_repo forged-level "$owned" "$tmp/m7" requirements.txt)"
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN "" '[]'
run_merge "$repo" 12
expect_refused "$repo" "a dependency change under a forged Level 2 statement" \
  "the diff shows escalation triggers, so the change is Level 3: dependency file changed: requirements.txt" \
  "does not commit the approval request .agents/approvals/12.md" \
  "the owner's identity owner-identity does not approve exactly the head $head"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "a trigger without the committed approval request, approved by the identity" \
  "does not commit the approval request .agents/approvals/12.md"
# With the request committed, the identity's approval of the head decides.
mkdir -p "$repo/.agents/approvals"
printf 'Issue: #12\nLevel: 3\nDerived from: dependency file changed\nTree: x\n' >"$repo/.agents/approvals/12.md"
git -C "$repo" add .agents/approvals/12.md
git -C "$repo" commit -q --amend --no-edit
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$(git -C "$repo" rev-parse HEAD~1)")]"
run_merge "$repo" 12
expect_refused "$repo" "a trigger with the request, approved only on an earlier commit" \
  "the diff shows escalation triggers" "does not approve exactly the head $head"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_merged "$repo" "a trigger with the request, approved by the identity for the head"
# A removed assertion under a forged Level 2 statement, likewise.
repo="$(setup_repo forged-assertion "$owned" "$tmp/m7")"
git -C "$repo" switch -q main
mkdir -p "$repo/tests/unit"
printf 'def test_x():\n    assert 1 + 1 == 2\n' >"$repo/tests/unit/test_x.py"
git -C "$repo" add tests/unit/test_x.py
git -C "$repo" commit -qm "A test"
git -C "$repo" switch -q feature/12-marker
git -C "$repo" rebase -q main
printf 'def test_x():\n    pass\n' >"$repo/tests/unit/test_x.py"
git -C "$repo" commit -qa --amend --no-edit
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN "" '[]'
run_merge "$repo" 12
expect_refused "$repo" "a removed assertion under a forged Level 2 statement" \
  "assertion removed or changed: tests/unit/test_x.py" \
  "does not commit the approval request .agents/approvals/12.md" \
  "the owner's identity owner-identity does not approve exactly the head $head"

# The assessed level is read from the latest review of the feature for
# exactly the head: a hand-made commit that states Level 2 and a review round
# while the review assesses Level 3 needs the committed approval request and
# the identity's approval of exactly the head.
REVIEW_LINE="Review: round 1, approve, by a reviewer" message "$tmp/m8" "$level2"
repo="$(setup_repo forged-assessment "$owned" "$tmp/m8")"
feature_review "$repo" 1 3
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN "" '[]'
run_merge "$repo" 12
expect_refused "$repo" "a Level 3 review assessment under a forged Level 2 statement" \
  "the independent review .agents/reviews/feature-12-marker-review-01.json assesses the change as Level 3" \
  "does not commit the approval request .agents/approvals/12.md" \
  "the owner's identity owner-identity does not approve exactly the head $head"
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_refused "$repo" "a Level 3 assessment without the committed approval request, approved by the identity" \
  "does not commit the approval request .agents/approvals/12.md"
mkdir -p "$repo/.agents/approvals"
printf 'Issue: #12\nLevel: 3\nDerived from: the assessment\nTree: x\n' >"$repo/.agents/approvals/12.md"
git -C "$repo" add .agents/approvals/12.md
git -C "$repo" commit -q --amend --no-edit
head="$(git -C "$repo" rev-parse HEAD)"
pr "$repo" CLEAN "" '[]'
run_merge "$repo" 12
expect_refused "$repo" "a review that is not of the head" \
  "the latest review .agents/reviews/feature-12-marker-review-01.json is not a review of exactly the head $head" \
  "the owner's identity owner-identity does not approve exactly the head $head"
feature_review "$repo" 2 3
pr "$repo" CLEAN APPROVED "[$(review owner-identity APPROVED "$head")]"
run_merge "$repo" 12
expect_merged "$repo" "a Level 3 assessment with the request, approved by the identity for the head"
# A review of the head that assesses Level 2 leaves GitHub's decision alone.
repo="$(REVIEW_LINE="Review: round 1, approve, by a reviewer" setup_repo reviewed-level2 "$owned" "$tmp/m8")"
feature_review "$repo" 1 2
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_merged "$repo" "a Level 2 pull request whose review of the head assesses Level 2"
# Uncommitted content besides the head makes the review no review of the head.
printf 'print("y")\n' >"$repo/src/extra.py"
feature_review "$repo" 2 2
run_merge "$repo" 12
expect_refused "$repo" "a review of content other than the head" "is not a review of exactly the head"
# No review in the worktree while the commit claims a review round.
repo="$(setup_repo no-review "$owned" "$tmp/m8")"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_refused "$repo" "a claimed review that is not here" "no review of the feature is in this worktree"

# A commit without the risk statement of finish-feature.sh needs the owner.
printf 'Hand-made commit\n\nRefs #12\n' >"$tmp/m6"
repo="$(setup_repo no-statement "$owned" "$tmp/m6")"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
run_merge "$repo" 12
expect_refused "$repo" "a commit without a risk statement" "the head commit has no risk statement"

# A draft and a head other than the finished one are not merged.
repo="$(setup_repo draft "$owned" "$tmp/m2")"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
jq '.isDraft = true' "$repo.pr.json" >"$repo.pr.tmp" && mv "$repo.pr.tmp" "$repo.pr.json"
run_merge "$repo" 12
expect_refused "$repo" "a draft" "is a draft"
pr "$repo" CLEAN REVIEW_REQUIRED '[]'
jq '.headRefOid = "0000000000000000000000000000000000000000"' "$repo.pr.json" >"$repo.pr.tmp" && mv "$repo.pr.tmp" "$repo.pr.json"
run_merge "$repo" 12
expect_refused "$repo" "another head" "publish the commit that was finished"

echo "merge-feature tests passed"
