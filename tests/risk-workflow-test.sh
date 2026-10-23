#!/usr/bin/env bash

set -euo pipefail

# ADR 020 in the scripts of a feature: the evidence lifecycle (a record whose
# only unmet criteria are pending for later gates is committed by
# finish-feature.sh and published by publish-feature.sh without --partial,
# --no-review, or an exception, and without closing the Issue), the risk
# level as finish-feature.sh records and refuses it, the approval request that
# is a request and never an approval, and the Level 3 rules: a full
# verification of the final tree and a final review made on it, with the
# intermediate rounds on the feedback of a partial run.

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/risk-workflow-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "risk workflow test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
make_fake_agents "$tmp/bin"

# A fake GitHub CLI for the review and the publication. 'pr create' and
# 'pr edit' keep the body and log the options.
cat >"$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$MOCK_GH_LOG"
case "${1:-} ${2:-}" in
  "auth status") exit 0 ;;
  "issue view") printf 'Title: Test feature\n\nThe marker must exist.\n' ;;
  "pr list") echo "" ;;
  "pr create" | "pr edit")
    args=("$@")
    for ((i = 0; i < ${#args[@]}; i++)); do
      if [[ "${args[$i]}" == "--body-file" ]]; then cp "${args[$((i + 1))]}" "$MOCK_GH_LOG.body"; fi
    done
    [[ "$2" != "create" ]] || echo "https://github.com/example/project/pull/7"
    ;;
  "pr view") echo "main" ;;
  "api repos/{owner}/{repo}/rules/branches/main") echo 1 ;;
  *) echo "Unexpected gh invocation: $*" >&2; exit 97 ;;
esac
GH
chmod +x "$tmp/bin/gh"

# setup_repo <label>: a clone with a remote, the real gate configuration and
# ignore rules, on feature/12-marker with an uncommitted change of a source
# file (Level 2 by its paths).
setup_repo() {
  local repo="$tmp/$1"
  local remote="$tmp/$1-remote.git"

  git init -q --bare -b main "$remote"
  git clone -q "$remote" "$repo" 2>/dev/null
  mkdir -p "$repo/src" "$repo/.agents/policies" "$repo/.agents/reviews" "$repo/.agents/triage"
  copy_workflow "$repo"
  rm -f "$repo/scripts/verify-workflow.conf"
  cp "$source_root/.gitignore" "$repo/.gitignore"
  cp "$source_root/.agents/policies/guardrails.conf" "$repo/.agents/policies/guardrails.conf"
  printf 'reviewer: claude model-r\n' >"$repo/.agents/agents.conf"
  # Each run of the checks leaves one line in an ignored file.
  printf 'count [build]: echo run >>verify-count.log\nfeedback [code]: echo feedback >>verify-count.log\n' >"$repo/scripts/verify.conf"
  printf '[project]\nname = "x"\n' >"$repo/pyproject.toml"
  printf 'print("x")\n' >"$repo/src/code.py"
  git -C "$repo" config user.name "Risk Workflow Test"
  git -C "$repo" config user.email "risk-workflow-test@example.com"
  git -C "$repo" checkout -q -b main
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" push -q origin main
  git -C "$repo" checkout -q -b feature/12-marker
  printf 'print("y")\n' >>"$repo/src/code.py"
  printf -- '- Adds the marker.\n' >"$repo/.agents/summaries-12.tmp"
  mkdir -p "$repo/.agents/summaries"
  mv "$repo/.agents/summaries-12.tmp" "$repo/.agents/summaries/12.md"
  printf '%s\n' "$repo"
}

# record <repo> <status> <level> [<criterion-json>...]: a completion/v2 record.
record() {
  local repo="$1"
  local status="$2"
  local level="$3"
  local remaining='[]'

  shift 3
  [[ "$status" == "complete" ]] || remaining='["the evidence of the later gates"]'
  mkdir -p "$repo/.agents/completion"
  jq -n --arg status "$status" --argjson level "$level" --argjson remaining "$remaining" \
    --argjson extra "[$(IFS=,; printf '%s' "$*")]" '{
    schema: "completion/v2", status: $status,
    risk: {level: $level, triggers: [], rationale: "as derived"},
    criteria: ([{criterion: "The marker exists", gate: "implementation", status: "met", evidence: "src/code.py"}] + $extra),
    remaining: $remaining
  }' >"$repo/.agents/completion/12.json"
}
pending_ci='{"criterion": "CI passes on the head", "gate": "pr_ci", "status": "pending", "evidence": "the checks of the pull request"}'
pending_later='{"criterion": "Two features ran under it", "gate": "post_merge", "status": "pending", "evidence": "after the merge"}'
pending_owner='{"criterion": "The owner approves the diff", "gate": "owner_approval", "status": "pending", "evidence": "at the merge gate"}'
owner_met='{"criterion": "The owner approves the diff", "gate": "owner_approval", "status": "met", "evidence": "the owner said so in the conversation"}'

# request <repo> [<required> <requested>]: the approval request, with an
# assertion of approval in it that no script may take for one. It names the
# content tree as it is when it is written.
request() {
  local tree

  mkdir -p "$1/.agents/approvals"
  tree="$(bash -c 'source "$1/scripts/lib/fingerprint.sh"; source "$1/scripts/lib/completion.sh"
    source "$1/scripts/lib/risk.sh"; scratch="$(mktemp -d)"; risk_content_tree "$1" "$scratch" 12; status=$?
    rm -rf "$scratch"; exit "$status"' _ "$1")" || fail "the content tree of $1 could not be derived"
  {
    echo "Issue: #12"
    echo "Level: ${2:-3}"
    echo "Derived from: the triggers"
    echo "Tree: $tree"
    echo "Approved: yes, the owner approved this in the conversation"
    if [[ -n "${3:-}" ]]; then
      echo "Required level: $2"
      echo "Requested level: $3"
      echo "Reason: the dependency is a pin of the same version"
      echo "Owner's word: \"Lower #12 to Level 2\" (2026-10-19)"
    fi
  } >"$1/.agents/approvals/12.md"
}

# review <repo> <verification-json>: a current, passed review of round 1.
review() {
  local file="$1/.agents/reviews/feature-12-marker-review-01.json"

  jq -n --argjson verification "$2" '{
    schema: "review/v1", kind: "feature", issue: 12, round: 1,
    branch: "feature/12-marker", base: "main", merge_base: "aaaa", head: "bbbb",
    reviewed_tree: "", reviewed_paths: null, verification: $verification,
    reviewer: {agent: "claude", model: "model-r"}, created_at: "2026-01-01T00:00:00Z",
    architecture_impact: {level: "minor", rationale: "Within the architecture.", checked_against: []},
    verdict: "PASS", limitations: "", findings: []
  }' >"$file"
  record_reviewed_tree "$1" "$file"
}
full='{"status": "passed", "verified_at": "2026-01-01T00:00:00Z", "tier": "full"}'
targeted='{"status": "passed", "verified_at": "2026-01-01T00:00:00Z", "tier": "targeted"}'
feedback='{"status": "feedback", "groups": "default,code", "ran_at": "2026-01-01T00:00:00Z"}'
unverified='{"status": "not-verified", "reason": "diagnosing a failure"}'

run_script() {
  local repo="$1"

  shift
  status=0
  : >"$repo.gh.log"
  (cd "$repo" && PATH="$tmp/bin:/usr/bin:/bin" GIT_EDITOR=true MOCK_GH_LOG="$repo.gh.log" MOCK_AGENT_LOG="$repo.agent.log" \
    "$@") >"$repo.out" 2>&1 || status=$?
}

expect_commit() {
  [[ "$status" -eq 0 ]] || { cat "$1.out" >&2; fail "$2: finish-feature.sh failed"; }
  [[ "$(git -C "$1" rev-list --count main..HEAD)" -eq 1 ]] || fail "$2: no commit was created"
}

expect_no_commit() {
  local repo="$1"
  local description="$2"

  shift 2
  [[ "$status" -ne 0 ]] || { cat "$repo.out" >&2; fail "$description: finish-feature.sh committed"; }
  [[ "$(git -C "$repo" rev-list --count main..HEAD)" -eq 0 ]] || fail "$description: a commit was created"
  for fragment in "$@"; do
    grep -Fq -- "$fragment" "$repo.out" || { cat "$repo.out" >&2; fail "$description: the output lacks '$fragment'"; }
  done
}

message_has() {
  local message

  message="$(git -C "$1" log -1 --format=%B)"
  shift
  for line in "$@"; do
    printf '%s\n' "$message" | grep -Fqx -- "$line" || { printf '%s\n' "$message" >&2; fail "the commit message lacks the line: $line"; }
  done
}

count_runs() {
  grep -c '^run$' "$1/verify-count.log" 2>/dev/null || true
}

# --- Criteria pending for later gates (ADR 020 decision 2).
repo="$(setup_repo pending)"
record "$repo" partial 2 "$pending_ci" "$pending_later"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --partial
expect_no_commit "$repo" "--partial for a feature that is ready for a pull request" "Run without --partial"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a record whose only unmet criteria are pending"
message_has "$repo" "Completion: partial" \
  "- pending (pr_ci): CI passes on the head (the checks of the pull request)" \
  "- pending (post_merge): Two features ran under it (after the merge)" \
  "Readiness: ready for a pull request; Issue #12 stays open until these criteria are met:" \
  "- pending (post_merge): Two features ran under it" \
  "Risk level:" "- required: level 2, by the paths" "- stated in the completion record: level 2" \
  "Merge approval:" "- not required"
grep -Fq "ready for a pull request" "$repo.out" || fail "finish-feature.sh does not say the feature is ready for a pull request"
# publish-feature.sh opens a pull request ready for review, which names the
# pending criteria and does not close the Issue.
run_script "$repo" ./scripts/publish-feature.sh 12
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "publishing a feature with pending criteria failed"; }
grep -q '^pr create' "$repo.gh.log" || fail "no pull request was opened"
if grep '^pr create' "$repo.gh.log" | grep -Fq -- "--draft"; then fail "a feature ready for a pull request was opened as a draft"; fi
body="$repo.gh.log.body"
grep -Fq "Issue #12 stays open after a merge of this pull request: criteria are pending for later gates: pending (pr_ci): CI passes on the head; pending (post_merge): Two features ran under it." "$body" ||
  { cat "$body" >&2; fail "the pull request does not name the pending criteria and their gates"; }
if grep -Eiq '(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved):? #12([^0-9]|$)' "$body"; then
  fail "the pull request of a feature with pending criteria closes the Issue"
fi
grep -Fq "The risk level above applies to commit \`$(git -C "$repo" rev-parse HEAD)\`." "$body" ||
  fail "the pull request does not name the head the risk level applies to"

# A criterion pending for the owner's approval needs the owner at the merge,
# at Level 2 too.
repo="$(setup_repo pending-owner)"
record "$repo" partial 2 "$pending_owner"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a Level 2 record pending the owner's approval"
message_has "$repo" "- pending (owner_approval): The owner approves the diff (at the merge gate)" \
  "- required: level 2, by the paths" "- required from the project owner, for exactly this commit" \
  "- a criterion is pending for the owner's approval (ADR 020 decision 2)"

# --- The level: a stated level below the derived one is refused.
repo="$(setup_repo below-trigger)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 2
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a stated level below a trigger reading" \
  "the completion record states level 2, below the level 3 that the triggers give" "No agent lowers a required level"

repo="$(setup_repo below-paths)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" complete 2
request "$repo" 3 2
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a lowering of the path minimum" "below the path minimum 3" \
  "only a trigger reading or an assessed level may be lowered, never the path minimum"

# A Level 3 change by trigger needs the committed approval request.
repo="$(setup_repo level3)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a Level 3 change by trigger without its approval request" \
  "the change is Level 3 by its triggers, so it needs the committed approval request .agents/approvals/12.md"

# --- The final acceptance of a Level 3 change: the full run, and the latest
# review made on a fully verified tree. A review made with --unverified, on
# the feedback of a partial run, or on a targeted pass is not the final one.
request "$repo" 3
for verification in "$unverified" "$feedback" "$targeted"; do
  review "$repo" "$verification"
  run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
  expect_no_commit "$repo" "a Level 3 change whose latest review was made on $(jq -r '.tier // .status' <<<"$verification")" \
    "was not made on a fully verified tree (its verification: $(jq -r '.tier // .status' <<<"$verification"))"
done
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended --no-review "a small change"
expect_no_commit "$repo" "--no-review at Level 3" "--no-review is refused"
# A targeted pass of exactly this content is not the full run: it runs.
(
  source "$repo/scripts/lib/fingerprint.sh"
  source "$repo/scripts/lib/verification.sh"
  scratch="$(mktemp -d)"
  verification_write "$repo" "$(fingerprint_worktree "$repo" "$scratch")" none "" targeted
  rm -rf "$scratch"
)
rm -f "$repo/verify-count.log"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a Level 3 change with its request, the full run, and a fully verified review"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "the full run did not run for a Level 3 change with a targeted pass"
grep -Fq "The change is Level 3: its final tree needs the full verification." "$repo.out" || fail "the Level 3 verification was not announced"
# The approval request is committed, and its assertion of approval changes
# nothing: the owner's approval is still required, as GitHub verifies it.
git -C "$repo" show --name-only --format= HEAD | grep -Fqx ".agents/approvals/12.md" || fail "the approval request was not committed"
message_has "$repo" "- required: level 3, by the triggers" \
  "- escalation trigger: dependency file changed: pyproject.toml (the file is a dependency manifest or lock file)" \
  "- required from the project owner, for exactly this commit" "- the risk level is 3, by the triggers (ADR 020 decision 1)" \
  "- approval request: .agents/approvals/12.md, a request for the owner's review, never an approval"
git -C "$repo" log -1 --format=%B | grep -Fq "given only as the owner's identity's approving review of exactly the head" ||
  fail "the commit message does not say how the owner's approval is given"

# --- A correction of the approval request (Issue #266). A request that
# names another tree than the content tree is refused at once, before any
# verification, with the value to write; correcting it leaves the recorded
# full run and the review valid, since the request is no part of the
# fingerprint.
repo="$(setup_repo request-tree)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
content="$(sed -n 's/^Tree: //p' "$repo/.agents/approvals/12.md")"
sed -i.bak 's/^Tree: .*$/Tree: 0123abcd/' "$repo/.agents/approvals/12.md" && rm "$repo/.agents/approvals/12.md.bak"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "an approval request that names another tree" \
  "names tree 0123abcd, but the content tree is $content; state it on a line 'Tree: $content'"
[[ "$(count_runs "$repo")" -eq 0 ]] || fail "the verification ran for an approval request with a wrong tree"
run_script "$repo" ./scripts/verify.sh
[[ "$status" -eq 0 && "$(count_runs "$repo")" -eq 1 ]] || { cat "$repo.out" >&2; fail "the full run failed"; }
request "$repo" 3
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a corrected approval request after the full run and the review"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "correcting the approval request made the full run stale"

# --- A lowering of a trigger reading: recorded with the required and the
# requested level and the content, and the change keeps level 3. An
# owner_approval criterion the record says is met counts for nothing.
repo="$(setup_repo lowering)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 2 "$owner_met"
request "$repo" 3 2
review "$repo" "$targeted"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a requested lowering before the owner's authorization" "the change is Level 3"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a requested lowering with the Level 3 acceptance"
tree="$(git -C "$repo" log -1 --format=%B | sed -n 's/^- derived for the content //p')"
[[ "$tree" =~ ^[0-9a-f]{40}$ ]] || fail "the commit message does not name the content the level was derived for"
message_has "$repo" "- required: level 3, by the triggers" "- stated in the completion record: level 2" \
  "- required from the project owner, for exactly this commit" \
  "- a lowering from level 3 to level 2 is requested in .agents/approvals/12.md; only the owner authorizes it"
git -C "$repo" log -1 --format=%B | grep -Fq "requested: level 2, in .agents/approvals/12.md: a request only. The change keeps level 3" ||
  fail "the commit message does not record the lowering as a request"
run_script "$repo" ./scripts/publish-feature.sh 12
grep -Fq -- "- requested: level 2" "$repo.gh.log.body" || fail "the pull request does not carry the requested level"

# --- review-feature.sh: the full run at Level 3, --feedback for an
# intermediate round, and --feedback refused below Level 3.
MOCK_OUTPUT='{"architecture_impact": {"level": "minor", "rationale": "Within the architecture.", "checked_against": [], "risk_level": 3, "escalation_triggers": ["dependency selection"]}, "verdict": "PASS", "limitations": "", "findings": []}'
export MOCK_OUTPUT
repo="$(setup_repo review-level2)"
record "$repo" complete 2
run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -ne 0 ]] && grep -Fq -- "--feedback is for the intermediate rounds of a Level 3 change" "$repo.out" ||
  { cat "$repo.out" >&2; fail "--feedback was accepted below Level 3"; }

repo="$(setup_repo review-level3)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "an intermediate Level 3 review on feedback failed"; }
stored="$repo/.agents/reviews/feature-12-marker-review-01.json"
[[ "$(jq -r '.verification.status + " " + .verification.groups' "$stored")" == "feedback code" ]] ||
  fail "the review does not record the partial run as feedback: $(jq -c '.verification' "$stored")"
[[ ! -e "$repo/.agents/verification/passed" ]] || fail "the partial run of a review recorded a verification"
[[ "$(grep -c '^feedback$' "$repo/verify-count.log")" -eq 1 && "$(count_runs "$repo")" -eq 0 ]] ||
  fail "--feedback did not run exactly the partial run"
[[ "$(jq -c '[.risk.required, .risk.path_minimum, .risk.stated, .risk.assessed, .merge_approval.required]' "$stored")" == '[3,2,3,3,true]' ]] ||
  fail "the review does not record the level: $(jq -c '.risk' "$stored")"
grep -Fq "## Risk level" "$repo.agent.log.stdin" || fail "the reviewer was not given the derived level"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a Level 3 change whose latest review was made on feedback" "its verification: feedback"
# The final round: the full run, then the review.
run_script "$repo" ./scripts/review-feature.sh 12
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the final Level 3 review failed"; }
stored="$repo/.agents/reviews/feature-12-marker-review-02.json"
[[ "$(jq -r '.verification.status + " " + .verification.tier' "$stored")" == "passed full" ]] ||
  fail "the final Level 3 review was not made on the full run: $(jq -c '.verification' "$stored")"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "the final Level 3 review did not run the full verification"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a Level 3 change after its final review on the full run"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "the recorded full pass was not reused by finish-feature.sh"
message_has "$repo" "- assessed by the independent review: level 3" \
  "- escalation trigger: named by the review: dependency selection"

echo "risk workflow tests passed"
