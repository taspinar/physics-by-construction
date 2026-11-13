# Plan: Issue #443, F106 phase 2 — X-ray diffraction lab (MAT5)

- Issue: #443 (source: `docs/roadmap.md`, F106); phase 1 (card, dossier,
  samples, reference figure, `go`) is on `main`
  (`.agents/plans/443-mat5-lab6-bragg-dossier.md`). Phase 2 started by the
  owner's word of 2026-11-13 on the Issue.
- Branch: `feature/443-mat5-xray-diffraction-lab`; base commit `cee205a`.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F106 is
  present and not retired.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/materials/diffraction.py`, a new experiment module, one adapter
  added to `src/pbc/data/adapters.py`, new tests, and the legend of the
  phase 1 reference figure (#467, also in this pull request). No existing
  assertion, tolerance, budget, protected path, or published claim
  changes. The lesson fills the planned slot MAT5 with `lesson.slot`;
  `site/curriculum.yaml` and `site/atlas.yaml` (which already pairs MAT5
  with MAT1) are not edited, but the learning path and the course headers
  change (a new lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/nist-srm660c-lab6.md` and the card
  `data/registry/nist-srm660c-lab6.yaml`.

## Where the Bragg model lives (the open point of phase 1)

MAT1 models a crystal as a lattice that repeats with a spacing `a` (a
one-dimensional chain) and never measures `a`. The lab introduces the
three-dimensional cubic lattice, its planes (h k l), Bragg's law, and the
displacement error itself, in a new model module
`src/pbc/materials/diffraction.py`, and tests MAT1's one-parameter lattice
against the measured peaks. No other lesson changes.

## Findings that shape the design (prototype on the committed samples)

- The analysis of the dossier (`pbc.data.reference.srm660c.analyse`) on 20
  measured patterns and 20 of NIST's model patterns takes about 5 s.
- Mean a over 20 specimens (Nelson–Riley above 60°): 4.156485 Å, SD
  0.000014 Å; NIST's model by the same method 4.156480 Å; NIST's refined
  a 4.156789 Å (20.85 °C); certified 4.156826 ± 0.000080 Å (k = 2,
  22.5 °C). The gap to the certified value, −82 ppm, closes exactly as
  method bias on NIST's model (−74.4 ppm) + NIST's refined against
  certified (−8.9 ppm) + measured minus model (+1.1 ppm).
- The residuals of the Nelson–Riley line are correlated in angle (lag-1
  autocorrelation about 0.47) and NIST's noise-free model scatters about
  its own line almost as much: that scatter is the profile's systematic,
  not counting noise, so the ordinary standard error of one intercept is
  not a statistical error. The counting part is the spread of measured
  minus model (SD about 1 ppm per specimen).
- A synthetic pattern built from the method's own symmetric doublet on
  specimen 100a's grid, with Poisson-scaled noise (seeded), is recovered
  to about 1 ppm; with a displacement of −0.1 mm the Nelson–Riley
  extrapolation is biased by about −9 ppm while the displacement function
  cos²θ/sinθ recovers a and the slope a s/R. On the data the slope against
  that function follows the CIF's displacement (correlation 0.9996) with a
  coefficient about 1.24 times a/R.
- Extrapolation choices (lowest angle 40 to 100°, the Nelson–Riley or the
  displacement function, weighted or not) move the measured mean between
  −93 and −76 ppm from the certified value, while measured minus model
  stays within 10 ppm.

## Discoveries during the work

- `fit_curve` warned that the line's slope was not determined separately
  when a was fitted in angstrom (intercept 4.16, slope 1e-3); the line is
  fitted in ppm of the certified a and converted back (`extrapolate`),
  and the warning is gone; the intercept equals the dossier's to 1e-10 Å.
- Measured minus model also has correlated residuals (about +0.48): NIST's
  model does not follow the measurement exactly either; the page says so
  and uses the spread over the specimens, not a fit error.
- Payload: 20 grey specimen lines in `fig-extrapolation` cost 58 kB and
  were dropped (`fig-specimens` shows the spread); the figure credit was
  shortened. At about 510 kB locally the figures would have exceeded the
  test's bound (525 kB) in CI, whose Linux build has come out up to 16.6 %
  larger (W7). Text is about 70 % of each PNG's bytes: smaller tick and
  axis labels (`_compact`), shorter legend entries and credit, figures
  6.0 inches wide, a narrower window around the drawn peaks, and the dense
  measured trace of `fig-pattern` drawn without antialiasing bring them to
  424 kB locally (at most 430 kB, so about 495 kB in CI).
- `standard_from_expanded` defaults to k = 1.96; the certificate's U is
  k = 2, passed explicitly.

## Design

One lesson, `xray-diffraction-lab`, slot MAT5, strand and course
`materials`, order 6 (the next free order), directory
`site/lessons/materials/06-xray-diffraction-lab`, difficulty 2,
`methods: [measured-data]`, prerequisite `crystal-lattices-and-phonons`.

Learning outcomes:

1. Derive Bragg's law for the planes (h k l) of a cubic lattice and index
   a measured powder pattern with one lattice parameter.
2. Fit a Kα1/Kα2 doublet to a measured reflection, judge it by its
   residuals, and turn its position into a spacing and a lattice parameter.
3. Explain how a displaced specimen shifts the peaks, and extrapolate the
   lattice parameters of single reflections to θ = 90°.
4. Separate the statistical error, the spread between specimens, the
   systematic of the method and of the extrapolation, and the certificate's
   uncertainty, and say which dominates the comparison with the certified
   value.

Code:

- `src/pbc/materials/diffraction.py` (new): `index_sum`, `plane_spacing`,
  `bragg_two_theta`, `bragg_spacing`, `lattice_parameter`,
  `displacement_shift`, `displacement_function`, `nelson_riley`.
- `src/pbc/data/adapters.py`: `diffraction_pattern_series`, the measured
  pattern as a `processed-measured` `Series` with its Poisson σ; import and
  function in alphabetical position by dataset module (after
  `nist_numisheet`, before `tess_wasp18`).
- `src/pbc/materials/experiments/xray_diffraction_lab.py` (new): the
  experiment of the page; the peak fits are the dossier's
  (`pbc.data.reference.srm660c`), the lattice parameters and the
  extrapolation go through `pbc.materials.diffraction` and
  `pbc.data.fit.fit_curve`, and tests assert that both give the same
  numbers.

Page sections: opening question; assumptions; explanation (planes and
Bragg's law; the doublet; the displacement and the extrapolation); code;
worked examples (the method on a synthetic pattern; the measurement and
its indexing; one reflection fitted; one lattice parameter per
reflection and the extrapolation; twenty specimens and the check of the
errors; the method's bias on NIST's model; the extrapolation's
sensitivity; the budget and the comparison with the certified value; what
the lab shows); limits; self-check; exercises; run this experiment.

Claims (typed): numerically-verified for the method on synthetic
patterns; observational for the indexing (24 peaks, fitted positions
against the certificate's Table 1); experimentally-supported for the
reduced χ² of the fits, a per reflection and its drift, the extrapolated
a with its spread, the check of the errors, the slope against the
displacement, the method's bias, measured minus model, the sensitivity
(stated as a sensitivity, never as an interval), and the comparison with
the certified value (a discrepancy of 4.3 U, reported as such); the
bias-corrected value scoped to NIST's model of the instrument; nothing
about the thermal expansion beyond what the record gives.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-pattern` (the preview): the 24 windows of specimen 100a on a log
  scale, measured, with the Kα1 positions Bragg's law predicts from the
  certified a as ticks (model, apart); status `processed`.
- `fig-peaks`: a low-angle (110) and a high-angle (510) reflection, the
  measured points with 1σ counting bars, the doublet fit dashed, NIST's
  model dotted, the residuals in σ below; `check_figure(...,
  residuals=True)`.
- `fig-extrapolation`: a per reflection of 100a against the Nelson–Riley
  function, measured and NIST's model by the same method, their lines,
  the lines of all 20 specimens, NIST's refined and the certified a.
- `fig-specimens`: a per specimen (measured, model, NIST's refined, the
  certified band ± U), and the slope against the CIF's displacement with
  the line of slope a/R.

All `fig-status: processed`, `fig-dataset: nist-srm660c-lab6`,
`fig-artifact: processed-measured`, the card's credit on each. Scientific
validation: every number drawn is asserted by
`tests/unit/test_xray_diffraction_lab_experiment.py` or the sample tests.
Accessible fallback: alt text without computed values; the reflections,
sensitivity and budget tables carry the numbers.

## #467 in this pull request

The per-specimen panel of the reference figure gives its legend values in
Å while its axis is in pm: the legend uses pm. The reference figure is not
committed (it is generated by `python -m pbc.data.reference`); it is
regenerated and inspected, and `tests/unit/test_data_plotting.py` still
passes.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: about 22 s for the page alone (40 analyses about 5 s, two
  synthetic analyses, four figures; the rest is Quarto's fixed cost).
- Payload: four PNGs under 525 kB together (70 % of the 750 kB the other
  labs keep, asserted in the test), the HTML about 0.25 MB.

## Verification

- `tests/unit/test_diffraction.py`: the model functions (Bragg's law both
  ways, the spacing of cubic planes, the displacement shift against the
  first-order error of a, the Nelson–Riley function at 90°).
- `tests/unit/test_xray_diffraction_lab_experiment.py`: the page and the
  results agree; the numbers of every claim; the lab's a equals the
  reference module's; figure conventions; byte-identical figures over
  twelve draws; no numeric console block; the figures' payload at most
  70 % of the bound; the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson MAT5 testing the MAT1 lattice model against the card's measurements | implementation |
| Peaks, Bragg spacings, a per peak, Nelson–Riley intercept, comparison with the certified a and U; statistical, extrapolation and certificate uncertainties apart, the dominant one named | implementation |
| #467: the legend in the axis unit, the reference figure regenerated | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
