# Plan: Issue #420, F104 phase 2 — Exoplanet light curves lab (AST8)

- Issue: #420 (source: `docs/roadmap.md`, F104); phase 1 (card, dossier,
  sample, reference figure) is merged with its `go`.
- Branch: `feature/420-ast8-exoplanet-light-curves-lab`
- Base commit: `3b6b5ab`
- Written by the implementer: no plan existed when phase 2 started (the
  owner's word of 2026-11-12 on the Issue).
- Roadmap row checked (owner's rule of 2026-11-07): F104 is listed, not
  retired, and the slot AST8 is planned in `site/curriculum.yaml`.
- Risk: Level 2. Paths: one new lesson, a new experiment module, one adapter
  added to `src/pbc/data/adapters.py`, new tests and one new test function
  in an existing test file, and the line "Open items" of the dossier
  `docs/datasets/tess-exoplanet-light-curves.md` brought up to date (it
  said that phase 2 waits for the owner). No existing assertion, tolerance, budget, test,
  dependency, or published claim changes; no protected path. The lesson
  fills the planned slot AST8 with `lesson.slot`; `site/curriculum.yaml` is
  not edited, but the learning path and the course headers change (a new
  lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007, ADR 013,
  ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`; section 8.4
  of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/tess-exoplanet-light-curves.md` and the card
  `data/registry/tess-exoplanet-light-curves.yaml`.

## Findings that shape the design

- The dossier's analysis chain is already source-controlled and tested in
  `pbc.data.reference.tess_wasp18` (dips found in the data, normalisation by
  a parabola per transit, the shape fit, mid-times, ephemeris, sensitivity).
  The lab reuses it: no second implementation of the same fit, so no test
  of two fits against each other is needed (EM8 needed one because its fit
  was its own).
- The model is AST7's: `pbc.astrophysics.transit` (`overlap_area`,
  `durations`, `central_depth`, `grid_flux`, `quadratic_limb`). The ring sum
  over the limb-darkened star and the 2-minute exposure average are in the
  reference module (`limb_flux`, `model_flux`), built on `overlap_area` and
  validated by the dossier against AST7's closed forms. No code moves (no
  refactor of a merged module); the page checks the ring model against
  AST7's closed forms and grid itself, as a numerically-verified claim.
- Prototype numbers from the committed sample (2026-11-12): p = 0.09795 ±
  0.00039, a = 3.437 ± 0.035, b = 0.400 ± 0.027, u1 = 0.237 ± 0.047,
  u2 = 0.266 ± 0.088; reduced chi-square 1.16 on 4,814 degrees of freedom.
  Derived, propagated with the full covariance (J C Jᵀ): depth 10,696 ±
  29 ppm, T14 = 2.1878 ± 0.0050 h, T23 = 1.720 ± 0.011 h, ingress 14.04 ±
  0.38 min, inclination 83.32 ± 0.52°, density 867 ± 26 kg/m³. Propagated as
  if the parameters were independent the depth error would be 244 ppm and
  the T14 error 0.031 h: the correlations (a with b −0.98) matter, and the
  page says so. The lab propagates through the covariance in its own
  function, since `pbc.data.uncertainty.propagate` is for independent inputs.
- A uniform star (AST7's closed form, u1 = u2 = 0) fitted to the same
  cadences gives chi-square 6,425 against 5,593 for the limb-darkened model
  (reduced 1.33 against 1.16): the data need limb darkening. Honest model
  comparison, shown with residuals.
- Discrepancies to report, none hidden: the mid-times scatter 1.5 times
  more than their errors (chi-square 41.8 for 19); the reduced chi-square
  1.16; the density from the transit (867 kg/m³) is 20 % above the one the
  TIC values of the FITS header imply (693 kg/m³, no uncertainty given); the
  straight baseline makes the transit 196 ppm deeper; the crowding and
  systematics corrections of the pipeline are not bounded.
- Sensitivity of the normalisation: a single pass (normalise and shape fit
  on the final ephemeris) reproduces the dossier's table (p 0.09769,
  0.09818, 0.09905) in 2.7 s, against 11 s for the full re-analysis per
  variant; the page uses the single pass, which keeps the render budget.
- No comparison with published literature values: the dossier leaves it to
  the lab, but every such number would need a verified source; the lab
  compares only with the values in the file (the TIC header values) and
  says that it makes no literature comparison.

## Design

One lesson, `exoplanet-light-curves`, slot AST8, strand and course
`astrophysics`, order 9 (the next free order), difficulty 2,
`methods: [measured-data]`, prerequisite `exoplanet-transit`, path
`site/lessons/astrophysics/09-exoplanet-light-curves/index.qmd`.

Learning outcomes:

1. Clean a real photometric time series: what the quality flags and the
   missing values remove, and why the measured flux stays apart from the
   detrended signal and the model.
2. Detrend each transit by a baseline fitted outside it, and say why the
   baseline of this star is curved.
3. Fit the AST7 transit model with limb darkening to the folded transits and
   report the radius ratio, impact parameter, depth, and duration with
   standard errors propagated through the correlations of the fit.
4. Judge the result by the reduced chi-square, the mid-time scatter, a
   simpler model, the sensitivity to the normalisation, and an independent
   value, and say what none of them bounds.

Code:

- `src/pbc/data/adapters.py`: `light_curve_series`, the PDCSAP flux as a
  `calibrated-observation` `Series` with the pipeline's error.
- `src/pbc/astrophysics/experiments/exoplanet_light_curves.py`: the
  experiment of the page: the AST7 check of the ring model, the cleaning
  accounting, one transit's detrending, the analysis of the reference
  module, the uniform-star comparison fit, the derived geometry with
  correlated propagation, the mid-time test, the normalisation sensitivity,
  the density check, figures, exercises.

Page sections: opening question; assumptions; explanation (what a light
curve is, cleaning, detrending and the tidal baseline, the fitted model and
its five parameters, error propagation with correlations); code; worked
examples (the model checked against AST7; the data card; cleaning; the
light curve as released; detrending one transit; the fit; the uniform star;
the geometry and its uncertainties; the mid-times; the normalisation
sensitivity; the density check; what the lab shows); limits; self-check;
exercises; run this experiment.

Claims (typed): numerically-verified for the ring model against AST7's
closed forms and grid; observational for the cleaning counts and the dips
seen in the calibrated flux; experimentally-supported for the fitted
geometry with its uncertainties (scope: the circular-orbit dark-disk model
with quadratic limb darkening, the pipeline's errors, corrections taken as
released), for the uniform star being worse, for the mid-time excess
scatter, and for the density difference; the normalisation table stated as
a sensitivity, never as a bound.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-light-curve`: the PDCSAP flux in e-/s as released over the sector
  (every finite value, the flagged cadences with a value marked apart), and
  two days of it with the pipeline errors. Status `calibrated`.
- `fig-detrending`: the flux outside the transits folded on the orbital
  phase (each orbit over its median, binned: the curved baseline seen in
  the data), one transit in e-/s with the cadences of the baseline and the
  fitted parabola (dashed, a model), and the same transit divided by the
  parabola. Status `processed`. (Changed while rendering: the straight line
  and the parabola of one transit differ by less than the scatter, so the
  figure shows the phase curve instead; the straight line stays in the
  sensitivity table and the prose.)
- `fig-transit-fit` (the preview): the 21 normalised transits folded, in
  6-minute bins with standard errors, the limb-darkened fit dashed and the
  uniform-star fit dotted, apart; binned residuals of both. Status
  `processed`, `check_figure(residuals=True)`.
- `fig-mid-times`: observed minus computed mid-time of each transit with
  its error, the ephemeris line. Status `processed`.

Every figure: `fig-dataset: tess-exoplanet-light-curves`, the MAST/TESS
acknowledgement by `add_credit`. Scientific validation: the numbers drawn
are asserted by `tests/unit/test_exoplanet_light_curves_experiment.py` and
the dossier tests; `check_figure` on every figure. Accessible fallback: alt
text without computed values; the cleaning, fit, geometry, and sensitivity
tables carry every number.

## Runtime and payload estimate

Budgets: a lesson page warns at 30 s and fails at 60 s of single-page render
(`scripts/lesson-budgets.conf`); the payload of a page is at most 3 MB.

- Render time: the experiment about 9 s (analysis 3.6 s, uniform fit 1.1 s,
  sensitivity 2.7 s, propagation and AST7 check under 0.1 s, four figures
  about 2 s) plus Quarto's fixed cost of a page (about 15 s warm): about
  25 s, under the 30 s warning. Measured: 27.1 s for the first
  `quarto render` of the page alone in this worktree (2026-11-12); the
  experiment as a program 10.5 s.
- Payload: four PNGs kept under 0.75 MB together by a test, the HTML about
  0.2 MB: about 1 MB, a third of the budget. The 704 KB sample is read at
  build time and not shipped. Measured in the single-page render:
  `index.html` 176 KB, the figures 197, 202, 210, and 88 KB (697 KB).

## Verification

- `tests/unit/test_exoplanet_light_curves_experiment.py`: the page and the
  results agree; the numbers of every claim; the correlated propagation
  against a Monte Carlo draw from the covariance; the uniform star worse;
  figure conventions and statuses; no numeric console block; figure
  payload.
- `tests/unit/test_data_analysis.py`: the new adapter.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at 1280 x 800
  and 390 x 844. The full and `--base` verification is left to the script
  after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson AST8 testing the AST7 model against the card's measurements | implementation |
| Cleaning and detrending shown; measured flux apart from the detrended signal and the model | implementation |
| Depth, duration, impact parameter, radius ratio with uncertainties; discrepancies reported | implementation |
| Every claim typed with its evidence, no claim wider than data and model | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
