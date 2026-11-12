# Plan: Issue #438, F84 phase 2 — Soil temperature measurements lab (T7)

- Issue: #438 (source: `docs/roadmap.md`, F84); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`.agents/plans/438-t7-dwd-dossier.md`). Phase 2 started by the owner's
  word of 2026-11-12 on the Issue.
- Branch: `feature/438-t7-soil-temperature-lab`
- Base commit: `1182770`
- Written by the implementer: no phase 2 plan existed.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F84 is
  present and not retired.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/thermodynamics/periodic_conduction.py`, a new experiment module,
  one adapter added at the end of `src/pbc/data/adapters.py`, new tests. No
  existing assertion, tolerance, budget, protected path, or published claim
  changes. The lesson fills the planned slot T7 with `lesson.slot`;
  `site/curriculum.yaml` and `site/atlas.yaml` (which already lists T7) are
  not edited, but the learning path and the course headers change (a new
  lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/dwd-potsdam-soil-temperature.md` and the card
  `data/registry/dwd-potsdam-soil-temperature.yaml`.

## Findings that shape the design

- T6 (`heat-conduction-and-diffusion`) solves the heat equation
  dT/dt = alpha d2T/dx2 by FTCS (`pbc.thermodynamics.conduction.ftcs_step`)
  with fixed and convective ends; it never meets a periodic forcing or a
  measurement. Its symbol for the diffusivity is alpha; the lab uses it
  (the dossier's kappa is the same quantity).
- The model the lab tests: a homogeneous half-space whose surface follows a
  cosine of angular frequency omega has the periodic solution
  T = T_mean + A0 exp(-z/d) cos(omega t - z/d - phi0), d = sqrt(2 alpha/omega).
  Two independent predictions: ln A falls linearly in z with slope -1/d, the
  lag rises linearly with slope +1/d, the same d; and the same alpha for the
  year and for the day (d scales as the square root of the period).
- Numbers from the committed sample (the reference module, reproduced):
  annual wave 2015–2024, alpha = 1.015 ± 0.025 (amplitude) and
  1.147 ± 0.009 (phase) × 1e-6 m²/s; daily wave June–August 2020–2024,
  1.084 ± 0.013 and 1.119 ± 0.009; damping depths 3.19/3.39 m and
  0.173/0.175 m; adjacent pairs of depths 0.88 to 2.49.
- Uncertainty assumptions, checked on the data (pitfall 6): the errors are
  standard errors of the mean over 10 years / 5 summers, which assume
  independent periods. Within one year the 6-hourly residuals of the
  harmonic are strongly correlated (about 0.8 at one day, 0.5 at ten days
  at 5 cm), so the least-squares error of one year's amplitude (0.17 K)
  understates the scatter between years (0.78 K) several-fold: that is why
  the between-period scatter is used. Between periods, the lag-one
  autocorrelation of the single-year estimates is negative (−0.34, −0.25),
  inside the band 2/sqrt(10); with five summers the check is weak, and the
  page says so. A third view, the standard error of the straight line in
  depth from the scatter about it (`fit_curve`), treats the departures from
  a straight line as random: it is larger than the between-year error
  (5 % and 4 % for the annual wave), a measure of the inhomogeneity, not a
  bound.

## Design

One lesson, `soil-temperature-measurements`, slot T7, strand and course
`thermodynamics`, order 10 (the next free order), directory
`site/lessons/thermodynamics/10-soil-temperature-measurements`,
difficulty 2, `methods: [measured-data]`, prerequisite
`heat-conduction-and-diffusion`. Preview `fig-depth-profiles`.

Learning outcomes:

1. Read a soil-temperature record for what it is: thermometer readings at
   five depths after the provider's quality control, rows selected, no
   sensor accuracy given.
2. Derive the periodic solution of the heat equation for a cosine surface
   temperature, check it against the T6 explicit scheme, and state its two
   predictions: exponential decay and linear lag with one damping depth.
3. Extract the annual and the daily harmonic at each depth by least squares
   and infer the thermal diffusivity from the amplitude and from the phase,
   with the scatter between years and summers as the uncertainty and its
   assumptions checked.
4. Judge where the homogeneous model fails from the disagreement of the
   estimates and of pairs of depths, and say what the record cannot bound.

Code:

- `src/pbc/thermodynamics/periodic_conduction.py` (new): `damping_depth`,
  `periodic_temperature` (the damped wave), `diffusivity_from_slope`, and
  `periodic_ftcs` (T6's `ftcs_step` with the surface held at a cosine, the
  harmonic of the last period at given depths).
- `src/pbc/data/adapters.py`: `soil_temperature_series`, the readings at
  one depth as a `processed-measured` `Series` (added at the end).
- `src/pbc/thermodynamics/experiments/soil_temperature_measurements.py`
  (new): the readings and their landmarks, the harmonic fits, the FTCS
  check, the depth-line fits with `fit_curve`, the diffusivity table, the
  pairs, the uncertainty checks, the figures, the exercises. Tests assert
  that its diffusivities equal the reference module's.

Page sections: opening question; assumptions; explanation (the periodic
solution; its two predictions; the harmonic of a record); code; worked
examples (the scheme of T6 against the formula; the measurement and its
card; the harmonics of one year and one day; amplitude and lag against
depth; the diffusivity, four ways; are the errors honest (uncertainty
checks); pairs of depths and where the model fails; what the lab shows);
limits; self-check; exercises (a cellar's depth; conductivity from an
assumed heat capacity); run this experiment.

Claims (typed): observational for the measured landmarks (extremes, the
daily range at 5 cm, counts); numerically-verified for the FTCS check;
experimentally-supported for the harmonic amplitudes and lags, the four
diffusivities with their errors, the amplitude–phase discrepancy, the
pairs, and the uncertainty checks, each scoped to station 03987 and the
years used, sensor accuracy and depth tolerance unknown; not-verified for
background physics (water content, freezing).

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-soil-record`: daily means 2015–2024 at five depths (line styles and
  colours), and one summer week hourly; status `processed`,
  `fig-dataset: dwd-potsdam-soil-temperature`, credit on the figure.
- `fig-harmonic-fits`: one year of 6-hourly readings at 5 and 100 cm with
  the fitted annual harmonic, and one summer day hourly at 5–50 cm with the
  fitted daily harmonic; residual panels below. Status `processed`;
  `check_figure(..., residuals=True)`.
- `fig-depth-profiles` (preview): amplitude (log) and lag against depth,
  annual and daily, measured points with one standard error, the model
  lines dashed (drawn from their two ends), residual panels. Status
  `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_soil_temperature_measurements_experiment.py` or the
dataset tests; `check_figure` on each; a byte-identity test draws each
figure twelve times. Accessible fallback: alt text without computed values;
the amplitude, diffusivity, and pair tables carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: the analysis under 2 s (dossier), the FTCS check about 1 s,
  three figures about 3 s; Quarto's fixed cost dominates.
- Payload: three PNGs under 0.75 MB together (asserted with a margin,
  pitfall 4), the HTML about 0.2 MB.

## Verification

- `tests/unit/test_periodic_conduction.py`: the model functions (damping
  depth, the wave solves the heat equation by finite differences of the
  formula, the slope inversion, `periodic_ftcs` against the formula).
- `tests/unit/test_soil_temperature_measurements_experiment.py`: the page
  and the results agree; the diffusivities equal the reference module's;
  the numbers of every claim; figure conventions; byte-identical figures;
  no numeric console block; figure payload; the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson T7 testing the T6 model against the card's measurements | implementation |
| Diffusivity from attenuation and phase of the annual and daily wave, compared with uncertainty | implementation |
| Where the homogeneous model fails; the dossier's caveats on the page | implementation |
| Measured temperatures distinct from fitted waves and from the model; every claim typed with evidence | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
