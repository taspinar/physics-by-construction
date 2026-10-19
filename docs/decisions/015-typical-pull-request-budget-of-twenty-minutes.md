# ADR 015: The budget of a typical pull request is 20 minutes

## Status

Accepted: the decision of the project owner of 2026-10-14 (requirements
decision 34; `docs/changes/pbc-planning-change-four-workstreams.md`,
change 3), recorded with the planning of that change cycle. Amends the
typical-pull-request row of
[ADR 003](003-single-verification-entry-point-and-ci-budget.md) decision
5, the restatement of that budget in
[ADR 012](012-parallel-verification-jobs-behind-one-required-check.md)
decision 8, and
[ADR 014](014-verification-proportional-to-the-change.md) decision 7.
Every other row and decision of those records stands; their older wording
is history.

Amended in one respect by [ADR 020](020-risk-proportionate-verification-and-review.md) (2026-10-19, change
cycle `risk-proportionate-workflow`, requirements decision 39): decision
4's "nothing else changes" stands, and a run above the 20 minutes is
recorded as a measurement and decided by the owner at the re-assessment
points ADR 020 decision 6 names, never as a mandate to optimise; the
"45-minute timeout per job" it names has been 60 minutes for the one
`build` job of a full run since the owner's interim gate of the same day
(ADR 014, status), 45 for every other job.

Date: 2026-10-15

## Context

ADR 003 set the budget of a typical pull request with warm caches at 12
minutes, ADR 012 made it the wall clock of a run in parallel jobs, and ADR
014 made it the acceptance criterion of F61, the feature that makes a pull
request pay only for what it changed.

F61 was measured on 2026-10-14 (`docs/release-readiness.md`, "Selection
against a base (F61)"), with twenty-two lessons, on three pull requests
that each change one lesson:

| Measure | Measured |
|---|---|
| One-lesson pull request with an accepted base, wall clock | 13 min 50 s, 14 min 01 s, 14 min 43 s |
| The same without a base (F58, before F61) | 22 min 56 s and 25 min 00 s |
| Longest path | `build` then the slowest `e2e` job (about 7.5 plus 6 minutes), or `integration` alone (10 min 48 s to 14 min 29 s) |

What the selection removed is the execution of the unchanged lessons.
What remains is fixed cost: every job prepares its own runner (about
100 s, in each of eight jobs), the Lean build runs in full, and the checks
that are not per lesson (`integration`, `workflow`, the built-site checks
of `e2e-other`) run as before. The measurement record proposed four
corrective actions, none applied: split `integration`, run the
lesson-independent built-site checks beside `build`, cut the preparation
of a runner, or accept a larger budget.

The owner accepts a budget of 20 minutes instead of paying for further
workflow changes now, keeps 15 minutes as a target, and asks that both the
duration and whether the target was met be recorded.

## Decision

1. **The budget of a typical pull request with warm caches is 20 minutes
   wall clock**, from the creation of the run to its end, in place of the
   12 minutes of ADR 003 decision 5, ADR 012 decision 8, and ADR 014
   decision 7. A typical pull request changes one lesson and runs with an
   accepted base (ADR 014).
2. **15 minutes is a non-blocking optimisation target.** A run above 15
   minutes and within 20 meets the budget. Every measurement of this
   budget records the actual duration and whether the target was met.
3. **The acceptance criterion of F61** (Issue #147, criterion 1) reads:
   three consecutive pull requests that each change one lesson finish
   within 20 minutes wall clock, recorded in the pull request and in
   `docs/release-readiness.md`, each with its duration and whether the
   15-minute target was met.
4. **Nothing else changes.** The 25-minute budget for cold caches, the
   45-minute timeout per job (ADR 012 decision 9), the per-check budgets
   of ADR 003, the checks, and the guarantees are untouched by this
   decision. The measurements of F61 stay exactly as recorded. The two
   cases F61 did not measure stay outstanding and are not claimed: the
   retrieval of the base by a pull request from a fork, and the full run
   at 110 lessons.
5. **No expiry.** The 20 minutes are the accepted budget until a later
   explicit decision changes it. The fixed costs stay eligible for later
   optimisation (the audit of F118 and the removals of F119 under
   requirements decision 35); a later owner decision may lower the budget
   again.

## Alternatives considered

- **Keep 12 minutes and apply the corrective actions now.** Rejected by
  the owner for now: the gain of each action is unmeasured, and each is a
  workflow change with its own review. They stay available under
  decision 5.
- **15 minutes as the budget** (the fourth corrective action proposed on
  2026-10-14). Rejected: the measured runs leave 17 seconds to 70 seconds
  under it, and the `integration` job alone varied by 3 min 41 s between
  runs that started three seconds apart, so the criterion would fail on
  runner variance rather than on a change. 15 minutes is kept as the
  target that keeps the fixed cost visible.
- **A measured time without a budget.** Rejected: the requirements demand
  a concrete budget ("CI cost and time").

## Consequences

- F61 criterion 1 is judged against 20 minutes. The three measured pull
  requests ran at the same time on separate runners, not consecutively,
  so the record of three consecutive runs is still owed; the Issue of
  F61 decides how it is produced.
- Every current statement of this budget in the requirements, the
  roadmap, and the architecture says 20 minutes; ADR 003, ADR 012, and ADR
  014 keep their wording and name this record in their status.
- Growth of the fixed cost (another job, a heavier integration test, a
  slower preparation) consumes the 5 minutes between the target and the
  budget before it fails a run; the recorded target keeps that growth
  visible.
