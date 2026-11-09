# Plan: independent groups of verify.sh run at the same time (Issue #430)

Source: Issue #430, change D of the plan of #389
(`.agents/plans/389-level-3-pipeline-one-verification.md`, "Question 3"),
and the owner's "start" of 2026-11-08. Reusing a passed group (#385) is not
part of it.

Skills: none (no visual deliverable: a shell script, its configuration, its
tests, and documentation).

Level 3: `scripts/verify.sh` and `scripts/verify.conf` are protected paths,
and the change touches a verification guarantee (the order in which the
checks run). The owner approves the exact commit.

## What changes

1. `scripts/verify.sh` runs every group of a run that has more than one group
   in the background, each group's checks in the order of the file, at most
   `VERIFY_JOBS` groups at a time (default 4). A group waits for a check of
   another group only where the reserved entry
   `after [<group>]: <check>[,<check>...]` of `scripts/verify.conf` says so;
   it starts when those checks have finished, passed or failed, as one after
   the other. A prerequisite in a group outside the run (`--only`) is not
   waited for. The entries are checked: a known group, checks of
   `scripts/verify.conf` in other groups, no circle.
2. One log per group, `.agents/verification/logs/<group>.log` (Git ignores
   it; a temporary directory where it would not and the run records its
   pass). The summary lists the outcomes in the order of the file, so it is
   the same as one after the other; the record, the time log, and the exit
   status are unchanged. INT or TERM stops the running groups and their
   processes.
3. `VERIFY_JOBS=1`, or a run with one group (each CI job's `--only
   <group>`), is the old loop, unchanged, streaming its output. CI is
   unchanged.
4. `tests/support/verify_conf.py` leaves out the entries `after`, as it does
   `targeted`, so that the Python tests that read the checks see the same
   checks.

## The dependency graph, checked against the scripts and tests

The Issue's graph was `code`, `default`, `integration-quarto`,
`integration-browser`, `lean-build` first; `integration-other` and
`site-build` after `lean-build`; the rest of `build` and the `e2e` groups
after `site-build`. Read against the files, three groups read `site/` while
`site-build` writes into it (the pages next to their sources,
`*.quarto_ipynb`, the `*_files` directories, `site_libs`, `_freeze`, then
`_site`), so they also wait for `site-build`:

- `code`: `tests/unit/test_introductions.py` copies `site/` with
  `shutil.copytree`; a file the render moves away during the copy fails it.
- `integration-browser`: `tests/integration/test_lesson_template.py` copies
  `site/`, its `_freeze` included, and builds the copy.
- `integration-other`: `tests/integration/test_agent_replay.py` and
  `test_review_replay.py` list the files of a lesson directory and fail on a
  render's working file; `tests/integration/test_lean_check.py` links the
  packages of `lean/.lake` (after `lean-build`, as the Issue says).

`default` (the datasets, the documentation through `git ls-files`, the
skills, the workflow self-tests in their own temporary repositories) and
`integration-quarto` (fixture sites under the temporary directory; only
tracked sources copied from `site/`) read nothing that `lean-build` or
`site-build` writes, and run beside the whole chain. `determinism` builds a
copy of `site/` under the temporary directory, and the reproduction clones
each lesson there, so the groups after `site-build` run beside them. No
check uses a fixed port. The chain of `build` stays the critical path; the
groups moved behind `site-build` (about 27 minutes together, measured in
#389) fit beside the determinism build and the reproduction (about 55).

## Measurements

Before, on this machine (ten cores, 32 GB), from the time log
(`<git common dir>/verify-time.log`): the eleven full runs that passed on
2026-11-07 and 2026-11-08 took 4467, 7177, 7200, 7217, 7512, 7574, 7585,
7947, 8588, 8684 and 9177 seconds, median 7574 s (126 min). The time log
does not record what else ran; on those days other sessions ran their own
verifications beside them (at 17:37 UTC on 2026-11-08, while this feature
was implemented, a full `./scripts/verify.sh --reuse` of another worktree
was running, load average about 5.8), so these are not idle-machine times.

After: not measured in the implementation session. The session was told
not to run the full `./scripts/verify.sh`, and another full verification
was running at the time. The first full run of this tree, which the
pipeline makes after the session, appends its line to the time log. An
edit of this file after that run would change the verified tree, so the
time after is entered here in a later change, after the merge, with what
else ran at the time; only a run on an idle machine is presented as the
saving. The estimate of #389 was 60 to 65
minutes alone, against 97.

## Tests

`tests/verify-test.sh`: the same checks and the same summary as one after
the other, the order inside a group; a failure in one group of a parallel
wave fails the run, the other groups run, and every log remains; the groups
really run at the same time (two checks that each wait for the other's
start, which fail with `VERIFY_JOBS=1`); a group that waits for a check
starts after it and not after its whole group, and starts at once without
the entry; a prerequisite outside the run is not waited for, and a failed
one still lets the dependent group run; `VERIFY_JOBS` limits the groups at
the same time and is validated; malformed entries `after` are rejected; a
TERM stops the running checks; a parallel run is recorded and reused like
one after the other; a group process killed with SIGKILL (its check kills
it, so no end marker is written) ends the run within a time limit, fails it,
names the group and the signal, and its dependent group never starts (fix of
2026-11-09, outside review of PR #431: the scheduler waited for the marker
alone and hung). The check finds the group process by walking up from
itself to the process whose parent is `verify.sh` (fix of 2026-11-09: CI's
bash 5 runs the check's shell in place of the subshell of `run_checks`, so
the grandparent the first version killed was `verify.sh` itself). No
self-test in `tests/` pipes into `grep -q` (fix of 2026-11-09, the owner's
finding on the full run at 1edc314: under the load of groups at the same
time the writer of such a pipe died of SIGPIPE when grep ended at its first
match, and risk-level, risk-workflow and merge-feature failed although
their assertions held); the guard and its own cases are in
`tests/verify-test.sh`. The existing tests of the selection and the tiers
run with `VERIFY_JOBS=1`, where the order of the file is still asserted.

## Steps

1. Done: the scheduler, the entries, the Python reader, the tests, the
   documentation (`docs/development.md`, "Groups at the same time").
   Fix of 2026-11-09: the scheduler checks with `kill -0` whether a running
   group's process still exists; one that is gone without its end marker is
   a failed group (its status from `wait`, the signal named), and a group
   that waits for one of its unfinished checks, directly or through another
   such group, is not started.
   Fix of 2026-11-09 (full run at 1edc314): the killed-group test walks up
   to the group process (bash 5 and 3.2); the 116 pipes into `grep -q` of
   the self-tests read to the end (`grep ... >/dev/null`), with a guard.
   The same pipe in the workflow scripts (`scripts/merge-feature.sh` and
   others, protected) is outside this Issue: a question to the owner.
2. After the session: the full `./scripts/verify.sh`, run last by the
   pipeline.
3. After the merge: a full run on an idle machine, its time and what else
   ran entered under "Measurements".

**Follow-up (owner, 2026-11-09):** the protected scripts with the same pipe pattern are repaired in #452, not in this Issue.
