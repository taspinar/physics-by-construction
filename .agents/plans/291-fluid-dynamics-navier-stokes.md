# Plan: Issue #291, F79 — Fluid dynamics: Navier-Stokes, vortex shedding, particle-based fluids (FL2, FL3, FL6)

- Issue: #291 (source: `docs/roadmap.md`, F79)
- Branch: `feature/291-fluid-dynamics-navier-stokes`
- Base commit: `30d179e`
- Risk: Level 2 (Medium) by its paths: three new lessons, three new modules
  of `src/pbc/fluids/`, their experiments, a reference-register entry, and
  tests; the scripts derive any trigger the diff hits
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`
  (format 2, the experiment of a lesson, references), ADR 007 (an optional
  tool's output is a `modelled-reference` card), ADR 013 (slots), ADR 016
  (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F73 delivered; F113 read as the owner's interim
  full-run gate, up to 110 lessons since 2026-10-24 (#281). The site has 53
  lesson pages; 56 after this feature.

## Design

Three lessons in the `fluids` strand at the next free orders (the placement
rule), one slot each. NumPy and SciPy only; every experiment runs within the
30-second page budget with margin (no entry in `scripts/lesson-budgets.conf`).

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `navier-stokes-fundamentals` (order 5) | FL2 | `pbc.fluids.navier_stokes`: a periodic staggered (MAC) grid, central second-order divergence, gradient, Laplacian, advection in divergence form, the FFT Poisson solve, the projection, the three-stage SSP Runge-Kutta step with a projection per stage, the pressure from its Poisson equation, energy, vorticity, viscous dissipation, the Taylor-Green vortex, and a manufactured solution with its force | the projection leaves a divergence at round-off and never adds energy; the Taylor-Green vortex against its exact decay; the manufactured solution (advection not a gradient) converges at order two in velocity and pressure; without viscosity the energy changes only by the time step (order three), with viscosity the energy lost equals the integrated discrete dissipation |
| `vortex-formation-and-flow-around-obstacles` (order 6) | FL3 | `pbc.fluids.vortices`: the double shear layer, circulation, a cylinder as a direct-forcing immersed body on the same grid, a fringe region that restores the free stream before the periodic boundary, a wake probe, the shedding frequency from zero crossings, Roshko's published Strouhal relation | the shear layers roll up into vortices with the circulation zero to round-off and the energy budget closed, and the vorticity converges under refinement; the Strouhal number at Re = 100 compared with Roshko's relation and the published stable range, the regime stated; at Re = 40 the wake oscillation decays (no shedding); the narrower box sheds faster (blockage) |
| `particle-based-fluid-simulation` (order 7) | FL6 | `pbc.fluids.sph`: the cubic spline kernel, pairs by k-d tree, summation density, plain and difference gradient estimates, the weakly compressible pressure and its internal energy, continuity density, the symmetric pressure force with an optional Monaghan viscosity that heats, the midpoint step, momentum, angular momentum, energy, the elliptical drop's exact solution | the kernel integrates to one; the particle gradient converges on a lattice and stalls on disordered particles, where the difference form fixes the constant; the elliptical drop against its exact semi-axes; conservation: momentum to round-off, angular momentum and energy changed only by the time step with the order measured; the density error against the speed of sound |

Units: SI throughout; the NS lessons are written in units of the cylinder
diameter and the free stream (dimensionless, said so on the page).

## Decisions

| Decision | Reason |
|---|---|
| FL2 checked against a manufactured solution (and the exact Taylor-Green vortex), not a lid-driven cavity | The criterion allows either; the manufactured solution needs no `modelled-reference` card and exercises every term; hence no card and no optional tool |
| Periodic MAC grid with FFT projection for FL2 and FL3 | One solver for both lessons, exact projection, second order, fast enough for the page budget |
| The cylinder as direct forcing with a one-cell smoothed mask, the inflow restored by a fringe region | Uses the periodic solver unchanged; the bias (blockage, upstream distance, resolution of ten cells per diameter) is stated and the blockage measured |
| Roshko (1954, NACA Report 1191) as the published reference | Freely readable on NTRS; its relation S = 0.212 (1 - 21.2/R), 50 < R < 150, and its regime boundaries were read in the report (page 11); register entry `roshko-vortex-street-strouhal` |
| SPH with continuity density and the midpoint step (discovered in implementation) | Kick-drift-kick with velocity-dependent density rates gave first-order energy error and an instability at the elliptical drop; the midpoint step gives a clean second-order energy error. Angular momentum is then conserved by the equations, not by the step; the page says so and measures it |
| The drop run to A0 t = 0.5 (discovered in implementation) | With a fixed kernel width the stretched direction loses neighbours; beyond about 0.7 the error grows. Stated in the Limits |
| No change to the architecture, ADRs, CI, the curriculum file, or the atlas | The slots and concepts exist; the lessons fit format 2 |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
false-colour fields with a colour bar centred on zero, alt text without
computed values:

- FL2: `fig-projection` (preview; a velocity field before and after the
  projection with its divergence in false colour), `fig-ns-convergence`
  (log-log error against cell width, velocity and pressure, reference slope
  two), `fig-energy-budget` (energy and the integrated dissipation against
  time).
- FL3: `fig-shear-layer` (vorticity at three times), `fig-karman-street`
  (preview; the vorticity of the wake at Re = 100), `fig-wake-signal` (the
  probe velocity against time at Re = 40 and Re = 100).
- FL6: `fig-particle-gradient` (log-log gradient error against spacing,
  lattice and disordered, plain and difference), `fig-elliptical-drop`
  (preview; particles at three times with the exact ellipses).

Scientific validation: each figure shows quantities that a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_navier_stokes.py`, `tests/unit/test_vortices.py`,
  `tests/unit/test_sph.py`: each component against a closed form, an
  identity, or a limit (the manufactured force against finite differences of
  the solution).
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/lessons`, the lesson source checks.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
