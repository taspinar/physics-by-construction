#!/usr/bin/env bash

set -euo pipefail

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/revise-planning-test.XXXXXX")"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  echo "revise-planning test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
make_fake_agents "$tmp/bin"

review=".agents/reviews/planning-project-bootstrap-review-01.json"
revision=".agents/reviews/planning-project-bootstrap-review-01-revision"
valid_decisions='{"decisions": [
  {"finding_id": "M1", "decision": "ADOPT", "rationale": "Offline use is an MVP requirement."},
  {"finding_id": "MIN1", "decision": "REJECT", "rationale": "The name follows the requirements."},
  {"finding_id": "S1", "decision": "ESCALATE", "rationale": "Sharing scope is a product decision."}
]}'
export MOCK_OUTPUT="$valid_decisions"

# Creates a planning repository with a current planning review of round 1.
setup_repo() {
  local repo="$tmp/$1"

  mkdir -p "$repo/docs/decisions" "$repo/.agents/reviews"
  copy_workflow "$repo"
  printf 'project-planner: claude model-p\n' >"$repo/.agents/agents.conf"
  printf '# Agents\n' >"$repo/AGENTS.md"
  printf '# Project Requirements\n\nStatus: Approved\nApproved at: 2026-01-01T00:00:00Z\n\n## MVP scope\n\nOffline recipes.\n' \
    >"$repo/docs/PROJECT_REQUIREMENTS.md"
  printf '# Architecture\n\nLocal storage.\n' >"$repo/docs/architecture.md"
  printf '# Roadmap\n\n## F01 — Recipes\n\n- Goal: list recipes.\n' >"$repo/docs/roadmap.md"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.name "Revise Test"
  git -C "$repo" config user.email "revise-test@example.com"
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" switch -q -c planning/project-bootstrap

  jq -n '{
    schema: "review/v1", kind: "planning", issue: null, round: 1,
    branch: "planning/project-bootstrap", base: "origin/main", merge_base: "aaaa", head: "bbbb",
    reviewed_tree: "", reviewed_paths: ["docs/PROJECT_DESCRIPTION.md", "docs/changes", "docs/PROJECT_REQUIREMENTS.md", "docs/architecture.md", "docs/roadmap.md", "docs/decisions"],
    reviewer: {agent: "codex", model: "model-r"}, created_at: "2026-01-01T00:00:00Z",
    verdict: "CHANGES_REQUIRED", limitations: "",
    findings: [
      {id: "M1", severity: "major", title: "Offline use is unplanned", evidence: "docs/roadmap.md", impact: "An MVP requirement is missing.", recommendation: "Add a feature for offline use."},
      {id: "MIN1", severity: "minor", title: "Feature name is vague", evidence: "docs/roadmap.md, F01", impact: "Readability.", recommendation: "Rename F01."},
      {id: "S1", severity: "suggestion", title: "Consider sharing", evidence: "docs/roadmap.md", impact: "Households share recipes.", recommendation: "Add sharing."}
    ]
  }' >"$repo/$review"
  record_reviewed_tree "$repo" "$repo/$review"

  printf '%s\n' "$repo"
}

run_revise() {
  local repo="$1"
  local answer="$2"
  shift 2

  (
    cd "$repo"
    printf '%s\n' "$answer" |
      PATH="$tmp/bin:/usr/bin:/bin" MOCK_AGENT_LOG="$repo.log" ./scripts/revise-planning.sh "$@"
  ) >"$repo.out" 2>&1
}

# An interactive write session runs in the 'auto' permission mode and without
# --print (Issue #512; before, it ran in 'acceptEdits').
write_sessions() {
  grep -- "--permission-mode auto" "$1.log" 2>/dev/null | grep -vc -- "--print" || true
}

unattended_sessions() {
  grep -- "--permission-mode auto" "$1.log" 2>/dev/null | grep -c -- "--print" || true
}

add_offline_feature="printf '\\n## F02 — Offline use\\n\\n- Goal: work offline.\\n' >>docs/roadmap.md"

# The planner decides read-only; after approval the decisions are recorded and
# a write session revises exactly the adopted findings.
repo="$(setup_repo revise)"
MOCK_WRITE_ACTION="$add_offline_feature" run_revise "$repo" y --review "$review" || {
  cat "$repo.out" >&2
  fail "revising the planning failed"
}
[[ -f "$repo/$revision.json" && -f "$repo/$revision.md" ]] || fail "the revision and its report were not recorded"
[[ "$(jq -c '[.schema, .review_round, (.decisions | map(.decision))]' "$repo/$revision.json")" == \
  '["revision/v1",1,["ADOPT","REJECT","ESCALATE"]]' ]] || fail "the recorded decisions are wrong"
grep -Fq -- "--tools Read,Glob,Grep" "$repo.log" || fail "the planner did not decide read-only"
grep -Fq -- "--json-schema" "$repo.log" || fail "the planner was not given the revision schema"
[[ "$(write_sessions "$repo")" -eq 1 ]] || fail "exactly one write session was expected"
grep -Fq "M1. Offline use is unplanned" "$repo.log" || fail "the adopted finding was not passed to the planner"
if grep -Fq "Feature name is vague" "$repo.log" || grep -Fq "Consider sharing" "$repo.log"; then
  fail "a finding that was not adopted was passed to the write session"
fi
grep -Fq "F02 — Offline use" "$repo/docs/roadmap.md" || fail "the revision did not reach the roadmap"
grep -Fq "Escalated findings need your decision" "$repo.out" || fail "the escalated finding was not reported"
status=0
(cd "$repo" && ./scripts/check-review.sh "$review" >/dev/null) || status=$?
[[ "$status" -eq 1 ]] || fail "the planning review is not stale after the revision"

# A revised review cannot be revised again; the next step is a new review.
if run_revise "$repo" y --review "$review"; then
  fail "an already revised review was revised again"
fi
grep -Fq "review-planning.sh" "$repo.out" || fail "the next review round was not suggested"

# --unattended (Issue #512): the planner decides and revises without a
# terminal; the record says that no human approved the decisions. Nothing is
# read from standard input.
no_escalation="$(jq '.decisions[2].decision = "REJECT"' <<<"$valid_decisions")"
run_unattended() {
  local repo="$1"
  shift
  (
    cd "$repo"
    PATH="$tmp/bin:/usr/bin:/bin" MOCK_AGENT_LOG="$repo.log" ./scripts/revise-planning.sh "$@" </dev/null
  ) >"$repo.out" 2>&1
}
repo="$(setup_repo unattended)"
MOCK_OUTPUT_FIRST="$no_escalation" MOCK_OUTPUT="Revised M1." MOCK_WRITE_ACTION="$add_offline_feature" \
  run_unattended "$repo" --review "$review" --unattended || {
  cat "$repo.out" >&2
  fail "an unattended revision failed"
}
[[ "$(jq -r '.unattended' "$repo/$revision.json")" == "true" ]] || fail "the unattended revision does not say so"
grep -Fq "by an unattended run; no human approved these decisions" "$repo/$revision.md" ||
  fail "the report of the unattended revision does not say that no human approved it"
[[ "$(unattended_sessions "$repo")" -eq 1 && "$(write_sessions "$repo")" -eq 0 ]] ||
  fail "the adopted findings were not revised in exactly one unattended session"
grep -Fq "This session is unattended" "$repo.log" || fail "the planner was not told that the session is unattended"
grep -Fq "F02 — Offline use" "$repo/docs/roadmap.md" || fail "the unattended revision did not reach the roadmap"
grep -Fq "review-planning.sh" "$repo.out" || fail "the next review round was not named"

# It stops with a clear message, before any revision, when a finding is
# escalated; the decisions are recorded for the owner.
repo="$(setup_repo unattended-escalated)"
status=0
MOCK_OUTPUT_FIRST="$valid_decisions" MOCK_OUTPUT="Revised." MOCK_WRITE_ACTION="$add_offline_feature" \
  run_unattended "$repo" --review "$review" --unattended || status=$?
[[ "$status" -eq 3 ]] || { cat "$repo.out" >&2; fail "an unattended revision with an escalated finding did not stop (status $status)"; }
grep -Fq "Stopped: an unattended revision does not go on while a finding is escalated" "$repo.out" ||
  fail "the stop on an escalation gave no clear message"
grep -Fq -- "- S1 Consider sharing" "$repo.out" || fail "the escalated finding was not named"
[[ "$(unattended_sessions "$repo")" -eq 0 && "$(write_sessions "$repo")" -eq 0 ]] || fail "a write session started despite the escalation"
[[ -f "$repo/$revision.json" ]] || fail "the decisions were not recorded for the owner"
if grep -Fq "F02" "$repo/docs/roadmap.md"; then fail "the planning was revised despite the escalation"; fi

# A planner that reports that it is blocked stops the run.
repo="$(setup_repo unattended-blocked)"
status=0
MOCK_OUTPUT_FIRST="$no_escalation" MOCK_OUTPUT=$'Could not.\nBLOCKED: the owner has to choose the storage.' \
  MOCK_WRITE_ACTION="$add_offline_feature" run_unattended "$repo" --review "$review" --unattended || status=$?
[[ "$status" -eq 3 ]] || fail "a blocked unattended planner did not stop the run (status $status)"
grep -Fq "the unattended planner stopped: the owner has to choose the storage." "$repo.out" || fail "the blocked reason was not reported"

# The interactive mode stays the default: without the flag the decisions are
# asked for.
repo="$(setup_repo interactive-default)"
run_revise "$repo" n --review "$review" || fail "declining the decisions failed"
grep -Fq "Record these decisions and revise the planning" "$repo.out" || fail "the interactive mode did not ask"
[[ ! -e "$repo/$revision.json" ]] || fail "the interactive mode recorded decisions without approval"

# The reviser may add a dated note of an owner decision to the requirements
# (Issue #512), and nothing else there.
note_line="*Note of the owner's decision of 2026-11-13 (https://github.com/owner/repo/issues/511#issuecomment-42).* Offline only."
repo="$(setup_repo note)"
MOCK_WRITE_ACTION="$add_offline_feature; printf '\\n%s\\n' \"$note_line\" >>docs/PROJECT_REQUIREMENTS.md" \
  run_revise "$repo" y --review "$review" || {
  cat "$repo.out" >&2
  fail "a note of an owner decision in the requirements was refused"
}
grep -Fq "$note_line" "$repo/docs/PROJECT_REQUIREMENTS.md" || fail "the note did not reach the requirements"
grep -Fq "added notes of owner decisions" "$repo.out" || fail "the added note was not reported"

repo="$(setup_repo note-and-requirement)"
if MOCK_WRITE_ACTION="$add_offline_feature; sed -i.bak 's/^Offline recipes.\$/Online recipes./' docs/PROJECT_REQUIREMENTS.md; rm docs/PROJECT_REQUIREMENTS.md.bak" \
  run_revise "$repo" y --review "$review"; then
  fail "a changed requirement was accepted from the reviser"
fi
grep -Fq "existing text is changed or removed" "$repo.out" || fail "the changed requirement was not named"
grep -Fq "only Project Grill changes a requirement" "$repo.out" || fail "the refusal did not name the route"

# A review with only suggestions needs no revision round.
repo="$(setup_repo only-suggestions)"
jq '.verdict = "PASS_WITH_MINOR_FINDINGS" | .findings = [.findings[2]]' "$repo/$review" >"$repo/$review.tmp"
mv "$repo/$review.tmp" "$repo/$review"
record_reviewed_tree "$repo" "$repo/$review"
run_revise "$repo" y --review "$review" || fail "a review with only suggestions was not accepted"
grep -Fq "only suggestions; they need no revision round" "$repo.out" || fail "the suggestions-only review gave no reason"
[[ ! -e "$repo.log" ]] || fail "an agent started for a review with only suggestions"

# Declining records nothing and changes nothing.
repo="$(setup_repo decline)"
run_revise "$repo" n --review "$review" || fail "declining returned an error"
[[ ! -e "$repo/$revision.json" ]] || fail "declined decisions were recorded"
[[ "$(write_sessions "$repo")" -eq 0 ]] || fail "a write session started after declining"

# Invalid decisions are retried once and then rejected before anything is recorded.
# One invalid result per rule, each derived from the valid decisions.
for invalid in \
  "not json" \
  '{"decisions": {}}' \
  "$(jq '.decisions[0].decision = "REJECT"' <<<"$valid_decisions")" \
  "$(jq '.decisions[0].decision = "DEFER"' <<<"$valid_decisions")" \
  "$(jq 'del(.decisions[2])' <<<"$valid_decisions")" \
  "$(jq '.decisions += [.decisions[1]]' <<<"$valid_decisions")" \
  "$(jq '.decisions[1].finding_id = "MIN9"' <<<"$valid_decisions")" \
  "$(jq '.decisions[1].decision = "LATER"' <<<"$valid_decisions")" \
  "$(jq '.decisions[1].rationale = ""' <<<"$valid_decisions")" \
  "$(jq '.decisions[1].severity = "minor"' <<<"$valid_decisions")"; do
  repo="$(setup_repo "invalid-$(grep -c . "$tmp/invalid-count" 2>/dev/null || true)")"
  echo x >>"$tmp/invalid-count"
  if MOCK_OUTPUT="$invalid" run_revise "$repo" y --review "$review"; then
    fail "invalid revision decisions were accepted"
  fi
  [[ ! -e "$repo/$revision.json" ]] || fail "invalid decisions were recorded"
  [[ "$(grep -c '^AGENT=' "$repo.log")" -eq 2 ]] || fail "invalid decisions were not retried exactly once"
done

# The write session may change only the architecture, roadmap, and ADRs.
for action in \
  "printf 'changed\\n' >>docs/PROJECT_REQUIREMENTS.md" \
  "printf 'changed\\n' >>AGENTS.md" \
  "printf 'x\\n' >.env" \
  "printf 'x\\n' >>$revision.json" \
  "printf 'x\\n' >docs/decisions/tool.sh" \
  "git add -A && git commit -qm 'Agent must not commit'"; do
  repo="$(setup_repo "scope-$(grep -c . "$tmp/scope-count" 2>/dev/null || true)")"
  echo x >>"$tmp/scope-count"
  if MOCK_WRITE_ACTION="$add_offline_feature; $action" run_revise "$repo" y --review "$review"; then
    fail "an out-of-scope change was accepted: $action"
  fi
  grep -Fq "preserved" "$repo.out" || fail "a scope violation did not preserve the worktree: $action"
done

# A minor finding may be deferred.
repo="$(setup_repo defer)"
MOCK_OUTPUT="$(jq '.decisions[1].decision = "DEFER"' <<<"$valid_decisions")" \
  MOCK_WRITE_ACTION="$add_offline_feature" run_revise "$repo" y --review "$review" || {
  cat "$repo.out" >&2
  fail "deferring a minor finding was rejected"
}

# A write session that changes nothing does not count as a revision; the
# approved decisions stay for a retry.
repo="$(setup_repo no-op)"
if run_revise "$repo" y --review "$review"; then
  fail "a write session without changes was reported as a revision"
fi
grep -Fq "changed no planning document" "$repo.out" || fail "an empty revision was not reported"
[[ -f "$repo/$revision.json" ]] || fail "the approved decisions were lost after an empty revision"

# A failed write session keeps the approved decisions; while the review is
# still current, a re-run applies them without deciding again.
repo="$(setup_repo resume)"
if MOCK_WRITE_EXIT=5 run_revise "$repo" y --review "$review"; then
  fail "a failed planner returned success"
fi
[[ -f "$repo/$revision.json" ]] || fail "the approved decisions were lost after a failed write session"
rm "$repo.log"
MOCK_WRITE_ACTION="$add_offline_feature" run_revise "$repo" y --review "$review" || {
  cat "$repo.out" >&2
  fail "resuming the revision failed"
}
[[ "$(grep -c '^AGENT=' "$repo.log")" -eq 1 ]] || fail "resuming decided again instead of applying the recorded decisions"

# Without adopted findings no document is changed.
repo="$(setup_repo nothing-adopted)"
MOCK_OUTPUT="$(jq '.decisions[0].decision = "ESCALATE"' <<<"$valid_decisions")" run_revise "$repo" y --review "$review" || {
  cat "$repo.out" >&2
  fail "a revision without adopted findings failed"
}
[[ "$(write_sessions "$repo")" -eq 0 ]] || fail "a write session started without adopted findings"

# A stale review is refused even when it has no findings.
repo="$(setup_repo stale-empty)"
jq '.verdict = "PASS" | .findings = []' "$repo/$review" >"$repo/$review.tmp"
mv "$repo/$review.tmp" "$repo/$review"
printf '\nChanged.\n' >>"$repo/docs/roadmap.md"
if run_revise "$repo" y --review "$review"; then
  fail "a stale review without findings was accepted"
fi

# Stale, foreign, and misplaced reviews fail before an agent starts.
repo="$(setup_repo stale)"
printf '\nChanged.\n' >>"$repo/docs/architecture.md"
if run_revise "$repo" y --review "$review"; then
  fail "a stale planning review was revised"
fi
[[ ! -e "$repo.log" ]] || fail "an agent started for a stale review"

repo="$(setup_repo feature-review)"
jq '.kind = "feature" | .issue = 3 | .reviewed_paths = null' "$repo/$review" >"$repo/$review.tmp"
mv "$repo/$review.tmp" "$repo/$review"
if run_revise "$repo" y --review "$review"; then
  fail "a feature review was revised as planning"
fi

repo="$(setup_repo not-planning)"
git -C "$repo" switch -q -c feature/1-x
if run_revise "$repo" y --review "$review"; then
  fail "revision ran outside a planning worktree"
fi
[[ ! -e "$repo.log" ]] || fail "an agent started despite failed preconditions"

# The scope snapshot covers the files Git tracks or would track, and ignored
# files outside an ignored directory (here a review artifact), but does not
# walk an ignored directory such as the .venv of a planning worktree (Issue
# #353). Its cost is measured by the number of file-hash calls, not by the
# wall clock.
scope_repo="$tmp/scope-snapshot"
mkdir -p "$scope_repo/docs" "$scope_repo/.agents/reviews"
printf '.venv/\n.pytest_cache/\n.agents/reviews/*\n' >"$scope_repo/.gitignore"
printf '# Architecture\n' >"$scope_repo/docs/architecture.md"
printf 'Readme.\n' >"$scope_repo/README.md"
printf 'Removed later.\n' >"$scope_repo/removed.txt"
git -C "$scope_repo" init -q -b planning/project-bootstrap
git -C "$scope_repo" add .
git -C "$scope_repo" -c user.name=Test -c user.email=test@example.com commit -qm "Seed"
printf 'Untracked, not ignored.\n' >"$scope_repo/draft.txt"
printf '{}\n' >"$scope_repo/.agents/reviews/review-01.json"
mkdir -p "$scope_repo/.venv/lib"
for index in $(seq 1 200); do
  printf '%s\n' "$index" >"$scope_repo/.venv/lib/module-$index.py"
done

# scope_snapshot_counted <target>
# Takes a snapshot and prints the number of file-hash calls it made.
scope_snapshot_counted() {
  (
    source "$source_root/scripts/lib/scope.sh" || exit 1
    counter="$tmp/scope-hash-calls"
    : >"$counter"
    git() {
      if [[ "${1:-}" == "hash-object" && "${2:-}" != "--stdin" ]]; then
        echo x >>"$counter"
      fi
      command git "$@"
    }
    scope_snapshot "$scope_repo" scope_planner_allowed "$1"
    grep -c . "$counter" || true
  )
}

# scope_check <description> <expected: same|changed>
# Compares a fresh snapshot with the baseline.
scope_check() {
  scope_snapshot_counted "$tmp/scope-after.tsv" >/dev/null
  if (source "$source_root/scripts/lib/scope.sh" &&
    scope_unchanged "$tmp/scope-before.tsv" "$tmp/scope-after.tsv" 2>/dev/null); then
    [[ "$2" == same ]] || fail "the scope check accepted $1"
  else
    [[ "$2" == changed ]] || fail "the scope check reported $1"
  fi
}

hash_calls="$(scope_snapshot_counted "$tmp/scope-before.tsv")"
# .gitignore, README.md, removed.txt, draft.txt, and the review artifact; the
# architecture is an allowed path.
[[ "$hash_calls" -eq 5 ]] ||
  fail "the scope snapshot hashed $hash_calls files instead of 5; it walks ignored files"
if grep -Fq ".venv" "$tmp/scope-before.tsv"; then
  fail "the scope snapshot lists the files of an ignored directory"
fi
snapshot_paths="$(cut -f2 "$tmp/scope-before.tsv")"
for path in README.md draft.txt .agents/reviews/review-01.json; do
  grep -Fqx "$path" <<<"$snapshot_paths" || fail "the scope snapshot does not list $path"
done

printf 'Changed by the planner.\n' >>"$scope_repo/docs/architecture.md"
scope_check "a change of an allowed document" same
mkdir -p "$scope_repo/.pytest_cache/v/cache"
printf '[]\n' >"$scope_repo/.pytest_cache/v/cache/lastfailed"
printf 'changed\n' >>"$scope_repo/.venv/lib/module-1.py"
scope_check "a new or changed ignored file (.pytest_cache, .venv)" same

cp "$scope_repo/README.md" "$tmp/README.md"
printf 'Changed by the planner.\n' >>"$scope_repo/README.md"
scope_check "a changed tracked file outside the allowed paths" changed
cp "$tmp/README.md" "$scope_repo/README.md"
scope_check "a restored tracked file" same

printf 'New.\n' >"$scope_repo/notes.txt"
scope_check "a new untracked, not ignored file outside the allowed paths" changed
rm "$scope_repo/notes.txt"

rm "$scope_repo/removed.txt"
scope_check "a deleted tracked file" changed
git -C "$scope_repo" checkout -q -- removed.txt

printf ' ' >>"$scope_repo/.agents/reviews/review-01.json"
scope_check "a changed review artifact, although it is ignored" changed

echo "revise-planning tests passed"
