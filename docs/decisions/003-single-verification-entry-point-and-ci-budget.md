# ADR 003: One verification entry point, one verified artifact, and a fixed CI time budget

## Status

Accepted with the approval of the project bootstrap planning. Decisions 1, 2,
and 7 are amended by
[ADR 005](005-workflow-self-tests-run-locally-on-workflow-changes.md): the
workflow self-tests have their own file and run locally only when a workflow
file changed; CI still runs every check.

Decision 2 is superseded by
[ADR 012](012-parallel-verification-jobs-behind-one-required-check.md): the
checks run in parallel jobs behind one aggregate required check that keeps
the name `verify`. The job timeout of decision 5 is 45 minutes per job, by
decision 9 of the same ADR.

[ADR 014](014-verification-proportional-to-the-change.md) is the new
decision record that decision 6 requires before a check runs less often:
on a pull request the lesson checks run for the lessons whose inputs
changed, by content and failing safe; a run on `main` runs everything, in
same-machine shards that keep every job within the timeout at 110 lessons
(ADR 014 decisions 7 and 11).

The typical-pull-request row of decision 5 is amended by
[ADR 015](015-typical-pull-request-budget-of-twenty-minutes.md)
(2026-10-15, requirements decision 34): 20 minutes with warm caches, with
15 minutes as a non-blocking target; the 12 minutes below are the budget
of the day this record was written. The other rows stand. The consequence
below on the prerequisites of local verification describes the
maintainers' and agents' setup; the learner's setup is separate since
[ADR 016](016-learners-run-experiments-not-the-site-build.md). Decision 4
of ADR 014 (a run on `main` executes every lesson) is under review by
[ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md),
proposed and not accepted; this record's decisions 3 and 6 are not
changed by it. **ADR 017 decision 7, accepted by the owner on 2026-10-15 on
F118's evidence and applied by F119 (Issue #185), amends decision 1 as
ADR 005 decision 5 restates it** ("every product check runs locally on
every run"): a recorded targeted run (`./scripts/verify.sh --targeted`,
which runs the checks that need no site build against the selection CI
will make and builds no site) is the finish and review evidence of an
ordinary change, recorded with its tier, its base, and its selection; a
run without options still runs every product check and is the only
verification of the content; CI runs every check on every pull request
and push. The one removal F119 made under decision 6 (the preview test's
third build, consolidated into the determinism check) has its coverage
evidence in `docs/verification-audit.md` and its regression test in
`tests/integration/test_determinism_check.py`.

Decisions 5 and 6 are amended in one respect by [ADR 020](020-risk-proportionate-verification-and-review.md)
(2026-10-19, change cycle `risk-proportionate-workflow`, requirements
decision 39): an exceeded wall-clock budget is recorded as a measurement
and decided by the owner at the re-assessment points ADR 020 decision 6
names (42 lessons measured, 44 decided, or a complete run on `main` above
45 minutes); the order of responses of decision 6 is what the owner
chooses from, not a standing obligation, and nothing of it ever changes
scientific content; a hard check such as the 30-second lesson page budget
keeps failing, with the documented exception table. The "45 minutes per
job" above is the timeout of every job but one: the one `build` job of a
full run has had 60 minutes since the owner's interim full-run gate of
2026-10-15 (ADR 014, status). Decisions 1, 3, 4, and 7, as amended before,
and the invariants they carry are unchanged by ADR 020; decision 1 as ADR
005 decision 5 restates it reads, since ADR 017 decision 7, as the status
line above says, and ADR 020 decision 5 adds only that an intermediate
Level 3 round may run `--only` groups as feedback that is never evidence.

Date: 2026-10-06

## Context

The requirements demand that CI on every pull request and on `main` runs lint
and format checks, executes all lesson Python code with tests, runs
`lake build` for all Lean sources, and builds the site; that deployment runs
only from `main` after these pass; and that the existing `./scripts/verify.sh`
runs the same checks locally. They also require the planner to set a concrete
time budget, because Mathlib builds are heavy.

The repository already has `scripts/verify.sh`, which runs every check listed
in `scripts/verify.conf`, and a CI workflow that calls only that script. The
project now adds three heavier kinds of work: Python tests, a Lean build
against Mathlib, and a site build that executes every lesson.

Two forces pull against each other. Parallel CI jobs with path filters would
be fastest, but every CI-specific step is a chance for CI and local
verification to diverge, and a required status check that is skipped by a path
filter blocks merging.

## Decision

1. **One entry point.** All checks are entries in `scripts/verify.conf` and
   run through `./scripts/verify.sh`. The CI workflow provides the same
   prerequisites as the documented local setup and restores caches, then calls
   that script. No check exists only in CI or only locally.
2. **One verify job, no path filters.** Every pull request and every push to
   `main` runs every check in a single job named `verify`, which is the one
   required status check on `main`.
3. **Deploy the verified artifact.** The verify job uploads the built site.
   On `main`, a deploy job publishes exactly that artifact to GitHub Pages and
   does not build anything. Only the deploy job has `pages: write` and
   `id-token: write`.
4. **Mathlib comes from its build cache.** CI fetches the Mathlib cache and
   also caches the `.lake` directory. If Mathlib would have to be compiled
   from source, the job fails.
5. **Time budget.**

   | Measure | Budget |
   |---|---|
   | Typical pull request, warm caches | 12 minutes or less |
   | Cold caches | 25 minutes or less |
   | Job timeout | 30 minutes |
   | Unit tests | 2 minutes or less |
   | Lean build after the Mathlib cache is in place | 3 minutes or less |
   | One lesson page, executed | 30 seconds or less |
   | One full site build | 3 minutes or less |

   The budget includes a second site build for the determinism check.
6. **Order of responses when the budget is exceeded.** First reduce the cost
   of the offending lesson or check. Then split the verify job into parallel
   jobs that each run a named subset of the same `verify.conf` checks, with an
   aggregate required check. Dropping a check, adding path filters, or moving
   a check to a schedule requires a new ADR.
7. **The existing workflow self-tests stay** in `verify.conf` while the
   workflow scripts remain in the repository, because they guard the tooling
   every feature relies on.

## Alternatives considered

**Parallel jobs per toolchain from the start.** Faster wall clock. Rejected
for now because `verify.sh` has no subset mode, so jobs would have to
re-declare checks in workflow YAML and could drift from local verification.
Kept as the planned second response in point 6.

**Path filters (skip Lean when no `.lean` file changed).** Rejected: the
requirements say every pull request builds all proofs, a Mathlib or toolchain
bump can break proofs without touching them, and skipped required checks block
merges.

**Rebuild the site in the deploy job.** Rejected: the published bytes would
not be the verified bytes.

**Avoid Mathlib to keep CI light.** Rejected: the requirements choose Lean 4
with Mathlib, and proofs about real-valued models need it.

**Nightly instead of per-pull-request determinism check.** Rejected for now:
it would let a nondeterministic lesson merge. Reconsidered only under point 6.

## Consequences

Positive:

- "Passes locally" and "passes in CI" mean the same thing.
- The merge gate is a single, always-present status check.
- What is deployed is what was verified.

Negative, with mitigations:

- Sequential checks make a run longer than parallel jobs would. The budget
  makes the cost explicit, and F01 records measured times.
- Local verification needs the full set of prerequisites, not only the
  language toolchains: Git, uv, and elan; jq, because the workflow self-tests
  of point 7 call it directly; the Playwright browser build for the
  built-site checks; and, on Linux, that browser's system libraries. They are
  provided by a documented one-time setup, the only step that may need
  administrator rights. `./scripts/verify.sh` itself stays unprivileged and
  reports a missing prerequisite with a fix hint (architecture, "Toolchains
  and pinning"; F01).
- The first local run also downloads a Mathlib cache of several gigabytes.
  Documented with the setup; later runs reuse it.
- Mathlib build products are large against GitHub's cache quota. Eviction
  slows runs but does not break them, because the Mathlib cache server is the
  primary source. F01 measures this.
- The Mathlib cache server is an external dependency of CI. An outage blocks
  merges until it recovers or the `.lake` cache hits.
