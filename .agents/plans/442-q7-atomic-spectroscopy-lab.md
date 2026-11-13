# Plan: Issue #442, F102 phase 2 — Atomic spectroscopy lab (Q7)

- Issue: #442 (source: `docs/roadmap.md`, F102); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`data/registry/sdss-balmer-spectrum.yaml`,
  `docs/datasets/sdss-balmer-spectrum.md`). Phase 2 started by the owner's
  word of 2026-11-13 on the Issue.
- Branch: `feature/442-q7-atomic-spectroscopy-lab`; base commit `cee205a`.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F102 is
  present and not retired; Q7 is the planned slot "Experimental: atomic
  spectroscopy" of `site/curriculum.yaml`.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/quantum/hydrogen.py`, a new experiment module, one adapter in
  `src/pbc/data/adapters.py` (alphabetical position by dataset module), one
  new entry in `site/references.yaml`, new tests. No existing assertion,
  tolerance, budget, protected path, or published claim changes. The lesson
  fills the planned slot Q7 with `lesson.slot`; `site/curriculum.yaml` and
  `site/atlas.yaml` (which already lists Q7) are not edited, but the learning
  path and the course headers change (a new lesson): the verification tier
  is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data", "References"),
  ADR 007, ADR 009, ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of
  `docs/roadmap.md`; section 8.4 of `docs/changes/physics-next-phase.md`.

## Findings that shape the design

- No earlier quantum lesson derives hydrogen. Q1 builds the grid
  Hamiltonian (`pbc.quantum.schrodinger.hamiltonian`, three-point second
  difference between two walls); Q3 diagonalises it for bound states
  (`pbc.quantum.eigenstates.eigenstates`). The radial equation of hydrogen,
  u = r R, -(1/2μ) u'' + (l(l+1)/2μr² - 1/r) u = E u with u(0) = 0, is
  exactly that problem on (0, r_max) in atomic units. The level model
  E_n = -μ/(2 m_e n²) Hartree is the lab's own, with its source
  (Fitzpatrick, *Quantum Mechanics*, UT Austin notes, "Hydrogen Atom" and
  "Rydberg Formula", a new register entry `fitzpatrick-hydrogen-atom`),
  and the lab checks it numerically with the Q1/Q3 solver.
- Grid check (explored): r_max = 250 a0, h = 0.025 gives the levels n = 1 to
  6 to relative 1e-4 (l = 0, n = 1) to 1e-5, second order in h (halving h
  divides the error by four); the l = 1 levels equal the l = 0 levels of
  the same n (the Coulomb degeneracy). Richardson extrapolation of h and h/2
  is reported as the converged value.
- Numbers from the committed sample (the reference module, reproduced):
  R = 10,968,065 ± 41 1/m, chi-square 0.74 for 3; calibration z0 =
  0.0149937 ± 0.0000030, slope 4.2 km/s per 1000 Å, chi-square 40.4 for 7;
  R − R_H = +2.80e-5 (fine structure 1.12e-5, the rest 1.67e-5 = 5.0 km/s);
  R − R_∞ = −5.16e-4, 137 standard errors: the reduced-mass correction is
  resolved; one z gives chi-square 29.6.
- Line widths: observed σ 70 to 86 km/s; the instrument's line-spread σ
  (`wdisp`) 56 to 73 km/s at the lines; the intrinsic σ 28 to 49 km/s, far
  above the thermal width of hydrogen at the assumed 10⁴ K (about 9 km/s)
  and about the same for H and heavier ions: the widths are motions of the
  gas in the galaxy, not of atoms in a lamp.
- Uncertainty assumptions (pitfall 6): the pixel errors are taken as
  independent. Checked on the residuals of the line fits: for the fits with
  reduced chi-square near one the correlation of neighbouring normalised
  residuals is within ±2/√N; for H δ and [O I] it is above (structured
  misfit, the stellar absorption): the scaled errors there may still be too
  small, and the page says so. The four Balmer values of R agree with
  chi-square 0.74 for 3 (a weak check); the sensitivity table bounds the
  choices; the velocity offset is not bounded.

## Design

One lesson, `atomic-spectroscopy`, slot Q7, strand and course `quantum`,
order 8 (the next free order), directory
`site/lessons/quantum/08-atomic-spectroscopy`, difficulty 2,
`methods: [measured-data, simulation]`, prerequisite
`quantum-harmonic-oscillator` (the bound states on a grid; it requires the
Schrödinger-equation lesson). Preview `fig-rydberg-law`.

Learning outcomes:

1. Read a calibrated astronomical spectrum for what it is: the pipeline's
   flux- and wavelength-calibrated, co-added pixels with inverse variances,
   a galaxy's gas rather than a lamp.
2. State the level model of hydrogen with the reduced mass, and check it
   with the grid solver of the quantum course on the radial equation.
3. Fit emission lines, calibrate the redshift on the forbidden lines, and
   infer the Rydberg constant of hydrogen with an uncertainty whose
   assumptions are checked.
4. Judge the result against the laboratory value: what the data resolve
   (the reduced mass), what they cannot separate (a velocity offset), what
   the Bohr formula leaves out (fine structure).

Code:

- `src/pbc/quantum/hydrogen.py` (new): `level` (E_n in Hartree with the
  mass ratio μ/m_e), `reduced_mass_ratio`, `rydberg_hydrogen`,
  `balmer_wavenumber`, `radial_levels` (Q1's Hamiltonian via Q3's
  `eigenstates` on the radial equation), `richardson`.
- `src/pbc/data/adapters.py`: `spectrum_flux_series`, the flux density of
  the SDSS spectrum as a `calibrated-observation` `Series` with σ from
  `ivar`.
- `src/pbc/quantum/experiments/atomic_spectroscopy.py` (new): the record
  and its landmarks, the radial check, the line table, the widths, the
  calibration, the Rydberg constant and its comparisons, the uncertainty
  checks, the sensitivity table, the figures, the exercises. Tests assert
  that its R equals the reference module's.

Page sections: opening question; assumptions; explanation (levels with the
reduced mass; the Balmer series; redshift and its degeneracy with R; line
widths); code; worked examples (the levels on the grid; the measurement and
its card; fitting the lines; what the widths say; calibrating the
redshift; the Rydberg constant; are the errors honest; what the
spectrum cannot tell apart; what the lab shows); limits; self-check;
exercises (the proton mass from R; deuterium's line shift); run this
experiment.

Claims (typed): observational for the record's landmarks (pixels, range,
signal-to-noise, masks); numerically-verified for the radial levels;
experimentally-supported for the line centres and widths, the calibration
and its extra scatter, R with its error and chi-square, the comparisons
with R_H and R_∞, the residual checks; not-verified for background physics
(gas temperature, kinematics of a starburst).

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-spectrum`: the whole spectrum, every pixel as released, the masked
  pixels marked, the thirteen fitted lines named; status `calibrated`,
  `fig-dataset: sdss-balmer-spectrum`, credit on the figure.
- `fig-balmer-fits`: the four Balmer lines' pixels with one-σ bars and the
  fitted Gaussian on a straight continuum (dashed), normalised residual
  panels below. Status `processed`; `check_figure(..., residuals=True)`.
- `fig-calibration`: the forbidden lines' velocities about z0 against the
  observed wavelength with the fitted z(λ) and the one-z line. Status
  `processed`.
- `fig-rydberg-law` (preview): the rest wavenumber of each Balmer line
  against 1/4 − 1/n² with the Rydberg line of the fitted R (drawn from its two
  ends), and residual panel: each line's offset in km/s from the formula
  with R_H, with one z and with z(λ). Status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_atomic_spectroscopy_experiment.py` or the dataset tests;
`check_figure` on each; a byte-identity test draws each figure twelve
times. Accessible fallback: alt text without computed values; the line,
calibration, and Rydberg tables carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: the analysis 0.1 s, the sensitivity analysis 0.5 s, the radial
  check about 1 s, four figures about 3 s.
- Payload: four PNGs together at most 0.70 × 750 kB = 525 kB locally (the
  test bound, pitfall 4), the HTML about 0.2 MB.

## Verification

- `tests/unit/test_hydrogen.py`: the model (levels, reduced mass, Balmer
  wavenumbers against the laboratory lines to 1e-4, radial levels converge
  at second order to −1/2n², l-degeneracy, Richardson).
- `tests/unit/test_atomic_spectroscopy_experiment.py`: the page and the
  results agree; R equals the reference module's; the numbers of every
  claim; figure conventions; byte-identical figures; no numeric console
  block; figure payload; the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson Q7 testing a level model of hydrogen against the card's measurements | implementation |
| Line centres with scaled errors, the redshift calibration with its extra scatter, the Balmer lines against the Rydberg formula with the reduced mass | implementation |
| Level model stated as the lab's own with its source, checked with the Q1 solver; prerequisites | implementation |
| Rights decision and SDSS acknowledgement shown; measured, fitted, model apart; every claim typed | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
