# Plan: F130, risk-proportionate workflow, part 1 (Issue #236)

Delivers ADR 020 decisions 1, 2, 3, 5, 6, and 7 in the scripts, the
schemas, the prompts, the policies, and the guides, without changing what
a verification executes, what CI runs, or what a review is. Written by the
implementer at the start of the feature (the Issue expects a detailed plan
and none existed), at base `2a1fea4` (2026-10-19).

## Goal

Acceptance criteria 1 to 11 of Issue #236, in its words; the evaluation's
first measurement (two features after the merge) and the owner's test pull
request are evidence that can only exist after the merge.

## Current state, found at `2a1fea4`

- `scripts/lib/completion.sh`: `completion/v1`, criterion statuses `met`,
  `not_met`, `not_applicable`; `complete` needs no `not_met`. The gate's
  outcomes are `complete`, `partial`, `blocked`, `missing`, `invalid`;
  `finish-feature.sh` needs `--partial` for anything but `complete`, and
  `publish-feature.sh` opens a draft that does not close the Issue.
- No script reads a risk level. `scripts/lib/guardrails.sh` classifies the
  diff as protected or sensitive (builtin list plus
  `.agents/policies/guardrails.conf`, read from the base), and the
  reviewer classifies `architecture_impact`.
- `finish-feature.sh` and `review-feature.sh` run
  `./scripts/verify.sh --reuse --targeted`; `apply-triage.sh` too. No
  script merges a pull request; `run-feature.sh` ends with
  `MERGE APPROVAL REQUIRED` when the commit says so.
- `./scripts/verify.sh` keeps no time log; `scripts/fetch-base.sh`
  downloads the base on every run.
- `.github/CODEOWNERS` names only the owner's login, which is also the
  agent's; the ruleset has no code-owner rule (ADR 020, Context).

## Design decisions

1. **Two versions of the completion record.** `completion/v2` adds the
   gate per criterion (`implementation`, `pr_ci`, `owner_approval`,
   `post_merge`), the status `pending` (never for `implementation`), and
   the implementer's `risk` (`level` 1 to 3, the triggers it names, a
   rationale). `completion/v1` stays valid unchanged: it is the contract
   of a feature started before F130's merge (ADR 020, Status: a feature
   in progress finishes under the contracts it started with), and the
   existing tests (F119 among them) use it. The scripts derive and record
   the level for both versions; the refusals that rest on a recorded level
   and the Level 3 rules (approval request, complete verification, review
   on a verified tree) apply to a `completion/v2` record, which the
   implementer contract requires from F130's merge on. The review context
   says which version a record uses and whether the feature's base already
   knew `completion/v2`, and the reviewer reports a `v1` record of a
   feature started after F130 as a major finding.
2. **Readiness is derived, never stored.** The gate gets one more outcome,
   `pending`: the record says `partial`, no criterion is `not_met`, at
   least one is `pending` for a later gate, and the handoff note lists no
   remaining work (pending evidence goes under "Pending"). That is "ready
   for a pull request": `finish-feature.sh` commits it without
   `--partial` and writes `Readiness:` with the pending criteria and their
   gates; `publish-feature.sh` opens a pull request that is ready for
   review and does not close the Issue; `run-feature.sh` treats it like
   `complete` for the review and the commit.
3. **The risk level** (`scripts/lib/risk.sh`): the highest of
   - the path minimum: Level 3 for every path the merge approval gate
     reports as protected (the builtin list and the protected list of
     `guardrails.conf` from the base), except `.agents/approvals/`;
     Level 1 when every other changed path is documentation or a process
     file (`docs/`, top-level `*.md`, `.agents/plans/`, handoffs,
     summaries); Level 2 otherwise;
   - the mechanical triggers on the diff against the merge base: a changed
     or removed tolerance or budget line (Python lines naming `rtol`,
     `atol`, `tol`, `tolerance`, `budget`, `approx`, `isclose`,
     `allclose`, with a number, and such a Python line added (triage M1 of
     review 05); a data line of
     `scripts/lesson-budgets.conf`), a new skip or expected failure, a
     removed or changed assertion or a removed test (an `assert` or
     `def test_` line that is not added back unchanged; in a shell test, a
     line that calls `fail`, exits with a failure, or calls an `expect_` or
     `assert_` helper; in Lean, a `theorem`, `lemma`, or `example` line or
     a `#guard`-like command, and a new `sorry`, `admit`, or `axiom`
     (triage M2 of review 01); a deleted test file), a changed marker (`pytest.mark.*`, `same_machine`), and a
     changed dependency file (by name: `pyproject.toml`, `uv.lock`, the
     Lean toolchain and manifests, and the usual manifests and lock files
     of other ecosystems). Conservative: a narrowed tolerance is reported
     too, and the owner may lower the reading;
   - the triggers the record names and the level it records, and the
     level the review assesses (`architecture_impact.risk_level` and
     `architecture_impact.escalation_triggers`, in the schema the
     reviewer already fills).
   Refusals (`finish-feature.sh`, for a `completion/v2` record): a
   recorded level below the path minimum; a recorded level below a trigger
   or assessed reading unless the approval request names that lowering; a
   requested level below the path minimum; a request whose levels do not
   match the record and the derivation; a Level 3 change by trigger or
   assessment without the approval request. The change keeps its required
   level for every rule; the requested level is only recorded.
4. **The approval request** `.agents/approvals/<issue>.md`: Markdown with
   the fields `Issue:`, `Level:`, `Derived from:`, `Tree:`, and for a
   lowering `Required level:`, `Requested level:`, `Reason:`,
   `Owner's word:`. The scripts read the levels to check them against the
   record and print them; nothing reads it as an approval.
5. **The merge-gate verification** (`scripts/merge-feature.sh`, the merge
   step an agent uses; `run-feature.sh` still never merges and points to
   it): for a pull request that needs the owner (Level 3, a lowering, a
   protected or approval-request path, or a commit without the risk
   statement of `finish-feature.sh`; the assessed level is read from the
   latest review of the feature for exactly the head, never from the
   commit message, triage M2 of review 05), it merges only when GitHub reports
   the pull request mergeable (`mergeStateStatus` `CLEAN`, review decision
   approved) and the latest review of the owner's identity approves
   exactly the head: the one login of the line `owner-identity: <login>`
   of `guardrails.conf` of the base, a code owner other than the agent's
   own login (triage M1 of review 01: no other code owner counts);
   otherwise it refuses and says that the owner merges, as today. Without
   such a configured identity (today), mechanism A does not exist
   and it never merges such a pull request (the present practice). It
   takes no flag, file, comment, record, or statement as approval, and
   merges with `--match-head-commit`.
6. **Level 3 verification**: `review-feature.sh` at Level 3 needs a pass
   of the full run (`./scripts/verify.sh --reuse`), or `--feedback`, which
   runs `./scripts/verify.sh --only` for the feedback groups (`default`,
   `code`, `integration-other`) and records the review's verification as
   `feedback`; `apply-triage.sh` at Level 3 runs the same partial run as
   feedback; `finish-feature.sh` at Level 3 needs a recorded full pass of
   the current content and a latest review whose verification is a passed
   full run (`--unverified` and `--feedback` reviews are refused as the
   final review); `run-feature.sh` uses `--feedback` for intermediate
   Level 3 rounds and makes the last round a verified complete review.
   The targeted tier is untouched (still refused on a changed check
   identity).
7. **The time log**: `./scripts/verify.sh` appends
   `<UTC time> | <tier> | <tree> | <seconds> | <result>` per run to
   `<git common directory>/verify-time.log` (shared by every worktree of
   the clone, outside every worktree's files, never committed), or to
   `VERIFY_TIME_LOG`. Tiers `full`, `base`, `targeted`, `only:<groups>`;
   results `passed`, `failed`, `refused`, `reused`. No gate reads it.
8. **The base re-fetch rule**: `scripts/fetch-base.sh` makes every
   acceptance check as before and chooses the run as before; only the
   download is skipped when `<target>.fetched` records that run, the
   digest of its artifact, and the digest of the contents unpacked from
   it, the target still has exactly those contents, and its
   `provenance.json` names the run and its commit (triage M1 of review
   04: a base changed after its retrieval is fetched again).
9. **Lists and texts**: `guardrails.conf` protects the Level 3 paths of
   ADR 020 decision 1; `scripts/lesson-budgets.conf` carries the budget
   policy; `AGENTS.md` (Definition of Done) and
   `.agents/policies/autonomy.md` refer to ADR 020; the prompts (planner,
   implementer, reviewer, triage-implementer) and the guides
   (`docs/development.md`, `docs/workflow.md`,
   `docs/repository-setup.md`, `docs/release-readiness.md`,
   `docs/project-map.md`) describe the behaviour.

## Steps

1. `completion.sh` v2, gates, `pending`, the `pending` outcome; tests in
   `tests/completion-test.sh`.
2. `scripts/lib/risk.sh` (path minimum, triggers, readings, approval
   request, refusals, statement lines); `tests/risk-level-test.sh`, with
   the protected list of the real `guardrails.conf` checked by
   `check-guardrails.sh` (criterion 11).
3. `finish-feature.sh`: `pending`, the risk statement, the refusals, the
   Level 3 verification and review rules; `publish-feature.sh`: `pending`
   ready and not closing; `run-feature.sh`: `pending`, Level 3 rounds;
   `review-feature.sh`: the risk record, the context, `--feedback`, the
   full run at Level 3; `apply-triage.sh`: feedback at Level 3; the
   schema and `review-data.sh`. Tests in `tests/risk-workflow-test.sh`.
4. `scripts/merge-feature.sh`; `tests/merge-feature-test.sh` (forged
   forms, a lowering without the identity's review of the head).
5. The time log in `verify.sh`; `tests/verify-time-log-test.sh`.
6. The re-fetch rule; `tests/integration/test_fetch_base_refetch.py`.
7. `guardrails.conf`, `lesson-budgets.conf`, `AGENTS.md`, `autonomy.md`,
   the prompts, the guides; the new tests in
   `scripts/verify-workflow.conf` (added checks).
8. The full `./scripts/verify.sh`, last.

## Template-synced files changed

Carry these to the template repository, or keep them through the merge of
`sync-template.sh`: `AGENTS.md`, `.agents/policies/autonomy.md`,
`.agents/prompts/planner.md`, `.agents/prompts/implementer.md`,
`.agents/prompts/reviewer.md`, `.agents/prompts/triage-implementer.md`,
`.agents/schemas/feature-review.schema.json`, `scripts/lib/completion.sh`,
`scripts/lib/risk.sh` (new), `scripts/lib/review-data.sh`,
`scripts/finish-feature.sh`, `scripts/publish-feature.sh`,
`scripts/review-feature.sh`, `scripts/apply-triage.sh`,
`scripts/run-feature.sh`, `scripts/merge-feature.sh` (new),
`scripts/verify.sh`, `scripts/verify-workflow.conf`,
`tests/completion-test.sh`, `tests/risk-level-test.sh`,
`tests/risk-workflow-test.sh`, `tests/merge-feature-test.sh`,
`tests/verify-time-log-test.sh` (new), `docs/development.md`,
`docs/workflow.md`, `docs/repository-setup.md`, `docs/project-map.md`.
`.agents/policies/guardrails.conf` is listed by the template but holds the
project's own list. Project-only: `scripts/fetch-base.sh`,
`scripts/lesson-budgets.conf`, the pytest test,
`docs/release-readiness.md`.

## Risk

Level 3 by its paths (the gate scripts, the prompts, the policies, the
schemas, `AGENTS.md`): a full run last, a full review, and the owner's
approval of the diff with the head it applies to.

## Visual deliverables

None (a workflow change). Skills: none (no visual deliverable).

## Open questions

None. The owner's actions of mechanism A (the identity, the ruleset,
`CODEOWNERS`, the test pull request) are not part of the feature.
