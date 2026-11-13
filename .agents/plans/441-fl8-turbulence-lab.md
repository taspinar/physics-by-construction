# Plan: Issue #441, F108 phase 2 — Turbulent boundary layer measurements lab (FL8)

- Issue: #441 (source: `docs/roadmap.md`, F108); phase 1 (two cards, two
  dossiers, samples, reference figures, `go`) is on `main`
  (`.agents/plans/441-fl8-turbulence-dossier.md`). Phase 2 started by the
  owner's word of 2026-11-13 on the Issue.
- Branch: `feature/441-fl8-turbulence-lab`
- Base commit: `cee205a`
- Written by the implementer: no phase 2 plan existed.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F108 is
  present and not retired; `site/curriculum.yaml` lists the planned slot
  FL8 (kind "measured-data lab").
- Risk: Level 2. One new lesson, a new model module
  `src/pbc/fluids/boundary_layer.py`, a new experiment module, two adapters
  in `src/pbc/data/adapters.py` (in alphabetical position by dataset
  module), new tests. No existing assertion, tolerance, budget, protected
  path, or published claim changes. The lesson fills the planned slot FL8
  with `lesson.slot`; `site/curriculum.yaml` is not edited, but the learning
  path and the course headers change (a new lesson): the verification tier
  is `--base`.
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Lesson format 2", "Measured data"), ADR 007,
  ADR 013, ADR 016, ADR 019, ADR 020; the lab rule of `docs/roadmap.md`;
  section 8.4 of `docs/changes/physics-next-phase.md`; the dossiers
  `docs/datasets/tudelft-turbulent-boundary-layer.md` and
  `docs/datasets/grazing-flow-hwa-benchmark.md` and their cards.

## Findings that shape the design

- FL2 (`navier-stokes-fundamentals`) solves the incompressible
  Navier-Stokes equations in two dimensions in a periodic box: no walls,
  laminar. FL3 (`vortex-formation-and-flow-around-obstacles`) adds a body by
  direct forcing, does not resolve its boundary layer, and states that
  vortex stretching, the engine of turbulence, vanishes in two dimensions.
  The laminar limit of their equations next to a wall is Prandtl's boundary
  layer, whose flat-plate solution is Blasius's. The lab tests that model
  against two measured turbulent layers and shows what replaces it.
- Numbers from the committed samples (reference modules, reproduced):
  TU Delft Re_tau 1351 to 4647, Re_theta 3079 to 12020; kappa 0.400 to
  0.410, B 4.77 to 5.17 on the nominal window, 0.355 to 0.428 over 15
  windows; H 1.331 to 1.368 against Blasius 2.591; u_tau within 1.1 % of
  Coles-Fernholz. VKI solid wall (u_tau from Coles-Fernholz, y fitted by the
  providers) kappa 0.387 to 0.421 on 6 to 10 points; H 1.326 to 1.357.
- New numbers of the lab (explored 2026-11-13): with x = 6.8 m (the record
  description), Re_x = 2.1e6 to 8.3e6; the measured skin friction
  C_f = 2 (u_tau/U_inf)^2 is 7 to 11 times the laminar 0.664/sqrt(Re_x);
  the measured delta is 5 to 9 times the laminar delta_99 and theta 3 to 6
  times the laminar theta at the same x. The outer turbulence intensity
  u'+ = sqrt(u'u')/u_tau agrees between PIV (TU Delft) and hot wire (VKI
  solid wall) to about 0.1 at y/delta 0.1 to 0.5 (1.9 to 2.1, 1.6 to 1.8,
  1.2 to 1.5). Near the wall the PIV u'+ rises to 4.5 to 5.5 at y+ 9 to 20,
  about twice the hot wire's inner peak (about 2.7): PIV noise or
  resolution, not physics; the page says so and claims nothing from it.
- Uncertainty assumptions (pitfall 6): the least-squares error of kappa
  assumes independent residuals; the residuals of the log fit are
  correlated by about 0.9 between adjacent PIV points, so that error is far
  too small. The window spread (dossier) is the uncertainty quoted; u_tau
  to about 1 % from Coles-Fernholz (TU Delft); the VKI kappa is partly
  imposed (the providers fitted the wall position) and its u_tau is the
  correlation itself, so it is no independent test.

## Design

One lesson, `turbulent-boundary-layer-measurements`, slot FL8, strand and
course `fluids`, order 8 (the next free order), directory
`site/lessons/fluids/08-turbulent-boundary-layer-measurements`, difficulty
3, `methods: [measured-data]`, prerequisites `navier-stokes-fundamentals`
and `vortex-formation-and-flow-around-obstacles`. Preview `fig-wall-units`.

Learning outcomes:

1. Read two boundary-layer records for what they are: mean profiles and
   second moments averaged by their creators from PIV, PTV, and hot-wire
   measurements, with no uncertainty or a statistical one only, and with
   caveats (a readme wrong on layout and units; a wall position fitted).
2. Derive the laminar flat-plate layer from the boundary-layer form of the
   Navier-Stokes equations, solve the Blasius equation, and predict its
   thickness, shape factor, and skin friction.
3. Compare the measured layers with the laminar prediction (H, delta,
   theta, C_f) and put them in wall units: the viscous sublayer and the log
   law, with kappa and B, the fit window as the dominant uncertainty, and
   the assumption of independent residuals checked.
4. Compare two independent facilities on the same law and on the
   turbulence intensity, say where an agreement is partly imposed, and
   state where the laminar two-dimensional models of FL2 and FL3 stop
   applying.

Code:

- `src/pbc/fluids/boundary_layer.py` (new): `blasius` (shooting with a
  classical RK4 of its own and bisection, numpy only), `laminar_layer`
  (delta_99, delta*, theta, C_f at a station), `integral_thicknesses`
  (trapezoid), `sublayer`, `log_law`, `coles_fernholz_friction`.
- `src/pbc/data/adapters.py`: `hot_wire_profile_series` (VKI U/Ue against
  y/delta, `processed-measured`, standard uncertainty from the 95 %
  half-width) after `impedance_series` (bayreuth) and before
  `stress_strain_series` (nist); `boundary_layer_profile_series` (TU Delft
  U against y, `processed-measured`, no uncertainty) after
  `light_curve_series` (tess) and before `pendulum_angle_series` (xu); their
  TYPE_CHECKING imports in alphabetical order.
- `src/pbc/fluids/experiments/turbulent_boundary_layer_measurements.py`
  (new): the records and their landmarks, the Blasius check against the
  reference module's `solve_ivp` solution, the laminar comparison, the log
  fits with `fit_curve`, the window sensitivity, the residual correlation,
  the turbulence intensity comparison, the figures, the exercises. Tests
  assert that its numbers equal the reference modules'.

Page sections: opening question; assumptions; explanation (the boundary
layer of the Navier-Stokes equations; the Blasius layer; integral
thicknesses and H; a turbulent layer: Reynolds stress, wall units, the
sublayer and the log law; skin friction and Coles-Fernholz); code; worked
examples (the Blasius solution checked; the measurements, two cards; the
laminar prediction against the measured layers; the layers in wall units;
the log-law constants and their window; are the errors honest; two
facilities, one law; turbulence intensity; what the lab shows); limits;
self-check; exercises (viscous length and the first PIV point; the
laminar plate at the trip); run this experiment.

Claims (typed): observational for the record landmarks (cases, speeds,
counts); numerically-verified for the Blasius solver against the reference
solver and the classical constants; experimentally-supported for H, the
laminar ratios, kappa and B with the window range, u_tau against
Coles-Fernholz, the residual correlation, the comparison of the facilities,
the turbulence intensity; not-verified for background physics (transition
Reynolds numbers, the mechanism of turbulent mixing). Every claim is scoped
to the records and the stated window; the VKI log-law agreement is stated
as partly imposed.

## Visual deliverables

Scientific figures only, no diagram. Skills: pbc-scientific-visualization@a70b501

- `fig-outer-profiles`: U/U_inf against y/delta for the four TU Delft cases
  (PTV below the first PIV point, then PIV) and the VKI solid wall at
  x = 0, with the Blasius profile (model, against y/delta_99); H against
  Re_theta for both records with Blasius's H. Status `processed`,
  `fig-dataset: tudelft-turbulent-boundary-layer`, credit for both records.
- `fig-wall-units` (preview): U+ against y+ (log), PIV lines, PTV and hot
  wire markers, the sublayer and the reference log law (model, not fitted)
  dashed, the nominal window shaded; below, the residual from the law.
  Status `processed`; `check_figure(..., residuals=True)`.
- `fig-turbulence-intensity`: u'+ against y/delta, PIV lines and hot-wire
  markers; -u'v'+ of the PIV with the wall value 1. Status `processed`.

Scientific validation: every number drawn is asserted by
`tests/unit/test_turbulent_boundary_layer_measurements_experiment.py` or the
dataset tests; `check_figure` on each; a byte-identity test draws each
figure twelve times; straight model lines drawn from their two ends.
Accessible fallback: alt text without computed values; the record, laminar,
log-law, and intensity tables carry the numbers.

## Runtime and payload estimate

Budgets: warning 30 s, limit 60 s per lesson page; 3 MB payload.

- Render: reading 32 small files and the fits well under 1 s; the two
  Blasius solutions about 1 s; three figures about 3 s.
- Payload: three PNGs kept below 525 kB together locally (0.70 x 750 kB,
  pitfall 4; asserted in the test), the HTML about 0.2 MB. Because the
  Linux build in CI came out up to 16.6 % larger than the local one (W7),
  the figures are drawn at most 430 kB locally (smaller figure sizes, a
  shorter credit), so CI stays under the test's bound.

## Verification

- `tests/unit/test_boundary_layer.py`: the model functions (Blasius
  constants and the ODE residual, the laminar layer's scaling, integral
  thicknesses of a known profile, the law of the wall, Coles-Fernholz).
- `tests/unit/test_turbulent_boundary_layer_measurements_experiment.py`:
  the page and the results agree; the numbers equal the reference
  modules'; the numbers of every claim; figure conventions; byte-identical
  figures; no numeric console block; figure payload; the adapters' status.
- `uv run python -m pbc.data.check`, `./scripts/verify.sh --only code`,
  `--only default`, the page checks of the new lesson; render at
  1280 x 800 and 390 x 844. The full and `--base` verification is left to
  the script after the session (owner's instruction on the Issue).

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule (gates of section 8.4) | implementation |
| A new published lesson FL8 testing the FL2/FL3 laminar models against the cards' measurements | implementation |
| Log law (kappa, B, window as dominant uncertainty), H against Blasius, Re_tau, turbulence intensity | implementation |
| The two records compared; imposed agreement and the dossiers' caveats stated | implementation |
| Measurements distinct from processed signals and models; every claim typed with evidence | implementation |
| CI on the published head | pr_ci |
| The independent physics review of the claim types | implementation (review after the session) |
| The owner approves the lesson on the rendered page | owner_approval |
