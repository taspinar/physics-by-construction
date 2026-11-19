# Plan: F144, Path 1: SA7 counterexamples, physical constraints, and falsification; SA8 traceable explanations and experiment reports (Issue #575)

Source: `docs/roadmap.md`, F144; change request section 3.1 (B1.7, B1.8)
and section 6 (AI2, AI3, AI7); ADR 022 decision 6 (the evidence
contract); ADR 023 decision 2; the session instructions on Issue #575.
Written by the implementer at the start of the work (the Issue expects a
short plan and none existed).

**Level 2.** Lessons, `src/`, tests, and documentation. No protected path,
no ADR, no CI workflow, no check of `scripts/verify.conf`, no dependency.
No existing test assertion changes: the tests of both experiments gain
new tests and keep theirs. The published claims of both lessons do not
change: their text, numbers, tables, figures, claim labels, exercises,
and tests stay as they are, and the feature only adds to the pages. If
that stops being true during the work, the feature becomes Level 3 and
the approval request of Issue 575 is created.

## What is delivered

| Part | Where |
|---|---|
| SA7, the extension of `counterexample-hunter` | a new level-2 section `## Physical constraints {#physical-constraints}` of `site/lessons/agents-llm/02-a-counterexample-hunter/index.qmd`, before "Limits"; two outcomes added (five in all); the description gains a clause; one limit and one exercise added |
| The four physical-constraint checks | `src/pbc/verification/constraints.py`: `dimensions`, `symmetry`, `limits`, `conservation` on a closed-form candidate motion of the oscillator; tests `tests/unit/test_verification_constraints.py` |
| The deliberately wrong candidates | `src/pbc/verification/faulty_motion.py` (WRONG ON PURPOSE, as `faulty` and `faulty_driven`): four plausible closed forms, each recording the checks that must catch it |
| SA7's experiment | additions to `src/pbc/mechanics/experiments/counterexample_hunter.py` and its test |
| SA8, the extension of `interpretable-physics-explanations` | a new level-2 section `## The experiment report {#experiment-report}` of `site/lessons/agents-llm/17-interpretable-physics-explanations/index.qmd`, after the worked examples and before "Limits"; one outcome added (five in all); the description gains a clause; one limit and one exercise added |
| The report and its traceability | `src/pbc/evidence/report.py`: statements with a kind (observed, computed, proposed), each resolved to a claim of a `pbc.evidence` ledger with its evidence status, or marked proposed; tests `tests/unit/test_evidence_report.py` |
| SA8's experiment | additions to `src/pbc/mechanics/experiments/interpretable_physics_explanations.py` (the ledger of the lesson's run and baselines, the report) and its test |
| Documentation | `docs/architecture.md` and `docs/project-map.md` (the new modules); `docs/discovery-protocol.md`, "The evidence contract" (the report) |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| Two witnesses of the constraint checks: the energy of the "frequency in hertz" candidate over two periods against the conserved energy; the "phase from the arctangent" candidate from the mirrored start against the mirror image of its motion | Scientific figure, `simulated`, `pair` (two panels stacked) | `fig-constraint-witnesses`, SA7 | every curve is a candidate or `pbc.mechanics.oscillator.harmonic_motion` evaluated by the build; the plotted witnesses are those the checks report (the experiment test compares them) | alt text; the table of witnesses |

SA8 has no new figure: the report is a table whose rows link to the
existing figure `fig-explanation-intervals` and the existing tables. The
lesson previews do not change. No animation, widget, or page layout.

## SA7: physical constraints as counterexample hunts

- **Learner.** Has the hunt of the page: a falsifiable claim with a
  domain, a predicate, and a budget; a counterexample is a recomputed
  experiment; a failed hunt is inconclusive. Has the oscillator of the
  course and its exact motion (prerequisite `numerical-integrators`).
- **Central question (of the extension).** The hunter searched blindly
  within its budget. A claim about a physical model has constraints every
  correct answer obeys. Can they say where to look, before any reference
  solution exists?
- **Counterintuitive points.** (a) A constraint is itself a claim about
  every input, so a single input that breaks it is a counterexample, and
  the constraint names the input to try. (b) A symmetry reaches inputs no
  test case contains: every case starts at a positive displacement, and
  only the mirror asks about a negative one. (c) The fault that the unit
  check of the lesson on verifying scientific code could not find (a
  frequency in hertz) is invisible to dimensions here too; conservation
  finds it. (d) Passing all four checks is not a proof: the checks are
  necessary conditions, and the verdict of a candidate that passes them is
  "no counterexample found", as for an inconclusive hunt.
- **Archetype.** AI agent or evaluation (the page), with a model or
  simulation section: no model runs in the new section, which says so at
  once; the candidates are written by the author, wrong on purpose.
- **The claim and the candidates.** Claim: "this closed form is the
  motion of a mass on a spring, x'' = -(k/m) x, from (x0, v0)". Five
  candidates: the exact motion (`harmonic_motion`) and four plausible
  errors of a derivation by hand or a formula a model writes:
  1. *missing square root*: the frequency k/m for sqrt(k/m). Caught by
     dimensions (and by conservation at the values of the checks, not at
     k/m = 1 s⁻², which the page computes);
  2. *phase from the arctangent*: amplitude and phase with `arctan` in
     place of `arctan2`; right for every start at positive displacement.
     Caught by symmetry (the mirror) only;
  3. *phase with the wrong sign*: cos(omega t + phi) for cos(omega t - phi),
     the motion of the start with the opposite velocity. Caught by limits
     only (the start, and the weak spring);
  4. *frequency in hertz*: sqrt(k/m) / (2 pi) as the angular frequency, the
     fault of the lesson on verifying scientific code. Caught by
     conservation only.
- **The checks** (`pbc.verification.constraints`), each a bounded hunt
  over a fixed list of cases (non-round masses, spring constants, and
  starts at positive displacement, velocities of both signs, times over
  two periods), returning the first violating case as the **witness** or
  "no counterexample" with the number of cases tried:
  - `dimensions`: three changes of the units of mass, length, and time;
    the motion converted back must be the motion;
  - `symmetry`: the mirror (x0, v0) -> (-x0, -v0) gives -x(t), and time
    reversal x(-t; x0, v0) = x(t; x0, -v0), with the velocity reversed;
  - `limits`: at the start the motion is (x0, v0); for a weak spring
    (k/m of order 1e-12 s⁻²) it is the free motion x0 + v0 t;
  - `conservation`: m v² / 2 + k x² / 2 is constant.
  One relative tolerance, written before the checks run.
- **Tests (acceptance criterion 2).** Each check rejects at least one
  deliberately wrong candidate, and each wrong candidate fails exactly
  the checks its entry names; the exact motion fails none; the witness of
  each failure is a case of the list (or its image under the symmetry)
  and its deviation exceeds the tolerance; the module is imported only by
  the lesson's experiment.
- **AI2's debugging cases linked.** The section names the six faulty
  steppers and the four faulty simulations of the lesson on verifying
  scientific code, and maps its checks to the four constraint kinds
  (limits, units = dimensions, energy and energy balance = conservation;
  the clock and purity tests as the symmetries of the interface). The
  frequency-in-hertz candidate is the same mistake in a formula.
- **Journey.** The question; the claim and the candidates (two shown as
  code, the others by their docstrings in a table); the four checks, each
  a hunt with a witness (`symmetry` shown, the case list shown); the
  prediction moment; the table of outcomes; the table of witnesses; the
  figure; the missing root at k/m = 1; what passing means; the debugging
  cases of the lesson on verifying scientific code.
- **Deliberate moment.** Before the table: the frequency-in-hertz fault
  escaped the unit check of the lesson on verifying scientific code;
  which of the four checks finds it here?
- **Code the learner reads.** `symmetry` (exact full source: the mirror
  and time reversal written as code are the point), `CASES` (region: the
  domain of the hunt, and the positive displacement point (b)),
  `phase_from_the_arctangent` and `frequency_in_hertz` (exact full source:
  the plausible line that is wrong). `dimensions` as an exact selection of
  the conversion lines. Drawing code: a Source link (read first: it
  evaluates the candidates and draws; it computes nothing the caption
  does not state).
- **Exercise.** The candidate with x0 cos(omega t) + v0 sin(omega t)
  (the division by omega forgotten): which checks fail, and which names
  the unit? (solution computed by the experiment).
- **Outcomes added.** "Reject a plausible formula with a check of its
  dimensions, symmetries, limiting cases, or conservation, and name its
  counterexample"; "Explain why a candidate that passes every constraint
  check is not thereby correct".

## SA8: the experiment report

- **Learner.** Has the page: four predictions, the tests of each
  explanation, the two baselines, three claims labelled on the page.
- **Central question (of the extension).** A reader of a report sees
  numbers and sentences. Which of them were observed (recorded), which
  computed, which proposed, and where is the run, the data, the plot, the
  assumption, and the uncertainty behind each one?
- **Counterintuitive points.** (a) A statement of the model is observed
  data about the model, not evidence for the physics: the recorded
  interval is observed, the verified result computed. (b) The evidence
  status is derived, not written: change the recording and the computed
  statements that rest on it lose their status (the ledger's digest). (c)
  A proposed statement is legitimate in a report when it is marked; an
  unmarked one is the fault.
- **Archetype.** AI agent or evaluation; the kind of evidence of each
  statement is the subject.
- **The report** (`pbc.evidence.report`): a `Statement` has a text, a
  kind (`observed`, `computed`, `proposed`), the id of a claim of the
  ledger (none for `proposed`), the page labels of its plots and tables,
  the numbers of the assumptions it rests on (indices into the run
  record's assumptions), and its uncertainty in words. `validate` refuses,
  with every problem and the statement it belongs to: an unknown kind; an
  observed or computed statement without a record, with a record the
  ledger does not have, without a plot, without an assumption, or without
  an uncertainty; a proposed statement with a record; an assumption
  number outside the run record. `trace` gives each statement its
  evidence status (`claim_status` after `check`), or "proposed, not
  evaluated".
- **The ledger of the lesson** (in the experiment): the run record (the
  task, the five assumptions of the page, the budget, the digests of the
  code and the questions); one attempt per question of the recorded run,
  with the fixture as its artifact, evaluated by the build's tests; one
  attempt per question of each baseline (no artifact: the build computes
  them); claims linking to those attempts. Nothing environment-dependent
  or digest reaches the page.
- **Statements of the report.** Computed: all predictions within the
  tolerance and all explanations passing; the curve fit outside the
  tolerance on the counterfactual question only; dimensional analysis
  identifies two of the four. Observed: the recorded interval of the
  second question is the widest relative to its prediction (read from the
  recording, replayed). Proposed: a scene where the picture and the given
  values disagree could separate predictions from explanations (marked,
  no record).
- **Tests (acceptance criterion 2).** Every statement of the lesson's
  report resolves to a claim of the ledger or is marked proposed; every
  plot it names is a cell label of the page; the run record's assumptions
  are the page's, in order. Deliberately wrong reports are refused: a
  computed statement without a record, a record the ledger lacks, a
  proposed statement with a record, an observed statement without an
  uncertainty, an assumption number out of range; a changed fixture turns
  the computed statements that rest on it into "not evaluated"; an
  evaluation that contradicts a claim makes it "failed".
- **Deliberate moment.** The self-check is the page's; the extension's
  moments are a prediction before the traced report (which statements rest
  on the recording, and which would stand without it?) and the exercise.
- **Code the learner reads.** `Statement` (exact full source: the schema
  is the concept), `problems` (exact selection of the rules, lines 13 to
  36: validation is the point). The statements of the report and the
  ledger are Source links: the two tables show every field of every
  statement, and the ledger is orchestration whose parts the prose names.
- **Exercise.** Change the recording (a copy of the fixture with one
  interval edited): what happens to each statement? (solution computed).
- **Outcome added.** "Trace each statement of an experiment report to its
  run, data, plot, assumptions, and uncertainty, and mark it observed,
  computed, or proposed".

## Steps

1. This plan and the handoff note.
2. `pbc.verification.constraints` and `faulty_motion`, with tests.
3. SA7's experiment additions, page section, and experiment test.
4. `pbc.evidence.report`, with tests.
5. SA8's experiment additions, page section, and experiment test.
6. Documentation: architecture, project map, discovery protocol.
7. The summary and the completion record.
8. Verification, last: the changed tests and the lesson checks while
   working; `./scripts/verify.sh --base` (changed front matter) at the
   end. The complete `./scripts/verify.sh` is not run in the session.

## Discoveries during the work

- **The cases decide what a check can see.** With every case at a positive
  displacement, the arctangent's fault is visible to the mirror only; from
  a negative start its motion does not even begin at its start, so a limit
  check with such a case would also find it. The page says so under the
  figure, and a test pins that the cases start at a positive displacement.
- **The wrong sign hides from rest.** The first case starts from rest,
  where the wrong sign changes nothing; the limits find it in the second
  case. A test pins that the check stops at the third trial.
- **The missing square root is found twice at the cases' values** (by
  dimensions and conservation), as planned; at k/m = 1 s⁻² only dimensions
  finds it, which the page computes (`unit-ratio-checks`).
- **The exercise's candidate keeps a constant that is not an energy.**
  The division by omega forgotten conserves k (x0² + v0²) / 2, a sum of a
  squared length and a squared velocity; conservation passes and
  dimensions names the fault.
- **The figure language allows two stacked panels, never side by side.**
  The plan's figure shows two witnesses (conservation and the mirror); the
  table holds all five. One legend under the plot for both panels, since
  both use the same encoding (dashed: what the constraint demands; solid:
  the wrong candidate).
- **A claim's assertions are constants.** The ledger of SA8 writes the
  outcome each claim asserts for its runs as constants of the claim, never
  read from the evaluations, so that an evaluation can contradict them
  (the unit test shows a contradicting evaluation failing the statement).
- **An observed statement rests on a raw artifact.** The distinction of
  observed and computed is enforced where it can be: a statement marked
  observed whose claim has no recorded artifact is refused.
- **Nothing environment-dependent reaches the page.** The run record holds
  the digests and the interpreter's version; the page shows only the
  statements, the kinds, the statuses, and the traces.
- **The ledger names files the lesson's digest can follow.** A first
  version used the repository root as the ledger's root and as the base of
  computed paths; the input digest of the lesson then failed ("a path
  constant names the whole repository"), and the selection fell back to a
  full run. The recording and the hashed sources are now literal paths,
  and the ledger's artifacts are named relative to the lesson directory.
- **The changed recording is a copy.** The exercise edits one interval of a
  copy of the fixture in a temporary directory and traces the report
  against it; the repository is not written.

## Where the teaching skill changed the learning experience

- **SA7 opens from the gap the hunt left** (a blind search with a budget)
  and states at once that no model runs in the section, as the AI-evidence
  archetype and F168's finding on AE3 ask (the kind of evidence first).
- **The prediction moment is placed where the counterintuitive point meets
  the evidence:** the frequency in hertz, which escaped the unit check of
  the lesson on verifying scientific code, is put to the learner before the
  table of outcomes, so that the learner meets "dimensions cannot see a
  factor 2 pi" twice and sees which constraint does.
- **Each fault is read against the constraint it breaks,** one sentence
  each after the table, instead of a list of results; the convenient value
  (k/m = 1) is computed, not asserted, echoing SA2's unit mass.
- **"Passing is not a proof" is its own short subsection,** tied back to
  the inconclusive hunt of the page, so the falsification point of the
  lesson holds for the new checks too.
- **AI2's debugging cases are a table mapping constraint kinds,** with the
  one place where a symmetry hides a fault (the stopped clock), rather than
  a link alone.
- **SA8 starts from the reader's problem** (three kinds of statement side
  by side) and asks a prediction before the traced tables (which
  statements rest on the recording?); the exercise (a changed copy of the
  recording) is the interpretation moment: a digest withdraws a status
  without judging the data.
- **Code on the pages.** `symmetry` is shown whole (the two symmetries as
  code are the point); `CASES` as a region (the domain of the hunt, and
  the positive displacements that matter for the mirror); `dimensions` as
  an exact selection of the conversion (lines 9 to 17, with the names
  `case`, `t`, `reference` given in the sentence before); the two wrong
  candidates whole (one plausible line each). `Statement` whole and
  `problems` as a selection of its rules. The drawing function, the
  ledger, and the statements are Source links; `draw_constraint_witnesses`
  was read first: it evaluates the candidates and draws, and computes
  nothing the caption does not state.

## Out of scope

Multi-agent review (F153); research reports (F154); putting a constraint
to the live agent as a claim; changes to the lessons' existing content.
