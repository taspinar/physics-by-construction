# Plan: the approval request leaves the fingerprint (Issue #266)

## Goal

Correcting the approval request `.agents/approvals/<issue>.md` (typically its
`Tree:` line) no longer makes a recorded verification or a review stale, and
a wrong `Tree:` is refused by a script at once, with the value to write. The
owner's decision of 2026-10-23 (the Issue): the smallest safe correction,
with the existing mechanisms.

## Acceptance criteria and their gates (ADR 020 decision 2)

| Criterion (Issue #266) | Gate |
| --- | --- |
| 1. `.agents/approvals` is in `FINGERPRINT_EXCLUDES`; an edit of the request leaves the fingerprint, a recorded verification, and a review valid | implementation |
| 2. `risk_assess` refuses a request whose `Tree:` (first token) differs from `RISK_CONTENT_TREE`, naming the right value; the other fields unchanged | implementation |
| 3. `.agents/plans/` stays in the fingerprint, with the evidence why | implementation |
| 4. Tests: request edit keeps the fingerprint; script, lesson, test, plan edits change it; wrong `Tree:` refused with the right value; right one accepted; lowering checked as before | implementation |
| 5. One sentence in `docs/development.md` and in the reviewer's prompt | implementation |

The owner's approval of the diff at the merge is the Level 3 process (ADR
020 decision 3), not a criterion of the Issue.

## Risk classification (ADR 020 decision 1)

Level 3 by its paths: `scripts/lib/fingerprint.sh`, `scripts/lib/risk.sh`,
`scripts/review-feature.sh`, `.agents/prompts/reviewer.md` are protected.
Trigger: verification guarantees (what a recorded verification and a review
cover changes). The final tree needs the full `./scripts/verify.sh`.

## Visual deliverables and skills

Skills: none (no visual deliverable; a change of the workflow scripts).

## Decisions

- **The approval request leaves the fingerprint** like the review and triage
  artifacts: it is removed from the index before the tree is written, so
  editing, adding, or removing it leaves the fingerprint as it is.
  `risk_content_tree` already left it out; its own removal is now redundant
  and is dropped.
- **What still guards it.** `fingerprint_artifacts` hashes every excluded
  directory, so a reviewer or a triage agent that edits the request is still
  detected (`scripts/lib/review-run.sh`, `scripts/triage-review.sh`). The path
  stays protected and code-owned (ADR 020 decision 3): the owner approves it
  with the diff at the merge. The new refusal in `risk_assess` checks its
  `Tree:` against the content tree, so `finish-feature.sh` refuses a wrong
  tree before any verification.
- **The diff the reviewer reads** is built from the fingerprint's index. With
  the request out of it, the requests that `main` already holds would show as
  deleted and the feature's own request would be missing. `review-feature.sh`
  therefore adds `.agents/approvals` back to the index of the review diff
  (only of the diff; `reviewed_tree` stays the fingerprint), so the reviewer
  still sees the request and compares its `Tree:`. The diff of a round of
  changes only compares two fingerprints and does not show an edit of the
  request; the script check covers the tree.
- **The path minimum and the triggers** diff `RISK_TREE`, now without the
  requests: the base's requests read as deleted there, and both readings
  already skip `.agents/approvals/` (the path minimum) or ignore Markdown
  outside tests (the triggers). No change.
- **The merge gate.** A request committed after the review leaves that review
  a review of the head (`merge-feature.sh`, `review_of_head`); the merge of a
  Level 3 change still needs the owner's identity's approval of exactly the
  head, which covers the request (`tests/merge-feature-test.sh`).
- **The plans stay in the fingerprint** (Issue, change 3). The plans of the
  recent features hold what the review rests on: the acceptance criteria and
  their gates (238, 239, 244: "Acceptance criteria and their gates"), the
  risk classification (238: Level 3 by assessment; 239, 244: Level 2 with the
  paths), the selected skills (`Skills:` lines in 238, 239, 244), and the
  design decisions that define the review scope (236: "Design decisions").
  An edit of a plan can change any of these, so it keeps a review stale.
- **ADR 020 is unchanged.** Decision 4 concerns the completion record and the
  handoff note, which Git ignores and the fingerprint already leaves out; the
  approval request is a protected, committed file whose content the owner
  approves at the merge, and only its place in the fingerprint changes.

## Steps

1. `scripts/lib/fingerprint.sh`: add `.agents/approvals` to the excludes;
   comments.
2. `scripts/lib/risk.sh`: the `Tree:` refusal; drop the redundant removal in
   `risk_content_tree`.
3. `scripts/review-feature.sh`: the request back in the diff's index.
4. Tests: `tests/fingerprint-test.sh`, `tests/risk-level-test.sh`, and the
   request helpers of the workflow tests that now must name the right tree.
5. Docs: `docs/development.md`, `.agents/prompts/reviewer.md`.
6. The approval request `.agents/approvals/266.md`, its `Tree:` computed
   after the completion record and the handoff note are final; then the full
   `./scripts/verify.sh`.
