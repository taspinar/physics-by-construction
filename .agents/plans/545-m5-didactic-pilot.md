# Plan: F167, the didactic pilot on M5, `mechanics/05-numerical-integrators`, and the review of the M1 to M5 sequence (Issue #545)

Source: `docs/roadmap.md`, F167 (and F165, whose in-scope list and criteria
1 to 9 it takes for M5); `docs/changes/teaching-by-construction.md`,
section 6 (T2, the row of lesson 05, the control cases, the sequence
review) and section 10 (the integrator explorer: moved and explained, not
rebuilt); requirements decision 44; ADR 023. F165 (#532,
`.agents/plans/532-m1-didactic-pilot.md`) and F166 (#527,
`.agents/plans/527-m3-didactic-pilot.md`) are the models. Written by the
implementer at the start of the work (the Issue expects a short plan and
none existed).

**Level 2.** The lesson source
`site/lessons/mechanics/05-numerical-integrators/index.qmd`, the caption and
docstring of one table of its experiment
`src/pbc/mechanics/experiments/numerical_integrators.py` ("the energy
formulas of the explanation" now names where they are derived), and this
plan. No protected path, no test, no number, no table value, no figure, no
widget file, no widget data, no front matter (the header and the learning
path show nothing new; the `outside` prerequisites stay, because the
depth section still uses complex numbers and two-by-two matrices). The
targeted run selects M5 alone.

## Visual deliverables

A lesson's teaching sequence, and a page change: the integrator explorer
moves from after the worked examples to directly after the explanation.
No figure is redrawn; the explorer's script, data, controls, and static
fallback are unchanged (the F07 checks of `tests/e2e/test_widgets.py`
select it by `#integrator-explorer`, not by its place).

Skills: pbc-physics-teaching@7f34987
Skills: none (pbc-scientific-visualization: no figure is redrawn or changed; the explorer moves unchanged)

- **Artifact:** the revised page of M5.
- **Scientific validation:** every equation, claim, value, table, figure,
  caption (except the one table caption above), alt text, exercise, and
  solution is the experiment's as before; the moved derivations are moved
  verbatim; the lesson-source checks, the experiment's unit tests, the
  single-page render, and the independent review.
- **Accessible fallback:** captions and alt text unchanged; the explorer
  keeps its static figure and its three tables; the page stays complete
  without scripts.

## The learner and the subject (criterion 1)

- **Learner.** Has done M1 (explicit Euler, local and global error,
  first-order convergence), M2 (the stepping interface `simulate(...,
  step=...)`, forces as functions, linear drag with its exact solution),
  M3 (validation without an exact solution), and M4 (the harmonic
  oscillator, its exact motion, and explicit Euler's energy factor
  $1 + \omega^2\Delta t^2$ per step, which made ten periods at one per cent
  impractical). Difficulty 2. Knows Taylor expansions; complex numbers and
  two-by-two determinants are listed as `outside` prerequisites, but a
  learner at this level need not follow an eigenvalue argument to choose a
  method.
- **Central question.** Which update rule can a long simulation trust, and
  for what: an accurate state over a few periods, or the energy over a
  thousand?
- **Counterintuitive points.** (a) Symplectic Euler costs the same as
  explicit Euler and has the same order, yet keeps the energy bounded for
  ever: one reordered line changes the long-run behaviour, not the order.
  (b) The highest-order method, Runge-Kutta 4, is the most accurate over a
  short run and still drains energy steadily over a long one. (c) A bounded
  energy is not an accurate state (the phase drifts).
- **Target misconceptions.** "Higher order is better for everything."
  "More force evaluations means a better method." "If the energy stays in a
  band, the trajectory is right." "Below the stability limit means
  accurate."
- **Archetype.** Model or simulation (a method comparison). Journey: the
  question, the four rules, what each predicts (order, energy, stability),
  a first check by the learner (the explorer), the measured comparison
  against the exact motion, the rule that follows, where it stops holding.
- **Why this sequence suits the subject.** The choice of method rests on
  three results per rule (order, energy behaviour, stability limit), not on
  their derivations. Before, the learner reached the first run of the
  methods only after two pages of complex numbers, matrices, eigenvalues,
  and modified energies, and the explorer only after every worked example.
  After, the rules are read together with their code, the three results
  are stated with a plain reason (the exact motion is a rotation; Euler and
  Runge-Kutta scale the energy by a factor per step; the symplectic pair
  preserve phase-space area and a nearby energy), and the learner tests
  them at once in the explorer by coarsening the step: the prediction
  ("which curves survive four steps per period?") meets the evidence where
  the counterintuitive points are visible (explicit Euler runs away, the
  other three survive but are not accurate). The worked examples then
  measure each question, and the derivations are one link away, verbatim,
  for the learner who wants the proof.

## Before-and-after reading map (criterion 2)

| Moment | Before | After |
|---|---|---|
| Main question | Introduction | Introduction, with the route (rules with their code, the explorer, the measurements, the derivations one link away); answered by the rule at the end of the worked examples |
| First physical intuition | Explanation, after seven assumptions: where should the rates be taken | Explanation, directly after the introduction: the same |
| The essential choice of update rule | Explanation, the four rules; their code in "The program", after the energy derivations | Explanation, the four rules, each followed by its stepper (exact, the update-order lines annotated) |
| Energy and stability | Explanation: the complex-number factor, the matrices, eigenvalues, the modified energies, then the summary | Explanation: the results with a plain reason (rotation, factor per step, preserved area, modified energy) and the summary; the derivations in "The energy of one step, in depth" (`#energy-in-depth`) |
| First experiment | Worked examples, after the assumptions, the explanation, and the program: four methods at fifty steps per period | The explorer (`#interactive-visualization`), directly after the explanation: the learner coarsens the step and tests the summary |
| Prediction moment | The explorer's question, after every worked example | The same question, now asked where the learner has just read the stability limits, and answered by the explorer's tables; the long-run question before the thousand-period table stays |
| Interpretation | After each table and figure | Unchanged, plus the answer to the explorer's question (surviving is not being accurate) |
| Key derivations | In the explanation | Verbatim in `#energy-in-depth` (three linkable subsections), after the worked examples that check them; the Taylor and Simpson arguments for the orders stay in the explanation |
| Assumptions | First section, before any physics | After the explorer, before the program; their first encounter is one sentence in the introduction, and the complete list is unchanged |
| Conclusion | The rule at the end of the worked examples; Limits | Unchanged |

**Stayed unchanged, and why.** Every equation (the moved ones verbatim),
claim (text, type, scope, evidence), value, table, figure, caption, alt
text, both Go deeper boxes (the Liouville one moves with the matrix
argument it refers to), Limits, the self-check, the exercises and their
solutions (their excerpts included), the reproduction section, and the
front matter. The order-of-accuracy argument and the Simpson weights stay
in the explanation: the cost example and the accuracy table rest on the
orders. The worked examples stay in their order: they are the
measurements, each answering one of the three questions. Every heading
keeps its identifier; the new depth section and its subsections get
explicit ones. No page links to an anchor of M5 (searched in `site`,
`docs`, `src`, `tests`); the widget tests find the explorer by
`#integrator-explorer`.

## Display of the code (criterion 6)

| Block | Purpose | Form |
|---|---|---|
| `integrators.symplectic_euler_step` | The numerical update: the velocity-first order | Exact, without its docstring (the rule above says the same), notes unchanged; moved under its rule |
| `integrators.verlet_step` | The numerical update: the Taylor position, the predicted velocity, the trapezoid | Exact, without its docstring (the rule and the notes say it), notes unchanged; moved under its rule |
| `integrators.rk4_step` | The numerical update: four rates, the weights | Exact, without its docstring (the rule says it), notes unchanged; moved under its rule |
| `experiment.draw_update_orderings` | None (a conceptual sketch's drawing; computes nothing) | Figure source link |
| `experiment.run`, region `explorer` | Validation of the widget: its data come from the tested integrators | Exact region, moved with the explorer |
| `integrators.Integrator` | The list the experiments loop over, with order and cost | Exact full, unchanged |
| `experiment.methods` | None (builds a table) | Source link |
| `experiment`, regions `setup`, `coarse`, `step-counts`, `twenty-periods` | The inputs of each example | Exact regions, unchanged |
| `experiment.counted` | Cost measurement: the counting wrapper (assumption five) | Exact full, unchanged |
| `experiment.run_method` | The one interface: the integrator goes in as `step` | Exact full, unchanged |
| `experiment.after_three_periods` | The comparison: each method's run and its final energy, and the exact end | Exact selection, lines 6 to 9 and 19; the table layout behind the Source link |
| `experiment.draw_integrators_phase_space` | None (plots the runs of the table against the exact orbit, as the prose says) | Figure source link |
| `experiment.state_error` | The error measure the accuracy rests on | Exact full, unchanged |
| `experiment.error_orders` | The errors and the observed order | Exact selection, lines 4 to 9 and 19; the table layout behind the Source link |
| `experiment.draw_integrators_convergence` | None (plots the table's errors; the reference lines' slopes are stated in the caption, their heights placed by hand, as the prose now says) | Figure source link |
| `experiment.draw_integrators_energy` | None (plots the relative energy of the runs, as the caption says) | Figure source link |
| `experiment.relative_energy`, `ratios`, `spread` | The validation quantities | Exact full, unchanged |
| `experiment.energy_formulas` | Validation: the derived formulas in code beside the runs | Exact full, unchanged |
| `experiment.long_run_energy_bands`, `calls_for_one_millimetre` | The long-run bands; the prediction of the steps from the order | Exact full, unchanged |
| Exercise solutions | Unchanged | Unchanged |

No generated signature is used: every stepper's header is short and its
types (a `State`, an `Acceleration`) are the concept.

## The explorer (criterion 10)

Moved, with its markup, static figure, controls note, three tables, data
cell, and module cell, as one block; only the prose before and after it
changes (it names the summary's stability limits it tests, and the page
answers its question from the tables already shown). No change to
`site/widgets/integrator-explorer.js`, `src/pbc/mechanics/explorer.py`,
the widget data, or `tests/e2e/test_widgets.py`.

## The sequence review of M1 to M5 (criterion 11)

Two bridges are added in M5 itself, in the energy results of the
explanation: the rotation is drawn in M4's phase space (with $v/\omega$),
and the stability limit is named as the oscillator's form of M2's
instability (explicit Euler on a fall with drag, step above $2\tau$).
Recorded on the Issue as a comment: progression, bridges added or
proposed, M2 and M4 as comparison cases (no change to them; a needed
scientific correction is recorded as separate work), and the F177
interaction candidates of M1 and M3 against the static sequence. The
owner's decision on the pilot approach is asked for on the Issue after the
review; it is not assumed (the Issue's instructions).

## Steps

1. The introduction: the question, the route, the assumptions in one
   sentence with a pointer.
2. The explanation: the four rules, each stepper under its rule; the
   ordering sketch with a Figure source link; order of accuracy; the energy
   results with a plain reason and the summary, pointing to the depth
   section.
3. The explorer moved after the explanation, its question tied to the
   summary and answered after its tables.
4. Assumptions after the explorer, wording "below" corrected where the
   results now stand above.
5. The program: the interface, `Integrator`, the methods table.
6. The worked examples: the selections and Source links of the display
   table; the energy check points to the depth section.
7. "The energy of one step, in depth" (`#energy-in-depth`): the three
   derivations verbatim, with the Liouville Go deeper box.
8. The experiment's table caption and docstring.
9. The lesson-source checks, the experiment's unit tests, the single-page
   render; screenshots at desktop and phone widths; the targeted
   verification last (`--base` is not needed: no front matter changes).
10. Criteria 1, 2, the sequence review, and the request for the owner's
    decision recorded on the Issue. Criteria 7, 8, and the decision of 11
    follow the session.
