# ADR 020: Risk-proportionate verification and review

## Status

Proposed with the planning of the change cycle
`risk-proportionate-workflow` (requirements decision 39;
`docs/changes/risk-proportionate-workflow.md`, human-supplied 2026-10-18,
version 2 of the workflow proposal with the owner's refinements R1 to R4);
accepted when that planning is approved. This record is the one
authoritative place for the rules of the agent workflow's risk levels,
evidence lifecycle, review chain, owner approval, and verification
budgets. It changes no invariant of `docs/architecture.md` and no
guarantee of the digest, the selection, the base provenance, the check
identity, the build, the deployment, the determinism check, the complete
CI run, or independent review (decision 9 below).

It amends the process statements, never the invariants, of
[ADR 002](002-regenerate-artifacts-and-display-by-reference.md) (the
lesson budget in its consequences),
[ADR 003](003-single-verification-entry-point-and-ci-budget.md)
decisions 5 and 6,
[ADR 005](005-workflow-self-tests-run-locally-on-workflow-changes.md)
decision 3 (its decisions 4 and 5 were reviewed with it, as the change
request's section 5 asked, and stand unamended: decision 5 below),
[ADR 012](012-parallel-verification-jobs-behind-one-required-check.md)
decisions 1 and 8,
[ADR 014](014-verification-proportional-to-the-change.md) decision 7 and
its consequences, and
[ADR 015](015-typical-pull-request-budget-of-twenty-minutes.md) decision
4, as decisions 5 and 6 below state; each of those records carries a
dated status line that names this record. It records in decision 8 that
[ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md)
decisions 1 to 6 and 9 stay proposed and paused, with the triggers that
reopen them; ADR 017 decisions 7 and 8 stay accepted and are built on. It
supersedes no decision of any ADR.

Delivered by F130 (decisions 1 to 3, 5, 6, and 7) and F131 (decision 4),
strictly one after the other; applied to features started after each
delivery is merged. A feature in progress finishes under the contracts it
started with (`AGENTS.md`, ADR 003, 005, 012, 014, 015, and 017 as they
stand on the day it started), with one stated exception, the merge
approval gate: the protected list of `.agents/policies/guardrails.conf`
that F130 brings in line with the Level 3 paths of decision 1 is read by
`scripts/check-guardrails.sh` from the base branch as it is at the check,
by the file's own design (a feature cannot relax the rules it is checked
by), and the code-owner rule of decision 3 is enforced by GitHub at the
merge whatever day the feature started. Both therefore knowingly apply
to every pull request finished or published after F130's merge: a
feature in flight that touches a path the wider list adds (such as
`docs/architecture.md`, `scripts/build-site.sh`, or `.agents/skills/`)
is reported as protected, is published without an agent merge, and needs
the owner's approval of its diff that it did not need on the day it
started. This adds only the owner's approval of the diff and changes no
verification tier, no review, and no evidence a feature in flight must
produce; grandfathering by reading the list at the merge base was
rejected, because it would let a feature choose the rules it is checked
by and would change nothing at the merge, where GitHub enforces the
code-owner rule regardless. The owner actions that decision 3 needs
(the second identity, the code-owners file, the ruleset) are not part of
any feature; an agent never performs them.

On 2026-10-19 the owner accepted, by approving the round 4 revision of
this planning's review (11:42 UTC), that the merge approval gate is the
one exception to the rule of requirements decision 39 that a feature in
progress finishes under the contracts it started with, for the reason
stated above; the requirements are not edited for it. The roadmap's
"Phase 7" rules, its reconciliation notes, F130, the F123 row of its
state section, and `docs/architecture.md` carry the same note.

On 2026-10-19 the owner accepted, by approving the round 1 revision of
this planning's review (10:56 UTC), that the policy updates the change
request's section 5 asks for, of `.agents/policies/autonomy.md` and the
Definition of Done of `AGENTS.md`, are delivered by F130 (its acceptance
criterion 10) and not by this planning: both are protected workflow
files outside the planner's file scope (`scripts/lib/scope.sh`). The
planning change's acceptance criterion that "the policy updates exist"
(the change request's section 7) is therefore met at F130's merge, and
the sentence of requirements decision 39 that both files refer to this
record holds from that merge; the requirements are not edited for it.

Date: 2026-10-19

## Context

The project's guarantees are strong and stay exactly as strong: every
pull request and push runs the complete verification in CI behind the one
required check `verify`; only the verified artifact is deployed; a pull
request reuses results only from a base whose provenance is established
(ADR 014); builds are deterministic; every feature of Medium or High risk
has an independent review by a different model; and no scientific check
is removed without coverage evidence (ADR 017 decision 8).

What has grown is the lead time of a feature under them. The change
request measured it on recent features (GitHub times in UTC; the local
verification and review counts from the working files of the worktrees,
which Git ignores and this planning could not re-read): one-character
lesson fixes took 12 to 16 minutes from the pull request to the merge
after 25 to 30 minutes of work; the fix of Issue #206 took 7 h 02 with
three review rounds, two triages, and three complete local verifications,
the first of 3708 s; F119 took 12 h 04 to merge and 20 h 38 to close;
F120 was open 67 h; F122 took 21 h 13 with two review rounds; F61 had
eight pull requests in two days and ten review files, and its Issue is
still open after six days. A pull request's CI takes 12 to 35 minutes, a push to `main` 29 to 39 at 38 lessons; a
feature takes hours to days. The largest items are a complete local
verification of about an hour after every change, a new full review round
and triage after every change however small, and an owner exception
(`--partial`, `--no-review`) needed five times in three days because a
criterion's evidence can only exist after the publication, after the
merge, or after the owner's approval. About half of the workflow gates
exist only as script behaviour with no ADR or `AGENTS.md` authority, and
`.agents/policies/autonomy.md` names three risk levels that no script
reads. ADR 017 and ADR 014 decision 11 (F113) are justified only by the
duration of a CI run, not by the lead time of a feature.

The verification matrix of the day, which `docs/architecture.md` records
as the standing reference ("The verification matrix"): in a full run,
every lesson is executed in three pages (`site-build`, `determinism`, and
the page reproduction of `site-checks-reproduction`), once as its
experiment through the learner path (the second test of
`site-checks-reproduction`), and once in the unit tests (`code`); run in
parallel, the critical path of CI is `build` and then the `e2e` jobs; run
sequentially on one machine, a complete verification is about 68 minutes
at 38 lessons (about 4 `code`, 4 `workflow`, 22 `integration`, 21 `build`,
17 `e2e`), of which `./scripts/verify.sh --only code,integration-other`
is about 13.

How the agent works: with the owner's own GitHub login. A comment, a
review, a label, a file, or a flag that the agent's login writes is
therefore never evidence of the owner's approval to a script, and
`docs/development.md` says so ("Your approval is your own merge"): the
merge approval gate is an agreement, not a lock. On the day of this
record the ruleset `protect main` of the repository requires a pull
request with zero approving reviews and no code-owner review, requires
the status check `verify`, and has no bypass actors;
`.github/CODEOWNERS` names only the owner's own login (read from the
GitHub API, 2026-10-19).

## Decision

1. **Three risk levels, raised freely and lowered only by the owner.**
   Every change carries one level, the highest of three readings:
   - *The minimum its paths imply.* Level 1: documentation and process
     files only (documentation outside the ADRs and the planning
     documents; `.agents/plans/`, handoffs, summaries). Level 2: lessons,
     `src/`, tests, and scripts that are not Level 3. Level 3: the
     following paths, which this list names directly and authoritatively
     (requirements decision 39 and the change request's section 3.1
     enumerate them; `.agents/policies/guardrails.conf` protects, on the
     day of this record, only `scripts/verify.sh` beyond its always
     protected set, and F130 brings its protected list in line with this
     one, so that from F130's merge "the protected paths of
     `guardrails.conf`" in the requirements is this list):
     - the ADRs, `docs/decisions/`;
     - the planning documents: `docs/PROJECT_REQUIREMENTS.md`,
       `docs/roadmap.md`, and `docs/architecture.md`, which carries the
       invariants I1 to I32 and is in the planner's file scope with the
       roadmap and the ADRs;
     - the CI workflows, `.github/workflows/`, and `.github/CODEOWNERS`
       itself;
     - the gate: the scripts of the workflow (`scripts/*-feature.sh`,
       `scripts/*-planning.sh`, `scripts/lib/`, `scripts/check-guardrails.sh`,
       `scripts/check-review.sh`, `scripts/ci-aggregate.sh`), the prompts
       `.agents/prompts/`, the schemas `.agents/schemas/`, the policies
       `.agents/policies/` (among them `guardrails.conf` and
       `autonomy.md`), `AGENTS.md`, `.agents/agents.conf`,
       `scripts/verify.conf`, and `scripts/verify.sh`;
     - the digest and the selection, `src/pbc/authoring/digest.py` and
       `src/pbc/authoring/selection.py`;
     - the base and its provenance, `scripts/fetch-base.sh`,
       `scripts/collect-base.sh`, and `src/pbc/authoring/provenance.py`;
     - the build and the deployment, `scripts/build-site.sh` and the
       deploy job of the CI workflow;
     - the agent skills, `.agents/skills/`;
     - the approval requests, `.agents/approvals/` (decision 3), which
       are code-owned, so that GitHub requires the identity's review of
       every pull request that carries one, but **do not count in the
       path minimum**: the request is the vehicle of a level reached by
       a trigger or by assessment, or of a lowering, and never raises the
       level of the change it belongs to; a change whose only Level 3
       path is its own approval request is not Level 3 by path.
   - *The escalation triggers*, any one of which raises the level to 3
     wherever the files are: a changed scientific claim, which is a
     change to or a removal of a claim that `main` already publishes (a
     number, a tolerance, an acceptance rule, a theory comparison, or
     what a figure shows, in a lesson or a check already on `main`); the
     claims a new lesson introduces are not this trigger, so a feature
     that adds a lesson stays at Level 2 by its paths, with the
     independent scientific review by a different model that decision 9
     keeps for Levels 2 and 3, and is Level 3 when it changes or removes a
     published claim or hits another trigger (the parallel reading of the
     next trigger, which covers weakening and removal, never new tests);
     weakened test strength (an assertion weakened or removed, a
     tolerance or budget widened, a new skip or expected failure, a removed
     test, a changed marker such as `same_machine`); security (permissions,
     secrets, credentials, network access, fetching or executing external
     content, the provenance of a base); verification guarantees (anything
     touching the check identity, the selection, the digest, the base,
     determinism, the build, the deployment, or a gate); and dependency
     selection (`pyproject.toml`, `uv.lock`, the Lean toolchain and
     manifest, action versions, vendored skills, pins of external tools).
     The scripts detect the mechanically detectable triggers on the diff
     against the base branch (a widened tolerance or budget, a new skip or
     expected failure, a removed assertion or test, a changed dependency
     file); the agent names the others in its completion record; the
     independent reviewer assesses every trigger with the impact
     classification it already fills (`architecture_impact` and its
     rationale), reporting a trigger the record missed as a major finding.
     No new agent and no new report.
   - *The assessed level*: the level the agent or the reviewer assigns,
     which may only be higher than the two readings above.

   An agent may raise the level at any time. **No agent lowers a required
   level.** A level is lowered only by the owner's authorization of
   decision 3, verified at the merge gate; a script refuses a recorded
   level below the path minimum of the change, refuses a recorded level
   below a trigger reading unless the committed approval request of
   decision 3 names that lowering, and refuses to lower a recorded level
   on an agent's statement alone. What a lowering means:
   - *What may be lowered.* The owner's authorization may lower a reading
     reached by an escalation trigger (mechanically detected or named by
     the agent or the reviewer) or an assessed level, down to the path
     minimum of the change and never below it. The path minimum is never
     lowered: the Level 3 paths are enforced by GitHub through
     `CODEOWNERS` whatever level is recorded, so a lowered path minimum
     would have no meaning at the merge, and the change request's section
     3.1 makes the paths a conservative minimum. The approval request's
     own path does not count, as the list above says.
   - *Until the owner has authorized the lowering, the change keeps its
     required level*: finish, review, triage, and verification run at the
     required (higher) level. The owner's explicit word in the
     conversation, naming the Issue and the level requested, is what lets
     the agent proceed at the requested level; the agent records that
     word in the approval request of decision 3 (a request, never proof to
     a script), the scripts record the required level, the requested
     level, and the head they apply to, and the identity's approving
     review of the exact head at the merge gate (or, until mechanism A
     exists, the owner's word naming the head) is the verification. A
     lowering the owner refuses, or that the identity has not approved
     for the head to be merged, means that the finish, the review, and
     the verification are redone at the required level before the merge.
     No script accepts the approval request, or any agent statement, as
     the authorization.

2. **One evidence lifecycle: criterion gates, `pending`, and one meaning
   of `complete`.** The completion record (`.agents/completion/<issue>.json`)
   stays the single record with its three statuses `complete`, `partial`,
   and `blocked` and their present meaning, and gains one attribute per
   criterion: the gate that clears it, one of `implementation` (tests,
   the local verification, the review chain), `pr_ci` (CI green on
   exactly the published head), `owner_approval` (the owner's approval of
   the exact commit, verified at the merge gate by decision 3), or
   `post_merge` (a measurement or an observation that can only exist after
   the merge). A criterion is `met`, `not_met`, `not_applicable`, or
   `pending`; `pending` is allowed only for the last three gates, names
   that gate, and is never allowed for `implementation`. **`complete`
   keeps one meaning: every acceptance criterion of the Issue is met** (or
   not applicable); a record with a pending criterion is `partial`, as
   today. Three readiness points are derived from the record and never
   stored as states:
   - *ready for a pull request*: every `implementation` criterion is met;
     pending `pr_ci`, `owner_approval`, and `post_merge` criteria do not
     stand in the way of committing and publishing;
   - *ready for merge*: additionally the `pr_ci` criteria are met by CI on
     the exact head, the review chain of decision 4 is current and covers
     the implementation, no major finding is open, and for Level 3 the
     owner's approval of the exact commit is verified by decision 3;
   - *done*: every criterion met, so `complete`; the Issue may close.

   Consequences: `finish-feature.sh` and `publish-feature.sh` accept a
   record whose only unmet criteria are pending for later gates, without
   `--partial`, `--no-review`, or any owner exception; the pull request
   then does not close the Issue (draft or ready, the agent's choice), and
   the Issue closes when the record says `complete`; pending CI blocks the
   merge, never the preparation or the publication of the pull request;
   outstanding post-merge evidence keeps the Issue open and never blocks
   the merge; an open major finding is never a pending criterion; and the
   reviewer's guidance says that a criterion whose evidence belongs to a
   later gate is not a finding. No new state machine.

3. **Owner approval is verified once, at the merge gate, by GitHub, and
   never from an agent's assertion (mechanism A).** The owner's approval
   of a Level 3 change, and an authorization to lower a level, are
   pre-merge requirements given as **an approving review of the pull
   request by a second GitHub identity that only the owner holds and no
   agent ever uses**, which names the head commit it applies to and, for
   a lowering, the level. GitHub enforces it at the merge: the ruleset of
   `main` requires a review from code owners, with zero required approving
   reviews so that Level 1 and 2 pull requests need no GitHub review, and
   `.github/CODEOWNERS` assigns the Level 3 paths of decision 1 (the one
   list, which includes the approval requests below and
   `.github/CODEOWNERS` itself, so that the code-owners file cannot be
   changed without the identity's review) to that identity. The planning recommends, for
   the owner's setup, that the ruleset also dismisses stale approvals on
   push and requires the last push to be approved, so that an approval
   never carries over to content pushed after it (R3: the approval
   applies to the exact commit), and that the bypass list stays empty.
   - *A Level 3 change that no protected path marks* (a level reached by
     an escalation trigger or by assessment) and *every lowering request*
     are made visible to GitHub by a committed **approval request**,
     `.agents/approvals/<issue>.md`, a code-owned path: it names the
     Issue, the level and how it was derived (paths, triggers, assessment),
     the tree it was written for, and for a lowering the required level,
     the level requested (a trigger reading or an assessed level, never
     the path minimum; decision 1), the reason, and the owner's word in
     the conversation that let the agent proceed at the requested level.
     `finish-feature.sh` refuses a Level 3 record without
     it and refuses a lowering without it, so the pull request touches a
     code-owned path and GitHub requires the identity's review. The file
     is a request, never an approval: no script reads it as the owner's
     decision, its own path raises no level (decision 1), the identity's
     approving review of the exact head is the authorization it asks for,
     and a lowering the identity has not approved for that head is redone
     at the required level before the merge (decision 1).
   - *What the scripts do*: `finish-feature.sh`, `review-feature.sh`,
     `triage-review.sh`, and `publish-feature.sh` only record what is
     required and the head (or tree) it applies to, in the commit message,
     the review, and the pull request, without network requests to verify
     an approval. **No script accepts an agent-written assertion, a
     comment or review by the agent's own login, a file, a flag, or a
     statement in chat as the owner's approval**; a test shows that a
     forged assertion is refused. An agent that merges applies GitHub's
     decision: it merges a Level 3 pull request only when GitHub reports
     the identity's approving review of the exact head, and never
     dismisses, re-requests, or works around a review.
   - *Owner actions, never an agent's*: create the second identity and
     grant it write access; change the ruleset of `main` (code-owner
     review required, zero approving reviews, stale approvals dismissed
     on push, last-push approval required, no bypass actors); change
     `CODEOWNERS` to name the identity for the Level 3 paths of decision
     1, `.agents/approvals/` and `.github/CODEOWNERS` among them; and
     verify with one test pull request that a Level 2 pull request needs
     no review while one that touches a code-owned path cannot be merged
     without the identity's approval. The agent's `gh` login never holds
     the identity's credentials. The owner may also give the agent a
     token without administration rights on the repository (an option
     for the owner's setup, not a requirement of this record; see the
     residual risks).
   - *Until the identity, the code-owner rule, and the ruleset change
     exist*, the present practice continues: an agent merges a Level 3
     change only after the owner's explicit word in the conversation and
     states the head commit it applies to; F130's merge-gate verification
     is tested against the recorded ruleset and the forged assertion, and
     relied on from the day the owner's setup is in place.

4. **Review in proportion to the level: none, a traceable chain, or full
   every round.** Level 1 needs no independent review. Level 3 keeps a
   full review in every round. Level 2 allows an initial full review
   followed by a traceable chain of delta reviews, and nothing more
   elaborate:
   - *Traceable chain.* Each review records the tree it compared against
     (the reviewed tree of the previous round) and the tree it reviewed.
     The chain begins with a full review and ends with a review whose
     reviewed tree is exactly the current tree; a gap or a break means a
     full review. `finish-feature.sh` verifies the chain for Level 2
     instead of requiring that the last review is a full one.
   - *Disposition of earlier findings.* Every finding has a stable
     identifier. Each later review states, for every earlier open finding,
     whether it is resolved (with the evidence), still open, or accepted.
     Finish requires that no finding is open.
   - *Full review when the impact cannot be bounded reliably.* There is
     **no changed-lines threshold** and **no general-purpose impact
     graph**. A delta review is allowed only when the delta is confined to
     kinds of change whose reach is certain: tests, documentation, lesson
     content, and a change to one source module whose importers are all
     among the files the baseline review covered, found by a plain textual
     search for the module name with the import knowledge the digest
     already has. Anything else requires a full review: a Level 3 path, an
     escalation trigger, a shared input of ADR 014 decision 4, a change to
     an exported interface, a file with an earlier unresolved finding, or
     any case where the search cannot decide.
   - *The fingerprint.* The completion record and the handoff note are
     part of what a review fingerprints, so that neither can change after
     the review without making it stale.
   - *Triage.* Minor and suggestion findings at Levels 1 and 2 are triaged
     mechanically: an automatic ACCEPT or DEFER with a reason, published
     once, with a follow-up Issue for every DEFER; a critical or major
     finding, and every finding at Level 3, keeps the full triage per
     finding with the owner's approval of the triage.

5. **Verification in proportion to the level, with unchanged final
   guarantees.** The tier a change needs is the one ADR 017 decision 7
   gives it (the targeted run, `--base`, or the full run, decided by the
   selection and the change type), at every level. For Level 3,
   **intermediate fix rounds may use targeted partial verification**: the
   groups the changed paths touch, through `./scripts/verify.sh --only
   <group>`, plus the unit tests of the changed modules (typically `code`
   and `integration-other`, about 13 minutes against about 68 for a
   complete run). That is quick feedback and **never evidence**: ADR 012
   decision 1 stands in that a run with `--only` verifies nothing and
   records nothing. **The final acceptance of a Level 3 change is always**
   a complete verification of the final tree, then a complete independent
   review of that tree made after the verification (a review made with
   `--unverified` never counts as the final review), and then the full CI,
   which stays the publication gate; `finish-feature.sh` requires the
   latest review of a Level 3 change to have been made on a verified
   tree. The targeted tier (`targeted: default,code`) stays refused when
   the check identity differs from the base's, because that is the
   fail-safe. The Level 3 rule amends ADR 005 decision 3 only; this
   decision adds nothing to ADR 003 decision 1, as ADR 005 decision 5
   restates it, beyond what ADR 017 decision 7 already changed, and it
   changes nothing of what a run without options does.

6. **Budgets are measured, decided by the owner at the chosen points, and
   never optimised against scientific content.** An exceeded wall-clock
   budget (the 20 minutes of ADR 015, the planning budget of a full run,
   the 45-minute trigger below) is recorded as a measurement and decided
   by the owner at the re-assessment points already chosen: re-measure at
   42 lessons, decide the capacity at 44 at the latest, or earlier if a
   complete run on `main` exceeds 45 minutes. It starts no mandatory
   optimisation work and never changes scientific content; the order of
   responses of ADR 003 decision 6 is what the owner chooses from, not a
   standing obligation. Hard checks, such as the 30-second lesson page
   budget, remain able to fail, with the documented exception table
   `scripts/lesson-budgets.conf`, whose header carries this policy (an
   exception needs a reason and the owner's approval; a lesson over its
   budget still fails). This amends the budget rows of ADR 002
   (consequences), ADR 003 decision 5, ADR 012 decision 8, ADR 014
   decision 7, and ADR 015 decision 4 in one respect only: an exceeded
   wall-clock budget is a measurement for the owner's decision, not a
   failed gate and not a mandate.

7. **A time log, and no needless re-fetch of the base.** `./scripts/verify.sh`
   appends one line per run (timestamp, tier, tree, duration, result) to a
   per-machine log outside the worktrees that is never committed and that
   no gate reads; the evaluation of decision 10 reads it afterwards.
   `scripts/fetch-base.sh` does not fetch again when the latest accepted
   run on `main` is the one already recorded, keeping the provenance rule
   of ADR 014 decision 2 as it is (the record of the producing run decides,
   never recency).

8. **ADR 017 decisions 1 to 6 and 9, and F113, stay paused.** Neither is
   justified by lead-time evidence. ADR 017 decisions 1 to 6 and 9 are
   not accepted, F113 (Issue #150) stays paused and open, F121 is not
   started, and F120 is finished (its evidence was published by pull
   request #224; Issue #196 closed on 2026-10-19). They are reopened only
   at the owner's triggers of decision 6 (42 lessons measured, 44 decided,
   or a complete run on `main` above 45 minutes). ADR 017 decisions 7 and
   8 stay accepted and are the tiers this record builds on.

9. **What stays exactly as it is, and is Level 3 to touch.** The complete
   CI run on every pull request and push; the aggregate required check
   `verify` and the deployment of only the verified artifact; the digest,
   the selection, the base provenance (including the stamped ref of F61
   M3) and the check identity, with the safe fall-back to executing
   everything; independent review by a different model for Levels 2 and
   3; no scientific check removed without coverage evidence (ADR 017
   decision 8); and the invariants I1 to I32 of `docs/architecture.md`.
   No new mandatory agent and no new mandatory reporting gate.

10. **Delivery in two bounded features, in order, and the evaluation.**
    F130 delivers decisions 2, 1, 3, 5, 6, and 7, and brings the
    protected list of `.agents/policies/guardrails.conf` in line with the
    Level 3 paths of decision 1 (the file's header says the owner decides
    the list, and F130's diff has the owner's approval); F131 delivers
    decision 4 (and applies decision 1 to the review: no review at Level
    1, the chain at Level 2, mechanical triage). Each is Level 3 with the owner's
    approval of its diff before the merge, under the contract it started
    with. F131 does not start until F130 is merged and two features have
    run under it with their effect observed (owner's answer, 2026-10-19),
    so that two changes to the workflow scripts (`scripts/lib/*`,
    `finish-feature.sh`, `review-feature.sh`, `triage-review.sh`,
    `apply-triage.sh`, `publish-feature.sh`, `verify.sh`) are never in
    flight together. The evaluation is a pilot of five features under the
    new rules after F131 is merged (two after F130 for its own effect),
    with six measurements derived afterwards from existing artifacts
    (GitHub, the review and verification records, the handoff notes, the
    time log) and no new report, agent, or gate: the total lead time of
    each feature from the Issue's creation to its merge and its closure;
    the number and total duration of verification runs per feature; the
    review rounds per feature with their time stamps and chain status;
    the owner's waiting time from a pull request or question being ready
    to the owner's next comment or merge; the defects missed by the
    reduced process (a defect found after the merge in a Level 1 or 2
    change that the full process could have caught gets an Issue with
    the label `process-miss`; a miss in an escalation-trigger category
    stops the pilot and puts that level back at full strictness until the
    owner decides); and the baseline of the change request's section 1.

## Alternatives considered

- **Mechanism B: an approval artifact signed with a key only the owner
  can use** (a signed tag or commit verified by a local script against an
  allowed-signers file immediately before the merge). Equally unforgeable
  by an agent; rejected by the owner for this cycle because it needs a
  script to be trusted at the moment of the merge and a key the owner's
  machine holds behind a passphrase or token, while mechanism A needs no
  script to trust anything and is checked by GitHub at the merge itself.
  It stays the alternative if a second identity proves impractical.
- **A comment, a label, a review, or a flag written by the owner's own
  login.** Rejected: the agent works with that login, so none of it
  distinguishes the owner from the agent (change request, 3.4).
- **A changed-lines threshold or a general-purpose impact graph for delta
  reviews.** Rejected (R1): a threshold mistakes size for reach, and an
  impact graph is infrastructure the project would have to verify; the
  kinds of change whose reach is certain, with the digest's import
  knowledge, are enough, and everything else is a full review.
- **New states or a second record for the evidence lifecycle.** Rejected
  (R2): the readiness points are derived from the one completion record;
  a second state machine would have to be kept consistent with it.
- **A reporting agent or a CI job for the risk level.** Rejected: no new
  mandatory agent and no new mandatory reporting gate; the independent
  reviewer already classifies the impact, and GitHub already enforces the
  review for the paths. A CI job on the pull request's diff would need
  `pull_request_target` or would run the pull request's own code, both of
  which the project rules out (invariant I15, the guardrails job not
  installed).
- **Optimising the full run now** (lesson shards, incremental `main`,
  self-hosted runners). Deferred with ADR 017 and F113 (decision 8): not
  justified by the lead-time evidence; the owner's triggers reopen them.

## Consequences

- A feature whose only unmet criteria wait for CI, the owner, or a
  post-merge measurement is committed and published as a matter of
  course, and its Issue stays open until the evidence exists; the five
  owner exceptions of three days become none of that kind.
- A Level 3 feature spends about 13 minutes instead of about 68 on each
  intermediate fix round, and exactly one complete verification and one
  full review on its final tree; nothing it publishes rests on a partial
  run.
- A Level 2 feature reviews its deltas when their reach is certain and is
  reviewed in full when it is not; every finding is followed to its
  disposition; minor and suggestion findings no longer wait for a triage
  session.
- The owner's approval of a Level 3 change becomes a GitHub review from a
  second identity, which an agent cannot give, cannot forge, and cannot
  carry over to a later commit, because GitHub checks the identity and
  the head; what GitHub does not exclude is stated under the residual
  risks below. Until the owner's setup exists, the
  present practice (the owner's word in the conversation, naming the head)
  continues, and the scripts already refuse every forgeable form.
- Owner actions this record needs, outside any feature: the second
  identity with write access; the ruleset change (code-owner review
  required with zero approving reviews, stale approvals dismissed on push,
  last-push approval required, no bypass actors); the `CODEOWNERS` change
  (the Level 3 paths of decision 1, with `.agents/approvals/` and
  `.github/CODEOWNERS` itself, to the identity); and the
  test pull request that shows a Level 2 pull request needs no review and
  a code-owned change cannot be merged without the identity. This planning
  could not perform that test (the ruleset has no code-owner rule today,
  and an agent changes no repository setting and opens no pull request),
  so the recommended default of requirements decision 39 is verified by
  the owner's test, recorded on the Issue of F130. Once the ADRs are
  code-owned by the identity, every planning pull request and every ADR
  amendment needs its approving review too, which is the Level 3 that
  decision 1 gives the planning documents.
- Residual risk, stated: the escalation triggers that are not mechanically
  detectable, and the assessed level, rest on the agent's record and the
  independent reviewer's classification, as the merge approval gate's
  `architecture_impact` does today; an agent that records a Level 3 change
  by trigger as Level 2 and no reviewer that catches it is the
  `process-miss` case that stops the pilot (decision 10). The Level 3
  paths are enforced by GitHub regardless.
- Residual risk, stated: mechanism A excludes forgery, not circumvention.
  The agent works with the owner's own login, which administers the
  repository; that login can change the ruleset of `main` through the
  API or the settings, and could merge a change to `.github/CODEOWNERS`
  if the file were not code-owned. GitHub's enforcement is therefore not
  independent of the agent's credentials: what holds the agent back from
  editing the ruleset or the code-owners file is the policy that an agent
  never changes a repository setting (the requirements, "Authentication
  and authorization"; the change request's section 8), not a lock. The
  planning reduces the surface by code-owning `.github/CODEOWNERS` itself
  (decision 1, decision 3), so that a change to the code-owners file
  needs the identity's review like any other Level 3 path, and names one
  owner-side mitigation as an option: an agent token without
  administration rights on the repository (a fine-grained token, or a
  login that is not an administrator), which turns the policy into a
  lock for the ruleset too. The owner decides whether to set it up; the
  record requires only that an agent never holds the identity's
  credentials and never changes a repository setting.
- `AGENTS.md` ("Definition of Done") and `.agents/policies/autonomy.md`
  refer to this record and define the levels and the evidence states;
  both are protected workflow files outside the planner's scope, so F130
  changes them with the scripts (the owner's acceptance of 2026-10-19,
  recorded in the status above). `docs/development.md` and
  `docs/workflow.md` describe the behaviour the features deliver.
- The measurements of the pilot decide what comes after: a further
  relaxation is a new change cycle; a `process-miss` in a trigger
  category restores full strictness at that level without one.
