#!/usr/bin/env bash

set -euo pipefail

# The completion gate of a feature: what counts as a valid completion record,
# what a handoff note lists as remaining work, and how the two decide.

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/completion-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "completion test failed: $*" >&2
  exit 1
}

source "$source_root/scripts/lib/completion.sh"

root="$tmp/project"
mkdir -p "$root/.agents/completion" "$root/.agents/handoffs" "$root/.agents/summaries"
record="$(completion_record "$root" 7)"
[[ "$record" == "$root/.agents/completion/7.json" ]] || fail "the record of an Issue is not where the contract says: $record"
note="$root/.agents/handoffs/7.md"

complete='{"schema": "completion/v1", "status": "complete", "criteria": [
  {"criterion": "Recipes can be searched", "status": "met", "evidence": "tests/test_search.py"},
  {"criterion": "Works offline", "status": "not_applicable", "evidence": "the Issue dropped it in a comment"}
], "remaining": []}'
partial='{"schema": "completion/v1", "status": "partial", "criteria": [
  {"criterion": "Recipes can be searched", "status": "met", "evidence": "tests/test_search.py"},
  {"criterion": "The page works without JavaScript", "status": "not_met", "evidence": "not started; plan step 4"}
], "remaining": ["Plan steps 4 to 6"]}'

# expect_errors <description> <record-json> <expected-error>...
expect_errors() {
  local description="$1"
  local errors

  printf '%s\n' "$2" >"$record"
  errors="$(completion_errors "$record")"
  shift 2
  if [[ $# -eq 0 ]]; then
    [[ -z "$errors" ]] || fail "$description: a valid record was refused: $errors"
    return 0
  fi
  for expected in "$@"; do
    printf '%s\n' "$errors" | grep -Fx "$expected" >/dev/null || fail "$description: missing error '$expected' in: $errors"
  done
}

expect_errors "a complete record" "$complete"
expect_errors "a partial record" "$partial"
expect_errors "a blocked record" "$(printf '%s' "$partial" | sed 's/"partial"/"blocked"/')"
expect_errors "not JSON" "status: complete" "it is not valid JSON"
expect_errors "not an object" '["complete"]' "it is not a JSON object"
expect_errors "an empty object" '{}' 'schema must be "completion/v2" (or "completion/v1" for a feature started before ADR 020)' "status must be complete, partial, or blocked" \
  "criteria must list at least one acceptance criterion" "remaining must be a list of texts; an empty list when nothing remains"
expect_errors "an unknown status" "$(printf '%s' "$complete" | sed 's/"complete"/"done"/')" \
  "status must be complete, partial, or blocked"
expect_errors "no criteria" '{"schema": "completion/v1", "status": "complete", "criteria": [], "remaining": []}' \
  "criteria must list at least one acceptance criterion"
expect_errors "a criterion without evidence" \
  '{"schema": "completion/v1", "status": "complete", "criteria": [{"criterion": "It works", "status": "met", "evidence": " "}], "remaining": []}' \
  "criterion 1 has no evidence"
expect_errors "a criterion without text or a known status" \
  '{"schema": "completion/v1", "status": "partial", "criteria": [{"criterion": "It works", "status": "met", "evidence": "a test"}, {"status": "yes", "evidence": "x"}], "remaining": ["more"]}' \
  "criterion 2 has no text" "criterion 2: status must be met, not_met, or not_applicable"
# The status has to follow from the criteria and from what remains.
expect_errors "complete with a criterion that is not met" \
  '{"schema": "completion/v1", "status": "complete", "criteria": [{"criterion": "It works", "status": "not_met", "evidence": "not started"}], "remaining": []}' \
  "status is complete, but a criterion is not met"
expect_errors "complete with work that remains" \
  '{"schema": "completion/v1", "status": "complete", "criteria": [{"criterion": "It works", "status": "met", "evidence": "a test"}], "remaining": ["the documentation"]}' \
  "status is complete, but work remains"
expect_errors "partial without saying what is left" \
  '{"schema": "completion/v1", "status": "partial", "criteria": [{"criterion": "It works", "status": "met", "evidence": "a test"}], "remaining": []}' \
  "status is partial, but remaining does not say what is left"
expect_errors "remaining that is not a list of texts" \
  '{"schema": "completion/v1", "status": "partial", "criteria": [{"criterion": "It works", "status": "met", "evidence": "a test"}], "remaining": "steps 3 to 9"}' \
  "remaining must be a list of texts; an empty list when nothing remains"

# What a handoff note lists as remaining, in the shapes implementers write.
# expect_remaining <description> <note> <expected, lines joined by '|'>
expect_remaining() {
  local found

  printf '%b' "$2" >"$note"
  found="$(handoff_remaining "$note" | tr '\n' '|')"
  [[ "$found" == "$3" ]] || fail "$1: found '$found' instead of '$3'"
}

expect_remaining "bold labels on one line each" \
  '**Done:** steps 1 and 2.\n**Remaining:** steps 3 to 9.\n**Open questions:** none\n' "steps 3 to 9.|"
expect_remaining "headings with a list" \
  '## Done\nsteps 1 and 2\n\n## Remaining\n- step 3\n- step 4\n\n## Open questions\nnone\n' "step 3|step 4|"
expect_remaining "a list of labels" \
  '- **Done:** a\n- **In progress:** b\n- **Remaining:** the documentation\n- **Tried and rejected:** c\n' "the documentation|"
expect_remaining "plain labels" 'Done: all\nRemaining work:\n  - docs\nIn progress: none\n' "docs|"
expect_remaining "text on the lines after the label" '**Remaining:**\nstep 3\nstep 4\n' "step 3|step 4|"
for nothing in 'Remaining: none.' '**Remaining:** nothing' '- **Remaining:** n/a' '## Remaining\n\nNone\n' \
  '**Remaining:** -' 'Remaining: nothing remains.'; do
  expect_remaining "nothing remains: $nothing" "$nothing\n" ""
done
expect_remaining "a note reduced to one line" 'Issue 7 is complete.\n' ""
expect_remaining "the word in a sentence" 'The remaining tests pass, and remaining: is not a label here.\n' ""
expect_remaining "an empty note" '' ""
rm "$note"
[[ -z "$(handoff_remaining "$note")" ]] || fail "a missing note lists remaining work"

# The triage implementer's check of each finding (#552): one line per finding
# under the heading of its triage. The lines do not change what the note lists
# as remaining work.
checks_note='**Done:** C1 fixed.\n**Remaining:** step 3\n\n## Triage feature-7-x-review-01-triage.json\n\n- C1: fixed — tests/a-test.sh: the CRLF case passes\n  Class: input split on LF only; checked scripts/b.sh (does not have it).\n- `M2`: `refuted` -- printf x | ./a.sh exits 0\n- M3: not_reproduced – the command ran and printed nothing wrong\n- S4: not_executable — needs a browser; settled by reading, unverified\n'
expect_remaining "the check lines under a triage heading" "$checks_note" "step 3|"
expect_remaining "the check lines after a list of labels" \
  '- **Remaining:** none\n\n## Triage feature-7-x-review-01-triage.json\n- C1: not_reproduced — ran it\n' ""
# A check line that is put under Remaining is still remaining work: the gate
# never reads a check as completion.
expect_remaining "a check line under Remaining" '**Remaining:**\n- C1: fixed — tests/a-test.sh\n' "C1: fixed — tests/a-test.sh|"

printf '%b' "$checks_note" >"$note"
[[ "$(handoff_finding_checks "$note" | cut -f 2,3 | tr '\t\n' ':|')" == "C1:fixed|M2:refuted|M3:not_reproduced|S4:not_executable|" ]] ||
  fail "the checks were not read: $(handoff_finding_checks "$note")"
[[ "$(handoff_finding_checks "$note" | sed -n 1p)" == "$(printf 'feature-7-x-review-01-triage.json\tC1\tfixed\ttests/a-test.sh: the CRLF case passes')" ]] ||
  fail "a check does not give its triage and its evidence: $(handoff_finding_checks "$note" | sed -n 1p)"
# Not a check: a line outside a triage heading, another value, no evidence,
# a none-word or only delimiters and punctuation for evidence, free text
# under the heading, or a label that is not a finding id.
printf '%b' '- C1: fixed — before any heading\n## Triage feature-7-x-review-01-triage.json\n- C1: resolved — it is fine\n- C2: fixed —\n- C3: fixed — none\n- C8: fixed — — —\n- C9: fixed -- .\n- C4: refuted\nC5: fixed — not a list line\n- Class: fixed — a label\n## Notes\n- C6: fixed — under another heading\n## Triage\n- C7: fixed — a heading without a name\n' >"$note"
[[ -z "$(handoff_finding_checks "$note")" ]] ||
  fail "a line that is not a check was read as one: $(handoff_finding_checks "$note")"

# The outcome per FIX_NOW finding of one triage: only its own section counts,
# and only fixed is resolved.
triage_file="$tmp/feature-7-x-review-02-triage.json"
jq -n '{decisions: [
  {finding_id: "C1", decision: "FIX_NOW"}, {finding_id: "M2", decision: "FIX_NOW"},
  {finding_id: "M3", decision: "FIX_NOW"}, {finding_id: "S4", decision: "FIX_NOW"},
  {finding_id: "M5", decision: "FIX_NOW"}, {finding_id: "M6", decision: "FIX_NOW"},
  {finding_id: "S7", decision: "ACCEPT"}]}' >"$triage_file"
printf '%b' '## Triage feature-7-x-review-01-triage.json\n- C1: fixed — an earlier round\n- M5: fixed — an earlier round\n## Triage `feature-7-x-review-02-triage.json`\n- C1: not_reproduced — ran tests/a-test.sh, it passes\n- M2: refuted — printf x | ./a.sh exits 0\n- M3: not_executable — needs GitHub\n- S4: fixed — tests/s-test.sh\n- M6: fixed — tests/m-test.sh\n- M6: refuted — the claim does not hold\n- S7: fixed — tests/s7-test.sh\n' >"$note"
[[ "$(triage_check_outcomes "$note" "$triage_file" | cut -f 1,2 | tr '\t\n' ':|')" == "C1:not_reproduced|M2:refuted|M3:not_executable|S4:fixed|M5:missing|M6:conflicting|" ]] ||
  fail "the outcomes of the checks are not as recorded: $(triage_check_outcomes "$note" "$triage_file")"
# Duplicate lines: identical ones count once, and the same value with other
# evidence conflicts. A line with delimiter-only evidence is no check, so it
# neither conflicts nor resolves.
printf '%b' '## Triage feature-7-x-review-02-triage.json\n- C1: fixed — tests/a-test.sh\n- C1: fixed — tests/a-test.sh\n- M2: fixed — tests/a-test.sh\n- M2: fixed — tests/b-test.sh\n- M3: fixed — tests/c-test.sh\n- M3: fixed — — —\n' >"$note"
[[ "$(triage_check_outcomes "$note" "$triage_file" | sed -n 1,3p | tr '\t\n' ':|')" == "C1:fixed:tests/a-test.sh|M2:conflicting:fixed, with differing evidence|M3:fixed:tests/c-test.sh|" ]] ||
  fail "duplicate checks are not read as identical or conflicting: $(triage_check_outcomes "$note" "$triage_file")"
rm "$note"
[[ "$(triage_check_outcomes "$note" "$triage_file" | cut -f 2 | sort -u)" == "missing" ]] ||
  fail "without a note, a finding is not missing its check"

# The gate: the outcome on the first line, the reasons after it.
# expect_gate <description> <outcome> [reason-fragment...]
expect_gate() {
  local description="$1"
  local expected="$2"
  local gate

  gate="$(completion_gate "$root" 7)"
  [[ "$(printf '%s\n' "$gate" | sed -n 1p)" == "$expected" ]] ||
    fail "$description: the gate says '$(printf '%s\n' "$gate" | sed -n 1p)' instead of '$expected'"
  shift 2
  for fragment in "$@"; do
    printf '%s\n' "$gate" | sed 1d | grep -F "$fragment" >/dev/null || fail "$description: the reasons lack '$fragment': $gate"
  done
}

rm -f "$record"
expect_gate "no record" missing "the implementer wrote no completion record (.agents/completion/7.json)"
printf 'broken\n' >"$record"
expect_gate "a record that cannot be read" invalid "it is not valid JSON"
printf '%s\n' "$partial" >"$record"
expect_gate "a partial record" partial "not met: The page works without JavaScript" "remaining: Plan steps 4 to 6"
printf '%s\n' "$partial" | sed 's/"partial"/"blocked"/' >"$record"
expect_gate "a blocked record" blocked "remaining: Plan steps 4 to 6"
printf '%s\n' "$complete" >"$record"
expect_gate "a complete record" complete
[[ "$(completion_gate "$root" 7)" == "complete" ]] || fail "a passed gate gives reasons"
# The record of another Issue says nothing about this one.
expect_gate "the record of another Issue" complete
[[ "$(completion_gate "$root" 8 | sed -n 1p)" == "missing" ]] || fail "the record of Issue 7 was used for Issue 8"

# The handoff note outweighs a record that says complete.
printf '**Remaining:** steps 3 to 9.\n' >"$note"
expect_gate "a complete record against a note with remaining work" partial \
  "the completion record says complete, but the handoff note (.agents/handoffs/7.md) lists remaining work" \
  "remaining: steps 3 to 9."
printf 'Issue 7 is complete.\n' >"$note"
expect_gate "a complete record with a note that agrees" complete

# The statement that finish-feature.sh puts in the commit message.
[[ "$(completion_commit_lines "$root" 7)" == "Completion: complete
- met: Recipes can be searched (tests/test_search.py)
- not applicable: Works offline (the Issue dropped it in a comment)" ]] || fail "the completion statement of a complete record is wrong"
printf '%s\n' "$partial" >"$record"
[[ "$(completion_commit_lines "$root" 7)" == "Completion: partial
- met: Recipes can be searched (tests/test_search.py)
- not met: The page works without JavaScript (not started; plan step 4)
- remaining: Plan steps 4 to 6" ]] || fail "the completion statement of a partial record is wrong"

# Closing keywords. GitHub closes an Issue on one of them next to its number,
# so text taken over into a pull request that may not close the Issue is
# rewritten, and a commit that carries one is found.
closes() {
  printf '%s\n' "$1" | grep -Ei "$(completion_closing_pattern 12)" >/dev/null
}
for closing in "Closes #12" "closes #12." "CLOSED #12" "Fix #12" "fixes: #12" "This fixed #12, see below" \
  "resolve #12" "Resolves owner/repo#12" "resolved https://github.com/owner/repo/issues/12" "(closes #12)"; do
  closes "$closing" || fail "a closing keyword was not recognised: $closing"
done
for harmless in "Refs #12" "Closes #123" "Closes #1" "This encloses #12" "prefixes #12" "See #12" "closes the gap in #12" \
  "Closes owner/repo#120"; do
  if closes "$harmless"; then fail "text without a closing keyword for Issue 12 was taken for one: $harmless"; fi
done
[[ "$(printf '%s\n' "Closes #12" "closes: #12." "This fixes #12 and Fixes #123, resolved owner/repo#12; see #12" \
  "Fixed https://github.com/o/r/issues/12" "Refs #12" "This encloses #12" | completion_neutralize_closing 12)" == "Refs #12
Refs #12.
This Refs #12 and Fixes #123, Refs owner/repo#12; see #12
Refs https://github.com/o/r/issues/12
Refs #12
This encloses #12" ]] || fail "closing keywords were not turned into references as expected"
neutralized="$(printf '%s\n' "Closes #12" "Fixes #12 and resolves #12" | completion_neutralize_closing 12)"
if grep -Eiq "$(completion_closing_pattern 12)" <<<"$neutralized"; then
  fail "a closing keyword survived the rewriting"
fi

# The record of ADR 020 decision 2 (completion/v2): a gate per criterion, the
# status pending for a later gate, and the level the implementer records.
v2() {
  # v2 <status> <remaining-json> <criterion-json>...
  local status="$1"
  local remaining="$2"

  shift 2
  jq -n --arg status "$status" --argjson remaining "$remaining" --argjson criteria "[$(IFS=,; printf '%s' "$*")]" '{
    schema: "completion/v2", status: $status,
    risk: {level: 2, triggers: [], rationale: "src/ and tests only"},
    criteria: $criteria, remaining: $remaining
  }'
}
met='{"criterion": "Recipes can be searched", "gate": "implementation", "status": "met", "evidence": "tests/test_search.py"}'
ci='{"criterion": "CI passes on the head", "gate": "pr_ci", "status": "pending", "evidence": "the checks of the pull request"}'
owner='{"criterion": "The owner approves the diff", "gate": "owner_approval", "status": "pending", "evidence": "at the merge gate"}'
later='{"criterion": "Two features ran under it", "gate": "post_merge", "status": "pending", "evidence": "after the merge"}'
open_work='{"criterion": "The page works without JavaScript", "gate": "implementation", "status": "not_met", "evidence": "plan step 4"}'
expect_errors "a complete v2 record" "$(v2 complete '[]' "$met")"
expect_errors "a partial v2 record with criteria pending for each later gate" \
  "$(v2 partial '["the evidence of the later gates"]' "$met" "$ci" "$owner" "$later")"
# complete keeps one meaning: every criterion met.
expect_errors "complete with a pending criterion" "$(v2 complete '[]' "$met" "$later")" \
  "status is complete, but a criterion is pending; complete means every criterion is met"
expect_errors "pending for the gate implementation" \
  "$(v2 partial '["the tests"]' '{"criterion": "Tests exist", "gate": "implementation", "status": "pending", "evidence": "later"}')" \
  "criterion 1: pending is never allowed for the gate implementation"
expect_errors "a v2 criterion without a gate" \
  "$(v2 complete '[]' '{"criterion": "It works", "status": "met", "evidence": "a test"}')" \
  "criterion 1: gate must be implementation, pr_ci, owner_approval, or post_merge"
expect_errors "a v2 record without a risk" \
  "$(v2 complete '[]' "$met" | jq 'del(.risk)')" "risk must hold the level, the triggers, and the rationale"
expect_errors "a v2 record with an unknown level and no rationale" \
  "$(v2 complete '[]' "$met" | jq '.risk = {level: 0, triggers: "none", rationale: ""}')" \
  "risk.level must be 1, 2, or 3" "risk.triggers must be a list of texts; an empty list when none applies" "risk needs a rationale"
# The earlier contract knows neither the gates nor pending.
expect_errors "pending in a v1 record" \
  '{"schema": "completion/v1", "status": "partial", "criteria": [{"criterion": "CI", "status": "pending", "evidence": "x"}], "remaining": ["CI"]}' \
  "criterion 1: status must be met, not_met, or not_applicable"
expect_errors "a gate in a v1 record" \
  '{"schema": "completion/v1", "status": "complete", "criteria": [{"criterion": "CI", "gate": "pr_ci", "status": "met", "evidence": "x"}], "remaining": []}' \
  "criterion 1: a gate needs the schema completion/v2"

# The readiness points are derived. Only pending criteria left: ready for a
# pull request ('pending', with the criteria and their gates), and still not
# complete.
rm -f "$note"
v2 partial '["the evidence of the later gates"]' "$met" "$ci" "$later" >"$record"
expect_gate "only pending criteria" pending "pending (pr_ci): CI passes on the head" \
  "pending (post_merge): Two features ran under it"
[[ "$(completion_gate "$root" 7 | sed -n 1p)" != "complete" ]] || fail "a record with a pending criterion counts as complete"
[[ "$(completion_commit_lines "$root" 7)" == "Completion: partial
- met: Recipes can be searched (tests/test_search.py)
- pending (pr_ci): CI passes on the head (the checks of the pull request)
- pending (post_merge): Two features ran under it (after the merge)
- remaining: the evidence of the later gates" ]] || fail "the completion statement of a record with pending criteria is wrong"
# Pending evidence is listed under its own label in the handoff note.
printf '**Done:** all.\n**Remaining:** none.\n**Pending:** CI on the head; two features after the merge.\n' >"$note"
expect_gate "only pending criteria, and a note that lists them as pending" pending
printf '**Remaining:** the documentation.\n' >"$note"
expect_gate "only pending criteria, but the note lists remaining work" partial
rm -f "$note"
v2 partial '["plan step 4"]' "$met" "$ci" "$open_work" >"$record"
expect_gate "a pending criterion beside one that is not met" partial "not met: The page works without JavaScript" \
  "pending (pr_ci): CI passes on the head"
v2 blocked '["the owner decides"]' "$met" "$owner" >"$record"
expect_gate "a blocked record with a pending criterion" blocked
v2 complete '[]' "$met" >"$record"
expect_gate "a complete v2 record" complete

# The summary of the changes, which an unattended commit needs.
if completion_summary_present "$root" 7; then fail "a missing summary counts as present"; fi
printf 'Some text without a list.\n' >"$root/.agents/summaries/7.md"
if completion_summary_present "$root" 7; then fail "a summary without a list line counts as present"; fi
printf -- '- Adds the search.\n' >"$root/.agents/summaries/7.md"
completion_summary_present "$root" 7 || fail "a summary with a list line does not count"

echo "completion tests passed"
