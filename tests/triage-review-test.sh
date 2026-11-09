#!/usr/bin/env bash

set -euo pipefail

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/triage-review-test.XXXXXX")"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  echo "triage-review test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
make_fake_agents "$tmp/bin"

# The fake GitHub CLI logs created Issues and finds them again by trace token.
cat >"$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail

case "${1:-} ${2:-}" in
  "auth status")
    exit 0
    ;;
  "api repos/{owner}/{repo}/issues/comments/4001")
    printf 'https://api.github.com/repos/example/project/issues/5\tOWNER\n'
    exit 0
    ;;
  "api repos/{owner}/{repo}/issues/comments/4002")
    printf 'https://api.github.com/repos/example/project/issues/5\tCONTRIBUTOR\n'
    exit 0
    ;;
  "api repos/{owner}/{repo}/issues/comments/4003")
    printf 'https://api.github.com/repos/example/project/issues/9\tOWNER\n'
    exit 0
    ;;
  "api "*)
    exit 1
    ;;
  "issue view")
    printf '%s' "${MOCK_ISSUE_CONTEXT:-Title: F02 — Test feature

Test acceptance criteria.}"
    exit 0
    ;;
  "issue comment")
    if [[ -n "${MOCK_GH_COMMENT_EXIT:-}" ]]; then
      echo "simulated comment failure" >&2
      exit "$MOCK_GH_COMMENT_EXIT"
    fi
    shift 2
    issue="$1"
    shift
    while [[ $# -gt 0 ]]; do
      if [[ "$1" == "--body-file" ]]; then
        {
          echo "COMMENT ON #$issue"
          cat "$2"
          echo "END COMMENT"
        } >>"$MOCK_GH_LOG.comments"
      fi
      shift
    done
    exit 0
    ;;
  "issue list")
    if [[ -n "${MOCK_EXISTING_ISSUE:-}" ]]; then
      echo "$MOCK_EXISTING_ISSUE"
    fi
    exit 0
    ;;
  "issue create")
    if [[ -n "${MOCK_GH_CREATE_EXIT:-}" ]]; then
      echo "simulated Issue creation failure" >&2
      exit "$MOCK_GH_CREATE_EXIT"
    fi
    shift 2
    title=""
    body_file=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --title) title="$2"; shift 2 ;;
        --body-file) body_file="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    {
      echo "TITLE: $title"
      cat "$body_file"
    } >>"$MOCK_GH_LOG"
    echo "https://github.com/example/project/issues/123"
    exit 0
    ;;
esac
echo "Unexpected gh invocation: $*" >&2
exit 1
GH
chmod +x "$tmp/bin/gh"

# Creates a repository with a stored review of Issue #5 in the given round.
setup_repo() {
  local repo="$tmp/$1"
  local round="${2:-1}"
  local findings="${3:-default}"

  mkdir -p "$repo/.agents/reviews"
  copy_workflow "$repo"
  printf 'triage: claude model-t\n' >"$repo/.agents/agents.conf"

  if [[ "$findings" == "none" ]]; then
    findings='[]'
    verdict="PASS"
  elif [[ "$findings" != "default" ]]; then
    verdict="CHANGES_REQUIRED"
  else
    verdict="CHANGES_REQUIRED"
    findings='[
      {"id": "C1", "severity": "critical", "title": "Correctness regression", "evidence": "src/a.sh:3", "impact": "Wrong result.", "recommendation": "Fix the branch."},
      {"id": "MIN1", "severity": "minor", "title": "Missing edge-case coverage", "evidence": "tests/a.sh:9\nSecond line.", "impact": "A regression would go unnoticed.", "recommendation": "Add a test."},
      {"id": "S1", "severity": "suggestion", "title": "Rename local helper", "evidence": "src/a.sh:8", "impact": "Readability.", "recommendation": "Rename it."}
    ]'
  fi
  jq -n --argjson round "$round" --argjson findings "$findings" --arg verdict "$verdict" '{
    schema: "review/v1", issue: 5, round: $round, branch: "feature/5-test", base: "main",
    merge_base: "aaaa", head: "bbbb", reviewed_tree: "cccc",
    reviewer: {agent: "codex", model: "model-r"}, created_at: "2026-01-01T00:00:00Z",
    verdict: $verdict, limitations: "", findings: $findings
  }' >"$repo/.agents/reviews/feature-5-test-review-$(printf '%02d' "$round").json"

  git -C "$repo" init -q -b main
  git -C "$repo" config user.name "Triage Test"
  git -C "$repo" config user.email "triage-test@example.com"
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed project"
  record_reviewed_tree "$repo" "$repo/.agents/reviews/feature-5-test-review-$(printf '%02d' "$round").json"

  printf '%s\n' "$repo"
}

run_triage() {
  local repo="$1"
  local answer="$2"
  shift 2

  (
    cd "$repo"
    printf '%s\n' "$answer" |
      PATH="$tmp/bin:/usr/bin:/bin" MOCK_AGENT_LOG="$repo.log" MOCK_GH_LOG="$repo.gh" \
        ./scripts/triage-review.sh "$@"
  ) >"$repo.out" 2>&1
}

expect_no_triage() {
  local repo="$1"
  local description="$2"
  shift 2

  if run_triage "$repo" y "$@"; then
    cat "$repo.out" >&2
    fail "expected failure: $description"
  fi
  if compgen -G "$repo/.agents/triage/*" >/dev/null; then
    fail "a triage artifact was stored although: $description"
  fi
  [[ ! -e "$repo.gh" ]] || fail "a follow-up Issue was created although: $description"
}

review=".agents/reviews/feature-5-test-review-01.json"
valid_decisions='{"decisions": [
  {"finding_id": "C1", "decision": "FIX_NOW", "rationale": "Correctness blocks the feature.", "followup": null},
  {"finding_id": "MIN1", "decision": "DEFER", "rationale": "Valuable but not blocking.", "followup": {"title": "Add boundary-condition coverage", "recommended_action": "Add focused tests.", "acceptance_criteria": ["The boundary is covered by a test."]}},
  {"finding_id": "S1", "decision": "ACCEPT", "rationale": "The name is adequate.", "followup": null}
]}'
# A Critical finding may not be deferred.
downgraded_decisions="$(jq '.decisions[0] = {"finding_id": "C1", "decision": "DEFER", "rationale": "Later.", "followup": {"title": "Fix it later", "recommended_action": "Fix.", "acceptance_criteria": ["Fixed."]}}' <<<"$valid_decisions")"
# A finding of the review is missing.
incomplete_decisions="$(jq 'del(.decisions[2])' <<<"$valid_decisions")"
export MOCK_OUTPUT="$valid_decisions"

# Approval stores validated decisions and creates exactly the deferred
# follow-up Issue with a provenance-prefixed title.
repo="$(setup_repo approve)"
run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "approved triage failed"
}
artifact="$repo/.agents/triage/feature-5-test-review-01-triage"
[[ -f "$artifact.json" && -f "$artifact.md" ]] || fail "triage artifact and report were not stored"
[[ "$(jq -c '[.schema, .issue, .source_review, (.decisions | map(.decision))]' "$artifact.json")" == \
  "[\"triage/v1\",5,\"$review\",[\"FIX_NOW\",\"DEFER\",\"ACCEPT\"]]" ]] || fail "stored triage is incomplete"
[[ "$(jq -r '.decisions[1].followup | "\(.title) #\(.issue_number)"' "$artifact.json")" == \
  "[F02][R01][MIN1] Add boundary-condition coverage #123" ]] || fail "follow-up Issue was not recorded with its provenance"
[[ "$(grep -c '^TITLE:' "$repo.gh")" -eq 1 ]] || fail "exactly one follow-up Issue was expected"
grep -Fqx "TITLE: [F02][R01][MIN1] Add boundary-condition coverage" "$repo.gh" || fail "follow-up title lacks provenance"
grep -Fq "triage-source:$review#MIN1" "$repo.gh" || fail "follow-up Issue lacks its trace token"
grep -Fqx "Second line." "$repo.gh" || fail "follow-up Issue lacks the multi-line evidence"
grep -Fq -- "--strict-mcp-config --permission-mode dontAsk --tools Read,Glob,Grep" "$repo.log" || fail "triage agent was not read-only"
grep -Fq -- "--json-schema" "$repo.log" || fail "triage agent was not given the schema"
grep -Fq "Correctness regression" "$repo.log.stdin" || fail "findings were not supplied to the triage agent"

# One comment with both reports is published on the source Issue, and the
# publication is recorded in the triage.
grep -Eq '"published_at": "[0-9]{4}-' "$artifact.json" || fail "the publication was not recorded in the triage"
[[ "$(grep -c '^COMMENT ON #5$' "$repo.gh.comments")" -eq 1 ]] || fail "exactly one comment on Issue #5 was expected"
grep -Fq "C1. Correctness regression" "$repo.gh.comments" || fail "the comment lacks the review report"
grep -Fq "## Fix now" "$repo.gh.comments" || fail "the comment lacks the triage report"
grep -Fq "#123" "$repo.gh.comments" || fail "the comment lacks the follow-up Issue link"
if grep -Fq "Generated from" "$repo.gh.comments"; then
  fail "the comment contains the generated-file marker"
fi

# The complete follow-up proposal is shown before the approval question.
proposal="$(sed '/Proceed with this triage/,$d' "$repo.out")"
for shown in "Add focused tests." "The boundary is covered by a test."; do
  [[ "$proposal" == *"$shown"* ]] || fail "the proposal did not show before approval: $shown"
done

# A second approved round reuses the recorded Issue instead of creating one.
run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "repeated triage failed"
}
[[ "$(jq -r '.decisions[1].followup.issue_number' "$artifact-02.json")" == "123" ]] ||
  fail "repeated triage did not reuse the existing follow-up Issue"
[[ "$(grep -c '^TITLE:' "$repo.gh")" -eq 1 ]] || fail "repeated triage created a duplicate follow-up Issue"

# Without a local record, an Issue found by its trace token is reused.
repo="$(setup_repo found-remotely)"
MOCK_EXISTING_ISSUE="https://github.com/example/project/issues/77" run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "triage with an existing remote Issue failed"
}
[[ "$(jq -r '.decisions[1].followup.issue_number' "$repo/.agents/triage/feature-5-test-review-01-triage.json")" == "77" ]] ||
  fail "an existing remote follow-up Issue was not reused"
[[ ! -e "$repo.gh" ]] || fail "a duplicate of an existing remote follow-up Issue was created"

# The published review is rendered from the JSON, not from an edited report,
# and a record too long for one comment is split rather than shortened.
repo="$(setup_repo long-report)"
printf 'Edited report that must not be published.\n' >"$repo/.agents/reviews/feature-5-test-review-01.md"
long_evidence="$(printf 'evidence line %s\\n' $(seq 1 4000))"
jq --arg evidence "$long_evidence" '.findings[1].evidence = $evidence' \
  "$repo/$review" >"$repo/$review.tmp"
mv "$repo/$review.tmp" "$repo/$review"
run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "triage with a long review failed"
}
if grep -Fq "Edited report that must not be published." "$repo.gh.comments"; then
  fail "an edited Markdown report was published instead of the JSON"
fi
parts="$(grep -c '^COMMENT ON #5$' "$repo.gh.comments")"
[[ "$parts" -ge 2 ]] || fail "a record too long for one comment was not split"
grep -Fq "evidence line 4000" "$repo.gh.comments" || fail "the long review was shortened"
grep -Fq "## Fix now" "$repo.gh.comments" || fail "the split record lacks the triage report"

# A failed publication keeps the stored triage and tells how to retry.
repo="$(setup_repo comment-fails)"
if MOCK_GH_COMMENT_EXIT=1 run_triage "$repo" y "$review"; then
  fail "a failed publication returned success"
fi
[[ -f "$repo/.agents/triage/feature-5-test-review-01-triage.json" ]] ||
  fail "a failed publication discarded the stored triage"
triage_file="$repo/.agents/triage/feature-5-test-review-01-triage.json"
[[ "$(jq -r '.published_at // "none"' "$triage_file")" == "none" ]] || fail "a failed publication was recorded as published"
grep -Fq "./scripts/triage-review.sh --publish .agents/triage/feature-5-test-review-01-triage.json" "$repo.out" ||
  fail "a failed publication did not print the retry command"
(
  cd "$repo"
  PATH="$tmp/bin:/usr/bin:/bin" MOCK_GH_LOG="$repo.gh" ./scripts/triage-review.sh --publish .agents/triage/feature-5-test-review-01-triage.json
) >"$repo.retry.out" 2>&1 || {
  cat "$repo.retry.out" >&2
  fail "retrying the publication failed"
}
[[ "$(grep -c '^COMMENT ON #5$' "$repo.gh.comments")" -eq 1 ]] || fail "the retry did not publish the reports"
grep -Eq '"published_at": "[0-9]{4}-' "$triage_file" || fail "the retried publication was not recorded"

# When Issue creation fails, no triage artifact is stored.
repo="$(setup_repo create-fails)"
if MOCK_GH_CREATE_EXIT=1 run_triage "$repo" y "$review"; then
  fail "a failed follow-up Issue creation returned success"
fi
if compgen -G "$repo/.agents/triage/*" >/dev/null; then
  fail "a triage artifact was stored although a follow-up Issue could not be created"
fi

# Without a feature ID in the Issue title, the Issue number is the provenance.
repo="$(setup_repo fallback 7)"
MOCK_ISSUE_CONTEXT=$'Title: Test feature without roadmap ID\n\nBody.' \
  run_triage "$repo" y ".agents/reviews/feature-5-test-review-07.json" || {
  cat "$repo.out" >&2
  fail "triage without a feature ID failed"
}
grep -Fqx "TITLE: [#5][R07][MIN1] Add boundary-condition coverage" "$repo.gh" || fail "fallback provenance is wrong"

# Declining has no side effects.
repo="$(setup_repo decline)"
run_triage "$repo" n "$review" --agent codex --model model-c || fail "declined triage returned an error"
if compgen -G "$repo/.agents/triage/*" >/dev/null || [[ -e "$repo.gh" || -e "$repo.gh.comments" ]]; then
  fail "declined triage had side effects"
fi
grep -Fq -- "--sandbox read-only" "$repo.log" || fail "Codex triage agent was not sandboxed read-only"
grep -Fq -- "--output-schema" "$repo.log" || fail "Codex triage agent was not given the schema"

# Invalid decisions are retried once and then rejected before any side effect.
# The triage agent may not supply script-owned fields or more than one result.
owned_fields_decisions="$(jq '.decisions[0].severity = "minor"' <<<"$valid_decisions")"
# A required field is absent rather than null.
missing_field_decisions="$(jq 'del(.decisions[2].followup)' <<<"$valid_decisions")"

# One invalid result per rule, each derived from the valid decisions.
invalid_decisions=(
  "not json"
  "$valid_decisions $valid_decisions"
  "$downgraded_decisions"
  "$incomplete_decisions"
  "$owned_fields_decisions"
  "$missing_field_decisions"
  "$(jq '.decisions += [.decisions[2]]' <<<"$valid_decisions")"
  "$(jq '.decisions[2].finding_id = "S9"' <<<"$valid_decisions")"
  "$(jq '.decisions[2].decision = "LATER"' <<<"$valid_decisions")"
  "$(jq '.decisions[2].rationale = ""' <<<"$valid_decisions")"
  "$(jq '.decisions[1].followup = null' <<<"$valid_decisions")"
  "$(jq '.decisions[1].followup.title = ""' <<<"$valid_decisions")"
  "$(jq '.decisions[1].followup.recommended_action = ""' <<<"$valid_decisions")"
  "$(jq '.decisions[1].followup.acceptance_criteria = []' <<<"$valid_decisions")"
  "$(jq '.decisions[2].followup = .decisions[1].followup' <<<"$valid_decisions")"
)
for index in "${!invalid_decisions[@]}"; do
  invalid="${invalid_decisions[$index]}"
  repo="$(setup_repo "invalid-$index")"
  MOCK_OUTPUT="$invalid" expect_no_triage "$repo" "the decisions are invalid" "$review"
  [[ "$(grep -c '^AGENT=' "$repo.log")" -eq 2 ]] || fail "invalid decisions were not retried exactly once"
done

repo="$(setup_repo retry)"
MOCK_OUTPUT_FIRST="$incomplete_decisions" run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "valid decisions after one invalid result were rejected"
}
grep -Fq "finding S1 was not classified" "$repo.log" || fail "the retry prompt lacks the rejection reason"

# A triage agent that fails or changes the working tree is rejected.
repo="$(setup_repo agent-fails)"
MOCK_AGENT_EXIT=9 expect_no_triage "$repo" "the triage agent failed" "$review"

repo="$(setup_repo modifies)"
MOCK_AGENT_ACTION="printf 'x\n' >'$repo/note.txt'" expect_no_triage "$repo" "the triage agent changed the working tree" "$review"

# A review of content that changed since is stale and is not triaged.
repo="$(setup_repo stale)"
printf 'changed after the review\n' >>"$repo/AGENTS.md"
expect_no_triage "$repo" "the review is stale" "$review"
grep -Fq "stale" "$repo.out" || fail "a stale review was not reported as stale"
[[ ! -e "$repo.log" ]] || fail "a triage agent was started for a stale review"

# A review without findings needs no agent and still records an approved triage.
repo="$(setup_repo none 1 none)"
run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "triage of a review without findings failed"
}
[[ "$(jq '.decisions | length' "$repo/.agents/triage/feature-5-test-review-01-triage.json")" -eq 0 ]] ||
  fail "triage of a review without findings is not empty"
[[ ! -e "$repo.log" ]] || fail "a triage agent was started for a review without findings"

# Invalid inputs fail before an agent starts.
repo="$(setup_repo preconditions)"
printf '# report\n' >"$repo/.agents/reviews/feature-5-test-review-01.md"
expect_no_triage "$repo" "the input is the generated report" ".agents/reviews/feature-5-test-review-01.md"
expect_no_triage "$repo" "the review does not exist" ".agents/reviews/missing.json"
printf '{"schema": "other"}\n' >"$repo/.agents/reviews/other.json"
expect_no_triage "$repo" "the file is not a review artifact" ".agents/reviews/other.json"
expect_no_triage "$repo" "the agent is unsupported" "$review" --agent copilot --model model-x
[[ ! -e "$repo.log" ]] || fail "a triage agent was started despite failed preconditions"

# --unattended approves the proposal without a question, and both the
# artifact and the published record say that no human approved it.
repo="$(setup_repo unattended)"
run_triage "$repo" "" "$review" --unattended || {
  cat "$repo.out" >&2
  fail "an unattended triage failed"
}
artifact="$repo/.agents/triage/feature-5-test-review-01-triage"
if grep -Fq "Proceed with this triage?" "$repo.out"; then fail "an unattended triage asked for approval"; fi
[[ "$(jq -r '.unattended' "$artifact.json")" == "true" ]] || fail "the artifact does not record the unattended approval"
[[ "$(jq -r '.decisions[0].decision' "$artifact.json")" == "FIX_NOW" ]] || fail "the unattended triage lost its decisions"
grep -Fq "by an unattended run; no human approved these decisions" "$artifact.md" ||
  fail "the report does not say that no human approved the triage"
grep -Fq "no human approved these decisions" "$repo.gh.comments" ||
  fail "the published triage does not say that no human approved it"
[[ "$(grep -c '^TITLE:' "$repo.gh")" -eq 1 ]] || fail "the unattended triage did not create the follow-up Issue"

# The proposal must still be valid: nothing is approved otherwise.
repo="$(setup_repo unattended-invalid)"
if MOCK_OUTPUT="$downgraded_decisions" run_triage "$repo" "" "$review" --unattended; then
  fail "an unattended triage approved invalid decisions"
fi
if compgen -G "$repo/.agents/triage/*.json" >/dev/null; then fail "invalid decisions were stored unattended"; fi

# A major finding is FIX_NOW, except that a triage you approve may defer or
# accept a further instance of a class you have bounded on the Issue (Issue
# #389); unattended, every major finding stays FIX_NOW, and a stored triage
# that says unattended is checked by the same rule.
major_review='[
  {"id": "M1", "severity": "major", "title": "One more number word", "evidence": "src/count.py:9", "impact": "One more instance of the class the owner bounded.", "recommendation": "Fix."},
  {"id": "S1", "severity": "suggestion", "title": "Rename", "evidence": "src/count.py:2", "impact": "Readability.", "recommendation": "Rename."}
]'
major_deferred='{"decisions": [
  {"finding_id": "M1", "decision": "DEFER", "rationale": "A further instance of the class the owner bounded on the Issue (https://github.com/example/project/issues/5#issuecomment-4001).", "followup": {"title": "Number words of the count validator", "recommended_action": "Handle every word form.", "acceptance_criteria": ["Every number word is counted."]}},
  {"finding_id": "S1", "decision": "ACCEPT", "rationale": "Adequate.", "followup": null}
]}'
repo="$(setup_repo major-deferred-attended 1 "$major_review")"
MOCK_OUTPUT="$major_deferred" run_triage "$repo" y "$review" || {
  cat "$repo.out" >&2
  fail "an attended triage that defers a major finding was refused"
}
artifact="$repo/.agents/triage/feature-5-test-review-01-triage"
[[ "$(jq -r '.decisions[0].decision' "$artifact.json")" == "DEFER" ]] || fail "the deferred major finding was not stored"
[[ "$(grep -c '^TITLE:' "$repo.gh")" -eq 1 ]] || fail "the deferred major finding got no follow-up Issue"
grep -Fq "This triage is approved by the owner at the prompt" "$repo.log" || fail "the triage agent was not told that the triage is attended"
grep -Fq "a further instance of a" "$repo.log" || fail "the triage agent was not told the one exception for a major finding"

# The exception needs a verifiable comment of the owner on this Issue: no
# URL, a comment of someone else, of another Issue, or a missing one is refused.
bad_n=0
for bad in 'Bounded by the owner (comment of 2026-11-06).' \
  'Class bounded: https://github.com/example/project/issues/5#issuecomment-4002' \
  'Class bounded: https://github.com/example/project/issues/5#issuecomment-4003' \
  'Class bounded: https://github.com/example/project/issues/5#issuecomment-4999'; do
  bad_n=$((bad_n + 1))
  repo="$(setup_repo "major-deferred-bad-comment-$bad_n" 1 "$major_review")"
  if MOCK_OUTPUT="$(jq -c --arg r "$bad" '.decisions[0].rationale = $r' <<<"$major_deferred")" run_triage "$repo" y "$review"; then
    fail "an attended triage deferred a major finding with the rationale: $bad"
  fi
  if compgen -G "$repo/.agents/triage/*.json" >/dev/null; then fail "a major deferral without an owner comment was stored"; fi
done

repo="$(setup_repo major-deferred-unattended 1 "$major_review")"
if MOCK_OUTPUT="$major_deferred" run_triage "$repo" "" "$review" --unattended; then
  fail "an unattended triage deferred a major finding"
fi
grep -Fq "major finding M1 must be FIX_NOW: only a triage that the owner approves may defer or accept a major finding, never an unattended one" "$repo.out" ||
  { cat "$repo.out" >&2; fail "the refusal of the unattended deferral does not name the rule"; }
grep -Fq "This triage is approved without a human (--unattended): every critical" "$repo.log" ||
  fail "the triage agent was not told that the triage is unattended"
if compgen -G "$repo/.agents/triage/*.json" >/dev/null; then fail "a deferred major finding was stored unattended"; fi
# The stored artifact of an attended triage, marked unattended by hand, is
# invalid: the rule is checked again on the artifact.
jq '.unattended = true' "$artifact.json" >"$tmp/major-unattended.json"
(
  source "$source_root/scripts/lib/review-data.sh"
  triage_artifact_errors "$tmp/major-unattended.json" "$tmp/major-deferred-attended/$review" | grep -F "major finding M1 must be FIX_NOW" >/dev/null
) || fail "a stored unattended triage that defers a major finding was accepted"

# An approval that you gave says nothing about an unattended run, and the
# artifact records it as unattended: false.
repo="$(setup_repo attended)"
run_triage "$repo" y "$review" || fail "an attended triage failed"
artifact="$repo/.agents/triage/feature-5-test-review-01-triage"
[[ "$(jq -r '.unattended' "$artifact.json")" == "false" ]] || fail "an attended triage was recorded as unattended"
if grep -Fq "unattended" "$artifact.md"; then fail "the report of an attended triage mentions an unattended run"; fi
# A triage of the old format has no marker. It stays valid when its
# decisions were valid under the old rules (every major FIX_NOW), so a
# feature in progress does not stop at the commit; a missing marker is never
# read as attended, so a deferred major without the explicit
# `unattended: false` is refused, and a marker that is not a boolean too.
jq 'del(.unattended)' "$artifact.json" >"$tmp/no-marker.json"
(
  source "$source_root/scripts/lib/review-data.sh"
  errors="$(triage_artifact_errors "$tmp/no-marker.json" "$repo/$review")"
  [[ -z "$errors" ]] || { echo "$errors" >&2; exit 1; }
) || fail "a triage of the old format without the unattended marker was refused"
jq 'del(.unattended)' "$tmp/major-deferred-attended/.agents/triage/feature-5-test-review-01-triage.json" >"$tmp/major-no-marker.json"
(
  source "$source_root/scripts/lib/review-data.sh"
  triage_artifact_errors "$tmp/major-no-marker.json" "$tmp/major-deferred-attended/$review" | grep -F "major finding M1 must be FIX_NOW" >/dev/null
) || fail "a triage without the unattended marker that defers a major finding was accepted"
jq '.unattended = "no"' "$artifact.json" >"$tmp/bad-marker.json"
(
  source "$source_root/scripts/lib/review-data.sh"
  triage_artifact_errors "$tmp/bad-marker.json" "$repo/$review" | grep -F "unattended must be true, false, or absent" >/dev/null
) || fail "a triage with a marker that is not a boolean was accepted"

echo "triage-review tests passed"
