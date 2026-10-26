#!/usr/bin/env bash

set -euo pipefail

# ADR 020 decision 4 in the scripts of a feature: stable finding identifiers
# and the disposition of every earlier open finding; the chain of reviews
# that finish-feature.sh accepts for Level 2 and its refusals, one per
# condition; the bounded-impact rule that allows a review of changes, with a
# test per reason that requires a review of the complete feature and none
# for the size of the delta; the completion record and the handoff note in
# the review fingerprint; Level 1 without a review and Level 3 with a review
# of the complete feature in every round; and mechanical triage of minor and
# suggestion findings at Levels 1 and 2, never of a critical or major one or
# at Level 3.

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/review-chain-test.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

fail() {
  echo "review chain test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"
make_fake_agents "$tmp/bin"

# A fake GitHub CLI for the review, the triage, and its publication.
cat >"$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$MOCK_GH_LOG"
case "${1:-} ${2:-}" in
  "auth status") exit 0 ;;
  "issue view") printf 'Title: F99 — Test feature\n\nThe speed must be right.\n' ;;
  "issue comment" | "issue list") ;;
  "issue create") echo "https://github.com/example/project/issues/321" ;;
  *) echo "Unexpected gh invocation: $*" >&2; exit 97 ;;
esac
GH
chmod +x "$tmp/bin/gh"

# setup_repo <label> [<level>]: a clone with the real gate configuration and
# ignore rules, with a small package and a lesson that imports it, on
# feature/12-speed with a committed change that a review of the complete
# feature covers: two modules, the lesson, and a test. The completion record
# states the level (completion/v2, default 2).
setup_repo() {
  local repo="$tmp/$1"
  local remote="$tmp/$1-remote.git"

  git init -q --bare -b main "$remote"
  git clone -q "$remote" "$repo" 2>/dev/null
  mkdir -p "$repo/.agents/policies" "$repo/.agents/reviews" "$repo/.agents/triage" "$repo/src/pbc/waves" \
    "$repo/site/lessons/waves" "$repo/tests" "$repo/docs"
  copy_workflow "$repo"
  rm -f "$repo/scripts/verify-workflow.conf"
  cp "$source_root/.gitignore" "$repo/.gitignore"
  cp "$source_root/.agents/policies/guardrails.conf" "$repo/.agents/policies/guardrails.conf"
  printf 'reviewer: claude model-r\ntriage: claude model-t\n' >"$repo/.agents/agents.conf"
  printf 'count: echo run >>verify-count.log\n' >"$repo/scripts/verify.conf"
  printf '' >"$repo/src/pbc/__init__.py"
  printf '' >"$repo/src/pbc/waves/__init__.py"
  printf 'def speed(v):\n    return v\n' >"$repo/src/pbc/waves/speed.py"
  printf 'from pbc.waves.speed import speed\n\n\ndef double(v):\n    return 2 * speed(v)\n' >"$repo/src/pbc/waves/double.py"
  printf 'def third(v):\n    return v / 3\n' >"$repo/src/pbc/waves/third.py"
  printf 'from pbc.waves import third\n\n\ndef ninth(v):\n    return third.third(third.third(v))\n' >"$repo/src/pbc/waves/ninth.py"
  printf -- '---\ntitle: Waves\n---\n\n```{python}\nfrom pbc.waves.speed import speed\nspeed(1)\n```\n' >"$repo/site/lessons/waves/index.qmd"
  printf 'p { color: black; }\n' >"$repo/site/styles.css"
  printf 'from pbc.waves.speed import speed\n\n\ndef test_speed():\n    assert speed(1) == 1\n' >"$repo/tests/test_speed.py"
  printf '# Guide\n' >"$repo/docs/guide.md"
  printf 'id,value\n1,2\n' >"$repo/table.csv"
  git -C "$repo" config user.name "Review Chain Test"
  git -C "$repo" config user.email "review-chain-test@example.com"
  git -C "$repo" checkout -q -b main
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" push -q origin main
  git -C "$repo" checkout -q -b feature/12-speed
  printf 'def speed(v):\n    # the speed of the wave\n    return v\n' >"$repo/src/pbc/waves/speed.py"
  printf 'from pbc.waves.speed import speed\n\n\ndef double(v):\n    return speed(v) * 2\n' >"$repo/src/pbc/waves/double.py"
  printf '\nThe speed of a wave.\n' >>"$repo/site/lessons/waves/index.qmd"
  printf '\n\ndef test_double():\n    assert True\n' >>"$repo/tests/test_speed.py"
  git -C "$repo" add .
  git -C "$repo" commit -qm "The feature"
  mkdir -p "$repo/.agents/summaries"
  printf -- '- Explains the speed.\n' >"$repo/.agents/summaries/12.md"
  record "$repo" "${2:-2}"
  printf '%s\n' "$repo"
}

# record <repo> <level>: a complete completion/v2 record.
record() {
  mkdir -p "$1/.agents/completion"
  jq -n --argjson level "$2" '{
    schema: "completion/v2", status: "complete",
    risk: {level: $level, triggers: [], rationale: "as derived"},
    criteria: [{criterion: "The speed is right", gate: "implementation", status: "met", evidence: "tests/test_speed.py"}],
    remaining: []
  }' >"$1/.agents/completion/12.json"
}

# lib <repo> <command>...: runs a command with the libraries of the chain.
lib() {
  local repo="$1"

  shift
  (
    cd "$repo"
    for library in review-data fingerprint guardrails completion risk review-chain; do
      source "scripts/lib/$library.sh"
    done
    "$@"
  )
}

# content_tree <repo>: the fingerprint a review of Issue #12 records.
content_tree() {
  lib "$1" content_tree_here
}
content_tree_here() {
  local scratch

  scratch="$(mktemp -d "${TMPDIR:-/tmp}/content-tree.XXXXXX")"
  fingerprint_with_records . "$scratch" .agents/completion/12.json .agents/handoffs/12.md
  rm -rf "$scratch"
}

# review <repo> <round> <scope-json> <findings-json> <dispositions-json> [<tree>]
# Writes a feature review of Issue #12 at Level 2 with the record paths. The
# tree defaults to the current content.
review() {
  local repo="$1"
  local file

  file="$repo/.agents/reviews/feature-12-speed-review-$(printf '%02d' "$2").json"
  jq -n --argjson round "$2" --argjson scope "$3" --argjson findings "$4" --argjson dispositions "$5" \
    --arg merge_base "$(git -C "$repo" rev-parse main)" --arg base_tree "$(git -C "$repo" rev-parse 'main^{tree}')" '{
    schema: "review/v1", kind: "feature", issue: 12, round: $round,
    branch: "feature/12-speed", base: "main", merge_base: $merge_base, head: "bbbb",
    compared_tree: (if $scope.kind == "changes" then $scope.base_tree else $base_tree end),
    reviewed_tree: "", reviewed_paths: null,
    record_paths: [".agents/completion/12.json", ".agents/handoffs/12.md"],
    scope: $scope, dispositions: $dispositions,
    verification: {status: "passed", verified_at: "2026-01-01T00:00:00Z", tier: "targeted"},
    risk: {required: 2, by: "paths", path_minimum: 2, record_schema: "completion/v2"},
    reviewer: {agent: "claude", model: "model-r"}, created_at: "2026-01-01T00:00:00Z",
    architecture_impact: {level: "minor", rationale: "Within the architecture.", checked_against: []},
    verdict: (if ($findings | length) == 0 then "PASS"
              elif ([$findings[] | select(.severity == "critical" or .severity == "major")] | length) > 0 then "CHANGES_REQUIRED"
              else "PASS_WITH_MINOR_FINDINGS" end),
    limitations: "", findings: $findings
  }' >"$file"
  if [[ -n "${6:-}" ]]; then
    jq --arg tree "$6" '.reviewed_tree = $tree' "$file" >"$file.tmp" && mv "$file.tmp" "$file"
  else
    record_reviewed_tree "$repo" "$file"
  fi
  printf '%s\n' "$file"
}

finding() {
  jq -n --arg id "$1" --arg severity "$2" --arg evidence "${3:-src/pbc/waves/speed.py:2}" '{id: $id, severity: $severity,
    title: "The speed is not checked", evidence: $evidence, impact: "A wrong speed passes.", recommendation: "Check it."}'
}

# triage <repo> <review> <decision>...: an approved, published triage that
# decides the findings in their order.
triage() {
  local repo="$1"
  local review="$2"
  local file

  shift 2
  file="$repo/.agents/triage/$(basename "$review" .json)-triage.json"
  jq --arg source ".agents/reviews/$(basename "$review")" '{
    schema: "triage/v1", source_review: $source, issue, reviewed_tree, review_verdict: .verdict,
    triage: {agent: "claude", model: "model-t"}, approved_at: "2026-01-02T00:00:00Z", published_at: "2026-01-02T00:00:00Z",
    decisions: [.findings | to_entries[] | .value as $f | {finding_id: $f.id, severity: $f.severity, title: $f.title,
      decision: $ARGS.positional[.key], rationale: "As triaged.",
      followup: (if $ARGS.positional[.key] == "DEFER" then {title: "Later", recommended_action: "Later.",
        acceptance_criteria: ["Done."], issue_number: 321, issue_url: "https://github.com/example/project/issues/321"} else null end)}]
  }' "$review" --args "$@" >"$file"
}

run_script() {
  local repo="$1"

  shift
  status=0
  : >"$repo.gh.log"
  rm -f "$repo.agent.log"
  (cd "$repo" && PATH="$tmp/bin:/usr/bin:/bin" GIT_EDITOR=true MOCK_GH_LOG="$repo.gh.log" MOCK_AGENT_LOG="$repo.agent.log" \
    "$@") >"$repo.out" 2>&1 || status=$?
}

finish() {
  run_script "$1" ./scripts/finish-feature.sh 12 "Explain the speed" --unattended
}

expect_commit() {
  [[ "$status" -eq 0 ]] || { cat "$1.out" >&2; fail "$2: finish-feature.sh failed"; }
  [[ "$(git -C "$1" rev-list --count main..HEAD)" -eq 2 ]] || fail "$2: no commit was created"
}

expect_no_commit() {
  local repo="$1"
  local description="$2"

  shift 2
  [[ "$status" -ne 0 ]] || { cat "$repo.out" >&2; fail "$description: finish-feature.sh committed"; }
  [[ "$(git -C "$repo" rev-list --count main..HEAD)" -eq 1 ]] || fail "$description: a commit was created"
  for fragment in "$@"; do
    grep -Fq -- "$fragment" "$repo.out" || { cat "$repo.out" >&2; fail "$description: the output lacks '$fragment'"; }
  done
}

# chain_repo <label>: a Level 2 feature with round 1, a review of the
# complete feature with a major finding that its triage fixes, a fix in the
# test, and round 2, a review of the changes since round 1 that gives the
# finding as resolved. Sets REPO to the repository and FIRST and SECOND to
# the reviews.
chain_repo() {
  local repo

  repo="$(setup_repo "$1")"
  FIRST="$(review "$repo" 1 '{"kind": "full"}' "[$(finding M1 major)]" '[]')"
  triage "$repo" "$FIRST" FIX_NOW
  printf '\n\ndef test_speed_two():\n    assert speed(2) == 2\n' >>"$repo/tests/test_speed.py"
  SECOND="$(review "$repo" 2 "$(jq -n --arg tree "$(jq -r '.reviewed_tree' "$FIRST")" '{kind: "changes", since_round: 1, base_tree: $tree}')" \
    '[]' '[{"finding_id": "R01-M1", "status": "resolved", "evidence": "tests/test_speed.py:9 checks it"}]')"
  REPO="$repo"
}

# --- Criterion 1: stable identifiers and the disposition of earlier findings.
repo="$(setup_repo identifiers)"
first="$(review "$repo" 1 '{"kind": "full"}' "[$(finding M1 major), $(finding MIN1 minor), $(finding S1 suggestion)]" '[]')"
open="$(lib "$repo" review_chain_open . feature-12-speed 2 | jq -c 'map(.id)')"
[[ "$open" == '["R01-M1","R01-MIN1","R01-S1"]' ]] || fail "the untriaged findings of round 1 are not open by their stable identifiers: $open"
triage "$repo" "$first" FIX_NOW DEFER ACCEPT
open="$(lib "$repo" review_chain_open . feature-12-speed 2 | jq -c 'map(.id)')"
[[ "$open" == '["R01-M1"]' ]] || fail "a deferred or accepted finding stayed open, or the finding to fix did not: $open"
# A finding a later review gives as open is carried on under that review.
second="$(review "$repo" 2 '{"kind": "full"}' \
  "[$(jq '. + {continues: "R01-M1"}' <<<"$(finding M1 major)")]" '[{"finding_id": "R01-M1", "status": "open", "evidence": "still unchecked"}]')"
[[ -z "$(lib "$repo" review_artifact_errors "$second")" ]] || fail "a review that carries an open finding on is invalid"
open="$(lib "$repo" review_chain_open . feature-12-speed 3 | jq -c 'map([.id, .carried])')"
[[ "$open" == '[["R02-M1",true]]' ]] || fail "the carried finding is not open under round 2: $open"
lib "$repo" review_render_markdown "$second" x | grep -Fq "**Continues:** R01-M1, still open" ||
  fail "the report does not show which finding is carried on"
lib "$repo" review_render_markdown "$second" x | grep -Fq -- "- R01-M1: open. still unchecked" ||
  fail "the report does not show the dispositions"
# An open disposition without a finding that carries it on, and a finding
# that continues no open disposition, are invalid.
jq '.findings[0].continues = null' "$second" >"$tmp/bad.json"
lib "$repo" review_artifact_errors "$tmp/bad.json" | grep -Fq "R01-M1 is not carried on" ||
  fail "an open disposition without a carrying finding was accepted"
jq '.dispositions[0].status = "resolved"' "$second" >"$tmp/bad.json"
lib "$repo" review_artifact_errors "$tmp/bad.json" | grep -Fq "which no disposition gives as open" ||
  fail "a finding that continues a resolved finding was accepted"
# A disposition is needed for every open earlier finding, and only for those.
lib "$repo" review_chain_open . feature-12-speed 2 >"$tmp/open.json"
jq '.dispositions = []' "$second" >"$tmp/bad.json"
lib "$repo" review_chain_disposition_errors "$tmp/bad.json" "$tmp/open.json" | grep -Fq "R01-M1 is open and has no disposition" ||
  fail "a missing disposition was not reported"
jq '.dispositions += [{finding_id: "R01-S1", status: "resolved", evidence: "x"}]' "$second" >"$tmp/bad.json"
lib "$repo" review_chain_disposition_errors "$tmp/bad.json" "$tmp/open.json" | grep -Fq "R01-S1 is not an earlier finding that is open" ||
  fail "a disposition of a closed finding was not reported"
# A review made under the rule closes only what its dispositions close: one
# that drops them closes nothing, and its artifact is invalid.
jq 'del(.dispositions)' "$second" >"$tmp/dropped.json"
lib "$repo" review_artifact_errors "$tmp/dropped.json" | grep -Fq "must give the dispositions of the earlier open findings" ||
  fail "a review with compared_tree and without dispositions was accepted"
cp "$second" "$tmp/kept.json" && mv "$tmp/dropped.json" "$second"
open="$(lib "$repo" review_chain_open . feature-12-speed 3 | jq -c 'map(.id)')"
[[ "$open" == '["R01-M1","R02-M1"]' ]] || fail "a review that dropped its dispositions closed the findings before it: $open"
mv "$tmp/kept.json" "$second"
# A review made before the rule has neither compared_tree nor dispositions: it
# closes what came before.
jq 'del(.dispositions, .compared_tree)' "$second" >"$tmp/legacy.json" && mv "$tmp/legacy.json" "$second"
open="$(lib "$repo" review_chain_open . feature-12-speed 3 | jq -c 'map(.id)')"
[[ "$open" == '["R02-M1"]' ]] || fail "a review without dispositions did not close the findings before it: $open"

# --- Criterion 4: the completion record and the handoff note are in the
# review fingerprint, one test per file.
repo="$(setup_repo fingerprint)"
mkdir -p "$repo/.agents/handoffs"
printf 'Done.\n' >"$repo/.agents/handoffs/12.md"
current="$(review "$repo" 1 '{"kind": "full"}' '[]' '[]')"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "a fresh review is not current"; }
cp "$repo/.agents/completion/12.json" "$tmp/record.json"
jq '.criteria[0].evidence = "nothing"' "$tmp/record.json" >"$repo/.agents/completion/12.json"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 1 ]] || fail "a change to the completion record after the review left it current"
grep -Fq "M	.agents/completion/12.json" "$repo.out" || fail "the stale notice does not name the completion record"
cp "$tmp/record.json" "$repo/.agents/completion/12.json"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 0 ]] || fail "restoring the completion record did not make the review current again"
printf 'Remaining: more\n' >>"$repo/.agents/handoffs/12.md"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 1 ]] || fail "a change to the handoff note after the review left it current"
grep -Fq "M	.agents/handoffs/12.md" "$repo.out" || fail "the stale notice does not name the handoff note"
rm "$repo/.agents/handoffs/12.md"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 1 ]] || fail "removing the handoff note after the review left it current"
# A review made before the rule covers the working tree only, as before.
jq 'del(.record_paths)' "$current" >"$tmp/legacy.json" && mv "$tmp/legacy.json" "$current"
record_reviewed_tree "$repo" "$current"
jq '.criteria[0].evidence = "other"' "$tmp/record.json" >"$repo/.agents/completion/12.json"
run_script "$repo" ./scripts/check-review.sh "$current"
[[ "$status" -eq 0 ]] || fail "a review without record paths became stale through the completion record"

# --- Criterion 3: the bounded-impact rule. Each delta starts from the content
# round 1 reviewed; the reasons are printed, and nothing for a bounded delta.
repo="$(setup_repo bounded)"
baseline="$(review "$repo" 1 '{"kind": "full"}' '[]' '[]')"
from="$(jq -r '.reviewed_tree' "$baseline")"
echo '[]' >"$tmp/no-open.json"
rules="$(lib "$repo" guardrails_rules_refs . main)"
# unbounded <label> <open-json-file>: the reasons for the current content.
unbounded() {
  lib "$repo" review_delta_unbounded . "$rules" "$baseline" "$from" "$(content_tree "$repo")" "$2"
}
reset_delta() {
  git -C "$repo" checkout -q -- .
  git -C "$repo" clean -qfd -- src site tests docs scripts table.csv
  record "$repo" 2
}
# A test, documentation, lesson content, and one module whose importers the
# baseline review covered: bounded, also when the delta is very large (there
# is no changed-lines threshold).
printf 'def speed(v):\n    # the speed of the wave, in m/s\n    return v\n' >"$repo/src/pbc/waves/speed.py"
printf '\n\ndef test_speed_zero():\n    assert speed(0) == 0\n' >>"$repo/tests/test_speed.py"
printf '\nMore about waves.\n' >>"$repo/site/lessons/waves/index.qmd"
for ((line = 0; line < 5000; line++)); do echo "Line $line of the guide."; done >>"$repo/docs/guide.md"
jq '.criteria[0].evidence = "tests/test_speed.py::test_speed_zero"' "$repo/.agents/completion/12.json" >"$tmp/r.json" &&
  mv "$tmp/r.json" "$repo/.agents/completion/12.json"
reasons="$(unbounded "$repo" "$tmp/no-open.json")"
[[ -z "$reasons" ]] || fail "a bounded delta of 5000 lines was refused: $reasons"
# Nor does the rule count changed lines anywhere.
if grep -Eq -- '--numstat|--shortstat|wc -l' "$source_root/scripts/lib/review-chain.sh"; then
  fail "the bounded-impact rule counts changed lines"
fi
reset_delta

# expect_unbounded <description> <fragment> [<open-json-file>]
expect_unbounded() {
  reasons="$(unbounded "$repo" "${3:-$tmp/no-open.json}")"
  printf '%s\n' "$reasons" | grep -Fq -- "$2" || fail "$1 did not require a full review (reasons: ${reasons:-none})"
  reset_delta
}
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
expect_unbounded "a Level 3 path" "a Level 3 path: scripts/lib/completion.sh"
printf 'from pbc.waves.speed import speed\n\n\ndef test_speed():\n    speed(1)\n\n\ndef test_double():\n    assert True\n' >"$repo/tests/test_speed.py"
expect_unbounded "an escalation trigger" "an escalation trigger: assertion removed or changed in tests/test_speed.py"
printf 'p { color: blue; }\n' >"$repo/site/styles.css"
expect_unbounded "a shared input" "a shared input of ADR 014 decision 4: site/styles.css"
mkdir -p "$repo/src/pbc/authoring"
printf 'x = 1\n' >"$repo/src/pbc/authoring/new.py"
expect_unbounded "a change to the authoring package" "a shared input of ADR 014 decision 4: src/pbc/authoring/new.py"
printf 'def speed(v, unit="m/s"):\n    # the speed of the wave\n    return v\n' >"$repo/src/pbc/waves/speed.py"
expect_unbounded "a changed exported interface" "a change to the exported interface of src/pbc/waves/speed.py"
printf 'def speed(v):\n    # the speed of the wave\n    return v\n\n\ndef faster(v):\n    return 2 * v\n' >"$repo/src/pbc/waves/speed.py"
expect_unbounded "a new exported name" "a change to the exported interface of src/pbc/waves/speed.py"
jq -n "[{id: \"R01-M1\", round: \"01\", severity: \"major\", title: \"x\", evidence: \"src/pbc/waves/speed.py:2\", carried: true}]" >"$tmp/carried.json"
printf 'def speed(v):\n    # the speed of the wave, again\n    return v\n' >"$repo/src/pbc/waves/speed.py"
expect_unbounded "an unresolved earlier finding" "a file with an earlier unresolved finding (R01-M1): src/pbc/waves/speed.py" "$tmp/carried.json"
# The same change with a finding that is open for its first fix is bounded.
jq '.[0].carried = false' "$tmp/carried.json" >"$tmp/first-fix.json"
printf 'def speed(v):\n    # the speed of the wave, again\n    return v\n' >"$repo/src/pbc/waves/speed.py"
reasons="$(unbounded "$repo" "$tmp/first-fix.json")"
[[ -z "$reasons" ]] || fail "the first fix of an open finding was refused: $reasons"
reset_delta
printf '# the waves\n' >"$repo/src/pbc/waves/__init__.py"
expect_unbounded "an undecidable search (a package)" "the importer search cannot decide the reach of a package's __init__"
printf 'import importlib\n\n\ndef third(v):\n    return v / 3\n' >"$repo/src/pbc/waves/third.py"
expect_unbounded "an undecidable search (a dynamic import)" "the module loads code by a computed name (importlib)"
# A separate module that loads modules by a computed name may load the changed
# one, which the importer search cannot see (review 04 M1): the loader is in
# the tree the delta starts from, and only the loaded module changes.
printf 'import importlib\n\n\ndef load(name):\n    return importlib.import_module(f"pbc.waves.{name}")\n' >"$repo/src/pbc/waves/loader.py"
loader_from="$(content_tree "$repo")"
printf 'def speed(v):\n    # the speed of the wave, by name\n    return v\n' >"$repo/src/pbc/waves/speed.py"
reasons="$(lib "$repo" review_delta_unbounded . "$rules" "$baseline" "$loader_from" "$(content_tree "$repo")" "$tmp/no-open.json")"
printf '%s\n' "$reasons" | grep -Fq -- "a file that loads code by a computed name and may load src/pbc/waves/speed.py, so the importer search cannot decide its reach: src/pbc/waves/loader.py" ||
  fail "a module that a separate dynamic importer may load did not require a full review (reasons: ${reasons:-none})"
reset_delta
printf 'def third(v):\n    # a third\n    return v / 3\n' >"$repo/src/pbc/waves/third.py"
expect_unbounded "an importer outside the baseline review" \
  "an importer of src/pbc/waves/third.py that the baseline review (round 1) did not cover: src/pbc/waves/ninth.py"
printf 'def speed(v):\n    # one\n    return v\n' >"$repo/src/pbc/waves/speed.py"
printf 'from pbc.waves.speed import speed\n\n\ndef double(v):\n    # two\n    return speed(v) * 2\n' >"$repo/src/pbc/waves/double.py"
expect_unbounded "two modules" "more than one source module changed"
printf 'id,value\n1,3\n' >"$repo/table.csv"
expect_unbounded "another kind of file" "a change outside tests, documentation, lesson content, and one source module: table.csv"

# --- Criterion 2: finish-feature.sh accepts a Level 2 chain and refuses it
# otherwise, a test per condition.
chain_repo chain-holds
repo="$REPO"
finish "$repo"
expect_commit "$repo" "a chain from a review of the complete feature"
git -C "$repo" log -1 --format=%B | grep -Fq "Review: round 2, PASS, by claude (model-r); reviews of changes since round 1, a review of the complete feature, with every finding given its disposition; triage published on #12" ||
  { git -C "$repo" log -1 --format=%B >&2; fail "the commit message does not describe the chain"; }

# It begins with a review of the complete feature: a chain whose first round
# is missing has a gap.
chain_repo chain-no-start
repo="$REPO"
rm "$FIRST" "$repo/.agents/triage/feature-12-speed-review-01-triage.json"
finish "$repo"
expect_no_commit "$repo" "a chain without its review of the complete feature" "round 2 builds on round 1, which has no review artifact: a gap"

# It is contiguous: a review of changes builds on the round right before it.
chain_repo chain-skips
repo="$REPO"
third_review="$(review "$repo" 3 "$(jq -n --arg tree "$(jq -r '.reviewed_tree' "$FIRST")" '{kind: "changes", since_round: 1, base_tree: $tree}')" '[]' '[]')"
finish "$repo"
expect_no_commit "$repo" "a review of changes that skips a round" "round 3 builds on round 1, not on the round right before it"
# ... and on the tree that round reviewed.
chain_repo chain-break
repo="$REPO"
jq '.scope.base_tree = "0123456789012345678901234567890123456789" | .compared_tree = .scope.base_tree' "$SECOND" >"$tmp/s.json" && mv "$tmp/s.json" "$SECOND"
finish "$repo"
expect_no_commit "$repo" "a review of changes on another tree" "did not compare against the tree that round 1 reviewed: a break"
# ... and begins with a review of the complete feature that compared against
# the tree of its merge base (review 06 M1), also when it is the only round.
chain_repo chain-baseline-tree
repo="$REPO"
jq '.compared_tree = "0123456789012345678901234567890123456789"' "$FIRST" >"$tmp/f.json" && mv "$tmp/f.json" "$FIRST"
finish "$repo"
expect_no_commit "$repo" "a chain whose review of the complete feature compared against another tree" \
  "round 1 is a review of the complete feature that did not compare against the tree of its merge base: a break"
repo="$(setup_repo full-review-tree)"
printf '\n\ndef test_speed_two():\n    assert speed(2) == 2\n' >>"$repo/tests/test_speed.py"
full_review="$(review "$repo" 1 '{"kind": "full"}' '[]' '[]')"
jq '.compared_tree = "0123456789012345678901234567890123456789"' "$full_review" >"$tmp/f.json" && mv "$tmp/f.json" "$full_review"
finish "$repo"
expect_no_commit "$repo" "a single review of the complete feature that compared against another tree" \
  "round 1 is a review of the complete feature that did not compare against the tree of its merge base: a break"

# It ends at exactly the current tree.
chain_repo chain-stale
repo="$REPO"
printf '\n# later\n' >>"$repo/tests/test_speed.py"
finish "$repo"
expect_no_commit "$repo" "a chain that ends before the current content" "the latest review (.agents/reviews/feature-12-speed-review-02.json) is stale"

# Every earlier finding has a disposition.
chain_repo chain-no-disposition
repo="$REPO"
jq '.dispositions = []' "$SECOND" >"$tmp/s.json" && mv "$tmp/s.json" "$SECOND"
finish "$repo"
expect_no_commit "$repo" "a review that leaves an earlier finding without a disposition" \
  "round 2: the earlier finding R01-M1 is open and has no disposition" "finding R01-M1 [major] is open"

# A review made under the chain rule cannot drop its dispositions to close the
# earlier findings, nor pass for a review made before the rule.
chain_repo chain-dispositions-omitted
repo="$REPO"
jq 'del(.dispositions)' "$SECOND" >"$tmp/s.json" && mv "$tmp/s.json" "$SECOND"
finish "$repo"
expect_no_commit "$repo" "a review that omits its dispositions" \
  "a review that records compared_tree must give the dispositions of the earlier open findings"
chain_repo chain-legacy-after-rule
repo="$REPO"
jq 'del(.dispositions, .compared_tree)' "$SECOND" >"$tmp/s.json" && mv "$tmp/s.json" "$SECOND"
finish "$repo"
expect_no_commit "$repo" "a review without the chain fields after a review made under the chain rule" \
  "round 2 records no compared_tree after round 1 did"

# No finding is open: a finding carried on to the latest round is still to fix.
chain_repo chain-open
repo="$REPO"
review "$repo" 2 "$(jq -r '.scope' "$SECOND")" "[$(jq '. + {continues: "R01-M1"}' <<<"$(finding M1 major tests/test_speed.py:9)")]" \
  '[{"finding_id": "R01-M1", "status": "open", "evidence": "the new test does not check the speed"}]' >/dev/null
triage "$repo" "$SECOND" FIX_NOW
finish "$repo"
expect_no_commit "$repo" "a chain that leaves a finding open" "critical or major finding"

# Every review of changes in the chain is bounded, checked again at the finish.
chain_repo chain-unbounded
repo="$REPO"
printf 'p { color: blue; }\n' >"$repo/site/styles.css"
review "$repo" 2 "$(jq -r '.scope' "$SECOND")" '[]' "$(jq -c '.dispositions' "$SECOND")" >/dev/null
finish "$repo"
expect_no_commit "$repo" "a chain with a review of changes whose reach is not certain" \
  "round 2 reviewed only changes whose reach is not certain: a shared input of ADR 014 decision 4: site/styles.css"

# --- Criterion 6: Level 1 needs no review, recorded without an exception.
repo="$(setup_repo level1)"
git -C "$repo" reset -q --hard main
mkdir -p "$repo/.agents/summaries"
printf -- '- Explains the guide.\n' >"$repo/.agents/summaries/12.md"
record "$repo" 1
printf 'More guidance.\n' >>"$repo/docs/guide.md"
run_script "$repo" ./scripts/finish-feature.sh 12 "Extend the guide" --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "a Level 1 change without a review was refused"; }
git -C "$repo" log -1 --format=%B | grep -Fqx "Review: none required (Level 1: documentation and process files only; ADR 020 decision 4)" ||
  fail "the commit does not record that Level 1 needs no review"
if git -C "$repo" log -1 --format=%B | grep -Fq "low risk:"; then fail "Level 1 was recorded as a --no-review exception"; fi
# --no-review is refused at Level 1: the level needs no exception.
repo="$(setup_repo level1-no-review)"
git -C "$repo" reset -q --hard main
mkdir -p "$repo/.agents/summaries"
printf -- '- Explains the guide.\n' >"$repo/.agents/summaries/12.md"
record "$repo" 1
printf 'More guidance.\n' >>"$repo/docs/guide.md"
run_script "$repo" ./scripts/finish-feature.sh 12 "Extend the guide" --no-review "documentation only" --unattended
[[ "$status" -ne 0 ]] || { git -C "$repo" log -1 --format=%B >&2; fail "a Level 1 change was committed as a --no-review exception"; }
[[ "$(git -C "$repo" rev-list --count main..HEAD)" -eq 0 ]] || fail "a Level 1 change with --no-review created a commit"
grep -Fq "the change is Level 1, which needs no independent review" "$repo.out" ||
  { cat "$repo.out" >&2; fail "the Level 1 refusal of --no-review is not explained"; }
# The same change at Level 2 still needs its review.
repo="$(setup_repo level2-needs-review)"
printf 'More guidance.\n' >>"$repo/docs/guide.md"
printf '\n# a fix\n' >>"$repo/tests/test_speed.py"
finish "$repo"
expect_no_commit "$repo" "a Level 2 change without a review" "no review of this feature exists"

# Level 3 keeps a review of the complete feature in every round: a review of
# changes is not accepted at the finish...
chain_repo level3-chain
repo="$REPO"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
review "$repo" 2 "$(jq -r '.scope' "$SECOND")" '[]' "$(jq -c '.dispositions' "$SECOND")" >/dev/null
run_script "$repo" ./scripts/finish-feature.sh 12 "Explain the speed" --unattended
[[ "$status" -ne 0 ]] || fail "a Level 3 change was committed on a review of changes"
grep -Fq "covers only the changes since round 1" "$repo.out" || { cat "$repo.out" >&2; fail "the Level 3 refusal does not name the review of changes"; }
# ... also when an earlier round reviewed only changes and the latest one
# reviews the complete feature.
chain_repo level3-earlier-delta
repo="$REPO"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
latest="$(review "$repo" 3 '{"kind": "full"}' '[]' '[]')"
jq '.verification.tier = "full"' "$latest" >"$tmp/l.json" && mv "$tmp/l.json" "$latest"
run_script "$repo" ./scripts/finish-feature.sh 12 "Explain the speed" --unattended
[[ "$status" -ne 0 ]] || fail "a Level 3 change was committed with an earlier review of changes"
grep -Fq "keeps a review of the complete feature in every round (ADR 020 decision 4), and round 2 covers only the changes since round 1" "$repo.out" ||
  { cat "$repo.out" >&2; fail "the Level 3 refusal does not name the earlier review of changes"; }
# ... and review-feature.sh makes none: --changes reviews the complete feature.
repo="$(setup_repo level3-review)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
pass='{"architecture_impact": {"level": "minor", "rationale": "Within.", "checked_against": [], "risk_level": 3, "escalation_triggers": []}, "verdict": "PASS", "limitations": "", "findings": [], "dispositions": []}'
MOCK_OUTPUT="$pass" run_script "$repo" ./scripts/review-feature.sh 12
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the first Level 3 review failed"; }
printf '\n# a fix\n' >>"$repo/tests/test_speed.py"
MOCK_OUTPUT="$pass" run_script "$repo" ./scripts/review-feature.sh 12 --changes --feedback
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the second Level 3 review failed"; }
[[ "$(jq -r '.scope.kind' "$repo/.agents/reviews/feature-12-speed-review-02.json")" == "full" ]] ||
  fail "a Level 3 change got a review of changes only"
grep -Fq "keeps a review of the complete feature in every round" "$repo.out" || fail "the full Level 3 round was not explained"

# At Level 2 a delta whose reach is not certain gets a review of the complete
# feature, and a bounded one a review of the changes.
repo="$(setup_repo level2-review)"
pass="$(jq -c '.architecture_impact.risk_level = 2' <<<"$pass")"
MOCK_OUTPUT="$pass" run_script "$repo" ./scripts/review-feature.sh 12
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the first Level 2 review failed"; }
printf 'p { color: blue; }\n' >"$repo/site/styles.css"
MOCK_OUTPUT="$pass" run_script "$repo" ./scripts/review-feature.sh 12 --changes
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the Level 2 review of an unbounded delta failed"; }
[[ "$(jq -r '.scope.kind' "$repo/.agents/reviews/feature-12-speed-review-02.json")" == "full" ]] ||
  fail "an unbounded delta got a review of changes only"
grep -Fq -- "- a shared input of ADR 014 decision 4: site/styles.css" "$repo.out" || fail "the reason for the full review was not shown"
printf '\n# a fix\n' >>"$repo/tests/test_speed.py"
MOCK_OUTPUT="$pass" run_script "$repo" ./scripts/review-feature.sh 12 --changes
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the Level 2 review of a bounded delta failed"; }
third_review="$repo/.agents/reviews/feature-12-speed-review-03.json"
[[ "$(jq -c '[.scope.kind, .scope.since_round, (.compared_tree == .scope.base_tree)]' "$third_review")" == '["changes",2,true]' ]] ||
  fail "a bounded delta was not reviewed as the changes since the round before"
[[ "$(jq -r '.reviewed_tree' "$third_review")" == "$(content_tree "$repo")" ]] ||
  fail "the review did not fingerprint the content with the completion record and the handoff note"

# --- Criterion 5: mechanical triage of minor and suggestion findings at
# Levels 1 and 2, published once with a follow-up Issue per DEFER.
repo="$(setup_repo mechanical)"
printf '\n# a fix\n' >>"$repo/tests/test_speed.py"
minor_review="$(review "$repo" 1 '{"kind": "full"}' "[$(finding MIN1 minor), $(finding S1 suggestion)]" '[]')"
run_script "$repo" ./scripts/triage-review.sh "$minor_review"
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the mechanical triage failed"; }
[[ ! -e "$repo.agent.log" ]] || fail "a triage agent was started for minor and suggestion findings at Level 2"
mechanical="$repo/.agents/triage/feature-12-speed-review-01-triage.json"
[[ "$(jq -c '[.mechanical, (.decisions | map([.finding_id, .decision]))]' "$mechanical")" == '[true,[["MIN1","DEFER"],["S1","ACCEPT"]]]' ]] ||
  fail "the mechanical triage did not defer the minor finding and accept the suggestion"
jq -e '.decisions | all(.rationale | test("mechanically"))' "$mechanical" >/dev/null || fail "a mechanical decision has no reason"
[[ "$(jq -r '.decisions[0].followup.issue_number' "$mechanical")" == "321" ]] || fail "the deferred finding has no follow-up Issue"
[[ "$(grep -c '^issue create ' "$repo.gh.log")" -eq 1 ]] || fail "not exactly one follow-up Issue was created"
[[ "$(grep -c '^issue comment 12 ' "$repo.gh.log")" -eq 1 ]] || fail "the mechanical triage was not published once"
[[ -z "$(lib "$repo" triage_artifact_errors "$mechanical" "$minor_review")" ]] || fail "the mechanical triage is invalid"
grep -Fq "mechanically: minor and suggestion findings at Level 1 or 2" "${mechanical%.json}.md" ||
  fail "the report does not say that the triage was mechanical"
run_script "$repo" ./scripts/triage-review.sh "$minor_review"
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "a second mechanical triage run failed"; }
if grep -q '^issue comment\|^issue create' "$repo.gh.log"; then fail "the mechanical triage was published or deferred again"; fi
[[ ! -e "$repo/.agents/triage/feature-12-speed-review-01-triage-02.json" ]] || fail "a second mechanical triage was stored"
# A stored mechanical triage whose decisions differ from the mapping is
# invalid, and finish-feature.sh refuses it: a minor finding accepted or
# fixed now, a suggestion deferred, a deferral without its follow-up Issue.
cp "$mechanical" "$tmp/mechanical.json"
for tamper in \
  'minor-accepted#(.decisions[0] |= (.decision = "ACCEPT" | .followup = null))#defers every minor finding; MIN1 is ACCEPT' \
  'minor-fixed#(.decisions[0] |= (.decision = "FIX_NOW" | .followup = null))#defers every minor finding; MIN1 is FIX_NOW' \
  'suggestion-deferred#(.decisions[1] |= (.decision = "DEFER" | .followup = $d.followup))#accepts every suggestion; S1 is DEFER' \
  'no-followup-issue#(.decisions[0].followup |= del(.issue_number, .issue_url))#only with its follow-up Issue; MIN1 has none'; do
  IFS='#' read -r name filter message <<<"$tamper"
  jq --argjson d "$(jq '.decisions[0]' "$tmp/mechanical.json")" "$filter" "$tmp/mechanical.json" >"$mechanical"
  lib "$repo" triage_artifact_errors "$mechanical" "$minor_review" | grep -Fq "$message" ||
    fail "$name: a mechanical triage that differs from the mapping was accepted"
  finish "$repo"
  expect_no_commit "$repo" "$name" "the triage of round 1 is invalid" "$message"
done
cp "$tmp/mechanical.json" "$mechanical"
# finish-feature.sh accepts it at Level 2.
finish "$repo"
expect_commit "$repo" "a Level 2 feature with a mechanical triage"

# A critical or major finding is never triaged mechanically: the review gets
# the full triage per finding, minor findings with it.
repo="$(setup_repo mechanical-major)"
major_review="$(review "$repo" 1 '{"kind": "full"}' "[$(finding M1 major), $(finding MIN1 minor)]" '[]')"
MOCK_OUTPUT='{"decisions": [{"finding_id": "M1", "decision": "FIX_NOW", "rationale": "Wrong.", "followup": null}, {"finding_id": "MIN1", "decision": "ACCEPT", "rationale": "Fine.", "followup": null}]}' \
  run_script "$repo" ./scripts/triage-review.sh "$major_review" --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the full triage of a major finding failed"; }
[[ -e "$repo.agent.log" ]] || fail "a review with a major finding was triaged without the triage agent"
[[ "$(jq -r '.mechanical // false' "$repo/.agents/triage/feature-12-speed-review-01-triage.json")" == "false" ]] ||
  fail "a review with a major finding was triaged mechanically"
# A mechanical triage of such a review is invalid.
jq '.decisions = [{finding_id: "M1", severity: "major", title: "The speed is not checked", decision: "FIX_NOW", rationale: "x", followup: null},
  {finding_id: "MIN1", severity: "minor", title: "The speed is not checked", decision: "ACCEPT", rationale: "x", followup: null}]
  | .mechanical = true' "$repo/.agents/triage/feature-12-speed-review-01-triage.json" >"$tmp/m.json"
lib "$repo" triage_artifact_errors "$tmp/m.json" "$major_review" | grep -Fq "never triaged mechanically" ||
  fail "a mechanical triage of a major finding was accepted"

# Every finding at Level 3 keeps the full triage.
repo="$(setup_repo mechanical-level3)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
level3_review="$(review "$repo" 1 '{"kind": "full"}' "[$(finding MIN1 minor)]" '[]')"
jq '.risk.required = 3' "$level3_review" >"$tmp/l3.json" && mv "$tmp/l3.json" "$level3_review"
MOCK_OUTPUT='{"decisions": [{"finding_id": "MIN1", "decision": "DEFER", "rationale": "Later.", "followup": {"title": "Check the speed", "recommended_action": "Add the check.", "acceptance_criteria": ["The speed is checked."]}}]}' \
  run_script "$repo" ./scripts/triage-review.sh "$level3_review" --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the full triage at Level 3 failed"; }
[[ -e "$repo.agent.log" ]] || fail "a minor finding at Level 3 was triaged without the triage agent"
# A mechanical triage that claims Level 2 for a Level 3 change, with the
# decisions of the mapping, is refused at the finish.
jq '.mechanical = true | del(.unattended)' "$repo/.agents/triage/feature-12-speed-review-01-triage.json" >"$tmp/m.json" &&
  mv "$tmp/m.json" "$repo/.agents/triage/feature-12-speed-review-01-triage.json"
jq '.verification.tier = "full"' "$level3_review" >"$tmp/l3.json" && mv "$tmp/l3.json" "$level3_review"
run_script "$repo" ./scripts/finish-feature.sh 12 "Explain the speed" --unattended
[[ "$status" -ne 0 ]] || fail "a Level 3 change was committed on a mechanical triage"
grep -Fq "was made mechanically; every finding of a Level 3 change keeps the full triage" "$repo.out" ||
  { cat "$repo.out" >&2; fail "the refusal of the mechanical triage at Level 3 was not explained"; }

# A review that claims Level 2 for a Level 3 change is not triaged
# mechanically: triage-review.sh derives the level of the change again.
repo="$(setup_repo mechanical-claims-level2)"
printf '# more\n' >>"$repo/scripts/lib/completion.sh"
record "$repo" 3
claimed_review="$(review "$repo" 1 '{"kind": "full"}' "[$(finding MIN1 minor)]" '[]')"
MOCK_OUTPUT='{"decisions": [{"finding_id": "MIN1", "decision": "DEFER", "rationale": "Later.", "followup": {"title": "Check the speed", "recommended_action": "Add the check.", "acceptance_criteria": ["The speed is checked."]}}]}' \
  run_script "$repo" ./scripts/triage-review.sh "$claimed_review" --unattended
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "the full triage of a review that claims Level 2 failed"; }
[[ -e "$repo.agent.log" ]] || fail "a Level 3 change whose review claims Level 2 was triaged mechanically"
[[ "$(jq -r '.mechanical // false' "$repo/.agents/triage/feature-12-speed-review-01-triage.json")" == "false" ]] ||
  fail "a Level 3 change whose review claims Level 2 got a mechanical triage"
grep -Fq "the level derived now for the change is 3" "$repo.out" ||
  { cat "$repo.out" >&2; fail "the full triage of a review that claims Level 2 was not explained"; }

echo "review chain tests passed"
