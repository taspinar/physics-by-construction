#!/usr/bin/env bash

set -euo pipefail

# Run as on CI: without the user's global or system Git configuration, so a
# test cannot depend on a local Git identity or setting.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/guardrails-test.XXXXXX")"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

fail() {
  echo "guardrails test failed: $*" >&2
  exit 1
}

source "$source_root/tests/lib-fakes.sh"

# A project with an ADR, two checks, and a gate configuration, on a feature
# branch without changes.
setup_repo() {
  local repo="$tmp/$1"

  mkdir -p "$repo/docs/decisions" "$repo/site" "$repo/src" "$repo/.agents/policies"
  copy_workflow "$repo"
  printf 'protected: site/_quarto.yml deploy\nsensitive: pyproject.toml docs/architecture.md\n' \
    >"$repo/.agents/policies/guardrails.conf"
  printf '# ADR 001: Quarto\n\nStatus: Accepted\n' >"$repo/docs/decisions/001-quarto.md"
  printf '# Architecture\n' >"$repo/docs/architecture.md"
  printf 'project: site\n' >"$repo/site/_quarto.yml"
  printf '[project]\nname = "x"\n' >"$repo/pyproject.toml"
  printf 'lint: true\nunit: true\n' >"$repo/scripts/verify.conf"
  printf 'print("x")\n' >"$repo/src/code.py"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.name "Guardrails Test"
  git -C "$repo" config user.email "guardrails-test@example.com"
  git -C "$repo" add .
  git -C "$repo" commit -qm "Seed"
  git -C "$repo" switch -q -c feature/5-thing
  printf '%s\n' "$repo"
}

# check <repo> [argument...]: runs the gate; sets 'status' and '<repo>.out'.
check() {
  local repo="$1"

  shift
  status=0
  (cd "$repo" && PATH="/usr/bin:/bin" ./scripts/check-guardrails.sh "$@") >"$repo.out" 2>&1 || status=$?
}

expect_level() {
  local repo="$1"
  local level="$2"
  local description="$3"

  check "$repo"
  [[ "$status" -eq 0 ]] || {
    cat "$repo.out" >&2
    fail "the gate failed although: $description"
  }
  [[ "$(sed -n 1p "$repo.out")" == "level: $level" ]] || {
    cat "$repo.out" >&2
    fail "expected level $level: $description"
  }
}

# Ordinary work of a feature needs nobody.
repo="$(setup_repo plain)"
printf 'print("y")\n' >>"$repo/src/code.py"
printf 'new\n' >"$repo/src/new.py"
expect_level "$repo" none "a feature changes only its own code"

# Every ADR that is added, changed, or removed needs the owner: a new ADR can
# replace an accepted one without touching its file.
repo="$(setup_repo adr-added)"
printf '# ADR 002: Replace Quarto with another generator\n\nStatus: Proposed\n' >"$repo/docs/decisions/002-other.md"
expect_level "$repo" protected "a feature adds an ADR"
grep -Fq "docs/decisions/002-other.md" "$repo.out" || fail "the added ADR was not named"

repo="$(setup_repo adr-changed)"
printf '\nSuperseded.\n' >>"$repo/docs/decisions/001-quarto.md"
expect_level "$repo" protected "a feature changes an accepted ADR"

repo="$(setup_repo adr-removed)"
git -C "$repo" rm -q docs/decisions/001-quarto.md
expect_level "$repo" protected "a feature removes an ADR"

# The paths the project lists: protected needs the owner, sensitive does not.
repo="$(setup_repo listed-protected)"
printf 'project: other\n' >"$repo/site/_quarto.yml"
expect_level "$repo" protected "a feature changes a path the project protects"
grep -Fq "site/_quarto.yml" "$repo.out" || fail "the protected path was not named"

repo="$(setup_repo listed-new-file)"
mkdir -p "$repo/deploy"
printf 'target: elsewhere\n' >"$repo/deploy/config.yml"
expect_level "$repo" protected "a feature adds an untracked file under a protected path"

repo="$(setup_repo listed-sensitive)"
printf 'dependencies = ["y"]\n' >>"$repo/pyproject.toml"
printf '\nMore.\n' >>"$repo/docs/architecture.md"
expect_level "$repo" sensitive "a feature changes sensitive paths only"
grep -Fq "pyproject.toml" "$repo.out" || fail "the sensitive path was not named"

# The verification: adding a check is sensitive, changing or removing one
# is protected.
repo="$(setup_repo check-added)"
printf 'new-check: true\n' >>"$repo/scripts/verify.conf"
expect_level "$repo" sensitive "a feature adds a check"

repo="$(setup_repo check-changed)"
printf 'lint: true\nunit: echo skipped\n' >"$repo/scripts/verify.conf"
expect_level "$repo" protected "a feature changes an existing check"

repo="$(setup_repo check-removed)"
printf 'lint: true\n' >"$repo/scripts/verify.conf"
expect_level "$repo" protected "a feature removes a check"

repo="$(setup_repo checks-deleted)"
rm "$repo/scripts/verify.conf"
expect_level "$repo" protected "a feature deletes the verification configuration"

# The same under the project's own configuration, which names
# scripts/verify.conf on no line, so the builtin rule alone reads it (D4 of
# #446, Issue #465): a listed path would make an added check protected too.
# setup_project_checks <label>: the project's gate configuration on the base.
setup_project_checks() {
  local repo

  repo="$(setup_repo "$1")"
  git -C "$repo" switch -q main
  cp "$source_root/.agents/policies/guardrails.conf" "$repo/.agents/policies/guardrails.conf"
  git -C "$repo" commit -qam "The project's gate configuration"
  git -C "$repo" switch -q feature/5-thing
  git -C "$repo" reset -q --hard main
  printf '%s\n' "$repo"
}
if sed -n 's/^protected:[[:space:]]*//p' "$source_root/.agents/policies/guardrails.conf" | tr -s '[:space:]' '\n' |
  grep -Ex 'scripts(/verify\.conf)?' >/dev/null; then
  fail "guardrails.conf names scripts/verify.conf on a protected line; the builtin rule is to read it"
fi
repo="$(setup_project_checks project-check-added)"
printf 'new-check: true\n' >>"$repo/scripts/verify.conf"
expect_level "$repo" sensitive "a feature adds a check under the project's configuration"
grep -Fq "sensitive: scripts/verify.conf (a check is added)" "$repo.out" || fail "the added check was not named as sensitive"

repo="$(setup_project_checks project-check-changed)"
printf 'lint: true\nunit: echo skipped\n' >"$repo/scripts/verify.conf"
expect_level "$repo" protected "a feature changes an existing check under the project's configuration"
grep -Fq "protected: scripts/verify.conf (an existing check or line is changed or removed)" "$repo.out" ||
  fail "the changed check was not named as protected"

repo="$(setup_project_checks project-check-removed)"
printf 'lint: true\n' >"$repo/scripts/verify.conf"
expect_level "$repo" protected "a feature removes a check under the project's configuration"

# A feature cannot relax the rules it is checked by: they are read from its
# base, and the files of the gate are protected themselves.
repo="$(setup_repo rules-relaxed)"
printf 'sensitive: docs/architecture.md\n' >"$repo/.agents/policies/guardrails.conf"
printf 'project: other\n' >"$repo/site/_quarto.yml"
expect_level "$repo" protected "a feature removes a path from the protected list and changes it"
grep -Fq "site/_quarto.yml" "$repo.out" || fail "the rules of the feature were used instead of those of its base"
grep -Fq ".agents/policies/guardrails.conf" "$repo.out" || fail "the changed gate configuration was not named"

for file in scripts/check-guardrails.sh scripts/lib/guardrails.sh scripts/finish-feature.sh \
  scripts/lib/review-run.sh scripts/lib/review-data.sh scripts/lib/agent.sh scripts/review-feature.sh \
  scripts/publish-feature.sh scripts/run-feature.sh scripts/lib/fingerprint.sh \
  .agents/prompts/reviewer.md .agents/schemas/review.schema.json; do
  repo="$(setup_repo "gate-$(basename "$file")")"
  printf '\n# changed\n' >>"$repo/$file"
  expect_level "$repo" protected "a feature changes $file"
done

# Who reviews is part of the gate too.
repo="$(setup_repo reviewer-changed)"
printf 'reviewer: claude weakest\n' >"$repo/.agents/agents.conf"
expect_level "$repo" protected "a feature changes the configured reviewer"

# A protection that the base got after the feature started applies to the
# feature: the rules are those of the base as it is now.
repo="$(setup_repo protected-later)"
printf 'print("y")\n' >>"$repo/src/code.py"
git -C "$repo" stash -q
git -C "$repo" switch -q main
printf 'protected: site/_quarto.yml deploy src\nsensitive: pyproject.toml docs/architecture.md\n' \
  >"$repo/.agents/policies/guardrails.conf"
git -C "$repo" commit -qam "The owner protects src"
git -C "$repo" switch -q feature/5-thing
git -C "$repo" stash pop -q
expect_level "$repo" protected "the base protects a path after the feature started"
grep -Fq "protected: src/code.py" "$repo.out" || fail "the later protection of the base was not applied"
if grep -Fq "protected: .agents/policies/guardrails.conf" "$repo.out"; then
  fail "the change of the rules on the base was counted as a change of the feature"
fi

# The same when only origin knows the new protection and the local base
# branch is behind: the rules of both count, wherever the diff starts.
repo="$(setup_repo protected-on-origin)"
printf 'print("y")\n' >>"$repo/src/code.py"
git -C "$repo" stash -q
git -C "$repo" switch -q -c ahead main
printf 'protected: src\n' >"$repo/.agents/policies/guardrails.conf"
git -C "$repo" commit -qam "The owner protects src on the remote"
git -C "$repo" update-ref refs/remotes/origin/main ahead
git -C "$repo" switch -q feature/5-thing
git -C "$repo" branch -q -D ahead
git -C "$repo" stash pop -q
expect_level "$repo" protected "origin protects a path while the local base is behind"
grep -Fq "protected: src/code.py" "$repo.out" || fail "the protection that only origin knows was not applied"

# An exclusion that only the stale ref still has does not cancel the
# protection of the other: each ref's rules are applied on their own.
repo="$(setup_repo exclusion-removed)"
printf 'print("y")\n' >>"$repo/src/code.py"
git -C "$repo" stash -q
git -C "$repo" switch -q main
printf 'protected: src :(exclude)src/code.py\n' >"$repo/.agents/policies/guardrails.conf"
git -C "$repo" commit -qam "Protect src, except one file"
git -C "$repo" switch -q -c ahead main
printf 'protected: src\n' >"$repo/.agents/policies/guardrails.conf"
git -C "$repo" commit -qam "The owner removes the exception on the remote"
git -C "$repo" update-ref refs/remotes/origin/main ahead
git -C "$repo" switch -q feature/5-thing
git -C "$repo" branch -q -D ahead
git -C "$repo" rebase -q main
git -C "$repo" stash pop -q
expect_level "$repo" protected "origin removes an exclusion while the local base still has it"
grep -Fq "protected: src/code.py" "$repo.out" || fail "a stale exclusion cancelled the current protection"

repo="$(setup_repo workflow-added)"
mkdir -p "$repo/.github/workflows"
printf 'name: x\n' >"$repo/.github/workflows/extra.yml"
expect_level "$repo" protected "a feature adds a CI workflow"

# The heaviest finding decides, and --fail-on-protected turns it into a status.
repo="$(setup_repo mixed)"
printf 'dependencies = ["y"]\n' >>"$repo/pyproject.toml"
printf 'project: other\n' >"$repo/site/_quarto.yml"
expect_level "$repo" protected "a feature changes a sensitive and a protected path"
check "$repo" --fail-on-protected
[[ "$status" -eq 3 ]] || fail "--fail-on-protected exited with $status for a protected change"
repo="$(setup_repo sensitive-status)"
printf 'dependencies = ["y"]\n' >>"$repo/pyproject.toml"
check "$repo" --fail-on-protected
[[ "$status" -eq 0 ]] || fail "--fail-on-protected failed for a sensitive change"

# Two commits, as CI compares the head of a pull request with its base. The
# base may have moved on: only what the feature changed counts.
repo="$(setup_repo commits)"
printf 'project: other\n' >"$repo/site/_quarto.yml"
git -C "$repo" commit -qam "Change the site configuration"
head="$(git -C "$repo" rev-parse HEAD)"
git -C "$repo" switch -q main
printf '# ADR 002: By the owner\n' >"$repo/docs/decisions/002-owner.md"
git -C "$repo" add -A
git -C "$repo" commit -qm "The owner adds an ADR on main"
check "$repo" --commits main "$head" --fail-on-protected
[[ "$status" -eq 3 ]] || fail "the gate did not fail for a protected change between two commits ($status)"
grep -Fq "site/_quarto.yml" "$repo.out" || fail "the protected path between two commits was not named"
if grep -Fq "002-owner.md" "$repo.out"; then fail "work on the base was counted as a change of the feature"; fi

repo="$(setup_repo commits-plain)"
printf 'print("y")\n' >>"$repo/src/code.py"
git -C "$repo" commit -qam "Change the code"
check "$repo" --commits main HEAD --fail-on-protected
[[ "$status" -eq 0 && "$(sed -n 1p "$repo.out")" == "level: none" ]] || fail "ordinary work between two commits was not level none"

# Refusals.
repo="$(setup_repo refusals)"
check "$repo" --commits main
[[ "$status" -eq 2 ]] || fail "--commits with one commit was accepted"
check "$repo" --commits main no-such-commit
[[ "$status" -eq 2 ]] || fail "an unknown commit was accepted"
check "$repo" no-such-base
[[ "$status" -eq 2 ]] || fail "an unknown base branch was accepted"

# --planning (Issue #512): no silent drift of the approved planning. A branch
# that changes a planning-only document is reported, and fails unless the
# approval is current for the change.
setup_planned() {
  local repo
  local fingerprint

  repo="$(setup_repo "$1")"
  git -C "$repo" switch -q main
  printf '# Requirements\n\nStatus: Approved\n' >"$repo/docs/PROJECT_REQUIREMENTS.md"
  printf '# Roadmap\n\n## F01 — Thing\n' >"$repo/docs/roadmap.md"
  fingerprint="$(bash -c 'source "$1/scripts/lib/fingerprint.sh"; source "$1/scripts/lib/planning.sh"
    scratch="$(mktemp -d)"; fingerprint_files "$1" "$scratch" "${PLANNING_SCOPE[@]}"; rm -rf "$scratch"' _ "$repo")"
  printf '# Planning Approval\n\nStatus: Approved\nPlanning fingerprint: %s\n' "$fingerprint" >"$repo/docs/PLANNING_APPROVAL.md"
  git -C "$repo" add -A
  git -C "$repo" commit -qm "Approved planning"
  git -C "$repo" switch -q feature/5-thing
  git -C "$repo" rebase -q main
  printf '%s\n' "$repo"
}

repo="$(setup_planned planning-untouched)"
printf '\nThe thing is a file.\n' >>"$repo/docs/architecture.md"
check "$repo" --planning
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "a feature that leaves the planning-only documents alone was reported"; }
grep -Fq "no planning-only document changed" "$repo.out" || fail "the unchanged planning was not reported as such"

repo="$(setup_planned planning-roadmap)"
printf '\n## F02 — Another thing\n' >>"$repo/docs/roadmap.md"
check "$repo" --planning
[[ "$status" -eq 1 ]] || { cat "$repo.out" >&2; fail "a feature branch that changes the roadmap was not reported ($status)"; }
grep -Fq "  docs/roadmap.md" "$repo.out" || fail "the changed roadmap was not named"
grep -Fq "finish-planning.sh --amend" "$repo.out" || fail "the amendment route was not named"
# Committed on the branch, the same.
git -C "$repo" commit -qam "Change the roadmap"
check "$repo" --planning
[[ "$status" -eq 1 ]] || fail "a committed roadmap change on the branch was not reported"

for document in docs/PROJECT_REQUIREMENTS.md docs/PROJECT_DESCRIPTION.md docs/changes/later.md; do
  repo="$(setup_planned "planning-$(basename "$document" .md)")"
  mkdir -p "$repo/docs/changes"
  printf '\nChanged by a feature.\n' >>"$repo/$document"
  check "$repo" --planning
  [[ "$status" -eq 1 ]] || fail "a feature branch that changes $document was not reported"
  grep -Fq "$document" "$repo.out" || fail "the changed $document was not named"
done

# Removing the approval, or replacing its fingerprint by hand, is drift too.
repo="$(setup_planned planning-approval-removed)"
git -C "$repo" rm -q docs/PLANNING_APPROVAL.md
check "$repo" --planning
[[ "$status" -eq 1 ]] || fail "a feature branch that removes the approval was not reported"
repo="$(setup_planned planning-approval-edited)"
sed -i.bak 's/^Planning fingerprint: .*/Planning fingerprint: 0000000000000000000000000000000000000000/' "$repo/docs/PLANNING_APPROVAL.md"
rm "$repo/docs/PLANNING_APPROVAL.md.bak"
check "$repo" --planning
[[ "$status" -eq 1 ]] || fail "a feature branch that breaks the approval's fingerprint was not reported"

# An amended approval, current for the change, passes.
repo="$(setup_planned planning-amended)"
printf '\n*Note of the owner'"'"'s decision of 2026-11-13 (https://github.com/o/r/issues/5#issuecomment-1).* Kept.\n' >>"$repo/docs/roadmap.md"
(cd "$repo" && printf 'y\n' | PATH="/usr/bin:/bin:$(dirname "$(command -v jq)")" ./scripts/finish-planning.sh --amend "Record the decision.") >"$repo.amend" 2>&1 || {
  cat "$repo.amend" >&2
  fail "the amendment in the guardrails test failed"
}
check "$repo" --planning
[[ "$status" -eq 0 ]] || { cat "$repo.out" >&2; fail "an amended planning change was reported as drift"; }
grep -Fq "The planning approval is current for them" "$repo.out" || fail "the current approval was not reported"

# A project without an approved planning has nothing to drift from.
repo="$(setup_repo planning-none)"
printf '# Roadmap\n' >"$repo/docs/roadmap.md"
check "$repo" --planning
[[ "$status" -eq 0 ]] || fail "a project without a planning approval was reported"

echo "guardrails tests passed"
