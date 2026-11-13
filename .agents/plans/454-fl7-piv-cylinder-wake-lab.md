# Plan: Issue #454, F53 phase 2 — the cylinder-wake PIV lab (FL7)

- Issue: #454 (source: `docs/roadmap.md`, F53); phase 1 (cards, dossiers,
  samples, reference figures, `go`) is on `main`
  (`data/registry/piv-cylinder-wake.yaml`,
  `data/registry/ost-hotwire-cylinder-wakes.yaml`, their dossiers under
  `docs/datasets/`; plan `454-fl7-cylinder-wake-dossier.md`). Phase 2
  started by the owner's word of 2026-11-13 on the Issue.
- Branch: `feature/454-fl7-piv-cylinder-wake-lab`; base commit `655ab03`.
- Roadmap row checked (owner's rule of 2026-11-07): F53 is present and not
  retired; FL7 is the planned slot "Experimental: particle image
  velocimetry" of `site/curriculum.yaml`.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/fluids/piv.py`, a new experiment module, two adapters in
  `src/pbc/data/adapters.py` (alphabetical position by dataset module), new
  tests. No existing assertion, tolerance, budget, protected path, or
  published claim changes. The lesson fills the planned slot FL7 with
  `lesson.slot`; `site/curriculum.yaml` is not edited, but the learning
  path and the course headers change (a new lesson): verification tier
  `--base`.
- Order: orders within a strand run from 1 without gaps
  (`pbc.authoring.path`), so the lab is `fluids` order 8, directory
  `site/lessons/fluids/09-cylinder-wake-piv-lab`. FL8 (#441, open branch)
  also takes order 8: whichever merges second renumbers to 9 and renames
  its directory (recorded in the handoff note).
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md`, ADR 007, ADR 009, ADR 013, ADR 016, ADR 019, ADR 020;
  the lab rule of `docs/roadmap.md`; section 8.4 of
  `docs/changes/physics-next-phase.md`.

## Findings that shape the design

- FL3 (`vortex-formation-and-flow-around-obstacles`) states the model this
  lab tests: St = f D / U; a street of alternating vortices (one period is
  one vortex of each sign); Roshko's stable-range fit for 50 < Re < 150; a
  two-dimensional computation that is valid only in the stable range;
  blockage raises the frequency; the frequency measured from upward
  crossings of the probe signal (`pbc.fluids.vortices.shedding_frequency`).
  Both datasets lie above the stable range (Re = 413 and 8e3 to 5e4): the
  lab does not run FL3's two-dimensional solver there (FL3's own limits say
  it does not describe that regime) and compares with the irregular-range
  fit of Roshko's report as the card states it (St = 0.212 - 2.7/Re,
  `pbc.data.reference.cylinder_wake.roshko`, a `modelled-reference` of the
  card). The lower bound of that fit's range was not re-read here (no PDF
  reader in this environment); the page says "the irregular range, above
  about 300", as the register entry states the regime.
- PIV numbers (reference module, reproduced): f = 0.8887 ± 0.0028 Hz (four
  100 s blocks of the spectral peak at 2 D), 0.889 Hz published; u at
  1.792 Hz, 2.02 f; St = 0.1941 with the paper's D and U; Roshko 0.2055;
  4.52 cm/s in the top row (St 0.187 with it); recirculation to 2.14 D.
- FL3's crossing method on the raw v fails (noise crossings: 0.995 Hz);
  after a zero-phase band-pass of 0.5 to 1.3 Hz it gives 0.8827 ±
  0.0043 Hz (four blocks), 352 periods. The period lengths correlate over
  a few periods only (inside ±2/√N beyond lag three, a 100 s block is
  about 88 periods): the four blocks are close to independent, which is
  the assumption of the block error (pitfall 6).
- The street's symmetry: ω(t + T/2) reflected about the wake axis with its
  sign flipped correlates with ω(t) at 0.67 (mean over frames), as high as
  ω(t + T) with ω(t); without the shift, 0.02.
- Vorticity stencils: central difference (FL3's and the reference
  module's), noise gain σ_ω = σ_u/h for white noise, truncation h²/6 f''';
  the five-point least-squares stencil (2 f₂ + f₁ − f₋₁ − 2 f₋₂)/10h, noise
  gain 0.447 σ_u/h, truncation 17/30 h² f''' (3.4 times larger). On the PIV
  field: free-stream ω standard deviation 0.70 1/s (central) and 0.41 1/s
  (least squares), ratio 0.59, not the 0.447 of white noise: the vectors
  are correlated between neighbours (neighbouring u fluctuations correlate
  at 0.88; the 50 % window overlap); the 99th percentile of |ω| drops from
  21.7 to 15.3 1/s.
- Hot wire: St 0.2125 to 0.2412, ordered by blockage; a straight line of
  St on D/W: slope 0.140 ± 0.036, intercept 0.201 ± 0.007 (errors from the
  residual scatter, runs taken as independent). The continuity ("gap")
  correction St (1 − D/W) overcorrects: it reverses the order (50 mm
  lowest, 0.176). The record's peaks are quoted to ±1 % per run (the
  dossier's spread between 16 s segments of the full record).

## Design

One lesson, `cylinder-wake-piv-lab`, slot FL7, strand and course `fluids`,
order 8, difficulty 2, `methods: [measured-data, simulation]`,
prerequisite `vortex-formation-and-flow-around-obstacles`. Preview
`fig-wake-keyframes`.

Learning outcomes:

1. Tell what a PIV record is: processed velocity vectors from image pairs,
   a mask where there is no light, a grid and a cadence; and what this lab
   derives from it (vorticity, streamlines, spectra).
2. Compute the vorticity with a finite-difference stencil, and state what
   the stencil does to noise and to resolution, checked on an analytic
   vortex.
3. Measure the shedding frequency and the Strouhal number with an
   uncertainty whose assumptions are checked, and test the vortex-street
   picture of FL3 on the measured field.
4. Compare St against Re and blockage across two experiments with FL3's
   expectations, saying what the data support and what they do not.

Code:

- `src/pbc/fluids/piv.py` (new): `central_derivative`,
  `least_squares_derivative`, `vorticity` (stencil, mask dilation by the
  stencil's reach), `NOISE_GAIN`, `TRUNCATION`, `lamb_oseen` (velocity and
  vorticity of an analytic vortex), `band_pass`, `reflect_about`
  (symmetry check of the street).
- `src/pbc/data/adapters.py`: `piv_probe_series` (v or u at a probe,
  `processed-measured`), `hot_wire_series` (one run, `processed-measured`),
  each in alphabetical position by dataset module.
- `src/pbc/fluids/experiments/cylinder_wake_piv_lab.py` (new): the record
  and its landmarks, the stencil check, the field's vorticity with both
  stencils, the symmetry check, the frequency (spectral blocks and FL3's
  crossings after a band-pass) with the period correlation check, St
  against Roshko and the paper's U, the hot-wire table, the blockage line,
  the figures, the exercises.

Page sections: opening question; assumptions; explanation (PIV: what is
measured and what processed; vorticity from a grid, stencils, noise; the
street and its frequency; St, Re and blockage); code; worked examples (the
stencils on an analytic vortex; the measurement and its cards; the vorticity
of the wake; the street in time; the mean wake; the shedding frequency; are
the blocks independent; the Strouhal number; St over Reynolds numbers and
blockages; what the lab shows); limits; self-check; exercises; run this
experiment.

Claims (typed): observational for the records' landmarks; numerically
verified for the stencils on the analytic vortex; experimentally supported
for the frequency, St, harmonic, symmetry, noise ratio, recirculation,
hot-wire St and the blockage line; not-verified for background statements.

## Visual deliverables

Scientific figures only, no diagram, no animation and no browser component
(the Issue: static keyframes where the order in time is the point).
Skills: pbc-scientific-visualization@a70b501

- `fig-wake-keyframes` (preview, processed): ω of three frames a quarter
  period apart (half a period), masked grey, signed colour map with colour
  bar, the probe; and a fourth panel, the mean u over 8000 frames with the
  streamlines of the mean field and the end of the recirculation.
- `fig-vorticity-stencils` (processed): frame 0 with both stencils.
- The stencil check on the Lamb–Oseen vortex is the table `stencil-check`
  (a separate simulated figure and a separate mean-wake figure were dropped
  to keep the payload under 430 kB: 404,840 bytes locally with four
  figures).
- `fig-shedding` (processed): band-passed and raw v at 2 D, spectra of u
  and v with f and 2 f.
- `fig-strouhal` (processed): St against Re (PIV, hot wire, Roshko's
  irregular fit over its range, FL3's stable fit), St against D/W with the
  fitted line (drawn from its two ends) and the gap correction.

Scientific validation: every number drawn is asserted by
`tests/unit/test_cylinder_wake_piv_lab_experiment.py` or the dataset tests;
`check_figure` on each data figure; a byte-identity test draws each figure
twelve times. Accessible fallback: alt text without computed values; tables
carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s; 3 MB payload. Analysis about 2 s; six
figures about 4 s. Figures together < 525,000 bytes in the test and at most
430,000 bytes locally (pitfall 4): small figures, nearest-neighbour images
of a 61 × 46 grid, dpi of the build settings.

## Verification

- `tests/unit/test_piv.py`: stencils exact on quadratic fields,
  second order on the Lamb–Oseen vortex, the 3.4 truncation ratio, the
  noise gains on seeded noise, the mask dilation, band-pass, reflection.
- `tests/unit/test_cylinder_wake_piv_lab_experiment.py`: the page and the
  results agree; numbers of every claim; figure conventions; byte-identical
  figures; no numeric console block; payload; adapters' status; no section
  id equal to a cell label.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at 1280 x 800
  and 390 x 844. The full and `--base` verification is left to the script
  after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson FL7 testing FL3's shedding model against the cards | implementation |
| Vorticity with stated stencil and noise; f and St; St against Re from the hot wire | implementation |
| PIV-derived fields apart from measurements; mask, cadence, caveats stated | implementation |
| Committed subset under the caps; static keyframes instead of an animation | implementation |
| CI on the published head | pr_ci |
| Independent physics review of the claim types | implementation (pending until review-feature.sh) |
| The owner approves the lesson on the rendered page | owner_approval |
