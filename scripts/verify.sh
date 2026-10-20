#!/usr/bin/env bash

set -euo pipefail

# Stable verification entry point for humans, agents, and CI.
# The required checks of the project are declared in scripts/verify.conf.
# The self-tests of the workflow scripts are declared in
# scripts/verify-workflow.conf and run only when a workflow file changed,
# or always with --all.
#
# A run in which every check passed is recorded for the content it verified
# (scripts/lib/verification.sh), with its tier. With --reuse, a second run on
# identical content is skipped.
#
# A check may name a group: '<name> [<group>]: <command>'. A check without one
# belongs to the group 'default'. --only runs the checks of the named groups,
# for a CI that spreads the same checks over parallel jobs. Such a partial
# run is never a verification: it records nothing.
#
# Three tiers (ADR 017 decision 7): a run without options runs every check;
# --base runs every check against a verified base, which selects the lessons
# to execute; --targeted runs the checks of the groups that the reserved
# entry 'targeted:' of scripts/verify.conf names, after the selection, and
# builds no site. The targeted run never guesses: without an acceptable base,
# or when the selection says CI will run everything, it reports that and
# verifies nothing.
#
# Every run appends one line to a time log (ADR 020 decision 7):
# '<UTC time> | <tier> | <tree> | <seconds> | <result>', with the tier full,
# base, targeted, or only:<groups>, and the result passed, failed, refused,
# or reused. The log is per clone and machine, in the Git directory that
# every worktree of the clone shares (<git common dir>/verify-time.log), or
# where VERIFY_TIME_LOG says; it is never committed, and no gate reads it.
# It is read afterwards, to measure (docs/development.md, "Verification").

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
config="$root/scripts/verify.conf"
workflow_config="$root/scripts/verify-workflow.conf"
fetch_script="$root/scripts/fetch-base.sh"
fetched_base="$root/.agents/verification/base"

comment_pattern='^[[:space:]]*(#.*)?$'
check_pattern='^([a-z0-9][a-z0-9-]*)([[:space:]]*\[([a-z0-9][a-z0-9-]*)\])?:[[:space:]]*(.*[^[:space:]])[[:space:]]*$'
groups_pattern='^[a-z0-9][a-z0-9-]*(,[a-z0-9][a-z0-9-]*)*$'
default_group="default"

usage() {
  echo "Usage: $0 [--all] [--reuse]"
  echo "       $0 [--all] --targeted [--base <directory>] [--reuse]"
  echo "       $0 [--all] --base [<directory>] [--only <group>[,<group>...]]"
  echo "       $0 [--all] --only <group>[,<group>...]"
  echo "       $0 --groups"
  echo
  echo "Runs the checks in scripts/verify.conf. The workflow self-tests in"
  echo "scripts/verify-workflow.conf run only when a file listed under 'paths:' in"
  echo "that file differs from the base branch. --all runs them regardless."
  echo
  echo "--reuse skips the run when verification already passed for exactly the"
  echo "current content, as recorded by an earlier run: a full run, or with"
  echo "--targeted a run of any tier."
  echo
  echo "--only runs the checks of the named groups only. A check names its group"
  echo "as '<name> [<group>]: <command>'; one without a group is in 'default'."
  echo "A partial run records nothing and cannot be combined with --reuse: only"
  echo "a run of every check verifies the content."
  echo
  echo "--base names the directory of a verified base (digests.json and freeze/, as"
  echo "a run on main publishes them). The script selects once what this run"
  echo "executes and checks, writes the selection to .agents/verification/selection.json,"
  echo "and records the base. Without a directory the base is retrieved with"
  echo "scripts/fetch-base.sh into .agents/verification/base. Without a base every"
  echo "lesson is executed and checked. A base that cannot be used gives a full run,"
  echo "with the reason (ADR 014)."
  echo
  echo "--targeted is the targeted run (ADR 017 decision 7): the selection CI will"
  echo "make, from the base, and then the checks of the groups that the entry"
  echo "'targeted:' of scripts/verify.conf names, which need no site build. It"
  echo "builds no site. Without an acceptable base, when the selection names a"
  echo "full run, or when a selected lesson is new to the base, it reports what CI"
  echo "will run and which run the change needs, and verifies nothing. A pass is"
  echo "recorded with its tier, the base, and the selection. A project whose"
  echo "scripts/verify.conf has no 'targeted:' entry has one tier: --targeted then"
  echo "runs every check."
  echo
  echo "--groups prints the groups that have a check, one per line."
  echo
  echo "Every run appends '<time> | <tier> | <tree> | <seconds> | <result>' to the"
  echo "time log, <git common dir>/verify-time.log or \$VERIFY_TIME_LOG; no gate reads it."
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
only=""
partial=0
base=""
fetch_base=0
targeted=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all) run_all=1 ;;
    --reuse) reuse=1 ;;
    --groups) list_groups=1 ;;
    --targeted) targeted=1 ;;
    --base)
      if [[ $# -ge 2 && -n "$2" && "$2" != --* ]]; then
        base="$2"
        shift
      else
        fetch_base=1
      fi
      ;;
    --only)
      [[ $# -ge 2 && "$2" =~ $groups_pattern ]] || usage
      only="$2"
      partial=1
      shift
      ;;
    *) usage ;;
  esac
  shift
done
if [[ ( -n "$base" || "$fetch_base" -eq 1 ) && "$reuse" -eq 1 && "$targeted" -eq 0 ]]; then
  echo "Error: --base cannot be combined with --reuse: a run with a base is a verification against that base, not of the content alone." >&2
  exit 1
fi
if [[ "$partial" -eq 1 && "$reuse" -eq 1 ]]; then
  echo "Error: --only cannot be combined with --reuse: a partial run is not a verification, so there is nothing to reuse." >&2
  exit 1
fi
if [[ "$partial" -eq 1 && "$targeted" -eq 1 ]]; then
  echo "Error: --only cannot be combined with --targeted: the targeted run performs the groups that scripts/verify.conf names for it." >&2
  exit 1
fi
if [[ "$targeted" -eq 1 && "$fetch_base" -eq 1 ]]; then
  echo "Error: --targeted retrieves the base itself; give --base a directory, or leave it out." >&2
  exit 1
fi
if [[ "$list_groups" -eq 1 && ( "$partial" -eq 1 || "$reuse" -eq 1 || "$run_all" -eq 1 || -n "$base" || "$fetch_base" -eq 1 || "$targeted" -eq 1 ) ]]; then
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
fi

# The time log (ADR 020 decision 7): one line per run, written when the run
# ends, whatever ends it. Writing it never changes the outcome of the run,
# also on a machine without a tool it uses: the duration is bash's own clock.
log_started="$SECONDS"
log_tier="full"
if [[ "$partial" -eq 1 ]]; then
  log_tier="only:$only"
elif [[ "$targeted" -eq 1 ]]; then
  log_tier="targeted"
elif [[ -n "$base" || "$fetch_base" -eq 1 ]]; then
  log_tier="base"
fi
log_result=""
log_tree=""
time_log_path() {
  local common

  if [[ -n "${VERIFY_TIME_LOG:-}" ]]; then
    printf '%s\n' "$VERIFY_TIME_LOG"
    return 0
  fi
  command -v git >/dev/null 2>&1 || return 1
  common="$(git -C "$root" rev-parse --git-common-dir 2>/dev/null)" || return 1
  [[ -n "$common" ]] || return 1
  [[ "$common" == /* ]] || common="$root/$common"
  [[ -d "$common" ]] || return 1
  printf '%s/verify-time.log\n' "$common"
}
write_time_log() {
  local status="$1"
  local log
  local tree="${log_tree:-${tree_before:-}}"
  local dir
  local now

  # Nothing here may fail the run or change its exit status.
  set +e
  if [[ "$list_groups" -eq 0 ]] && log="$(time_log_path)"; then
    if [[ -z "$tree" ]] && declare -F fingerprint_worktree >/dev/null; then
      dir="$(mktemp -d "${TMPDIR:-/tmp}/verify-log.XXXXXX")" &&
        tree="$(fingerprint_worktree "$root" "$dir" 2>/dev/null)" || tree=""
      [[ -z "${dir:-}" ]] || rm -rf "$dir"
    fi
    [[ -n "$log_result" ]] || { if [[ "$status" -eq 0 ]]; then log_result="passed"; else log_result="failed"; fi; }
    now="$(date -u +'%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"
    { [[ -n "$now" ]] && mkdir -p "$(dirname "$log")"; } 2>/dev/null &&
      printf '%s | %s | %s | %s | %s\n' "$now" "$log_tier" "${tree:--}" \
        "$((SECONDS - log_started))" "$log_result" >>"$log" 2>/dev/null
  fi
  [[ -z "$scratch" ]] || rm -rf "$scratch" 2>/dev/null
  return 0
}
trap 'write_time_log $?' EXIT

names=()
commands=()
groups=()
workflow_paths=""
targeted_groups=""

# load_checks <file> <reserved-entry>
# Appends the checks of <file> to names and commands. <reserved-entry> names
# the one entry of the file that declares no check: 'paths' sets
# workflow_paths (the workflow files), 'targeted' sets targeted_groups (the
# groups of the targeted run), and 'none' reserves nothing.
load_checks() {
  local file="$1"
  local reserved="$2"
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
    if [[ "$reserved" != "none" && "$name" == "$reserved" ]]; then
      [[ -z "$group" ]] || config_fail "'$reserved' takes no group on line $line_number of $label."
      case "$reserved" in
        paths)
          [[ -z "$workflow_paths" ]] ||
            config_fail "'paths' is declared more than once in $label."
          workflow_paths="$value"
          ;;
        targeted)
          [[ -z "$targeted_groups" ]] ||
            config_fail "'targeted' is declared more than once in $label."
          [[ "$value" =~ $groups_pattern ]] ||
            config_fail "'targeted' names groups as '<group>[,<group>...]' on line $line_number of $label: $value"
          targeted_groups="$value"
          ;;
      esac
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

[[ "$list_groups" -eq 1 ]] || echo "== Agentic project verification =="

[[ -f "$config" ]] || config_fail "verification config not found: $config"
load_checks "$config" targeted
[[ "${#names[@]}" -gt 0 ]] || config_fail "scripts/verify.conf declares no checks."

# Decide whether the workflow self-tests run. Their checks follow the project
# checks; a project without scripts/verify-workflow.conf has none.
project_count="${#names[@]}"
workflow_note=""
workflow_skipped=""
workflow_base=""
if [[ -f "$workflow_config" ]]; then
  load_checks "$workflow_config" paths
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

# The tier of this run (ADR 017 decision 7). The targeted run performs the
# groups of the 'targeted:' entry after the selection; a project without the
# entry has one tier, and --targeted runs every check (a full run, recorded
# as one; --reuse still takes a recorded pass of any tier for it).
tier="full"
selected_groups=""
if [[ "$targeted" -eq 1 ]]; then
  if [[ -z "$targeted_groups" ]]; then
    echo "The targeted run: scripts/verify.conf declares no 'targeted:' entry, so this project has one tier and every check runs."
  else
    IFS=, read -r -a wanted <<<"$targeted_groups"
    for group in "${wanted[@]}"; do
      in_list "$group" "$known_groups" ||
        config_fail "the entry 'targeted' of scripts/verify.conf names the group '$group', which has no check. The groups are: ${known_groups//,/, }."
    done
    tier="targeted"
    selected_groups="$targeted_groups"
    [[ -n "$base" ]] || fetch_base=1
    echo "The targeted run (ADR 017 decision 7): the selection CI will make, then the checks of the groups ${targeted_groups//,/, }. No site is built."
  fi
elif [[ -n "$base" || "$fetch_base" -eq 1 ]]; then
  tier="base"
fi
[[ "$partial" -eq 0 ]] || selected_groups="$only"
log_tier="$tier"
[[ "$partial" -eq 0 ]] || log_tier="only:$only"

# With --reuse, a recorded pass for exactly this content stands in for a run:
# a full run, or with --targeted a run of any tier. A record made without the
# workflow self-tests does not cover a run that needs them.
tree_before=""
targeted_record_pending=0
if [[ "$recordable" -eq 1 ]]; then
  tree_before="$(fingerprint_worktree "$root" "$scratch")" || tree_before=""
  if [[ "$reuse" -eq 1 && -n "$tree_before" && "$(verification_field "$root" tree)" == "$tree_before" ]]; then
    recorded_tier="$(verification_tier "$root")"
    if [[ "$recorded_tier" == "full" || "$targeted" -eq 1 ]]; then
      recorded_workflow="$(verification_field "$root" workflow-tests)"
      if [[ "$recorded_workflow" != "skipped" || ( -n "$workflow_skipped" && "$run_all" -eq 0 ) ]]; then
        if [[ "$recorded_tier" == "targeted" ]]; then
          # A targeted pass holds for the selection it was made against: the
          # tree alone does not say what CI selects once main has advanced.
          # It stands only after the current base and selection match it.
          targeted_record_pending=1
        else
          echo
          echo "Verification already passed for this content at $(verification_field "$root" verified-at) (a $recorded_tier run); not run again."
          echo "Run ./scripts/verify.sh without --reuse to run every check."
          log_result="reused"
          exit 0
        fi
      fi
    fi
  fi
fi

# The base of the run, retrieved read-only from the latest successful run on
# main under the same provenance rule as CI (ADR 014 decision 2). Without an
# acceptable base the targeted run cannot tell what CI will execute and
# verifies nothing; a run with --base and no base is a full run.
base_record=""
if [[ "$fetch_base" -eq 1 ]]; then
  [[ -x "$fetch_script" ]] ||
    config_fail "scripts/fetch-base.sh is missing or not executable, so no base can be retrieved; give --base <directory>."
  fetch_output="$(mktemp "${TMPDIR:-/tmp}/verify-base.XXXXXX")"
  echo
  echo "== Base =="
  fetch_status=0
  GITHUB_OUTPUT="$fetch_output" "$fetch_script" "$fetched_base" || fetch_status=$?
  accepted="$(sed -n 's/^accepted=//p' "$fetch_output" | tail -n 1)"
  base_run="$(sed -n 's/^run-id=//p' "$fetch_output" | tail -n 1)"
  rm -f "$fetch_output"
  if [[ "$fetch_status" -ne 0 ]]; then
    echo "No base: scripts/fetch-base.sh exited with status $fetch_status."
    accepted="false"
  fi
  if [[ "$accepted" == "true" && -n "$base_run" && -d "$fetched_base" ]]; then
    base="$fetched_base"
    base_record="run $base_run"
  elif [[ "$tier" == "targeted" ]]; then
    echo "CI will run everything. The targeted run cannot tell what CI will execute, so it verifies nothing; run the full ./scripts/verify.sh."
    echo
    echo "REFUSED  targeted-run (no base: CI will run everything; the change needs the full ./scripts/verify.sh)"
    log_result="refused"
    exit 1
  else
    echo "The run is a full run: every lesson is executed and checked."
    base=""
    tier="full"
    log_tier="full"
  fi
elif [[ -n "$base" ]]; then
  base_record="directory $base"
fi

# The selection of the run (ADR 014 decision 5): made once, here, and written
# to the one file the checks read. A run without a base removes any selection
# an earlier run left, so that it verifies everything.
selection_file="$root/.agents/verification/selection.json"
if [[ -e "$selection_file" ]]; then rm -f "$selection_file"; fi
selection_note=""
if [[ -n "$base" ]]; then
  [[ -d "$base" ]] || echo "Note: the base $base is not a directory; the run is a full run."
  base_abs="$(cd "$base" 2>/dev/null && pwd -P || printf '%s' "$base")"
  tier_options=()
  [[ "$tier" != "targeted" ]] || tier_options=(--tier targeted)
  selection_status=0
  selection_note="$(cd "$root" && uv run --locked python -m pbc.authoring.selection --root "$root" --base "$base_abs" ${tier_options[@]+"${tier_options[@]}"})" ||
    selection_status=$?
  echo
  echo "== Selection =="
  echo "$selection_note"
  if [[ "$selection_status" -eq 3 ]]; then
    # The targeted run does not act on this selection (ADR 017 decision 7):
    # the change needs the full run, or the run with --base, as said above.
    echo "The targeted run verifies nothing for this change."
    echo
    echo "REFUSED  targeted-run (${selection_note##*$'\n'})"
    log_result="refused"
    exit 1
  elif [[ "$selection_status" -ne 0 ]]; then
    config_fail "the selection against the base $base failed."
  fi
  selection_note="${selection_note%%$'\n'*}"
  if [[ "$targeted_record_pending" -eq 1 ]]; then
    if [[ "$(verification_field "$root" base)" == "$base_record" && "$(verification_field "$root" selection)" == "$selection_note" ]]; then
      echo
      echo "Verification already passed for this content at $(verification_field "$root" verified-at) (a targeted run) against this base and selection; not run again."
      echo "Run ./scripts/verify.sh without --reuse to run every check."
      log_result="reused"
      exit 0
    fi
    echo
    echo "The recorded targeted pass was made against another base or selection (base: $(verification_field "$root" base), now $base_record); the targeted checks run again."
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
  if [[ -n "$selected_groups" ]] && ! in_list "${groups[$index]}" "$selected_groups"; then
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
  echo "The checks of the groups ${only//,/, } passed. Not a verification: run ./scripts/verify.sh without --only for that."
  exit 0
fi

# Record the pass for the content that was verified, with its tier. When a
# check changed a file, no single content was verified, so nothing is
# recorded.
if [[ "$recordable" -eq 1 ]]; then
  if [[ -n "$tree_before" && "$(fingerprint_worktree "$root" "$scratch")" == "$tree_before" ]]; then
    if [[ ! -f "$workflow_config" ]]; then
      workflow_state="none"
    elif [[ -n "$workflow_skipped" ]]; then
      workflow_state="skipped"
    else
      workflow_state="ran"
    fi
    verification_write "$root" "$tree_before" "$workflow_state" "$selection_note" "$tier" "$base_record" ||
      echo "Warning: could not record the passed verification." >&2
  else
    verification_forget "$root"
  fi
fi

if [[ "$tier" == "targeted" ]]; then
  echo "The targeted run passed: the checks of the groups ${targeted_groups//,/, }, for the selection above (base: $base_record). No site was built; CI builds and checks the site of the pull request."
  echo "Verification passed (targeted run)."
else
  echo "Verification passed."
fi
