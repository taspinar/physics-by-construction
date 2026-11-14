---
name: pbc-physics-teaching
description: "Physics by Construction's pedagogical reasoning for a lesson: who the learner is, the central question and the counterintuitive point, the missing steps, one or two deliberate prediction or interpretation moments, the kinds of result kept apart, essential against optional derivations, the lesson's archetype and its learner journey, and why each displayed code block is read where it is. Use when a feature plan selects it because the feature writes or revises a lesson's teaching: its sequence, explanations, exercises, or displayed code."
license: "Project-owned"
---

# PBC Physics Teaching

How a learner comes to understand the physics of a lesson: what to ask
first, which step is missing, where a prediction helps, which derivation
carries the lesson, and why a code block is on the page. This skill is
reasoning guidance for the planner, the implementer, and the reviewer
(ADR 023 decisions 1 and 2). It is never evidence, never a check, and
never a template: lessons do not become alike because of it.

## Who owns what

This file owns the pedagogical decisions only. For everything else it
points to the owner and repeats none of its rules; where this file and
one of them disagree, the owner wins and this file is wrong.

| Question | Owner |
|---|---|
| Sentences, register, openings, transitions, conclusions, the recurring faults of prose | `docs/editorial-voice.md` |
| The required sections, the front matter, claim labels, figure status, the self-check, Go deeper, exercises and hints, numbers in prose, measured data, agent and Lean lessons, what is verified and what is not | `docs/authoring.md` |
| The display forms of code and their checks | ADR 002 and ADR 023 decisions 3 to 7; `docs/authoring.md`, "Code" |
| What a figure shows and how (axes, uncertainty, status, comparison) | `.agents/skills/pbc-scientific-visualization/` |
| Whether a claim is true | the checks and the independent review |

The questions here come before those rules: *what* the lesson must make
understood, and in what order. The owners then say *how* it is written,
labelled, and checked.

## 1. The learner and the question

Write down, before changing anything:

- **The learner at the start.** The lesson's `prerequisites` (lessons and
  `outside`), and what the previous lessons of its path actually
  established, not what they mention. A symbol, a method, or a data
  format the learner has not met is a gap.
- **The central question.** One physical question the lesson answers,
  answerable by its end, and asked in its opening. A topic ("Euler's
  method") is not a question; "how wrong is the program, and how does
  the error shrink?" is.
- **The counterintuitive point.** What the learner would get wrong
  without the lesson (the velocity of explicit Euler is exact under a
  constant acceleration while the position is not; a wrong model still
  returns small standard errors). A lesson with none is often a lesson
  that states rather than teaches.
- **The intended outcome.** What the learner can do afterwards; it should
  match `lesson.outcomes`.

**Gaps.** For each step of the explanation, ask what the learner must
already hold to follow it. Give an abstraction its physical meaning before
its formal use (the state is "what you need to know to say what happens
next" before it is a triple); name each symbol and assumption when it
first carries weight; connect each derivation to something observable or
to an operation of the program. A step that only the author finds obvious
is the missing one.

## 2. The archetype and its journey

Name the archetype before proposing any restructure; the learner's
journey differs, and a change that makes one archetype look like another
is uniformity, not teaching.

| Archetype | The journey | Watch for |
|---|---|---|
| Model or simulation | Question, model and assumptions, method, a check against something known, what the result means, where it stops holding | A simulation shown before the learner knows what it should give |
| Measured-data investigation | The lineage, visible in order: recorded and calibrated values, quality and cleaning, processing, the model, comparison or fit, residuals and uncertainty, the warranted conclusion | Agreement produced by a processing choice read as independent validation |
| Engineering design or capstone | The brief, the constraints, and the success criteria before or beside the method; then a decision or trade-off summary | A chain of numerical checks with no design decision they serve |
| AI agent or evaluation | The kind of evidence stated at once (written example, model transcript, tool replay, recorded run, held-out scoring, independent evaluation); what this lesson adds beyond the earlier agent protocols | A transcript read as a measurement of capability |
| Agent-based model | The individual rule, the collective behaviour it produces, and the check that the behaviour comes from the rule and not from a parameter choice | Emergence asserted from one run |
| Formal proof | Assumptions, theorem, the verified proof, and the exploratory numeric example kept apart; a first proof-writing step the learner can take | A numeric example offered as if it proved the theorem |

A lesson may combine two (a measured lab with a model built first); name
the main one and follow its journey.

## 3. One or two deliberate moments

Choose one or two places where the learner predicts, experiments, or
interprets before being told. Choose where the counterintuitive point
meets the evidence: just before the table, figure, or run that settles
it, after the learner holds everything needed to predict. Ask a specific
question with a checkable answer ("above or below the exact curve?"),
then let the page answer it. Do not sprinkle questions through the prose;
a question the next sentence answers without the learner having to think
is decoration. The self-check of `docs/authoring.md` is usually the
interpretation moment; the other, if any, is a prediction in the prose.

## 4. Five kinds of result, kept apart

A learner must always be able to tell which of these a statement is:

1. a **prediction** of the model, made before the comparison;
2. a **derived property**, proved analytically within stated assumptions;
3. a **simulation output**, what the program computed;
4. a **measurement**, raw, calibrated, or processed, with its lineage;
5. an **inference about reality**, what the comparison warrants.

Agreement of 1 or 2 with 3 says the program implements the model;
agreement with 4 says the model describes the measurement within its
uncertainty and processing; only then is 5 warranted, and only as far as
its scope. The claim labels and figure status of `docs/authoring.md` mark
the kind on the page; this section is about the order of the reasoning,
so the learner meets each kind where it is earned.

## 5. Essential and optional derivations

A derivation is essential when the lesson's question, a later check, or a
later lesson rests on its result or on its method. Keep it in the
explanation, stepwise, with each step's reason. An optional one (a
general bound, a full proof of a result the lesson only uses, a second
route to the same answer) moves to a labelled, linkable depth section; it
is never deleted, and its scope is stated where it is moved from. Never
replace a derivation by "it can be shown".

## 6. Assumptions where they are needed

Keep every assumption and every limitation; change only where the learner
meets it. A long list of technical boundary conditions before any
motivating calculation loses the learner. Keep the complete list where
`docs/authoring.md` requires it, keep its first encounter short, and
recall the assumption at the step that uses it ("the fifth assumption said
round-off is negligible; here is the number"). A recall is a pointer, not
a second statement that could drift from the first.

## 7. Code the learner reads

**Purpose first.** For every displayed code block, state why the learner
reads it at that point: a new physical relationship, a numerical update,
scientific processing or validation, an engineering trade-off, agent
control, a formal proof, or none of these (rendering or housekeeping).
"It generated the next figure" is not a purpose. Record the purpose in
the plan or the review, not on the page.

**The four display choices** (ADR 023; the forms and their checks are
theirs and `docs/authoring.md`'s):

| Choice | Choose it when |
|---|---|
| Exact full source | The code is short or central and its control flow is the point: a stepper, a solver stage, a fit, an allowlist, a proof |
| Exact selection | The lines that teach are a part of a long object: the relevant body, the scientific transformation inside a plotting function |
| Generated signature, or executed teaching code | Only where it demonstrably clarifies; teaching code only where a check of it exists |
| Source link only | Plot formatting, decoration, orchestration, file handling the lesson does not teach |

None is a default for a whole lesson; decide per block.

- **Transformations inside plotting code.** Before making a `draw_*`
  function a Source link, read it: if it computes a residual, smoothing,
  an offset, a calibration, or a binning the conclusion depends on,
  surface those lines (an exact selection, or a separately tested analysis
  function) or state the transformation where the figure is read. Never
  hide the only visible calculation behind a link to shorten the page.
- **Docstrings.** Check whether the prose just before or after already
  says what the docstring says. Show a docstring where it supplies an
  assumption, a unit, an interface meaning, or an insight the prose does
  not; the source keeps it in any case.
- **Types.** Keep complex, array, state, schema, and proof types where they
  are the concept (a quantum state, a dataset artifact, an agent's tool
  schema, a Lean theorem). Drop annotations only in a labelled summary,
  and only when the learner loses nothing needed.
- **Fragments.** A selection is not a runnable whole; do not invite the
  learner to copy one as if it were.
- **Equation and code side by side.** Where an equation becomes code,
  the names should let the learner find each term of one in the other.

## 8. The whole lesson, and its neighbours

Read the lesson end to end, then its predecessor and successor on the
path. Ask whether the question raised in the opening is the one answered
in the conclusion, whether each section needs the one before it, and
whether the transition to the next lesson names what carries over and
what changes. A paragraph-level edit that breaks the sequence is a loss
however good the paragraph.

## Practice distilled from the sources

Exemplars, not authorities; PBC keeps its own voice and objectives. Each
line names where the practice is shown and what this skill takes from it.
Nothing of them is copied here or into a lesson: no diagram, figure, or
passage beyond a short quoted phrase with its citation.

- **Feynman, Leighton, Sands, *The Feynman Lectures on Physics*, Vol. I.**
  Ch. 1, "Atoms in Motion", section 1-2: one fruitful question (what single
  sentence would carry the most knowledge) organises a whole field. Ch. 4,
  "Conservation of Energy", section 4-1: an abstract law introduced through
  a concrete bookkeeping story before its formula. Ch. 9, "Newton's Laws of
  Dynamics", sections 9-6 and 9-7: motion computed step by step from the
  equations, by hand, as part of the physics. Taken: the central question,
  the physical meaning before the formalism, numerical stepping as
  explanation.
- **Chabay and Sherwood, *Matter & Interactions*, 4th ed. (Wiley, 2015).**
  Ch. 1, "Interactions and Motion", and Ch. 2, "The Momentum Principle",
  its iterative prediction of motion: a few general principles applied to a
  chosen system, with the computational update loop as the model itself.
  Taken: the program as the model, the update rule as physics, the system
  and its assumptions named before computing.
- **Taylor, *Classical Mechanics* (University Science Books, 2005).** Ch. 2,
  "Projectiles and Charged Particles", sections 2.1 to 2.4 on linear and
  quadratic air resistance: a derivation developed in small, justified
  steps, each result checked in a limit the reader already knows. Taken:
  stepwise development, the limiting-case check as a habit.
- **OpenStax, *University Physics Volume 1* (2016, CC BY 4.0).** Ch. 3,
  "Motion Along a Straight Line", section 3.4, "Motion with Constant
  Acceleration": worked examples in the steps Strategy, Solution, and
  Significance. Taken: the reasoning visible before the arithmetic, and a
  stated meaning of every result.
- **McDermott, Shaffer, and the Physics Education Group, *Tutorials in
  Introductory Physics* (Prentice Hall, 2002).** Mechanics, "Motion in one
  dimension" (the tutorials on velocity, representations of motion, and
  acceleration in one dimension): elicit a prediction, confront it with
  the evidence, resolve the difference. Taken: the deliberate prediction
  moment placed where a known misconception meets the evidence.
- **MIT OpenCourseWare, 8.01SC *Classical Mechanics* (Fall 2016), and PhET
  Interactive Simulations** (University of Colorado Boulder; Wieman, Adams,
  and Perkins, "PhET: Simulations That Enhance Learning", *Science* 322,
  682, 2008; Podolefsky, Perkins, and Adams, "Factors promoting engaged
  exploration with computer simulations", *Phys. Rev. ST Phys. Educ. Res.*
  6, 020117, 2010). 8.01SC, Week 1, "Kinematics": short concept questions
  between demonstrations and worked problems; PhET: implicit scaffolding,
  an interaction with a goal and few controls. Taken: sequencing a
  demonstration after the question it answers, and interactivity only with
  a purpose.

## Before and after, from PBC

Each states why the change helps comprehension. Lessons are cited by slot
and path; the "after" is a decision, not a change made by this file.

**A prediction the learner makes (M1,
`site/lessons/mechanics/01-kinematics-as-a-program/index.qmd`, "A ball
thrown straight up").** Before: the text states that the velocities will
agree and the positions differ by $-\tfrac{1}{2}a\,t\,\Delta t$, then shows
the table. After: one question first (above or below the exact ball? do
the velocities differ?), the table second. Why: the derivation has just
given the learner what is needed; answering it for them removes the one
moment where they test their reading of the formula.

**A drawing function off the page (M1, the listing of
`draw_state_and_update` before `fig-state-and-update`).** Before: box and
arrow calls between the update rule and its sketch. After: a Source link.
Why: it teaches neither physics nor method, and it interrupts the step
from the equation to its picture. Checked first: it computes nothing.

**A transformation kept on the page (MAT6,
`site/lessons/materials/05-stress-strain-measurements/index.qmd`, and
`draw_elastic_regime` in `src/pbc/materials/experiments/stress_strain_measurements.py`).**
Before: a long plotting function shown whole, or the temptation to replace
it by a link. After: an exact selection of the shift and residual lines
the figure's reading depends on, the formatting behind the Source link.
Why: those lines are the only visible calculation behind the comparison;
a link alone would hide it.

**Leave as it is (AST8,
`site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd`).** The
page follows the measured-data lineage in order (the model checked before
the data, cleaning labelled as a selection, the curved baseline shown and
justified, the fit, residuals against a simpler model, correlated
uncertainties, the sensitivity to the normalisation, an independent
check, and a conclusion that names what no number bounds), and its code
blocks show the transformations the conclusions rest on. Why no change:
moving sections or adding activities would make it resemble other
lessons without making any step clearer.

## Recording the use

- **The plan** of a feature that writes or revises a lesson's teaching
  selects this skill on its `Skills:` line, or records why it is not
  useful on a line `Skills: none (<reason>)`; it names the archetype, the central question, the chosen
  moments, and the purpose of each displayed code block it changes.
- **The implementer** records where the skill changed the learning
  experience (which moment, which derivation moved, which block changed
  form and why), not that it was read; and the digest of
  `PROVENANCE.yaml`.
- **The reviewer** reports named pedagogical weaknesses, each with the
  evidence on the page and an action; never a score, and never a
  criterion of sounding human or of an AI-text detector.
