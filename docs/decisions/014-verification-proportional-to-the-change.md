# ADR 014: Verification proportional to the change, with the verified result of `main` as the base

## Status

Proposed with the planning of the change cycle `final-curriculum`;
accepted when that planning is approved. Amends
[ADR 002](002-regenerate-artifacts-and-display-by-reference.md) (an
execution cache may be restored from a verified artifact, never committed)
and is the new decision that
[ADR 003](003-single-verification-entry-point-and-ci-budget.md) decision 6
and [ADR 012](012-parallel-verification-jobs-behind-one-required-check.md)
decision 8 require before a check runs less often. Decision 11 amends ADR
012 decisions 2, 3, and 6: the group `build` runs in same-machine lesson
shards whose results one assembly turns into the one built site. ADR 005
is unchanged.

**Acceptance, by the owner on 2026-10-15: decisions 1 to 10 are accepted.**
They are implemented by F61 (Issue #147; pull requests #152, #158, #159,
#160, #164, #166, and the fixes #177 and #178). **Decision 11 (the lesson
shards and the assembly, F113) is not accepted:** it is paused (requirements
decision 35), its implementation was closed unmerged (pull request #175,
Issue #150 open, branch preserved for reference), and it stays unaccepted
and unimplemented; [ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md),
proposed, would supersede it if the owner accepts it. Decision 7's budget
of 12 minutes is amended by ADR 015, and its timeout of a full run by the
interim full-run gate recorded below. The criterion of F61 that asks for
this acceptance is its criterion 8; the other criteria of F61 are decided
on Issue #147.

**ADR 017, 2026-10-16:** the owner's decision on it is to amend, not yet
accept ([ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md),
status): decisions 1 to 6 and 9 stay proposed, and decision 11 of this
record stays paused and unaccepted. F113 (Issue #150) stays paused and is
neither closed nor superseded until the full-run fallback strategy is
adequately covered. Every push to `main` still executes and checks every
lesson.

Implementation of F61 (Issue #147) in stages: the input digest, the check
identity, the selection, the store, the regenerated context, and the page
checks by selection (decisions 1, 3, 5, 6, 9, 10) were merged with pull
requests #152, #158, and #159. The transport of the base through artifacts
(decision 2) and the workflow and permission change it needs (`actions:
read` on the jobs `build` and `e2e`) are in the pull request that adds
`scripts/fetch-base.sh`; the measurement of F61 (step 9) follows once that
workflow has run on `main`. The status of this ADR changes with the human's
merge decision, not with this note.

Change cycle `pbc-planning-change-four-workstreams` (2026-10-15):

- Decision 7's budget of 12 minutes for a typical pull request is amended
  by [ADR 015](015-typical-pull-request-budget-of-twenty-minutes.md) to
  20 minutes with warm caches, with 15 minutes as a non-blocking target
  (requirements decision 34); the 35-minute planning budget for one job
  of a full run, the 45-minute timeout, and the 25-minute cold-cache
  budget are unchanged by that amendment.
- Decision 11 (the lesson shards and the assembly, F113) is **paused** by
  requirements decision 35: pull request #175 was closed on 2026-10-15
  without a merge, Issue #150 stays open, and the branch is preserved. A
  full run is the one `build` job of ADR 012 until the owner decides.
  [ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md),
  proposed and not accepted by the planning, would supersede decision 11
  and amend decisions 2, 4, 7, and 10 if the owner accepts it on the
  staged evidence of F118 and F120; the interim full-run gate is the
  owner's decision on the timeout of the one `build` job (requirements,
  unresolved question 10), from the measurements F118 records.
- Decision 9 is amended in name only by
  [ADR 016](016-learners-run-experiments-not-the-site-build.md): the
  provenance region regenerated on every build is the "Run this
  experiment" (or "Replay this experiment", "Check this proof") section,
  which keeps the identifier `reproduce-this`.

- **Interim full-run gate, decided by the owner on 2026-10-15**
  (requirements, unresolved question 10; the proposal and its evidence are
  on Issue #180 and in `docs/verification-audit.md` and `docs/release-readiness.md`,
  "The full run and the one-lesson pull request, decomposed (F118)"): the
  timeout of the one `build` job of a full run is **60 minutes**, with a
  planning budget of 50 minutes, and the gate is approved for up to **45
  lessons** (the arithmetic limit at the slowest measured runner is 47).
  The lesson features of Phase 4 may take the lesson count past 32 up to
  45 under this gate; past 45 lessons the gate needs a further decision of
  the owner, or the acceptance of ADR 017. The 45-minute timeout and the
  35-minute planning budget of the rest of this ADR stay as recorded for
  the other jobs; the value is applied by the pull request that records
  this decision: the job `build` of `.github/workflows/ci.yml` has
  `timeout-minutes: 60`, the test that pins the timeouts and the
  architecture say so, and every other job keeps 45 minutes. Measured at
  32 lessons, a full run's `build` job takes 21 to 31 minutes, so no run
  needs the new value yet; the growth is 32 to 46 seconds per lesson.
- **F119 (Issue #185, 2026-10-15) applied, under ADR 017 decisions 7 and 8
  (accepted the same day on F118's evidence):** the third build of the
  preview test is consolidated into the determinism check of decision 3
  (a lesson executes three times in a full run, as decision 11 counted;
  the regression test is `tests/integration/test_determinism_check.py`);
  the integration tests of decision 8 run as three checks in three jobs,
  still on every run and never selected; `tests/integration` left the
  check identity of decision 10, with the completeness test the audit
  names (no check a base reduces reads it, and the checks that run it are
  never reduced by a base), while every other input stays and the
  identity stays one digest, so an input no classification names still
  invalidates every reused result; and the agents' local verification is
  the three tiers of ADR 017 decision 7, of which `./scripts/verify.sh
  --base` is the run of decision 5 with the base retrieved read-only on
  the developer's machine. Decision 4 is unchanged: a run on `main`
  executes every lesson.

- **Change cycle `risk-proportionate-workflow`, 2026-10-19
  ([ADR 020](020-risk-proportionate-verification-and-review.md), requirements decision 39).** Decision 7 and the consequences
  are amended in one respect: an exceeded wall-clock budget is a
  measurement for the owner's decision at the re-assessment points ADR
  020 decision 6 names (42 lessons measured, 44 decided, or a complete
  run on `main` above 45 minutes), not a mandate; the consequence "no
  lesson feature takes the count past it before F113 is delivered" is
  history since the interim full-run gate above (up to 45 lessons). ADR
  017 decisions 1 to 6 and 9 stay proposed and paused, not justified by
  lead-time evidence, and decision 11 of this record (F113, Issue #150)
  stays paused and open; both are reopened only at those triggers. F120's
  evidence was published (pull request #224) and Issue #196 closed on
  2026-10-19 without accepting ADR 017. Decisions 1 to 6, 8, 9, and 10,
  the selection, the base provenance (with the stamped ref of F61 M3,
  pull request #216), and the check identity are unchanged, and any change
  to them is Level 3 under ADR 020. The site publishes thirty-eight lessons
  since 2026-10-17 (F66 and F72), within the interim gate.

- *Amendment note (Issue #253, 2026-10-21).* The owner extended the
  interim full-run gate above from 45 to **64 lessons**, with the timeout
  of the one `build` job kept at 60 minutes and every other timeout
  unchanged, as a planning boundary that no check enforces: capacity is
  re-measured at 55 lessons and the next decision is the owner's by 60
  lessons at the latest, or earlier if the `build` job approaches 55
  minutes, repeated runs show too little margin, or verification failures
  point to a capacity problem, with the `build` job's duration and the
  run's total duration reported separately; these points replace, for
  this boundary, the re-assessment points of 42 and 44 lessons named
  above and in ADR 020 decisions 6 and 8, every push to `main` still
  executes every lesson, and decision 11 (F113) and ADR 017 decisions 1
  to 6 and 9 stay paused.

Date: 2026-10-12

## Context

Every verification run executes every lesson three times: the site build,
the second build for determinism, and the reproduction of the lesson in a
fresh clone; and checks every built page. With twenty-two lessons a pull
request takes 18 to 25 minutes in parallel jobs (ADR 012, "Measured"),
against the budget of 12 minutes, and the cost per lesson is about 45
seconds of runner time (change request, section 15), of which about 41
seconds fall on the `build` job of ADR 012, which holds the site build,
the second build, and the reproduction of every lesson. At the 110 lessons
of the reference curriculum the site build alone would take about 19
minutes, and that job about 80 minutes with cold caches, against its
timeout of 45 minutes; the cold run of F58 took 20 min 27 s with
twenty-two lessons. A run on `main` that times out publishes nothing.

The requirements (decision 30) now say: the time a pull request waits
depends on what it changes, not on the size of the curriculum; a pull
request that changes one lesson executes and checks that lesson and every
lesson that depends on what it changed; one that changes shared code, the
locked environment, the site configuration, or a toolchain executes and
checks every lesson; every push to `main` executes and checks every lesson;
a lesson counts as unchanged only when none of its inputs changed (its
source, the modules of `src/pbc` it imports, its dataset samples, the lock
file, the Lean toolchain and manifest, the site configuration, and shared
templates); the rule fails safe, and when the inputs cannot be determined
with certainty, everything runs; no check is dropped; the selection is
made by `./scripts/verify.sh`; a local run without options still verifies
everything; the published site is still the site that was verified; the
Lean build keeps running in full on every pull request (unresolved
question 8); and the 12-minute budget holds at 110 lessons.

ADR 002 decided that Quarto's `freeze` and any other committed execution
cache are not used, because a committed cache is a second copy of every
result that can drift. ADR 003 decision 6 and ADR 012 decision 8 require a
new decision record before a check runs less often, and ADR 012 kept the
job timeout at 45 minutes until that record exists.

## Decision

1. **A lesson is unchanged when its input digest equals the digest of the
   base.** The inputs of a lesson are: its directory under `site/lessons/`
   (source, replay fixture, everything in it); every module of `src/pbc`
   its executed cells import, followed transitively through the imports of
   those modules; the dataset samples and cards its cells use, found by the
   name analysis of the dataset check (`tests/support/data_use.py`); the
   files of the repository that a path constant of a `pbc` module names
   wherever its cells or those modules use it (a constant made from
   `__file__`, such as `EXPECTED_DIR` of `pbc.data.pipeline`, which names
   `reports/expected`): the file or directory the use names with literal
   parts, the whole directory of the constant when a part is computed,
   and a missing file as missing, so that adding it changes the digest;
   the data directories stay with the name analysis; the
   Lean modules it displays (`lean-modules`) and the Lean toolchain and
   manifest; `pyproject.toml`, `uv.lock`, and `.python-version`; and every
   shared file of the site project: `_quarto.yml`, the filters, the assets,
   the scripts and pages at the top of `site/`, the glossary, the reference
   register, the curriculum file, and `src/pbc/authoring`. The digest is a
   hash over the content of those files, computed by one function that the
   lesson source checks also exercise. When the analysis cannot follow a
   lesson's inputs with certainty (a dynamic import, a path put together
   from parts, a cell in another language, a file read outside the known
   locations, a use of `__file__` that is not a path, a path constant that
   names the whole repository or leaves it, the use of a constant that may
   be a path and whose value cannot be followed, such as `EXPECTED_DIR =
   make_expected_dir()`), the lesson has no digest, and
   the run is a full run: every lesson is executed and checked (decision
   4), as the requirements say
   when the inputs cannot be determined with certainty. The digests of
   every lesson are written beside the built site. The digest covers
   what the scientific cells of a lesson compute from. It deliberately
   leaves out the front matter of the other lessons and the build commit:
   they feed the presentation that decision 9 regenerates on every build,
   and putting them in the digest would turn every pull request that adds
   a lesson into a full run.

2. **The base is the verified result of the latest successful run on
   `main`.** That run publishes, beside the site and its checksums (ADR 012
   decision 6), the executed results of every lesson (the `_freeze` store
   of the build), the digests, and the identity of the checks that
   produced it (decision 10). Only a run whose aggregate `verify` check
   passed publishes a base. A pull request run retrieves the latest base
   read-only and accepts it only when the run that produced it is a
   `push` run on `refs/heads/main` whose aggregate `verify` check
   concluded with success. The workflow establishes that from the
   producing run's recorded event, branch, and conclusion, never from the
   artifact's name, its recency, or anything the artifact says about
   itself: a pull request run, including one from a fork, uploads
   artifacts too (the built site for review) and must not be able to
   supply the base a later pull request is verified against. The
   contents of a base (the executed results, the digests, the check
   identity) are data; nothing in it is executed or read as
   configuration. An artifact of a pull request run, an artifact of a
   `main` run whose `verify` did not succeed, and an artifact whose
   provenance cannot be established are rejected, and the run is a full
   run. When no acceptable base exists, when it cannot be read, or when
   its format is not the one the current code writes, everything runs as
   well. Because digests are content hashes, the base need not be the
   merge base of the pull request: a lesson whose inputs are
   byte-identical to those verified on `main` was verified with exactly
   these inputs, whatever commit that was.

3. **What runs less often, and what the base provides.** On a pull request
   with a base:

   | Check | With a base |
   |---|---|
   | Site build | Starts from the base's executed results with the entries of every changed lesson removed; Quarto executes the changed lessons and renders every page. The header, the navigation, and the provenance of every page, and every page that is not a lesson, are produced by this build and never taken from the store (decision 9). A changed lesson's time is measured during the build against the 30-second budget. |
   | Determinism | The second build starts from the same restored state as the first, so the changed lessons execute twice and the comparison still covers every byte of the site. |
   | Reproduction in a fresh clone | Runs for the changed lessons, which are the lessons this run executed. A reproduction compares bytes with a result this run computed on the machine of the comparison, never with a result of the base (ADR 012 decision 4). |
   | Checks of one page (accessibility, reading without scripts, widths, payload) | Run for every page whose built bytes differ from the base's, which includes every changed lesson, every page whose header or links changed because of it, and the pages built from all lessons; a page that is byte-identical to a checked page of `main` is not checked again. The bytes are compared with the build commit normalised, the one value every page carries that changes with every commit; that the commit a page names is the commit of the run is checked separately (decision 9). When the identity of the checks differs from the base's, the run is a full run (decision 10). |
   | Everything else | Unchanged: lint, format, unit tests, lesson source checks, dataset checks, the Lean build in full, the integration tests, and the checks of the site as a whole (links, origins, search, learner state, widgets). |

   The result of an unchanged lesson is never recomputed and never
   recorded as computed by the pull request; the record of the run names
   the base it used.

   *Amendment note (Issue #213, 2026-10-19).* The per-page checks are also
   run for every page when any non-page file of the site record (a style
   sheet, a script, a font, an image, or any other file that is not
   HTML) differs from the base's, or is added or removed, because such a
   file changes how every page is displayed even when no page's bytes
   differ. This selects no lesson for execution: the lessons executed,
   and the reproductions, are those of the changed lessons only. A page
   selected only for this reason is recorded as such in the record of the
   checked pages. The text of the decision is otherwise unchanged.

4. **What stays unconditional, and what shared code means.** A full run
   executes and checks every lesson. It is: every run on `main`, which
   uses no base and verifies everything, so that the published site is the
   site that was verified in full (ADR 003 decision 3, ADR 012 decision
   6); a run without an acceptable base, or whose base is rejected by
   its provenance, cannot be read, or is of another format (decision 2);
   a run in which any lesson has no digest
   (decision 1); a run whose check identity differs from the base's
   (decision 10); and a run in which a shared input changed. A shared
   input is an input of every lesson, so a change to it changes every
   digest: `src/pbc/authoring`; the templates, the filters, the assets,
   the shared scripts and pages at the top of `site/`, the glossary, the
   reference register, and the curriculum file; the site configuration
   `_quarto.yml`; `pyproject.toml`, `uv.lock`, and `.python-version`; the
   Lean toolchain and manifest; and a module of `src/pbc` whose importers
   cannot be followed with certainty (a module that imports in a way the
   analysis cannot follow, so that which lessons depend on it is
   uncertain), which the digest function treats as an input of every
   lesson. Any other module of `src/pbc` is an input of the lessons that
   import it, directly or through another module, and a change to it
   selects every one of them: that is the granularity the requirements
   give ("the modules of `src/pbc` it imports"), and a module every lesson
   imports selects every lesson. The checks that do not depend on a
   lesson, listed above, run on every run. No check leaves
   `scripts/verify.conf`; a check in a group that runs less often runs on
   the lessons the selection names, never on none when a lesson changed.

5. **The selection is made by `./scripts/verify.sh`.** It gains an option
   that names a base directory (the retrieved base); the checks that can
   use it read the selection from the one place the script writes it. A
   run without that option verifies everything, locally and in CI. The CI
   workflow passes the base only on `pull_request` runs. A run with a base
   is a verification of the change against that base and says so in its
   record; the workflow self-tests keep running as ADR 005 and ADR 012
   decide.

6. **The execution cache is restored, never committed.** ADR 002's rule
   that generated artifacts are never committed stands: the `_freeze`
   store lives in the artifact of a `main` run and in the working
   directory of a build, is listed in `.gitignore`, and the committed
   artifact check rejects it like any build output. The default build
   (`freeze: false` today) becomes a build that writes the store; a page is
   taken from the store only when the selection says the lesson is
   unchanged, never because Quarto's own source hash matched.

7. **Budgets.** The 12 minutes for a typical pull request with warm caches
   (ADR 003 decision 5, ADR 012 decision 8) are the acceptance criterion of
   the feature that delivers this decision (F61), measured with the lesson
   count of that day and projected to 110 lessons from the measured
   per-lesson cost of rendering a page from the store; the 25-minute
   budget for cold caches applies to pull requests. A full run (decision
   4) has no wall-clock budget, but every job of it must fit the job
   timeout at 110 lessons, because a run on `main` that times out
   publishes nothing. The timeout stays 45 minutes (ADR 012 decision 9),
   and the planning budget for one job of a full run is 35 minutes with
   cold caches, leaving 10 minutes of the timeout for a runner slower
   than any measured. The per-lesson cost and the fixed cost are derived
   from the slowest run F58 measured: the cold run of the `build` job
   took 20 min 27 s at twenty-two lessons, which is about 41 seconds per
   lesson (change request, section 15: about 10 for the build, 10 for
   the second build, 21 for the reproduction) over a fixed cost of about
   5 minutes. The same job took 12 min 33 s on a faster runner with warm
   caches, so the 41 seconds already describe the slowest measured runner
   with cold caches and are not scaled a second time. At that cost one
   such job holds about 40 lessons within the budget and would need
   about 80 minutes at 110. Decision 11 bounds it with lesson shards of
   at most S = 32 lessons: about 27 minutes on the slowest measured runner with
   cold caches, about 8 minutes under the 35-minute budget, with the 10
   minutes to the timeout on top of that. S = 32 rests on this
   derivation and is confirmed or lowered, never raised, by the
   per-lesson cost that F61 (criterion 9) and F113 (criterion 1) measure
   on the slowest runner of their runs. The per-check budgets of ADR 003
   stand. F61 projects the full run to 110 lessons from the cost it
   measures and records the lesson count at which one unsharded job
   leaves the budget; the feature that delivers decision 11 (F113) lands
   before that count is reached.

8. **Out of this decision.** The Lean build runs in full on every pull
   request until the human decides otherwise (requirements, unresolved
   question 8). The integration tests and the workflow self-tests are not
   selected; they are not on the longest path. A schedule, a path filter in
   the workflow file, or a dropped check stays unavailable: the selection
   is by content, fails safe, and lives in the verification script.

9. **Context-dependent presentation is regenerated on every build; the
   store holds scientific results only.** A lesson page carries output
   that depends on things outside the lesson's inputs: the header
   (`lesson_header`), which reads the front matter of every lesson for the
   previous and next links, the prerequisites, the related lessons, the
   course, the slot, and the position in a path; and the provenance of the
   "Reproduce this" section, the code excerpts, and the Lean excerpts
   (`reproduce_this`, the excerpt and Lean helpers), which embed the build
   commit. Today these are executed cells, so a replayed store would show
   the base's navigation and the base's commit on an unchanged page. With a
   base they are never taken from the store: the build produces them from
   the current front matter, the current curriculum file, and the commit
   of the run, for every page, changed or not. F61 chooses the mechanism
   (the helpers leave the executed cells and become a step of the build,
   such as a filter or a post-render over marked regions; or the store is
   written without the outputs of the cells so marked and those cells run
   on every build), and the test is the same either way: on a run with a
   base, inserting a lesson, retitling one, or changing its prerequisites
   or related links updates the header and the previous, next, and related
   links of every unchanged page that refers to it, and the provenance of
   every page names the commit of the run, never the commit of the base.
   The pages that are not lessons (the home page, the path page, the
   evidence map, the glossary, the about page) are built from every lesson
   and are never restored from the store.

10. **The checks are versioned with the base.** A result reused from the
    base is a result of the checks as they were on `main`; a pull request
    that fixes or strengthens a check must not merge on the older check's
    result. The base therefore records the identity of the checks that
    produced it: one digest over the implementation of every check that
    runs less often with a base and over what it runs with:
    `scripts/verify.sh`, `scripts/verify.conf`, the scripts those checks
    name (`scripts/build-site.sh`, `scripts/check-determinism.sh`),
    `tests/e2e`, `tests/support`, `tests/integration`,
    `tests/e2e/shards.json` (the division of the built-site tests between
    the two `e2e-pages` jobs of ADR 012, not the lesson shards of
    decision 11), `pyproject.toml`, `uv.lock` (which fixes the browser build and
    the accessibility engine), and the browser tooling the preparation of
    a runner installs. When the identity of the current tree differs from
    the base's, nothing of the base is reused: the run is a full run
    (decision 4), which executes every lesson, checks every page, and
    reproduces every lesson with the current checks, and its record says
    why. A lesson's results depend on its inputs and not on the checks,
    so the executed results of the base could in principle be kept; they
    are not, because the base was computed on another runner and a
    reproduction compares bytes on the machine that computed them (ADR
    012 decision 4). The rule that follows holds for every run: a lesson
    selected for reproduction is a lesson this run executed, and a
    comparison of bytes is made only against a result this run computed.
    The cost of an identity change is the cost of a shared-code change,
    which is the fail-safe direction. The identity is one digest, so that
    a change whose impact is uncertain reruns everything; F61 may split it
    per check group only with a test that shows each group's inputs are
    complete, and anything a split does not classify belongs to every
    group. A base without an identity is of another format and runs
    everything.

11. **A full run executes the lessons in same-machine lesson shards and
    assembles one site.** The group `build` of ADR 012 decision 3 holds
    the three executions of every lesson, so a full run grows past the
    job timeout at about 40 lessons (decision 7). The group is split in
    two, and every comparison of bytes stays on the machine that computed
    both sides (ADR 012 decision 4). A *lesson shard* is a share of the
    lessons that one `build` job executes; the verification script
    derives the shares from the lesson count and reads them from no
    file. It is a different division from `tests/e2e/shards.json`, which
    splits the tests of the built site between the two `e2e-pages` jobs
    of ADR 012 and is unchanged by this decision; "shard" alone in this
    record means a lesson shard.

    - `build`, run by each of N lesson shards: the Lean build in full (cheap
      with Mathlib's build cache, and a lesson page reads the record it
      writes); the execution of the lessons of the shard, their second
      execution for determinism, and the reproduction of each of them in
      a fresh clone, compared with the pages and figure files this shard
      rendered; and the publication of the shard's executed results (its
      part of the store, with the pages it rendered) with the checksum of
      every file.
    - `assemble`, run by one job after every shard: it retrieves the
      parts, requires that the files are exactly the recorded ones and
      that the parts cover every lesson exactly once, renders every page
      from the parts without executing a scientific cell of any lesson
      (decision 9 produces the context of every page here, from the
      current front matter, curriculum file, and commit; if F61 keeps the
      header and provenance helpers as executed cells that run on every
      build, the assembly runs those context cells and nothing else of a
      lesson, and its runner prepares what they read, in particular the
      Lean build record the Lean excerpt helper checks, restored from a
      shard's part and required equal across the parts, or recreated by
      the Lean build, which is cheap with Mathlib's cache; F61's
      measurement of the render cost per page without execution is taken
      on a build of the same shape, so the assembly's cost is the
      measured one), renders a second time and compares
      the bytes on its own machine, requires that each lesson page it
      rendered is byte-identical to the page its shard rendered and
      reproduced (the store holds the executed outputs and the figure
      files as bytes, so the render is the same whatever executed; a
      difference means the published page is not the reproduced one and
      fails the run), and uploads the one built site with its checksums
      (ADR 012 decision 6), which the `e2e` jobs check and `deploy`
      publishes.

    The lesson shards and the assembly are the code path of decision 3: a
    lesson shard is a run whose selection is its share of the lessons and
    whose store holds only what it executed; the assembly is a build whose
    selection is empty and whose store is the union of the parts (and, on
    a pull request, the base for the unchanged lessons). The verification
    script assigns the lessons to lesson shards from the lesson list in a
    stable order, at most S lessons per shard with S = 32 declared in
    `scripts/verify.conf`, N the ceiling of the lesson count over S (four
    at 110 lessons), and never from a declaration file; a test fails when
    a lesson is in no shard or in two, when a shard exceeds S, and when
    the lesson shards of the workflow file are not the lesson shards the
    script derives. A pull request run has the same
    jobs: each shard executes the changed lessons of its share, and a
    shard with nothing to execute finishes in its fixed cost. Locally,
    `./scripts/verify.sh` without options is unchanged in meaning: it
    executes every lesson in one build on one machine and makes the
    comparisons there, so a local run is still a verification of
    everything; `--shard k/N` and the assembly are partial runs like
    `--only` and verify nothing by themselves. ADR 012 decision 2 holds
    with a shard matrix counted as the one job of its group, and the
    tests marked `same_machine` run on the machine that computed the
    bytes they compare with, which is the shard for a reproduction and
    the assembly for the determinism of the render. A shard that fails
    fails `verify`; so does an assembly whose parts do not cover every
    lesson exactly once. Should the hosted runners show that a page
    rendered from the same store differs between machines, the fallback
    is not a tolerance but a revision of this record that raises the
    timeout of the one `build` job for full runs explicitly, with the
    growth per lesson stated; F113 measures it.

## Alternatives considered

- **Path filters in the workflow file** (skip the site build when no lesson
  changed). Rejected, as in ADR 003: a skipped required check counts as
  passed, a filter does not see that `src/pbc` changed what a lesson
  computes, and the selection would exist only in CI.
- **Select by the files a pull request touches, relative to its merge
  base.** Rejected: a touched-file list needs a dependency analysis anyway
  to find the lessons a changed module affects, and it has to find a base
  artifact for the exact merge base, which may not exist. Content digests
  need one analysis, work with any verified base, and say nothing about a
  lesson whose inputs changed in a way the analysis did not see, because
  then the digest changes.
- **Commit Quarto's freeze store** (the alternative ADR 002 rejected).
  Still rejected: a committed cache drifts, and pull request diffs would
  carry binary outputs. A store restored from a verified artifact has
  neither problem, because it is never a source.
- **A second Quarto project that holds only the changed lessons.**
  Rejected: previous and next links, the path page, the evidence map, and
  the search index need every lesson rendered.
- **Reuse page checks by digest instead of by bytes.** Rejected: a page's
  bytes can change through another lesson (its header names a related
  lesson) without its own inputs changing; comparing the built bytes with
  the base catches that and errs towards checking more.
- **Reduce the three executions by dropping the reproduction test or
  running determinism nightly.** Rejected: no check is dropped, and a
  nightly check would let a nondeterministic lesson merge.
- **Put the front matter of every lesson and the build commit into every
  digest** (so that a cached header or provenance can never be stale).
  Rejected: every pull request that adds a lesson, or any commit at all,
  would run in full, and the cached page would still be checked instead of
  the page the reader gets. Decision 9 regenerates what depends on the
  context and caches only what depends on the lesson's inputs.
- **Reuse the per-page checks whatever changed in the checks themselves,
  and trust the run on `main` to catch it.** Rejected: the pull request
  that changes a check is exactly the one whose result must come from the
  new check (I7); failing only on `main` is the direction the rule must
  not fail in. Decision 10 versions the checks with the base.
- **On an identity change, reproduce every lesson against the store of
  the base and keep the unchanged results.** Rejected: the store was
  computed on another runner, and ADR 012 decision 4 observed last-digit
  differences between runners, so an unchanged lesson could fail its
  reproduction without any change to it. That is a false failure, not
  more verification. Decision 10 makes the run a full run instead.
- **Treat a lesson whose inputs cannot be followed as the one changed
  lesson.** Rejected: the requirements say that when the inputs cannot be
  determined with certainty everything runs, and an unfollowable import
  may hide a dependency of another lesson. Decision 1 makes the run a
  full run.
- **Keep one `build` job for a full run and raise its timeout to what 110
  lessons need.** Rejected as the first choice: about 80 minutes with
  cold caches, growing with every lesson, on the path of every push to
  `main` and of every pull request that changes shared code; a slow
  runner would still time out and publish nothing. Kept as the explicit
  fallback of decision 11, to be taken only by a revision of this record.
- **Give every shard its own full site build and publish one of them.**
  Rejected: the other shards would check a site that is not the published
  one (ADR 012 decision 6), and every shard would render every page.
  Decision 11 renders the published site once, from the parts.

## Consequences

- A pull request that changes one lesson executes that lesson twice and
  reproduces it once; every other lesson is rendered from the base's
  results without execution. The expected cost is the render of every page
  without execution plus the fixed checks; the feature measures the render
  cost per page, which is the number that decides whether the budget holds
  at 110 lessons.
- A pull request that changes `uv.lock`, `src/pbc/authoring`, the site
  configuration, or another shared input of decision 4 runs in full, as a
  run on `main` does; one that changes a module of `src/pbc` executes
  every lesson that imports it, which for a widely imported module is
  every lesson. That is the fail-safe direction and the price of shared
  changes.
- A full run is bounded: at 110 lessons it is four lesson shards of at
  most 32 lessons beside the assembly, each within the budget of decision 7, so a
  push to `main` and a full-run pull request fit the timeout at the
  target size. The price is more runner minutes (every shard prepares its
  own runner) and a second step on the longest path, the assembly, whose
  cost is the render of every page without executing a scientific cell,
  the number F61 measures on a build of the same shape.
- The workflow needs read access to the artifacts of earlier runs and a
  retention long enough for a base to exist; a pull request older than the
  retention runs in full. The read access is used only for a base whose
  provenance decision 2 accepts, so an artifact a pull request uploaded
  never becomes a base. The permission change is reviewed with the
  feature as a High-risk change.
- The digest function is a new guarantee with the same limits as the
  name analysis of the dataset check: it follows names, not pixels. Its
  fail-safe is that an unfollowable lesson makes the run a full run, and a
  test shows that every kind of input in decision 1 changes the digest.
- The base was built on another runner. A page rendered from the store
  carries the base's bytes, not what this runner would compute, so the
  risk is not a differing page but a comparison of bytes against a result
  another machine computed; decision 10 and decision 11 rule that out by
  comparing only with results this run computed on the machine of the
  comparison, and the determinism comparison stays within one run.
- `--reuse` of the verification script (skip a run whose content was
  verified before) and the base are different things: the first is a
  record of a whole verification, the second an input to a selective one.
- The header and the provenance of a lesson stop being plain executed
  cells, or the store stops holding their output; either way the lesson
  template and the authoring helpers change once, in F61, and the lesson
  bodies do not. The pages a pull request renders then always show the
  navigation of the pull request's tree and name its commit, which is what
  a reviewer of the attached site artifact expects.
- A pull request that changes a test of the built site, the verification
  script, or the browser tooling is a full run, as a run on `main` is; a
  pull request that changes a lesson and nothing of the checks reuses the
  checks of the base. The check identity is a second digest beside the
  lesson digests, with the same fail-safe: when it is missing or differs,
  everything runs.
- Two features deliver this record: F61 the selection, the base, the
  store, the regenerated context, and the check identity; F113 the
  lesson shards and the assembly of decision 11. Until F113 lands, a full run is
  the one `build` job of ADR 012, which fits the budget of decision 7 up
  to the shard size, 32 lessons; no lesson feature takes the count past
  it before F113 is delivered.
