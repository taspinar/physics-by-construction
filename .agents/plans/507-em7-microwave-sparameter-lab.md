# Plan: Issue #507, F54 — the microwave S-parameter lab (EM7)

- Issue: #507 (source: `docs/roadmap.md`, F54). The dataset is on `main`
  with its `go`: `data/registry/npl-onwafer-sparameters.yaml`, the dossier
  `docs/datasets/npl-onwafer-sparameters.md`, the four committed files,
  the reader `src/pbc/data/touchstone.py`, the adapter
  `transmission_series`.
- Branch: `feature/507-em7-microwave-sparameter-lab`; base commit `0406b36`.
- Written by the implementer: no plan existed when the session started.
- Roadmap row checked (owner's rule of 2026-11-07): F54 is present and not
  retired; EM7 is the planned slot "Experimental: microwave S-parameters"
  of `site/curriculum.yaml`.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/electromagnetism/two_port.py`, a new experiment module, one
  adapter added to `src/pbc/data/adapters.py` (beside
  `transmission_series`, the adapter of the same reader), new tests. No
  existing assertion, tolerance, budget, protected path, or published claim
  changes. The lesson fills the planned slot EM7 with `lesson.slot`;
  `site/curriculum.yaml` is not edited, but the learning path and the
  course headers change (a new lesson): the tier is `--base`.
- Order: the next free order of `electromagnetism` on `main` is 9
  (EM8 is 8): directory `site/lessons/electromagnetism/09-microwave-sparameter-lab`.
- Out of scope: the Lean theorem of F56; the paper's calibration
  uncertainty budget (the ARFTG paper is not read; the files carry no
  uncertainty and the page says so).
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md`, ADR 007, ADR 013, ADR 016, ADR 019, ADR 020; the lab
  rule of `docs/roadmap.md`; section 8.4 of
  `docs/changes/physics-next-phase.md`.

## Findings that shape the design (prototype on the committed files)

- The four files: three coaxial-system sweeps (3, 6, 10 dB pads,
  2.5–50 GHz, 191 points) and one single-sweep file of the 3 dB pad
  (2.5–220 GHz, 871 points), 250 MHz step, 50 Ω reference, calibrated
  (multiline TRL by the creators). The card's status is `calibrated`.
- Mean |S21|: −3.89, −6.83, −10.53 dB. |S11| from about −25 to −20 dB to
  50 GHz; up to −11 dB at 220 GHz in the single sweep.
- Energy: the fraction of the incident power absorbed in the pad,
  1 − |S11|² − |S21|², is 0.58, 0.78, 0.90 (coaxial) and stays positive to
  220 GHz; the largest singular value of S is at most 0.78.
- EM6 has no transmission-line model, but its guide wavenumber with zero
  cut-off is the TEM line: a matched line of length ℓ only delays a wave,
  e^{−jωτ}, τ = ℓ/v. EM5 gives the element impedances.
- Model (tested against three alternatives): a symmetric resistive T
  network with a series inductance in each arm, between two matched lines
  of total delay τ; four parameters (R_series, R_shunt, L, τ). Fitted to
  the complex S11 and S21 of each coaxial file to 50 GHz: residual rms
  0.002–0.003 in S, largest 0.011–0.018. Without the inductance the rms is
  0.02 (eight times larger); an inductance in the shunt arm instead gives
  0.007–0.009; both inductances do not improve on the series one.
- The fitted T is not a matched pad: the 3 dB pad fits R_series 14.1 Ω,
  R_shunt 145.5 Ω, against 11.0 Ω and 107.7 Ω for a matched T with its own
  measured loss; hence its |S11| of 0.075 at low frequency. The T is an
  equivalent circuit, not the layout (a pi network is equivalent).
- Standard errors of the fit assume independent residuals; the residuals of
  neighbouring frequencies correlate at about 0.9, so they understate. The
  same fit on the two instruments' files of the 3 dB pad (2.5–50 GHz)
  differs by 0.045 Ω in R_series, five standard errors.
- The 3 dB fit (to 50 GHz) carried to 220 GHz against the single sweep:
  the misfit grows from 0.002 at 50 GHz to about 0.02 at 100 GHz and
  0.12 at 220 GHz: the lumped model holds to 50 GHz and fails well before
  220 GHz.

## Design

One lesson, `microwave-sparameter-lab`, slot EM7, strand and course
`electromagnetism`, order 9, difficulty 2, `methods: [measured-data]`,
prerequisites `waveguides-and-antenna-basics` and `rlc-circuits-and-resonance`.
Preview `fig-smith-chart`.

Learning outcomes:

1. Read a calibrated Touchstone file as complex reflection and transmission
   amplitudes at a reference impedance, and tell an amplitude in dB from a
   power fraction.
2. Check passivity and the energy balance of a two-port on the data, and
   reciprocity and symmetry as consistency checks.
3. Build a lumped two-port model from EM5's element impedances and EM6's
   matched line, fit it, and read it on the Smith chart.
4. State what the record bounds (two instruments on one pad) and what it
   does not (the calibration), and where the lumped model fails.

Code:

- `src/pbc/electromagnetism/two_port.py` (new): `REFERENCE_IMPEDANCE`,
  `amplitude_db`, `power_fraction`, `absorbed_fraction`,
  `largest_singular_value`, `normalised_impedance`, `reflection`,
  `symmetric_s` (from the Z parameters of a symmetric reciprocal two-port),
  `matched_tee`, `TeeAttenuator` (R_series, R_shunt, L, τ; `s(frequency)`).
- `src/pbc/data/adapters.py`: `reflection_series` (|S11| in dB) beside
  `transmission_series`.
- `src/pbc/electromagnetism/experiments/microwave_sparameter_lab.py` (new):
  the record, consistency checks, power and amplitude table, energy
  balance, the matched-pad check, the fits with residual correlation,
  two instruments, band halves, the extrapolation, figures, exercises.

Page sections: opening question; assumptions; explanation (S-parameters,
amplitude and power, passivity and energy, the pad as a lumped two-port, the
Smith chart); code; worked examples (the matched pad, the record and its
card, consistency, amplitude and power, energy, the fit, its residuals and
what its standard errors assume, two instruments and two bands, the Smith
chart, beyond the fitted band, what the lab shows); limits; self-check;
exercises; run this experiment.

Claims: observational (record landmarks, consistency, energy, the
instrument cross-check), numerically verified (the matched pad closed form
against the network computation), experimentally supported (the fit, its
residual, the sensitivity, the extrapolated misfit).

## Visual deliverables

Scientific figures only, no diagram, no animation, no widget.
Skills: pbc-scientific-visualization@a70b501

- `fig-transmission` (calibrated): |S21| and |S11| in dB of the three
  coaxial files with the fitted models dashed, and the misfit
  |S_model − S_measured| of each fit below.
- `fig-smith-chart` (calibrated, preview): S11 of the three coaxial pads
  and of the single sweep near the centre of the Smith chart (circles of
  constant r and arcs of constant x drawn by the code), with the fitted
  models.
- `fig-wideband` (calibrated): the absorbed fraction of all four files to
  220 GHz; the misfit of the 3 dB fit against the single sweep to 220 GHz
  beside the two instruments' difference, the fitted band shaded.
- Dropped to keep the payload under 430 kB (pitfall 4): a separate energy
  figure, a separate beyond-the-band figure, and the whole-plane panel of
  the Smith chart (four figures came to 720 kB, then 440 kB; three figures
  417 kB locally). The fitted values and the residual checks are the
  tables `fit` and `fit-residuals`.

Scientific validation: every number drawn is asserted by the experiment
test or the dataset tests; `check_figure` on every figure; a byte-identity
test draws each figure twelve times. Accessible fallback: alt text without
computed values; the tables carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s. Fits under a second; four figures about
3 s. Figures together < 525,000 bytes in the test, at most 430,000 bytes
locally (pitfall 4).

## Verification

- `tests/unit/test_two_port.py`: the matched T gives S11 = 0 and the
  stated loss; a matched line only delays; the absorbed fraction of a
  lossless network is zero; normalised impedance and reflection invert;
  the model is reciprocal and symmetric; power and amplitude dB agree.
- `tests/unit/test_microwave_sparameter_lab_experiment.py`: page and
  results agree; numbers of every claim; figure conventions; byte-identical
  figures; no numeric console block; payload; the adapters' status; no
  section id equal to a cell label.
- The fit table (repair after the first `--base` run, which found its cells
  differing from the page's): a cell is `value ± stderr` with plain spaces,
  because the page's table is read with its white space collapsed and a
  no-break space became a plain one. The standard error has one
  significant figure and the value is rounded to the same place. Tests: the
  cells survive the collapse; other start points of every fit give the same
  tables and numbers (the fits move by at most 3e-7 relative); no float the
  page shows lies within 1e-6 relative of a rounding edge.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at 1280 x 800
  and 390 x 844. The full and `--base` verification is left to the script
  after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson EM7 testing EM5/EM6 models against the card | implementation |
| Touchstone to complex S, Smith chart, fitted lumped/line model | implementation |
| Calibration assumptions, passivity and energy, uncertainty as far as the record allows | implementation |
| Power and amplitude definitions distinguished | implementation |
| Discrepancies reported honestly | implementation |
| CI on the published head | pr_ci |
| Independent review | implementation (not_met until review-feature.sh) |
| The owner approves the lesson on the rendered page | owner_approval |
