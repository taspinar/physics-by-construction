# Plan: F152, path 4 of Part B: generating and selecting research ideas (RR1), from a question or publication to a research plan (RR2), literature, novelty assessment, and evidence maps (RR3) (Issue #585)

Source: `docs/roadmap.md`, F152; `docs/changes/part-b-scientific-products-and-research.md`,
B4.1 to B4.3, section 6 (R2, R3), and section 10.1, pilot 4; the owner's
start on #585 (2026-11-20). Written by the implementer at the start of the
work (the Issue expects a detailed plan and none existed).

**Level 2.** Three new lessons (`mechanics` 22 to 24, slots RR1 to RR3,
course mechanics) with their experiments, a new library package
`src/pbc/research/` (`ideas.py`, `plan.py`, `corpus.py`, `literature.py`),
new tests, and additive text in `docs/architecture.md` and
`docs/project-map.md`. No protected path. No existing test assertion, no
existing experiment file, and no published claim of another lesson
changes: the new code imports `pbc.agents.specification` and the
laboratory of SA1 (`pbc.mechanics.experiments.experiment_specification`)
and changes neither. No file is added next to a published lesson page and
no replay fixture is added. If any of these turns out to be needed, the
feature becomes Level 3 and the approval request (.agents/approvals/585.md)
is created.

## One investigation through the three lessons

The three lessons follow one bounded investigation, so that each lesson
adds one competence to a question the learner already holds: the tennis
ball of the projectile lesson (M3) and of SA1, simulated with quadratic
drag in SA1's laboratory (the actions `range_with_drag` and
`range_in_vacuum`, with their units and bounds).

- **RR1** writes candidate questions about the ball, assesses each against
  the laboratory and an archive of what is already answered, keeps the
  proposers' self-ratings beside the assessment without using them, and
  selects one: the slow throw (10 m/s, well below the terminal speed): is
  its best angle within two degrees of forty-five? Every other idea is
  archived with its reason and what would warrant revisiting it.
- **RR2** turns two questions into research plans declared before
  execution: a replication of SA1's published claim at 25 m/s and the
  original question selected in RR1. The plan template is executed by the
  scripted route of SA1, with a positive control, a method baseline, and
  withheld tests that are opened once after the plan is frozen.
- **RR3** compares the claims of these plans and the scaling guess the
  projectile lesson considered before its simulation (drag leaves the best
  angle at forty-five degrees) with a small local corpus of verified passages, distinguishes supporting,
  contradicting, and insufficient evidence, links claims to passages and
  to the assumptions each passage holds under, and shows that a search of
  this corpus cannot certify that the selected question is new.

No model is run in any of the three lessons. The proposer of an idea is a
person (changed during the work: the fixed generator was dropped; the
proposers are the author and a colleague), the executor of a plan is the
scripted route, the retrieval is a lexical baseline, and the annotator of
the corpus is the author of the lesson, stated as such on the page, whose
two records agreeing is reported as consistency, not correctness. Each
page says so in its
opening (F168's gap in AE3: the kind of evidence at once). Path 4's later
lessons (RR4 to RR7, F153 and F154) bring agents into the investigation;
these three lessons set the records an agent's work is held to. Out of
scope, as the Issue says: live retrieval and any agent that writes a
citation. The optional retrieval integration of pilot 4 (PaperQA) is not
built: section 10.1 makes it optional and the Issue allows it "only with
its own comparison"; RR3's limits say what it would have to be compared
with.

## The corpus of RR3 and its rights

The corpus is a set of passages quoted from the site's own published
lessons (M3, SA1, SA5 "An agent runs an experiment", the analysis-pipelines
lesson M10, and two passages from other lessons that do not bear on the
claims): the project's own text under CC BY 4.0 (`LICENSE-CONTENT`), a
licence ADR 007 accepts. It is not a third-party dataset, so it gets no
card under `data/registry/`; each passage records its page, its licence,
and its attribution. Each passage is held in `pbc.research.corpus` as a
quotation with its location, and a test checks every quotation against the
current lesson source (a typed claim through `pbc.authoring.evidence.read_claims`,
with its type and scope; a plain sentence as normalised text of the page).
A change of a quoted page therefore fails the test until the corpus is
updated: the passages are verified, not only cited. The build reads no
other page at run time (the digest of RR3 stays followable).

The reference register enters as the second kind of source: an entry is a
source a person has reviewed for one stated purpose and whose text is not
held locally. RR3 uses `drag-coefficient-regimes` for what it was reviewed
for, the quadratic force law, which is an assumption of every claim on the
page; its reviewed statement is quoted from `site/references.yaml` and
checked by the same test. The register entry's own `alternatives` record a
source that "came up in search and was not opened"; RR3's review log holds
it as a proposed source awaiting human review. Nothing is added to the
register and nothing from the web is read: no live retrieval in the build
or in the authoring.

## Visual deliverables

Scientific figures drawn by the build from the verified code, and
conceptual diagrams drawn with `pbc.authoring.diagrams`; no artwork, no
image file.

Skills: pbc-physics-teaching@7f34987, pbc-scientific-visualization@a70b501, diagram-design@550fd66

- **Artifacts.**
  - RR1 `fig-idea-checks` (`conceptual`): an idea passes through the checks
    the build computes (feasible in the laboratory, falsifiable, within its
    budget, contribution against the archive) and one judgement a named
    person records (interest); the self-rating is drawn beside the idea and
    leads nowhere; every idea ends in the archive.
  - RR1 `fig-idea-assessment` (`simulated`, the preview): ideas against
    the five criteria, each cell a computed outcome told apart by marker
    shape and fill (passed, failed, not reached, a person's judgement),
    and the proposer's self-ratings in a separate column marked "not
    used".
  - RR2 `fig-plan-stages` (`conceptual`): written, checked (refused or
    accepted), frozen with its digest, positive control, the route and the
    baseline, the withheld tests opened once, the verdict; a change after
    the freeze goes to the deviation record.
  - RR2 `fig-plan-results` (`simulated`, the preview): two panels, the
    replication at 25 m/s and the original question at 10 m/s: the route's
    runs, its bracket, the predicted bound, the baseline's grid, and the
    withheld tests in their own marker.
  - RR3 `fig-evidence-chain` (`conceptual`): a claim, the passages a
    retrieval proposes, the label the annotator's reading gives each, the
    assumptions each passage holds under, and the source behind an
    assumption; the proposals nobody read stay in the review log.
  - (Changed during the work: the idea keys carry no digits, `replication`,
    `slow-throw`, `middle-throw`, `fast-throw`, because the prose and alt
    text checks read a digit as a typed number.)
  - RR3 `fig-retrieval-ranks` (`simulated`, the preview): for each claim
    the lexical score of every passage of the corpus in rank order, the
    marker by the annotated label, the cut-off of the search drawn.
- **Scientific validation.** Every number is computed by the build: the
  route's runs through the allowlist of SA1, the plan's checks and
  withheld tests, the assessment of every idea, the retrieval scores and
  labels. Tests assert each stated result and the agreement of page and
  results (`assert_the_page_and_the_results_agree`); the lesson-source
  checks, the single-page renders, and the independent review.
- **Accessible fallback.** Every figure has a caption that states its
  conclusion and an alt text without computed values; the numbers of every
  simulated figure are also in a result table on the page; no script is
  added.

## The learner and the subject (pbc-physics-teaching)

**Archetype: AI agent or evaluation** for all three (the evaluation of
research decisions: what counts as evidence for choosing a question, for a
plan, and for a claim). No lesson has a recorded model run; each opening
says what kind of evidence the page shows: computations of the build on
written ideas and plans, and the annotator's readings, which a test checks
against the quoted text. Prerequisites: SA1 (`experiment-specification`)
for all three; RR1 for RR2, RR2 for RR3.

### RR1, Generating and selecting research ideas

- **Learner.** Has done SA1 (the seven-part specification, the scripted
  route, a verdict that can be "refuted") and M3 (the ball, the terminal
  speed). Knows that a specification is checked before it runs.
- **Central question.** Several questions about the ball could be asked
  next. Which one is worth the next runs, and on what evidence can that be
  decided before any of them has been run?
- **Counterintuitive points.** (a) The proposer's confidence in an idea is
  no evidence of its quality: the idea its proposer rated most feasible
  cannot be run in the laboratory, and one rated highly is unfalsifiable as
  written. (b) Most of the choice can be computed before any run (what the
  laboratory permits, whether a result could contradict the prediction,
  how many runs the route needs, what the archive already answers), and
  what cannot be computed (interest) is recorded as a named judgement, not
  as a score. (c) A rejected idea is a result: archived with its reason
  and the condition for revisiting it.
- **Ideas** (`pbc.mechanics.experiments.generating_and_selecting_research_ideas`):
  seven, written as SA1 specifications where the laboratory can express
  them, each with its proposer (the author of the page, a colleague, or a
  fixed generator that varies the launch speed of SA1's question) and
  their self-ratings: SA1's own question at 25 m/s (answered), SA1's
  exercise at 40 m/s (answered), the slow throw at 10 m/s, a throw at
  15 m/s, a question about spin (no action of the laboratory), the best
  angle "below sixty degrees" (cannot be contradicted inside the range),
  and SA1's question at a hundredth of a degree with a budget of twenty
  runs (the route needs more).
- **Computed** (`pbc.research.ideas`): feasibility by `parse` against the
  laboratory; falsifiability by whether the predicted bound lies inside the
  varied range by at least one resolution from each end; resources by the
  number of runs the route makes for the specification, counted from its
  procedure without running it (`runs_needed`), against the stated budget;
  contribution against an archive of answered questions (the published
  answers of SA1 and the formula without drag): a replication, an
  extension, or not answered in this archive. Interest is a judgement with
  its author and reason. Selection by a rule declared before the
  assessment: every check passed, then the contribution, then the fewest
  runs, then interest. The self-ratings are an argument of nothing that
  selects; a test shuffles them and the selection is unchanged.
- **The archive.** An append-only record: every idea with its assessment,
  its decision (selected, rejected, deferred), the reason, and the
  condition that would warrant revisiting it; each entry carries the
  digest of its idea and the digest of the entry before it, so that an
  edited or deleted entry is found (`verify_archive`).
- **Moment.** A prediction before the assessment table: "which of the
  seven ideas will the checks remove, and is it the ones their proposers
  rated lowest?" The self-check on what a self-rating is evidence of.
- **Code shown and why.** `ideas.falsifiable` (exact full source: the
  check's rule is the point, validation); `ideas.runs_needed` (exact full
  source: resources computed from the route's procedure without running
  it, validation); `ideas.select` (exact full source: the declared rule;
  its signature takes no self-rating, which is the point); `Archive.add`
  (exact selection of the chaining lines, validation). An idea of the
  experiment as an exact region. Drawing functions are Source links (they
  compute nothing: every cell is an assessment of the table).

### RR2, From a question or publication to a research plan

- **Learner.** RR1 (the selected idea and the archive), SA1.
- **Central question.** Before the first run of an investigation, what has
  to be fixed so that its result can count, whether the question comes
  from a publication to replicate or from an idea of one's own?
- **Counterintuitive points.** (a) A plan that already contains a
  specification is still not enough: without a test the search never saw,
  the search's own record is the only check of its answer, and without a
  stopping condition the budget is chosen by the results. (b) A positive
  control with a known answer is what tells "the hypothesis is wrong" from
  "the method is broken". (c) A replication repeats the published
  procedure and compares with the published claim, not with the
  replicator's expectation; agreement of a reproduction with its original
  shows that the record is complete, not that the claim is right.
- **The template** (`pbc.research.plan`): seven parts, `PLAN_PARTS`: kind
  (replication or original) and source (the published claim and its
  passage, or the archive entry of the idea), the specification (SA1's
  seven parts, parsed by SA1's `parse`), baselines (a positive control on
  `range_in_vacuum` with its known answer, and an even grid with the
  route's budget), withheld tests (a finer scan at a time step the route
  never uses, on angles it never tries, with its own budget), success
  criteria (the route's criteria, the control, the withheld tests), and
  stopping conditions (the route's budget, the whole plan's budget, and
  stop when the positive control fails). `check` refuses a plan without
  withheld tests, without stopping conditions, with a withheld test the
  search could see (its time step is one the route uses), or with budgets
  that do not add up, with every problem at once (criterion 3).
- **Execution.** `freeze` writes the plan's digest before any run;
  `execute` runs the positive control, the route of SA1 on the
  specification, the baseline, and then the withheld tests once, and
  returns a record whose verdict is given only when every criterion is
  met. A plan changed after the freeze is found by its digest and its
  result is reported as a deviation, never as the plan's result.
- **Worked examples.** The two refusals (no withheld test; no stopping
  condition); the replication of SA1's claim (same procedure, the
  published bracket reproduced, the withheld test passed, the claim
  compared); the original question at 10 m/s (supported or not by its
  prediction, decided by the build); a deviation (the prediction moved
  after the result).
- **Moment.** Before the original plan's result: "the positive control,
  the route, and the withheld test: which of them could fail here, and
  what would each failure mean?" The self-check on a replication that
  agrees.
- **Code shown and why.** `plan._withheld` (exact full source: the rule
  that a withheld test uses nothing the search sees, validation);
  `plan._stopping` (exact full source); `plan.execute` (exact full source:
  the order of the stages and the one opening of the withheld tests is the
  control flow); the plans of the experiment as exact regions. Drawing
  functions are Source links.

### RR3, Literature, novelty assessment, and evidence maps

- **Learner.** RR2 (two claims with their plans), RR1 (the archive), M3.
- **Central question.** What does the existing literature say about these
  claims, and can a search show that a question has not been answered?
- **Counterintuitive points.** (a) A passage that names the same
  quantity can still say nothing about the claim: "forty-five degrees"
  holds without air, and a passage about a baseball says nothing about a
  tennis ball; the label belongs to the claim, the passage, and the
  assumptions together. (b) Lexical retrieval ranks the passages that
  share words with the claim, not the ones that decide it, and writes
  numbers and names in other forms than the claim ("forty-five degrees",
  "$45^\circ$", "flatter"). (c) "Not found" is a property of the search,
  not of the world: the corpus, its size, and the retrieval's recall on
  claims whose answers are known bound what an empty result means; it
  never certifies novelty.
- **The labels** (`pbc.research.literature`): the annotator's reading of each
  passage in a structured form (the quantity, the ball, the drag, the
  speed, the bound the passage gives), and `label(claim, reading)` that
  returns supports, contradicts, or insufficient with the reason (another
  assumption, another quantity, a bound that does not decide). The
  annotator also recorded the label of every pair directly; a test checks
  the computed labels against those annotations, pair by pair
  (criterion 2).
- **Retrieval baseline.** TF-IDF with cosine similarity over the corpus,
  no stemming, fixed tokenisation; top three per claim; recall of the
  decisive (supporting or contradicting) passages at that cut-off against
  the annotations. Every retrieved item is written to a review log with
  its status: a verified passage with its label, or a source awaiting
  human review (the register's unread proposal); the log is a table of the
  page and a record of the results, and nothing in it is accepted by the
  program.
- **Novelty.** For the selected idea: no decisive passage; the corpus
  holds the direction of the idea (a slow ball hardly notices the air)
  as insufficient evidence for its bound, so the contribution is the
  number, not the idea; the statement is "not found in this corpus of
  N passages, searched with a recall of r on the annotated claims",
  never "new".
- **Evidence map.** A table: each claim, each decisive passage with its
  label, its lesson, and its assumptions, and the register source behind
  the quadratic drag assumption; the site's evidence map (F19) lists the
  quoted claims of the other lessons with their own evidence, and the
  page points to it.
- **Moment.** Before the labels: "the passage 'Without air the answer is
  forty-five degrees' and the claim that the best angle at 25 m/s lies
  below 44 degrees: support, contradiction, or neither?" The self-check
  on an empty search.
- **Found while writing.** The test that compares the computed labels with
  the direct annotations caught one slip of the annotator: the projectile
  lesson's passage on the ratio of the launch speed to the terminal speed
  contradicts the scaling guess, and was first annotated insufficient. The
  annotation was corrected; the reading was right.
- **Code shown and why.** `literature.label` (exact full source: the
  rule, assumptions first, validation); `literature.retrieve` (exact full
  source: the baseline is short, its tokeniser is the reason for its
  failures); a passage of `corpus` as an exact region (what a verified
  passage holds). Drawing functions are Source links.

## Steps

1. `pbc.research.ideas` and tests.
2. `pbc.research.plan` and tests (criterion 3: refusals and execution).
3. `pbc.research.corpus` and `pbc.research.literature`, tests: quotations
   verified against the lesson sources and the register, labels against
   the annotations, retrieval (criterion 2).
4. The three experiments and their tests.
5. The three pages.
6. `docs/architecture.md` and `docs/project-map.md`: the new package, one
   entry each, added at the end.
7. Lesson-source checks, the changed tests, the replay tests, the skills
   check, the single-page renders and their page checks; then
   `./scripts/verify.sh --base` with `VERIFY_JOBS=2` last (new lessons).

## Acceptance criteria and where they are met

1. Lesson and agent rules, outcomes: the three pages, their front matter,
   the lesson-source checks, the experiments' tests; no model is run, and
   each page states its kind of evidence.
2. RR3's labels against the annotated passages, the quotations against
   the sources, no live retrieval, the review log: tests of
   `pbc.research.literature` and `pbc.research.corpus`.
3. RR2's template executed by the scripted route and refused without
   withheld tests or stopping conditions: tests of `pbc.research.plan`
   and of RR2's experiment.
4. The verification the targeted run reports (here `--base`), run last.
