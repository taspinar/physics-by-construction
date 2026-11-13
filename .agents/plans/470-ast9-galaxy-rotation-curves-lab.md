# Plan: Issue #470, F105 phase 2 — Galaxy rotation curves lab (AST9)

- Issue: #470 (source: `docs/roadmap.md`, F105); phase 1 (card, dossier,
  sample, reference figure, `go`) is on `main`
  (`data/registry/sparc-rotation-curves.yaml`,
  `docs/datasets/sparc-rotation-curves.md`, plan
  `.agents/plans/470-ast9-sparc-rotmod-dossier.md`). Phase 2 started by the
  owner's word of 2026-11-13 on the Issue.
- Branch: `feature/470-ast9-galaxy-rotation-curves-lab`; base commit
  `655ab03`.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F105 is
  present and not retired; AST9 is the planned slot "Experimental: galaxy
  rotation curves" of `site/curriculum.yaml`.
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/astrophysics/rotation_curves.py`, a new experiment module, one
  adapter in `src/pbc/data/adapters.py` (alphabetical position by dataset
  module: after `sdss_flux_series`, before `light_curve_series` of
  `tess_wasp18`), one new entry in `site/references.yaml`, new tests. No
  existing assertion, tolerance, budget, protected path, or published claim
  changes; the reference module `sparc_rotmod` is read, not changed. The
  lesson fills the planned slot AST9 with `lesson.slot`;
  `site/curriculum.yaml` is not edited, but the learning path and the
  course headers change (a new lesson): the verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data", "References"),
  ADR 007, ADR 009, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`.

## Findings that shape the design

- No earlier astrophysics lesson derives a galaxy's circular speed. The
  Kepler-orbit lesson (M8) gives the circular speed sqrt(GM/a) of a point
  mass; the lab states the extension to a spherical mass, v² = G M(<r)/r
  (the shell theorem), and the halo profiles as its own model, with the
  source de Blok et al. 2008 ("High-resolution rotation curves and galaxy
  mass models from THINGS", AJ 136, 2648; arXiv 0810.2100, sections 5 and
  5.3: the sum V² = Vgas² + Υ V*² + Vhalo² (Eq. 3), NFW (Eqs. 6, 7) and
  pseudo-isothermal (Eqs. 8, 9)), a new register entry
  `deblok-things-mass-models`, read on 2026-11-13.
- **Where the model lives.** The fits stay in the reference module
  `pbc.data.reference.sparc_rotmod` (ADR 007 wants the figure code there,
  and no reference module imports a physics module); the lab's model module
  `pbc.astrophysics.rotation_curves` states the densities, the enclosed
  mass, and the circular speed, and checks numerically (1) that the pull of
  every thin shell summed over angle and radius gives v² = G M(<r)/r, the
  shells outside r adding nothing, and (2) that the reference module's
  closed-form halo speeds equal G M(<r)/r with M integrated from the
  densities. The dossier left this decision to phase 2.
- Numbers from the committed sample (the reference module, reproduced): the
  dossier's table (baryons only chi²/dof 175 to 1026; halo fits 1.2 to 10.7
  with errV; 0.13 to 3.3 with a 5 % floor). Baryons only fall short of the
  outermost point by 31 to 44 % of Vobs.
- **Uncertainty assumptions (pitfall 6).** The residuals of every fit are
  strongly correlated from point to point (neighbour correlation 0.6 to
  1.0, against a band 2/sqrt(N) of 0.23 to 0.58): errV are not independent
  errors of a smooth model (rings overlapping the beam, non-circular
  motions). So chi² is not a probability and the fit's standard errors are
  lower bounds; the lab says so and rests its conclusions on sizes of
  misfit and on robustness to the unknown systematics instead:
  - inclination: a common scale of Vobs and errV (×0.9, ×1.1, given);
  - distance: radii × k, baryon speeds × sqrt(k) (k = 0.8, 1.25, given);
  - per-point floor of 5 and 10 % of Vobs (given, illustrative).
  Under all of them baryons-only stays above chi²/dof 160 with errV; the
  floors bring it down to 5 to 21 at 10 %, still far above the halo fits.
- **Cusp and core.** DDO 154: the cusp overshoots the two innermost points
  by 2.5 and 4.6 errV; its chi²/dof is about four times the core's under
  every variant, but with a 10 % floor both fall below one. NGC 2903 with
  the three points inside 1 kpc (the bar) left out prefers the cusp
  (0.68 against 1.61). The shapes are not one answer across galaxies; the
  lab reports both and draws no general conclusion about dark matter.
- **Degeneracy.** NGC 2403: Y 0.29 (cusp) against 0.76 (core); the core's
  profile has two minima (Y ≈ 0.08 and 0.76); the maximum disk is 0.86.
  Y moves with the inclination and distance scale (0.62 to 0.94 for the
  core).

## Design

One lesson, `galaxy-rotation-curves`, slot AST9, strand and course
`astrophysics`, order 10, directory
`site/lessons/astrophysics/10-galaxy-rotation-curves`, difficulty 2,
`methods: [measured-data, simulation]`, prerequisite `kepler-orbit`.
Preview `fig-mass-models`.

Learning outcomes:

1. State the Newtonian model of a disk galaxy's circular speed, v² =
   G M(<r)/r for spherical mass and the sum of the squared speeds of its
   components, and check it by summing the pull of thin shells.
2. Read a SPARC rotation curve for what it is: a processed measurement,
   deprojected and folded, with errors that exclude the inclination and
   the distance, beside the team's modelled speeds of the gas and the stars.
3. Fit mass models with and without a dark halo of two shapes, with the
   stellar mass-to-light ratio, and show their residuals.
4. Judge what the fits support: which result survives the unknown
   inclination, distance, and error floor, the degeneracy of the
   mass-to-light ratio, and why a chi-square of correlated residuals is
   not a probability.

Code:

- `src/pbc/astrophysics/rotation_curves.py` (new): `G_KPC`,
  `nfw_density`, `iso_density`, `enclosed_mass` (quadrature of 4πr²ρ),
  `circular_speed_squared`, `shell_sum_speed_squared` (the pull of thin
  shells summed numerically over angle and radius, out to a truncation
  radius).
- `src/pbc/data/adapters.py`: `rotation_curve_series`, Vobs ± errV as a
  `processed-measured` `Series`.
- `src/pbc/astrophysics/experiments/galaxy_rotation_curves.py` (new): the
  model check, the record table, the fit table, the residual correlations,
  the robustness table, the bar, the degeneracy, the figures, the
  exercises.

Page sections: opening question; assumptions; explanation (circular speed
of a spherical mass; components add in squares; the stars' mass-to-light
ratio; the two halos; the maximum disk); code; worked examples (the model
on shells; the measurement and its card; the baryons alone; a halo; are
the errors honest; what survives the systematics; cusp or core; the bar of
NGC 2903; how heavy are the stars; what the lab shows); limits;
self-check; exercises (a larger distance for NGC 2841; the mass inside the
last point of NGC 3198 against the baryons'); run this experiment.

Claims (typed): observational for the record (points, radii, errV);
numerically-verified for the shell sum and the closed forms;
experimentally-supported for the fits, the residual correlations, the
robustness, cusp/core, the bar, and Y; not-verified for background
(the physics of bars, other explanations of flat curves).

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-curves`: the five rotation curves, Vobs with errV bars, with the
  SPARC speeds of gas and stars at Y = 1 dotted and labelled as the team's
  model. Status `processed`, `fig-dataset: sparc-rotation-curves`,
  `fig-artifact: processed-measured`.
- `fig-mass-models` (preview): NGC 3198 and DDO 154, Vobs with errV, the
  components, the three fitted totals, residual panels below. Status
  `processed`; `check_figure(..., residuals=True)`.
- `fig-degeneracy`: NGC 2403, a halo-dominated and a near-maximum disk
  decomposition with their residuals, and the chi² profile in Y for both
  halos with the maximum disk. Status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_galaxy_rotation_curves_experiment.py` or the dataset
tests; `check_figure` on each; a byte-identity test draws each figure
twelve times. Accessible fallback: alt text without computed values; the
fit, robustness and correlation tables carry the numbers.

## Runtime and payload estimate

- Render: the fits about 1 s, the robustness variants about 4 s, the Y
  profiles about 2 s, the shell sums under 1 s, three figures about 3 s.
- Payload: the PNGs at most 430 kB locally (test bound `< 525_000`,
  pitfall 4), the HTML about 0.2 MB.

## Verification

- `tests/unit/test_rotation_curves.py`: the model.
- `tests/unit/test_galaxy_rotation_curves_experiment.py`: the page and the
  results agree; the numbers of every claim; one id per element; figure
  conventions; byte-identical figures; no numeric console block; payload;
  the adapter's status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson AST9 testing a Newtonian mass model against the card's measurements | implementation |
| Fits with and without a halo (NFW, pseudo-isothermal), error bars, components, residuals, degeneracy of Y | implementation |
| errV without inclination and distance: its effect on chi² stated | implementation |
| The model stated as the lab's own with its sources; prerequisites | implementation |
| SPARC permission and citation shown; every claim typed | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
