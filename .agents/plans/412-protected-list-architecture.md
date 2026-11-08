# Plan: the protected list and the verification architecture (Issue #412)

Source: Issue #412 and its comment of 2026-11-08, Issue #396 (points 1, 3
and 5, the owner's decisions of 2026-11-07), ADR 020 decisions 1, 3 and 5,
ADR 014 decision 11, ADR 017, `docs/process.md` (#404), the plan of #389,
and the measurements on #236 and #389.

Skills: none (no visual deliverable: a policy list, a test, and process
text).

Level: 3 for the change to the list (`guardrails.conf` and
`tests/risk-level-test.sh` are protected paths, and the change narrows what
needs the owner's approval). The part delivered in the session of
2026-11-08 touches only `docs/process.md` and this plan (Level 1 by path);
the feature is assessed at Level 3 because it is the first step of a Level
3 change and the owner approves the exact commit.

Status: the owner answered the four open questions in the Issue body
("Decisions of 2026-11-08"); the resumed session of 2026-11-08 delivered the
whole change. The sections "What the session found" and the proposals below
are the record of the first session; the decisions replace them where they
differ.

## The owner's decisions (2026-11-08, Issue #412) and where they are

1. The ADR 020 addendum is part of this Issue: ADR 020, "Addendum to
   decision 1 (Issue #412, 2026-11-08)", status Proposed, with a line in the
   ADR's status.
2. `.agents/prompts/reviewer.md` and `.agents/schemas/` stay protected (the
   builtin list of `scripts/lib/guardrails.sh` is unchanged; both are on the
   `protected:` line of `guardrails.conf`); the other prompts are on a
   `sensitive:` line.
3. `docs/architecture.md` leaves the `protected:` line, is `sensitive:`, and
   is Level 2 by path (`risk_level1_path` in `scripts/lib/risk.sh`); a
   trigger in its content keeps Level 3. `tests/risk-level-test.sh` shows
   the list, the sensitive reports, and both level cases.
4. F113 and the paused part of ADR 017 are deferred with three triggers
   (95 lessons, a full `main` run near 80 minutes, too little margin in
   repeated runs): `docs/process.md`, "The verification architecture". ADR
   017 is unchanged; `docs/roadmap.md` is unchanged (the owner did not ask).

Also updated: `docs/process.md` ("Risk levels" with the reason and the
safeguard of criterion 2, "Proposals, not rules"), and the paragraph on the
risk levels in `docs/architecture.md`.

## What the session found

1. **ADR 020 decision 1 names the three paths as Level 3.** Its list of
   Level 3 paths, "which this list names directly and authoritatively",
   contains "the planning documents: `docs/PROJECT_REQUIREMENTS.md`,
   `docs/roadmap.md`, and `docs/architecture.md`" and, under the gate, "the
   prompts `.agents/prompts/`, the schemas `.agents/schemas/`". The same
   decision says that from F130's merge "the protected paths of
   `guardrails.conf`" is this list. Removing the three from the protected
   lines therefore contradicts an accepted ADR, which ranks above the Issue
   (`AGENTS.md`, "Source precedence"); `docs/process.md` says that "a rule
   changes only through an ADR". The Issue does not ask for an ADR change,
   and the implementer contract allows one only when the Issue asks for it.
2. **The builtin list of `scripts/lib/guardrails.sh` protects
   `.agents/prompts/reviewer.md` and `.agents/schemas` whatever the
   configuration says** (`GUARDRAILS_BUILTIN_PROTECTED`; the comment of
   `guardrails.conf`, "Always protected, whatever this file says: ... the
   scripts, prompts, and schemas that carry out the gate"). Taking the two
   off the `protected:` line would leave the reviewer contract and every
   schema protected; the Issue's criterion 1 needs a change to that gate
   script too, which the Issue's "Not in scope" allows only for "what the
   list needs".
3. **`docs/architecture.md` off the list becomes Level 1, and a Level 1
   change needs no review.** `risk_level1_path` in `scripts/lib/risk.sh`
   reads every path under `docs/` as Level 1, and `docs/process.md`
   ("Risk levels") says "Level 1: the tier of the change; no review
   required". The sensitive treatment ("the reviewer is told to look at
   it") then reaches a change that touches only `docs/architecture.md` only
   when a review runs. `.agents/prompts` and `.agents/schemas` would be
   Level 2 by path (not `docs/`, not top-level Markdown), so a review is
   required there.

## Proposal for points 1 and 3 (for the owner's decision on the route)

- An addendum to ADR 020 (status Proposed, accepted by the merge) that
  takes `docs/architecture.md`, `.agents/prompts/` and `.agents/schemas/`
  out of decision 1's Level 3 list and names them sensitive, with the
  reason below.
- `guardrails.conf`: the three off the `protected:` lines, onto the
  `sensitive:` line; its header comment and the builtin list's comment
  updated.
- `scripts/lib/guardrails.sh`: `.agents/prompts/reviewer.md` and
  `.agents/schemas` off `GUARDRAILS_BUILTIN_PROTECTED`, unless the owner
  wants the reviewer contract or the schemas kept protected (question 2).
- `docs/architecture.md` at Level 2 by path (one case in
  `risk_level1_path`), so that the reviewer always sees a change to it,
  unless the owner accepts that a change to it alone needs no review
  (question 3).
- `tests/risk-level-test.sh`: the expected protected list without the
  three; a change to each reported as sensitive and not protected; the
  path minimum of a change that touches only one of them is 1 or 2, not 3.
  `tests/guardrails-test.sh` and `tests/review-feature-test.sh`, which name the builtin paths, are
  checked and updated.
- `docs/process.md` ("Risk levels", "The owner's approval and the merge")
  and the comments of `scripts/lib/risk.sh` updated to the new list.

**What a silent change of a prompt or a schema can do, and what catches
it** (criterion 2; the same text is in `docs/process.md`, "Proposals, not
rules"). A prompt change can weaken a review: a reviewer contract that no
longer asks for a check, a severity rule that turns majors into minors, an
implementer or triage contract that lets a finding through. A schema change
can loosen what a review record or a completion record must contain. None
of it fails a test. What catches it once the paths are sensitive: the
change is Level 2 by path, so it gets a review of the complete feature
(`--changes` is not allowed for it, its reach is not certain); the merge
approval gate lists it as sensitive in the reviewer's context; the reviewer
is a different model from the implementer and reports a weakened guarantee
as the escalation trigger "verification guarantees", which makes the change
Level 3 again; and the owner reads every pull request before it is merged,
because no agent merges.

## Proposal for point 5: F113 (ADR 014 decision 11, Issue #150) and ADR 017

The decision is the owner's, on Issue #412. The text in
`docs/process.md` and, if the owner asks, `docs/roadmap.md` is written
after it.

**The numbers.**

- A full run takes 94 to 140 minutes: a median of 94 min before F131 and
  110 to 140 min after it; 140 min in the heavy period of 2026-11-04 to
  08 (54 full runs, 128.6 h; #236, the time-log table).
- 22 percent of the full runs failed in the heavy period (12 of 54; #236).
- The `build` chain is 57 percent of a full run: about 72 of 127 min under
  the load of the measured run (Lean build, site build, determinism build,
  reproduction 40 min lesson by lesson; #389's plan, question 3). The rest
  (57 min) fits beside it.
- #389 cut the number of full runs of a Level 3 feature to one on the
  final tree (changes A and B); change D (parallel groups, 30 to 40
  percent of a full run, estimated 60 to 75 min) is a feature of its own.
- Every push to `main` executes every lesson (ADR 017 paused by ADR 020
  decision 8); CI's `build` job has a 120 min timeout, the planning
  boundary of 110 lessons (ADR 012 decision 9).

**Options.**

- **(a) Say no to F113 and ADR 017 decisions 1 to 6 and 9.** Close #150
  and the branch, mark ADR 014 decision 11 and ADR 017 rejected, keep the
  tiers as they are: CI is the complete gate, locally `--targeted` or
  `--base` and one full run of a Level 3 final tree. The capacity question
  goes to the re-assessment points that exist (a complete run on `main`
  near 100 minutes) and to change D. Cost: the full run stays near 100 to
  140 min and grows with the lesson count.
- **(b) Do F113.** Same-machine lesson shards of the build split the
  reproduction and the page renders, the 57 percent. Expected saving: most
  of the reproduction's 40 min and part of the build, on top of D. Cost:
  a feature that touches the build and the digest, Level 3; the paused
  branch is a month old.
- **(c) Defer with a date or a lesson count.** Keep both paused, and decide
  at a named point (for example the first `main` run above 100 min, or 110
  lessons).

**Recommendation for the owner:** (a), with change D as the one capacity
step: D gives 30 to 40 percent without touching the build or the digest,
the full run is now needed once per Level 3 feature, and the re-assessment
points that exist catch growth. Deciding "no" ends the re-opening that
point 5 of #396 names.

## Steps

1. `docs/process.md`: a section "The verification architecture" (CI is the
   complete gate; locally the fast tier and one full run of the final tree
   of a Level 3 change), with its ADR decisions; under "Proposals, not
   rules" the owner's decision on points 1 and 3 with its reason and its
   safeguard, and a pointer to this plan for F113. **Done 2026-11-08.**
2. The ADR addendum, the list, the level of `docs/architecture.md`, and
   the tests, as the owner decided (the builtin list unchanged). **Done
   2026-11-08.**
3. The F113 decision "deferred" with its triggers in `docs/process.md`.
   **Done 2026-11-08.**
4. Verification: `bash tests/risk-level-test.sh`, `./scripts/check-docs.sh`,
   the unit tests of the changed files; the full `./scripts/verify.sh` runs
   after the session (Issue comment of 2026-11-08).
5. Criteria 4 and 5: the share of Level 3 commits on the next ten commits
   after the merge, recorded on #396 (`post_merge`); the pull request refers
   to #396 and does not close it (`pr_ci`).

## Open questions

None: answered in the Issue body, "Decisions of 2026-11-08".
