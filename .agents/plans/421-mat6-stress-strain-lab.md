# Plan: Issue #421, F107 phase 2 — Stress-strain measurements lab (MAT6)

- Issue: #421 (source: `docs/roadmap.md`, F107); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`. Phase 2 started by the
  owner's word of 2026-11-12 on the Issue.
- Branch: `feature/421-mat6-stress-strain-lab`
- Base commit: `3b6b5ab`
- Written by the implementer: no plan existed when phase 2 started.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F107 is
  present and not retired.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/materials/stress_strain.py`, a new experiment module, one adapter
  added to `src/pbc/data/adapters.py`, new tests. No existing assertion,
  tolerance, budget, protected path, or published claim changes; the new
  tolerances sit in new files only. The lesson fills the planned slot MAT6
  with `lesson.slot`; `site/curriculum.yaml` and `site/atlas.yaml` (which
  already lists MAT6 beside MAT3) are not edited, but the learning path and
  the course headers change (a new lesson): the verification tier is
  `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/nist-numisheet-dp980.md` and the card
  `data/registry/nist-numisheet-dp980.yaml`.

## Findings that shape the design

- The MAT3 model is linear isotropic elasticity, sigma = E epsilon, with an
  illustrative steel E = 200 GPa (`elasticity_and_deformation.E`), "chosen,
  not measured"; MAT3 says that beyond yield the model cannot describe the
  metal and that "measured stress-strain curves, a later lesson" show where
  it leaves the line. The lab tests exactly that: the slope, the range of
  the line, and what the model predicts on unloading.
- Numbers from the committed sample (prototype, the reference module's
  functions): first loading 490 rows to the stress maximum 991.3 MPa at
  e = 0.0575; E = 196.3 +- 1.1 GPa with intercept 7.4 MPa in the window
  100–400 MPa (84 points, residual rms 4.4 MPa); windows give 192.5 to
  198.4 GPa; a line through the origin gives 201.5 GPa; MAT3's 200 GPa line
  through the origin leaves 5.4 MPa rms in the window. Offset yields:
  0.02 % 542 MPa, 0.05 % 620 MPa, 0.1 % 689 MPa, 0.2 % 775 MPa (gradual
  yielding, no sharp elastic limit). Unloading from the hold end
  (970.3 MPa, e = 0.0579) to zero stress recovers 0.0068 of strain, where
  an elastic unloading with E would recover 0.0049; chord 950→0 MPa
  143.6 GPa. Loop 75.8 MJ/m³ (closed integral, closing segment
  −0.1 MJ/m³; shoelace equal). Necking at 981.2 MPa, e = 0.091; fracture
  e = 0.177. Preload noise 25 µm/m strain, 0.18 MPa stress.
- The record holds unloading and a load reversal, so hysteresis is shown
  (the Issue: "only if the card's tests contain unloading").
- 200 GPa lies 1.9 % above the fit and outside the window range; the
  record gives no load-cell, extensometer or dimension calibration, and an
  error common to every point scales E alike. The page reports the
  discrepancy and does not decide between a softer steel and a calibration
  error; MAT3's value was illustrative.

## Design

One lesson, `stress-strain-measurements`, slot MAT6, strand and course
`materials`, order 5 (the next free order; MAT5 is not published),
directory `site/lessons/materials/05-stress-strain-measurements`,
difficulty 2, `methods: [measured-data]`, prerequisite
`elasticity-and-deformation`.

Learning outcomes:

1. Read a measured stress-strain test for what it is: stress from a force
   over the original area, strain from an image-correlation extensometer,
   both processed, with no uncertainty per point.
2. Fit Young's modulus to the elastic regime with its standard error,
   compare it with the MAT3 model, and judge the fit by its residuals and
   its sensitivity to the window and to the intercept.
3. Locate the departure from linearity with offset lines and explain why a
   gradually yielding steel has no single elastic limit.
4. Test the model's prediction for unloading against the measured reversal,
   and compute the work per volume of the hysteresis loop with its sign
   convention.

Code:

- `src/pbc/materials/stress_strain.py` (new): the uniaxial MAT3 model and
  its extensions used by the lab: `hooke_stress` (sigma = E epsilon + S0),
  `offset_crossing` (where a curve crosses a line shifted by an offset
  strain), `elastic_unloading` (the line of slope E from a point),
  `closed_loop_work` (trapezoids plus the closing segment, the closed
  integral of S de), `true_stress_strain`.
- `src/pbc/data/adapters.py`: `stress_strain_series`, the engineering
  stress against strain of the test as a `processed-measured` `Series`.
- `src/pbc/materials/experiments/stress_strain_measurements.py` (new): the
  experiment of the page (the measured landmarks, the elastic fit and its
  sensitivity table, the MAT3 comparison, the offset table, the unloading
  test, the loop, the figures, the exercises). Tests assert that its fit,
  offset yield, and loop equal the reference module's.

Page sections: opening question; assumptions; explanation (engineering
stress and strain and what the instruments measure; Hooke's law of MAT3 and
what it predicts on loading and unloading; offset definitions of yield;
the work per volume of a closed loop); code; worked examples (the data card
and the measured path; the elastic fit against MAT3; sensitivity table;
the departure from linearity; the unloading against the elastic
prediction; the hysteresis loop; necking and the true columns; what the lab
shows); limits; self-check; exercises; run this experiment.

Claims (typed): observational for the measured landmarks (stress maximum,
most compressive stress, start of necking, fracture strain, preload
scatter); experimentally-supported for E with its standard error, the MAT3
discrepancy, the offset yields, the unloading recovery and chord, and the
loop work, each scoped to this one test (R01) with the calibration unknown;
numerically-verified for `closed_loop_work` against the exact area of an
ellipse; the sensitivity table stated as a sensitivity, never as a bound.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-stress-strain` (the preview): the whole measured path in its three
  segments (markers and line styles, not colour alone), the loop shaded,
  the stress maximum, the most compressive stress, the start of necking
  marked; status `processed`, `fig-dataset: nist-numisheet-dp980`, credit
  on the figure.
- `fig-elastic-regime`: the first loading to e = 0.012 as measured points,
  the fitted line dashed, MAT3's 200 GPa line dotted, the 0.2 % offset
  line, the fit window shaded; below, the residuals of both lines against
  stress. Status `processed`; `check_figure(..., residuals=True)`.
- `fig-unloading`: the reversal, measured unloading and compression points
  with the elastic unloading of slope E from the hold end (model, dashed)
  and the residual of the measurement against it. Status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_stress_strain_measurements_experiment.py` or the sample
tests; `check_figure` on each. Accessible fallback: alt text without
computed values; the landmark, fit-sensitivity and offset tables carry the
numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: about 20 s for the page alone (one linear fit, five window
  fits, closed-form offsets on 1,607 rows, three Matplotlib figures, about
  3 s; the rest is Quarto's fixed cost). Measured: see the handoff note.
- Payload: about 0.6 MB: three PNGs under 0.75 MB together (asserted), the
  HTML about 0.2 MB.

## Verification

- `tests/unit/test_stress_strain.py`: the model functions (Hooke line,
  offset crossing on a bilinear curve, elastic unloading, the closed loop
  integral against an ellipse and its sign, true stress and strain).
- `tests/unit/test_stress_strain_measurements_experiment.py`: the page and
  the results agree; the fit, yield and loop equal the reference module's;
  the numbers of every claim; figure conventions; no numeric console
  block; figure payload; the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson MAT6 testing the MAT3 model against the card's measurements | implementation |
| Elastic regime and modulus with uncertainty, departure from linearity, plastic regime, hysteresis (the test unloads) | implementation |
| Measured force/displacement-derived quantities kept apart from the model; every claim typed with evidence | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
