#!/usr/bin/env bash

# The completion gate of a feature. Source this file; it needs jq.
#
# A session that ends without an error is not a feature that is complete.
# The implementer therefore states where the work stands in a completion
# record, .agents/completion/<issue>.json, and the scripts go on to the
# commit and the pull request only when that record and the handoff note
# agree. The record is a claim of the implementer: the independent review
# of the complete feature checks it against the code and the tests.
#
#   {
#     "schema": "completion/v2",
#     "status": "complete" | "partial" | "blocked",
#     "risk": {"level": 1 | 2 | 3,
#              "triggers": ["<an escalation trigger the change hits>", ...],
#              "rationale": "<why this level>"},
#     "criteria": [
#       {"criterion": "<an acceptance criterion of the Issue, or a plan step>",
#        "gate": "implementation" | "pr_ci" | "owner_approval" | "post_merge",
#        "status": "met" | "not_met" | "not_applicable" | "pending",
#        "evidence": "<the test, file, or command that shows it; for
#                     not_applicable the reason; for pending what is
#                     awaited>"}
#     ],
#     "remaining": ["<what is left>", ...]
#   }
#
# The gate of a criterion is the point that clears it (ADR 020 decision 2):
# the implementation (tests, the local verification, the review), CI on the
# exact head of the pull request, the owner's approval of the exact commit
# at the merge gate, or a measurement after the merge. 'pending' names a
# later gate and is never allowed for 'implementation'.
#
# 'complete' needs every criterion met or not applicable and nothing
# remaining. 'partial' and 'blocked' need something that remains; a record
# with a pending criterion is partial. Whether a partial record is ready for
# a pull request is derived, never stored: every criterion that is not met is
# pending for a later gate.
#
# 'completion/v1' is the record of a feature started before ADR 020 was
# delivered (F130): no gate, no 'pending', and no risk. It stays valid, so
# that such a feature finishes under the contract it started with.
COMPLETION_DIR=".agents/completion"

# completion_record <root> <issue>
# Prints the path of the completion record of the Issue.
completion_record() {
  printf '%s/%s/%s.json' "$1" "$COMPLETION_DIR" "$2"
}

# completion_errors <record>
# Prints what is wrong with a completion record, one problem per line, and
# nothing for a valid one.
completion_errors() {
  local record="$1"

  if ! jq -e . "$record" >/dev/null 2>&1; then
    echo "it is not valid JSON"
    return 0
  fi
  jq -r '
    def text: type == "string" and test("[^[:space:]]");
    if type != "object" then "it is not a JSON object"
    else
      (.schema == "completion/v2") as $v2
      | (if (.schema | IN("completion/v1", "completion/v2")) | not
         then "schema must be \"completion/v2\" (or \"completion/v1\" for a feature started before ADR 020)" else empty end),
      (if (.status | IN("complete", "partial", "blocked")) | not
       then "status must be complete, partial, or blocked" else empty end),
      (if $v2 then
         if (.risk | type) != "object" then "risk must hold the level, the triggers, and the rationale"
         else
           (if (.risk.level | IN(1, 2, 3)) | not then "risk.level must be 1, 2, or 3" else empty end),
           (if (.risk.triggers | type) != "array" or ([.risk.triggers[]? | text] | all | not)
            then "risk.triggers must be a list of texts; an empty list when none applies" else empty end),
           (if (.risk.rationale | text) | not then "risk needs a rationale" else empty end)
         end
       elif has("risk") then "risk needs the schema completion/v2" else empty end),
      (if (.criteria | type) != "array" or (.criteria | length) == 0
       then "criteria must list at least one acceptance criterion"
       else (.criteria | to_entries[] |
         (.key + 1) as $n | .value |
         if type != "object" then "criterion \($n) is not an object"
         else
           (if (.criterion | text) | not then "criterion \($n) has no text" else empty end),
           (if $v2 then
              (if (.gate | IN("implementation", "pr_ci", "owner_approval", "post_merge")) | not
               then "criterion \($n): gate must be implementation, pr_ci, owner_approval, or post_merge" else empty end),
              (if (.status | IN("met", "not_met", "not_applicable", "pending")) | not
               then "criterion \($n): status must be met, not_met, not_applicable, or pending"
               elif .status == "pending" and .gate == "implementation"
               then "criterion \($n): pending is never allowed for the gate implementation" else empty end)
            else
              (if (.status | IN("met", "not_met", "not_applicable")) | not
               then "criterion \($n): status must be met, not_met, or not_applicable" else empty end),
              (if has("gate") then "criterion \($n): a gate needs the schema completion/v2" else empty end)
            end),
           (if (.evidence | text) | not then "criterion \($n) has no evidence" else empty end)
         end)
       end),
      (if (.remaining | type) != "array" or ([.remaining[]? | text] | all | not)
       then "remaining must be a list of texts; an empty list when nothing remains" else empty end),
      (if .status == "complete" and (.criteria | type) == "array"
          and ([.criteria[]? | objects | .status] | index("not_met")) != null
       then "status is complete, but a criterion is not met" else empty end),
      (if .status == "complete" and (.criteria | type) == "array"
          and ([.criteria[]? | objects | .status] | index("pending")) != null
       then "status is complete, but a criterion is pending; complete means every criterion is met" else empty end),
      (if .status == "complete" and (.remaining | type) == "array" and (.remaining | length) > 0
       then "status is complete, but work remains" else empty end),
      (if (.status == "partial" or .status == "blocked") and (.remaining | type) == "array"
          and (.remaining | length) == 0
       then "status is \(.status), but remaining does not say what is left" else empty end)
    end' "$record"
}

# handoff_remaining <handoff-note>
# Prints the work that a handoff note lists under 'Remaining', one line per
# line of the note, and nothing when there is none. The implementer reduces
# the note to one line when the Issue is complete, so text here means that
# work is left, whatever the completion record says.
handoff_remaining() {
  [[ -f "$1" ]] || return 0
  awk '
    function emit(text) {
      gsub(/^[[:space:]*:>-]+|[[:space:]]+$/, "", text)
      if (text == "") return
      if (tolower(text) ~ /^(none|nothing|n\/a|no remaining|nothing remains|-)[[:space:].!]*$/) return
      print text
    }
    # Another part of the note ends the list.
    found && (/^#/ || tolower($0) ~ /^[[:space:]]*([-*][[:space:]]*)?\**(done|in progress|pending|tried and rejected|open questions?)\**[[:space:]]*:/) {
      found = 0
    }
    tolower($0) ~ /^[[:space:]]*(#+[[:space:]]*|[-*][[:space:]]*)?\**remaining( work)?\**[[:space:]]*:?\**[[:space:]]*/ &&
      tolower($0) !~ /^[[:space:]]*(#+[[:space:]]*|[-*][[:space:]]*)?\**remaining( work)?[a-z]/ {
      found = 1
      line = $0
      sub(/^[[:space:]]*(#+[[:space:]]*|[-*][[:space:]]*)?\**[Rr][Ee][Mm][Aa][Ii][Nn][Ii][Nn][Gg]( [Ww][Oo][Rr][Kk])?\**[[:space:]]*:?\**/, "", line)
      emit(line)
      next
    }
    found { emit($0) }' "$1"
}

# completion_summary_present <root> <issue>
# Succeeds when the implementer wrote the summary of the changes that the
# commit message is made from. An unattended run needs it: nobody edits the
# message there.
completion_summary_present() {
  local summary="$1/.agents/summaries/$2.md"

  [[ -f "$summary" ]] && grep -q '^[[:space:]]*- [^[:space:]]' "$summary"
}

# completion_gate <root> <issue>
# Decides whether the feature is complete. Prints the outcome on the first
# line and the reasons after it, one per line:
#
#   complete  the record is valid and says so, and the handoff note lists
#             no remaining work
#   pending   ready for a pull request: the record says partial, every
#             criterion that is not met is pending for a later gate, and the
#             handoff note lists no remaining work; the reasons name the
#             pending criteria and their gates
#   partial   work remains, by the record or by the handoff note
#   blocked   the implementer cannot go on without the human
#   missing   there is no record
#   invalid   the record cannot be used
completion_gate() {
  local root="$1"
  local issue="$2"
  local record
  local errors
  local status
  local left

  record="$(completion_record "$root" "$issue")"
  if [[ ! -f "$record" ]]; then
    echo "missing"
    echo "the implementer wrote no completion record ($COMPLETION_DIR/$issue.json)"
    return 0
  fi
  errors="$(completion_errors "$record")"
  if [[ -n "$errors" ]]; then
    echo "invalid"
    printf '%s\n' "$errors" | sed "s|^|the completion record ($COMPLETION_DIR/$issue.json): |"
    return 0
  fi

  status="$(jq -r '.status' "$record")"
  left="$(handoff_remaining "$root/.agents/handoffs/$issue.md")"
  # Ready for a pull request (ADR 020 decision 2): a partial record whose
  # only unmet criteria are pending for a later gate, with no remaining work
  # in the handoff note.
  if [[ "$status" == "partial" && -z "$left" ]] && completion_only_pending "$record"; then
    echo "pending"
    completion_pending_lines "$record"
    return 0
  fi
  if [[ "$status" != "complete" ]]; then
    echo "$status"
    jq -r '.criteria[] | select(.status == "not_met") | "not met: \(.criterion)"' "$record"
    jq -r '.criteria[] | select(.status == "pending") | "pending (\(.gate)): \(.criterion)"' "$record"
    jq -r '.remaining[] | "remaining: \(.)"' "$record"
    return 0
  fi

  if [[ -n "$left" ]]; then
    echo "partial"
    echo "the completion record says complete, but the handoff note (.agents/handoffs/$issue.md) lists remaining work:"
    printf '%s\n' "$left" | sed 's/^/remaining: /'
    return 0
  fi
  echo "complete"
}

# completion_only_pending <record>
# Succeeds when a valid record has a pending criterion and every criterion
# that is not met or not applicable is pending.
completion_only_pending() {
  jq -e '[.criteria[].status] | (index("pending") != null) and (index("not_met") == null)' "$1" >/dev/null 2>&1
}

# completion_pending_lines <record>
# Prints one line per pending criterion of a valid record:
# 'pending (<gate>): <criterion>'.
completion_pending_lines() {
  jq -r '.criteria[] | select(.status == "pending") | "pending (\(.gate)): \(.criterion)"' "$1"
}

# completion_closing_pattern <issue>
# Prints an extended regular expression, to be matched without regard to
# case, for a keyword with which GitHub closes that Issue on a merge: in a
# pull request description, and in the message of a commit that reaches the
# default branch.
completion_closing_pattern() {
  printf '%s' "(^|[^[:alnum:]])(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)[[:space:]]*:?[[:space:]]+(#|[[:alnum:]_.-]+/[[:alnum:]_.-]+#|https?://github\\.com/[^[:space:]]+/issues/)$1([^0-9]|\$)"
}

# completion_neutralize_closing <issue>
# Copies standard input and turns every closing keyword for the Issue into
# 'Refs', so that text taken over from a commit message cannot close an Issue
# whose completion gate did not pass.
completion_neutralize_closing() {
  awk -v pattern="$(completion_closing_pattern "$1")" '
    {
      line = $0
      out = ""
      while (match(tolower(line), pattern)) {
        found = substr(line, RSTART, RLENGTH)
        # Keep what stands before the keyword and after the reference.
        lead = (tolower(found) ~ /^[^a-z]/) ? substr(found, 1, 1) : ""
        rest = substr(found, length(lead) + 1)
        sub(/^[A-Za-z]+([[:space:]]*:)?/, "Refs", rest)
        out = out substr(line, 1, RSTART - 1) lead rest
        line = substr(line, RSTART + RLENGTH)
      }
      print out line
    }'
}

# completion_commit_lines <root> <issue>
# Prints the completion statement of a commit message from a valid record:
# the status, the criteria with their evidence, and what remains.
completion_commit_lines() {
  local record

  record="$(completion_record "$1" "$2")"
  jq -r '
    "Completion: \(.status)",
    (.criteria[] | "- \(.status | gsub("_"; " "))\(if .status == "pending" then " (\(.gate))" else "" end): \(.criterion) (\(.evidence))"),
    (.remaining[] | "- remaining: \(.)")' "$record"
}
