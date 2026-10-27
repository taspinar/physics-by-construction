# Plan: Issue #301, F80 — Applied capstone: adaptive phased-array beam steering (EM9)

- Issue: #301 (source: `docs/roadmap.md`, F80)
- Branch: `feature/301-applied-capstone-adaptive-phased`
- Base commit: `90d181e`
- Risk: Level 2 (Medium) by its paths: one new lesson, one new module of
  `src/pbc/electromagnetism/`, its experiment, and tests; four tests of the
  home and the atlas change their expectation because EM9 becomes published
  (no assertion is dropped: planned capstones are still asserted planned,
  EM9 published). The scripts derive any trigger the diff hits.
- Governing documents: `docs/architecture.md` ("Applied capstone and
  numerical-engineering lesson", the lesson model, the placement rule),
  `docs/authoring.md` (format 2, the experiment of a lesson), ADR 007 (an
  optional tool's output is a `modelled-reference` card), ADR 013 (slots),
  ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F78, F71 delivered; F113 read as the owner's interim
  full-run gate (up to 110 lessons, #281). The site has 56 lesson pages; 57
  after this feature.

## Design

One lesson, `adaptive-phased-array-beam-steering`, slot EM9, in the
`electromagnetism` strand at the next free order, 7 (the placement rule;
EM7 and EM8 are gated measured-data labs and take later orders). NumPy and
SciPy only; the experiment runs in a few seconds.

Code: `pbc.electromagnetism.arrays`, built on `antennas.array_factor` and
`antennas.half_wave_dipole_pattern` of EM6 (no second solver): element
positions of a linear array, the direct-sum array factor in the plane of the
array, steering weights, the least-squares null projection, the closed-form
uniform array factor, peak search (bounded search polished by the root of
the derivative), the grating-lobe onset by bisection, phase quantisation
with fixed per-element insertion phases, the exact expected power pattern
under independent element errors, realised gain, the Dolph-Chebyshev taper,
the dipole element along the array axis.

The capstone workflow on the page (architecture, item 2), for a
hypothetical 16-element array at 10 GHz, band 9.5 to 10.5 GHz, scan within
50 degrees, a moving receiver and a fixed interferer:

| Step | Check against |
|---|---|
| Requirements | stated, hypothetical, typed in the page as given values |
| Model verified | direct sum against the closed-form array factor (round-off); peak at the commanded angle (round-off); first nulls at sin psi0 ± lambda / (N d); symmetries: mirror and translation in sin psi |
| Spacing | grating-lobe onset by bisection against lambda / (1 + sin psi0), the offset of the threshold predicted to leading order |
| Amplitude control | Dolph-Chebyshev peak sidelobe equal to the design level; taper loss |
| Null | depth of the ideal null at round-off; gain cost against 1 - r^2 (closed form for equal amplitudes) |
| Quantisation | rounding without insertion phases: quantisation lobes (failure mode); with them, mean gain loss against sinc^2 and mean null depth against the exact expectation, by Monte Carlo with a fixed seed |
| Noise | random amplitude and phase channel errors: mean gain loss and mean null fill against the exact expectation |
| Frequency | beam squint of phase steering against arcsin((f0 / f) sin psi0); null depth across the band (failure mode) |
| Element pattern | total pattern of dipoles along the axis: peak pulled toward broadside, scan loss |
| Tracking | the receiver passing on a road, interferer fixed: weights recomputed per step, null only where it costs at most 3 dB (feasibility rule); gain and null depth over the pass of one realised array |
| Decision | the number of phase-shifter bits from the measured 90th percentile of the null depth with the channel-error budget; the spacing from the onset at the top of the band |

No full-wave element reference is used (the optional criterion is not
applicable); no widget (the static sequence is the page).

## Visual deliverables

Scientific figures, each `simulated`, drawn by `draw_` functions of the
experiment from the tested code, colours from `FIGURE_COLOURS` with line
style or marker as well, alt text without computed values:
`fig-steered-pattern`, `fig-grating-lobes`, `fig-taper-and-null`,
`fig-quantisation`, `fig-tracking-sequence` (the preview: the verified
sequence of patterns as the receiver passes), `fig-tracking-history`.
Squint and element pattern are shown by their tables (discovered in
verification: with eight figures the page transferred 3.33 MB, over the
3 MB budget; the two figures were dropped and the dense pattern plots
thinned to two curves each, which brought the figures from 1.21 MB to
0.71 MB without raising the budget).

Scientific validation: each figure shows quantities that a check of the
lesson or its unit tests asserts. Accessible fallback: the alt text and the
result tables; nothing moves.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_arrays.py`: each function against a closed form or a
  limit.
- `tests/unit/test_adaptive_phased_array_beam_steering_experiment.py`.
- `tests/unit/test_home.py`, `tests/unit/test_atlas.py`, `tests/e2e/test_home.py`,
  `tests/e2e/test_atlas.py` (discovered in implementation): they assumed
  every capstone planned. The unit tests keep their planned assertions on a
  path without the capstone lessons and add one that EM9 is published and
  linked; the end-to-end tests assert each capstone's state from the path.
- `tests/lessons`, the lesson source checks.
- `./scripts/verify.sh --base` (a new lesson; the home and the atlas change
  what they show of EM9).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The capstone rule | implementation |
| Steering angle, null depth, grating-lobe onset against analytic expressions | implementation |
| Quantisation and noise degradation measured | implementation |
| Optional full-wave reference declared as `modelled-reference` | implementation (not applicable: none used) |
| Deterministic preview figures from the verified sequence; any interactive enhancement degrading to them | implementation |
