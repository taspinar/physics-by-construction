# Plan: F153, Path 4: RR4 reproducible and resumable research pipelines; RR5 multi-agent investigation and scientific review (Issue #586)

Source: `docs/roadmap.md`, F153; change request section 3.4 (B4.4, B4.5)
and section 6 (R1, AI4, R4); ADR 004 (agents replay, never call a model
in the build); ADR 022 decision 6 (the evidence contract); ADR 023
decision 2; the session instructions on Issue #586. Written by the
implementer at the start of the work.

**Level 2.** Lessons, `src/`, tests, and documentation. No protected path,
no ADR, no CI workflow, no check of `scripts/verify.conf`, no dependency.
No existing test assertion changes: the experiment tests of both lessons
keep theirs and gain new tests in new test functions; the new modules have
new test files. The published claims of both lessons do not change: their
text, numbers, tables, figures, claim labels, and exercises stay as they
are, and the feature only adds to the pages (outcomes appended, a clause
appended to each description, new sections, one limit and one exercise
each). No file is added next to either page: RR5 reads the recordings of
AE6 from that lesson's directory, where they are. `pbc.agents.review_lab`
is used as F150 left it and is not changed. Every new threshold lives in a
new module, never in an existing experiment file (the tolerance trigger).
If any of this stops being true, the feature becomes Level 3 and the
approval request of Issue 586 is created.

## What is delivered

| Part | Where |
|---|---|
| RR4, the extension of `automated-analysis-pipelines` | a new level-2 section `## A pipeline that can stop and resume {#resumable-pipeline}` of `site/lessons/mechanics/10-automated-analysis-pipelines/index.qmd`, before "Limits"; one outcome added (five in all, the most a lesson states); the description gains a clause; one limit and one exercise added |
| The resumable pipeline | `src/pbc/evidence/resumable.py`: stages, branches, the state file of each stage, the run, the resume with its refusals, the fork with its rule, the lineage, all on a `pbc.evidence` ledger; tests `tests/unit/test_evidence_resumable.py` |
| RR4's pipeline | `src/pbc/data/flume_stages.py`: the four stages of the flume analysis (load, window, estimate, report) and the branches of the lesson; tests in the same new test file |
| RR4's experiment | additions to `src/pbc/mechanics/experiments/automated_analysis_pipelines.py` and new tests in its test file |
| RR5, the extension of `scientific-review` | a new level-2 section `## Roles, a human step, and checks instead of votes {#investigation-roles}` of `site/lessons/agents-llm/03-three-reviewers/index.qmd`, after the worked examples and before "Exercises"; two outcomes added (five in all); the description gains a clause; a "Limits" item list is absent on this page, so the new limits are stated in the section; one exercise added |
| The roles and the human step | `src/pbc/agents/investigation.py`: the interfaces of the extraction, implementation, and review roles and of the human, a board that refuses what an interface does not allow, the checked extraction of the claim from the handover, the steering actions and their rule, the decision of the investigation, and the vote against the recomputed check on the replayed panel; tests `tests/unit/test_investigation.py` |
| RR5's experiment | additions to `src/pbc/mechanics/experiments/scientific_review.py` and new tests in its test file |
| Documentation | `docs/architecture.md` and `docs/project-map.md` (the new modules, appended at the end of rows or entries); `docs/discovery-protocol.md` (a short subsection on resumable runs and on roles) |

## Visual deliverables

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@550fd66

| Deliverable | Class | Cell | Validation | Accessible fallback |
|---|---|---|---|---|
| How far each alternative branch moved the RMS elevation, in standard errors of the main branch, with the threshold of the negative claim, and the failed branch marked where its window would end | Scientific figure, `processed`, dataset `aalborg-submerged-bar`, artifact `processed-measured` (it declares its provenance, Issue #531) | `fig-branch-shifts`, RR4 | every value is read back from the state files the ledger digests, never recomputed for the figure; a test compares the plotted values with the estimates of the branches | alt text; the lineage table and the table of the branches |
| The roles of the investigation: handover, extraction, implementation, the three reviewers, the build's recomputed checks, the human step, and the decision, with what each role receives and returns | Conceptual diagram, `conceptual`, `pbc.authoring.diagrams` | `fig-investigation-roles`, RR5 | a sketch: it carries no computed value; its boxes and arrows are the interfaces of `pbc.agents.investigation.INTERFACES` (a test checks that every role of the interfaces is drawn) | alt text that states the insight; the table of interfaces |

The previews of both lessons do not change. No animation, widget, or page
layout.

## RR4: a pipeline that can stop and resume

- **Learner.** Has the page: the analysis as a function, the sweep, the
  report and its committed expectation, the window as the dominant
  uncertainty of the flume result. Has met the evidence contract's ledger
  only by name (the prerequisite of the page is the drag lesson); the
  section introduces the three records it uses (attempt, artifact digest,
  claim) in one paragraph.
- **Central question (of the extension).** A long analysis is stopped (a
  crash, a laptop closed) and started again, or tried with another choice.
  How can the second start be sure it continues the first, and how does a
  reader find which data, code, and choices a number came from, including
  the branches that failed or said no?
- **Counterintuitive points.** (a) Resuming is the dangerous step, not
  stopping: a resume that silently picks up a state written by older code
  or an edited file mixes two analyses, and its report still looks
  complete. (b) A failed branch and a negative result are evidence and
  stay in the record; deleting them makes the surviving branch look
  chosen in advance. (c) A branch may share the earlier stages of its
  parent only if those stages did not read the choice it changes; the
  rule is checked from what each stage declares it reads.
- **Archetype.** Measured-data investigation (the page's own), with the
  pipeline's records as the subject; the lineage of the flume result
  (record, window, estimate, report) is the order of the stages.
- **The pipeline** (`pbc.evidence.resumable`, generic; the flume stages
  in `pbc.data.flume_stages`): a stage has a name, the keys of the
  configuration it reads, and a function from the previous stage's output
  and those keys to a JSON-able output. Running a stage writes its state
  file `<branch>/<stage>.json` under the ledger's root (the stage, the code
  digest, the configuration it read, the digests of its input, and the
  output) and records an attempt in the `pbc.evidence` ledger: id
  `<branch>/<stage>`, candidate = branch, prior = the attempt it follows,
  the state file as its derived artifact. A stage that raises is recorded
  as a failed attempt with its reason, and the run stops.
- **The flume stages.** `load` (reads the data file name; records the
  file's digest and the span of its time axis), `window` (reads the
  window; refuses a window outside the record; RMS and period of each
  repetition), `estimate` (mean and standard error of both, and the period
  resolution), `report` (the first six lines of the published flume
  report, as `pbc.data.pipeline.Report` renders them).
- **Branches.** `main` (the published window, 5 to 14 s); `end-10` and
  `end-12` (shorter windows, forked after `load`, which reads no window);
  `end-40` (a longer window for a finer period resolution, forked after
  `load`; it fails at `window`: the record ends at 30 s). The lineage of an
  attempt is the chain of its `prior` back to the first stage.
- **Resume, and what it refuses.** `resume(branch)` re-reads every state
  file of the branch's lineage and continues after the last completed
  stage. It refuses, naming the cause: a state file whose digest is not the
  recorded one (an edited or deleted file); a state written by other code
  (its code digest is not the current one); a configuration that differs
  from the one the state records (a changed choice is a new branch, never a
  resume); a branch whose last attempt failed (the failure is kept, not
  retried with the same choice); a data file whose digest changed. A fork
  is refused when a stage it would share read a key the branch changes.
- **Reproducible.** A run stopped after `window` and resumed gives state
  files with the same digests as an uninterrupted run in another root, and
  the report of `main` equals the first six lines of the committed
  expectation `reports/expected/flume-waves.txt`.
- **Claims connected, failed and negative results kept.** Two claims in
  the ledger, each evaluated by the evaluator from the state files:
  "the resumed main branch reproduces the published report" (runs:
  `main/report`; the evaluation compares the report lines with the
  committed expectation; status completed), and the negative claim "the
  RMS elevation does not depend on the end of the window, within two
  standard errors of the main branch" (runs: `end-10/estimate`,
  `end-12/estimate`; status failed). The failed branch stays in the
  ledger as a failed attempt. The ledger's summary is shown with every
  status counted. The figure and the report are named as the claims'
  sources.
- **Tests (acceptance criterion 2).** A resume from each invalid state is
  refused with the cause named (edited state file, deleted state file,
  other code, changed configuration, failed last attempt, changed data);
  a fork after a stage that reads the changed key is refused; the lineage
  of every branch's last attempt ends at `main/load`; the failed branch is
  in the ledger with its reason; the resumed run equals the uninterrupted
  one by digest; the main report equals the committed expectation's
  lines; the negative claim's status is failed.
- **Deliberate moment.** Before the table of resumes: of five attempts to
  resume, which does the pipeline allow? (Only the one from an untouched
  state.) The self-check of the page stays the interpretation moment.
- **Code the learner reads.** `State` (exact full source: the record of a
  run state is the concept); `Research.problems` (the region `problems`
  of the class, the whole method: every check is the point); `Research.fork`
  (the region `fork`: the rule on shared stages); `window` of `flume_stages`
  (exact full source: the guard that makes the long branch fail is a
  physical one, the record's span). The experiment functions that run the
  branches and build the tables: Source links (orchestration). The drawing
  function: Figure source (it reads values and draws; it computes nothing
  the caption does not state).
- **Exercise.** Resume `end-12` after its `window` state file is edited by
  one character: what is refused, and what must be done instead?
  (solution computed by the experiment, in a temporary directory.)
- **Outcome added.** "Record each stage of a pipeline as a state that
  names its data, code, and configuration, resume only from a state that
  is still valid, and keep failed branches and negative results with their
  lineage" (one outcome: a lesson states five at most).

## RR5: roles, a human step, and checks instead of votes

- **Learner.** Has the page: three reviewers with bounded allowlists, the
  recomputed checks, the rule that a failed check stands. Has not met
  AE6's panel; the section introduces its four recorded sessions in one
  paragraph as replayed traces, recorded for another lesson.
- **Central question (of the extension).** A review is one part of an
  investigation: someone extracts the claim from what was handed over,
  someone implements, someone reviews, and a person decides what to do.
  What may each role see and write, where does the person's decision
  belong, and why is the answer of several reviewers not their majority?
- **Counterintuitive points.** (a) A role that sees too much can tune to
  the next one: an implementer that reads the reviewers' verdicts can
  write code that passes the checks that were run. (b) The human step is
  meaningful when it changes the question (the claim, the scope, the next
  action), and it is refused when it tries to change an answer (a
  recomputed check). (c) A vote of four replayed reviewers ties on three
  of eight cases, and dropping one reviewer turns the tie into a wrong
  majority; the recomputed check gives the same answer in every
  composition that still runs it.
- **Archetype.** AI agent or evaluation; the kind of evidence stated at
  once: the extraction and implementation roles are played by the
  author's code here, the review role by the recorded models of the page,
  the vote by AE6's recorded sessions replayed; no model runs.
- **The interfaces** (`pbc.agents.investigation.INTERFACES`): extraction
  reads the handover and writes the claim; implementation reads the claim
  and writes the pieces; review reads the claim and the pieces and writes
  the verdicts (recomputed by the build, never the reviewers' words); the
  human reads everything and writes only steering. The board refuses a
  read or a write outside the interface, and a second write of a field
  (append-only; a correction is a steering entry).
- **Extraction checked.** The extracted claim names, for each property,
  the words of the handover it rests on; a quote the handover does not
  contain is refused (an invented property), and the claim must be the
  claim the recorded reviewers were given (`review_lab.CLAIM`), or the
  replay does not review it.
- **Steering.** Actions: `accept` a piece (refused while a recomputed
  check that applies to its claim failed), `send-back` a piece to
  implementation with the failed checks as the reason, `narrow` the claim
  of a piece (drop a property, with a reason; recorded, and the original
  claim stays rejected), `require` a check no reviewer ran before any
  acceptance. No action can set a verdict. On the page: the human accepts
  piece 1, tries to accept piece 2 (refused), and sends piece 2 back; an
  exercise narrows piece 2's claim to first order only for a short run.
- **Not a vote, on a replayed trace (acceptance criterion 3).** The four
  recorded panel sessions of AE6 are replayed (`review_lab.replay_panel`)
  and their `decide` calls counted as votes, case by case, for the panel
  of four and for each panel of three; the recomputed checks decide by the
  contract's rule (`pbc.evidence.reviewers.contract_rule`). Case 6 is
  piece 2 of this page. Tests: the four-way vote ties on cases 1, 4, and
  6; a panel of three gives a majority that accepts a faulty case; the
  recomputed decision rejects every faulty case in every panel of three.
- **Deliberate moment.** Before the vote table: four reviewers, two say
  accept and two reject piece 2; what does a vote give, and what does
  dropping one physics reviewer give? The table answers.
- **Code the learner reads.** `INTERFACES` (the region `interfaces` of
  the module: the bounded interfaces are the concept); `Board` (exact full
  source: the refusals of a read and a write); `steer` (exact full source:
  the rule that refuses an acceptance against a failed check). `votes` and
  `checked` stay behind the Source link of the module: the table and the
  prose state what they count. The drawing function of the diagram:
  Figure source.
- **Outcomes added.** "Give the roles of an investigation bounded
  interfaces, and say what each may read and write"; "Place a human
  decision where it changes the question, and decide a disagreement by a
  recomputed check rather than a vote".

## Steps

1. This plan and the handoff note.
2. `pbc.evidence.resumable` and `pbc.data.flume_stages`, with tests.
3. RR4's experiment additions, figure, page section, and experiment tests.
4. `pbc.agents.investigation`, with tests.
5. RR5's experiment additions, diagram, page section, and experiment tests.
6. Documentation: architecture, project map, discovery protocol.
7. The summary and the completion record.
8. Verification, last: the changed tests, the replay tests, `python -m
   pbc.skills`, the format-2 and evidence-map page checks while working;
   `./scripts/verify.sh --base` with `VERIFY_JOBS=2` at the end (changed
   front matter). The complete `./scripts/verify.sh` is not run in the
   session.

## Discoveries during the work

- **A lesson states five outcomes at most.** The learning-path check
  refuses a sixth, so RR4 adds one outcome that covers both the resume and
  the kept failures.
- **A method is not excerpted by itself.** `excerpt` takes a top-level
  function or class; the checks of `Research.problems` and the rule of
  `Research.fork` are shown as regions of the class, as AE4 shows
  `Ledger`'s `add-final`.
- **The panel's votes and checks.** Replayed, the four sessions of AE6
  tie on the three faulty cases 1, 4, and 6; in each panel of three the
  majority accepts a faulty case for two of the three (6 of 15 votes),
  while the recomputed checks reject all three cases in every panel
  (`clock`, `purity`, `bounded-energy`). The panel replay takes about two
  seconds.
- **No new threshold in an existing experiment file.** The two standard
  errors of the negative claim live in `pbc.data.flume_stages` (`WITHIN`);
  the trigger scan of `scripts/lib/risk.sh` on the working tree reports
  nothing, and the path minimum is Level 2.
- **The state files live in a temporary directory of the build.** The
  figure receives the values, not the investigation, so it is drawn after
  the directory is gone; nothing environment-dependent (a path, a digest)
  reaches the page.
- **Section anchors.** The new headings carry their own anchors
  (`resumable-pipeline`, `stages-and-states`, `what-a-resume-refuses`,
  `pipeline-claims-and-branches`, `investigation-roles`,
  `roles-and-interfaces`, `the-human-step`, `not-a-vote`); the result
  tables are labelled `pipeline-*`, `role-interfaces`, and
  `vote-against-checks`, so no heading reuses the anchor of a cell or a
  claim (checked in the single-page renders).

## Where the teaching skill changed the learning experience

- **Both sections open on their question and state the kind of evidence
  at once** (the AI-evidence archetype and F168's finding on AE3): RR5
  says in its second paragraph which parts are the author's code, which
  are recorded models replayed, and that no model runs.
- **The prediction moments sit where the counterintuitive point meets the
  evidence.** RR4 asks which of five resumes the pipeline allows just
  before the table that answers it (only the untouched one; a reasonable
  change of window is refused as a resume). RR5 asks what a vote of four,
  and of three, gives on piece 2 just before the vote table.
- **The code shown is the rule, not the orchestration.** The state record,
  the resume checks, the fork rule, the window guard, the interfaces, the
  board's refusals, and the steering rule are on the page; the functions
  that run the branches, build the tables, and draw are Source links, and
  each drawing function was read first: `draw_branch_shifts` computes
  nothing (the shift comes from `flume_stages.shifts`, named in the
  prose), and the diagram is a sketch.
- **Failure and negative results are taught as evidence**, not as a
  footnote: the failed branch is a row of the lineage table and a mark in
  the figure, and the failed claim is a row of the claims table beside the
  one that holds.
- **Each exercise asks for the honest next move** (an edited state is a
  new branch; a narrowed claim keeps the failed check in the record), so
  the interpretation is the learner's, with the computed solution after.
