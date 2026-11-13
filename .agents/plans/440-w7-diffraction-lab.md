# Plan: Issue #440, F52 phase 2 — the optical diffraction lab (W7)

- Issue: #440 (source: `docs/roadmap.md`, F52); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`.agents/plans/440-w7-lycopodium-dossier.md`). Phase 2 started by the
  owner's word of 2026-11-13 on the Issue. Also in this change: #453.
- Branch: `feature/440-w7-diffraction-lab`; base commit `b2e5079`.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F52 is
  present, kept, and not retired; its course `waves` exists (F71).
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/waves/halo.py`, a new experiment module, one adapter added at the
  end of `src/pbc/data/adapters.py`, new tests, one new test in
  `tests/unit/test_data_lycopodium.py` (#453). No existing assertion,
  tolerance, budget, protected path, or published claim changes. The lesson
  fills the planned slot W7 with `lesson.slot`; `site/curriculum.yaml` is not
  edited, but the learning path and the course headers change (a new
  lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossier
  `docs/datasets/lycopodium-spore-diffraction.md` and the card
  `data/registry/lycopodium-spore-diffraction.yaml`.

## Findings that shape the design

- The model under test is that of the lesson "Diffraction and imaging"
  (`diffraction-and-imaging`, slot W5, directory `06-…`): the far field of a
  round aperture as the radial integral of its wavelets,
  `pbc.waves.diffraction.circular_field`, whose square is the Airy pattern,
  first zero at sin θ = 1.2197 λ/D. Babinet's principle carries it to an
  opaque disk; spores at random places add intensities, so the halo is the
  Airy intensity averaged over the measured diameters with weight d⁴. It
  depends on q = sin θ/λ alone: the dark ring's sin θ scales with λ.
- The numbers of the committed sample (reference module, reproduced):
  dark ring 16.68 ± 0.34 (632.8 nm) and 11.02 ± 0.33 (405 nm) in the
  record's unknown unit of x; ratio 0.661 ± 0.024 against 0.640; whole
  spores 29.91 ± 0.34 µm (x160, n = 72) and 30.36 ± 0.13 µm (x80,
  n = 605); bright-to-dark radius 1.19 and 1.11 against 1.31 (first
  minimum) and 1.17 (second); implied screen distance 640/661 or 353/365
  units of x.
- Uncertainty assumptions (pitfall 6), checked on the data: the ± of a
  radius is half the range over five smoothing widths, a sensitivity of the
  analysis, not a statistical error. The quadrature propagation of the ratio
  treats the two ranges as independent, but both radii depend on the same
  smoothing choice; the ratio computed at each common width (0.642 to 0.685)
  is the direct check and is shown. At 405 nm the radius rises with the
  width monotonically (a bias of the smoothing, not scatter). The two sides
  agree at 632.8 nm; at 405 nm the right side has no dip. The microscope's
  standard errors assume independent particles; the two magnifications,
  calibrated separately, agree within 1.2 combined standard errors.

## Design

One lesson, `lycopodium-diffraction-lab`, slot W7, strand and course
`waves`, order 9 (the next free order), directory
`site/lessons/waves/09-lycopodium-diffraction-lab`, difficulty 2,
`methods: [measured-data, simulation]`, prerequisite
`diffraction-and-imaging`. Preview `fig-scaling`.

Learning outcomes:

1. Explain by Babinet's principle and incoherent addition why a layer of
   spores gives the Airy pattern of one disk averaged over their diameters,
   and why its rings depend on sin θ/λ alone.
2. Build the halo of a measured size distribution from the wavelet integral
   of the round aperture and check it against the closed form.
3. Find the dark ring of a measured line profile (centre, fold, smoothing)
   and state its uncertainty as the sensitivity to the analysis, with the
   assumptions checked.
4. Test the wavelength scaling of the rings without the missing calibration,
   and say what the record does not allow: no absolute diameter, no
   intensities, the ring order unsettled.

Code:

- `src/pbc/waves/halo.py` (new): `disk_amplitude(u)` (W5's
  `circular_field` with D = λ = 1, u = d sin θ/λ), `halo(q, diameters)` (the
  d⁴-weighted mean of the squared amplitude, from a tabulated amplitude),
  `extrema(diameters, count)` (q of the minima and maxima),
  `radius_ratio(q, wavelengths)` (the ratio of ring radii on a flat screen,
  tan of the angle), `screen_distance(radius, q, wavelength)`.
- `src/pbc/data/adapters.py`: `luma_profile_series`, a line profile as a
  `processed-measured` `Series` (added at the end).
- `src/pbc/waves/experiments/lycopodium_diffraction_lab.py` (new): the
  diameters, the halo model and its check against the closed form, the
  profiles, the dark rings and their sensitivity table, the sides, the
  ratio at each width, the ring order, the implied screen distances, the
  figures, the exercises. Tests assert that its numbers equal the reference
  module's (the dossier's).

Page sections: opening question; assumptions; explanation (Babinet and
incoherent addition; the halo of many sizes; what scales with the
wavelength; what the record lacks); code; worked examples (the halo from
W5's integral against the closed form; the measurement and its card; the
microscope diameters; the two profiles; the dark ring and its sensitivity;
the scale-free test; is the uncertainty honest; which minimum; what the
diffraction cannot give); limits; self-check; exercises (the screen
distance of a tabletop if the unit were the millimetre; a green laser);
run this experiment.

Claims (typed): numerically-verified for the halo from the wavelet integral
against the closed form and the minima of one disk; observational for the
microscope diameters and the saturated core; experimentally-supported for
the dark-ring radii, the ratio against 0.640 (scoped: same spatial scale
and geometry assumed, sensitivity range not statistical), the ring-order
comparison (not decisive), each scoped to the two profiles of the record.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-profiles`: the two measured line profiles about their centres, the
  saturation level, the dark ring dotted on both sides. Status
  `processed`, `fig-dataset: lycopodium-spore-diffraction`,
  `fig-artifact: processed-measured`, credit on the figure.
- `fig-diameters`: histograms of the microscope diameters of whole spores at
  x160 and x80 (step lines, hatch and colour). Status `processed`.
- `fig-halo-model`: the halo of one disk (W5) and of the 72 measured
  diameters against q d̄, log intensity, minima marked. Status
  `simulated`, `fig-model-of: lycopodium-spore-diffraction`.
- `fig-scaling` (preview): the folded, smoothed profiles against radius over
  wavelength with their dark rings; the ratio r(405)/r(632.8) at each
  smoothing width against the predicted 0.640 (a prediction, not a fit:
  set by the two wavelengths alone); residual panel (ratio − prediction).
  Status `processed`. No line fitted to the rings is drawn (#453).

Scientific validation: every number drawn is asserted by the lab's tests or
the dataset tests; `check_figure` on each; a byte-identity test draws each
figure twelve times. Accessible fallback: alt text without computed values;
the tables carry every plotted number (diameters, radii per width, ratios,
ring order, screen distances).

## #453

The reference figure's line already reads "proportional fit to the two
measured radii" on `main` (fixed in the last round of phase 1, after the
finding was filed). This change regenerates the figure, adds a test that
the dashed series of the reference figure is labelled a fit and never a
model, and the lesson draws no fitted line as a model.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.
Analysis about 1 s (profiles, 5 widths × 2), the halo table about 0.5 s,
four figures about 3 s. Figures together under 0.36 MB locally, asserted
below a bound of 0.42 MB (15 % margin, pitfall 4).

## Verification

- `tests/unit/test_halo.py`: closed form, minima of one disk, scaling,
  weighting, flat-screen ratio, screen distance.
- `tests/unit/test_lycopodium_diffraction_lab_experiment.py`: the page and
  the results agree; the dossier's numbers; uncertainty checks; figure
  conventions; byte-identical figures; no numeric console block; payload;
  the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at 1280 x 800
  and 390 x 844. The full and `--base` verification is left to the script
  after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson W7 testing the W5 model against the card's measurements | implementation |
| Ring radii, their ratio against 0.640, the microscope diameter; the record's limits stated | implementation |
| Every claim typed with evidence; measurement apart from model | implementation |
| #453 resolved | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
