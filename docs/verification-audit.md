# Verification audit (F118)

The record that Issue #180 (F118) produces before a check is removed, a job
is divided, or an agent's obligation is lifted: what a full run executes and
compares, whether the third build duplicates the determinism build, what the
check identity covers, where the time of `integration` goes, which local
builds the agent workflow demands, and what the proposal for the owner's
interim full-run gate is. It changes no check, job, script, or prompt; F119
and F120 take their evidence from here. The measurements it rests on, with
run identifiers and cache state, are in `docs/release-readiness.md`, "The
full run and the one-lesson pull request, decomposed (F118)". The facts that
code can show are asserted by `tests/integration/test_verification_audit.py`,
so the record does not drift from the repository.

**Applied by F119 (Issue #185), under ADR 017 decisions 7 and 8, which the
owner accepted on 2026-10-15.** The tables below record the state at the base
commit of F118; where F119 changed it, the place says so, and the tests
assert the state after F119:

- `test_a_second_build_gives_byte_identical_previews` and its helper
  `tests/support/second_build.py` are removed, after the regression test
  `tests/integration/test_determinism_check.py` showed that a differing,
  missing, or extra preview, and any other differing file, still fails
  `scripts/check-determinism.sh` in a full run and in a selective run. **A
  lesson executes three times in a full run** (build 1, build 2, and its
  reproduction) where it executed four; in a selective run an executed
  lesson executes three times and an unchanged lesson is rendered from the
  store twice. Since F117 (ADR 016 decision 4) the experiment check adds a
  fourth execution of an executed lesson's science, without a render: its
  experiment, in one learner environment of a fresh clone, in the check
  `site-checks-reproduction` of the group `build`. Its cost per lesson is
  measured with the first full run on `main` after the switch
  (`docs/release-readiness.md`).
- The `integration` job is divided into the three parts of "Division into
  independent parts": the checks `check-tests-quarto`, `check-tests-browser`,
  and `check-tests-other` of `scripts/verify.conf`, in three jobs of
  `.github/workflows/ci.yml` with the preparation each part needs.
- `tests/integration` left the check identity (`CHECK_DIRECTORIES` of
  `src/pbc/authoring/digest.py`), with the completeness test this record
  names; every other input stays, and the identity stays one digest.
- The local build obligations of the inventory are replaced by the three
  verification tiers of ADR 017 decision 7: the targeted run
  (`./scripts/verify.sh --targeted`), `./scripts/verify.sh --base`, and the
  full run (`docs/development.md`, "Verification").

Read on 2026-10-15 at the base commit `553214c` of the feature branch.

## Call graph

Every check of the groups `build` and `e2e-*` of `scripts/verify.conf`, in a
full run (no base, a base that cannot be used, or a change to the checks) and
in a selective run (an accepted base, ADR 014). "Execute" means that Quarto
runs the cells of the lessons; a restored lesson is rendered from the store and
its cells do not run. A *build* is a run of `scripts/build-site.sh`.

| Check (group) | Build it performs | Lessons it executes: full run | Lessons it executes: selective run | Bytes it compares |
|---|---|---|---|---|
| `lean-build` (`build`) | none; `lake build`, the axiom audit, and the exercise stubs | none | none | none |
| `site-build` (`build`) | **build 1** of `site/` into `site/_site`, with `site/_freeze` empty (full) or restored from the base for the unchanged lessons (selective); it writes `_digests.json`, `_timings.json`, and `_pages.json` | every lesson, once | the selected lessons, once | none; it fails on a failing cell and on an equation that cannot become MathML |
| `determinism` (`build`) | **build 2**: `scripts/check-determinism.sh` copies the sources without `_site`, `.quarto`, `_freeze`, `_digests.json`, and `_timings.json`, and builds the copy into a temporary directory with the selection of the run | every lesson, once | the selected lessons, once (the others restored again) | every file of build 1 with every file of build 2 (`diff -r`), names and bytes: 178 files at 32 lessons |
| `site-checks-reproduction` (`build`), the reproductions | for each lesson a clone of the tracked files and `quarto render` of that one page, as the page's "Reproduce" commands say (no store, so no restore) | its own lesson, once, in each of the lessons' reproduction tests: every lesson | the same, for the lessons the run executed only (the tests of the others are deselected) | the regenerated page and every figure file of its directory with the page and figure files of build 1 |
| `site-checks-reproduction` (`build`), `test_a_second_build_gives_byte_identical_previews` (removed by F119) | **build 3**: `tests/support/second_build.py` copies the sources without the same five names and builds the copy through `scripts/build-site.sh`, with the selection of the run when it is selective | every lesson, once | the selected lessons, once | the names and bytes of the files in `previews/` of build 1 with those of build 3 |
| `site-checks-pages-1`, `site-checks-pages-2` (`e2e-pages-1`, `e2e-pages-2`) | none; they read the site that `build` built | none | none | none; the per-page checks run for every page (full) or for the pages whose normalised bytes differ from the base's record `_pages.json` and the pages of the executed lessons, and for every page when a file that is not a page differs (selective) |
| `site-checks-other` (`e2e-other`) | none | none | none | none; the same page selection for the per-page checks |

- **A lesson executes four times in a full run** (three since F119 removed
  build 3): build 1, build 2, build 3,
  and its reproduction. ADR 014 decision 11 counts three. In a selective run
  an executed lesson also executes four times and an unchanged lesson none;
  it is rendered from the store three times (builds 1, 2, and 3), 1.2 to 1.4 s
  each.
- No test of `tests/integration` executes the cells of a published lesson: its
  builds are of fixture sites, of the home page alone, or of copies whose
  lessons are reduced to their front matter.
- **Measured duration of each step** (full run, 22, 28, and 32 lessons, from
  the logs of runs 38545077253, 38527223459, 38607388478, 38621916706,
  38639021950, 38659296393, and 38687330455): the Lean build 12 to 20 s;
  `site-build` 2 min 43 s to 5 min 49 s; `determinism` 2 min 30 s to 5 min 31 s;
  the reproduction group (the reproductions and the third build) 8 min 02 s to
  17 min 47 s, of which the third build is estimated at the duration of
  `determinism` (the same build from a fresh copy) and the 32 reproductions at
  14 to 25 s each. In the three one-lesson pull requests (runs 38547877605,
  38547877332, 38547883087; 22 lessons, one executed): the Lean build 14 to
  15 s, `site-build` 1 min 44 s to 1 min 46 s, `determinism` 1 min 29 s to
  1 min 33 s, the group of two tests (one reproduction and the third build)
  2 min 04 s to 2 min 21 s. The `e2e` jobs took 3 min 50 s to 4 min 29 s
  (`e2e-pages-*`) and 5 min 48 s to 7 min 30 s (`e2e-other`) in the full runs at 28
  and 32 lessons, 1 min 39 s to 2 min 21 s and 5 min 49 s to 6 min 03 s in the
  one-lesson pull requests. The full table is in `docs/release-readiness.md`.

## Redundancy verdict: the third build

**Verdict: `test_a_second_build_gives_byte_identical_previews` duplicates the
determinism check with identical coverage.** Everything it compares, the
determinism check compares under the same build conditions, and it catches
no failure the determinism check does not.

| | `scripts/check-determinism.sh` | `test_a_second_build_gives_byte_identical_previews` |
|---|---|---|
| State the build starts from | a copy of `site/` without `_site`, `.quarto`, `_freeze`, `_digests.json`, `_timings.json` | `tests/support/second_build.py`: a copy of `site/` without the same five names |
| Selection it honours | `PBC_STORE_SELECTION` is set when the selection file exists, whatever its mode; `pbc.authoring.store` restores from the base only for the mode `selective` | `PBC_STORE_SELECTION` is set when the mode is `selective`; in every other mode the build is empty-started, as `store.prepare` makes it for mode `full` |
| What a failed build does | fails the check with the log | fails the test with the log |
| Files compared | the whole tree of build 1 with the whole tree of build 2: names and bytes (`diff -r`), previews included | names and bytes of the files in `previews/` only |
| Failure modes caught | a build-time value, a path, a random identifier, a cache effect in any file; a missing or an extra file | the same, in the previews only |
| Fails when no preview exists | no (two empty directories are equal) | yes (`assert first_files`), but `test_every_lesson_has_one_verified_preview_within_the_budget` of `tests/e2e/test_built_site.py` already requires one preview per lesson in a check of the built site |

The two builds differ in where the copy lies and when it runs, and both
differences are of the kind a determinism check exists to expose: neither
check names the location or the time, so one comparison covers the other.
Under the same selection (full, or selective with the same base) they start
from the same state, which is what the repair of pull request #164 made them
do.

**What the duplicate costs.** The third build costs the same as `determinism`:
2 min 30 s to 5 min 31 s in a full run at 22 to 32 lessons, 18 to 19 percent of
the group `build`, and 1 min 29 s to 1 min 33 s (about 70 percent of the group
of two tests) in a one-lesson pull request.

**The regression test F119 must add before it removes the test:** a
differing preview still fails `verify`. Two trees built by `scripts/build-site.sh`
that differ in one byte of one file under `previews/` must make
`scripts/check-determinism.sh` fail and name the file, in a full run and in a
selective run, and the same trees with no difference must pass. The test
builds no lesson: it gives the script a first build and a copy whose second
build is replaced by a fixture, or it tests the comparison at the level of
`diff -r` as `tests/integration/test_verification_audit.py` does now for
the property that the comparison covers `previews/`.

**Applied by F119.** The regression test is
`tests/integration/test_determinism_check.py`: it runs the script with a
fake `scripts/build-site.sh` that writes a fixture tree, so a differing,
missing, or extra preview, and a differing page, fail the check and are
named, in a full run and in a selective run (the selection reaches the
second build), and identical trees pass. The preview test and
`tests/support/second_build.py` are removed; the two tests of
`tests/integration/test_store.py` that used the helper exercise the
determinism check itself. A lesson without a preview still fails
`test_every_lesson_has_one_verified_preview_within_the_budget`.

## Validity domains of the check identity

`check_identity` (`src/pbc/authoring/digest.py`) is one digest over the
files of `CHECK_FILES` and over every file under `CHECK_DIRECTORIES`; a
missing file is part of it. A base made under another identity is not used
(ADR 014 decision 10). What a base lets a run skip is: the execution of the
unchanged lessons (build 1, 2, and 3), the reproduction of the lessons it did
not execute, and the per-page checks of the pages whose bytes equal the
base's. The four domains: **S** scientific execution (what runs a lesson's
cells and with what), **R** rendered output (what writes the page, the
figures, and the sitemap), **V** the verification rule (which check runs and
what it requires), **B** the browser tooling (the browser build and the
accessibility engine the page checks use).

### Classification of the inputs

| Input | S | R | V | B | Verdict |
|---|---|---|---|---|---|
| `scripts/verify.sh` | x | | x | | every domain: it makes the selection that decides what executes, and runs the checks |
| `scripts/verify.conf` | x | x | x | | every domain: it names the command of every check, including the build |
| `scripts/build-site.sh` | x | x | | | every domain: it executes, renders, and normalises the sitemap, and it is the build of the determinism and the third build |
| `scripts/check-determinism.sh` | | | x | | V only |
| `pyproject.toml` | x | x | | x | every domain: the Python pins, the Quarto and rendering stack, Playwright, and the accessibility engine |
| `uv.lock` | x | x | | x | every domain: the same pins, locked |
| `.github/actions/prepare/action.yml` | x | x | | x | every domain: it installs the toolchains and the browser build |
| `tests/e2e` | | | x | | V only: the per-page checks and the reproduction; `tests/e2e/shards.json` is inside it and divides tests between jobs |
| `tests/support` | | | x | | V only, shared by `tests/e2e` and `tests/integration`: it belongs to the domain of each of them |
| `tests/integration` | | | x | | V only, and no consumer of a reused result: `check-tests` is never reduced by a base; left the identity with F119 (the `check-tests-*` checks are its only consumers) |

**Rule.** An input that this table does not classify belongs to every domain,
as ADR 014 decision 10 requires. `tests/integration/test_verification_audit.py`
fails when an input of `CHECK_FILES` or `CHECK_DIRECTORIES` is not in the
table, so a new input cannot be taken for a single-domain one.

**Which domains could be split, and which could not.**

- **Cannot be split:** `scripts/verify.sh`, `scripts/verify.conf`,
  `scripts/build-site.sh`, `pyproject.toml`, `uv.lock`, and
  `.github/actions/prepare/action.yml` each affect two or more domains. A
  change to any of them can change what a lesson computes or how a page is
  written, so each stays in every domain (and stays a reason for a full run).
- **Could be split off, with a complete-input test:** `tests/integration`.
  The checks that a base lets a run skip are the builds, the reproductions,
  and the per-page checks; they execute `scripts/build-site.sh`,
  `scripts/check-determinism.sh`, `tests/e2e`, and `tests/support`, and none of
  them reads or imports `tests/integration` (the test asserts that the
  only mentions of it are comments, the docstrings of two support modules, and
  the check `check-tests` that runs it). The test a split needs: no file of
  `tests/e2e`, `tests/support`, `scripts` (except `verify.conf`, which names
  `check-tests`), `src`, or `.github` reads, imports, or executes a file of
  `tests/integration`, and `check-tests` is the only consumer of it. Without
  that test the directory stays in the identity. The effect is measurable: of
  the 102 merges to `main` from 2026-10-01 to 2026-10-15, 71 changed an input
  of the identity and 8 of those changed `tests/integration` and no other
  input; each of those 8 made the next run against a base a full run, by the rule of ADR 014 decision 10.
  **Applied by F119**: `tests/integration` is no longer in
  `CHECK_DIRECTORIES`; the completeness test is
  `test_no_check_that_a_base_reduces_reads_the_integration_tests` of
  `tests/integration/test_verification_audit.py`, and
  `tests/integration/test_selection.py` shows that a change to an input of
  each domain, and to an input no classification names, gives a full run,
  while a change to `tests/integration` keeps the selection.
- **Possible but without effect:** `scripts/check-determinism.sh` is V only,
  and `tests/e2e` and `tests/support` are V only, but a change to them
  changes the logic of a check that certifies the pages of the base (the
  per-page checks) or compares bytes of the executed lessons (the
  reproduction and the determinism check): a stronger check must not
  certify a result reused from an older one (ADR 014 decision 10), so they
  stay in the identity until the same-commit design of F120 decides what a
  reused result is.

## The critical path of `integration`

The job runs `check-tests` (`pytest tests/integration`: 804 tests in 26 files
at this commit before this file) after a runner preparation of about 100 s with
the Lean packages restored and the browser installed. At 32 lessons the tests
took 10 min 10 s to 14 min 31 s (runs 38659296393, 38621916706, 38687330455:
the same tests, the three runners). It is the longest job of one of the three
one-lesson pull requests (14 min 29 s in #163) and the third path of the other
two. It executes no lesson, so the lesson count does not move it.

### Where the time goes

The file of each test is run in order; the time of a file is the interval
between the end of the previous file and its end in the log of the job, in
seconds, from the three runs (fast, middle, slow runner):

| Test file | Needs | Fast | Middle | Slow |
|---|---|---|---|---|
| `test_store.py` | Quarto builds of fixture sites | 124 | 177 | 163 |
| `test_context.py` | Quarto builds | 90 | 133 | 129 |
| `test_site_checks.py` | the browser, fixture sites | 97 | 102 | 102 |
| `test_site_check_division.py` | `pytest --collect-only` of `tests/e2e` for each part | 65 | 100 | 97 |
| `test_lean_check.py` | the Lean packages (one `lake build` per case) | 63 | 83 | 87 |
| `test_lesson_checks.py` | Python only (lessons written to violate a rule) | 54 | 86 | 84 |
| `test_lesson_template.py` | a Quarto build and the browser | 55 | 90 | 83 |
| `test_lesson_digest.py` | Python only | 18 | 31 | 32 |
| `test_site_build.py` | Quarto builds | 14 | 23 | 22 |
| `test_home_build.py` | a Quarto build | 10 | 16 | 16 |
| `test_lean_lessons.py` | the Lean packages | 7 | 10 | 12 |
| the other 15 files | Python only | 0 to 2 each | 0 to 4 each | 0 to 3 each |
| all 26 files | | 607 | 867 | 843 |

The per-file figures are the time of a file in a run that executes the files
in sequence, so they are exact for the sum and for a file of more than a few
seconds, and one second of rounding at most for the others; they are not a
`pytest --durations` listing, which the log does not hold.

### Division into independent parts

A division that runs every test exactly once, in the manner of the built-site
checks: two parts name their files, a third runs every file the first two do
not name, so a file added later runs somewhere and none runs twice. Parts by
what they need, balanced by the mean of the three runs (772 s in all):

| Part | Files | Needs | Mean of the three runs |
|---|---|---|---|
| 1 | `test_store.py`, `test_context.py`, `test_home_build.py`, `test_site_build.py` | the Quarto of the locked environment | 306 s |
| 2 | `test_site_checks.py`, `test_lesson_template.py`, `test_setup_page.py`, `test_browser_check.py`, `test_site_check_division.py` | the browser | about 265 s (setup page and browser check under 5 s) |
| 3 | every other file: `test_lean_check.py`, `test_lean_lessons.py`, `test_lesson_checks.py`, `test_lesson_digest.py` and the 13 small files, with this audit's test | the Lean packages (restored only here) | about 205 s |

What it would shorten: the longest job of a one-lesson pull request falls
from about 100 s + 772 s to about 100 s + 306 s (the slowest part), 6 to 9
minutes in the three runs, and the pull requests' critical path
becomes `build` then `e2e` (13 min 24 s to 13 min 46 s in the three measured
runs) in all three. The cost is the runner time of two more preparations
(about 200 s per run) and one more check in `scripts/verify.conf`; parts 1
and 2 need not restore the Lean packages (saving the Mathlib cache restore, 45
to 60 s of each preparation). No part can be shorter than its largest
file, so `test_store.py` (124 to 177 s) bounds part 1 from below.
**Applied by F119** as the checks `check-tests-quarto` (part 1),
`check-tests-browser` (part 2), and `check-tests-other` (part 3, every file
the first two do not name, so a file added later runs there) of
`scripts/verify.conf`, run by the jobs `integration-quarto`,
`integration-browser`, and `integration-other` of
`.github/workflows/ci.yml`. The test
`tests/integration/test_verification_audit.py` checks, without a browser, that
parts 1 and 2 name files that exist, that no file is named twice, that the
checks name exactly these files, and that
the three parts together collect exactly the tests of the directory, each once.

### Could the reproduction of the lessons run in parallel?

**Not assumed, and the evidence does not support it on one runner.** The
reproductions are most of the group `build` (59 to 60 percent) and each is a
separate clone, so they look independent; four facts decide against taking
that as given:

1. **The per-lesson budget measures wall clock.** Each reproduction asserts
   that the `quarto render` of its page finished within 30 s
   (`LESSON_BUDGET_SECONDS` in `tests/e2e/test_lessons.py`). The slowest page
   of a first build took 21.4 s on a slow runner, 71 percent of the budget: a
   margin of 1.4 times. Two or more renders at once on shared cores take
   longer each, so the check would measure the contention instead of the page.
2. **Contention is unmeasured and likely.** Nothing in the repository limits
   the threads of NumPy's linear algebra (no `OMP_NUM_THREADS` or equivalent)
   and the logs of the jobs record neither the cores of the runner nor CPU
   time against wall time. Without that, the gain of parallel workers is
   unknown, and the same logs show a 1.7 fold spread in the speed of the same
   work between runners.
3. **The comparisons need one machine** (ADR 012 decision 4), which parallel
   workers on the runner keep, but `pytest-xdist` is not a dependency of the
   project and the fixtures of the reproduction test (the session server,
   the shared Lean packages symlinked into each clone) were not written for
   concurrent workers.
4. **The structure that scales is the one the ADR already has**: lesson
   shards of separate jobs (ADR 014 decision 11, paused with F113), which
   give each reproduction its own runner and so its own cores, at the price of
   the preparation of each job.

What a decision needs, from F119 or F120: the CPU time and the wall time of
each reproduction on a runner (`/usr/bin/time` around the render command), and
the same renders with two and four at once. Only if the wall time of the
slowest lesson stays under the 30 s budget with room does a parallel local
split deserve a design; the reproduction group is otherwise cut by removing the
duplicate third build (about a fifth) or by sharding across jobs.

## Inventory of local build obligations

Where the agent workflow and the documentation demand a run of everything
before a result counts, found by searching the files named in the Issue on
2026-10-15. A *targeted run* is the one ADR 017 decision 7 describes (the
unit tests and lesson source checks the change touches, the experiment check
of the changed lessons, the single-page render of each changed lesson page,
the Lean build for affected proofs, and the computation of the selection CI will
make); F119 delivers it as `./scripts/verify.sh --targeted`. None was
applied by F118; F119 applied the replacements of this table after the owner
accepted ADR 017 decisions 7 and 8 (2026-10-15).

| Where | The demand | Replacing targeted check (ADR 017 decision 7) | Change types that keep a local render |
|---|---|---|---|
| `AGENTS.md`, "Definition of Done": `./scripts/verify.sh` passes | a run of every check, including the site build, the second build, the third build, the reproductions, and the built-site checks | the recorded pass of a targeted run, with its base and selection | a full run for a change the selection bounds to no lesson: shared authoring code, templates, filters, assets, the site configuration, the curriculum file, the Python pins, and a change to the checks or their configuration (the identity differs); `./scripts/verify.sh --base` for a change to the front-matter fields that form the learning path or the neighbours' headers, and for a new lesson |
| `.agents/prompts/implementer.md`, "Completion" step 6 and the paragraph after it ("the full run is for the end") | run `./scripts/verify.sh` last, once, as the evidence of the final run | the targeted run last; the single checks while working already are targeted | the same change types |
| `.agents/prompts/triage-implementer.md`, "Completion": run `./scripts/verify.sh` after the last change | the same, for a triage fix | the targeted run of the files the fix touched | the same change types |
| `scripts/finish-feature.sh` (the gate `./scripts/verify.sh --reuse`, and the line "./scripts/verify.sh passed" in the commit message) | a recorded pass of a run without options for the exact content | a recorded targeted run, with its tier, base, and selection, as the finish evidence of an ordinary change | the same change types: they record a full or `--base` run |
| `scripts/review-feature.sh` (the gate `./scripts/verify.sh --reuse` and its message) | the review starts only on a recorded pass | the recorded targeted run | the same change types |
| `scripts/apply-triage.sh` (`./scripts/verify.sh --reuse`) | the result of a triage is verified by a recorded pass | the recorded targeted run | the same change types |
| `scripts/triage-review.sh` (the text of every follow-up Issue: "`./scripts/verify.sh` passes") | an acceptance criterion of the generated Issue | the targeted run | the same change types |
| `scripts/run-feature.sh` (a second `./scripts/verify.sh` after a failure, to tell failures that repeat from failures that do not) | a full repeat of a failing run | the failing checks again, alone | none |
| `docs/development.md`, "Verification": "This one command reproduces the whole site" and the preview of the site with `quarto preview site` | read the site, and verify everything, from a local build | the targeted run; the page render of a changed lesson; no preview in a maintained guide (ADR 016) | a full run for the shared-input change types; `./scripts/verify.sh --base` for the path and header fields and for a new lesson |
| `docs/development.md` (the recorded verification, the finish, review, and triage steps, the template sync that runs `./scripts/verify.sh --all`) | the descriptions of the same gates | the same replacements | the same |
| `docs/authoring.md`, "Check it" (`quarto preview site` to read the page while writing, then `./scripts/verify.sh # everything, before a pull request`) and step 5 of recording an agent lesson | the whole run before a pull request | the targeted run, with the single-page render of the page in progress | the same change types |
| `docs/authoring.md`, the Lean section: `./scripts/check-lean.sh` before a render | a Lean build for a Lean change | already a targeted check; keep | a change to a Lean module a lesson displays: the selection executes the lessons that display it |
| `docs/workflow.md` (the table of steps with a `verify.sh` column and its description) | which step runs the checks | the same replacements | the same |
| `.agents/plans/` (19 of 40 plans end with a `./scripts/verify.sh` step or its evidence line; 4 plans, 7, 15, 18, and 21, demand a `quarto render` of each new page) | a plan's last step is a full run, and a new page is rendered | the targeted run; the single-page render of a new page is the targeted check | a new lesson page: a single-page render, not a build of the site |
| Skills | none: the repository holds no project skill (`.claude` has none) | none | none |
| `.agents/prompts/planner.md`, `reviewer.md`, the policies | no demand to run everything | none | none |

CI stays the publication gate in every row: it builds and checks the site of
every pull request and push, whatever the agent ran locally.

## Proposal for the owner

**Decided by the owner on 2026-10-15** (pull request #184, ADR 014 status): a
timeout of 60 minutes for the job `build`, approved for up to 45 lessons.
Extended by the owner on 2026-10-21 (ADR 014 status, Issue #253) to 64
lessons with the same 60 minutes, as a planning boundary re-measured at 55
lessons and decided again by 60 at the latest, or earlier if the `build` job
approaches 55 minutes, repeated runs show too little margin, or verification
failures point to a capacity problem (the amendment note in the status of
ADR 014 records the decision).

For the unresolved question 10 of the requirements and the full-run gate of
Phase 4 (`docs/roadmap.md`, "The full run on `main` at the current lesson
count"), as the fallback that ADR 014 decision 11 requires while F113 is
paused and ADR 017 is not accepted. The numbers are the measurements of
`docs/release-readiness.md`; the projections are labelled there.

**Proposal: a timeout of 60 minutes for the one `build` job of a full run,
approved for up to 45 lessons.**

- **Growth per lesson:** 32 to 46 s of marginal cost per lesson in the
  group `build` (the fits of the fast and the slow runner class), and 36 to 60
  s per lesson of the whole group (the measured ratio, which includes a
  fixed part of 1.8 to 4.4 minutes); no growth of the cost per lesson was
  seen from 22 to 32 lessons. The spread between runners (1.7 fold) is larger
  than any trend.
- **Job time at the bounds** (prepare 126 s, the slowest measured, plus the
  lessons): 45 lessons take 29 to 47 minutes; 47 lessons take 30 to 49 minutes.
  The planning budget of ADR 014 decision 7 keeps 10 minutes between the
  budget and the timeout, so 50 minutes of planning budget under a 60-minute
  timeout hold 47 lessons at the slow bound; 45 leaves two lessons of slack.
- **Today (32 lessons) the 45-minute timeout is not the limit**: the slow
  bound is 34 minutes, the slowest measured job 31 min 15 s. The 35-minute
  planning budget holds 32 to 33 lessons, so the gate of 32 is the largest
  count that this budget supports; the timeout of 45 minutes holds 40 at the
  slow bound with 3 minutes of margin.
- **Options for the owner**

  | Option | `build` timeout | Planning budget | Lessons at the slow bound | Lessons at the fast bound |
  |---|---|---|---|---|
  | Keep the gate | 45 min | 35 min | 32 to 33 | about 54 |
  | **Proposed** | **60 min** | **50 min** | **47** | **about 79** |
  | Wider | 75 min | 65 min | 62 | about 104 |

  The fast-bound column is an upper reading, not a plan. Removing the third
  build (F119, after its regression test) would take about a fifth off the
  cost per lesson and move the proposed row to about 59 at the slow bound;
  that is a projection and nothing here depends on it.
- **What it costs in wall clock:** the run of a push to `main` at 45 lessons on
  the slow bound is about 47 minutes of `build`, 7.5 minutes of the slowest
  `e2e` job, and the deploy: about 57 minutes. A pull request with a base is
  not affected (13 min 50 s to 14 min 43 s at 22 lessons, 4 s more per
  unchanged lesson).
- **What the owner decides:** the timeout value and the lesson count the
  gate allows until ADR 017 is accepted and F121 delivered, or F113 is
  resumed. The decision is recorded as a status line of ADR 014 (an ADR
  change needs the owner's approval at the merge) and restates the full-run
  gate of Phase 4 for the lesson features. F118 changes neither the timeout,
  nor ADR 014, nor the roadmap's gate. The proposal is posted on Issue #180.
