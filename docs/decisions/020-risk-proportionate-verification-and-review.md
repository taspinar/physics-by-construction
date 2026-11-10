# ADR 020: Risk-proportionate verification and review

## Status

**Current rules: see [`docs/process.md`](../process.md) (Issue #404,
2026-11-07); this ADR is the history of the decision.** The text below is
kept as it was written. In force from this record: decisions 1 to 7 and 9,
and the addendum of 2026-11-05, delivered by F130 and F131 (decision 10).
The addendum of 2026-11-08 to decision 1 (Issue #412), proposed with that
Issue and accepted by its merge, takes `docs/architecture.md` and the
prompts other than `.agents/prompts/reviewer.md` out of decision 1's Level 3
list; decision 1 is read with it.
The addendum of 2026-11-09 to decision 1 (Issue #463, D12 of #446), proposed
with that Issue and accepted by its merge, sets which review findings are
about form and writes the approval request by script.
The addendum of 2026-11-10 to decision 1 (Issue #464, D10 and D11 of #446),
proposed with that Issue and accepted by its merge, makes a changed claim
span a detected trigger and pins the execution settings.
Superseded in part: the re-assessment points of decisions 6 and 8 (42 and 44
lessons, a run above 45 minutes) by the notes of 2026-10-21, 2026-10-24, and
2026-11-04 in ADR 014's status; decision 8's pause of ADR 017 and F113
stands. The owner's actions of decision 3 (the second identity, the
code-owners file, the ruleset) are accepted but not yet implemented, so the present practice it
names continues; `docs/process.md` says where the scripts and this record
differ.

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

### Addendum to decision 6 (Issue #383, 2026-11-05): one budget rule for every lesson

On 2026-11-05 the owner replaced the hard 30-second budget of a lesson, with
an exception for each lesson that came close, by one rule for every lesson:
"a measurement threshold at 30 s that warns, and a hard limit of 60 s for
every lesson". The reason is the evidence of Issues #374, #376, #261, #272
and #267: CI runners measure about twice the developer machine, so a lesson
at about 15 s locally sits at the edge of 30 s on CI, and three runs of
`main` in two days (41790340315, 41832366470, 41965790194) failed on one
lesson at 30.3 to 30.7 s alone. Decision 6 stands in everything else: the
budget stays a hard check, an exception needs a reason and the owner's
approval, and a budget is never met by changing the scientific content of a
lesson. It changes the number and adds one outcome:

- A render of a lesson page and the run of its experiment that take less
  than the warning threshold (30 s) pass silently; from the threshold up to
  the limit they pass and are reported as a warning in the report of the
  check, which never fails a verification; at the limit or above they fail.
  A duration exactly at a boundary belongs to the higher outcome (30 s warns,
  the limit fails), because the existing rule was "under the budget".
- The limit is 60 s for every lesson. A line of `scripts/lesson-budgets.conf`
  only raises the limit of one lesson above that and needs its reason and the
  owner's approval; a line at or below the limit is redundant and a test
  refuses it. `lessons/agents-abm/01-particles-in-a-box` keeps its 90 s
  (#272: its reproduction measured 67 to 69 s). The 60-second lines of
  `mechanics/08`, `mechanics/11` and `mechanics/12` (#261) are the default
  now and were removed; the lines proposed in #374 and #376 are not needed.
- The threshold and the limit are in that file and nowhere else: the shell
  check `scripts/check-lesson-pages.sh` and the reproduction tests of
  `tests/e2e/test_lessons.py` read it, and a test shows that they judge every
  duration the same way, at the boundaries and for the exception.
- Raising the threshold or the limit is the escalation trigger "a budget
  widened" and is Level 3. This addendum changes no wall-clock budget of a
  run, no payload budget (#264, #318, #319), and the build timeout of 120
  minutes (#373) stays what it is. It amends the lesson budget in the
  consequences of ADR 002, decision 5 of ADR 003 and the row "one lesson page,
  executed" of its table, in the same respect as decision 6 above.
  The dated notes of ADR 002 and ADR 003 say so. In `docs/PROJECT_REQUIREMENTS.md`
  one sentence is synchronised, by the owner's word of 2026-11-06 on this
  Issue (option 1: a factual update of the one statement, no planning change):
  decision 30's "30-second lesson page budget keep failing" now names the
  limit of 60 seconds with the warning from 30. No other line of the
  requirements and no line of the roadmap changes.

### Addendum to decision 1 (Issue #412, 2026-11-08): the architecture document and the prompts are sensitive

Status: Proposed with Issue #412; accepted when its pull request is merged
with the owner's approval of the exact commit.

On 2026-11-07 the owner decided points 1 and 3 of Issue #396, and on
2026-11-08 the route and two exceptions (Issue #412, "Decisions of
2026-11-08"). Decision 1 stands in everything else; its list of Level 3
paths changes in three respects:

- **`docs/architecture.md` leaves the Level 3 list** and is sensitive in
  `.agents/policies/guardrails.conf`: the independent reviewer is told to
  look at a change to it. Its path minimum is **Level 2**, not Level 1 like
  the other documentation, so that an ordinary change to it always gets an
  independent review and the verification tier that fits the change. When
  its content touches an escalation trigger (an invariant of the digest,
  the selection, the base, determinism, the build, or a gate weakened: the
  trigger "verification guarantees"), the change is Level 3 as before, by
  the trigger reading. The reason: the document describes how the code
  works, and the decisions it records are in the ADRs, which stay Level 3;
  28 of 215 commits were Level 3 only because they touched it.
- **The prompts under `.agents/prompts/` other than the reviewer contract**
  leave the Level 3 list and are sensitive; they are Level 2 by path. The
  reason: they change often with the process, and the review chain and the
  owner's reading of every pull request catch a weakening (below).
- **Two exceptions stay protected and Level 3 by path**: the reviewer
  contract `.agents/prompts/reviewer.md` and the schemas `.agents/schemas/`,
  which the built-in list of `scripts/lib/guardrails.sh` protects whatever
  the configuration says. The reviewer contract defines the review that
  catches a weakening of every other prompt, and the schemas define what a
  review and a completion record must hold; a change to either can weaken
  the safeguard itself. This narrows point 3 of #396 ("prompts and
  schemas").

What a silent change of a prompt can do: weaken a review or a triage (a
check no longer asked for, a severity rule that turns majors into minors, a
contract that lets a finding through); no test fails on it. What catches
it: the change is Level 2 by path, so it gets an independent review of the
complete feature; the merge approval gate names it as sensitive in the
reviewer's context; the reviewer, a different model, reports a weakened
guarantee as the trigger "verification guarantees", which makes the change
Level 3; and the owner reads every pull request before it is merged, since
no agent merges. Requirements decision 39's "the protected paths of
`guardrails.conf`" is the list as this addendum leaves it; the requirements
are not edited for it. `scripts/lib/risk.sh` gives `docs/architecture.md`
its path minimum, and `tests/risk-level-test.sh` shows both cases and the
list. Nothing else changes: no other path, no tier, no budget, and no
decision of ADR 017.

### Addendum to decision 1 (Issue #463, 2026-11-09): administrative findings cost no round

Status: Proposed with Issue #463; accepted when its pull request is merged
with the owner's approval of the exact commit.

On 2026-11-09 the owner decided D12 of the inventory of #446 (point 6 of
#396), as the first of three pull requests. Decision 1 stands in everything
else; two things change, so that a review round is no longer spent on
administration while every check stays as reliable as before:

- **What blocks and what is form.** The reviewer contract
  (`.agents/prompts/reviewer.md`, "Blocking faults and findings about form")
  keeps every fault in the review evidence (a missing or stale review, a
  review of a Level 3 change not made after the full verification of its
  final tree, a finding not triaged), in the verification (a verification
  not run on the final tree, a skipped, removed, or weakened check, a pass
  record that does not match the tree, a failing check), and in the
  approval (a missing approval request of a Level 3 change that no
  protected path marks, decision 3, an approval of another head commit,
  a level lowered without the owner's review, a pending `owner_approval`
  criterion marked met) at `major` and blocking. Only a finding about the
  form of a record, the wording of a field, or the staleness of a working
  file is downgraded, to at most `minor`; the staleness of the handoff note
  is at most a suggestion. When in doubt a finding keeps its severity. The
  scripts still read the note's "Remaining" section themselves and refuse a
  complete record while it lists work.
- **The approval request is written by the script in full.**
  `scripts/finish-feature.sh` writes every field of
  `.agents/approvals/<issue>.md` from its derivation (`Issue:`, `Level:`,
  `Derived from:`, `Tree:`, and for a lowering `Required level:` and
  `Requested level:`) before it checks it (`risk_request_write` in
  `scripts/lib/risk.sh`), so a hand-edited field is overwritten, not
  refused. Only a lowering's `Reason:` and `Owner's word:` are written by
  hand. The script creates no request: a Level 3 change by trigger or
  assessment without one stays refused, and a lowering without the owner's
  word stays refused.

`tests/review-feature-test.sh` pins the contract text, one case per blocking
fault and the handoff rule, and what `review-feature.sh` tells the reviewer
about a stale note; `tests/risk-workflow-test.sh` shows the request written
in full, the free fields, and the refusals that stay. No check, tier, level,
path, or trigger changes.

### Addendum to decision 1 (Issue #464, 2026-11-10): a changed claim is detected; the execution settings are pinned

Status: Proposed with Issue #464; accepted when its pull request is merged
with the owner's approval of the exact commit.

On 2026-11-09 the owner decided D10 and D11 of the inventory of #446 (point
6 of #396), as the second of three pull requests. Decision 1 stands in
everything else; two things are added, and no detection is weakened:

- **D10: a changed scientific claim is a detected trigger.**
  `risk_triggers` in `scripts/lib/risk.sh` reports the trigger "changed
  scientific claim", with the claim as its detail, for every typed claim of
  a page that the base publishes (a `.qmd` file under `site/` at the base:
  a `[...]{.claim ...}` span or a `::: {.claim ...}` div) that is removed or
  changed and not added back as it was (`risk_claim_triggers`). A claim is
  compared as its text, the span with its attributes or the div's
  attributes with its content, after every run of whitespace is made one
  space: a claim that is rewrapped, reindented, or moved within its page or
  to another changed page reads the same and is no reading, and so are the
  text around a claim, a transition, a caption, and an added claim (the
  claims of a new lesson are no trigger, as decision 1 says). A reworded
  claim reads as changed, also when only its type, scope, or evidence
  changes: conservative, like the other detections, and only the owner
  lowers the reading. This narrows nothing the agent names: a claim changed
  in prose without a span, in a figure, or in a check stays a trigger the
  completion record names and the reviewer assesses.
- **D11: the execution settings are pinned.**
  `tests/unit/test_execution_settings.py` fails when `site/_quarto.yml`
  does not state `execute.freeze: false` and `execute.cache: false` (ADR
  002: every build executes every page and stores no result). It is a pin,
  not a protection: the file stays sensitive in
  `.agents/policies/guardrails.conf`, not protected.

`tests/risk-level-test.sh` shows a changed, a removed, a reworded claim, a
claim whose evidence changed, a claim of a removed page, and one of two equal
claims removed as readings; an added claim, a claim moved within its page and
to another page, a changed paragraph around a claim, a transition, a caption,
and whitespace and line wrapping inside a claim as none. No check, tier,
path, or level changes, and no test is removed.

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
