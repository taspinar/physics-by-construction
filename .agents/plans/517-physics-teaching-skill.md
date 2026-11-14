# Plan: F164, the PBC Physics Teaching skill and its selection rule (Issue #517)

Source: `docs/roadmap.md`, F164; ADR 023 decisions 1 and 2 (amending ADR
019 decisions 2 and 5); `docs/architecture.md`, "Teaching by
construction"; `docs/changes/teaching-by-construction.md`, section 5 (T1)
and section 17.

**Level 3.** Paths: `.agents/skills/` and `AGENTS.md` (protected in
`.agents/policies/guardrails.conf`). No trigger beyond the paths: no
published claim, test strength, dependency, or check changes. The full
`./scripts/verify.sh` of the final tree runs after the session
(`review-feature.sh`; the owner's rule on the Issue), the full review, and
the owner's approval of the exact commit at the merge gate.

## Visual deliverables

Skills: none (no visual deliverable; the feature writes the teaching skill itself)

The artifact is a prose skill file. It is written under the conventions
of the README of `.agents/skills/` for the project-owned skill: front
matter with `name` and `description`, the rules it defers to named
first, no script.

## Steps

1. The `SKILL.md` of `.agents/skills/pbc-physics-teaching/`: the content listed in
   `docs/architecture.md`, "Teaching by construction" (target learner and
   prerequisites, central question and counterintuitive point,
   prerequisite gaps, one or two deliberate moments, the five kinds of
   result kept apart, essential versus optional derivations, the six
   archetypes and their journeys, the teaching purpose of every displayed
   code block with the four display choices of ADR 023, scientific
   transformations inside plotting functions, types that are the concept,
   just-in-time assumptions); the ownership boundaries with
   `docs/editorial-voice.md`, `docs/authoring.md`, and the
   scientific-visualization skill, pointing to their sections and
   restating none of their rules; the distilled practice of the named
   sources with chapter or section references and what each contributes,
   in original words; short before-and-after examples from PBC lessons,
   one of them "leave as it is", each with why it helps comprehension.
2. `PROVENANCE.yaml` (kind `project`, revision `none`, the sources it
   distils in `assessment`, the review and update policy, the digest of
   `python -m pbc.skills --digest`), and the row in the README of
   `.agents/skills/` (the README's opening says the set is no longer only
   visual).
3. The selection rule of ADR 023 decision 2 in `AGENTS.md`, "Visual
   deliverables and skills", and in `docs/process.md`, "Agent skills": a
   plan that writes or revises a lesson's teaching selects the skill or
   records why not on the same `Skills:` line; the implementer records
   where it changed the learning experience; the reviewer names weaknesses
   with evidence and an action, no score; no review role, agent, model
   call, or round.
4. `tests/unit/test_skills_boundary.py`: the new skill's name joins the
   pattern of names that no machinery file may mention (the boundary of
   ADR 019 decision 1 for the new skill; strengthens, weakens nothing).
5. The dry run on M1 (model or simulation) and AST8 (measured-data
   investigation), source only, no lesson changed: recorded below and on
   the Issue as a comment.
6. `uv run python -m pbc.skills`, the boundary and skills tests, the docs
   checks; the targeted verification last in the session; the full run
   after it by `review-feature.sh`.

## Template-synced files changed

Carry this to the template repository, or keep it through the merge of
`sync-template.sh`: `AGENTS.md` (the selection rule of the teaching skill
in "Visual deliverables and skills"). Project-only: `.agents/skills/`,
`docs/process.md`, `tests/unit/test_skills_boundary.py`.

## Dry run (criterion 5)

The skill applied to the sources of two lessons on 2026-11-14. Decisions
only; no lesson is changed by this feature (the pilots F165 to F167 and
the calibration F168 decide what is changed). A "Source link only" below
uses the compact Source link that F175 delivers; F165, which depends on
F175, applies it to M1.

### M1, `mechanics/01-kinematics-as-a-program` (model or simulation)

1. **Leave as it is: the opening and the counterintuitive point.** The
   central question (where is a thrown ball after one second, knowing only
   its start and its acceleration) comes first; the counterintuitive point
   (the velocity is exact, the position lags by
   $-\tfrac{1}{2}a\,t_n\,\Delta t$) is derived and then tested. Nothing
   to restructure.
2. **Change: make the first prediction the learner's.** "A ball thrown
   straight up" states the prediction for the reader ("the velocities
   agree in every row, and the positions differ by ..."). Ask first, in
   one question before the table: will the Euler ball be above or below
   the exact one, and will the velocities differ? Then the table answers.
   Why: the derivation just gave the learner everything needed to
   predict; stating the answer removes the one moment where the learner
   checks their own reading of the formula. One moment only; the
   self-check on round-off stays the second (interpretation).
3. **Change: `draw_state_and_update` becomes a Source link only.** It
   positions boxes and arrows of a conceptual sketch; it teaches no
   physics and no method, and its listing sits between the update rule
   and the sketch, between the equation and its picture. Why: the learner
   reads the update rule, then the picture of it, without a detour
   through drawing calls.
4. **Change: `draw_ball_thrown_up` and `draw_error_against_time_step`
   become Source links only.** Checked for a scientific transformation
   first: the first evaluates the exact motion on a fine grid and plots;
   the second plots `np.abs` of errors that `halving` and
   `shaking_cart` computed and that the page already shows. Neither
   computes anything the conclusion rests on. Why: the code that carries
   the comparison (`thrown_ball`, `final_error`, `halving`) stays on the
   page and is no longer buried among plotting calls.
5. **Leave as it is: the exact-error derivation, and the Go deeper.**
   The sum that gives $x_n - x(t_n)$ is essential: the first worked
   example tests exactly that prediction. The local-versus-global error
   proof is already optional in a Go deeper block with the scope stated.
6. **Leave as it is: the Assumptions section, and `State` with its
   types.** All five assumptions are needed; the fifth is recalled where
   it is used ("The fifth assumption said ..."), which is the
   just-in-time placement. `State` is the concept of the lesson; its
   fields and types are what the learner must read.

### AST8, `astrophysics/09-exoplanet-light-curves` (measured-data investigation)

1. **Leave as it is: the lineage.** The page runs in the order of the
   measured-data journey: the model checked before the data, the record
   and its card, cleaning (a selection, labelled processed), detrending
   with the curved baseline shown, the fit, residuals against a simpler
   model, propagated uncertainties, the mid-time scatter, the
   sensitivity to the normalisation, an independent check (the density),
   and a conclusion that says what no number bounds. Measurement,
   processed signal, model, and inference are named apart at each step.
   Restructuring it would only make it look like other lessons.
2. **Leave as it is: the code of the physics and the processing.**
   `limb_flux` (a new relationship: the star summed over rings),
   `propagate_correlated`, `phase_curve`, and `one_transit` show the
   transformations the conclusions rest on (the per-orbit median, the
   parabola fitted outside the transit, the division). Exact full source
   is right for them.
3. **Change, after F175: `geometry_table` and `sensitivity_table` as
   exact selections.** Most of their lines record a table (column names,
   formats, a caption); the lines that teach are the propagation call and
   the scaling by the square root of the reduced chi-square, and the
   loop over windows and baselines. A multi-range exact selection with
   the omission marked keeps those and the Source link. Until F175
   delivers the form, leave them whole.
4. **Change: one prediction moment before the uniform-star fit.** Before
   `fig-transit-fit`, ask: if the star were uniform, how would the fit
   make up for the missing rounded bottom? The page's point ("fitting the
   wrong model still returns numbers, with small standard errors") is
   counterintuitive, and a learner who predicted "it cannot fit" or "only
   the depth changes" meets the larger $p$ and $b$ as an answer, not a
   fact. The existing self-check on how well $b$ is known stays the second
   moment.
5. **Leave as it is: the residual inside `draw_transit_fit`.** The
   plotting function bins data minus model; the transformation is stated
   in the legend and the caption, and the claim against the uniform star
   rests on the chi-square of `fit_uniform_star`, which is shown. No
   calculation the conclusion needs is hidden behind the Source link.

Several "leave as it is" decisions are recorded (M1 1, 5, 6; AST8 1, 2,
5): AST8 is one of the change request's positive counterexamples, and the
skill agrees.
