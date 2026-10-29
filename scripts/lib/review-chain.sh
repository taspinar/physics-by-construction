#!/usr/bin/env bash

# The traceable chain of reviews of a feature (ADR 020 decision 4). Source
# this file after scripts/lib/review-data.sh, scripts/lib/fingerprint.sh,
# scripts/lib/guardrails.sh, and scripts/lib/risk.sh; it needs jq.
#
# Every finding has a stable identifier, its round and its identifier in that
# round: R01-M1. Each review records the tree it compared against
# (compared_tree: the merge base for a review of the complete feature, the
# reviewed tree of the round before for a review of changes) and the tree it
# reviewed, and gives, in dispositions, every earlier open finding as
# resolved or accepted with the evidence, or as open, carried on by a finding
# of the same review that names it in continues. An earlier finding is open
# from its round until a disposition closes it, unless the approved triage of
# its round accepted or deferred it. A review made before this rule (it has
# neither compared_tree nor dispositions) re-reported the findings that were
# not resolved, so the earlier ones end with it; a review made under the rule
# (it has compared_tree) closes only what its dispositions close, and no
# review made before the rule follows one made under it.
#
# A review of changes is allowed only when the reach of the delta is certain
# (review_delta_unbounded); the chain begins with a review of the complete
# feature, and every review of changes builds on the round right before it.
# There is no changed-lines threshold and no general-purpose impact graph.

# The names that load code or run text as code, as the digest knows them
# (src/pbc/authoring/digest.py, _DYNAMIC): a module that uses one can reach
# any other, so its reach is not certain.
REVIEW_CHAIN_DYNAMIC_NAMES=(
  __import__ __builtins__ builtins import_module importlib imp zipimport
  module_from_spec exec_module load_module SourceFileLoader exec eval compile
  runpy run_module run_path pkgutil find_spec spec_from_file_location
)

# review_chain_reviews <root> <slug>
# Prints the review artifacts of the feature branch, one per line, in the
# order of their rounds.
review_chain_reviews() {
  local candidate

  for candidate in "$1/.agents/reviews/$2-review-"[0-9][0-9].json; do
    [[ -f "$candidate" ]] && printf '%s\n' "$candidate"
  done
  return 0
}

# review_chain_open <root> <slug> <before-round>
# Prints, as a JSON array, the findings that are open before the given round:
# {id, round, severity, title, evidence, carried}, where id is the stable
# identifier and carried says that a review already found the finding still
# open. An invalid or unapproved triage decides nothing.
review_chain_open() {
  local root="$1"
  local open='[]'
  local review
  local triage
  local decisions

  while IFS= read -r review; do
    [[ -n "$review" ]] || continue
    [[ "$(jq -r '.round' "$review")" -lt "$3" ]] || break
    decisions='{}'
    triage="$(review_latest_triage "$root" "$review")"
    if [[ -n "$triage" && -z "$(triage_artifact_errors "$triage" "$review")" ]]; then
      decisions="$(jq '.decisions | map({key: .finding_id, value: .decision}) | from_entries' "$triage")"
    fi
    open="$(jq --argjson open "$open" --argjson decisions "$decisions" '
      (.round | tostring | if length < 2 then "0" + . else . end) as $round
      | (if (.dispositions | type) == "array" then
           (.dispositions | map({key: .finding_id, value: .status}) | from_entries) as $status
           | $open | map(select($status[.id] == null))
         elif has("compared_tree") then $open
         else [] end)
      + [.findings[] | select($decisions[.id] | IN("ACCEPT", "DEFER") | not)
         | {id: "R\($round)-\(.id)", round: $round, severity, title, evidence, carried: (.continues != null)}]
    ' "$review")" || return 1
  done < <(review_chain_reviews "$root" "$2")
  printf '%s\n' "$open"
}

# review_chain_dispositioned <root> <slug> <review-json>
# Succeeds when a later review of the feature gives every finding of the
# review as resolved or accepted, so that the chain, not a triage, closes
# them (Issue #326). A finding a later review gives as open, or none gives,
# is not closed this way. Whether the chain holds is checked by the caller.
review_chain_dispositioned() {
  local round
  local ids
  local closed='[]'
  local later

  round="$(jq -r '.round' "$3")"
  ids="$(jq -c '(.round | tostring | if length < 2 then "0" + . else . end) as $round
    | [.findings[] | "R\($round)-\(.id)"]' "$3")" || return 1
  while IFS= read -r later; do
    [[ -n "$later" && "$(jq -r '.round' "$later")" -gt "$round" ]] || continue
    closed="$(jq -c --argjson closed "$closed" '$closed + [.dispositions // [] | .[]? | objects
      | select(.status == "resolved" or .status == "accepted") | .finding_id]' "$later")" || return 1
  done < <(review_chain_reviews "$1" "$2")
  jq -en --argjson ids "$ids" --argjson closed "$closed" '($ids | length) > 0 and ($ids - $closed | length) == 0' >/dev/null
}

# review_chain_disposition_errors <result-json> <open-json-file>
# Prints what is wrong with the dispositions of a result or a review against
# the findings that were open before it, one problem per line.
review_chain_disposition_errors() {
  jq -r --slurpfile open "$2" '
    ([.dispositions // [] | .[]? | objects | .finding_id]) as $given
    | ($open[0] | map(.id)) as $ids
    | ($ids[] | . as $id | select($given | index($id) | not)
       | "the earlier finding \($id) is open and has no disposition; give it as resolved, open, or accepted"),
      ($given[] | . as $id | select($ids | index($id) | not)
       | "\($id) is not an earlier finding that is open; give a disposition only of the findings listed as open")
  ' "$1"
}

# review_chain_baseline <root> <review-json>
# Prints the review of the complete feature that the chain ending at the
# given review begins with, and the reviews of changes on the way, one per
# line, the baseline first. Prints the reason to standard error and fails at
# a gap or a break: a missing or invalid round, a round that does not build
# on the round right before it or on its reviewed tree, a review of the
# complete feature that did not compare against the tree of its merge base,
# or a changed base.
review_chain_baseline() {
  local review="$2"
  local chain=()
  local since
  local round
  local previous
  local stem
  local compared

  while true; do
    [[ -z "$(review_artifact_errors "$review")" ]] || {
      echo "${review#"$1"/} is not a valid review" >&2
      return 1
    }
    chain=("$review" ${chain[@]+"${chain[@]}"})
    if [[ "$(jq -r '.scope.kind // "full"' "$review")" != "changes" ]]; then
      # A review of the complete feature compared against the tree of its
      # merge base; one made before the rule records no compared_tree.
      compared="$(jq -r '.compared_tree // empty' "$review")"
      if [[ -n "$compared" &&
            "$compared" != "$(git -C "$1" rev-parse --verify --quiet "$(jq -r '.merge_base' "$review")^{tree}" 2>/dev/null)" ]]; then
        echo "round $(jq -r '.round' "$review") is a review of the complete feature that did not compare against the tree of its merge base: a break in the chain" >&2
        return 1
      fi
      break
    fi
    round="$(jq -r '.round' "$review")"
    since="$(jq -r '.scope.since_round' "$review")"
    [[ "$since" -eq $((round - 1)) ]] || {
      echo "round $round builds on round $since, not on the round right before it: a gap in the chain" >&2
      return 1
    }
    stem="${review%-review-[0-9][0-9].json}"
    previous="$stem-review-$(printf '%02d' "$since").json"
    [[ -f "$previous" ]] || {
      echo "round $round builds on round $since, which has no review artifact: a gap in the chain" >&2
      return 1
    }
    [[ "$(jq -r '.scope.base_tree' "$review")" == "$(jq -r '.reviewed_tree' "$previous" 2>/dev/null)" &&
       "$(jq -r '.compared_tree // .scope.base_tree' "$review")" == "$(jq -r '.scope.base_tree' "$review")" ]] || {
      echo "round $round did not compare against the tree that round $since reviewed: a break in the chain" >&2
      return 1
    }
    [[ "$(jq -r '.merge_base' "$review")" == "$(jq -r '.merge_base' "$previous")" ]] || {
      echo "the base of the branch changed between round $since and round $round: a break in the chain" >&2
      return 1
    }
    review="$previous"
  done
  printf '%s\n' "${chain[@]}"
}

# review_delta_path_kind <path>
# Prints what a changed path is for the bounded-impact rule: test,
# documentation, lesson, shared (a shared input of ADR 014 decision 4),
# module (a module of src/pbc), or other.
review_delta_path_kind() {
  case "$1" in
    .agents/completion/* | .agents/handoffs/*) echo documentation; return 0 ;;
    tests/* | */test_*.py | test_*.py | *_test.py | *-test.sh) echo test; return 0 ;;
    pyproject.toml | uv.lock | .python-version | lean/lean-toolchain | lean/lake-manifest.json | lean/lakefile.toml | \
      src/pbc/authoring/* | src/pbc/__init__.py | _quarto.yml) echo shared; return 0 ;;
    site/lessons/*) echo lesson; return 0 ;;
    site/*) echo shared; return 0 ;;
    src/pbc/*.py) echo module; return 0 ;;
  esac
  if risk_level1_path "$1"; then
    echo documentation
  else
    echo other
  fi
}

# review_delta_unbounded <root> <rules-refs> <baseline-review> <from-tree> <to-tree> <open-json-file>
# Prints one reason per line why the delta from <from-tree> to <to-tree> needs
# a review of the complete feature, and nothing when its reach is certain:
# every changed path is a test, documentation or a process file, lesson
# content, or one module of src/pbc whose exported interface is unchanged,
# that loads no code by a computed name, that no other Python or lesson file
# of the repository could load by a computed name (a file that uses one of
# REVIEW_CHAIN_DYNAMIC_NAMES), and whose importers, found by a
# plain textual search of the import lines for its name, are all among the
# files the baseline review covered. Fails only when the arguments cannot be
# read.
review_delta_unbounded() {
  local root="$1"
  local rules="$2"
  local baseline="$3"
  local from="$4"
  local to="$5"
  local open_file="$6"
  local covered
  local status
  local path
  local kind
  local modules=()
  local module
  local stem
  local name
  local importers
  local grep_status
  local importer
  local found

  if ! git -C "$root" cat-file -e "$from^{tree}" 2>/dev/null || ! git -C "$root" cat-file -e "$to^{tree}" 2>/dev/null; then
    echo "the trees of the delta are not available, so its reach cannot be decided"
    return 0
  fi
  if ! covered="$(git -C "$root" diff --name-only --no-renames "$(jq -r '.merge_base' "$baseline")" \
    "$(jq -r '.reviewed_tree' "$baseline")" 2>/dev/null)"; then
    echo "the files that the baseline review (round $(jq -r '.round' "$baseline")) covered cannot be determined"
    return 0
  fi

  guardrails_classify "$root" "$rules" "$from" "$to" |
    awk -F '\t' -v approvals="$RISK_APPROVALS_DIR/" '$1 == "protected" && index($2, approvals) != 1 { printf "a Level 3 path: %s\n", $2 }' |
    sort -u
  risk_triggers "$root" "$from" "$to" | awk -F '\t' '{ printf "an escalation trigger: %s in %s\n", $1, $2 }' | sort -u

  while IFS=$'\t' read -r status path; do
    [[ -n "$path" ]] || continue
    kind="$(review_delta_path_kind "$path")"
    case "$kind" in
      shared) echo "a shared input of ADR 014 decision 4: $path" ;;
      other) echo "a change outside tests, documentation, lesson content, and one source module: $path" ;;
      module)
        modules+=("$path")
        [[ "$status" != "D" ]] || echo "a removed module, which changes an exported interface: $path"
        ;;
    esac
    # A file a review already found still open is not fixed on a delta again.
    jq -r --arg path "$path" '.[] | select(.carried and (.evidence | contains($path))) |
      "a file with an earlier unresolved finding (\(.id)): \($path)"' "$open_file"
  done < <(git -C "$root" diff --name-status --no-renames "$from" "$to")

  [[ "${#modules[@]}" -gt 0 ]] || return 0
  if [[ "${#modules[@]}" -gt 1 ]]; then
    echo "more than one source module changed: ${modules[*]}"
    return 0
  fi
  module="${modules[0]}"
  stem="$(basename "$module" .py)"
  if [[ "$stem" == "__init__" || "$stem" == "__main__" ]]; then
    echo "the importer search cannot decide the reach of a package's $stem: $module"
    return 0
  fi
  for name in "${REVIEW_CHAIN_DYNAMIC_NAMES[@]}"; do
    if git -C "$root" show "$to:$module" 2>/dev/null | grep -Eq "(^|[^[:alnum:]_])$name([^[:alnum:]_]|$)"; then
      echo "the module loads code by a computed name ($name), so the importer search cannot decide its reach: $module"
      return 0
    fi
  done
  # A file elsewhere that loads code by a computed name may load this module,
  # and the text cannot say which modules it loads.
  grep_status=0
  found="$(git -C "$root" grep -l -E \
    -e "(^|[^[:alnum:]_])($(IFS='|'; printf '%s' "${REVIEW_CHAIN_DYNAMIC_NAMES[*]}"))([^[:alnum:]_]|$)" \
    "$to" -- '*.py' '*.qmd')" || grep_status=$?
  [[ "$grep_status" -le 1 ]] || { echo "the search for files that load code by a computed name failed"; return 0; }
  importers=""
  while IFS= read -r importer; do
    importer="${importer#"$to":}"
    [[ -n "$importer" && "$importer" != "$module" ]] || continue
    importers+="$importer"$'\n'
    echo "a file that loads code by a computed name and may load $module, so the importer search cannot decide its reach: $importer"
  done <<<"$found"
  [[ -z "$importers" ]] || return 0
  # The exported interface: the public top-level definitions, decorators,
  # assignments, and __all__.
  if git -C "$root" diff -U0 --no-renames --no-color "$from" "$to" -- "$module" |
    grep -v '^\(---\|+++\) ' |
    grep -Eq '^[-+]((async[[:space:]]+)?def[[:space:]]+[A-Za-z]|class[[:space:]]+[A-Za-z]|@|__all__|[A-Za-z][A-Za-z0-9_]*[[:space:]]*(:[^=]*)?=[^=])'; then
    echo "a change to the exported interface of $module"
  fi

  # The importers: every Python or lesson file with an import line, or a
  # parenthesized import, that names the module. A file that names it in a
  # comment counts too, which can only ask for more review.
  importers=""
  grep_status=0
  found="$(git -C "$root" grep -l -E -e "(^|[^[:alnum:]_])(import|from)[[:space:]].*[^[:alnum:]_]$stem([^[:alnum:]_]|$)" \
    "$to" -- '*.py' '*.qmd')" || grep_status=$?
  [[ "$grep_status" -le 1 ]] || { echo "the importer search for $module failed"; return 0; }
  importers+="$found"$'\n'
  grep_status=0
  found="$(git -C "$root" grep -l --all-match -E -e 'import[[:space:]]*\([[:space:]]*$' \
    -e "(^|[^[:alnum:]_])$stem([^[:alnum:]_]|$)" "$to" -- '*.py' '*.qmd')" || grep_status=$?
  [[ "$grep_status" -le 1 ]] || { echo "the importer search for $module failed"; return 0; }
  importers+="$found"
  while IFS= read -r importer; do
    importer="${importer#"$to":}"
    [[ -n "$importer" && "$importer" != "$module" ]] || continue
    printf '%s\n' "$covered" | grep -Fqx -- "$importer" ||
      echo "an importer of $module that the baseline review (round $(jq -r '.round' "$baseline")) did not cover: $importer"
  done < <(printf '%s\n' "$importers" | sort -u)
}

# review_chain_errors <root> <rules-refs> <slug> <latest-review>
# Prints one problem per line with the chain of reviews that ends at the
# latest review, and nothing when the chain holds (ADR 020 decision 4): it
# begins with a review of the complete feature, is contiguous, every review
# of changes in it is bounded, every review gives the disposition of every
# earlier open finding, and no finding is open after the latest review.
# Whether the latest review is current is checked by the caller.
review_chain_errors() {
  local root="$1"
  local rules="$2"
  local slug="$3"
  local latest="$4"
  local scratch
  local chain
  local baseline
  local review
  local round
  local reasons
  local ruled

  scratch="$(mktemp -d "${TMPDIR:-/tmp}/review-chain.XXXXXX")"
  if chain="$(review_chain_baseline "$root" "$latest" 2>"$scratch/reason")"; then
    baseline="$(printf '%s\n' "$chain" | sed -n 1p)"
    while IFS= read -r review; do
      [[ -n "$review" ]] || continue
      round="$(jq -r '.round' "$review")"
      review_chain_open "$root" "$slug" "$round" >"$scratch/open.json" || {
        echo "the open findings before round $round cannot be determined"
        continue
      }
      reasons="$(review_delta_unbounded "$root" "$rules" "$baseline" "$(jq -r '.scope.base_tree' "$review")" \
        "$(jq -r '.reviewed_tree' "$review")" "$scratch/open.json")"
      [[ -z "$reasons" ]] ||
        printf '%s\n' "$reasons" | sed "s/^/round $round reviewed only changes whose reach is not certain: /"
    done < <(printf '%s\n' "$chain" | sed 1d)
  else
    cat "$scratch/reason"
  fi

  ruled=""
  while IFS= read -r review; do
    [[ -n "$review" ]] || continue
    round="$(jq -r '.round' "$review")"
    if [[ "$(jq -r 'has("compared_tree")' "$review")" == "true" ]]; then
      ruled="${ruled:-$round}"
    elif [[ -n "$ruled" ]]; then
      echo "round $round records no compared_tree after round $ruled did: a review made before the chain rule cannot follow one made under it"
    fi
    [[ -n "$ruled" || "$(jq -r 'has("dispositions")' "$review")" == "true" ]] || continue
    review_chain_open "$root" "$slug" "$round" >"$scratch/open.json" || continue
    review_chain_disposition_errors "$review" "$scratch/open.json" | sed "s/^/round $round: /"
  done < <(review_chain_reviews "$root" "$slug")

  if review_chain_open "$root" "$slug" $(($(jq -r '.round' "$latest") + 1)) >"$scratch/open.json"; then
    jq -r '.[] | "finding \(.id) [\(.severity)] is open: \(.title)"' "$scratch/open.json"
  else
    echo "the findings that are still open cannot be determined"
  fi
  rm -rf "$scratch"
}
