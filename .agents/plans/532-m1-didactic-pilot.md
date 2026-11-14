# Plan: F165, the didactic pilot on M1, `mechanics/01-kinematics-as-a-program` (Issue #532)

Source: `docs/roadmap.md`, F165; `docs/changes/teaching-by-construction.md`,
section 6 (T2, the row of lesson 01, acceptance 1 to 9); requirements
decision 44; ADR 023. F166 (#527, `.agents/plans/527-m3-didactic-pilot.md`)
is the model. Written by the implementer at the start of the work (the Issue
expects a short plan and none existed).

**Level 2.** The lesson source
`site/lessons/mechanics/01-kinematics-as-a-program/index.qmd`, its
experiment module `src/pbc/mechanics/experiments/kinematics.py` (new
numbers only: the first step by hand), one new test in
`tests/unit/test_kinematics_experiment.py`, and this plan. No protected
path, no existing test assertion, no front matter (the header and the
learning path show nothing new), no claim, table, figure, exercise, or
existing number changed. The targeted run selects M1 alone.

## Visual deliverables

A lesson's teaching sequence. No figure is redrawn, and none moves out of
its section: `fig-state-and-update` stays in the explanation,
`fig-ball-thrown-up` and `fig-error-against-time-step` in the worked
examples.

Skills: pbc-physics-teaching@7f34987
Skills: none (pbc-scientific-visualization: no figure moves or is redrawn)

- **Artifact:** the revised page of M1.
- **Scientific validation:** every existing number, table, figure, caption,
  alt text, claim and exercise is the experiment's as before; the new
  numbers of the first step come from the same `simulate` run as the
  table, and a new unit test checks that the gap after one step is
  $\tfrac{1}{2}\,g\,\Delta t^{2}$ in the digits shown and that the
  velocities agree; the lesson-source checks, the single-page render, and
  the independent review.
- **Accessible fallback:** captions and alt text unchanged; no script is
  added; the page stays complete without scripts.

## The learner and the subject (criterion 1)

- **Learner.** The first lesson of the course: no PBC lesson before it.
  Knows derivatives, integrals, and a second-order Taylor expansion;
  Python functions, dataclasses, and NumPy arrays; the base-2 logarithm
  and a log-log plot (the `outside` prerequisites). Has seen
  $x = x_0 + v_0 t + \tfrac12 a t^2$ but has never let a program advance a
  motion in steps, and has never asked how wrong such a program is.
- **Central question.** Where is a thrown ball a moment later, when the
  program only knows a rule for the next instant, and how wrong is that
  program, and how does its error shrink with the time step?
- **Counterintuitive point.** Under a constant acceleration the velocity
  computed by explicit Euler is exact while the position is not: the
  computed ball moves with the speed it had at the start of each step, so
  it is too high by the same $\tfrac12 g\,\Delta t^2$ after every step, and
  the gap grows with time though nothing in the velocity is wrong.
- **Target misconceptions.** "The program is either right or wrong; a
  small step makes it right." "If the velocity is right, the position is
  right." "The error of one step is the error of the method" (local against
  global: the dropped $\Delta t^2$ terms add up to a $\Delta t$ error).
  "Halving the step again and again makes the error as small as you like"
  (round-off; the self-check).
- **Archetype.** Model or simulation. Journey: the question, the model and
  the method, a check against the exact motion, what the discrepancy
  means, the general error order, where it stops holding.
- **Why this sequence suits the subject.** The analysis of local and
  global errors is an argument about sums of dropped terms, and a first
  learner has nothing to attach it to before seeing one dropped term. One
  step by hand, with the ball's own numbers, makes the dropped term a
  visible 5 cm: the learner predicts above or below, sees the velocity
  agree and the height not, and learns why (the speed at the start of the
  step). The exact derivation for constant acceleration then says that
  every step adds the same amount, which is the bridge to the general
  statement: $T/\Delta t$ steps of size $\Delta t^2$ give an error of size
  $\Delta t$. The asymptotic analysis comes last in the explanation, as the
  generalisation of something already seen, and the worked examples
  measure it.

## Before-and-after reading map (criterion 2)

| Moment | Before | After |
|---|---|---|
| Main question | Introduction | Introduction, with the route (one step by hand, the whole flight, how the error shrinks); restated at the first step and answered at the end of the worked examples |
| First physical intuition | Explanation, after five assumptions: what one needs to know to say what happens next (the state) | Explanation, directly after the introduction: the same |
| First calculation | Worked examples, after the local/global analysis, the exact derivation, and four listings: the thrown-ball table | Explanation, "One step by hand" (`#one-step`): the ball's first step, computed and exact |
| First experiment | Worked examples, "A ball thrown straight up" | Unchanged place; its first step is now met in the explanation, and the code before it is the state, the step, the loop, and the exact motion (no drawing code) |
| Prediction moment | None in the prose: the text states that the velocities agree and the positions differ, then shows the table | Before the first step: above or below the real ball, and does the velocity differ? The page answers it in the next paragraph. The self-check stays the interpretation moment |
| Interpretation | After the figure of the thrown ball | First at the first step (why the computed ball is higher: the speed at the start of the step), then after the table and the figure as before |
| Key derivations | Local and global error first, then the exact lag for constant acceleration | The exact lag first, as "where the gap comes from" (`#the-lag`), ending in "every step adds the gap of the first one"; then the local/global argument (`#how-large-is-the-error`, kept) as its generalisation |
| Assumptions | First section, before any physics | After the explanation, before the program; their first encounter is one sentence in the introduction, and the complete list is unchanged |
| The state update in code | `kinematics.euler_step` in "The program", after the sketch's drawing code | `kinematics.State` and `kinematics.euler_step` directly under the update rule they implement; the drawing code behind a Figure source link |
| Conclusion | End of the worked examples; Limits | Unchanged |

**Stayed unchanged, and why.** Every equation, claim (text, type, scope,
evidence), value, table, figure, caption, alt text, the Go deeper box,
Limits, the self-check, the exercises and their solutions (their excerpts
included), the reproduction section, and the front matter. The two
derivations are essential (the exact lag is the first check of the
program, the local/global argument gives the order the examples measure),
so both stay in the explanation, stepwise; only their order changes. The
worked examples stay where they are: they are the measurement, and the
learner now arrives at them holding the prediction. Every heading keeps its
identifier; the two new subsections get explicit ones (`one-step`,
`the-lag`). No page links to an anchor of M1 (searched in `site`, `docs`,
`src`, `tests`).

## Display of the code (criterion 6)

Per block, its teaching purpose and the form (ADR 023; F175's forms):

| Block | Purpose | Form |
|---|---|---|
| `experiment.draw_state_and_update` | None (a conceptual sketch's drawing; computes nothing) | Figure source link, after the sketch (the skill's own before-and-after case) |
| `kinematics.State` | The state, the triple of the derivation, as a record | Exact full, moved under the update rule |
| `kinematics.euler_step` | The numerical update, term by term the update rule; the docstring states the cause of the lag (rates at the start of the step), so it stays | Exact full, moved under the update rule |
| `experiment`, region `setup` | The ball's inputs, used by the first step | Exact region, moved to "One step by hand" |
| `kinematics.simulate` | The step in a loop; the guards and the length of the result | Exact full, unchanged place |
| `kinematics.constant_acceleration` | The exact reference | Exact full, unchanged place |
| `experiment.thrown_ball` | The comparison: the simulation and the exact motion at the same instants | Exact selection, lines 4 to 5; the table record behind the Source link |
| `experiment.draw_ball_thrown_up` | None (plots the two curves) | Figure source link, after the figure |
| `experiment.final_error` | The error: last simulated position minus exact | Exact full, unchanged |
| `experiment.halving` | The errors and the ratio the conclusion reads | Exact selection, lines 3 and 12; the table layout behind the Source link |
| `experiment`, region `cart` | The cart's inputs | Exact region, unchanged |
| `experiment.shaking_cart` | The errors and the observed order (the binary logarithm of the ratio) | Exact selection, lines 4 to 5 |
| `experiment.draw_error_against_time_step` | Holds the reference line the figure is read by (slope one: the time step itself) and the time steps | Exact selection, lines 5 and 19, after the figure; the formatting behind the Source link |
| Exercise solutions | Unchanged | Unchanged |

No derived form (generated signature) is used: every signature shown is
short and its annotations are the concept (a `State`, a callable of time).

## A Δt interaction, a candidate for F177 (recorded, not built)

- **What it would add over the static page.** A control over the time step
  of the thrown ball, stepping through the convergence grid
  (`step_counts`: 24 to 768 steps over the same duration), showing the
  Euler points against the exact parabola and the gap at the end beside
  $\tfrac12 g\,T\,\Delta t$. A learner would see the whole curve approach
  the parabola and the gap halve, instead of reading it from a table.
- **Data.** Only Python-generated values: the trajectories of the grid,
  written by the experiment. The control steps through the grid and says
  so; it computes nothing.
- **Honesty.** The page keeps the table and the log-log figure as the
  evidence; the control is an illustration of the same runs. Round-off is
  not shown by it, and the control says the grid stops far above it.
- **Assessment.** Low to moderate: the first step by hand and the halving
  table already confront "a small step makes it right"; the interaction
  would mostly add the picture of the whole curve converging. Recommend it
  only if F167's review of M1 to M5 finds the static sequence
  insufficient; the owner chooses (F177).

## Steps

1. The introduction: the question, the route, the assumptions in one
   sentence with a pointer to Assumptions (below).
2. The explanation: the update rule, the sketch with its Figure source
   link, `State` and `euler_step` under the rule; "One step by hand" with
   the setup region, the prediction, the computed and exact first step,
   and its meaning; "Where the gap comes from" (the exact lag, the claim,
   every step adds the first step's gap); "How large is the error?" (the
   local/global argument as the generalisation); Go deeper.
3. Assumptions after the explanation; "The worked examples add one more"
   pointed at the ball of the first step.
4. The program: `simulate`, `constant_acceleration`, with an opening that
   points to the state and the step above.
5. The worked examples: the thrown ball as the check of the prediction over
   the whole flight; the exact selections and the Figure source links of
   the display table.
6. The experiment: the numbers of the first step; a unit test.
7. The lesson-source checks, the experiment's unit tests, the single-page
   render of M1; the targeted verification last.
8. Criteria 1 and 2 and the F177 candidate recorded on the Issue as a
   comment. Criteria 7 and 8 (the review, the owner's view at desktop and
   phone widths, comprehension observations) follow the session.
