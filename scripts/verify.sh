#!/usr/bin/env bash

set -euo pipefail

# Stable verification entry point for humans, agents, and CI.
# The required checks of the project are declared in scripts/verify.conf.
# The self-tests of the workflow scripts are declared in
# scripts/verify-workflow.conf and run only when a workflow file changed,
# or always with --all.
#
# A run in which every check passed is recorded for the content it verified
# (scripts/lib/verification.sh). With --reuse, a second run on identical
# content is skipped.
#
# A check may name a group: '<name> [<group>]: <command>'. A check without one
# belongs to the group 'default'. --only runs the checks of the named groups,
# for a CI that spreads the same checks over parallel jobs. Such a partial
# run is never a verification: it records nothing.
#
# A full run of CI spreads the group 'build' over same-machine lesson shards
# (ADR 014 decision 11). --shard k/N runs that group on the k-th share of the
# lessons, which the script derives from the lesson count; --assemble renders
# the one site from the parts the shards made. Both are partial runs.

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
config="$root/scripts/verify.conf"
workflow_config="$root/scripts/verify-workflow.conf"

comment_pattern='^[[:space:]]*(#.*)?$'
check_pattern='^([a-z0-9][a-z0-9-]*)([[:space:]]*\[([a-z0-9][a-z0-9-]*)\])?:[[:space:]]*(.*[^[:space:]])[[:space:]]*$'
default_group="default"

usage() {
  echo "Usage: $0 [--all] [--reuse]"
  echo "       $0 [--all] --base <directory> [--only <group>[,<group>...]]"
  echo "       $0 [--all] --only <group>[,<group>...]"
  echo "       $0 [--all] [--base <directory>] --shard <k>/<N>"
  echo "       $0 [--all] --assemble <parts-directory>"
  echo "       $0 --groups"
  echo "       $0 --shards"
  echo
  echo "Runs the checks in scripts/verify.conf. The workflow self-tests in"
  echo "scripts/verify-workflow.conf run only when a file listed under 'paths:' in"
  echo "that file differs from the base branch. --all runs them regardless."
  echo
  echo "--reuse skips the run when verification already passed for exactly the"
  echo "current content, as recorded by an earlier run."
  echo
  echo "--only runs the checks of the named groups only. A check names its group"
  echo "as '<name> [<group>]: <command>'; one without a group is in 'default'."
  echo "A partial run records nothing and cannot be combined with --reuse: only"
  echo "a run of every check verifies the content."
  echo
  echo "--base names the directory of a verified base (digests.json and freeze/, as"
  echo "a run on main publishes them). The script selects once what this run"
  echo "executes and checks, writes the selection to .agents/verification/selection.json,"
  echo "and records the base. Without it every lesson is executed and checked. A"
  echo "base that cannot be used gives a full run, with the reason (ADR 014)."
  echo
  echo "--shard runs the group 'build' on the k-th lesson shard: a share of the lessons"
  echo "that this script derives from their count (at most the 'shard-size' of"
  echo "scripts/verify.conf per shard; N is derived, never given freely). It leaves a part"
  echo "in .agents/verification/part for the assembly. --assemble verifies the parts"
  echo "of every shard (a directory holding one directory per part), renders the one"
  echo "site from them without executing a lesson, and compares each lesson page with"
  echo "the page its shard made. Both are partial runs: they record nothing, cannot be"
  echo "combined with --reuse, and verify nothing by themselves."
  echo
  echo "--groups prints the groups that have a check, one per line."
  echo "--shards prints the numbers of the lesson shards of this tree, one per line."
  exit 1
}

config_fail() {
  echo "Error: $*" >&2
  echo "Declare required checks as '<name>: <command>' or '<name> [<group>]: <command>'." >&2
  exit 1
}

run_all=0
reuse=0
list_groups=0
list_shards=0
only=""
partial=0
base=""
shard=""
assemble=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) run_all=1 ;;
    --reuse) reuse=1 ;;
    --groups) list_groups=1 ;;
    --shards) list_shards=1 ;;
    --shard)
      [[ $# -ge 2 && "$2" =~ ^[0-9]+/[0-9]+$ ]] || usage
      shard="$2"
      partial=1
      shift
      ;;
    --assemble)
      [[ $# -ge 2 && -n "$2" ]] || usage
      assemble="$2"
      partial=1
      shift
      ;;
    --base)
      [[ $# -ge 2 && -n "$2" ]] || usage
      base="$2"
      shift
      ;;
    --only)
      [[ $# -ge 2 && "$2" =~ ^[a-z0-9][a-z0-9-]*(,[a-z0-9][a-z0-9-]*)*$ ]] || usage
      only="$2"
      partial=1
      shift
      ;;
    *) usage ;;
  esac
  shift
done
# The two lesson-shard modes run the group 'build' and nothing else.
if [[ -n "$shard" || -n "$assemble" ]]; then
  [[ -z "$shard" || -z "$assemble" ]] ||
    { echo "Error: --shard and --assemble cannot be combined." >&2; exit 1; }
  [[ -z "$only" || "$only" == "build" ]] ||
    { echo "Error: --shard and --assemble run the group build; --only $only cannot be combined with them." >&2; exit 1; }
  [[ -z "$assemble" || -z "$base" ]] ||
    { echo "Error: --assemble takes no --base: the selection is made against the parts." >&2; exit 1; }
  only="build"
  if [[ -n "$assemble" ]]; then
    [[ -d "$assemble" ]] || { echo "Error: --assemble names $assemble, which is not a directory of parts." >&2; exit 1; }
    assemble="$(cd "$assemble" && pwd -P)"
  fi
fi
if [[ -n "$base" && "$reuse" -eq 1 ]]; then
  echo "Error: --base cannot be combined with --reuse: a run with a base is a verification against that base, not of the content alone." >&2
  exit 1
fi
if [[ "$partial" -eq 1 && "$reuse" -eq 1 ]]; then
  echo "Error: --only, --shard, and --assemble cannot be combined with --reuse: a partial run is not a verification, so there is nothing to reuse." >&2
  exit 1
fi
if [[ "$list_groups" -eq 1 && "$list_shards" -eq 1 ]]; then usage; fi
if [[ ( "$list_groups" -eq 1 || "$list_shards" -eq 1 ) && ( "$partial" -eq 1 || "$reuse" -eq 1 || "$run_all" -eq 1 || -n "$base" ) ]]; then
  usage
fi

# A passed run is recorded only where the record is a file that Git ignores.
recordable=0
scratch=""
for library in fingerprint verification; do
  [[ -f "$root/scripts/lib/$library.sh" ]] || continue
  source "$root/scripts/lib/$library.sh"
done
if declare -F verification_recordable >/dev/null && declare -F fingerprint_worktree >/dev/null &&
  verification_recordable "$root"; then
  recordable=1
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/verify.XXXXXX")"
  trap 'rm -rf "$scratch"' EXIT
fi

names=()
commands=()
groups=()
workflow_paths=""

# load_checks <file> <paths-entry>
# Appends the checks of <file> to names and commands. With <paths-entry> 'yes',
# the reserved entry 'paths:' sets workflow_paths instead of declaring a check.
load_checks() {
  local file="$1"
  local paths_entry="$2"
  local label="${1#"$root"/}"
  local line
  local line_number=0
  local name
  local group
  local value
  local existing

  while IFS= read -r line || [[ -n "$line" ]]; do
    line_number=$((line_number + 1))
    [[ "$line" =~ $comment_pattern ]] && continue
    [[ "$line" =~ $check_pattern ]] ||
      config_fail "malformed check on line $line_number of $label: $line"

    name="${BASH_REMATCH[1]}"
    group="${BASH_REMATCH[3]}"
    value="${BASH_REMATCH[4]}"
    # The size of a lesson shard is declared in verify.conf; it is no check.
    if [[ "$file" == "$config" && "$name" == "shard-size" ]]; then
      [[ -z "$group" && "$value" =~ ^[1-9][0-9]*$ ]] ||
        config_fail "'shard-size' takes a number of lessons and no group on line $line_number of $label."
      continue
    fi
    if [[ "$paths_entry" == "yes" && "$name" == "paths" ]]; then
      [[ -z "$group" ]] || config_fail "'paths' takes no group on line $line_number of $label."
      [[ -z "$workflow_paths" ]] ||
        config_fail "'paths' is declared more than once in $label."
      workflow_paths="$value"
      continue
    fi
    for existing in ${names[@]+"${names[@]}"}; do
      [[ "$existing" != "$name" ]] ||
        config_fail "duplicate check name on line $line_number of $label: $name"
    done
    names+=("$name")
    commands+=("$value")
    groups+=("${group:-$default_group}")
  done <"$file"
}

# in_list <value> <comma-separated-list>
in_list() {
  [[ ",$2," == *",$1,"* ]]
}

# workflow_files_changed
# Exits 0 when a file under workflow_paths differs from the base branch,
# counting uncommitted and untracked files, 1 when none does, and 2 when that
# cannot be determined. Sets workflow_base to the base branch used.
workflow_files_changed() {
  local specs=()
  local ref
  local base=""
  local changed

  read -r -a specs <<<"$workflow_paths"
  command -v git >/dev/null 2>&1 || return 2
  git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 2
  for ref in origin/main main; do
    if base="$(git -C "$root" merge-base "$ref" HEAD 2>/dev/null)" && [[ -n "$base" ]]; then
      workflow_base="$ref"
      break
    fi
    base=""
  done
  [[ -n "$base" ]] || return 2

  changed="$(
    git -C "$root" diff --name-only "$base" -- "${specs[@]}" &&
      git -C "$root" ls-files --others --exclude-standard -- "${specs[@]}"
  )" || return 2
  [[ -n "$changed" ]]
}

# The lesson shards of this tree: derived from the lesson count and the size
# declared in scripts/verify.conf, read from no other file.
if [[ "$list_shards" -eq 1 ]]; then
  (cd "$root" && uv run --locked python -m pbc.authoring.shards --root "$root" matrix) |
    tr -d '[],' | tr ' ' '\n'
  exit "${PIPESTATUS[0]}"
fi

[[ "$list_groups" -eq 1 ]] || echo "== Agentic project verification =="

[[ -f "$config" ]] || config_fail "verification config not found: $config"
load_checks "$config" no
[[ "${#names[@]}" -gt 0 ]] || config_fail "scripts/verify.conf declares no checks."

# Decide whether the workflow self-tests run. Their checks follow the project
# checks; a project without scripts/verify-workflow.conf has none.
project_count="${#names[@]}"
workflow_note=""
workflow_skipped=""
workflow_base=""
if [[ -f "$workflow_config" ]]; then
  load_checks "$workflow_config" yes
  workflow_count=$((${#names[@]} - project_count))
  [[ "$workflow_count" -gt 0 ]] || config_fail "scripts/verify-workflow.conf declares no checks."
  [[ -n "$workflow_paths" ]] ||
    config_fail "scripts/verify-workflow.conf must declare the workflow files as 'paths: <pathspec>...'."

  if [[ "$run_all" -eq 1 ]]; then
    workflow_note="requested with --all"
  else
    changed_status=0
    workflow_files_changed || changed_status=$?
    case "$changed_status" in
      0) workflow_note="a workflow file differs from $workflow_base" ;;
      1) workflow_skipped="SKIP  workflow self-tests ($workflow_count checks): no workflow file differs from $workflow_base; --all runs them" ;;
      *) workflow_note="could not determine whether a workflow file changed" ;;
    esac
  fi
fi

# The groups that have a check, in the order of their first check.
known_groups=""
for group in "${groups[@]}"; do
  in_list "$group" "$known_groups" || known_groups="${known_groups:+$known_groups,}$group"
done
if [[ "$list_groups" -eq 1 ]]; then
  printf '%s\n' "${known_groups//,/$'\n'}"
  exit 0
fi
if [[ "$partial" -eq 1 ]]; then
  IFS=, read -r -a wanted <<<"$only"
  for group in "${wanted[@]}"; do
    in_list "$group" "$known_groups" ||
      config_fail "no check is in the group '$group'. The groups are: ${known_groups//,/, }."
  done
  echo "Only the groups: ${only//,/, }. A partial run is not a verification and records nothing."
fi

# The selection of the run (ADR 014 decision 5): made once, here, and written
# to the one file the checks read. A run without --base removes any selection
# an earlier run left, so that it verifies everything.
selection_file="$root/.agents/verification/selection.json"
shard_file="$root/.agents/verification/shard.json"
assembly_dir="$root/.agents/verification/assembly"
part_dir="${PBC_PART_DIR:-$root/.agents/verification/part}"
if [[ -e "$selection_file" ]]; then rm -f "$selection_file"; fi
# Likewise the shard of an earlier run, and what an earlier shard or assembly left.
for leftover in "$shard_file" "$assembly_dir" "$root/.agents/verification/part"; do
  if [[ -e "$leftover" ]]; then rm -rf "$leftover"; fi
done
selection_note=""
if [[ -n "$shard" ]]; then
  (cd "$root" && uv run --locked python -m pbc.authoring.shards --root "$root" write "$shard") ||
    { echo "Error: the lesson shard $shard cannot be run." >&2; exit 1; }
fi
if [[ -n "$assemble" ]]; then
  # The parts are data: they are verified as such, and the selection is made
  # against what they hold. A run that would execute a lesson is no assembly.
  echo "== Assembly of the parts in $assemble =="
  (cd "$root" && uv run --locked python -m pbc.authoring.assemble verify \
    --root "$root" --parts "$assemble" --union "$assembly_dir/union") ||
    { echo "Error: the parts in $assemble cannot be assembled." >&2; exit 1; }
  selection_note="assembly of the parts of $assemble"
fi
if [[ -n "$base" ]]; then
  [[ -d "$base" ]] || echo "Note: the base $base is not a directory; the run is a full run."
  base_abs="$(cd "$base" 2>/dev/null && pwd -P || printf '%s' "$base")"
  selection_note="$(cd "$root" && uv run --locked python -m pbc.authoring.selection --root "$root" --base "$base_abs")" ||
    config_fail "the selection against the base $base failed."
  echo "== Selection =="
  echo "$selection_note"
  selection_note="${selection_note%%$'\n'*}"
fi

# With --reuse, a recorded pass for exactly this content stands in for a run.
# A record made without the workflow self-tests does not cover a run that
# needs them.
tree_before=""
if [[ "$recordable" -eq 1 ]]; then
  tree_before="$(fingerprint_worktree "$root" "$scratch")" || tree_before=""
  if [[ "$reuse" -eq 1 && -n "$tree_before" && "$(verification_field "$root" tree)" == "$tree_before" &&
    -z "$(verification_field "$root" selection)" ]]; then
    recorded_workflow="$(verification_field "$root" workflow-tests)"
    if [[ "$recorded_workflow" != "skipped" || ( -n "$workflow_skipped" && "$run_all" -eq 0 ) ]]; then
      echo
      echo "Verification already passed for this content at $(verification_field "$root" verified-at); not run again."
      echo "Run ./scripts/verify.sh without --reuse to run every check."
      exit 0
    fi
  fi
fi

results=()
failed=0
for index in "${!names[@]}"; do
  if [[ "$index" -eq "$project_count" ]]; then
    [[ -z "$workflow_skipped" ]] || break
    echo
    echo "== Workflow self-tests: $workflow_note =="
  fi
  name="${names[$index]}"
  command="${commands[$index]}"
  if [[ "$partial" -eq 1 ]] && ! in_list "${groups[$index]}" "$only"; then
    continue
  fi
  read -r tool _ <<<"$command"

  echo
  echo "-- $name: $command"

  if ! (cd "$root" && command -v "$tool" >/dev/null 2>&1); then
    echo "Error: required check '$name' cannot run; '$tool' is missing or not executable." >&2
    results+=("FAIL  $name (missing tool: $tool)")
    failed=1
    continue
  fi

  set +e
  (cd "$root" && bash -eo pipefail -c "$command")
  status=$?
  set -e

  if [[ "$status" -eq 0 ]]; then
    results+=("PASS  $name")
  else
    echo "Error: required check '$name' failed with status $status." >&2
    results+=("FAIL  $name (exit $status)")
    failed=1
  fi
done

# The part a passed shard hands to the assembly, and the comparison of the
# lesson pages of the assembly with those of the shards that made them.
if [[ "$failed" -eq 0 && -n "$shard" ]]; then
  echo
  echo "-- part: the results of the lesson shard $shard"
  if (cd "$root" && uv run --locked python -m pbc.authoring.assemble part \
    --root "$root" --out "$part_dir"); then
    results+=("PASS  part")
  else
    results+=("FAIL  part")
    failed=1
  fi
fi
if [[ "$failed" -eq 0 && -n "$assemble" ]]; then
  echo
  echo "-- compare: every lesson page equals the page its shard made"
  if (cd "$root" && uv run --locked python -m pbc.authoring.assemble compare \
    --root "$root" --parts "$assemble"); then
    results+=("PASS  compare")
  else
    results+=("FAIL  compare")
    failed=1
  fi
fi

echo
echo "== Verification summary =="
[[ "${#results[@]}" -eq 0 ]] || printf '%s\n' "${results[@]}"
[[ -z "$workflow_skipped" ]] || echo "$workflow_skipped"

if [[ "$failed" -ne 0 ]]; then
  [[ "$recordable" -eq 0 ]] || verification_forget "$root"
  echo "Verification failed." >&2
  exit 1
fi

# A partial run passed its own checks and says nothing about the others: an
# existing record is left as it is, and none is written.
if [[ "$partial" -eq 1 ]]; then
  echo "The checks of the groups ${only//,/, } passed. Not a verification: run ./scripts/verify.sh without --only, --shard, or --assemble for that."
  exit 0
fi

# Record the pass for the content that was verified. When a check changed a
# file, no single content was verified, so nothing is recorded.
if [[ "$recordable" -eq 1 ]]; then
  if [[ -n "$tree_before" && "$(fingerprint_worktree "$root" "$scratch")" == "$tree_before" ]]; then
    if [[ ! -f "$workflow_config" ]]; then
      workflow_state="none"
    elif [[ -n "$workflow_skipped" ]]; then
      workflow_state="skipped"
    else
      workflow_state="ran"
    fi
    verification_write "$root" "$tree_before" "$workflow_state" "$selection_note" ||
      echo "Warning: could not record the passed verification." >&2
  else
    verification_forget "$root"
  fi
fi

echo "Verification passed."
