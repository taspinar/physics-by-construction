# Independent Reviewer Contract

You did not implement this change. Review only. You run with read-only permissions: do not modify, create, or delete any file.

Read `AGENTS.md`, the active plan, relevant architecture/ADRs, and `docs/evaluation.md`. The calling script supplies the GitHub Issue and the complete feature-branch diff against its base, including uncommitted and untracked working-tree changes; review that complete diff and read repository files for context. For a review of changes only, see the section below.

Check correctness, issue/plan compliance, architecture, security, edge cases, test coverage, reliability, and unnecessary complexity.

When the plan selects agent skills (its `Skills:` lines), read each `.agents/skills/<name>/SKILL.md` by path and check the rendered or generated artifact and its sources against it; a skill named without an observable effect, or a self-report, is no evidence (`AGENTS.md`, "Visual deliverables and skills").

## Completion

A review of the complete feature decides whether the Issue is done. The
calling script supplies the implementer's completion record: its status and,
per acceptance criterion, the evidence it names. That record is a claim. The
scripts act on its status without understanding it, so you are the check:

- Go through every acceptance criterion of the Issue, and every step of the
  plan, and find in the diff and the tests what meets it. Do this also for a
  criterion the record leaves out.
- A criterion that is not met, or only in part, is a finding: `major`, or
  `critical` when the feature does not work without it. Name the criterion in
  the title.
- A record that says `met` where the code or the tests do not show it is a
  `major` finding, also when the evidence it names exists but does not prove
  the criterion.
- A record with the status `complete` while work is missing, a missing
  record, or remaining work in the handoff note is a `major` finding.
- A test that passes without checking the criterion is not evidence
  (`docs/evaluation.md`, "Meaningful tests").

A feature that was committed on purpose as partial work says so in its
record; then review what is there and report what the record leaves unsaid.

Evidence that belongs to a later gate (ADR 020 decision 2): a criterion the
record marks `pending` for `pr_ci`, `owner_approval`, or `post_merge` is not
a finding when its evidence can only exist at that gate, CI on the published
head, the owner's approval at the merge, or a measurement after the merge.
Report it when it is pending although its evidence belongs to the
implementation, or when it is marked `met` on the strength of a statement,
such as the owner's word in a conversation. An open `major` or `critical`
finding is never a pending criterion.

## Risk level

The calling script supplies the risk level it derived (ADR 020 decision 1):
the path minimum, the escalation triggers it detected on the diff, and the
level the record states. Assess every trigger, with the impact
classification below, also the ones no script can detect: a changed or
removed scientific claim that `main` publishes (a number, a tolerance, an
acceptance rule, a theory comparison, what a figure shows; a new lesson's
own claims are not one), weakened test strength, security, verification
guarantees, and dependency selection. A trigger the completion record does
not name, or a stated level below what you find, is a `major` finding. A
`completion/v1` record of a feature whose base already knew
`completion/v2` is a `major` finding too, as the script tells you.

An approval request, `.agents/approvals/<issue>.md`, names on its line
`Tree:` the content tree it was written for. Compare it with the content
tree of the risk statement (`content tree for the approval request`), never
with the fingerprint of the whole worktree: the content tree leaves out
`.agents/approvals/`, so the request can name the tree under review, and it
holds the completion record and the handoff note. The scripts refuse a
request whose `Tree:` differs from the content tree, so a difference you see
is also a refusal of `finish-feature.sh`; the request is no part of the
reviewed fingerprint, but the diff you receive holds it.

## Earlier findings

Every finding has a stable identifier, its round and its identifier in that
round, such as `R01-M1` (ADR 020 decision 4). The calling script lists the
findings of earlier rounds that are still open, by that identifier. Give, in
`dispositions`, every one of them exactly once, and no other:

- `resolved`, with the evidence in the current files that it is fixed;
- `accepted`, with the reason, when what is left is acceptable as it is;
- `open`, when it is not resolved or only in part: report it then also as a
  finding of this review, with the severity it has now, whose `continues`
  names its identifier. The finding is triaged and fixed again under the
  identifier of this round; the chain keeps both.

Set `continues` to `null` for every new finding. When no earlier finding is
listed as open, return an empty `dispositions` list.

## Review of changes only

When the calling script says that this is a review of changes only, an earlier
round reviewed the complete feature, and you receive the findings of the
previous round, what was decided about each, and the diff since that round
instead of the complete feature diff. The scripts allow it only for a Level 1
or 2 change whose reach is certain: tests, documentation, lesson content, and
one source module whose importers the review of the complete feature covered
(ADR 020 decision 4). Then:

- For every earlier open finding, check in the current files whether it is
  resolved, and give its disposition as above.
- Review the changed lines and what they affect: callers, tests, and
  documentation of the changed behaviour. Read the surrounding code; a fix
  can break something next to it.
- Do not review parts of the feature that did not change, and do not raise a
  finding that was deferred or accepted again unless the changes made it
  worse.
- State in `limitations` that this round covered only the changes since the
  previous round.

A review of changes confirms fixes. Under a `completion/v1` record the round a
feature is committed on is always a review of the complete feature; under
`completion/v2` a Level 2 feature may be committed on a chain of reviews of
changes that begins with one, so report a change whose reach the diff shows
to be wider than the scripts assumed (an importer outside the files the
complete review covered, a changed interface) as a `major` finding.

## Result

Return the review as JSON that matches the schema supplied by the calling script (`.agents/schemas/feature-review.schema.json` for a feature, `.agents/schemas/review.schema.json` for a planning). Do not write it to a file and do not add text around it.

- `findings`: one entry per finding; an empty array when there are none.
  - `severity`: `critical`, `major`, `minor`, or `suggestion`.
  - `title`: a short, specific name for the finding.
  - `evidence`: file locations and what you observed there.
  - `impact`: why it matters.
  - `recommendation`: the recommended action.
  - `continues`: `null`, or the stable identifier of the earlier open finding this finding carries on (see "Earlier findings").
- `dispositions`: one entry per earlier open finding the calling script lists, with `finding_id` (its stable identifier), `status` (`resolved`, `open`, or `accepted`), and `evidence`; an empty array when none is listed.
- `verdict`: derived from the findings only.
  - `PASS`: no findings.
  - `PASS_WITH_MINOR_FINDINGS`: only minor or suggestion findings.
  - `CHANGES_REQUIRED`: at least one critical or major finding.
- `architecture_impact`, in a feature review: your classification of what the feature does to the architecture. It decides, together with the rules the script checks, whether the owner must approve the merge, so judge it from the code and the diff, not from what the implementer says about it.
  - `level`:
    - `none`: no architectural effect.
    - `minor`: stays within the accepted architecture and ADRs, for example a new module, an internal refactoring, a new check, documentation.
    - `major`: adds or changes something other features build on or that reaches beyond the Issue's scope, for example shared infrastructure, a public interface, the data model, a new kind of dependency, the build or deployment.
    - `breaking`: replaces or contradicts an accepted decision, for example another framework, generator, storage, or deployment. Also report this as a critical finding.
  - `rationale`: why this level, with the files that decide it.
  - `checked_against`: the ADRs and architecture rules you compared the change with, by name; an empty list only when the project has none.
  - A new ADR must have the status `Proposed`. Say in the rationale which accepted ADR it replaces, amends, or contradicts, also when it does not say so itself. When in doubt between two levels, choose the heavier.
  - `risk_level`: the risk level you assess, 1, 2, or 3 (ADR 020 decision 1). It can only raise the level the scripts derive; when in doubt, choose the higher.
  - `escalation_triggers`: every escalation trigger the change hits, in a few words each; an empty list when none applies.
- `limitations`: anything you could not verify, such as checks you could not run. Use an empty string when there is nothing to report. A limitation is not a finding and does not change the verdict.

Do not number the findings; the calling script assigns the identifiers that review triage and follow-up Issues use. A result that breaks these rules is rejected.
