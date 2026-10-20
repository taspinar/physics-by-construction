#!/usr/bin/env bash

set -euo pipefail

# Retrieves the verified base of a pull request run (ADR 014 decision 2).
#
# Usage: fetch-base.sh [--run <id>] <directory>
#
# Looks for the base among the artifacts of earlier runs of this workflow and
# accepts one only by the record of the run that produced it, read from the
# runs API: the run is a `push` run of ci.yml on `refs/heads/main` of this
# repository that completed with success, its aggregate job `verify`
# concluded with success, and it holds exactly one unexpired artifact named
# verification-base whose recorded digest is the digest of what was
# downloaded. The name of an artifact, its recency, and its contents decide
# nothing: a pull request run, a fork, or a failed main run is never
# accepted, whatever it uploaded.
#
# The record names the branch only by its short name, and a tag push records
# the tag's name there: a tag named main reads like the branch. The full ref
# is therefore established from the repository and from the run itself. The
# commit the run checked out must be on the history of refs/heads/main (the
# compare API), so a commit that never reached main, with whatever ci.yml it
# carries, is never a base; no tag refs/tags/main may exist; and the base
# must hold provenance.json, which collect-base.sh writes from the run's own
# GITHUB_REF, naming refs/heads/main, the commit and the run the runs API
# checked. That record is trusted only because the commit is on main: its
# ci.yml is the reviewed one, which writes the true ref. A tag push of a
# commit on main, even one whose tag was deleted since, names refs/tags/main
# there and is rejected; a base without the record is rejected too. The
# record can only reject a base, never make one acceptable.
#
# A base that was already retrieved is not downloaded again (ADR 020
# decision 7) when the run these checks choose is the run it came from: every
# check above is made as always, and the choice of the run is theirs alone.
# The download is skipped only when <directory>.fetched records that run, the
# digest of its artifact, and the digest of the contents unpacked from it,
# <directory> still has exactly those contents (every name and every file's
# digest), and <directory>/provenance.json names the run and its commit. A
# base changed after its retrieval is fetched again. Recency never decides; a
# base from any other run is replaced, and without an accepted base both are
# removed.
#
# --run <id> names the producing run; the same checks apply to it. The jobs
# that check a built site use it to take the very base the build job took.
#
# The archive is data. It is unpacked only when every name in it is a plain
# relative path and it holds no link; nothing in it is executed or read as
# configuration here. A base that is missing, rejected, or damaged is not an
# error: the script says why, leaves <directory> absent, and the run verifies
# everything. With GITHUB_OUTPUT set it writes accepted=true|false and
# run-id=<id>.
#
# Needs the tools gh, jq, unzip and sha256sum (or shasum). In CI the
# environment variables GH_TOKEN and GITHUB_REPOSITORY name the token and the
# repository. On a developer's machine (the targeted run, ADR 017 decision 7)
# both may be absent: the repository is then the one of this clone, as gh
# reports it, and the login of gh is used, read-only. Without a login or a
# repository there is no base, and the caller says that CI will run
# everything; nothing is ever guessed.

workflow_path=".github/workflows/ci.yml"
artifact_name="verification-base"
max_bytes=$((2 * 1024 * 1024 * 1024))

fail() {
  echo "Error: $*" >&2
  exit 2
}

run_id=""
if [[ "${1:-}" == "--run" ]]; then
  [[ $# -ge 2 ]] || fail "usage: $0 [--run <id>] <directory>"
  run_id="$2"
  [[ "$run_id" =~ ^[0-9]+$ ]] || fail "the run id must be a number."
  shift 2
fi
[[ $# -eq 1 ]] || fail "usage: $0 [--run <id>] <directory>"
target="$1"
# The record of the base in <directory>: the run and the artifact digest.
fetched_record="${target%/}.fetched"

for tool in gh jq unzip; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool is required."
done
if command -v sha256sum >/dev/null 2>&1; then
  sum=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
  sum=(shasum -a 256)
else
  fail "sha256sum or shasum is required."
fi
scratch="$(mktemp -d "${TMPDIR:-/tmp}/fetch-base.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT

# The digest of the contents of directory $1: the sorted names of its
# directories and the digest of each file under its name. Fails when it holds
# anything other than files and directories.
contents_digest() {
  [[ -d "$1" && -z "$(find "$1" ! -type f ! -type d -print -quit)" ]] || return 1
  (
    cd "$1" || exit 1
    find . -type d -print0 | LC_ALL=C sort -z | tr '\0' '\n'
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 "${sum[@]}"
  ) | "${sum[@]}" | cut -d' ' -f1
}

output() {
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s\n' "$@" >>"$GITHUB_OUTPUT"
  fi
}

# Without a base the run verifies everything. Says why, and why only.
without_base() {
  echo "No base: $1. Every lesson is executed and checked."
  rm -rf "$target" "$fetched_record"
  output "accepted=false" "run-id="
  exit 0
}

api() {
  gh api -H "Accept: application/vnd.github+json" "$1"
}

# The repository and the credentials: from the environment in CI, from the
# clone and the login of gh on a developer's machine.
repo="${GITHUB_REPOSITORY:-}"
if [[ -z "$repo" ]]; then
  repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)" ||
    without_base "the repository cannot be determined (set GITHUB_REPOSITORY, or run in a clone whose remote is on GitHub)"
fi
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail "GITHUB_REPOSITORY is not set to owner/name."
if [[ -z "${GH_TOKEN:-}" ]]; then
  gh auth status >/dev/null 2>&1 ||
    without_base "GH_TOKEN is not set and gh is not logged in (run gh auth login)"
fi

# Whether the record of one run, in $scratch/run.json, is a run whose
# artifacts may be a base. Sets $why when it is not.
why=""
acceptable_run() {
  local file="$1"
  why="$(jq -r --arg repo "$repo" --arg path "$workflow_path" '
    if type != "object" then "the run record is not an object"
    elif .event != "push" then "the run is a \(.event // "unknown") run, not a push run"
    elif .head_branch != "main" then "the run is on the branch \(.head_branch // "unknown"), not main"
    elif (.head_repository.full_name // "") != $repo then "the run is from another repository"
    elif (.repository.full_name // "") != $repo then "the run is of another repository"
    elif .path != $path then "the run is of the workflow \(.path // "unknown"), not ci.yml"
    elif .status != "completed" then "the run has not completed"
    elif .conclusion != "success" then "the run concluded with \(.conclusion // "no result")"
    else "" end' "$file" 2>/dev/null)" || why="the run record cannot be read"
  [[ -z "$why" ]]
}

# Whether the commit of the run, in $scratch/run.json, is on the history of
# main: the merge base of the two is that commit itself.
on_main() {
  local sha
  sha="$(jq -r '.head_sha // ""' "$scratch/run.json" 2>/dev/null)" || return 1
  [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || return 1
  api "repos/$repo/compare/$main_sha...$sha?per_page=1" >"$scratch/compare.json" 2>/dev/null || return 1
  jq -e --arg sha "$sha" '(.status == "identical" or .status == "behind")
                          and .merge_base_commit.sha == $sha' \
    "$scratch/compare.json" >/dev/null 2>&1
}

# Whether the aggregate job of run $1 concluded with success.
verify_succeeded() {
  api "repos/$repo/actions/runs/$1/jobs?filter=latest&per_page=100" >"$scratch/jobs.json" 2>/dev/null || return 1
  jq -e '[.jobs[]? | select(.name == "verify")]
         | length == 1 and .[0].status == "completed" and .[0].conclusion == "success"' \
    "$scratch/jobs.json" >/dev/null 2>&1
}

# Writes the one usable artifact of run $1 to $scratch/artifact.json.
artifact_of() {
  api "repos/$repo/actions/runs/$1/artifacts?name=$artifact_name&per_page=100" >"$scratch/artifacts.json" 2>/dev/null || return 1
  jq -e --arg name "$artifact_name" --argjson run "$1" --argjson max "$max_bytes" '
    [.artifacts[]? | select(.name == $name)] as $found
    | ($found | length) == 1
      and ($found[0].expired == false)
      and ($found[0].workflow_run.id == $run)
      and ($found[0].workflow_run.head_branch == "main")
      and (($found[0].size_in_bytes // 0) > 0 and $found[0].size_in_bytes <= $max)
      and (($found[0].digest // "") | test("^sha256:[0-9a-f]{64}$"))' \
    "$scratch/artifacts.json" >/dev/null 2>&1 || return 1
  jq -c --arg name "$artifact_name" '[.artifacts[] | select(.name == $name)][0]' \
    "$scratch/artifacts.json" >"$scratch/artifact.json"
}

candidates=()
if [[ -n "$run_id" ]]; then
  candidates=("$run_id")
else
  api "repos/$repo/actions/workflows/ci.yml/runs?branch=main&event=push&status=success&per_page=20" >"$scratch/runs.json" 2>/dev/null ||
    without_base "the runs of earlier pushes to main cannot be listed"
  while IFS= read -r id; do
    [[ "$id" =~ ^[0-9]+$ ]] && candidates+=("$id")
  done < <(jq -r '.workflow_runs[]?.id' "$scratch/runs.json" 2>/dev/null || true)
fi
[[ ${#candidates[@]} -gt 0 ]] || without_base "no earlier push to main has a successful run"

# The commit of refs/heads/main, read by its full ref. A tag of that name makes
# the short name of a run record ambiguous, so there is no base while one
# exists.
api "repos/$repo/git/ref/heads/main" >"$scratch/main.json" 2>/dev/null ||
  without_base "the branch main cannot be read"
main_sha="$(jq -r 'if .ref == "refs/heads/main" and .object.type == "commit"
                   then .object.sha else "" end' "$scratch/main.json" 2>/dev/null || true)"
[[ "$main_sha" =~ ^[0-9a-f]{40}$ ]] || without_base "the ref refs/heads/main is not a commit"
api "repos/$repo/git/matching-refs/tags/main" >"$scratch/tags.json" 2>/dev/null ||
  without_base "the tags named main cannot be listed"
jq -e 'type == "array"' "$scratch/tags.json" >/dev/null 2>&1 ||
  without_base "the tags named main cannot be listed"
jq -e 'all(.[]; .ref != "refs/tags/main")' "$scratch/tags.json" >/dev/null 2>&1 ||
  without_base "a tag named main exists, so a run record cannot tell it from the branch"

chosen=""
chosen_sha=""
reasons=()
for id in "${candidates[@]}"; do
  api "repos/$repo/actions/runs/$id" >"$scratch/run.json" 2>/dev/null || {
    reasons+=("run $id: the record cannot be read")
    continue
  }
  if ! acceptable_run "$scratch/run.json"; then
    reasons+=("run $id: $why")
    continue
  fi
  if ! on_main; then
    reasons+=("run $id: its commit is not on the history of refs/heads/main")
    continue
  fi
  if ! verify_succeeded "$id"; then
    reasons+=("run $id: the job verify did not conclude with success")
    continue
  fi
  if ! artifact_of "$id"; then
    reasons+=("run $id: it has no single unexpired $artifact_name with a digest")
    continue
  fi
  chosen="$id"
  chosen_sha="$(jq -r '.head_sha' "$scratch/run.json")"
  break
done
if [[ ${#reasons[@]} -gt 0 ]]; then
  printf 'Rejected: %s\n' "${reasons[@]}" >&2
fi
if [[ -z "$chosen" ]]; then
  without_base "no run offers a base that passes the provenance checks"
fi

artifact_id="$(jq -r '.id' "$scratch/artifact.json")"
[[ "$artifact_id" =~ ^[0-9]+$ ]] || without_base "the artifact record has no id"
expected="$(jq -r '.digest' "$scratch/artifact.json")"
expected="${expected#sha256:}"

# The accepted run is the one whose base is already here: not fetched again.
if [[ -f "$fetched_record" && -f "$target/provenance.json" ]] &&
  [[ "$(sed -n 's/^run-id=//p' "$fetched_record")" == "$chosen" ]] &&
  [[ "$(sed -n 's/^artifact-digest=//p' "$fetched_record")" == "$expected" ]] &&
  recorded_contents="$(sed -n 's/^contents-digest=//p' "$fetched_record")" &&
  [[ "$recorded_contents" =~ ^[0-9a-f]{64}$ ]] &&
  [[ "$(contents_digest "$target" 2>/dev/null)" == "$recorded_contents" ]] &&
  jq -e --arg sha "$chosen_sha" --argjson run "$chosen" '
    type == "object" and .ref == "refs/heads/main" and .sha == $sha and .run_id == $run' \
    "$target/provenance.json" >/dev/null 2>&1; then
  echo "Base accepted: the artifact of the push run $chosen on main, whose job verify succeeded; it is the base already retrieved, so it was not fetched again."
  output "accepted=true" "run-id=$chosen"
  exit 0
fi
rm -f "$fetched_record"

api "repos/$repo/actions/artifacts/$artifact_id/zip" >"$scratch/base.zip" 2>/dev/null ||
  without_base "the artifact of run $chosen cannot be downloaded"
found="$("${sum[@]}" "$scratch/base.zip" | cut -d' ' -f1)"
[[ "$found" == "$expected" ]] ||
  without_base "the download of run $chosen is not the archive that was recorded (digest differs)"

# Names first: a plain relative path, no link, nothing outside the archive.
names="$(unzip -Z1 "$scratch/base.zip" 2>/dev/null)" || without_base "the archive is empty or not readable"
[[ -n "$names" ]] || without_base "the archive is empty or not readable"
while IFS= read -r name; do
  case "$name" in
  /* | *../* | ../* | *'\'* | *$'\n'*) without_base "the archive holds the path $name" ;;
  esac
done <<<"$names"
# Not a pipe into 'grep -q': grep stops at the first link, unzip then gets
# SIGPIPE, and under pipefail a listing longer than a pipe buffer made the
# condition false although the archive holds a link.
listing="$(unzip -Z "$scratch/base.zip" 2>/dev/null)" || without_base "the archive cannot be listed"
if grep -q '^l' <<<"$listing"; then
  without_base "the archive holds a link"
fi

stage="$scratch/stage"
mkdir "$stage"
unzip -q "$scratch/base.zip" -d "$stage" 2>/dev/null || without_base "the archive cannot be unpacked"
if [[ -n "$(find "$stage" ! -type f ! -type d -print -quit)" ]]; then
  without_base "the archive holds something other than files"
fi

# Complete: the three parts of a base, the two records as JSON objects. Their
# format is checked by the selection, which runs every lesson on a format it
# does not know.
[[ -d "$stage/freeze" && -n "$(find "$stage/freeze" -type f -print -quit)" ]] ||
  without_base "the base holds no stored results"
for record in digests.json pages.json; do
  [[ -f "$stage/$record" ]] || without_base "the base holds no $record"
  jq -e 'type == "object"' "$stage/$record" >/dev/null 2>&1 ||
    without_base "$record is not a JSON object"
done

# The full ref of the run that collected the base, as that run recorded it.
[[ -f "$stage/provenance.json" ]] ||
  without_base "the base holds no provenance.json, so the ref of its run is not established"
jq -e --arg sha "$chosen_sha" --argjson run "$chosen" '
  type == "object" and .ref == "refs/heads/main" and .sha == $sha and .run_id == $run' \
  "$stage/provenance.json" >/dev/null 2>&1 ||
  without_base "provenance.json of run $chosen does not name refs/heads/main, its commit, and the run"

rm -rf "$target"
mkdir -p "$(dirname "$target")"
mv "$stage" "$target"
contents="$(contents_digest "$target")" || without_base "the contents of the base cannot be read"
printf 'run-id=%s\nartifact-digest=%s\ncontents-digest=%s\n' "$chosen" "$expected" "$contents" >"$fetched_record"
echo "Base accepted: the artifact of the push run $chosen on main, whose job verify succeeded."
output "accepted=true" "run-id=$chosen"
