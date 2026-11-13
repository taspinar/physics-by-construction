# Plan: Issue #439, F85 phase 2 — Brownian motion tracking lab (T8)

- Issue: #439 (source: `docs/roadmap.md`, F85); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`.agents/plans/439-t8-trackpy-dossier.md`). Phase 2 started by the owner's
  word of 2026-11-13 on the Issue.
- Branch: `feature/439-t8-brownian-motion-lab`
- Base commit: `0a9e160`
- Written by the implementer: no phase 2 plan existed.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F85 is
  present and not retired.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/thermodynamics/brownian.py`, a new experiment module, one adapter
  added at the end of `src/pbc/data/adapters.py`, new tests. No existing
  assertion, tolerance, budget, protected path, or published claim changes.
  The lesson fills the planned slot T8 with `lesson.slot`;
  `site/curriculum.yaml` and `site/atlas.yaml` (which already lists T8) are
  not edited, but the learning path and the course headers change (a new
  lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/trackpy-bulk-water.md` and the card
  `data/registry/trackpy-bulk-water.yaml`.

## Findings that shape the design

- T1 (`random-walks-and-diffusion`) derives MSD = 2 d D t (4 D t in the
  plane) from independent steps and estimates D with a line through the
  origin (`pbc.thermodynamics.diffusion.diffusion_coefficient`). It never
  meets a camera, a drift, or a temperature.
- A camera does not see positions at instants: it averages them over an
  exposure tau_e and adds a localisation error sigma. For Brownian motion
  the measured MSD is then 2 d D (tau - tau_e/3) + 2 d sigma^2 for
  tau >= tau_e: still a straight line of slope 2 d D, with an intercept,
  and successive steps correlated by (D tau_e/3 - sigma^2) / var(step) per
  axis (+1/4 for blur over a whole frame without noise). This is the model
  the lab tests, with T1's walk as its engine.
- Numbers from the committed sample (the reference module, reproduced):
  596 tracks of at least 15 frames, drift 0.55 µm/s, D = 0.403 ± 0.010
  µm²/s (bootstrap over tracks), intercept -0.036 µm²; T1's estimator
  through the origin gives 0.373; Stokes–Einstein 0.429 (20 °C) and 0.491
  (25 °C); processing choices 0.377 to 0.411.
- The camera model does not explain the data: the local slope of the MSD
  grows from 0.33 to about 0.42 µm²/s over the ten lags (the model is a
  straight line), the intercept is more negative than blur over a whole
  frame can make it, and with the measured intercept the model predicts a
  step correlation of about 0.4 where 0.14 is measured. The lab reports
  this as not understood.
- Uncertainty assumptions, checked on the data (pitfall 6): the bootstrap
  assumes independent tracks. The least-squares error of the slope, which
  assumes independent MSD points, is 0.004 against the bootstrap's 0.010
  (the bootstrapped MSD at lags 1 and 10 correlate by about 0.5, adjacent
  lags by 0.99). D from the four quarters of the field scatters by 0.028
  against the 0.020 the bootstrap predicts for a quarter, and the top and
  bottom halves differ by about two of their combined errors: the bootstrap
  may understate the spread across the field; the page says so. A particle
  whose track broke may appear as two tracks; few candidates exist (about
  9 of 596), so the tracks are close to independent.

## Design

One lesson, `brownian-motion-tracking`, slot T8, strand and course
`thermodynamics`, order 11 (the next free order), directory
`site/lessons/thermodynamics/11-brownian-motion-tracking`, difficulty 2,
`methods: [measured-data]`, prerequisite `random-walks-and-diffusion`.
Preview `fig-msd`.

Learning outcomes:

1. Tell the measurement from the processing in a tracking experiment: the
   video frames as recorded, the positions and tracks as this project's
   processing, the drift, the MSD, and the fit as analysis.
2. Extend T1's random walk to what a camera records (exposure, localisation
   error), check the formula on simulated walks, and state its prediction:
   a straight MSD of slope 4D with an intercept.
3. Infer D from the drift-corrected MSD with a bootstrap over tracks, check
   the assumptions of that error on the data, and set the sensitivity to
   the processing beside it.
4. Compare D with Stokes–Einstein, say what the record leaves open (the
   temperature, the size, the exposure), and say where the data depart from
   the model.

Code:

- `src/pbc/thermodynamics/brownian.py` (new): `stokes_einstein`,
  `camera_msd` (the blurred and noisy MSD), `camera_step_correlation`, and
  `camera_walks` (T1's `random_walks` at fine sub-steps, averaged over an
  exposure, with Gaussian localisation noise).
- `src/pbc/data/adapters.py`: `track_series`, one coordinate of one track
  in µm against time in s as a `processed-measured` `Series` (added at the
  end).
- `src/pbc/thermodynamics/experiments/brownian_motion_tracking.py` (new):
  the camera check, the record's landmarks, the MSD and the fit (the
  reference module's `analyse`), T1's estimator, Stokes–Einstein, the
  sensitivity table, the uncertainty checks, the local slopes and the
  consistency of the camera model, the figures, the exercises.

Page sections: opening question; assumptions; explanation (from T1's walk
to a sphere in water; Stokes–Einstein; what a camera records; the tracking
as processing); code; worked examples (the camera model against simulated
walks; the measurement and its card; the tracks; the MSD and D; against
Stokes–Einstein; the processing choices; are the errors honest; what the
camera does not explain; what the lab shows); limits; self-check; exercises
(the time to move one diameter; the size the data imply); run this
experiment.

Claims (typed): observational for the record's landmarks (frames, features
per frame, tracks); numerically-verified for the camera check;
experimentally-supported for the drift, D and its error, T1's estimator,
the Stokes–Einstein comparison, the sensitivity range, the uncertainty
checks, the local slopes and the inconsistency of the camera model, the
non-Gaussian steps, each scoped to frames 000–039 of this video, the
README's calibration taken as exact; not-verified for background physics
(hindered diffusion near a wall, polydispersity).

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-frame`: a corner of frame 000, the green channel as recorded, grey
  levels with a colour bar; status `measured`,
  `fig-dataset: trackpy-bulk-water`, credit on the figure.
- `fig-tracks`: the same corner with the features of frame 000 and the
  tracks of 40 frames, and the drift of the whole sample against time;
  status `processed`.
- `fig-msd` (preview): the drift-corrected MSD with bootstrap bars, the
  fitted line dashed, T1's line through the origin and Stokes–Einstein at
  20 and 25 °C dotted (straight lines drawn from their two ends), residuals
  below; status `processed`, `check_figure(..., residuals=True)`.
- `fig-steps`: the one-frame steps after the drift on a log scale against
  the Gaussian of their variance; status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_brownian_motion_tracking_experiment.py` or the dataset
tests; `check_figure` on each; a byte-identity test draws each figure
twelve times. Accessible fallback: alt text without computed values; the
record, MSD, Stokes–Einstein, sensitivity, and uncertainty tables carry the
numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: the analysis with 1,000 bootstrap resamples about 0.1 s, the
  sensitivity 0.2 s, the camera check about 1 s, four figures about 3 s.
- Payload: four PNGs under 0.65 MB together, kept at least 15 % under it
  locally (pitfall 4); the frame shown as a small crop, not the 814 kB of
  the three frames.

## Verification

- `tests/unit/test_brownian.py`: the model functions (Stokes–Einstein
  against the dossier, the camera MSD and correlation in their limits,
  `camera_walks` against the formulas, seeded).
- `tests/unit/test_brownian_motion_tracking_experiment.py`: the page and
  the results agree; D and the drift equal the reference module's; the
  numbers of every claim; the uncertainty checks; figure conventions;
  byte-identical figures; no numeric console block; figure payload; the
  adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson T8 testing the T1 model against the card's tracks | implementation |
| MSD against lag, D with the bootstrap and the processing range, Stokes–Einstein with its assumed temperature and viscosity | implementation |
| The tracking disclosed as processing: frames as measured, tracks processed, MSD, fit and model apart; blur and the caveats stated | implementation |
| Every claim typed with evidence; discrepancies reported | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
