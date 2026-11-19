# Teaching calibration on four lesson archetypes (F168)

The record of F168 (Issue #553): the teaching skill
(.agents/skills/pbc-physics-teaching/SKILL.md) and the code-display policy
of ADR 023 tried on four lessons that are not simulations, to find what the
mechanics pilots taught that carries over and what does not. It is a
source-only diagnostic. No lesson was changed, no rendered page was
inspected, and no learner was observed: every finding is a reading of the
lesson source and of the code it displays, made on 2026-11-18 against
`main` at `a794daf`.

The pilots are F165 (M1), F166 (M3), and F167 (M5). Their method, as the
owner accepted it on Issue #545 on 2026-11-16, is: open with the physical
question; let the learner predict before the evidence; give a small first
calculation before the general analysis; move optional derivations to a
labelled depth section, and say in the lesson header that the mathematics
of that section (for M5, complex numbers and matrices) is needed only
there; show the code that carries the method and link the drawing code.
The owner added three improvements that apply to every lesson of the
rollout: coupled formulas stacked on narrow screens (the `equation-pair`
of `docs/authoring.md`, "Equations"), the chart and its controls directly
after the prediction question, and distinct words for two Source links
that stand alone next to each other. Each map below records whether its
lesson shows these gaps, and whether the header note of M5 would apply.

## The four lessons

| Archetype | Lesson mapped | Compared with |
|---|---|---|
| Measured-data investigation | AST8, `site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd` | Not mapped: MAT6, whose code display the skill's own example and the code-selection pilot F176 already treat |
| Engineering design or capstone | EM9, `site/lessons/electromagnetism/07-adaptive-phased-array-beam-steering/index.qmd` | T11, `site/lessons/thermodynamics/09-thermal-engineering-of-an-ai-accelerator/index.qmd`, for where each states its requirements |
| AI agent or evaluation | AE3, `site/lessons/agents-llm/13-agent-versus-non-agent-baselines/index.qmd` | |
| Formal proof | `site/lessons/lean/04-lean-exercises-on-your-machine/index.qmd` (a lesson beyond the baseline, without a slot label) | The Lean lessons before it, for the tactics it assumes |

## Measured data: AST8, exoplanet light curves

**The journey.** The learner follows a measurement through its lineage: the
calibrated flux as released, the selection that cleaning makes, the
processing that turns each transit into a normalised dip, the model and its
fit, the residuals, the uncertainty and what does not bound it, and a
conclusion that claims no more than the comparison warrants. The question is
not "what does the model give?" but "does the model describe these data,
and how well do the data determine its numbers?".

| Element | Where and what |
|---|---|
| Physical question | In the opening, as three questions: does the transit model describe the dips, which radius ratio, impact parameter, depth, and duration it gives and how well they are known, and what the model does not explain. The conclusion, "What the lab shows", answers all three |
| Prerequisite bridge | The opening recalls what the exoplanet transit lesson established and what it could not (the model agreeing with the program, not with a star). The outside prerequisites (a weighted least-squares fit with its covariance and chi-square; first-order propagation of uncertainty) are needed for the main results, not for an optional section |
| First observable | The light curve as the file gives it (`fig-light-curve`), "the dips are visible without any model". It is the first figure, but the learner reaches it after the five assumptions, the explanation of cleaning, the baseline, the model and the covariance propagation, two code listings, the model check, the data card, and the cleaning code and table |
| Main derivation | The projected distance of the planet, the flux as a sum over rings, and $\sigma_g = \sqrt{J C J^\mathsf{T}}$ with the reason the off-diagonal terms matter (a smaller orbit and a more central crossing give nearly the same dip). All three are essential: the results rest on them |
| Role of the code | The ring model (`limb_flux`, a new physical relationship), the propagation through the covariance (`propagate_correlated`), the cleaning, the phase curve, one transit's baseline, the fit and the uniform-star fit (scientific processing and validation). No drawing function is shown. `geometry_table` (34 lines) and `sensitivity_table` (44 lines) are shown whole, though in `geometry_table` only the call to the propagation and the scaling by the square root of the reduced chi-square compute anything; the rest records a table |
| Evidence and limits | Each kind of result is kept apart and labelled: the model checked against the closed forms before the data (numerically verified), the cleaning counts and the dips (observational), the fit, the uniform star, the mid-times, the sensitivity, and the density check (experimentally supported). The sensitivity table is said not to be an uncertainty interval; the conclusion names what no number on the page bounds (the pipeline's corrections) |
| Exercises | A self-check that asks which of three numbers says how well $b$ is known (the interpretation moment, placed after all three are on the page); the planet's radius from $p$ and the catalogue radius; the precision of the period from the spread of the transit numbers |

**Good practice.**

- The lineage is visible and in order inside the worked examples: model
  check, raw light curve, cleaning as a labelled selection, the curved
  baseline shown by the phase curve before it is used, the fit, residuals
  against a simpler model, correlated uncertainties, the sensitivity to the
  normalisation, an independent check. The skill's "leave as it is" verdict
  on the sequence holds.
- The counterintuitive point is made with evidence: "fitting the wrong model
  still returns numbers, with small standard errors, and only the residuals
  show that they mean little".
- The uncertainty is honest in layers: the standard error, the scaled error,
  the excess scatter of the mid-times, the sensitivity, and the systematic no
  number bounds.
- The code shown is the science; the drawing code is not on the page.

**Gaps.**

- The first observation comes late. The required sections put the
  explanation of the processing and two code listings (the ring model, the
  covariance propagation) before the learner has seen one cadence, and
  assumption 5 (a parabola as baseline) before the phase curve that
  justifies it. The order inside the worked examples is right; the order of
  the sections around them is the template's.
- `geometry_table` is a table-recording function shown whole for the few
  lines that compute. The skill's rule on transformations inside plotting
  code applies to it in the same way.
- **Owner's gaps.** Coupled formulas: yes, twice. The projected distance with
  its phase and inclination, and the standard error with its Jacobian, are
  each one display joined by `\qquad`. Chart directly after the prediction:
  not applicable (no interactive figure, no prediction question). Two Source
  links alone side by side: no (every Source link sits under its listing).
  Header note: not applicable. The lesson has no depth section, and its
  outside prerequisites are needed for its main results; a note that they
  are "needed only for the depth section" would be false.

## Engineering capstone: EM9, adaptive phased array, compared with T11

**The journey.** The learner starts from a brief: what the design must
achieve, under which constraints, and how success is judged. The method is
there to serve the brief, each check answers a design question, and the end
is a decision with its trade-offs and its conditions. Checking the model
against closed forms comes before any design conclusion, as in a simulation
lesson, but the reason for checking is that a decision will rest on it.

| Element | Where and what |
|---|---|
| Physical question | In the opening, as a motivation (a beam steered by phases, not by motors) and a promise to "turn a set of requirements into a design decision". The design question itself, what this array must do, is not stated in words anywhere on the page |
| Prerequisite bridge | Named explicitly: the interference lesson (two sources), the antenna lesson (pattern multiplication and the array factor). Complex numbers and the mean and variance of a random variable are needed in the explanation and in the error studies that decide the number of bits: the main line, not a depth section |
| First observable | The steered pattern against the closed form (`fig-steered-pattern`), the first figure, after the explanation and nine code listings |
| Main derivation | The array factor and its closed form, with nulls, symmetries, and the grating-lobe condition; the cost of a null, $G = 1 - r^2$; the exact expected pattern under independent errors; the squint. All carry the decision. The bisection threshold that shifts the grating-lobe onset (`onset_shift`) explains a numerical artefact and is optional |
| Role of the code | The nine functions of `arrays` (10 to 47 lines) are the model and its numerical checks, complex-valued and short: exact full source is right for them. The design studies are shown whole and are long: `degradation` 138 lines, `model_checks` 82, `taper_and_null` 81, `tracking` 65, `band` 55, each mixing the computation with table recording |
| Evidence and limits | A credibility boundary in the opening: an array-factor model, hypothetical requirements, every claim numerically verified and none physically validated. The decision is qualified (a window near the interferer that no weight can avoid, the error budget measured at the carrier only), and the limits name what the model cannot take on (coupling, planar arrays, estimated directions, correlated errors, wide band) |
| Exercises | A multiple-choice self-check on the squint of a wider band (the interpretation moment, after the band study); the largest spacing for a wider scan; the bits for a deeper null |

**Where the requirements are stated.** In EM9 they first appear under
"Worked examples", after the explanation and all nine code listings, and
only as the Python constants of three regions of the experiment module. The
region called `requirements` holds requirements (the band, the scan to
fifty degrees, a null thirty decibels deep, at most three decibels of gain
for a null) next to design choices (sixteen elements, a spacing of half a
wavelength, a taper designed for thirty decibels); the success criterion
that decides the number of bits, nineteen realised arrays in twenty, is in
the region called `errors`. The decision at the end lists the design but
does not go back through the requirements one by one.

T11 states its requirements as the first part of "Assumptions", before the
model and its assumptions: two tables of invented loads and limits, then one
sentence that says what the design must keep (the hottest junction at or
below the limit, the spreader within mass and thickness, the cold plate
within what the coolant loop provides, the clearances). Its opening asks
the design question in one sentence, and its claim box draws the line
between verification and validation before any number. **T11's placement
serves the design question better:** the learner reads every derivation and
every check knowing which limit it serves. EM9's credibility boundary and
its qualified decision are as good as T11's; only its brief is late and
mixed with choices.

**Good practice (EM9).** The credibility boundary stated before any
derivation; the model checked against closed forms before it decides
anything ("Is the model right?"); trade-offs named as they arise (the taper
costs gain and widens the beam); an honest, qualified decision that names
the next step a real design would need; exact full source for the short
model functions, with their complex weights kept.

**Gaps (EM9).**

- The brief is late and exists only as code (above).
- The long design-study listings put table recording and Monte Carlo
  orchestration on the page with the few lines that teach the design.
  Exact selections (F175's forms) would serve them as they served MAT6.
- **Owner's gaps.** Coupled formulas: yes, twice. The closed-form array
  factor with its variable $x$, and the null's cost $G$ with $r$, are each
  joined by `\qquad`. Chart directly after the prediction: not applicable
  (no interactive figure, no prediction question). Two Source links alone
  side by side: no. The nine consecutive listings of "Code" each end with
  their own "Source", which is not the M5 defect, since each link is bound to
  the listing above it. Header note: not applicable, as for AST8. Complex
  numbers carry the main line here, so no reading route avoids them.

## AI evidence: AE3, the agent against methods without one

**The journey.** The learner must know at once what kind of evidence each
row is: a recorded run of a language model, replayed and scored again from
its tool calls; a deterministic baseline that the build computes; a judge
that scores both. The lesson's contribution beyond the earlier agent
protocols is the control: each baseline differs from the agent in one known
way, so each comparison measures one thing. The conclusion is narrow: these
runs, one judge, one allowance.

| Element | Where and what |
|---|---|
| Physical question | In the opening: is a language model with tools better than simpler methods at finding a law, against what, and how can the comparison be rigged by accident? |
| Prerequisite bridge | The benchmark lesson (the systems, protocols, judge, held-out settings, and the "partial condition"), which the assumptions name but do not explain; least squares and the chi-square |
| First observable | The plain model's three recorded runs, displayed, then the table of every method under one judge |
| Main derivation | No formula. The argument that carries the lesson is the list "What each comparison measures" with the `comparable` check: what differs between two entries decides what their comparison measures |
| Role of the code | `comparable` (validation of fairness), `plain_task` (agent control: what the plain model was given), `baseline_entry` and `random_fit` (the baselines and the scoring), `entries`, `tally`, and `seeds` (orchestration and the exercise). `draw_methods` is shown whole (about 50 lines); one line of it transforms the data, mapping a zero error to a floor and "no claim" to the top of the axis, and the caption and the prose after the figure already say so |
| Evidence and limits | The kinds are kept apart: the plain model's claims are said to be priors, the baselines are computed, the agent's runs recorded once. The limits say that one run per system cannot rank, that easy systems favour fits, that round hidden values flatter the agent, and that the recordings are Claude Code sessions, not API runs |
| Exercises | A multiple-choice self-check on which conclusion the lesson supports (the interpretation moment, with feedback on the two tempting wrong answers); random selection over twenty seeds; what the plain model's comparison measures and what a fairer control would be |

**Good practice.** Each baseline is introduced as a control for exactly one
difference; the build checks, for every row, whether a comparison is
allowed and says what an unallowed one measures instead; a model's
statement ("its claim was a prior") is reported as the model's statement,
not as evidence; the self-check's wrong answers are the two readings a
learner is most likely to make (a ranking from one run, efficiency from
fewer probes).

**Gaps.**

- The kind of evidence is not stated at once. That the agent's rows are
  recorded runs, one per system, replayed and re-scored, reaches the learner
  in assumptions 2 and 3 and in the worked examples, not in the opening that
  sets the agent beside the baselines.
- One system has two names. The prose and the figure's caption call it the
  spring; the figure's axis, its alternative text, and the recorded run of
  the plain model call it the oscillator.
- `draw_methods` is on the page for one line whose transformation the
  caption already states; under the skill's rule a Source link is enough.
- **Owner's gaps.** Coupled formulas: not applicable (no display formula).
  Chart directly after the prediction: not applicable (no interactive
  figure). Two Source links alone side by side: no. Header note: not
  applicable (no depth section).

## Formal proof: Lean exercises on your machine

**The journey.** The learner moves from reading proofs to writing one: the
theorem first, in words and as a Lean statement with its hypotheses; then
the learner's own attempt, where the goal Lean shows after each tactic is
the evidence; then hints in order; then the checked solution. A numeric
instance can show what a statement says, but it comes after the statement
it instances and is never a step of the proof. The deliberate moment is not
a prediction about a figure but being stuck on a goal.

| Element | Where and what |
|---|---|
| Physical question | Not a physical question but a skill: can you prove three statements about constant acceleration and an impulse? The physics is the content of the statements; the limits say that whether a real motion has constant acceleration is a question for measurement |
| Prerequisite bridge | The first Lean lesson (finished proofs; it already uses `subst`, `field_simp`, and `ring`); a clone with the pinned toolchain. The page sends the learner to work locally from its second paragraph, but the setup page that installs Lean is linked only from "Check this proof" at the end |
| First observable | The numeric instance: both sides of the first two statements for a throw at 20 m/s and the momentum before and after, then a figure of the two sides of the first statement. It comes before any statement is shown: the stubs appear only in "Exercises" |
| Main derivation | The proofs themselves (substitute, clear the division, close with `ring`), shown as checked solutions; the reason for `ha : a ≠ 0` (in Lean division by zero is zero, so the statement is false without it) |
| Role of the code | The stubs (not verified, by design) and the solutions (compiled, read from the files that compiled them) are the formal proof and the exercise: they must stay exact. The numeric cell `both_sides` evaluates both sides; `draw_two_sides` (20 lines) computes the same two sides again for the figure, so a Source link would lose no calculation |
| Evidence and limits | The difference between a stub (shown as not verified), a checked solution, and a numeric instance ("an instance of each statement, not a proof of it") is kept explicit; the limits say that the site cannot check the learner's proof and that the solutions are public |
| Exercises | Three proofs, each with hints that open one at a time (what to do, then which tactic, then why it works), and a self-check on why `ha` is a hypothesis, which is the lesson's counterintuitive point |

**Good practice.** The graded hints are a first proof-writing step the
learner can take, one decision at a time; the not-verified box and the
compiled solution make the status of every Lean block visible; the
self-check turns a hypothesis into the point of the theorem; the numeric
instance is labelled as an instance.

**Gaps.**

- The statements arrive last. The assumptions name the hypotheses `hx`,
  `hv`, `hm₁`, and `hm₂` before the learner has seen a statement that uses
  them, and the worked example evaluates "both sides of the first two
  statements" before those statements are on the page.
- The opening says tactics make sense "once you have been stuck with a goal
  that will not close", and the hints speak of "the goal", but the page never
  shows a goal, nor what Lean reports when a tactic fails. The step from
  reading to writing a proof lacks its one observable.
- The setup that the whole lesson depends on is linked at the end, not
  where the learner starts.
- **Owner's gaps.** Coupled formulas: not applicable (no display formula).
  Chart directly after the prediction: not applicable. Two Source links
  alone side by side: no; the throw region and `both_sides` are two
  consecutive listings, each with its own link. Header note: not applicable.

## Where the pilots' method does not transfer

| Part of the pilots' method | Measured data (AST8) | Engineering (EM9, T11) | AI evidence (AE3) | Formal proof (lean/04) |
|---|---|---|---|---|
| Open with the physical question | Transfers | Transfers as the design question and its brief; a motivation alone is not enough | Transfers as the evidence question (better against what?) | Becomes the statement to prove; the question is a skill, not a phenomenon |
| A prediction before the evidence | Optional; the interpretation moment after the evidence (the self-check on $b$) carries more | Optional; trade-offs are judged against requirements, not guessed | Transfers (would the plain model find the hidden value?) but the self-check already does the work | Does not transfer as a prediction; the deliberate moment is the learner's attempt and the goal it leaves |
| A small first calculation before the general analysis | Transfers as the raw observation first; the template's section order works against it | The model check against the closed form plays this role and is already first | Not applicable (no calculation) | Inverted: a numeric instance before the statement is the order to avoid |
| Optional derivations to a depth section, with a header note | Does not transfer: the fit, covariance, and propagation are the main result | Partly: one artefact explanation (the onset shift) is optional, the rest carries the decision; the header note would be false | Not applicable | Not applicable: the proof is the lesson and is never optional |
| Interactive chart directly after the question | Not applicable | A candidate exists (steering angle, bits; Appendix B of the change request), not a gap | Not applicable | Not applicable; Appendix B of the change request rules out requiring Lean in the browser |
| Code: show what carries the method, link the drawing | Transfers, and extends to table-recording functions | Transfers, and extends to long design-study functions | Transfers (`draw_methods`) | Transfers for the figure only; stubs and solutions stay exact and whole |
| Stacked coupled formulas | Transfers (two displays) | Transfers (two displays in EM9; none in T11) | Not applicable | Not applicable |

## The skill after the calibration

**Corrections: none.** No rule of the skill is contradicted by these four
lessons. The archetype table, the five kinds of result, the code-display
choices, and the rule on transformations inside plotting code each describe
what the good practice above does and name the gaps found. The "leave as it
is" verdict on AST8 holds for its sequence; its coupled formulas and
`geometry_table` are presentation gaps the verdict does not cover.

**Under-specified, recorded for the owner.** Two rows of the archetype
table allowed what the calibration found to be a gap, and section 7 names
plotting code where table code has the same problem:

- *Engineering design or capstone.* "Before or beside the method" admits
  EM9's brief, which comes after the method and only as code. A sharper row
  would read: the brief, constraints, and success criteria stated in words
  before the method, kept apart from the choices the design makes, and
  recalled one by one at the decision; watch for requirements that exist
  only as constants of the code, or that arrive after the method serving
  them.
- *Formal proof.* The row says what to keep apart but not the order, and it
  says nothing of an exercise lesson. A sharper row would add: the theorem
  stated before any instance of it; in an exercise, the deliberate moment is
  the learner's attempt, with the goal Lean shows and what a failing tactic
  reports, then hints in order; watch for a numeric instance shown before
  the statement it instances.
- *Section 7.* "Transformations inside plotting code" applies equally to a
  function that records a table, such as `geometry_table` in AST8.

These are not made here, for two reasons. They sharpen rules rather than
correct wrong ones. And any change to a project-owned skill changes its
digest, which `skills-config` checks against every plan that pins the
skill: six plans of delivered features (F165, F166, F167, F170, F176, and
the F175 follow-up of Issue #536) name `pbc-physics-teaching@7f34987`. A change
must first settle how those records keep the revision they were made
with, which is a decision for the owner, not a side effect of this
diagnostic. The natural place is the review the skill's provenance
record schedules "after the pilots F165 to F168 report", together with
F116.

## For F116

What generalises from the four lessons, for the authoring guide, template,
and rubric:

- The archetype decides the order before the template does. A measured lab
  needs its first observation before the processing it motivates, and a
  capstone needs its brief before its method. T11 shows that the required
  sections allow the brief (it puts it in "Assumptions"); nothing yet says
  where the first observation of a measured lab goes.
- The header note of M5 generalises only to a lesson with a depth section.
  Where the outside prerequisites carry the main line (AST8, EM9), the note
  would mislead.
- The `equation-pair` rollout has four displays to convert in these
  lessons (two in AST8, two in EM9); the Lean and agent lessons have none.
- The code-display check before linking a function applies to tables and
  long experiment functions as it does to drawing functions.

## The proposal for F169

**Proposed: one redesign, of EM9**
(`site/lessons/electromagnetism/07-adaptive-phased-array-beam-steering/index.qmd`).

**The learner-facing problem.** A learner works through the explanation and
nine code listings without knowing what the design must achieve. When the
requirements appear, they are Python constants in which requirements and
design choices sit side by side, and the success criterion that decides the
number of bits is in another region. At the decision, the learner cannot
check the design against a stated list. T11 shows, in the same curriculum,
the placement that avoids this.

**Proposed scope**, the science unchanged (no number, claim, figure, or
check changes):

1. A design brief in words before the explanation: the requirements and the
   success criteria, kept apart from the design choices, from the same
   constants.
2. The decision recalls each requirement with how the design meets it, or
   under which condition.
3. The two coupled formulas as `equation-pair`.
4. If F175's forms are used: exact selections for the longest design-study
   listings (`degradation`, `model_checks`, `taper_and_null`), the rest
   behind the link.

**Not proposed.** AST8 needs no redesign; its gaps are the template order
and two formulas. AE3's gaps (the evidence kind in the opening, one name for
the spring, `draw_methods` as a link) are small edits for F116's rollout.
The Lean lesson's gaps (statements before the instance, a goal shown, the setup link)
are real but local to a short lesson; they are candidates for the rollout,
not a redesign.

**Interaction candidate for F177.** EM9's steering angle and number of bits
over precomputed patterns, as Appendix B of the change request lists it;
recorded, not proposed for a decision here.

**The owner's decision** on this proposal is recorded on Issue #553; until
then F169 does not start.
