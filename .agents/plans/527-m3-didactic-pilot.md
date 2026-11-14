# Plan: F166, the didactic pilot on M3, `mechanics/03-projectile-motion-with-drag` (Issue #527)

Source: `docs/roadmap.md`, F166 (and F165, whose in-scope list and
criteria it takes for M3); `docs/changes/teaching-by-construction.md`,
section 6 (T2, the row of lesson 03) and section 10 (the launch-angle
candidate); requirements decision 44; ADR 023. Written by the implementer
at the start of the work (the Issue expects a short plan and none
existed).

**Level 2.** One lesson source,
`site/lessons/mechanics/03-projectile-motion-with-drag/index.qmd`, and
this plan. No protected path, no test, no source module, no front matter
(the header and the learning path show nothing new), no claim, value,
figure, exercise, or excerpt changed: the sequence and the connecting
prose change, every `excerpt(...)` call, cell, claim, and inline value
stays as it is. The targeted run selects M3 alone.

**Revision after the agent reading (owner's decision, 2026-11-14).** The
owner decided to fix the stumbling points of the agent reading of
criterion 8 in this feature ("Criterion 8: an agent's reading of M3" on the
Issue, and the decision that follows it). That adds the experiment module
`src/pbc/mechanics/experiments/projectile_with_drag.py` to the change, still
Level 2: Figure 1's labels sit beside their curves, Figure 4's 45° line has a
legend entry, and two computed numbers are new (`scan-error-cm`, the error of
the convergence table's throw at the scan step; `angle-gain`, how much
further the best angle throws than 45°). No existing number, table, result,
claim, or test assertion changes. See step 7.

## Visual deliverables

A lesson's teaching sequence, and two revised scientific figures
(step 7): the conceptual sketch `fig-drag-against-speed` (labels moved
beside their curves) and the simulated plot `fig-range-against-angle` (a
legend entry for the 45° line). The data of both are unchanged.

Skills: pbc-physics-teaching@7f34987
Skills: pbc-scientific-visualization@a70b501

- **Artifact:** the revised page of M3.
- **Scientific validation:** the experiment is untouched, so every number,
  table, and figure is the same; the claim and its evidence are unchanged;
  the lesson-source checks, the single-page render, and the independent
  review.
- **Accessible fallback:** captions and alt text unchanged except Figure 2
  (its caption and alt text now say the peak is at a shorter distance than
  the drag-free throw but past the middle of its own path, as the computed
  paths show: 19.7 m against a half range of 17.7 m) and Figure 3 (its
  caption); the page stays complete without scripts. The two redrawn
  figures are compared with the previous ones by the reproduction of the
  experiment (the single-page render and the experiment's entry point).

## The learner and the subject (criterion 1)

- **Learner.** Has done M1 (explicit Euler, the lag
  $\tfrac{1}{2}a\,t\,\Delta t$, first-order convergence) and M2 (forces as
  a list, the stepping interface, linear drag with its exact solution and
  the lopsided path of a body with drag); knows vector components at an
  angle and can read a log-log plot. Has never validated a simulation that
  has no exact solution.
- **Central question.** At what angle should a tennis ball be thrown to go
  furthest, with air?
- **Counterintuitive points.** (a) Drag does not scale every range down
  alike, so the best angle moves, and the curve becomes lopsided. (b) A
  converged simulation is not an accurate description of a real ball:
  convergence measures the method's error, not the model's.
- **Target misconceptions.** "Drag only shortens the throw; 45° stays
  best." "A result that stops changing with the step is correct." "Without
  an exact solution a simulation cannot be checked."
- **Archetype.** Model or simulation. Journey: question, model and
  assumptions, method, checks against what is known, the answer, where it
  stops holding.
- **Why this sequence suits the subject.** M2 ended on the lopsided path
  with linear drag and announced that quadratic drag has no formula. The
  learner therefore expects the picture and needs a reason to trust it:
  showing the drag/no-drag throw first makes the trust question concrete
  (these numbers came from a program with nothing to compare them with),
  and the checks then answer that question instead of preceding a question
  the learner has not yet felt. The launch-angle question is restated where
  each part hands over to the next, so the validation reads as the
  condition for the answer, not as a detour.

## Before-and-after reading map (criterion 2)

| Moment | Before | After |
|---|---|---|
| Main question | Introduction, then not again until the last worked example | Introduction; restated after the first look, at the start of the checks, at the start of the worked examples, answered in the last one, bounded in Limits |
| First physical intuition | Explanation, after six assumptions: the drag law, the terminal speed as the scale | Explanation, first: the same, directly after the introduction |
| First calculation | Worked examples, "One throw": the tennis ball's drag constant, terminal speed, Reynolds number, stable step | Explanation, "A first look: one throw with and without drag" (`#one-throw`), the same numbers |
| First experiment | Worked examples, after the assumptions, the explanation, and seven code listings: the throw with and without drag | Explanation, right after the drag law: the same table and figure, read before any check |
| Interpretation | After the figure; then "two different questions" | The same, plus the two questions the figure raises: does the best angle move, and should the numbers be believed |
| Key derivations | The drag-free lag of explicit Euler and Richardson extrapolation, in "How to trust a simulation without one" | Unchanged, now motivated by the trust question the first look raised |
| Assumptions | First section, before any physics | After the explanation, before the program and the checks; their first encounter is one sentence in the introduction, and the complete list is unchanged |
| Prediction moment | Before the angle scan: does drag move the best angle, and which way? | Unchanged (the one deliberate prediction); the self-check stays the interpretation moment |
| Conclusion | End of the angle example; Limits | Unchanged |

**Stayed unchanged, and why.** Every equation, claim, value, table,
figure, caption, alt text, exercise, solution, self-check, and excerpt
call; the derivations (each is essential: the drag-free lag is the first
check, Richardson the second, the interpolation bound justifies the
landing point); the prediction before the scan (it sits where the
counterintuitive point meets the evidence, as the skill asks); Limits and
the self-check (they state the real-ball boundary already); the
exercises; the front matter. Every heading keeps its identifier (`one-throw`
is now explicit because its title changed).

## Display of the code (criterion 6 of F165, for M3's code blocks)

Exact forms only (F175 is not merged; no Source-link-only form exists
yet). Per block, its teaching purpose and the decision:

| Block | Purpose | Decision |
|---|---|---|
| `draw_drag_against_speed` | None (a conceptual sketch's drawing) | Exact full, moved after the sketch and its reading; a Source link when F175's forms reach the lesson |
| `experiment`, region `setup` | The model's inputs and the scales derived from them | Exact region, in the first look |
| `experiment.throws` | The comparison: two force lists that differ by the drag only | Exact full, in the first look |
| `draw_throw_with_and_without_drag` | None (plots the two flights) | Exact full, moved after the figure and its reading |
| `drag.quadratic_drag`, `drag.drag_constant` | The force law and its constant | Exact full, unchanged place |
| `projectile.launch`, `fly`, `landing` | The start state, the stopping loop, the interpolated landing of "Finding the ground" | Exact full, unchanged place |
| `projectile.projectile_range` | The function the question is asked of | Exact full, unchanged |
| `projectile.drag_free_range` | The exact reference of the first check | Exact full, unchanged |
| `experiment.drag_free_convergence`, `experiment.richardson` | Validation: the error against the exact range; observed order and extrapolation | Exact full, unchanged |
| `draw_convergence_of_the_range` | Holds the transformation the figure is read by (the error against the extrapolated limit, the reference line) | Exact full, kept before its figure |
| `experiment`, region `scan` | The precomputed angle grid and its step | Exact region, unchanged |
| `experiment.best_angle`, `experiment.longest_throws` | The bounded minimiser, separate from the grid | Exact full, unchanged; the prose now says that the grid draws the curve and the minimiser, not the grid, gives the best angle |
| `draw_range_against_angle` | None (plots the grid's ranges and the 45° mark) | Exact full, moved after the figure's reading |
| Exercise solutions | Unchanged | Unchanged |

## Launch-angle interaction, a candidate for F177 (recorded, not built)

- **What it would add over the static figure.** The figure shows the
  ranges against the angle; a control over the angle could show the two
  paths of the chosen angle side by side, so a learner sees *why* a steep
  throw loses more: its longer flight under drag.
- **Data.** Only Python-generated values: the existing grid
  (`angles`, every 2.5° from 10° to 80°, at `scan_dt`) and the paths at
  those angles, written by the experiment. The control steps through the
  grid's angles and says so.
- **Honesty.** The page never presents the grid's largest value as the
  best angle; the best angle stays the minimiser's value from the table,
  labelled as such. The model's assumptions (no spin, still air, constant
  drag coefficient) are stated beside the control.
- **Assessment.** Moderate: the misconception it addresses ("drag scales
  all ranges alike") is already confronted by the prediction and the
  lopsided curve. Recommend it only if F167's review of M1 to M5 finds the
  static comparison insufficient; the owner chooses (F177).

## Steps

1. The introduction: the question, the three-part route, and the model's
   assumptions in one sentence with pointers to Assumptions and Limits.
2. The explanation first: the drag law and the terminal speed, then the
   first look at one throw (moved from the worked examples, `#one-throw`
   kept), then the two questions it raises, then the subsections on the
   missing closed form, the checks, and finding the ground.
3. Assumptions after the explanation, the two references to "the first
   example" pointed at the first look.
4. The worked examples open with the reason the checks come first; the
   angle example says that the grid draws the curve and the minimiser
   finds the best angle; the drawing-only listings after their figures.
5. The lesson-source checks and the single-page render of M3; the
   targeted verification last.
6. Criteria 1 and 2 and the F177 candidate recorded on the Issue as a
   comment. Criteria 7 and 8 (the review, the owner's view at desktop
   and phone widths, comprehension observations) follow the session.
7. The stumbling points of the agent reading (owner's decision,
   2026-11-14), each kept true to the computed values: the first look
   points to Assumptions for the stable step and says why the drag may be
   linearised there (item five says it too); "the computed ball is higher
   by" in place of "lags"; $R(\Delta t) = R^* + C\,\Delta t$ before the
   observed order; the source of the interpolation remainder and how a
   height error becomes a range error; "Reynolds numbers from about a
   thousand to" in Assumptions; the difference column named as the error
   estimate (the convergence text and Exercise 2); the captions of Figures 2
   and 3; "(below)" in the opening; the viscosity's role; `landing`; the
   2 cm traced to $v_x\,\Delta t$; `minimize_scalar`, its bounds and
   `xatol`; the error at `scan_dt` (computed); Figure 1's labels; Figure 4's
   legend; the size of the gain at the best angle (computed) against the
   unverified drag coefficient.
