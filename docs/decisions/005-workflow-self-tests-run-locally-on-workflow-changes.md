# ADR 005: Workflow self-tests run locally only when workflow files change

## Status

Accepted by the project owner with the merge of the pull request that adds
this ADR. Amends decisions 1, 2, and 7 of
[ADR 003](003-single-verification-entry-point-and-ci-budget.md).

This ADR was not part of a planning review round. The planning approval was
updated by hand for it; `docs/PLANNING_APPROVAL.md` records that.

Decision 2 is superseded by
[ADR 012](012-parallel-verification-jobs-behind-one-required-check.md), as
far as it says that verification is one job: every job calls
`./scripts/verify.sh --all`, no check is skipped in CI, and no path filter
is added.

Decision 4 was rewritten on 2026-10-07. It first listed the guarded files and
guarded `scripts/` as a whole, which made `scripts/verify.conf` a guarded
file: nearly every feature adds a check there, so the self-tests still ran in
most local runs.

[ADR 017](017-incremental-main-from-a-chain-of-verified-bases.md)
decision 7, proposed by the change cycle
`pbc-planning-change-four-workstreams` and **accepted by the owner on
2026-10-15 on F118's evidence, applied by F119 (Issue #185), amends
decision 3 and the restatement of ADR 003 decision 1 in decision 5**: for
an ordinary change, the finish and review evidence of the agent workflow
is a recorded targeted run (`./scripts/verify.sh --targeted`) that
performs the checks that need no site build and the single-page render of
the selected lessons, recorded with its tier, base, and selection; a run
without options still runs every product check locally and is the only
verification of the content; CI runs every check on every pull request
and push. The workflow self-tests keep the rule of decision 1 in every
tier: they run when a workflow file changed, and always in CI.

[ADR 020](020-risk-proportionate-verification-and-review.md) (2026-10-19, change cycle
`risk-proportionate-workflow`, requirements decision 39) amends decision
3 in one respect beyond ADR 017 decision 7: an intermediate fix
round of a Level 3 change (ADR 020 decision 1) may run
`./scripts/verify.sh --only <group>` for the groups its paths touch as
quick feedback, which verifies nothing and records nothing (ADR 012
decision 1 stands), and the final acceptance of such a change is always a
complete verification of the final tree, a full independent review made
after it, and the full CI. Decision 3's rule for the workflow self-tests
(run when a guarded file changed, always in CI) is unchanged. Decisions
4 and 5 were reviewed with it, as the change request's section 5 asked,
and stand unamended: decision 4 (the guarded files) is untouched by a
run with `--only`, and decision 5's restatement of ADR 003 decision 1
was already amended by ADR 017 decision 7, to which ADR 020 decision 5
adds nothing; its restatement of ADR 003 decision 6 is unchanged.

Date: 2026-10-06

## Context

ADR 003 keeps the workflow self-tests (`tests/*-test.sh`) in
`scripts/verify.conf`, so every local `./scripts/verify.sh` runs them.

These tests check the scripts of the agentic development workflow in
`scripts/`, their agent contracts, and their schemas. They build temporary Git
repositories with fake agents and start `bash`, `git`, and `jq` thousands of
times. They do not check a lesson, the Python package, a proof, or the site,
and a feature can make them fail only by changing a workflow file.

F01 measured the cost. A full local verification run took about 20 minutes on
the owner's machine, of which more than 15 were the workflow self-tests. In CI
the same self-tests take about one minute. The product checks, which the
requirements name (lint and format, lesson code with tests, the Lean build,
the site build), took about two minutes locally.

A local run of that length is run less often, which weakens the checks that
do guard the product.

## Decision

1. **The workflow self-tests move to their own file**,
   `scripts/verify-workflow.conf`, which also lists the workflow files they
   guard. They still run only through `./scripts/verify.sh`; no check is
   declared in workflow YAML.
2. **CI runs everything.** The verify job calls `./scripts/verify.sh --all`
   on every pull request and every push to `main`. It stays one job and the
   one required status check, with no path filters, so no check is ever
   skipped in CI.
3. **Locally, the product checks always run.** `./scripts/verify.sh` runs
   every check in `scripts/verify.conf`. It runs the workflow self-tests when
   a guarded file differs from `origin/main` (or `main`), counting uncommitted
   and untracked files, when it cannot determine that, and with `--all`.
   Otherwise the summary reports them as skipped.
4. **Guarded files** are listed in `scripts/verify-workflow.conf`. The list
   covers every file a workflow self-test reads or copies: the workflow
   scripts, their agent contracts and schemas, the agent configuration, the
   ignore rules, and the tests themselves. A file that no self-test reads may
   be excluded there without a new ADR; a new file under `scripts/` is guarded
   until it is excluded. A test of a project script belongs with the product
   checks in `scripts/verify.conf`, not with the workflow self-tests.
5. **ADR 003 stays in force otherwise.** Its decision 1 now reads: no check
   exists only in CI, and every product check runs locally on every run. Its
   decision 7 now reads: the workflow self-tests stay while the workflow
   scripts remain in the repository, in their own file. Its decision 6 is
   unchanged: dropping a product check, filtering one by path, or moving one
   to a schedule requires a new ADR.

## Alternatives considered

**Keep every local run complete (ADR 003 unchanged).** Rejected: more than 15
minutes per run for tests that a lesson or site change cannot affect.

**Remove the workflow self-tests from the project.** Rejected: the project
edits the workflow scripts itself. F01 changed `scripts/doctor.sh` and added
`scripts/preflight.sh`, both covered by these tests.

**Run the workflow self-tests only in CI.** Rejected: a change to a workflow
script would then first be tested after a push.

**Also skip them in CI when no workflow file changed.** Rejected: they cost
about a minute there, and the reasons of ADR 003 against path filters in CI
still hold.

## Consequences

Positive:

- A local run for a lesson or site change takes minutes instead of about 20.
- CI is unchanged in what it checks: every pull request runs every check.
- For a change that touches no guarded file, "passes locally" and "passes in
  CI" still mean the same, because the inputs of the skipped tests are those
  of `main`, where CI ran them.

Negative, with mitigations:

- A local pass no longer always includes the workflow self-tests. The summary
  says so on every run that skips them, and `--all` runs them.
- The skip relies on the list of guarded files being complete. A file missing
  from the list is caught by CI, not locally.
- The comparison uses the local `origin/main`. When it is out of date, more
  files differ and the self-tests run more often, never less.
