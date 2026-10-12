# Plan — Issue #130 (F58): parallel verification jobs behind one required check

Status: second version, after the owner's review of 2026-10-12; for approval
before anything is built.
Decisions of the owner on 2026-10-12: the group mechanism is built in the
workflow template first and synced; `site-checks` becomes four checks in
`scripts/verify.conf`; the work is done step by step, each step reviewed.

## Measured, 2026-10-12

One run of `verify` on `main` took 33 minutes; the budget of ADR 003 is 12.

| Check | Seconds |
|---|---|
| `site-checks` (`pytest tests/e2e`) | 894 |
| `check-tests` (`pytest tests/integration`) | 366 |
| `site-build` | 205 |
| `determinism` (second build, compared) | 204 |
| Workflow self-tests (19 checks) | 187 |
| `unit-tests`, `lean-build`, `lesson-checks`, lint, format, preflight | 102 |
| Setting up the runner (uv, Lean caches, browser), per job | about 120 |

Inside `site-checks`: the reproduction of every lesson (`test_lessons.py`) and
the scan of every page (`test_built_site.py`) take most of the time; the other
eight files together take three to four minutes. The split by file is an
estimate from the log and is measured again in step 3.

## Design

### 1. Groups (template)

`scripts/verify.conf` and `scripts/verify-workflow.conf` keep one line per
check. A check may name its group in square brackets after its name:

```text
unit-tests [code]: uv run --locked pytest tests/unit
site-build [build]: ./scripts/build-site.sh
```

- A check without a group belongs to the group `default`.
- `./scripts/verify.sh` without arguments runs every check, as before.
- `./scripts/verify.sh --only <group>[,<group>...]` runs the checks of the
  named groups, from both files, in the order of the files.
- `./scripts/verify.sh --groups` prints every group that has a check, one per
  line, `default` included.
- An unknown group is an error.
- **A partial run is never a verification.** With `--only` the script writes
  no record of a passed verification, removes nothing from an existing one,
  and refuses `--reuse`. A test shows that after `--only` on every group in
  turn there is still no record, and that `review-feature.sh` and
  `finish-feature.sh` do not accept such a state as verified.

This is a change of the template, made there first and brought here with
`sync-template.sh`.

### 2. Every check in a job, and a default that is run

| Group | Checks | Job |
|---|---|---|
| `default` | `preflight`, `preflight-test`, `dataset-checks`, `template-structure`, `shell-syntax`, `docs-scripts`, and any check without a group | `code` (`--only default,code`) |
| `code` | `lint`, `format`, `unit-tests`, `lesson-checks` | `code` |
| `build` | `lean-build`, `site-build` | `build` |
| `integration` | `check-tests` | `integration` |
| `workflow` | the workflow self-tests | `workflow` |
| `determinism` | `determinism` | `determinism` |
| `e2e-*` | the checks of the built site, see below | one job each |

The earlier version had no job for `default`: a check added without a group
would have run locally and never in CI. Two things close that:

- the `code` job runs `default` together with `code`;
- a test reads the groups from `./scripts/verify.sh --groups` and the groups
  from the `--only` arguments of the workflow file, and fails unless they are
  the same set, each group in exactly one job. It also fails when a job runs
  `verify.sh` without `--only`, which would run everything twice. This is
  stronger than checking that each check has one group: it compares what is
  declared with what CI runs.

### 3. Lean: who needs what

Found while checking the owner's second point:

- `site-build` reads `lean/.lake/pbc-build-record.json`, which `lean-build`
  writes: a lesson page states which versions compiled its proofs. So
  `lean-build` and `site-build` are one group, `build`, in that order in one
  job. The record that the published site shows comes from that job.
- `check-tests` needs the Mathlib packages in `lean/.lake/packages` (it runs
  the Lean check on small projects and `lake env lean` on lesson files), not
  the project's own build.
- The reproduction of a Lean lesson in `test_lessons.py` needs the same
  packages.
- The second build of `determinism` reads the same record as the first.

Jobs do not share a work directory, so each job that needs Lean prepares it
itself:

- every such job restores the cache of elan and of `lean/.lake`, which holds
  Mathlib's build products, by the key of today;
- on a cold cache the job fetches Mathlib's build cache in its setup
  (`lake exe cache get`), exactly what `check-lean.sh` does first. This is
  preparation, like installing the browser; it compiles and checks nothing.
  A test of today forbids the word `lake` in a setup step, to keep checks out
  of the workflow file. It is narrowed to allow this one command, and ADR 012
  says so. **This needs the owner's agreement**: the alternative is that the
  jobs wait for `build` to fill the cache, which puts `integration` behind
  the build and breaks the time budget.
- `determinism` gets the build record of the `build` job as a file, beside
  the site (see "One artifact").

Step 3 starts by proving this on a branch: `integration` and a lesson shard
with a cold cache and without any other job having run. If a job turns out to
need more than the packages, it gets `needs: build` and the plan is revised
before anything else is built.

### 4. The checks of the built site

`site-checks` is replaced by checks that are each declared in `verify.conf`.
How many is decided by measurement, not in advance: step 2 first records the
duration of every test (`pytest --durations=0` in CI, where the times count),
then divides.

- `site-checks-lessons-<i>`: `pytest tests/e2e/test_lessons.py --shard i/n`.
  A lesson belongs to a shard by a rule on its path that does not depend on
  the order of collection: the lessons are sorted by path and dealt out by
  measured duration, heaviest first, and the resulting list is written in a
  file that the option reads. A lesson that is in no list fails the
  collection, so a new lesson cannot be left out. Tests of that file that
  belong to no lesson run in shard 1.
- `site-checks-pages`: `pytest tests/e2e/test_built_site.py`, in two parts by
  the same option if it takes more than three minutes.
- `site-checks-other`: `pytest tests/e2e` with `--ignore` for the files above.
  It names what it leaves out, so a new test file runs without a change here.

A test proves the division, by collection only, without running a browser:

- the node IDs collected by all `site-checks-*` commands together are exactly
  those of `pytest tests/e2e --collect-only`;
- every node ID is collected by exactly one command;
- no command collects zero tests.

### 5. Jobs

```text
code            --only default,code
integration     --only integration
workflow        --only workflow
build           --only build        -> uploads the site and the build record
determinism     --only determinism  (needs build)
e2e-<name>      --only e2e-<name>   (needs build), one job per check
verify          the aggregate
deploy          needs verify; publishes the artifact that build uploaded
```

**The aggregate.** `verify` needs every job above, runs with
`if: ${{ always() }}`, and passes only when the result of each of them is
exactly `success`. A job that failed, was cancelled, or was skipped (for
example an `e2e` job after a failed build) fails it. The decision is a small
script, `ci-aggregate.sh`, that reads `toJSON(needs)`, so it is tested
without GitHub: one job failed, one job skipped, one job cancelled, one job
missing from the list, and all succeeded. `deploy` needs `verify`, so it does
not run unless the aggregate passed; a test of the workflow file checks that
`deploy` has no other path.

**One artifact.** `build` uploads the site with the Pages artifact action, as
today; that archive is what `deploy` publishes. `build` also writes a list of
the checksum of every file of the site and uploads it with the Lean build
record. A job that needs the site downloads the Pages artifact, unpacks the
tar archive inside it to `site/_site`, and compares every file with the list
before any test runs: a missing, extra, or changed file stops the job. The
unpacking and the comparison are one script, `fetch-built-site.sh`,
with a test. `determinism` then builds a second time and compares with the
unpacked files, as `check-determinism.sh` does today with a directory.

**Permissions.** `contents: read` everywhere; `actions: read` where a job
downloads an artifact, if the action needs it; `pages: write` and
`id-token: write` only in `deploy`. Every action pinned by its commit.

### 6. Time

For a pull request, without `deploy`:

```text
T = max(T_code, T_integration, T_workflow,
        T_build + max(T_determinism, T_e2e-slowest)) + T_verify
```

Estimate: `integration` 2 + 6 = 8 minutes; `build` 2 + 4 = 6; the slowest job
after it about 1.5 + 3 = 4.5, when no check of the built site takes more than
three minutes. That gives about 10.5 minutes, and the division of step 2 aims
at 9 to 10 so that there is room. Twelve stays the budget of ADR 003.

Measured in step 4, and recorded in the pull request and in
`docs/release-readiness.md`:

- three pull request runs with warm caches: the time of every job, the
  critical path, and the total;
- one run with cold caches (a changed cache key), against the 25 minutes of
  ADR 003;
- the runner minutes of a run, beside those of the single job of today:
  parallel jobs finish sooner and use more minutes, because each prepares its
  own runner.

### 7. Decision record

ADR 012 **supersedes** decision 2 of ADR 003 and decision 2 of ADR 005; it
does not rewrite them. Both older ADRs keep their text and get a line in
their status that names ADR 012. ADR 012 records the groups, the aggregate
check, the single artifact, the preparation of Mathlib in a setup step, and
the measured times. The budgets of ADR 003 decision 5 stand.

The timeout per job stays 45 minutes until the cold-cache run is measured;
whether it returns to 30 is decided from that number and written in ADR 012.

## Steps, each with its own review

1. **Template:** groups in `verify.sh` (`[group]`, `--only a,b`, `--groups`),
   the rule that a partial run is never a verification, their tests, and the
   documentation. Then `sync-template.sh` here, as its own pull request.
2. **Checks:** measure every test of `tests/e2e` in CI; the `--shard` option
   and the lists; the new checks and the groups in `verify.conf`; the test of
   the division; the test that every original check is covered exactly once.
   The workflow still runs one job.
3. **Workflow:** first the proof that `integration` and a lesson shard run
   alone on a cold cache. Then the jobs, `ci-aggregate.sh` and
   `fetch-built-site.sh` with their tests, the tests of the workflow file
   (declared groups equal the groups CI runs; one job named `verify`; only
   `deploy` writes; `deploy` only after `verify`), and ADR 012 with the
   documentation.
4. **Measure:** as under "Time".

## What needs the owner

- This plan, and in it: fetching Mathlib's build cache in a setup step
  (section 3).
- ADR 012.
- The merge of every pull request: all of them change protected paths.
- If GitHub asks for it: confirming the required check `verify` in the ruleset
  of `main` after the first run with the new jobs.

## Risks

- **The aggregate passes while a job did not run.** `ci-aggregate.sh` accepts
  only `success` for every needed job, and is tested on each other result.
- **A check is declared and never run in CI.** The test that compares
  `--groups` with the workflow file.
- **A test of the built site falls between the checks.** The collection test.
- **The tested site differs from the deployed one.** One build, one archive,
  and the checksum list compared after unpacking.
- **A job depends on what another job left behind.** Each job prepares Lean
  itself; proven on a cold cache before the workflow is written.
- **The budget is not reached.** The division is made from measured times and
  aims two minutes under it.
- **More runner minutes.** Measured and recorded; the repository is public, so
  they cost nothing today, and the number is there if that changes.

## Step 2 as built, 2026-10-12

Measured in CI (draft pull request 134, closed): `tests/e2e` takes 943 s, of
which `test_lessons.py` 434 s, `test_built_site.py` 269 s, `test_widgets.py`
122 s, and the eight other files 115 s. The reproduction test of the lessons
is 404 s of the first.

Five checks, each in a group of its own: `site-checks-lessons-1` and `-2`
(about 250 s each, with lesson 12 estimated at 62 s because it was merged
after the measurement), `site-checks-pages-1` (about 120 s) and `-2` (the
three slowest tests, about 150 s), `site-checks-other` (about 240 s).

Two deviations from the design above, both approved by the owner on 2026-10-12:

1. **A lesson that no list names does not fail the collection.** It runs in
   the part that a checksum of its path selects. The aim of the rule, that a
   new lesson cannot be left out, holds either way, and
   `docs/authoring.md` can keep its promise that there is no list to add a
   lesson to. A failing collection would also have broken every feature
   branch that adds a lesson as soon as this is merged.
2. **The workflow self-tests stay in the group `default`.** Their list is
   `scripts/verify-workflow.conf`, a file of the template; giving each line a
   group there would have to be merged by hand on every sync. Step 3
   therefore runs `default` in the job `workflow` and `code` in the job
   `code`, in place of `default,code` in one job and `workflow` in another.
   Every group still has exactly one job, and the test that compares
   `--groups` with the workflow file is unchanged.

The owner's conditions with the approval:

- The lists of `tests/e2e/shards.json` stay, for balance; a new lesson gets
  its part from a stable checksum; every collected test runs exactly once.
  The test of the division compares with what `pytest tests/e2e` collects at
  that moment and holds no count.
- The job of step 3 that runs the group `default` runs
  `./scripts/verify.sh --all --only default`, so that the workflow self-tests
  are never skipped in CI.
- Every check belongs to exactly one group, `default` included. A test
  requires that the groups `./scripts/verify.sh --groups` prints are the
  groups of the checks.
- A run without `--only` is unchanged: it runs every check and is the only
  run that records a verification.

## Step 3 as built, 2026-10-12

Three trial runs of the planned jobs (draft pull request 140, closed) changed
the design in two places. The owner approved the second on 2026-10-12
("option B").

1. **`integration` does not need the build.** One test imported the modules
   of the Lean project and relied on `lean-build` having run before it in the
   same job. It now builds the modules it imports, which takes no time after
   `lean-build` and makes the test independent of the order of checks.
2. **A comparison of bytes runs in the `build` job.** With the reproduction
   of the lessons in jobs of their own, five lessons differed from the built
   site in the second trial (one digit in a page, four figures or data
   files) and passed in the first; in the third the second build of
   `determinism` differed. The runners of two jobs can have different
   processors. `determinism` and the reproduction test (marked
   `same_machine`, check `site-checks-reproduction`) are therefore in the
   group `build`. The two lesson parts of step 2 and their lists are gone:
   without the reproduction the other tests of `test_lessons.py` take half a
   minute and run in `site-checks-other`. With them goes the rule for a
   lesson that no list names (deviation 1 of step 2), which has nothing left
   to decide.

Jobs as built: `code`, `workflow` (the group `default`, with `--all`),
`integration`, `build`, `e2e` in three parts (`pages-1`, `pages-2`, `other`),
`verify`, `deploy`.

Time: the trial runs took 12 to 14.5 minutes with the comparisons beside the
build. With the comparisons in the `build` job the longest path is that job
(preparation, Lean, two site builds, the reproduction) and then an `e2e`
job; step 4 measures it. It is expected above the 12 minutes of ADR 003, and
the remainder is left to the feature that makes verification proportional to
what a pull request changes.

**Acceptance criterion 1, revised by the owner on 2026-10-12.** The review of
step 3 found that the design with the comparisons in the `build` job does not
deliver the 12 minutes that criterion 1 of the Issue asks, and that no one
had waived it. The owner chose to keep the design and revise the criterion:
F58 measures and records the run time on three consecutive pull requests; the
12 minutes become a criterion of the feature that makes verification
proportional to what a pull request changes (planning change
`final-curriculum`). The Issue and ADR 012, decision 8, say so.

Measurement runs of step 4: draft pull requests on the branches `measure/130-step4-warm` and `measure/130-step4-cold`, closed afterwards.
