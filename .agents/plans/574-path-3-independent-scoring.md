# Plan: F150, path 3 of Part B: independent scoring and sealed evaluation (AE4), robustness and statistical uncertainty (AE5), failure analysis, reviewer evaluation, and regressions (AE6) (Issue #574)

Source: `docs/roadmap.md`, F150; `docs/changes/part-b-scientific-products-and-research.md`,
B3.4 to B3.6 and the rows of EV4, EV5, AI4; the owner's start on #574
(2026-11-19). Written by the implementer at the start of the work (the
Issue expects a detailed plan and none existed).

**Level 2.** Three new lessons (`agents-llm` 22 to 24, slots AE4 to AE6,
course mechanics) with their replay fixtures, three new library modules
(`src/pbc/evidence/sealed.py`, `src/pbc/evidence/robustness.py`,
`src/pbc/evidence/reviewers.py`), an additive extension of
`src/pbc/agents/review_lab.py`, three experiments in
`src/pbc/mechanics/experiments/`, new tests, and a section of
`docs/discovery-protocol.md`. No protected path. No existing test
assertion changes: the extension of `review_lab` adds names beside
`CANDIDATES`, `REVIEWERS`, `verdicts`, `resolve`, and `ReviewDisplay` and
changes none of them, so AI4's replay and its tests run as before
(criterion 4). No published claim of another lesson changes. If an existing
assertion or claim has to change after all, the feature becomes Level 3
and the approval request of the Issue (.agents/approvals/574.md) is created.

## Visual deliverables

Scientific figures, drawn by the build from the verified code; no artwork,
no image file.

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

- **Artifacts.**
  - AE4 `fig-evaluator-scores` (`simulated`): two stacked panels, the
    projectile candidates' recomputed held-out errors beside the one error
    a candidate reported for itself, and the spring candidates'
    development errors beside the frozen candidate's sealed error, with
    the tolerance. (Changed during the work: a plot of the error against
    time would print the held-out and sealed times and reveal the hidden
    frequency, which a page never shows.)
  - AE5 `fig-trial-spread` (`simulated`): the held-out error of every
    recorded trial, by variant (repeated, noisier readings, failing
    instrument), log scale, with the tolerance, beside the range of the two
    baselines over twenty seeds of the same variant.
  - AE5 `fig-success-intervals` (`simulated`): the share of recovering
    trials per variant with its exact 95 % interval, beside the baselines'.
  - AE6 `fig-review-outcomes` (`simulated`): cases by reviewer session, each
    cell a decision classified as correct acceptance, correct rejection,
    missed error, false alarm, or no decision, told apart by marker shape
    and fill, not by colour alone.
- **Scientific validation.** Every number is recomputed by the build from
  frozen traces (replay re-executes each tool call) or computed by the
  evaluator itself; tests assert each stated result; the lesson-source
  checks, the single-page renders, and the independent review.
- **Accessible fallback.** Every figure has a caption that states its
  conclusion and an alt text that describes it without computed values;
  every figure's numbers are also in a table on the page; no script is
  added.

## The learner and the subject (pbc-physics-teaching)

**Archetype: AI agent or evaluation** for all three. Each opening states
the kind of evidence at once (F168's gap in AE3): recorded runs replayed
and re-scored, the evaluator's own computation, deterministic baselines,
and what is a model's own statement.

### AE4, Independent scoring, sealed evaluation, and provenance

- **Learner.** Has done AE3 (the benchmark, the plain model, the
  baselines, `comparable`) and AE1's measures. Knows replay (ADR 004).
- **Central question.** Who computes a score, and how does a reader know
  that the reported result belongs to the candidate that was selected and
  was not tuned on the test?
- **Counterintuitive points.** (a) A candidate's own score is a claim, not
  evidence: stored, shown, labelled unverified, never used. (b) Selecting
  the best of several candidates by their development error makes that
  error optimistic: the frozen candidate's error on a withheld split is
  the one to report, and it is larger here. (c) A digest says which file
  was evaluated, not that it is right.
- **Sections.** (1) The evaluator scores, the candidate reports: the
  pilot ledger of F137 on the projectile (`pbc.evidence.pilot`), run by
  the experiment on a temporary copy of the fixtures: a plain model's
  report of recovery with an error of 0.001 against the evaluator's
  recomputation (claim *failed*); a fixture whose readings were edited
  (*invalid*); resources counted by the evaluator against the run's own
  cost record. These are the cases of F137's tests
  (`tests/unit/test_evidence_pilot.py`), reproduced on the page
  (criterion 2). (2) Frozen and bound: the freeze, the final evaluation
  bound to the digest and version, the second final evaluation refused, a
  change after the freeze refused, a new cycle with a new version, and an
  invalidation by a changed artifact. (3) A withheld final evaluation on
  the spring (`pbc.evidence.sealed`): D2's three recorded runs (told the
  form, the names, nothing) evaluated in development on the protocol's
  held-out settings; the best selected and frozen; one final evaluation on
  a sealed split of later times that no development evaluation used. The
  sealed split's digest is in the configuration recorded before the
  development evaluations. The isolation is stated: the split is in the
  repository, so it is withheld from the candidate's tools and from
  selection, not secret.
- **Moments.** A prediction before the sealed result: "the selected run
  had the smallest development error; will its error on the later, sealed
  times be smaller, equal, or larger, and why?" The self-check:
  which statement the ledger supports (the interpretation moment).
- **Code shown and why.** `Ledger.add_final` (exact full source: the
  binding rules are its control flow, validation); `sealed.select` and
  `sealed.final_on_sealed` (the method of the section: selection on
  development only, one sealed evaluation); `claim_status` is described in
  prose with a Source link (its precedence list is in the prose). The
  drawing function is a Source link (it computes nothing; every point is
  an evaluation of the ledger). The experiment's `scoring` (region
  "fabricated") and `tampering` (region "new-cycle") are exact selections:
  the fabricated report and the legitimate new cycle.

### AE5, Robustness and statistical uncertainty

- **Learner.** AE4, D2. Binomial proportions (outside prerequisite).
- **Central question.** The spring's partial run failed once (D2, AE1).
  Was that the model, or that run? How many runs does it take to say,
  and what changes when the readings or the instrument get worse?
- **Counterintuitive points.** (a) Four successes in four trials still
  leave an interval for the success rate whose lower end is far below one
  (exact 95 % interval [0.40, 1]); a single failure or success says little
  about a rate. (b) A perturbation the agent cannot see (larger noise; the
  prompt is the same) degrades a fit the agent does not adapt; a failing
  instrument costs calls, not necessarily accuracy. (c) Costs differ
  between trials of the same task and are recorded by the runs, not
  measured by the build.
- **Recordings (criterion 3).** Ten sessions on protocol
  `f66-prior-knowledge-1` (the spring, hidden stiffness, budget 20, 12
  steps, tolerance 0.05), condition `partial`, each a fresh sub-agent:
  - *repeated*: seeds 1 to 4, readings as published (four trials);
  - *noisier readings*: the noise five times larger, seeds 1 to 3 (three
    trials); the prompt is unchanged, so the agent is not told;
  - *failing instrument*: every third `measure` call fails with an error
    and uses no probe, seeds 1 to 3 (three trials).
  Each trial's `TraceInfo` (protocol version of its variant, seed, prompt
  SHA-256, model, date, cost: model messages and tool calls as the session
  recorded them; tokens and price not reported) is in
  `pbc.evidence.robustness`, checked against the fixture by a test. The
  page quotes the costs from these records; nothing is timed or counted
  live in CI.
- **Computed by the build.** Each trial replayed and scored; per variant:
  recovered k of n with the exact (Clopper–Pearson) 95 % interval, the
  median and range of the held-out error, probes, refused or failed calls;
  the baselines grid + least squares and random + least squares over
  twenty noise seeds of each variant (the build runs them), with their
  rates and intervals. Every trial and every outcome is held in a
  `pbc.evidence` ledger, so that a failed or inconclusive trial lowers
  the rate instead of leaving it.
- **Moment.** A prediction before the repeated trials' table: "the
  published partial run failed; in four more trials, how many recover?",
  then the interval that says how little either answer would show. The
  self-check on what the intervals support.
- **Code shown and why.** `robustness.failing_instrument` (exact full
  source: the injected failure, agent control), `robustness.noisier`
  (the perturbation), `robustness.success_interval` (the statistics: the
  method). The experiment's per-variant row (exact selection,
  orchestration of one row). The drawing functions are Source links.

### AE6, Failure analysis, reviewer evaluation, and regressions

- **Learner.** AI4 (three reviewers, the checks of the contract) and AE5.
- **Central question.** A reviewer accepted or rejected a piece of code:
  how often is it wrong, in which direction, and would we notice if the
  review got worse?
- **Controlled cases.** Eight steppers with known truth, numbered in a
  fixed order that says nothing: the three correct methods of the gallery
  (velocity Verlet, symplectic Euler, Runge–Kutta 4) and five faulty ones
  (the stopped clock, the remembered acceleration, RK4 with equal weights,
  explicit Euler posing as symplectic, Verlet without the half), each with
  the claim of the method it poses as. Every check outcome is recomputed;
  Runge–Kutta 4, correct, fails the bounded-energy band, which it does not
  claim: the trap for a false alarm.
- **Reviewers.** The physics and numerics roles of AI4, with the same
  checks, over the eight cases, each with a `decide(case, accept)` tool
  that records its decision: a structured decision, so that missed errors
  (a faulty case accepted) and false alarms (a correct case rejected) are
  counted from the trace, not read from prose. Each role recorded twice
  with the same prompt (repeated assessment): four sessions, Opus
  sub-agents in a Claude Code session, fixtures in AE6's directory, their
  record in `review_lab`.
- **Computed by the build.** For each session: decisions classified
  against the known truth; consistency between the two repeats of a role.
  For the evaluator's rules on the recomputed checks of the panel: AI4's
  rule (any failed check rejects) and the contract's rule (a check counts
  only when it applies to the case's claim), with missed errors and false
  alarms; ablations (each role alone, each check removed); evaluator
  overfitting (a rule chosen on AI4's two pieces, "reject when the
  bounded-energy check fails", perfect there and measured on the eight
  cases); a regression (the panel's frozen trace replayed against a
  stepper changed after the recording fails visibly with the step and the
  tool that differ, and a loosened band of the energy check, applied by
  the evaluator to the recorded measurements, turns a correct rejection
  into a missed error, which a comparison with the frozen outcomes
  reports).
- **AI4 unchanged.** `CANDIDATES`, `REVIEWERS`, their tools, prompts,
  `verdicts`, `resolve`, and the display are untouched; the AI4 tests and
  `test_scientific_review_experiment.py` pass unchanged.
- **Moment.** A prediction before the outcomes figure: "which case will
  the physics reviewer miss, and which correct case may a reviewer
  reject?" The self-check on what a missed-error rate of a role measures.
- **Code shown and why.** `reviewers.classify` (the classification:
  validation), `reviewers.contract_rule` (the applicability rule), the
  ablation function (exact full source), `reviewers.regressions`
  (validation). The panel's `decide` tool definition (agent control,
  exact selection). Drawing functions are Source links.

## Recording protocol

Each session: a fresh sub-agent (Opus) given only the system prompt, the
task, and the tool specifications, told to write each message as one JSON
object `{"text": ..., "tool_calls": [...]}` and to deliver it through one
harness command (a script in the implementer's scratchpad), using no other
tool. The harness runs every call through the allowlist of the run with
`pbc.agents.loop.run` and a scripted client holding the messages so far,
and prints the recomputed results. (Changed during the work: relaying every
round trip through the implementer's session was too costly; one session
whose command a permission check refused was relayed that way.) Each
sub-agent's session log was checked afterwards for any other command. The fixture is written with
`save_recording`; the cost is the number of model messages and tool calls.
Model `claude-opus-5-5 in a Claude Code session`, recorded 2026-11-19.

Names after the lesson-source checks: the experiments are
`independent_scoring_and_sealed_evaluation`,
`robustness_and_statistical_uncertainty`, and
`failure_analysis_and_reviewer_evaluation` (the lesson's slug); fixtures
are named with letters only (`replay-repeatedone.json`,
`replay-physicsone.json`, ...).

## Steps

1. `pbc.evidence.sealed` (AE4) and tests.
2. `pbc.evidence.robustness` (AE5): variants, failing instrument,
   trials and their records, replay, scoring, intervals, baselines, live
   entry point; tests.
3. `review_lab` extension (cases, panel, decide, replay) and
   `pbc.evidence.reviewers` (classification, rules, ablation, overfitting,
   regressions); tests, AI4 tests unchanged.
4. Record the fourteen sessions; commit the fixtures with their records.
5. The three experiments and pages; tests of each experiment
   (`assert_the_page_and_the_results_agree` and the stated results).
6. `docs/discovery-protocol.md`: the sealed split and the decision on it,
   robustness trials, reviewer evaluation.
7. Lesson-source checks, the changed tests, then `./scripts/verify.sh
   --base` last (new lessons).

## Acceptance criteria and where they are met

1. Lesson and agent rules, outcomes: the three pages, their front matter,
   the lesson-source checks, the experiments' tests.
2. AE4: the fabricated report failing, the invalid fixture, and the final
   evaluation bound to the frozen candidate, run on the page from the
   pilot of F137 and asserted by the experiment's tests.
3. AE5: every trial a recorded fixture replayed by the build; costs and
   call counts from the `TraceInfo` of each recording, checked against the
   fixture by a test.
4. AE6: missed errors and false alarms from the four frozen traces; AI4's
   tests unchanged and passing.
5. The verification the targeted run reports (here `--base`), run last.
