# Plan: F131, risk-proportionate workflow, part 2 (Issue #241)

Delivers ADR 020 decision 4, and decision 1 as it applies to the review,
in the review, triage, and finish scripts, the schemas, the prompts, the
policy, and the guides. Written by the implementer on the owner's
instruction of 2026-10-24 (no plan existed), at base `f86cd65`.

## Scope

The seven acceptance criteria of Issue #241, from the F131 block of
`docs/roadmap.md`. Out of scope: everything of F130, what a verification
executes, CI, the "owner accepts" triage route (#248), and any idea beyond
the F131 block.

## Design

1. **The fingerprint.** A review records `record_paths`, the Git-ignored
   completion record and handoff note of its Issue, and its
   `reviewed_tree` is the working-tree fingerprint with those files added
   (`fingerprint_with_records` in `scripts/lib/fingerprint.sh`; the
   content tree of the approval request is the same tree). A review
   without `record_paths`, made before F131, keeps the working-tree
   fingerprint. The verification record keeps the working-tree
   fingerprint, so editing the record or the note costs a review, never a
   verification.
2. **Stable identifiers and the chain.** A finding's stable identifier is
   its round and its identifier in the round, `R01-M1`. Every review
   records `compared_tree` (a full review: the tree of the merge base; a
   review of changes: the reviewed tree of the previous round, as
   `scope.base_tree` already did) and `reviewed_tree`. Every later review
   records `dispositions`: for every earlier open finding, `resolved` or
   `accepted` with the evidence, or `open`, in which case a finding of the
   same review names it in `continues` and carries it on (so the fix, the
   triage, and the follow-up of a still-open finding run as today). An
   earlier finding is open from its round until a disposition closes it,
   unless its round's approved triage accepted or deferred it. A review
   made before F131 (neither `compared_tree` nor `dispositions`) closes
   the earlier findings, as its contract re-reported the unresolved ones.
   A review made under the rule (it records `compared_tree`) must give
   `dispositions` and closes only what they close, and a review without
   the chain fields cannot follow one made under the rule (review 03, M1).
   The chain checks the recorded `compared_tree` of a full review against
   the tree of its recorded merge base, and a mismatch is a break (review
   06, M1).
3. **The bounded-impact rule** (`scripts/lib/review-chain.sh`). A delta
   is bounded only when every changed path is a test, documentation or a
   process file (with the completion record and the handoff note),
   lesson content under `site/lessons/`, or one module of `src/pbc` that
   is not a shared input, whose public top-level names, decorators, and
   `__all__` are unchanged, that loads no code by a computed name (the
   digest's dynamic names), that no other `.py` or `.qmd` file could load
   by a computed name (no other file uses one of the dynamic names; review
   04, M1), and whose importers, found by a plain textual
   search of the import lines (and of parenthesized imports) in `.py` and
   `.qmd` files for the module's name, are all among the files the chain's
   baseline full review covered. Anything else gives a reason that
   requires a full review: a Level 3 path, a detected escalation trigger,
   a shared input of ADR 014 decision 4, a changed exported interface, a
   file named by a finding that a review already found still open, an
   undecidable search (a package `__init__`, a `__main__`, a dynamic
   import in the module or in any other file, a missing tree). There is no line count anywhere.
   `review-feature.sh --changes` reviews the changes only when the rule
   allows it and the level is 1 or 2; otherwise it reviews the complete
   feature and says why.
4. **The levels at the finish** (completion/v2 only; a completion/v1
   feature finishes under the rule it started with). Level 1: no review
   needed, recorded as "Review: none required (Level 1, ADR 020 decision
   4)", and `--no-review` is refused at Level 1; a review that exists is checked as at
   Level 2. Level 2: the chain from the latest review back to a full
   review is contiguous (each review of changes builds on the round
   before it, its tree, and the same merge base), every review of changes
   in it is bounded (checked again), every disposition is present, and no
   finding is open. Level 3: every review is full (a round of changes
   anywhere in the reviews is refused), the latest on the full
   verification, and no finding is open; `review-feature.sh` makes no
   review of changes at Level 3, and `run-feature.sh` asks for none.
5. **Mechanical triage.** `triage-review.sh` triages a review at Level 1
   or 2 (completion/v2; the level derived again from the base and the
   current content, and equal to the review's recorded one) whose findings
   are all minor or suggestion without an agent and without a question:
   a minor finding is deferred with a follow-up Issue made from the
   finding, a suggestion is accepted, each with the rule as its reason;
   the artifact says `mechanical: true` and is published once. A review
   with a critical or major finding, and every review at Level 3, keeps
   the full triage with the owner's approval. `triage_artifact_errors`
   refuses a mechanical triage with a critical or major finding, or
   whose decisions differ from the rule (a minor finding not deferred
   with its follow-up Issue, a suggestion not accepted);
   `finish-feature.sh` refuses such a triage, and any mechanical one at
   Level 3.

## Files

`scripts/lib/fingerprint.sh`, `scripts/lib/review-chain.sh` (new),
`scripts/lib/review-data.sh`, `scripts/lib/review-run.sh` (stores the
dispositions), `scripts/lib/risk.sh`,
`scripts/check-review.sh` (unchanged: it reads `fingerprint_review`),
`scripts/review-feature.sh`, `scripts/finish-feature.sh`,
`scripts/triage-review.sh`, `scripts/run-feature.sh`,
`.agents/schemas/feature-review.schema.json`,
`.agents/prompts/reviewer.md`, `.agents/prompts/triage-reviewer.md`,
`.agents/policies/autonomy.md`, `docs/development.md`, `docs/workflow.md`,
`docs/evaluation.md` (the review rule of the final round, review 02),
`scripts/verify-workflow.conf` (one added check), tests
`tests/review-chain-test.sh` (new) and additions to the fingerprint,
review, finish, and triage tests.

## Template-synced files changed

Carry these to the template repository, or keep them through the merge of
`sync-template.sh`: the scripts, prompts, schema, policy, tests, and guides
above, all of which the template lists.

## Risk

Level 3 by its paths (the gate scripts, the prompts, the schemas, the
policy). Skills: none (no visual deliverable).

## Verification

Lint, format, and the shell tests of the changed workflow scripts, run
directly (the owner's instruction of 2026-10-24: no local full or targeted
run). The full run is CI's, pending for the gate `pr_ci`; the owner's
approval of the exact head is pending for `owner_approval`; the six
measurements of ADR 020 decision 10 after the pilot are `post_merge`.
