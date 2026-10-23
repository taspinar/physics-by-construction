#!/usr/bin/env bash

# The risk level of a change (ADR 020 decision 1). Source this file after
# scripts/lib/fingerprint.sh, scripts/lib/guardrails.sh, and
# scripts/lib/completion.sh; it needs jq.
#
# Every change carries one level, 1 to 3, the highest of three readings:
#
# - the path minimum: 3 for every path the merge approval gate reports as
#   protected (its builtin list and the protected list of
#   .agents/policies/guardrails.conf, read from the base), except the
#   approval requests themselves; 1 when every other changed path is
#   documentation or a process file; 2 otherwise;
# - the escalation triggers: 3 when the diff against the base shows one the
#   scripts can detect, or when the implementer's completion record or the
#   independent review names one;
# - the assessed level: the level the completion record states and the level
#   the review assesses (architecture_impact.risk_level).
#
# An agent may raise the level; no agent lowers it. Only the owner lowers a
# trigger reading or an assessed level, never the path minimum, by an
# approving review of the exact head at the merge gate (ADR 020 decision 3).
# The approval request, .agents/approvals/<issue>.md, asks for that review:
# it is committed with the change so that GitHub requires the review, and no
# script reads it as the owner's decision. Until the owner authorizes a
# lowering the change keeps its required level, and the scripts record the
# required level, the requested level, and the head or tree they apply to.
#
# The refusals and the Level 3 rules apply to a completion/v2 record. A
# completion/v1 record is the contract of a feature started before ADR 020
# was delivered: its level is derived and recorded, nothing more.

RISK_APPROVALS_DIR=".agents/approvals"

# Dependency files, by name wherever they are: a change to one is the trigger
# 'dependency selection'. Action versions and vendored skills are Level 3 by
# their paths.
RISK_DEPENDENCY_NAMES=(
  pyproject.toml uv.lock poetry.lock Pipfile Pipfile.lock requirements.txt
  package.json package-lock.json yarn.lock pnpm-lock.yaml
  Cargo.toml Cargo.lock go.mod go.sum Gemfile Gemfile.lock
  lean-toolchain lakefile.toml lakefile.lean lake-manifest.json
)

# The groups of the partial run that gives an intermediate round of a Level 3
# change quick feedback (ADR 020 decision 5): the checks without a site build,
# the Python sources and the unit tests, and the integration tests of the
# scripts. Typically about 13 minutes against about 68 for the full run.
RISK_FEEDBACK_CANDIDATES=(default code integration-other)

# risk_feedback_groups <root>
# Prints the feedback groups that the project's ./scripts/verify.sh knows,
# separated by commas: 'default' at least.
risk_feedback_groups() {
  local known
  local group
  local groups=""

  known="$(cd "$1" && ./scripts/verify.sh --groups 2>/dev/null)" || known="default"
  for group in "${RISK_FEEDBACK_CANDIDATES[@]}"; do
    printf '%s\n' "$known" | grep -Fqx "$group" && groups+="${groups:+,}$group"
  done
  printf '%s\n' "${groups:-default}"
}

# risk_level1_path <path>
# Succeeds for documentation and process files: docs/, a Markdown file at the
# top level, plans, handoff notes, and summaries. The ADRs, the planning
# documents, and AGENTS.md are Level 3 paths; that reading wins.
risk_level1_path() {
  case "$1" in
    docs/* | .agents/plans/* | .agents/handoffs/* | .agents/summaries/*) return 0 ;;
    */*) return 1 ;;
    *.md) return 0 ;;
  esac
  return 1
}

# risk_snapshot <root> <scratch-dir>
# Prints the fingerprint of the working tree (scripts/lib/fingerprint.sh): a
# tree that holds the uncommitted and untracked files too.
risk_snapshot() {
  fingerprint_worktree "$1" "$2"
}

# risk_content_tree <root> <scratch-dir> <issue>
# Prints the content tree an approval request names (its line 'Tree:'): the
# fingerprint of the working tree, which leaves out .agents/approvals/, with
# the completion record and the handoff note of the Issue, which Git ignores.
# The request is the vehicle of a level and of a lowering, never part of the
# content it is about, so editing it leaves this tree unchanged and the
# request can name the tree under review.
risk_content_tree() {
  local root="$1"
  local index="$2/content.index"
  local tree
  local path
  local paths=()

  tree="$(fingerprint_worktree "$root" "$2")" || return 1
  for path in "$COMPLETION_DIR/$3.json" ".agents/handoffs/$3.md"; do
    [[ ! -e "$root/$path" && ! -L "$root/$path" ]] || paths+=("$path")
  done
  rm -f "$index"
  GIT_INDEX_FILE="$index" git -C "$root" read-tree "$tree" || return 1
  if [[ "${#paths[@]}" -gt 0 ]]; then
    GIT_INDEX_FILE="$index" git -C "$root" add -f -- "${paths[@]}" >/dev/null || return 1
  fi
  GIT_INDEX_FILE="$index" git -C "$root" write-tree
}

# risk_path_minimum <root> <rules-refs> <from> <tree>
# Prints the path minimum on the first line and, for Level 3, one line
# '<path>: <reason>' per Level 3 path.
risk_path_minimum() {
  local root="$1"
  local rules="$2"
  local from="$3"
  local tree="$4"
  local protected
  local path
  local level=1

  protected="$(guardrails_classify "$root" "$rules" "$from" "$tree" |
    awk -F '\t' -v approvals="$RISK_APPROVALS_DIR/" '$1 == "protected" && index($2, approvals) != 1 { printf "%s: %s\n", $2, $3 }' |
    sort -u)"
  if [[ -n "$protected" ]]; then
    echo 3
    printf '%s\n' "$protected"
    return 0
  fi
  while IFS= read -r path; do
    [[ -n "$path" && "$path" != "$RISK_APPROVALS_DIR/"* ]] || continue
    risk_level1_path "$path" || { level=2; break; }
  done < <(git -C "$root" diff --name-only --no-renames "$from" "$tree")
  echo "$level"
}

# risk_triggers <root> <from> <tree>
# Prints one line '<trigger><TAB><path><TAB><detail>' per escalation trigger
# the scripts detect on the diff from <from> to <tree>, and nothing when there
# is none:
#
#   tolerance or budget changed     a Python or lesson line that names a
#                                   tolerance or a budget with a number, removed
#                                   or changed; such a Python line added (a new
#                                   tolerance can widen what a check accepts);
#                                   a data line of a budget table
#   skip or expected failure added  a new skip, skipif, xfail, or importorskip;
#                                   in Lean, a new sorry, admit, or axiom
#   assertion removed or changed    a line that is not added back as it was: a
#                                   Python assert; in a shell test (a .sh file
#                                   under tests/ or named *-test.sh), a line
#                                   that calls fail, exits with a failure, or
#                                   calls an expect_ or assert_ helper; in
#                                   Lean, the first line of a theorem, lemma,
#                                   or example, or a #guard, #guard_msgs,
#                                   #check_failure, or #print axioms command
#   test removed                    a test function (Python def test_, shell
#                                   test_ function) or a test file removed
#   marker changed                  a pytest marker or same_machine added or
#                                   removed, except a parametrize that
#                                   decorates a new test (the first def after
#                                   it in its added block is a new def
#                                   test_), which only structures new cases;
#                                   on a test that is already there, and
#                                   when removed or changed, it stays a
#                                   reading;
#                                   the shell tests and the Lean proofs have
#                                   no markers
#   dependency file changed         a dependency manifest or lock file
#
# The reading is conservative: a narrowed tolerance reads as changed too, and
# only the owner lowers a trigger reading. The formats are the ones of this
# project's checks: Python, shell tests, and Lean proofs; a Lean statement
# changed below its first line rests on the review (ADR 020, the residual
# risk of the triggers that are not mechanically detectable).
risk_triggers() {
  local root="$1"
  local from="$2"
  local tree="$3"
  local path
  local name
  local dependency

  while IFS=$'\t' read -r status path; do
    [[ -n "$path" ]] || continue
    name="$(basename "$path")"
    for dependency in "${RISK_DEPENDENCY_NAMES[@]}"; do
      if [[ "$name" == "$dependency" ]]; then
        printf 'dependency file changed\t%s\t%s\n' "$path" "the file is a dependency manifest or lock file"
      fi
    done
    if [[ "$status" == "D" ]] && [[ "$path" == tests/* || "$name" == test_*.py || "$name" == *_test.py || "$name" == *-test.sh ]]; then
      printf 'test removed\t%s\t%s\n' "$path" "the test file is deleted"
    fi
  done < <(git -C "$root" diff --name-status --no-renames "$from" "$tree")

  git -C "$root" diff -U0 --no-renames --no-color "$from" "$tree" -- '*.py' '*.qmd' '*budgets.conf' '*.sh' '*.lean' |
    awk '
      BEGIN {
        tolerance = "(rtol|atol|tolerance|[^[:alnum:]_]tol[^[:alnum:]_]|^tol[^[:alnum:]_]|budget|approx|isclose|allclose)"
        structuring = "pytest\\.mark\\.parametrize([^[:alnum:]_]|$)"
        lean_declaration ="^(@\\[[^]]*\\][[:space:]]*)?((private|protected|noncomputable|nonrec|unsafe)[[:space:]]+)*(theorem|lemma|example)([[:space:]]|$)"
      }
      function trim(text) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", text); return text }
      function short(text) { return length(text) > 100 ? substr(text, 1, 97) "..." : text }
      function report(kind, line) {
        key = kind SUBSEP file SUBSEP line
        if (!(key in seen)) { seen[key] = 1; printf "%s\t%s\t%s\n", kind, file, short(line) }
      }
      # Whether the first def or class that follows added line i in its own
      # added block is a new def test_: the decorator on line i then decorates
      # that new test. A def that is not in the block is an existing one.
      function decorates_new_test(i,   k) {
        for (k = i + 1; k <= nadded && addblock[k] == addblock[i]; k++) {
          if (addlist[k] ~ /^(async[[:space:]]+)?def[[:space:]]+test_/) return 1
          if (addlist[k] ~ /^(async[[:space:]]+)?def[[:space:]]/ || addlist[k] ~ /^class[[:space:]]/) return 0
        }
        return 0
      }
      function finish(   i, line) {
        if (file == "") return
        for (i = 1; i <= nremoved; i++) {
          line = removed[i]
          if (line in added) continue
          if (is_python || is_lesson) {
            if (line ~ tolerance && line ~ /[0-9]/)
              report("tolerance or budget changed", line)
          }
          if (is_budgets && line !~ /^#/ && line != "") report("tolerance or budget changed", line)
          if (is_python) {
            if (line ~ /^assert[[:space:](]/ || line ~ /^self\.assert/ || line ~ /pytest\.raises/)
              report("assertion removed or changed", line)
            if (line ~ /^(async[[:space:]]+)?def[[:space:]]+test_/) report("test removed", line)
            if (line ~ /pytest\.mark\.|same_machine/ && line !~ /(skip|xfail)/) report("marker changed", line)
          }
          if (is_shell_test && line !~ /^#/) {
            if (line ~ /(^|[^[:alnum:]_-])fail([[:space:]";)]|$)/ || line ~ /(^|[^[:alnum:]_-])exit[[:space:]]+[1-9]/ ||
                line ~ /(^|[^[:alnum:]_-])(expect|assert)_[[:alnum:]_]+([[:space:];)]|$)/)
              report("assertion removed or changed", line)
            if (line ~ /^(function[[:space:]]+)?test_[[:alnum:]_]*[[:space:]]*(\(\)|\{)/) report("test removed", line)
          }
          if (is_lean && line !~ /^--/) {
            if (line ~ lean_declaration || line ~ /^#(guard|guard_msgs|guard_expr|check_failure|print[[:space:]]+axioms)([^[:alnum:]_]|$)/)
              report("assertion removed or changed", line)
          }
        }
        for (i = 1; i <= nadded; i++) {
          line = addlist[i]
          if (line in gone) continue
          if (is_budgets && line !~ /^#/ && line != "") report("tolerance or budget changed", line)
          if (is_python && line !~ /^#/ && line ~ tolerance && line ~ /[0-9]/) report("tolerance or budget changed", line)
          if (is_lean && line !~ /^--/ &&
              (line ~ /(^|[^[:alnum:]_.\047`])(sorry|admit)([^[:alnum:]_\047`]|$)/ || line ~ /^(@\[[^]]*\][[:space:]]*)?((private|protected|noncomputable|unsafe)[[:space:]]+)*axiom[[:space:]]/))
            report("skip or expected failure added", line)
          if (!is_python) continue
          if (line ~ /pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail|importorskip)[[:space:]]*\(|unittest\.(skip|expectedFailure)|@skip/)
            report("skip or expected failure added", line)
          else {
            # A marker that only structures tests is no trigger when it is
            # added to a new test (the first def after it in its added block is
            # a new def test_);
            # on a test that is already there it changes the cases the test
            # runs, so it is one; every other marker on the line still is.
            rest = line
            if (decorates_new_test(i)) gsub(structuring, "", rest)
            if (rest ~ /pytest\.mark\.|same_machine/) report("marker changed", line)
          }
        }
      }
      /^diff --git / {
        finish()
        file = $0
        sub(/^diff --git a\//, "", file)
        sub(/ b\/.*$/, "", file)
        is_python = (file ~ /\.py$/)
        is_lesson = (file ~ /\.qmd$/)
        is_budgets = (file ~ /budgets\.conf$/)
        is_shell_test = (file ~ /\.sh$/ && (file ~ /^tests\// || file ~ /(^|\/)[^\/]*-test\.sh$/))
        is_lean = (file ~ /\.lean$/ && file !~ /(^|\/)lakefile\.lean$/)
        nremoved = 0; nadded = 0; block = 0
        delete added; delete gone; delete removed; delete addlist; delete addblock
        next
      }
      /^(---|\+\+\+) / { next }
      /^-/ { block++; line = trim(substr($0, 2)); removed[++nremoved] = line; gone[line] = 1; next }
      /^\+/ {
        line = trim(substr($0, 2)); addlist[++nadded] = line; added[line] = 1
        addblock[nadded] = block
        next
      }
      { block++ }
      END { finish() }'
}

# risk_review_reading <review-json> <field>
# Prints, for the review and the rounds it builds on (a review of changes
# only cannot lower what an earlier round found), the highest
# architecture_impact.risk_level ('level') or every named escalation trigger
# ('triggers', one per line). Prints nothing without a review or a reading.
risk_review_reading() {
  local review="$1"
  local since
  local stem
  local level=""
  local found

  while [[ -n "$review" && -f "$review" ]]; do
    if [[ "$2" == "level" ]]; then
      found="$(jq -r '.architecture_impact.risk_level // empty | select(IN(1, 2, 3))' "$review" 2>/dev/null || true)"
      [[ -z "$found" || ( -n "$level" && "$level" -ge "$found" ) ]] || level="$found"
    else
      jq -r '.architecture_impact.escalation_triggers // [] | .[] | strings | select(test("\\S"))' "$review" 2>/dev/null || true
    fi
    since="$(jq -r 'if (.scope | type) == "object" and .scope.kind == "changes" then .scope.since_round else empty end' "$review" 2>/dev/null || true)"
    [[ -n "$since" ]] || break
    stem="${review%-review-[0-9][0-9].json}"
    review="$stem-review-$(printf '%02d' "$since").json"
  done
  [[ "$2" != "level" ]] || printf '%s' "$level"
}

# approval_request_path <issue>
approval_request_path() {
  printf '%s/%s.md' "$RISK_APPROVALS_DIR" "$1"
}

# approval_request_field <file> <field>
# Prints the value of a line '<field>: <value>' (also as a list item or in
# bold) of an approval request, or nothing.
approval_request_field() {
  sed -nE "s/^[[:space:]]*([-*][[:space:]]+)?(\*\*)?$2:(\*\*)?[[:space:]]*//p" "$1" | head -n 1 |
    sed -E 's/^\*\*[[:space:]]*//; s/[[:space:]]+$//'
}

# approval_request_level <file> <field>
# Prints the level a field of the approval request names (the first digit 1
# to 3 of its value), or nothing.
approval_request_level() {
  approval_request_field "$1" "$2" | sed -nE 's/^[^0-9]*([1-3]).*$/\1/p'
}

# risk_assess <root> <rules-refs> <from> <issue> [<review-json>]
# Derives the level of the change in the working tree at <root> against
# <from>, and sets:
#
#   RISK_TREE            the fingerprint the derivation applies to
#   RISK_CONTENT_TREE    the content tree an approval request names (risk_content_tree)
#   RISK_PATH_MIN        the path minimum, and RISK_PATH_REASONS its Level 3 paths
#   RISK_TRIGGERS        the detected triggers, one '<trigger>: <path> (<detail>)' per line
#   RISK_NAMED_TRIGGERS  the triggers the record and the review name, one per line
#   RISK_SCHEMA          the schema of the completion record, or 'none'
#   RISK_RECORDED        the level the record states, or empty
#   RISK_REVIEWED        the level the review assesses, or empty
#   RISK_REQUIRED        the required level: the highest of the readings
#   RISK_BY              what gives the required level: paths, triggers, or assessment
#   RISK_REQUEST         the approval request, relative to <root>, when it exists
#   RISK_REQUESTED       the level it asks for, when it names a lowering
#   RISK_ENFORCED        1 for a completion/v2 record, whose rules apply
#   RISK_ERRORS          what the rules refuse, one problem per line
#
# Returns 1 when the working tree cannot be read.
risk_assess() {
  local root="$1"
  local rules="$2"
  local from="$3"
  local issue="$4"
  local review="${5:-}"
  local scratch
  local record
  local path_lines
  local trigger_reading=0
  local assessed=0
  local request_file
  local request_issue
  local request_required
  local request_level
  local request_tree
  local field

  RISK_TREE=""
  RISK_CONTENT_TREE=""
  RISK_PATH_MIN=""
  RISK_PATH_REASONS=""
  RISK_TRIGGERS=""
  RISK_NAMED_TRIGGERS=""
  RISK_SCHEMA="none"
  RISK_RECORDED=""
  RISK_REVIEWED=""
  RISK_REQUIRED=""
  RISK_BY=""
  RISK_REQUEST=""
  RISK_REQUESTED=""
  RISK_ENFORCED=0
  RISK_ERRORS=""

  scratch="$(mktemp -d "${TMPDIR:-/tmp}/risk.XXXXXX")"
  RISK_TREE="$(risk_snapshot "$root" "$scratch")" &&
    RISK_CONTENT_TREE="$(risk_content_tree "$root" "$scratch" "$issue")" || { rm -rf "$scratch"; return 1; }
  rm -rf "$scratch"

  path_lines="$(risk_path_minimum "$root" "$rules" "$from" "$RISK_TREE")"
  RISK_PATH_MIN="$(printf '%s\n' "$path_lines" | sed -n 1p)"
  RISK_PATH_REASONS="$(printf '%s\n' "$path_lines" | sed 1d)"
  RISK_TRIGGERS="$(risk_triggers "$root" "$from" "$RISK_TREE" | awk -F '\t' '{ printf "%s: %s (%s)\n", $1, $2, $3 }')"

  record="$(completion_record "$root" "$issue")"
  if [[ -f "$record" ]] && [[ -z "$(completion_errors "$record")" ]]; then
    RISK_SCHEMA="$(jq -r '.schema' "$record")"
    if [[ "$RISK_SCHEMA" == "completion/v2" ]]; then
      RISK_ENFORCED=1
      RISK_RECORDED="$(jq -r '.risk.level' "$record")"
      RISK_NAMED_TRIGGERS="$(jq -r '.risk.triggers[] | "named in the completion record: \(.)"' "$record")"
    fi
  elif [[ -f "$record" ]]; then
    RISK_SCHEMA="invalid"
  fi
  RISK_REVIEWED="$(risk_review_reading "$review" level)"
  field="$(risk_review_reading "$review" triggers | sed 's/^/named by the review: /')"
  [[ -z "$field" ]] || RISK_NAMED_TRIGGERS+="${RISK_NAMED_TRIGGERS:+$'\n'}$field"

  [[ -z "$RISK_TRIGGERS$RISK_NAMED_TRIGGERS" ]] || trigger_reading=3
  [[ -z "$RISK_RECORDED" || "$RISK_RECORDED" -le "$assessed" ]] || assessed="$RISK_RECORDED"
  [[ -z "$RISK_REVIEWED" || "$RISK_REVIEWED" -le "$assessed" ]] || assessed="$RISK_REVIEWED"
  RISK_REQUIRED="$RISK_PATH_MIN"
  RISK_BY="paths"
  if [[ "$trigger_reading" -gt "$RISK_REQUIRED" ]]; then
    RISK_REQUIRED="$trigger_reading"
    RISK_BY="triggers"
  fi
  if [[ "$assessed" -gt "$RISK_REQUIRED" ]]; then
    RISK_REQUIRED="$assessed"
    RISK_BY="assessment"
  fi

  request_file="$root/$(approval_request_path "$issue")"
  if [[ -f "$request_file" ]]; then
    RISK_REQUEST="$(approval_request_path "$issue")"
    RISK_REQUESTED="$(approval_request_level "$request_file" "Requested level")"
  fi

  [[ "$RISK_ENFORCED" -eq 1 ]] || return 0

  # The rules of a completion/v2 record.
  if [[ "$RISK_RECORDED" -lt "$RISK_PATH_MIN" ]]; then
    RISK_ERRORS+="the completion record states level $RISK_RECORDED, below the path minimum $RISK_PATH_MIN of the change; the path minimum is never lowered (ADR 020 decision 1)"$'\n'
  elif [[ "$RISK_RECORDED" -lt "$RISK_REQUIRED" && ( -z "$RISK_REQUESTED" || "$RISK_REQUESTED" != "$RISK_RECORDED" ) ]]; then
    RISK_ERRORS+="the completion record states level $RISK_RECORDED, below the level $RISK_REQUIRED that the $RISK_BY give; record level $RISK_REQUIRED, or name the lowering the owner asked for in the approval request $(approval_request_path "$issue") (ADR 020 decision 1)"$'\n'
  fi
  if [[ "$RISK_REQUIRED" -eq 3 && "$RISK_PATH_MIN" -lt 3 && -z "$RISK_REQUEST" ]]; then
    RISK_ERRORS+="the change is Level 3 by its $RISK_BY, so it needs the committed approval request $(approval_request_path "$issue"), which makes GitHub require the owner's review (ADR 020 decision 3)"$'\n'
  fi
  if [[ -n "$RISK_REQUEST" ]]; then
    if git -C "$root" check-ignore -q "$RISK_REQUEST"; then
      RISK_ERRORS+="Git ignores $RISK_REQUEST, so it would not be committed; an approval request is committed with the change"$'\n'
    fi
    request_issue="$(approval_request_field "$request_file" "Issue" | sed -nE 's/^#?([0-9]+).*$/\1/p')"
    [[ "$request_issue" == "$issue" ]] ||
      RISK_ERRORS+="the approval request $RISK_REQUEST does not name Issue #$issue on a line 'Issue: #$issue'"$'\n'
    request_level="$(approval_request_level "$request_file" "Level")"
    if [[ -z "$request_level" ]]; then
      RISK_ERRORS+="the approval request $RISK_REQUEST does not state the level on a line 'Level: <1 to 3>'"$'\n'
    elif [[ "$request_level" != "$RISK_REQUIRED" ]]; then
      RISK_ERRORS+="the approval request $RISK_REQUEST states level $request_level, but the change requires level $RISK_REQUIRED; state it on a line 'Level: $RISK_REQUIRED'"$'\n'
    fi
    for field in "Derived from" "Tree"; do
      [[ -n "$(approval_request_field "$request_file" "$field")" ]] ||
        RISK_ERRORS+="the approval request $RISK_REQUEST has no line '$field: ...'"$'\n'
    done
    # The request leaves the fingerprint, so a wrong tree would not make a
    # verification or a review stale; it is refused here instead.
    request_tree="$(approval_request_field "$request_file" "Tree" | awk '{ print $1 }' | tr -d '`')"
    if [[ -n "$request_tree" && "$request_tree" != "$RISK_CONTENT_TREE" ]]; then
      RISK_ERRORS+="the approval request $RISK_REQUEST names tree $request_tree, but the content tree is $RISK_CONTENT_TREE; state it on a line 'Tree: $RISK_CONTENT_TREE'"$'\n'
    fi
    if [[ -n "$RISK_REQUESTED" ]]; then
      request_required="$(approval_request_level "$request_file" "Required level")"
      if [[ "$RISK_REQUESTED" -lt "$RISK_PATH_MIN" ]]; then
        RISK_ERRORS+="the approval request asks to lower the level to $RISK_REQUESTED, below the path minimum $RISK_PATH_MIN; only a trigger reading or an assessed level may be lowered, never the path minimum (ADR 020 decision 1)"$'\n'
      elif [[ "$RISK_REQUESTED" -ge "$RISK_REQUIRED" ]]; then
        RISK_ERRORS+="the approval request asks for level $RISK_REQUESTED, which is no lowering of the required level $RISK_REQUIRED; remove the line 'Requested level:'"$'\n'
      fi
      [[ "$RISK_REQUESTED" == "$RISK_RECORDED" ]] ||
        RISK_ERRORS+="the approval request asks for level $RISK_REQUESTED, but the completion record states level $RISK_RECORDED"$'\n'
      [[ "$request_required" == "$RISK_REQUIRED" ]] ||
        RISK_ERRORS+="the approval request names the required level '${request_required:-none}', but the change requires level $RISK_REQUIRED; state it on a line 'Required level: $RISK_REQUIRED'"$'\n'
      for field in "Reason" "Owner's word"; do
        [[ -n "$(approval_request_field "$request_file" "$field")" ]] ||
          RISK_ERRORS+="the lowering in $RISK_REQUEST has no line '$field: ...'; a lowering names the reason and the owner's word that let the agent proceed"$'\n'
      done
    fi
  fi
  RISK_ERRORS="${RISK_ERRORS%$'\n'}"
}

# risk_statement_lines
# Prints the statement of the level for a commit message or a pull request,
# from the variables risk_assess set, one list item per line.
risk_statement_lines() {
  local reasons

  echo "- required: level $RISK_REQUIRED, by the $RISK_BY"
  if [[ "$RISK_PATH_MIN" -eq 3 ]]; then
    reasons="$(printf '%s\n' "$RISK_PATH_REASONS" | sed 's/: .*$//' | head -n 5 | paste -sd ',' - | sed 's/,/, /g')"
    [[ "$(printf '%s\n' "$RISK_PATH_REASONS" | grep -c .)" -le 5 ]] ||
      reasons+=", and $(($(printf '%s\n' "$RISK_PATH_REASONS" | grep -c .) - 5)) more"
    echo "- path minimum: level 3 ($reasons)"
  else
    echo "- path minimum: level $RISK_PATH_MIN"
  fi
  if [[ -z "$RISK_TRIGGERS$RISK_NAMED_TRIGGERS" ]]; then
    echo "- escalation triggers: none detected or named"
  else
    printf '%s\n' "$RISK_TRIGGERS" "$RISK_NAMED_TRIGGERS" | grep . | sed 's/^/- escalation trigger: /'
  fi
  case "$RISK_SCHEMA" in
    completion/v2) echo "- stated in the completion record: level $RISK_RECORDED" ;;
    completion/v1) echo "- stated in the completion record: none (completion/v1, the contract of a feature started before ADR 020)" ;;
    *) echo "- stated in the completion record: none" ;;
  esac
  echo "- assessed by the independent review: ${RISK_REVIEWED:+level }${RISK_REVIEWED:-not assessed}"
  if [[ -n "$RISK_REQUESTED" ]]; then
    echo "- requested: level $RISK_REQUESTED, in $RISK_REQUEST: a request only. The change keeps level $RISK_REQUIRED until the owner's identity approves exactly the head at the merge gate; without that approval the finish, the review, and the verification are redone at level $RISK_REQUIRED before the merge"
  elif [[ -n "$RISK_REQUEST" ]]; then
    echo "- approval request: $RISK_REQUEST, a request for the owner's review, never an approval"
  fi
  echo "- derived for the content $RISK_TREE"
  echo "- content tree for the approval request (Tree:): $RISK_CONTENT_TREE"
}
