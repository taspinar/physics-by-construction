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
  "issue view")
    case "$*" in
      *"--json number"*) echo "$3" ;;
      *) printf 'Title: Test feature\n\nThe marker must exist.\n' ;;
    esac
    ;;
  "issue comment") ;;
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
  printf 'reviewer: claude model-r\ntriage: claude model-t\ntriage-implementer: claude model-i\n' >"$repo/.agents/agents.conf"
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
    printf '%s\n' "$message" | grep -Fx -- "$line" >/dev/null || { printf '%s\n' "$message" >&2; fail "the commit message lacks the line: $line"; }
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
if grep '^pr create' "$repo.gh.log" | grep -F -- "--draft" >/dev/null; then fail "a feature ready for a pull request was opened as a draft"; fi
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

# A change whose paths are Level 3 needs no approval request, even when a
# trigger gives Level 3 too: its protected paths are code-owned, so GitHub
# requires the owner's review without one (ADR 020 decision 3). The request
# is refused as missing only when the paths are below Level 3 (below).
repo="$(setup_repo level3-paths)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a Level 3 change by its paths and a trigger, without an approval request"
grep -Fq "needs the committed approval request" "$repo.out" &&
  fail "a change whose paths are Level 3 was asked for an approval request"
message_has "$repo" "- required: level 3, by the paths" "- stated in the completion record: level 3"
git -C "$repo" log -1 --format=%B | grep -F -- "- escalation trigger: " >/dev/null ||
  fail "the trigger of a change whose paths are Level 3 is not recorded"
[[ ! -e "$repo/.agents/approvals/12.md" ]] || fail "finish-feature.sh created an approval request"

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
git -C "$repo" show --name-only --format= HEAD | grep -Fx ".agents/approvals/12.md" >/dev/null || fail "the approval request was not committed"
message_has "$repo" "- required: level 3, by the triggers" \
  "- escalation trigger: dependency file changed: pyproject.toml (the file is a dependency manifest or lock file)" \
  "- required from the project owner, for exactly this commit" "- the risk level is 3, by the triggers (ADR 020 decision 1)" \
  "- approval request: .agents/approvals/12.md, a request for the owner's review, never an approval"
git -C "$repo" log -1 --format=%B | grep -F "given only as the owner's identity's approving review of exactly the head" >/dev/null ||
  fail "the commit message does not say how the owner's approval is given"

# --- A correction of the approval request (Issues #266 and #382). A request
# that names another tree than the content tree is corrected by
# finish-feature.sh before the check, not refused, and committed as
# corrected; the recorded full run and the review stay valid, since the
# request is no part of the fingerprint.
repo="$(setup_repo request-tree)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
content="$(sed -n 's/^Tree: //p' "$repo/.agents/approvals/12.md")"
sed -i.bak 's/^Tree: .*$/Tree: 0123abcd/' "$repo/.agents/approvals/12.md" && rm "$repo/.agents/approvals/12.md.bak"
run_script "$repo" ./scripts/verify.sh
[[ "$status" -eq 0 && "$(count_runs "$repo")" -eq 1 ]] || { cat "$repo.out" >&2; fail "the full run failed"; }
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "an approval request whose line Tree: names another tree"
grep -Fq "named tree 0123abcd; its line 'Tree:' is refreshed to the content tree $content." "$repo.out" ||
  { cat "$repo.out" >&2; fail "finish-feature.sh does not say that it corrected the line Tree:"; }
git -C "$repo" show HEAD:.agents/approvals/12.md | grep -Fx "Tree: $content" >/dev/null ||
  fail "the committed approval request does not name the content tree"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "correcting the approval request made the full run stale"

# --- The approval request is written by finish-feature.sh in full (Issue
# #463, D12): every field from the derivation, a hand-edited one overwritten,
# any other text dropped; only a lowering's Reason and Owner's word are free.
# The verification stays valid, since the request is no part of the content.
repo="$(setup_repo request-written)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
content="$(sed -n 's/^Tree: //p' "$repo/.agents/approvals/12.md")"
sed -i.bak -e 's/^Issue: .*$/Issue: #99/' -e 's/^Level: .*$/**Level:** two/' -e 's/^Derived from: .*$/Derived from: my guess/' \
  "$repo/.agents/approvals/12.md" && rm "$repo/.agents/approvals/12.md.bak"
run_script "$repo" ./scripts/verify.sh
[[ "$status" -eq 0 && "$(count_runs "$repo")" -eq 1 ]] || { cat "$repo.out" >&2; fail "the full run failed"; }
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "an approval request with hand-edited fields"
grep -Fq "The approval request .agents/approvals/12.md is written from the derivation: level 3, by the triggers" "$repo.out" ||
  { cat "$repo.out" >&2; fail "finish-feature.sh does not say that it wrote the approval request"; }
written="$(git -C "$repo" show HEAD:.agents/approvals/12.md)"
for line in "Issue: #12" "Level: 3" "Tree: $content" \
  "Derived from: the triggers (dependency file changed: pyproject.toml (the file is a dependency manifest or lock file))"; do
  grep -Fx -- "$line" >/dev/null <<<"$written" || fail "the written approval request lacks '$line': $written"
done
if grep -E "Approved:|my guess|#99|two" >/dev/null <<<"$written"; then
  fail "the written approval request keeps hand-written text: $written"
fi
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "writing the approval request made the full run stale"

# A lowering: the derived fields are written, the Reason and the Owner's word
# (with its continuation line) kept as they stand, and nothing else is free.
repo="$(setup_repo request-lowering)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 2
request "$repo" 2 1
awk '/^Owner.s word: / { print "Owner'"'"'s word: \"Lower #12 to Level 2\""; print "  (2026-10-19, in the session)"; next } { print }' \
  "$repo/.agents/approvals/12.md" >"$repo/approval.tmp" && mv "$repo/approval.tmp" "$repo/.agents/approvals/12.md"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a requested lowering whose levels were written by hand"
written="$(git -C "$repo" show HEAD:.agents/approvals/12.md)"
for line in "Level: 3" "Required level: 3" "Requested level: 2" "Reason: the dependency is a pin of the same version" \
  "Owner's word: \"Lower #12 to Level 2\"" "  (2026-10-19, in the session)"; do
  grep -Fx -- "$line" >/dev/null <<<"$written" || fail "the written lowering lacks '$line': $written"
done
fields="$(sed -nE 's/^([A-Z][A-Za-z'"'"' ]*): .*$/\1/p' <<<"$written" | sort | paste -sd ',' -)"
[[ "$fields" == "Derived from,Issue,Level,Owner's word,Reason,Requested level,Required level,Tree" ]] ||
  fail "the written lowering has other fields: $fields"
(
  source "$repo/scripts/lib/risk.sh"
  free="$(risk_request_free_fields "$repo/.agents/approvals/12.md" | sed -nE 's/^([A-Z][A-Za-z'"'"' ]*): .*$/\1/p' | sort | paste -sd ',' -)"
  [[ "$free" == "Owner's word,Reason" ]] || fail "the free fields of the request are not exactly the Reason and the Owner's word: $free"
)

# What stays blocking: a lowering without the owner's word, a stated level
# below the derived one without a lowering, and a Level 3 change without its
# request (above), are refused although the script writes the request.
repo="$(setup_repo request-no-word)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 2
request "$repo" 3 2
sed -i.bak "/^Owner's word:/d; /^Reason:/d" "$repo/.agents/approvals/12.md" && rm "$repo/.agents/approvals/12.md.bak"
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a lowering without the owner's word, in a written request" "has no line 'Reason: ...'" \
  "has no line 'Owner's word: ...'"
repo="$(setup_repo request-below)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 2
request "$repo" 3
review "$repo" "$full"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_no_commit "$repo" "a stated level below the derived one, with a request that asks no lowering" \
  "the completion record states level 2, below the level 3 that the triggers give"

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
git -C "$repo" log -1 --format=%B | grep -F "requested: level 2, in .agents/approvals/12.md: a request only. The change keeps level 3" >/dev/null ||
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

# --- The reviewer is told the verification state of the round (Issue #389):
# a feedback round is a limitation, not a finding; the report says so. The
# content changes first, so that no full pass is recorded for it, and the
# request is written for the new content.
printf 'print("w")\n' >>"$repo/src/code.py"
request "$repo" 3
context="$repo.agent.log.stdin"
run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "a feedback round after the commit failed"; }
grep -Fq "## Verification of this round" "$context" || fail "the reviewer was not told the verification state of the round"
grep -Fq "This is an intermediate round of a Level 3 change (ADR 020 decision 5)" "$context" ||
  fail "the reviewer was not told that the round is an intermediate one"
grep -Fq "Do not report" "$context" && grep -Fq "the missing full run" "$context" ||
  fail "the reviewer was not told that the missing full run is no finding"
grep -Fq "neither 'named in the completion record' nor 'named by the review') is" "$context" ||
  fail "the reviewer was not told that a detected trigger is recorded by the scripts"
stored="$repo/.agents/reviews/feature-12-marker-review-03.json"
grep -Fq "Verification: an intermediate round of a Level 3 change, reviewed on the feedback of the partial run of the groups code at" "${stored%.json}.md" ||
  { cat "${stored%.json}.md" >&2; fail "the report does not render the feedback round as such"; }
grep -Fq "| review round 3, reviewer session | started | claude (model-r) | on the feedback of code" "$repo/.agents/run/12-log" ||
  { cat "$repo/.agents/run/12-log" >&2; fail "the start of the reviewer session is not in the log of the feature"; }
grep -Eq "\| review round 3, reviewer session \| ended \| status 0 \| [0-9]+ s$" "$repo/.agents/run/12-log" ||
  fail "the end of the reviewer session is not in the log of the feature"

# --- --feedback takes a full pass recorded for exactly the content (Issue
# #389): no partial run, and the review counts as one made on the full run.
repo="$(setup_repo review-level3-recorded)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
(cd "$repo" && PATH="$tmp/bin:/usr/bin:/bin" ./scripts/verify.sh >/dev/null 2>&1) || fail "the implementer's full run failed"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "the full run did not run"
run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "--feedback with a recorded full pass failed"; }
grep -Fq "a full pass is recorded for exactly this content" "$repo.out" || fail "the reused full pass was not reported"
stored="$repo/.agents/reviews/feature-12-marker-review-01.json"
[[ "$(jq -r '.verification.status + " " + .verification.tier' "$stored")" == "passed full" ]] ||
  fail "the review on a recorded full pass is not recorded as made on the full run: $(jq -c '.verification' "$stored")"
# The full run ran the group of the feedback check once; --feedback added no run.
[[ "$(grep -c '^feedback$' "$repo/verify-count.log" 2>/dev/null || true)" -eq 1 && "$(count_runs "$repo")" -eq 1 ]] ||
  fail "--feedback ran although a full pass was recorded"
grep -Fq "this round is made on the full run: it can be the" "$repo.agent.log.stdin" ||
  fail "the reviewer was not told that the round can be the final one"
run_script "$repo" ./scripts/finish-feature.sh 12 "Add the marker" --unattended
expect_commit "$repo" "a Level 3 change whose feedback round reused a recorded full pass"
[[ "$(count_runs "$repo")" -eq 1 ]] || fail "finish-feature.sh ran the full verification again"

# --- --feedback takes a recorded full pass by the rule of verify.sh --reuse,
# not by the tier and the tree alone: a pass whose record says the workflow
# self-tests were skipped stands only for a run that would skip them too,
# which this one would not, so it is not taken, and the
# round stays an intermediate one on the partial run (Issue #389, owner's
# review of PR #415).
repo="$(setup_repo review-level3-recorded-without-workflow)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
(cd "$repo" && PATH="$tmp/bin:/usr/bin:/bin" ./scripts/verify.sh >/dev/null 2>&1) || fail "the implementer's full run failed"
sed -i.bak 's/^workflow-tests: .*/workflow-tests: skipped/' "$repo/.agents/verification/passed"
rm -f "$repo/.agents/verification/passed.bak"
(cd "$repo" && ./scripts/verify.sh --reuse-only >/dev/null 2>&1) && fail "verify.sh --reuse-only took a pass made without the workflow self-tests"
run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "--feedback with a pass recorded without the workflow self-tests failed"; }
if grep -Fq "a full pass is recorded for exactly this content" "$repo.out"; then
  fail "--feedback took a full pass recorded without the workflow self-tests that the content needs"
fi
stored="$repo/.agents/reviews/feature-12-marker-review-01.json"
[[ "$(jq -r '.verification.status' "$stored")" == "feedback" ]] ||
  fail "the round on a pass without the workflow self-tests is not an intermediate one: $(jq -c '.verification' "$stored")"
[[ "$(grep -c '^feedback$' "$repo/verify-count.log")" -eq 2 && "$(count_runs "$repo")" -eq 1 ]] ||
  fail "--feedback did not make the partial run when the recorded pass does not stand"

# --- A stale approval request is corrected by review-feature.sh before its
# check (Issue #382), and apply-triage.sh refreshes its line 'Tree:' after a
# fix session (Issue #389).
repo="$(setup_repo stale-request)"
printf 'dependencies = ["numpy"]\n' >>"$repo/pyproject.toml"
record "$repo" complete 3
request "$repo" 3
printf 'a later change\n' >>"$repo/src/code.py"
# A fix session: the request names the tree before it, and the fixes change
# the content; the script refreshes the line to the tree it leaves behind.
request "$repo" 3
MOCK_OUTPUT='{"architecture_impact": {"level": "minor", "rationale": "Within the architecture.", "checked_against": [], "risk_level": 3, "escalation_triggers": ["dependency selection"]}, "verdict": "CHANGES_REQUIRED", "limitations": "", "findings": [{"severity": "major", "title": "Wrong print", "evidence": "src/code.py:2", "impact": "Bug.", "recommendation": "Fix."}]}' \
  run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the review before the fix session failed"; }
stored="$repo/.agents/reviews/feature-12-marker-review-01.json"
MOCK_OUTPUT='{"decisions": [{"finding_id": "M1", "decision": "FIX_NOW", "rationale": "It is wrong.", "followup": null}]}' \
  run_script "$repo" ./scripts/triage-review.sh .agents/reviews/feature-12-marker-review-01.json --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the triage before the fix session failed"; }
tree_before="$(sed -n 's/^Tree: //p' "$repo/.agents/approvals/12.md")"
MOCK_OUTPUT="M1 is fixed." MOCK_WRITE_ACTION="printf 'print(\"z\")\n' >>'$repo/src/code.py'" \
  run_script "$repo" ./scripts/apply-triage.sh .agents/triage/feature-12-marker-review-01-triage.json --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the fix session of a Level 3 change failed"; }
grep -Fq "its line 'Tree:' is refreshed to the content tree" "$repo.out" || { cat "$repo.out" >&2; fail "the fix session did not refresh the approval request"; }
tree_after="$(sed -n 's/^Tree: //p' "$repo/.agents/approvals/12.md")"
[[ "$tree_after" != "$tree_before" && "$tree_after" =~ ^[0-9a-f]{40}$ ]] || fail "the line Tree: was not refreshed: $tree_after"
grep -Fq "Approved: yes, the owner approved this in the conversation" "$repo/.agents/approvals/12.md" ||
  fail "the refresh changed more than the line Tree:"
grep -Fq "The risk level the scripts derive for the change is 3, by the triggers" "$repo.agent.log" ||
  fail "the fix session was not told the level"
grep -Fq "dependency file changed: pyproject.toml" "$repo.agent.log" || fail "the fix session was not told the detected triggers"
grep -Fq "script refreshes its line 'Tree:'" "$repo.agent.log" || fail "the fix session was not told that the script refreshes the request"
grep -Fq "| fixes for round 1, fix session | started | claude (model-i) | 1 FIX_NOW finding(s)" "$repo/.agents/run/12-log" ||
  { cat "$repo/.agents/run/12-log" >&2; fail "the start of the fix session is not in the log of the feature"; }
# The refreshed request passes the next review's check, and the reviewer is
# given the decisions of the earlier round only for deferred or accepted
# findings: none here.
MOCK_OUTPUT='{"architecture_impact": {"level": "minor", "rationale": "Within the architecture.", "checked_against": [], "risk_level": 3, "escalation_triggers": ["dependency selection"]}, "verdict": "PASS", "limitations": "", "findings": [], "dispositions": [{"finding_id": "R01-M1", "status": "resolved", "evidence": "src/code.py:3"}]}' \
  run_script "$repo" ./scripts/review-feature.sh 12 --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the review after the refreshed request failed"; }
grep -Fq "checked by the script: the request names the current content tree" "$repo.agent.log.stdin" ||
  fail "the refreshed request does not name the content tree"
if grep -Fq "## Earlier findings that were deferred or accepted" "$repo.agent.log.stdin"; then
  fail "the reviewer was given deferred or accepted findings although there are none"
fi

echo "risk workflow tests passed"
