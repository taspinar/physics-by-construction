#!/usr/bin/env bash

set -euo pipefail

# Decides the one required status check of CI from the results of the jobs
# it needs (ADR 012).
#
# Usage: ci-aggregate.sh <job>...
#
# Reads from the environment variable NEEDS the JSON that GitHub gives a job
# about the jobs it needs (the expression toJSON(needs)): an object with, per
# job, its result. Passes only when every job named as an argument is in that
# object with the result "success", and the object holds no other job. A job
# that failed, was cancelled, or was skipped fails the check, and so does a
# job that is named here and not needed, or needed and not named here: the
# list in the workflow file and the jobs it waits for have to be the same.

fail() {
  echo "Error: $*" >&2
  exit 1
}

[[ $# -ge 1 ]] || fail "usage: $0 <job>..."
command -v jq >/dev/null 2>&1 || fail "jq is required."
[[ -n "${NEEDS:-}" ]] || fail "the environment variable NEEDS is empty."
jq -e 'type == "object"' >/dev/null 2>&1 <<<"$NEEDS" ||
  fail "NEEDS is not a JSON object."

problems=0
for job in "$@"; do
  result="$(jq -r --arg job "$job" '.[$job].result // "missing"' <<<"$NEEDS")"
  if [[ "$result" == "success" ]]; then
    echo "ok       $job"
  else
    echo "$(printf '%-8s' "$result") $job" >&2
    problems=$((problems + 1))
  fi
done

while IFS= read -r job; do
  known=0
  for expected in "$@"; do
    [[ "$expected" == "$job" ]] && known=1
  done
  if [[ "$known" -eq 0 ]]; then
    echo "unlisted $job" >&2
    problems=$((problems + 1))
  fi
done < <(jq -r 'keys[]' <<<"$NEEDS")

[[ "$problems" -eq 0 ]] ||
  fail "$problems job(s) did not succeed or are not accounted for; verification failed."
echo "All $# jobs succeeded."
