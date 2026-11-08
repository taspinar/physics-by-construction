# Plan: Level 3 pipeline, one complete verification on the final tree, parallel verification groups, and a duration record per step (Issue #389)

Source: Issue #389 and its two comments of 2026-11-06, ADR 020 decisions 4,
5, 7 and 10, ADR 012 decision 1, ADR 017 decision 7, `docs/development.md`
("Verification"), the pipeline scripts, and the records of the runs of
#372, #375, #383 and #388 on 2026-11-04 to 06.

Skills: none (no visual deliverable: measurements, a decision table, and
script changes).

Status: **the owner decided on 2026-11-07** (comment on the Issue): changes
A, B, C, E, F and G go in this Issue as one Level 3 feature, in the order B,
A, C, F, E, G; D is a feature of its own after this one is merged (ADR 020
decision 10). **Implemented in the session of 2026-11-07**; see "What the
implementation found" and the implementation steps below. The measurements
of the findings are read from the artifacts that exist (the time log of
`./scripts/verify.sh`, the review and triage records, the run logs, the CI
jobs); no new run was made for them, because the machine ran two heavy
verifications of other features during the research session, which the
owner's rule of at most two at a time does not allow to add to.

## Goal

Answer the four questions of the Issue with measurements and file
references, and name the changes with their expected saving and their
level, so that the owner can decide which of them the pipeline gets.

## Acceptance criteria and their gates

1. The four questions are answered with measurements and file references
   (gate `implementation`: this plan, "Findings").
2. A plan names the changes with their expected saving and their level
   (gate `implementation`: this plan, "Changes for the owner's decision").
3. After the owner's decision: the pipeline completes a Level 3 feature with
   one complete verification of the final tree and no complete verification
   in intermediate rounds, and the duration of every step is recorded
   (gate `implementation`, after the decision; `owner_approval` for the
   merge, because every file it touches is a protected path).

## Findings

### Question 1: where a verified tree is required, and what `--unverified` does

The pipeline is `scripts/run-feature.sh`; the review gate is
`scripts/review-feature.sh`; the commit gate is `scripts/finish-feature.sh`.

- **Round 1 of a Level 3 change always runs the complete verification.**
  `run-feature.sh` adds `--feedback` only when a previous review exists
  (the round loop, `review_options`, the test `[[ -n "$review" ...` before
  `review_options+=(--feedback)`). Without it, `review-feature.sh` runs
  `./scripts/verify.sh --reuse` for a Level 3 change (its branch "The
  change is Level 3: checking that the full verification passes"), which is
  the full run unless a full pass is recorded for exactly this tree. The
  three runs show it: #372 round 1, 9569 s; #383 round 1, 11 481 s; #388
  round 1, 10 071 s (the table under question 2).
- **A clean intermediate round is followed by a complete round.** When a
  review has no findings, or its triage leaves nothing to fix,
  `run-feature.sh` ends the loop only if `final_for_level3` holds (the
  review's `verification.status` is `passed` with `tier` `full`, and the
  review is not of changes only); otherwise it sets `complete_review=1`,
  and the next round is reviewed without `--feedback`, on the full run.
  When that complete round finds a major, the fix is followed by a feedback
  round, and when that is clean, by another complete round. The cost is
  therefore one full run for round 1, one for the final round, and one more
  for every major that a complete round finds: #372 ran the full
  verification five times (rounds 1, 5, 6, 7, and a failed attempt before
  round 5).
- **`--unverified` and `--feedback` reviews count as rounds and are never
  final.** `review-feature.sh` numbers every review it stores, whatever its
  verification state; `run-feature.sh` reads the `.round` of the latest
  review against `MAX_ROUNDS=5`. `finish-feature.sh` refuses the commit of a
  Level 3 change unless the recorded pass has the tier `full` and the latest
  review's `verification.tier` is `full` (its messages "a Level 3 change
  needs a full verification of its final tree" and "was not made on a fully
  verified tree"). A review with `--unverified` (status `not-verified`) or
  `--feedback` (status `feedback`) therefore uses up a round and still
  needs a complete round after it; the five-round limit is reached one
  round earlier for each of them.
- **The reviewer is not told the verification state of the round.** The
  context that `review-feature.sh` writes for the reviewer (its Issue,
  diff, completion record, risk statement) says nothing about the tier;
  only the console line `Verified: ...` does. `.agents/prompts/reviewer.md`
  does not mention feedback rounds. The reviewer reads the completion record
  and the handoff note, finds "the full run did not finish", and reports it
  as a major (#375 R04-M1 and R05-M1), which no fix session can repair in a
  feedback round. The Markdown report (`scripts/lib/review-data.sh`,
  `review_render_markdown`) renders a feedback round as "Verification: NOT
  verified (null)", which is what the owner sees on the Issue (#375, round
  4).
- **A failed verification is repeated with the wrong tier, and the repeat
  is always refused at Level 3.** `repair_verification` in
  `run-feature.sh` repeats a failed verification with
  `./scripts/verify.sh --targeted`, whatever tier the step ran. A Level 3
  change that alters the checks (every one of #372, #383 and #388 did: the
  selection says "the checks changed since the base (identity differs)")
  is refused by the targeted run in about 45 s, and the refusal is counted
  as the failing check `targeted-run`. The first run's failures (a feedback
  run, or the full run) and the second run's (`targeted-run`) never
  coincide, so every failure is classified "unstable, failed in one of two
  runs", and after `MAX_UNSTABLE=3` the run stops. Both long runs stopped
  this way, not at the five-round limit: #372 at 02:13 UTC on 11-06
  ("checks failed in one verification run and not in the next, for the 4.
  time: check-tests-other site-checks-reproduction targeted-run"), #383 at
  05:15 UTC. Each stop cost a manual restart and a gap of 7 to 12 hours
  (#372 rounds 4 to 5: 455 min; #383 rounds 3 to 4: 737 min).

### Question 2: how long each step takes

**Verification runs**, from the time log of `./scripts/verify.sh` (ADR 020
decision 7; 467 runs since 2026-10-19 on this machine, read with the
concurrency of other heavy runs derived from the end times and durations):

| Tier | Passed runs | Median | Min | Max |
|---|---|---|---|---|
| full, since 10-28 (94 lessons) | 49 | 7200 s (120 min) | 6439 s (107 min) | 11 519 s (192 min) |
| full, no other heavy run at the time | 45 | 5841 s (97 min) | | |
| full, one other heavy run | 30 | 6216 s (104 min) | | |
| full, two others | 30 | 6715 s (112 min) | | |
| full, three others | 8 | 7199 s (120 min) | | |
| full, four others | 4 | 7765 s (129 min) | | |
| full, eight or nine others | 3 | about 11 400 s (190 min) | | |
| `--base` | 46 | 3908 s (65 min) | | |
| feedback, `--only default,code,integration-other` | 40 | 1586 s (26 min) | 892 s (15 min) | 3760 s (63 min) |
| `--targeted` | 9 | 547 s (9 min) | | |
| `--targeted`, refused | 49 | 47 s | 24 s | 129 s |

Two readings of the log. Thirteen runs of exactly 7199 or 7200 s are
recorded as `passed` (2026-10-23 to 11-06, six of them on 11-04): that is
the two-hour limit of a background command of the agent's shell, which
kills the run; the exit trap of `verify.sh` then logs the status of the
last command, not the kill, and no pass record is written, so no gate is
affected, but the log overstates the passes and the median of the full run.
And in the window the Issue names, 2026-11-04 09:00 to 11-06 21:30 UTC,
the machine ran 37 full or `--base` attempts (100 machine hours; 26 passed,
11 failed) and 38 feedback runs (25 hours; 30 passed), most of them with two
to four heavy runs at once, which is where the 2 h 13 to 3 h 11 per full run
of the Issue comes from (97 min alone).

**Per step of the three pipeline runs**, read from `verification.ran_at`
or `verified_at` and `created_at` of the review records, `approved_at` of
the triage records, the time log, and `.agents/run/<issue>-log` (a line is
written there only for an exceptional outcome: a stop, a retry, an
unstable check). "Next" is the time from the triage to the start of the
next round's run, which holds the fix session and the waits of the queue.

| Issue, round | Verification | Run | Review | Triage | Next |
|---|---|---|---|---|---|
| #372 r1 | full, 3 others at once | 159 min | 6.2 min | 12 s | 36 min |
| #372 r2 | feedback | 26 min | 0.7 min | 10 s | 97 min (two misclassified repeats) |
| #372 r3 | feedback | 28 min | 0.7 min | 14 s | 32 min |
| #372 r4 | feedback, clean | 30 min | 0.7 min | | 455 min (two failed full attempts, 196 and 165 min; the stop at 02:13; manual restart) |
| #372 r5 | full | 139 min | 1.8 min | 21 s | 143 min |
| #372 r6 | full | 141 min | 1.0 min | | 16 min |
| #372 r7 | full | 133 min | 0.6 min | 18 s | (record changes only after the owner's scope decision) |
| #372 r8, r9 | full, reused | 0 | about 1 min | 20 s | |
| #383 r1 | full, 9 others at once | 191 min | 0.8 min | 21 s | 66 min |
| #383 r2, r3 | feedback | 56 min each | 0.8 min | 12 s | 121 min; then the stop at 05:15, 737 min |
| #383 r4, r5, r6 | feedback | 42, 39, 39 min | 0.7 min | 20 s | 43, 57 min; r6 clean, the complete round still to run at 21:30 |
| #388 r1 | full, 4 others | 168 min | 1.0 min | 16 s | 21 min |
| #388 r2 | feedback | 18 min | 0.8 min | 11 s | 21 min |
| #388 r3 | feedback, clean | 19 min | 0.7 min | | 0 min |
| #388 r4 | full | 127 min | 0.7 min | | commit refused (no approval request) |

What the table shows: a review takes about one minute (6 min for the first
of #372), a triage 10 to 21 s, a fix session with its queue wait 16 to 57
min, and the verification 86 to 98 percent of a round. #388, the shortest
Level 3 run, took 6 h 16 from its first run to its clean complete review,
of which 5 h 31 was verification. The implementation step has no start
time in any record (the session's final message
`.agents/run/<issue>-implementer.md` has only an end time). One more
reading: the #372 run spent three implementer sessions of about 20 s each
(19:10:12 to 19:11:18 UTC on 11-05) and stopped, because the handoff note
listed the pending criteria under "Remaining", which the completion gate
reads as work left; that is the handoff format of
`.agents/prompts/implementer.md`, not a script defect.

**CI, for comparison** (the four runs on `main` of 2026-11-05 and 06,
jobs on separate runners):

| Job | Duration |
|---|---|
| `code` | 6.5 to 12 min |
| `workflow` (group `default`) | 5.5 to 7.5 min |
| `integration-quarto` | 5 to 6 min |
| `integration-browser` | 5 to 11 min |
| `integration-other` | 7 to 15 min |
| `build` | 46 to 73 min |
| `e2e` pages-1, pages-2, other | 10 to 17, 10 to 23, 13 to 15 min |
| whole run (build, then the slowest e2e) | 64 to 108 min |

### Question 3: sequential groups, and the saving of parallel groups

**Sequential.** `scripts/verify.sh` runs its checks one after the other
in one loop (`for index in "${!names[@]}"`), in the order of
`scripts/verify.conf`; `--only` selects groups but runs them in the same
loop. CI runs the groups as parallel jobs (`.github/workflows/ci.yml`:
`code`, `workflow`, `integration-quarto`, `integration-browser`,
`integration-other` and `build` start together; `e2e` needs `build`).

**Per check, locally**, from the output of the final full run of #388
(11-06 11:25 to 13:32 UTC, 7621 s, two other heavy runs at the time; the
pytest summaries and `site/_timings.json` of that run):

| Check (group) | Duration |
|---|---|
| unit-tests (code) | 381 s |
| lesson-checks, starters, lint, format (code) | 46 s, 3 s, and about a minute together |
| lesson-pages (code) | 0 (nothing to do in a full run) |
| check-tests-quarto (integration-quarto) | 384 s |
| check-tests-browser (integration-browser) | 289 s |
| check-tests-other (integration-other) | 645 s |
| site-build (build) | one build executes 104 pages in 954 s; with Quarto's own time about 15 min |
| determinism (build) | a second build, about the same |
| site-checks-reproduction (build) | 2428 s (188 reproductions, one clone after the other) |
| lean-build (build) | a few minutes with the Mathlib cache (not printed) |
| site-checks-pages-1, pages-2 (e2e) | 463 s, 363 s |
| site-checks-other (e2e) | 616 s |
| default (preflight, datasets, docs, skills; the workflow self-tests when a workflow file changed) | about 3 min, about 7 with the self-tests |

By group: `build` about 72 min (57 percent of the run), `e2e` 24 min,
the three `integration` groups 22 min, `code` 8 min, `default` 3 to 7 min.

**What the groups share**, read from the scripts and tests: `site/_site`,
`site/.quarto`, `site/_freeze`, `site/_digests.json`, `site/_pages.json`
and `site/_timings.json` are written by `site-build` only; `determinism`
builds a copy under the temporary directory; the `e2e` checks and the
reproduction read `site/_site`. `lean/.lake` is written by `lean-build`;
`tests/integration/test_lean_check.py` links its `packages` read-only and
needs the Lean build first, as the comment in `scripts/verify.conf` says.
`check-tests-quarto` builds fixture sites under the temporary directory;
`check-tests-browser` and the `e2e` checks open the pinned browser on local
files, with no fixed port; the reproduction makes one clone per lesson under
the temporary directory and runs `uv sync` there (the `uv` cache takes its
own lock). `.agents/verification/selection.json` is written once before the
checks. So the dependencies are: `integration-other` and `site-build` after
`lean-build`; `determinism`, `site-checks-reproduction` and the three `e2e`
groups after `site-build`; `code`, `default`, `integration-quarto` and
`integration-browser` free.

**Estimate** (no idle-machine run was possible in this session; the
estimate is the critical path of the dependencies above with the local
durations): the chain inside `build` (Lean, build, determinism,
reproduction) is the critical path, about 70 min under the load of the
measured run; everything else (57 min) fits beside it, the `e2e` groups
after the first build beside the determinism build and the reproduction.
A parallel run would take about 70 to 75 min instead of 127 under that
load (a saving of 40 percent), and about 60 to 65 instead of 97 alone.
What limits it: the chain itself, above all the reproduction (40 min,
lesson by lesson); CPU, which stays within the ten cores (Quarto renders one
page at a time, the chain uses one to two cores, the free groups four to
five more); memory (32 GB; a page render or a browser is under 1 GB); the
output, which needs one log per group and a summary instead of one stream;
and the owner's rule of two heavy runs at a time, which would have to count
cores instead of runs. Not measured: the idle-machine durations of each
group and of the parallel run, which the first run after the change gives
(the time log and the per-step record below).

### Question 4: which Level 3 findings can be deferred or accepted

The 21 major findings of the four features, from their review records:

| Kind | Findings | What they cost |
|---|---|---|
| The approval request's `Tree:` line is stale after a fix session | #372 R01-M2, R03-M1, R09-M1; #383 R02-M1, R04-M2 | one round each; `finish-feature.sh` refuses a stale tree anyway |
| The completion record misses a trigger the script detected, or marks a later-gate criterion met | #372 R08-M1; #383 R02-M2, R03-M2; #388 R01-M2, R02-M1; #375 R03-M2 | one round each; #372 R08 and R09 on a reused full run, the others on a feedback run |
| The full verification is missing in a feedback round | #375 R04-M1, R05-M1 | two rounds that no fix session could repair |
| A further instance of a class already fixed | #372 R05-M1, R06-M1, R07-M1 (number words of the count validator, one more per round); #383 R03-M1, R04-M1, R05-M1 (one more "30 seconds" sentence per round, in four documents) | three full runs for #372 (about 7 h), three feedback rounds for #383 (about 3 h) |
| Substance | #372 R01-M1, R02-M1, R09-M2; #383 R02-M3; #388 R01-M1; #375 R03-M1 | the rounds the review is for |

So 13 of the 21 are findings about the records (the request, the
completion record, the verification state), 6 are repeats of a class, and
6 are substance. ADR 020 decision 4 keeps the full triage of every finding
of a Level 3 change with the owner's approval; the rule that a major is
always `FIX_NOW` is in `.agents/prompts/triage-reviewer.md` ("Critical and
Major findings must use this decision"), not in the ADR. Deferring the
record findings would not help: they are mechanical, and the scripts can
keep them from reaching the reviewer (change F below). The repeats are the
case the owner agrees to in principle: a further instance of a class the
owner has bounded on the Issue (as the owner did for #372 on 2026-11-06,
14:22 UTC) can be deferred with a follow-up Issue or accepted with the
owner's reason, under the full triage; in an unattended run the triage is
approved without the owner, so a major stays `FIX_NOW` there unless the
Issue holds such a decision. Better than deferring is one exhaustive
finding: a reviewer that searches the diff for the other instances of the
pattern it found and lists them in one finding ends the class in one round
(change G).

## Changes for the owner's decision

Every file below is a protected path of `.agents/policies/guardrails.conf`
(the workflow scripts, their library, the prompts, `scripts/verify.sh`),
so each change is Level 3: a full verification of its final tree, a full
review after it, and the owner's approval of the exact commit, and only one
change to the workflow scripts in flight at a time (ADR 020 decision 10).
The savings are per Level 3 feature, from the measurements above.

| | Change | Files | Expected saving |
|---|---|---|---|
| A | Round 1 of a Level 3 change is reviewed on the feedback run too; only the complete round that can end the run gets the full verification. ADR 020 decision 5 asks for the complete verification of the final tree and a complete review after it, and nothing of round 1. | `scripts/run-feature.sh` (the `review_options` lines of the round loop) | one full run: 97 min alone, 2 h 13 to 3 h 11 as measured |
| B | A failed verification is repeated with the tier the step ran (the feedback groups for a feedback round, the full run for a complete round), not with `--targeted`, which a Level 3 change refuses. | `scripts/run-feature.sh` (`repair_verification`, the handoff text it writes) | the false "unstable" stops: two of the three runs, 7 to 12 h of calendar time and a manual restart each |
| C | A per-step duration record: one line per step start and end, with the step, its outcome and its seconds, in `.agents/run/<issue>-log` (today only exceptional outcomes are written there), and the start time of each agent session. `docs/development.md` names it beside the time log. | `scripts/run-feature.sh` (`retrying`, `step_once`, `note`), `docs/development.md` | none; the estimate of a run becomes a reading |
| D | Independent groups of `verify.sh` run at the same time: `code`, `default`, `integration-quarto`, `integration-browser` and `lean-build` first; `integration-other` and `site-build` after `lean-build`; the rest of `build` and the three `e2e` groups after `site-build`; one log per group, the summary and the pass record unchanged; `--only` and the CI jobs unchanged. | `scripts/verify.sh`, `tests/verify-test.sh`, `docs/development.md`, the ADR 012 status line if the owner wants the local order recorded | 30 to 40 percent of every full run (25 to 50 min), today two to five full runs per Level 3 feature |
| E | The reviewer's context names the verification state of the round, and the reviewer contract says that the missing full run of a feedback round is a limitation, not a finding; the Markdown report renders a feedback round as such. | `scripts/review-feature.sh` (the context), `.agents/prompts/reviewer.md`, `scripts/lib/review-data.sh` | the #375 class: two rounds, about 2 to 3 h |
| F | The fix session refreshes the approval request's `Tree:` line and the detected triggers of the completion record before it ends, told by the script with the current values; `review-feature.sh` reports a stale request or a missing detected trigger before it starts the verification run, so the round is not spent on it. | `scripts/apply-triage.sh`, `.agents/prompts/triage-implementer.md`, `scripts/review-feature.sh` | 13 of the 21 majors: about one round each (a feedback run of 15 to 60 min, the review, a fix session of 20 to 40 min), 6 to 8 h over the three features |
| G | The reviewer lists every instance of a repeated pattern in one finding; the triage of a Level 3 change may `DEFER` (with a follow-up Issue) or `ACCEPT` a major that is a further instance of a class the owner has bounded on the Issue, under the full triage and the owner's approval, never unattended. | `.agents/prompts/reviewer.md`, `.agents/prompts/triage-reviewer.md` | #372 rounds 6 and 7 (two full runs, about 4.5 h) and #383 rounds 3 to 5 (about 3 h) |

Recommended order: B and A (the two defects that made the runs stop and
repeat), C (so that the next runs are measured), F and E (the record
findings and the feedback-round findings), G, then D (the largest change,
measured by C). A, B, C, E, F and G together are one small feature on
`run-feature.sh`, `review-feature.sh`, `apply-triage.sh` and the prompts;
D is a feature of its own on `verify.sh`, after the first one is merged
(ADR 020 decision 10). The owner may also decide that only some of them are
made.

Out of scope, as the Issue says: ADR 020 decisions, the CI route, the
five-round limit, the verification rules of ADR 017. Two observations
outside the four questions, for a later Issue if the owner wants one: the
reproduction check is 40 min of every full run and runs its clones one by
one; and the time log records a run killed at the two-hour limit as
`passed`.

## What the implementation found

Four details that the table above did not know, and the plan now records:

- **G needs the scripts, not only the prompts.** The rule that a major
  finding is always `FIX_NOW` was enforced in `scripts/lib/review-data.sh`
  (`triage_decision_rules`, on the agent's result and on the stored
  artifact) and in `scripts/finish-feature.sh` (a latest review with a
  major finding refused the commit). Both now follow the owner's decision:
  a triage that the owner approves at the prompt may `DEFER` or `ACCEPT` a
  major finding; an unattended triage (the artifact says `unattended:
  true`), and a critical finding, keep `FIX_NOW`; `finish-feature.sh`
  commits when the approved triage of the latest review deferred or
  accepted its major findings and says so in the commit message.
  `triage-review.sh` tells the triage agent which rule applies. And a
  complete re-review of a Level 3 change is given the earlier rounds'
  deferred and accepted findings (it received nothing of them before, so
  it reported a bounded class again every round).
- **F: the scripts refresh the line `Tree:` themselves.** The content tree
  holds the handoff note, which every fix session changes, so the line was
  stale after every fix; an agent cannot compute the tree without sourcing
  the libraries. `risk_request_refresh` (`scripts/lib/risk.sh`) rewrites
  the line, `apply-triage.sh` calls it after the fix session and
  `run-feature.sh` before every review; `review-feature.sh` refuses a
  stale request before the verification run. The detected triggers: ADR
  020 decision 1 says the scripts detect them and the record names the
  others, so the reviewer is now told that a detected trigger absent from
  the record is no finding (it was read as one: six majors).
- **A: a recorded full pass is taken by `--feedback`.** The implementer
  contract already asks for the full run last; `review-feature.sh
  --feedback` now takes a full pass recorded for exactly the content
  instead of the partial run and records the review as made on the full
  run, so round 1 of a Level 3 feature whose first review is clean is the
  complete round: one full run per such feature.
- **C: the sessions inside a step.** The per-step record lives in
  `.agents/run/<issue>-log`; `review-feature.sh` and `apply-triage.sh`
  write the start and the end of their agent session there too, through
  `agent_log` in `scripts/lib/agent.sh`, so the time of the agent is told
  apart from the verification inside the step (which the time log holds).

Out of scope, noted for the owner: a completion record that marks a
later-gate criterion `met` (two of the record findings) is not refused by
the completion gate; a mechanical refusal would end that class too.

## Affected components

`scripts/run-feature.sh` (A, B, C, F), `scripts/review-feature.sh` (A, C,
E, F, G), `scripts/apply-triage.sh` (C, F), `scripts/triage-review.sh` (G),
`scripts/finish-feature.sh` (G), `scripts/lib/agent.sh` (`agent_log`, C),
`scripts/lib/risk.sh` (`risk_request_refresh`, F),
`scripts/lib/review-data.sh` (the triage rule, G; the report of a feedback
round, E), `.agents/prompts/reviewer.md` (E, F, G),
`.agents/prompts/triage-reviewer.md` (G),
`.agents/prompts/triage-implementer.md` (F), the tests
`tests/run-feature-test.sh`, `tests/review-feature-test.sh`,
`tests/risk-workflow-test.sh`, `tests/triage-review-test.sh`,
`tests/finish-feature-test.sh`, and `docs/development.md`,
`docs/project-map.md`. `scripts/verify.sh` is untouched (D is not in this
Issue).

## Constraints and ADRs

- ADR 020 decision 5: a partial run is never evidence; the final tree gets
  the complete verification and a complete review after it (A keeps both).
- ADR 020 decision 4: a Level 3 change is reviewed complete in every round
  and every finding keeps the full triage with the owner's approval (G
  keeps both).
- ADR 020 decision 10: one change to the workflow scripts in flight at a
  time.
- ADR 012 decision 1: a run with `--only` verifies nothing; D changes the
  local order of the groups, not what a verification is.
- ADR 017 decision 7: the tiers stay as they are.

## Risk classification

This plan: Level 1 (a file under `.agents/plans/`), no trigger. The
changes: Level 3 by their paths, as the table says.

## Implementation steps

1. Done: the answers above.
2. Done: the owner decided (2026-11-07): A, B, C, E, F, G here; D later.
3. Done (2026-11-07): the six changes with their tests
   (`tests/run-feature-test.sh`: the Level 3 rounds, the reused full pass,
   the refreshed request, the repeat in the feedback tier;
   `tests/risk-workflow-test.sh`: the reviewer's context, the report, the
   reused pass, the stale request, the fix session;
   `tests/review-feature-test.sh`, `tests/triage-review-test.sh`,
   `tests/finish-feature-test.sh`), the documentation, the full
   verification last, the full review after it. No approval request: the
   change is Level 3 by its paths, which the code owners enforce.
4. For D, in a feature of its own after this one is merged: the parallel
   loop with one log per group, `tests/verify-test.sh`, the documentation,
   the same gates; the first run after it gives the idle-machine
   measurement that this plan could not make.
5. Criterion 3 is shown by the tests of step 3 on the pipeline (one full
   run per Level 3 feature in the three cases, and the duration record),
   and observed on the next Level 3 feature run under the changed
   pipeline: its per-step record and the time log.

## Test and verification strategy

The changes are Level 3 (every file a protected path): the workflow
self-tests named above for each change, and the full `./scripts/verify.sh`
on the final tree, run last. The self-tests run in the full run because
workflow files changed (ADR 005).

## Context

Base commit e729b1e on `main` (2026-11-06). The measurements were read on
2026-11-06 between 22:00 and 23:30 UTC while the owner's queue ran
`./scripts/verify.sh --base` for #372 and #383 on this machine.

## Open questions

None. The owner decided on 2026-11-07.

## Next action

The full verification, the independent review, the owner's approval of the
exact commit; then D as a feature of its own.
