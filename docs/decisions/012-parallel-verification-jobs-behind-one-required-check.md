# ADR 012: Verification runs in parallel CI jobs behind one required check

## Status

Proposed with the implementation of F58 (Issue #130); accepted when the pull
request that adds this ADR is merged. Supersedes decision 2 of
[ADR 003](003-single-verification-entry-point-and-ci-budget.md) and decision 2
of [ADR 005](005-workflow-self-tests-run-locally-on-workflow-changes.md); the
other decisions of both stand.

Date: 2026-10-12

## Context

ADR 003 put every check in one CI job named `verify`, with a budget of 12
minutes for a typical pull request, and named the response when the budget is
exceeded: first make the offending checks cheaper, then run the same checks in
parallel jobs behind one required check. The first response was applied in F10
and was not enough. On 2026-10-12, with twenty lessons, the job took 32 to 43
minutes; the owner had raised its timeout from 30 to 45 minutes the day
before. Measured in that job: the checks of the built site 894 s, the
integration tests 366 s, the site build 205 s, the second build for
determinism 204 s, the workflow self-tests 187 s, and about 120 s to prepare
the runner.

Three properties of the single job have to survive the split:

- no check exists only in the workflow file, and CI runs what a local
  verification runs (invariant I8);
- the site that is published is the site that was checked (invariant I9);
- the merge gate is one status check that is always present.

## Decision

1. **Checks have groups, and a job runs groups.** A check in
   `scripts/verify.conf` names a group; a check without one is in the group
   `default`, which also holds the workflow self-tests. A CI job runs
   `./scripts/verify.sh --all --only <groups>`. A run with `--only` verifies
   nothing by itself and records nothing; only a run without it is a
   verification, and that is what a developer and the review workflow run
   locally. `--all` stays on every job, so CI never skips the workflow
   self-tests (ADR 005, decision 2, as far as it concerns `--all`).

2. **Every group runs in exactly one job.** A test compares the groups that
   `./scripts/verify.sh --groups` prints with the groups that the jobs of
   the workflow file run, and fails unless they are the same, each once. A
   check that is added without a group therefore runs in CI, in the job of
   `default`; a new group that no job runs fails the test.

3. **The jobs.**

   | Job | Groups | Needs |
   |---|---|---|
   | `code` | `code`: lint, format, unit tests, lesson source checks | |
   | `workflow` | `default`: the checks without a group and the workflow self-tests | |
   | `integration` | `integration` | |
   | `build` | `build`: the Lean build, then the site build | |
   | `determinism` | `determinism` | `build` |
   | `e2e`, one job per part | `e2e-lessons-1`, `e2e-lessons-2`, `e2e-pages-1`, `e2e-pages-2`, `e2e-other` | `build` |
   | `verify` | none: the aggregate | all of the above |
   | `deploy` | none | `verify` |

   The Lean build and the site build are one group in one job, in that
   order, because a lesson page states which versions compiled its proofs
   and reads that from the record the Lean build writes.

4. **`verify` is the one required status check and passes only on success.**
   It runs whatever happened to the jobs it needs (`if: always()`), because
   GitHub would otherwise skip it after a failure and treats a skipped
   required check as passed. `scripts/ci-aggregate.sh` reads the results and
   passes only when every job it is told to expect has the result `success`
   and no other job is among the results. A job that failed, was cancelled,
   or was skipped fails it. `deploy` needs `verify`, so nothing is published
   unless every job succeeded.

5. **One built site.** `build` uploads the site as the Pages artifact, which
   is what `deploy` publishes, and beside it a list with the checksum of
   every file and the Lean build record. A job that checks the site
   downloads both, and `scripts/fetch-built-site.sh` unpacks the archive and
   requires that the files are exactly the recorded ones, before any check
   runs. No job that checks the site builds it.

6. **A job prepares its own runner, and that includes Mathlib's build
   cache.** Jobs do not share a work directory. The preparation is one local
   action, `.github/actions/prepare`, which installs and restores and runs
   no check. The `build` job restores and saves `lean/.lake` as before. The
   jobs that need the Lean packages and build nothing of their own
   (`integration` and the two parts of the lesson checks) restore that cache
   without saving it, and fetch the build products that Mathlib publishes
   (`lake exe cache get`) when nothing was restored. That one command is
   allowed in the preparation: it downloads, and compiles and checks
   nothing. Mathlib is still never compiled from source (ADR 003,
   decision 4).

7. **The budgets of ADR 003, decision 5, stand**, now for the wall clock of
   a run: 12 minutes for a typical pull request with warm caches, 25 with
   cold caches. The timeout of a job stays 45 minutes until a run with cold
   caches is measured; step 4 of F58 records the measured times here and
   decides from them whether the timeout returns to 30 minutes.

## Alternatives considered

- **Keep one job and make checks cheaper.** Applied first, as ADR 003 asks;
  the cost grows with every lesson and the job was at three times its budget.
- **Path filters, or checks on a schedule.** Ruled out by ADR 003 and still
  ruled out: every pull request runs every check.
- **Declare the parallel work in the workflow file** (a job per pytest
  command). It would create checks that exist only in CI and break
  invariant I8.
- **Let every job that needs the site build it.** Simple, and it multiplies
  the most expensive step and checks a site that is not the published one.
- **Make the jobs that need Mathlib wait for `build`** in place of fetching
  its build cache themselves. It puts the integration tests behind the
  build on every run with a cold cache and keeps `lake` out of the
  preparation; the wait was judged worse than one download command.
- **A required check per job.** A job that is renamed, added, or removed
  would need a change of the ruleset of `main` each time, and a skipped job
  would count as passed.

## Consequences

- The wall clock of a run is the longest path, not the sum: preparation and
  build, then the slowest job that checks the site.
- A run uses more runner minutes than the single job did, because every job
  prepares its own runner.
- The workflow file knows the names of the groups. The test of decision 2
  keeps that list equal to `verify.conf`.
- Two more scripts and a local action are part of the merge gate; each has
  tests, and the action is covered by the tests of the workflow file
  (pinned actions, no secrets, no check tool).
- The cost per lesson is unchanged. With the curriculum growing, the build
  and the reproduction of every lesson grow with it; making verification
  proportional to what a pull request changes is a separate decision.
- A local `./scripts/verify.sh` is unchanged: it runs every check in one
  process and is the only run that records a verification.
