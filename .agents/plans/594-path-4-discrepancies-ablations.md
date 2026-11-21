# Plan: F154, path 4 of Part B: discrepancies, ablations, and follow-up experiments (RR6); independently checkable reports and research memory (RR7) (Issue #594)

Source: `docs/roadmap.md`, F154; `docs/changes/part-b-scientific-products-and-research.md`,
B4.6, B4.7, section 3.4 (evidence status; "Revising prose after review does
not count as resolving a request for new scientific evidence"), section 6
(R3, R5); the owner's start on #594 (2026-11-21). Written by the implementer
at the start of the work, as the Issue asks.

**Level 2.** Two new lessons (`mechanics` 25 and 26, slots RR6 and RR7,
course mechanics, the course of the worked example) with their experiments,
three new modules of `src/pbc/research/` (`followup.py`, `report.py`,
`memory.py`), new tests, and additive text in `docs/architecture.md` and
`docs/project-map.md`. No protected path. No existing test assertion, no
existing experiment file, and no published claim of another lesson changes:
the new code imports `pbc.agents.specification`, the laboratory of SA1, the
specifications of RR1 and RR2, and the corpus and labels of RR3, and changes
none of them; the new tolerances and budgets live in the new modules. No file
is added next to a published lesson page and no replay fixture is added. If
any of this turns out to be needed, the feature becomes Level 3 and the
approval request (.agents/approvals/594.md) is created.

## One investigation, continued

RR1 to RR3 followed the simulated tennis ball of M3 and SA1 to one claim
(RR2, the original plan): at 10 m/s the best launch angle lies above the
predicted bound of 43 degrees, supported by the scripted route of SA1 with
every criterion of a frozen plan met. RR6 and RR7 continue that claim.

- **RR6** reviews it. Four findings (the review of RR5's kind, here written
  by the author as a reviewer, said so on the page): every run used explicit
  Euler (requests evidence); the drag coefficient is fixed at M3's value 0.5
  although a tennis ball's is not known that well (requests evidence over
  a stated range, 0.4 to 1.0, a reviewer's assumption, not a measurement);
  the claim says "the tennis ball" for a simulated ball (wording); no real
  ball was thrown (requests evidence the laboratory cannot produce). Each
  request becomes a knowledge gap with two competing explanations and the
  outcome each predicts for a declared experiment; an experiment for which
  both predict the same outcome is refused as not discriminating. An
  ablation of the claim through the same route (drag removed, the
  fourth-order integrator, the coefficient at the ends of the range) shows
  what the result depends on. (Changed during the work: the ablation comes
  after the tests, and its rows that are a test's record say so; run
  first, it would have let the tests be declared with known outcomes.) The experiments run, their records enter an
  append-only log chained by digest, the claim is revised from them, and
  each branch is continued or stopped with its reason and the condition for
  revisiting it.
- **RR7** writes the report of the whole investigation (RR1 to RR6): every
  citation resolves to a verified passage of RR3's corpus and is checked
  against the label RR3's rule computes; every number resolves to a field of
  a record; an interpretation is marked. The records form a reproducible
  bundle that the build executes again and compares by digest. A research
  memory stores ideas, code, data, results, limitations, and open questions
  with their identities, and a reuse is checked against them.

No model is run in either lesson. The reviewer of RR6 is the author of the
page; the route is SA1's scripted route; the report is written data checked
by a program. Each page says so at its opening.

## The laboratory of RR6

A new laboratory in RR6's experiment (SA1's is unchanged): SA1's two
actions, plus `range_fourth_order` (the same throw stepped with
`pbc.mechanics.integrators.rk4_step`) and `range_with_coefficient` (the
same throw with the drag coefficient as an argument, `cd`, dimensionless,
0 to 1, through `pbc.mechanics.drag.drag_constant` and M3's ball). The route
and its budget are SA1's; every follow-up is a specification derived from
RR1's `SLOW_THROW` by one change, run through the allowlist.

Computed before planning (route, resolution one degree): explicit Euler and
the fourth-order method give the same bracket at 10 m/s; the coefficient
0.8 is supported above 43 degrees, 1.0 is undecided (the bound lies inside
the bracket), and at half a degree 1.0 stays undecided.

## Visual deliverables

Scientific figures drawn by the build from the verified code, and
conceptual diagrams drawn with `pbc.authoring.diagrams`; no artwork, no
image file.

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

- **Artifacts.**
  - RR6 `fig-follow-up-chain` (`conceptual`): a finding, the gap it opens,
    two explanations with their predicted outcomes, the discriminating
    experiment, the new record, the revised claim; a revision of the prose
    that leads back to the finding, still open.
  - RR6 `fig-ablation-brackets` (`simulated`, the preview): for each
    condition of the ablation and the follow-ups, the route's bracket as a
    horizontal interval with its best setting, the bound as a vertical line,
    the marker by the verdict (supported, undecided), the baseline condition
    drawn as a band.
  - RR7 `fig-report-trace` (`conceptual`): a statement of the report, its
    number to a field of a record and the record to the bundle that executes
    it again; its citation to a passage and the passage to its page; a
    marked statement to nothing.
  - RR7 `fig-report-checks` (`simulated`, the preview): for each statement
    of the report (rows), each number and citation in order (columns),
    marked by what it resolved to (a record, a passage, marked, refused);
    two panels, the report as written and the report with planted errors.
- **Scientific validation.** Every number is computed by the build: the
  route's runs through the allowlist, the brackets and verdicts, the
  statuses of the findings, the resolution of every token of the report,
  the bundle's digests executed again, the memory's reuse checks. Tests
  assert each stated result and the agreement of page and results
  (`assert_the_page_and_the_results_agree`); the lesson-source checks, the
  single-page renders, and the independent review.
- **Accessible fallback.** Every figure has a caption that states its
  conclusion and an alt text without computed values; the numbers of every
  simulated figure are also in a result table on the page; no script is
  added.

## The learner and the subject (pbc-physics-teaching)

**Archetype: AI agent or evaluation** for both (the evaluation of research
decisions: what counts as resolving a review finding, and what makes a
report checkable). No recorded model run; each opening says what kind of
evidence the page shows. Prerequisites: RR6 takes RR2 and RR5
(`from-question-to-research-plan`, `scientific-review`); RR7 takes RR6 and
RR3 (`discrepancies-and-follow-up-experiments`,
`literature-and-evidence-maps`).

### RR6, Discrepancies, ablations, and follow-up experiments

- **Learner.** RR2 (a frozen plan and its supported claim), RR5 (a review
  finding decided by a recomputed check, not by votes), SA1 (the route).
- **Central question.** A reviewer doubts a supported claim. What has to
  happen before the doubt counts as answered, and when is a line of
  follow-up worth continuing?
- **Counterintuitive points.** (a) An experiment that confirms the claim
  can still answer nothing: it must be one whose outcome the competing
  explanations predict differently (the coefficient 0.4 is refused: both
  predict "supported"). (b) A revision of the wording can make a finding
  disappear from the text and leave it unanswered: only a new record
  resolves a request for evidence, and a revised claim that cites no new
  record leaves it open. (c) The ablation shows that the integrator, which
  a reviewer of numerics would check first, does not move the bracket at
  all, while the coefficient, which nobody measured, takes most of the
  claim's margin; the revised claim keeps its number and narrows its
  scope, and its stated reason (drag under a fifth of the weight) fails
  inside the range where the claim still holds.
- **Computed** (`pbc.research.followup`): `Finding` (its kind: evidence or
  wording), `Gap` (the question, two explanations with their predicted
  verdicts), `discriminates` (refuses an experiment both explanations
  predict alike), `Log` (append-only, chained by digest, entries: finding,
  experiment declared, evidence recorded, revision, decision),
  `status(finding, log)`: open, inconclusive (new evidence that did not
  decide), resolved by new evidence, or reworded (a wording finding only);
  a revision never changes the status of an evidence finding. Branch
  decisions by a declared rule: stop when the gap is closed, continue with
  a declared follow-up when the evidence was inconclusive, stop as
  infeasible when no action of the laboratory can produce the evidence;
  each stop names the condition for revisiting it.
- **Moment.** Before the ablation table: "which change moves the bracket
  more, the fourth-order integrator or the coefficient at the top of the
  reviewer's range?" The self-check: a revised claim that answers a
  finding in words.
- **Code shown and why.** `followup.discriminates` (exact full source: the
  rule is the point, validation); `followup.status` (exact full source:
  why a revision cannot resolve a request for evidence, validation); the
  findings and a gap as exact regions of the experiment (what a finding
  holds); the two new actions of the laboratory as an exact region (what
  the follow-ups may change, agent control). Drawing functions are Source
  links (they compute nothing the tables do not show).

### RR7, Independently checkable reports and research memory

- **Learner.** RR6 (the log and the revised claim), RR3 (verified passages
  and labels), RR2 (records and digests), SA8 where known (traced
  statements; not a prerequisite).
- **Central question.** A report says what the investigation found. How
  can a reader who was not there check every sentence of it, and what
  should the next investigation be allowed to reuse?
- **Counterintuitive points.** (a) A citation that exists can still not
  support the sentence it stands in: the check is the label of the passage
  for that statement, not the presence of the key. (b) A number that is
  right to the digits written can rest on a record that no longer
  reproduces; the bundle executes the records again. (c) A result taken
  from memory without its limitations is a different, stronger claim; a
  reuse returns the limitations with it, and a reuse under another
  configuration or code is refused.
- **Computed** (`pbc.research.report`): a report is a list of statements,
  each with its text, the record field of every number it writes, the role
  of every passage it cites, or the mark "proposed, not evaluated";
  `check_report` finds every number and citation in the text and resolves
  each, or names the problem (a number without a record, a number that
  differs from its record at the digits written, an unknown passage, a
  passage whose computed label is not the role cited, a marked statement
  with a number), and the status of every review finding from RR6's log
  (criterion 2 on the report); `Bundle` and `reproduce` digest each
  record's specification, output, and code, execute it again, and compare.
  (`pbc.research.memory`) entries of six kinds with their identities;
  `recall` returns a result with its limitations and open questions and
  refuses a reuse whose code or configuration identity differs.
- **Moment.** Before the planted-error table: "which of these three
  errors could a reader find without the records, and which only with
  them?" The self-check: what a reuse of the slow-throw result at 15 m/s
  should carry with it.
- **Code shown and why.** `report.resolve_number` and
  `report.resolve_citation` (exact full source: the rules, validation);
  `memory.recall` (exact full source: the reuse check); a statement of the
  report as an exact region (what a checkable sentence holds). Drawing
  functions are Source links.

## Steps

1. `pbc.research.followup` and tests (criterion 2 at the module: a
   revision never resolves an evidence finding).
2. RR6's experiment, its test, its page.
3. `pbc.research.report`, `pbc.research.memory`, and tests (criterion 3:
   every citation and number resolves or is marked; criterion 2 on the
   report's evidence status).
4. RR7's experiment, its test, its page.
5. `docs/architecture.md` and `docs/project-map.md`: one entry each, added
   at the end; the package docstring of `pbc.research`.
6. Lesson-source checks, the changed tests, the replay tests, the skills
   check, the single-page renders and their page checks; then
   `./scripts/verify.sh --base` with `VERIFY_JOBS=2` last (new lessons).

## Acceptance criteria and where they are met

1. Lesson and agent rules, outcomes: the two pages, their front matter, the
   lesson-source checks, the experiments' tests; no model is run, and each
   page states its kind of evidence.
2. Revising prose never resolves a request for new evidence: tests of
   `pbc.research.followup.status` and of the report's findings status in
   RR7's experiment test.
3. Every citation and quantitative statement of RR7's report resolves or is
   marked: tests of `pbc.research.report` and of RR7's experiment.
4. The verification the targeted run reports (here `--base`), run last.
