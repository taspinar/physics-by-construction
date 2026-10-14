# ADR 012: Verification runs in parallel CI jobs behind one required check

## Status

Accepted by the project owner with the merge of pull request #141 on
2026-10-12 (F58, Issue #130). Decision 9 and the section "Measured" were
added by the pull request that closes the feature. Supersedes decision 2 of
[ADR 003](003-single-verification-entry-point-and-ci-budget.md) and decision 2
of [ADR 005](005-workflow-self-tests-run-locally-on-workflow-changes.md); the
other decisions of both stand. The feature that decision 8 names is F61,
and its decision record is
[ADR 014](014-verification-proportional-to-the-change.md); the timeout of
decision 9 stays 45 minutes by that ADR's decision 7. ADR 014 decision 11
amends decisions 2, 3, and 6 of this ADR for a full run (F113): the group
`build` runs in same-machine lesson shards that each execute a bounded
share of the lessons and make the comparisons of decision 4 on their own
machine, and one `assemble` job renders the one built site of decision 6
from their results; a lesson-shard matrix counts as the one job of its
group in decision 2. The lesson shards are not the division of
`tests/e2e/shards.json`, which splits the built-site tests between the
`e2e-pages` jobs of this ADR and stands.

Implementation of F113 (Issue #150): the workflow has the jobs `plan`
(derives the lesson shards, and takes the base of a pull request once),
`build` (a matrix of lesson shards, `./scripts/verify.sh --shard <k>/<N>`),
and `assemble` (`./scripts/verify.sh --assemble`), and the `e2e` jobs wait for
`assemble`. The measurements of F113 on the hosted runners follow once that
workflow has run on `main`; the status of this ADR changes with the human's
merge decision, not with this note.

Date: 2026-10-12

## Context

ADR 003 put every check in one CI job named `verify`, with a budget of 12
minutes for a typical pull request, and named the response when the budget is
exceeded: first make the offending checks cheaper, then run the same checks in
parallel jobs behind one required check. The first response was applied in F10
and was not enough. On 2026-10-12, with twenty lessons, the job took 31 to 43
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
   | `build` | `build`: the Lean build, the site build, the second build for determinism, the reproduction of every lesson | |
   | `e2e`, one job per part | `e2e-pages-1`, `e2e-pages-2`, `e2e-other` | `build` |
   | `verify` | none: the aggregate | all of the above |
   | `deploy` | none | `verify` |

   The Lean build and the site build are one group in one job, in that
   order, because a lesson page states which versions compiled its proofs
   and reads that from the record the Lean build writes.

4. **A comparison of bytes runs on the machine that built the site.** The
   second build of `determinism` and the reproduction of a lesson compare
   their result byte for byte with the first build. The runners of two jobs
   can have different processors, and numerical output then differs in the
   last digit: in the trial runs of this feature a reproduced page differed
   from the built one in one digit, figures differed, and the second build
   differed, in jobs that passed in another run. Both checks are therefore in
   the group `build`. A test that compares bytes with the built site carries
   the marker `same_machine`, and a test requires that the check in the
   group `build` holds exactly the marked tests.

5. **`verify` is the one required status check and passes only on success.**
   It runs whatever happened to the jobs it needs (`if: always()`), because
   GitHub would otherwise skip it after a failure and treats a skipped
   required check as passed. `scripts/ci-aggregate.sh` reads the results and
   passes only when every job it is told to expect has the result `success`
   and no other job is among the results. A job that failed, was cancelled,
   or was skipped fails it. `deploy` needs `verify`, so nothing is published
   unless every job succeeded.

6. **One built site.** `build` uploads the site as the Pages artifact, which
   is what `deploy` publishes, and beside it a list with the checksum of
   every file. A job that checks the site downloads both, and
   `scripts/fetch-built-site.sh` unpacks the archive and requires that the
   files are exactly the recorded ones, before any check runs. No job that
   checks the site builds it.

7. **A job prepares its own runner, and that includes Mathlib's build
   cache.** Jobs do not share a work directory. The preparation is one local
   action, `.github/actions/prepare`, which installs and restores and runs
   no check. The `build` job restores and saves `lean/.lake` as before. The
   job that needs the Lean packages and is not the build (`integration`)
   restores that cache without saving it, and fetch the build products that Mathlib publishes
   (`lake exe cache get`) when nothing was restored. That one command is
   allowed in the preparation: it downloads, and compiles and checks
   nothing. Mathlib is still never compiled from source (ADR 003,
   decision 4).

8. **The budgets of ADR 003, decision 5, stand, except the job timeout
   (decision 9)**, now for the wall clock of a run: 12 minutes for a typical pull request with warm caches, 25 with
   cold caches. With decision 4 the longest path is the whole `build` job
   and then the slowest `e2e` job, and that path is expected above 12
   minutes. The project owner decided on 2026-10-12 to accept that for F58:
   acceptance criterion 1 of Issue #130 was revised to a measured and
   recorded run time, and the 12 minutes become an acceptance criterion of
   the feature that makes verification proportional to what a pull request
   changes, which the planning change `final-curriculum` adds. Until that
   feature is delivered the budget is exceeded and the response of ADR 003,
   decision 6, stays due.

9. **The timeout of a job stays 45 minutes**, in place of the 30 minutes
   of ADR 003, decision 5. The longest job measured is
   `build` with 20 minutes 27 seconds, in the run with cold caches. The 30
   minutes of ADR 003 would hold it today with less than ten minutes to
   spare, and the job grows with every lesson until verification is
   proportional to a change. The feature that brings that decides whether
   the timeout returns to 30 minutes.

## Measured

On 2026-10-12, with twenty-two lessons; the runs and the times of the jobs
are in `docs/release-readiness.md`, "Parallel jobs (F58)".

| Run | Wall clock | Runner time |
|---|---|---|
| Single job before this ADR | 31 to 43 minutes | the same |
| Pull request, warm caches (two runs) | 22 min 56 s and 25 min 00 s | 44 min 36 s and 47 min 13 s |
| Push to `main` with deploy, warm caches | 17 min 52 s | 38 min 55 s |
| Pull request, cold caches | 25 min 17 s | 45 min 12 s |

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
- **Give every job that compares bytes its own first build.** It keeps
  those comparisons out of the `build` job and shortens the longest path,
  at the price of a second and third full site build per run, which grows
  with every lesson.
- **Compare with a tolerance, or pin the numerical code paths** so that all
  processors agree. The first changes what the checks prove; the second
  cannot be proved and breaks silently with a library update.
- **A required check per job.** A job that is renamed, added, or removed
  would need a change of the ruleset of `main` each time, and a skipped job
  would count as passed.

## Consequences

- The wall clock of a run is the longest path, not the sum: the `build`
  job with its two comparisons, then the slowest job that checks the site.
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
