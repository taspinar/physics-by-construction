# Plan: Issue #418, F86 phase 2 — RLC circuit measurements lab (EM8)

- Issue: #418 (source: `docs/roadmap.md`, F86); phase 1 (card, dossier,
  sample, reference figure, the card-count test) is merged with PR #429.
- Branch: `feature/418-em8-rlc-lab`
- Base commit: `769a2bb`
- Written by the implementer: no plan existed when phase 2 started.
- Roadmap row checked (owner's rule of 2026-11-07): F86 is Not started and
  not retired.
- Risk: Level 2 by its paths: one new lesson, an addition to
  `src/pbc/electromagnetism/circuits.py` (a new class, nothing of EM5
  changed), one adapter added to `src/pbc/data/adapters.py`, a new
  experiment module, new tests. No existing assertion, tolerance, budget, or
  published claim changes. The lesson fills the planned curriculum slot EM8
  with `lesson.slot`; `site/curriculum.yaml` is not edited, but the learning
  path and the course headers change (a new lesson): the tier is `--base`.
- Discovered while rendering: the card's `calibration` field, which the
  lab's data card shows, still said the instrument error was "covered by the
  model-error estimate", against the dossier and the owner's correction of
  2026-11-08. One sentence of the card is corrected to the dossier's
  statement (unknown, bounded by neither the standard errors nor the band
  fits). No page of `main` shows this card, so no published claim changes;
  `data/registry` is a sensitive path, named for the reviewer.
- A scale error common to every frequency is invisible to the fit:
  Z(kR, kL, C/k) = k Z(R, L, C) exactly (a unit test), so the page says that
  the resonance and Q are unaffected and R, L, C are not.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007, ADR 013,
  ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`; section 8.4
  of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/bayreuth-rlc-impedance.md`.

## Findings that shape the design

- The record's circuit is a coil (L with the resistance R of its winding) in
  **parallel** with a capacitor; EM5 builds the **series** circuit. The lab
  uses EM5's element impedances and phasor rules and combines them in
  parallel, and says so; it does not pretend that the series formulas
  apply. The undamped frequency 1/sqrt(LC) and Q = sqrt(L/C)/R are the same
  expressions; the |Z| maximum and the phase zero are not at 1/sqrt(LC).
- Closed forms of the parallel circuit (derived on the page, checked
  numerically): the phase of Z is zero at omega0 sqrt(1 - 1/Q^2), where
  Z = L/(R C) exactly (the dynamic resistance). The maximum of |Z| has no
  short closed form; a bounded search finds it.
- Numbers from the committed sample (prototype run, the same fit as the
  reference module): R = 9.537 +- 0.021 ohm, L = 4.849 +- 0.007 mH,
  C = 2.1832 +- 0.0031 uF; f0 = 1546.9 Hz, |Z| maximum of the fit 1546.3 Hz,
  phase zero of the fit 1514.9 Hz, Q = 4.94; highest measured |Z| 222.7 ohm
  at the sample 1584.5 Hz; residual rms 1.1 %, largest 4.3 %. The nominal
  values (9.7 ohm, 5 mH, 2.2 uF) predict f0 = 1517 Hz and miss the data by
  3.8 % rms, 16 % at worst. Band fits: below f0 1539.8 Hz, above 1546.1 Hz,
  R 9.46 and 10.38 ohm: a sensitivity table, not a bound.
- The galvanostatic measurement imposes the current (30 mA amplitude) and
  reads the voltage, so the |Z| peak is a voltage peak of a current-driven
  parallel circuit; the dual of EM5's current peak of a voltage-driven
  series circuit.

## Design

One lesson, `rlc-circuit-measurements`, slot EM8, strand and course
`electromagnetism`, order 8 (the next free order), difficulty 2,
`methods: [measured-data]`, prerequisite `rlc-circuits-and-resonance`.

Learning outcomes:

1. Derive the impedance of a lossy coil in parallel with a capacitor from the
   element impedances of a series RLC circuit, and its three characteristic
   frequencies.
2. Read a measured impedance spectrum for what it is: a processed
   measurement, a sweep of discrete frequencies, no uncertainty per point.
3. Fit R, L, and C with their standard errors, compare them with the values
   printed on the parts, and judge the fit by its residuals and its
   sensitivity to the band, not by its standard errors alone.

Code:

- `src/pbc/electromagnetism/circuits.py`: `CoilParallelCapacitor`
  (impedance, natural frequency, Q, phase-zero frequency and dynamic
  resistance in closed form) and `impedance_peak` (bounded search).
- `src/pbc/data/adapters.py`: `impedance_series`, |Z| or phase of the
  spectrum as a `processed-measured` `Series`.
- `src/pbc/electromagnetism/experiments/rlc_circuit_measurements.py`: the
  experiment of the page (the closed forms checked on the nominal circuit,
  the measured extremes, the fit, the residuals, the band sensitivity, the
  figures, the exercises). The fit is its own (the circuits model through
  `fit_curve`, relative complex residual, as the dossier); a test asserts
  that it equals the reference module's fit.

Page sections: opening question, assumptions, explanation (the parallel
circuit from EM5's impedances, the three frequencies, current drive), code,
worked examples (the closed forms checked; the data card and the measured
spectrum; the prediction from the nominal values; the fit with its table;
the residuals; the three frequencies against the sweep; the band
sensitivity table; the interpretation), limits, self-check, exercises, run
this experiment.

Claims (typed): numerically-verified for the closed forms against the
search on the nominal circuit; observational for the measured maximum and
the phase sign change between samples; experimentally-supported for the
fitted values with their standard errors and the model's three frequencies,
scoped to the three-element model with no calibration known; the band table
stated as a sensitivity of the model fit, never as a plus-minus bound.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-impedance-fit` (the preview): |Z| (log-log) and phase against
  frequency, the measured points as markers without band (the record gives
  none, the legend says so), the model with the nominal values dotted and
  the fitted model dashed, apart; the residual panel (relative, real and
  imaginary part, %). Status `processed`, `fig-dataset:
  bayreuth-rlc-impedance`, credit on the figure.
- `fig-resonance-detail`: the samples around the resonance on linear axes
  with the fitted |Z| and phase, the highest measured sample, the fit's
  maximum and phase zero, and f0 marked. Status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_rlc_circuit_measurements_experiment.py` or by the sample
tests; `check_figure` on both. Accessible fallback: alt text without
computed values, the fit table, the frequency table, the sensitivity table.

## Verification

- `tests/unit/test_coil_parallel_capacitor.py`: the closed forms of
  `CoilParallelCapacitor` against the admittance sum and a root search; the
  peak search; the common scale. `tests/unit/test_data_analysis.py`: the
  new adapter.
- `tests/unit/test_rlc_circuit_measurements_experiment.py`: the page and the
  results agree; the fit equals the reference module's; the numbers of the
  claims; figure conventions; no numeric console block; figure payload.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at 1280 x 800
  and 390 x 844. The full and `--base` verification is left to the script
  after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson EM8 testing the EM5 model against the card's measurements | implementation |
| Every claim typed with its evidence, no claim wider than data and model | implementation |
| The band fits a sensitivity table, not a bound; the discrepancy reported honestly | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
