# The process: verification, risk, and review, as they stand

The rules in force on 2026-11-07. Each names its ADR decision and the script
or file that carries it out; where an ADR and a script disagree the last
section says so and decides nothing. The ADRs (003, 005, 012, 014, 015, 017,
019, 020) stay the record of each decision and rank above this document
(`AGENTS.md`, "Source precedence"); a rule changes only through an ADR. How to
run the commands is in `docs/development.md`, the invariants in
`docs/architecture.md`.

## The verification entry point and its tiers

- **One entry point.** Every check is a line of `scripts/verify.conf` and
  runs through `./scripts/verify.sh`, locally and in CI (ADR 003 decision 1,
  ADR 005 decision 5). The workflow self-tests run locally only when a file
  under the `paths:` entry of `scripts/verify-workflow.conf` differs from the
  base branch, and always in CI (ADR 005 decisions 1 to 4).
- **Groups.** A check names its group in square brackets, or is in
  `default`. `--only <groups>` runs those groups, verifies nothing, and
  records nothing (ADR 012 decision 1); a test keeps the groups equal to the
  CI jobs (decision 2; `tests/integration/test_ci_workflow.py`).
- **Tiers** (ADR 017 decision 7, accepted 2026-10-15; `scripts/verify.sh`):
  `./scripts/verify.sh` (`full`) runs every check and every lesson, and is
  needed when the targeted run says CI will run everything and for the final
  tree of a Level 3 change (ADR 020 decision 5); `--base [<dir>]` runs every
  check against a verified base, needed when a change alters what other pages
  display of a lesson (path front matter, headers, a new lesson);
  `--targeted` computes the selection CI will make and runs the groups
  `default,code` (among them `lesson-pages`, `scripts/check-lesson-pages.sh`)
  without a site build, the tier of an ordinary change, and refuses and names
  the tier needed when it has no acceptable base or the selection is a full
  run; `--only <groups>` runs the CI jobs and the feedback of an intermediate
  Level 3 round and records nothing. A pass is recorded for the fingerprint
  of the content with its tier (`scripts/lib/verification.sh`); `--reuse`
  takes it for the same content (a targeted one for the same base and
  selection). CI builds and checks the site on every pull request and push.
- **The selection and the base** (ADR 014 decisions 1 to 6 and 10;
  `src/pbc/authoring/digest.py`, `src/pbc/authoring/selection.py`): a lesson
  is unchanged when the digest of its inputs equals the base's; a shared
  input, a missing digest, a differing check identity, or a missing or
  rejected base gives a full run. The base is the result of the latest `push`
  run on `main` whose `verify` succeeded, accepted only by that run's record
  (`scripts/fetch-base.sh`, `scripts/collect-base.sh`; ADR 020 decision 7). A
  run on `main` takes no base (ADR 014 decision 4).
- **Removing a check** needs a new decision record with coverage evidence
  (ADR 003 decision 6, ADR 017 decision 8). Every run appends a line to
  `verify-time.log`; no gate reads it (ADR 020 decision 7).

## The verification architecture

One settled division of the work between CI and the maintainer's machine
(Issue #396, point 5, the owner's decision of 2026-11-07; Issue #412):

- **CI is the complete gate.** Every pull request and every push to `main`
  runs every check through the required check `verify` (ADR 012 decisions 1
  and 5); every push to `main` executes every lesson (ADR 014 decision 4,
  ADR 020 decision 8). Nothing merges without it.
- **Locally, the fast tier of the change.** `--targeted` for an ordinary
  change, `--base` when a change alters what other pages display of a
  lesson, the full run only when the targeted run reports that CI will run
  everything (ADR 017 decision 7; `AGENTS.md`, "Definition of Done").
- **One complete verification of the final tree of a Level 3 change.**
  Intermediate rounds take the feedback groups and record nothing; the round
  that can end the run gets the full run and a review of the complete
  feature after it (ADR 020 decision 5; `scripts/run-feature.sh`, Issue
  #389).

**The next capacity step, F113 and the paused part of ADR 017: deferred**
(the owner's decision of 2026-11-08, Issue #412), neither rejected nor done.
The measured reason: a full run takes 94 to 140 minutes, the `build` chain is
57 percent of it, and 22 percent of the full runs failed in the heavy period
of 2026-11-04 to 08 (#236, #389). Issue #430 runs independent groups of
`verify.sh` at the same time; F113 splits the heavy lesson build in CI, which
is a different step. The capacity agreement of #278 stays. The question is
decided again at the first of three points: 95 lessons; a full run on `main`
that approaches 80 minutes; or repeated runs that leave too little margin.
The decisions of ADR 017 are not changed.

## CI: the jobs and the required check

`.github/workflows/ci.yml` runs on every pull request and push to `main`
(ADR 012 decisions 1 to 7; ADR 003 decisions 3 and 4). The check jobs
below (all except `verify`, `deploy` and `base`) run
`./scripts/verify.sh --all --only <group>` after `.github/actions/prepare`.

- `code`, `workflow`, the three `integration-*` jobs: one group each, 45 min.
- `build`: Lean build, site build, determinism build, reproduction; fetches
  the base on a pull request, uploads the site, collects the base on `main`;
  120 min.
- `e2e` (three parts): the `e2e-*` groups on the downloaded site, compared
  with its record first (`scripts/fetch-built-site.sh`); 45 min.
- `verify` runs no check itself: `scripts/ci-aggregate.sh` passes only when every needed job
  succeeded; `if: always()`; 5 min.
- `deploy` (the only job with `pages: write`) and `base` (publishes the
  collected base, kept 30 days), on push to `main`; 10 min each. Neither
  runs `verify.sh`.

`verify` is the one required status check of `main` (ADR 012 decision 5). The
comparisons of bytes stay in `build` (decision 4).
`tests/integration/test_ci_workflow.py` pins the timeouts, the permissions,
and that every job that runs checks does so only through the entry point.

## Budgets

- Typical pull request: 20 min warm, 25 cold, 15 a non-blocking target (ADR
  015 decisions 1 and 2, ADR 003 decision 5; `docs/release-readiness.md`);
  unit tests 2 min, Lean and site builds 3 min each. No check enforces them.
- Job timeout 45 min; `build` 120 min, approved for up to 110 lessons as a
  planning boundary (ADR 012 decision 9; ADR 014 status notes;
  `.github/workflows/ci.yml`).
- One lesson page and its experiment: a warning from 30 s, a failure at 60 s;
  a line of `scripts/lesson-budgets.conf` raises one lesson's limit with a
  reason and the owner's approval (ADR 020 decision 6, addendum of
  2026-11-05, Issue #383; `scripts/check-lesson-pages.sh`,
  `tests/support/budgets.py`).

An exceeded wall-clock budget is a measurement for the owner's decision,
never a failed gate, and is never met by changing scientific content (ADR 020
decision 6); ADR 014's note of 2026-11-04 sets the owner's re-assessment
points (a complete run on `main` near 100 minutes, too little margin).

## Risk levels

Every change carries one level, the highest of three readings, derived by
`scripts/lib/risk.sh` (`risk_assess`) and stated in the completion record
(ADR 020 decision 1):

- **The path minimum.** Level 3 for every protected path: the builtin list of
  `scripts/lib/guardrails.sh` (the ADRs, workflows, code-owners file,
  policies, the reviewer contract, schemas, gate scripts) and the
  `protected:` lines of `.agents/policies/guardrails.conf`, read from the
  base branch. Level 1 for documentation and process files, except
  `docs/architecture.md`; Level 2 otherwise. `docs/architecture.md` and the
  prompts other than `.agents/prompts/reviewer.md` are sensitive, not
  protected, and Level 2 by path (ADR 020, the addendum of 2026-11-08 to
  decision 1; Issue #412); a trigger in their content makes them Level 3.
- **The escalation triggers**, any of which gives Level 3: a changed or
  removed published scientific claim; weakened test strength; security;
  verification guarantees; dependency selection. The scripts detect on the
  diff (`risk_triggers`) a changed tolerance or budget, a new skip, `sorry`,
  or axiom, a removed or changed assertion, a removed test, a changed marker,
  a changed dependency manifest; the agent names the others, and the reviewer
  reports a missed trigger as major.
- **The assessed level**: stated in the completion record and assessed by the
  review (`architecture_impact.risk_level`), only ever higher.

Why the prompts may be sensitive, and what catches a silent change (Issue
#396, point 3; the owner's decision of 2026-11-07): a changed prompt can
weaken a review or a triage (a check no longer asked for, a severity rule
that turns majors into minors, a contract that lets a finding through), and
no test fails on it. It is caught because the change is Level 2 by path and
gets an independent review of the complete feature; the merge approval gate
names it as sensitive in the reviewer's context; the reviewer, a different
model, reports a weakened guarantee as the trigger "verification
guarantees", which makes it Level 3; and the owner reads every pull request
before it is merged, since no agent merges. The reviewer contract and the
schemas, which define that review and what its record must hold, stay
protected.

An agent may raise a level; no agent lowers one. The scripts refuse a
recorded level below the path minimum, and one below a trigger reading or an
assessment unless the committed request `.agents/approvals/<issue>.md` names
the lowering with the owner's word (ADR 020 decision 3; `risk_assess`,
`scripts/finish-feature.sh`, `scripts/merge-feature.sh`). The request is
never an approval. What each level requires (ADR 020 decisions 4 and 5;
`.agents/policies/autonomy.md`):

- Level 1: the tier of the change; no review required; no owner.
- Level 2: the tier of the change; a review of the complete feature, then a
  chain of reviews of changes of certain reach; the owner only when the
  reviewer classifies the impact `major` or `breaking`.
- Level 3: a full run of the final tree; a review of the complete feature in
  every round, the last after the full run; the full triage; the owner's
  approval of the exact head.

## Evidence: the completion record

`.agents/completion/<issue>.json` (schema `completion/v2`) is the one record
(ADR 020 decision 2; `scripts/lib/completion.sh`). Each criterion names its
gate (`implementation`, `pr_ci`, `owner_approval`, `post_merge`) and is
`met`, `not_met`, `not_applicable`, or `pending`, never pending for
`implementation`. `complete` means every criterion met or not applicable; a
record with a pending criterion is `partial`, and when every implementation
criterion is met `scripts/publish-feature.sh` opens a pull request that does
not close the Issue. Work under "Remaining" in `.agents/handoffs/<issue>.md`
counts as not complete whatever the record says.

## Review, triage, and the commit

- **A review starts on verified content** (`scripts/review-feature.sh`): the
  tier the change needs through `./scripts/verify.sh --reuse --targeted`, the
  full run for a Level 3 change, or `--feedback` for an intermediate Level 3
  round (`--only default,code,integration-other`; ADR 020 decision 5). The
  reviewer is the role `reviewer` of `.agents/agents.conf`, a different model
  from the implementer, read-only (ADR 020 decision 9).
- **The chain** (ADR 020 decision 4; `scripts/lib/review-chain.sh`): every
  finding has a stable identifier (`R01-M1`); every review records the trees
  it compared and reviewed and the disposition of earlier open findings.
  `--changes` reviews only the delta, at Level 1 or 2 and only when its reach
  is certain (tests, documentation, lesson content, or one `src/pbc` module
  with an unchanged interface); anything else is a review of the complete
  feature. A review is stale when the fingerprint of the content changed
  (`scripts/check-review.sh`, `scripts/lib/fingerprint.sh`).
- **Triage** (`scripts/triage-review.sh`): a Level 1 or 2 review whose
  findings are all minor or suggestion is triaged mechanically; any other
  review gets the full triage. Every Level 3 review with findings gets full
  triage, which is published on the Issue. In `--unattended` mode, triage runs
  without human confirmation and every critical or major finding must be
  marked `FIX_NOW`. In attended triage, the owner may approve deferring or
  accepting a major finding only if it is another instance of a class the
  owner explicitly bounded in a comment on the Issue. The rationale must cite
  that comment. `scripts/apply-triage.sh` applies the `FIX_NOW` findings and
  verifies.
- **The commit** (`scripts/finish-feature.sh`) checks the completion gate,
  the level, the verification tier (at Level 3 the full run for exactly this
  content), a current review with no critical or major finding, the chain,
  and the published triage of every round. It writes tier, base, selection,
  review, and risk level into the commit message; `scripts/publish-feature.sh`
  copies them into the pull request, which closes the Issue only on
  `complete`.

## The owner's approval and the merge

- **The merge approval gate** (`scripts/check-guardrails.sh`,
  `scripts/lib/guardrails.sh`) reads its rules from the base branch. The owner
  must approve when the diff changes a protected path, when the impact is
  `major` or `breaking` or unclassified, when the level is 3 or a lowering is
  requested, or when a criterion is pending for `owner_approval` (ADR 020
  decisions 1 to 3).
- **How the approval is given** (ADR 020 decision 3): an approving review of
  exactly the head commit by a second GitHub identity that only the owner
  holds, named on the line `owner-identity:` of `guardrails.conf` and a code
  owner in `.github/CODEOWNERS`; GitHub enforces it at the merge. Nothing an
  agent writes counts (`tests/merge-feature-test.sh`).
  `scripts/merge-feature.sh` merges only on GitHub's decision.
- **The owner's setup is not in place** (`docs/repository-setup.md`; Issue
  #396, 2026-11-06): no `owner-identity:` line, no ruleset requiring a
  code-owner review. Until it exists, `merge-feature.sh` refuses every pull
  request that needs the owner, who merges it on GitHub.

## Agent skills (the process part of ADR 019)

Skills are audited, pinned guidance under `.agents/skills/`, never a
dependency of the build or CI and never evidence (ADR 019 decisions 1, 3, and
5; `AGENTS.md`, "Visual deliverables and skills"). The check `skills-config`
(`src/pbc/skills.py`) validates them; a missing selected skill fails the
feature visibly.

## Proposals, not rules

The owner deferred the first two items on 2026-11-08 (Issue #412; "The
verification architecture" above names the points that reopen them). The
third was accepted and is not yet implemented.

- **ADR 017 decisions 1 to 6 and 9**: incremental verification on `main` from
  a chain of verified bases, paused by ADR 020 decision 8; every push to
  `main` executes every lesson. The provenance format is prototyped in
  `src/pbc/authoring/provenance.py`, which nothing calls; evidence in
  `docs/incremental-main-evidence.md`.
- **ADR 014 decision 11 (F113, Issue #150)**: same-machine lesson shards;
  paused since 2026-10-15, pull request #175 closed unmerged; deferred by
  the owner on 2026-11-08.
- **ADR 020 decision 3, the owner's actions** (second identity, code-owners
  and ruleset changes): accepted by the owner, not yet implemented. The pilot
  evaluation of decision 10 has no recorded result.

## Where the ADRs and the scripts disagree

Listed, not resolved:

1. `build` timeout: the status lines of ADR 003, 012, and 015 say 60 minutes;
   `.github/workflows/ci.yml` and its test say 120 (ADR 014's note of
   2026-11-04).
2. Lesson page budget: ADR 014's note of 2026-11-04, ADR 003 decision 5, and
   ADR 014 decision 3 name 30 seconds; `scripts/lesson-budgets.conf` warns
   from 30 s and fails at 60 s (ADR 020's addendum of 2026-11-05).
3. ADR 020 decision 5 runs, in an intermediate Level 3 round, the groups the
   changed paths touch; `scripts/lib/risk.sh` runs the fixed groups
   `default`, `code`, and `integration-other`.
4. ADR 020 decision 3 lets an agent merge a Level 3 change on the owner's
   explicit word until the identity exists; `scripts/merge-feature.sh` never
   merges such a pull request.
5. ADR 020 decision 4 triages minor and suggestion findings mechanically per
   finding; `scripts/triage-review.sh` does so only when all findings are
   minor or suggestion.
6. ADR 020 decision 1 names documentation, plans, handoffs, and summaries as
   Level 1; `scripts/lib/risk.sh` also reads a top-level Markdown file as
   Level 1 (`AGENTS.md` stays Level 3 by its path).
7. ADR 012 decision 3 lists one `integration` job and no `base` job;
   `.github/workflows/ci.yml` has three integration jobs and a `base` job
   (ADR 014 decision 2 describes the publication without naming a job).
8. ADR 020 decisions 6 and 8 name the re-assessment points 42 and 44 lessons
   and a run above 45 minutes; `scripts/lesson-budgets.conf` and
   `docs/architecture.md` name those of ADR 014's note of 2026-11-04.
