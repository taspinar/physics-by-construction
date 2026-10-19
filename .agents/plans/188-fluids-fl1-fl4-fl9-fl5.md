# Plan: Issue #188, F73 — Fluid dynamics: advection, Burgers, finite volumes, shallow water

- Issue: #188 (source: `docs/roadmap.md`, F73)
- Branch: `feature/188-fluids-em-fl1-fl5`
- Base commit: `71fa0d2`
- Risk: Medium (physics content; first lesson feature of the `fluids` course)
- Governing documents: `docs/architecture.md` (lesson model, `fluids/` for
  the conservative finite-volume fluxes), `docs/authoring.md`, ADR 013,
  ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.
- Sequencing (owner, on the Issue, 2026-10-16): merged only after F117
  (#202). F117 is merged and is in the base of this branch, so the lessons are
  built to its experiment contract from the start (`lesson.experiment`, one
  `draw_` function per figure, "Run this experiment", a unit test per
  experiment).
- Owner's conditions (2026-10-15): one shared conservative flux interface,
  with a Riemann solver per system (Burgers: the exact Godunov flux; shallow
  water: HLL with Einfeldt's speeds); the dam-break reference solution, its
  initial conditions, and its error measure are fixed and recorded (below and
  on the page).

## Design

The first lesson feature of the `fluids` course: it creates the strand
directory `site/lessons/fluids/` and the package `src/pbc/fluids/`. Four
lessons, one slot each, in the teaching order FL1, FL4, FL9, FL5; 39
lessons after it, within the interim gate of 45.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `advection-and-diffusion` (order 1) | FL1 | `advection.py`: upwind, central, and Lax-Wendroff steps with an explicit diffusion term, inflow and outflow boundaries, `amplification`, `modified_diffusion`, `mode_amplitude` | the diffusion of a Fourier mode measured from the run against the modified equation a dx (1 - C) / 2 (gap of order two in dx); the same plus a physical diffusion; von Neumann factors measured by the code against the stability limits; a front fed through the inflow against the error-function front of the modified equation; an outflow condition that upwind never reads and Lax-Wendroff does |
| `shock-waves-and-burgers-equation` (order 2) | FL4 | `burgers.py`: flux, exact Godunov flux, characteristic solution before breaking, breaking time, shock speed, energy dissipation rate | the run against the characteristic solution before breaking (order one); the measured shock speed against Rankine-Hugoniot; the energy lost at a shock against (uL - uR)^3 / 12, and the vanishing energy loss of smooth flow under refinement |
| `finite-volume-methods-and-conservation-laws` (order 3) | FL9 | `finite_volume.py`: the shared interface (boundaries, interface fluxes, conservative update, CFL step, budgets), Rusanov flux; `burgers.nonconservative_step` | budgets of Burgers and flat-bottom shallow water closed to round-off; the CFL limit (total variation); the conservative scheme converging to the Rankine-Hugoniot shock and the non-conservative one to a wrong one |
| `shallow-water-equations` (order 4) | FL5 | `shallow_water.py`: flux, HLL Riemann solver, reflective walls, hydrostatic reconstruction over a bed, the naive source, the exact dam-break solution (Stoker, wet bed; Ritter, dry bed) | lake at rest over a bump kept to round-off (and the naive source's spurious current); the dam break against the exact solution with the error measure below; depth positivity on a dry bed; the speed of a long wave against sqrt(g h); mass and momentum budgets in a closed tank |

The dam-break comparison (owner's condition): one-dimensional ideal shallow
water, flat frictionless bed, g = 9.81 m/s^2; still water of depth 2 m left
of x = 0 and 0.5 m right of it, on [-10, 10] m with transmissive ends; the
reference is the exact Riemann solution (rarefaction and shock, Stoker); the
error measures are the L1 norm of the depth error over the domain at
t = 1 s and the position of the front (where the depth crosses the mean of
the middle and the downstream depth) against the exact shock position.

## Decisions

| Decision | Reason |
|---|---|
| The shared interface is `pbc.fluids.finite_volume`: a Riemann solver is any function `(left, right) -> flux`, the update is the flux difference, and `evolve` records the totals and the boundary inflow at each step | Owner's condition; FL10 reuses it with its own fluxes |
| Still water over a bump (lake at rest) with hydrostatic reconstruction (Audusse et al. 2004), compared with a pointwise source | Still water over a flat bed is kept by every consistent scheme, so it would check nothing |
| First-order schemes only (no limiters) | The lessons are about conservation, CFL, and numerical diffusion; the measured orders are those of first-order schemes |
| `FL9` is listed before `FL5` in `site/curriculum.yaml` | The course view orders by the file (ADR 013 decision 8); the approved teaching order is FL1, FL4, FL9, FL5 |
| No change to the architecture, ADRs, or CI | The lessons fit format 2; the architecture already names `fluids/` |
| `tests/unit/test_curriculum.py` updated | The published lessons that carry a slot, and the planned courses, change |

## Visual deliverables

Four scientific figures, one per lesson, each its lesson's preview:
`fig-advected-pulse` (FL1), `fig-burgers-steepening` (FL4),
`fig-conservative-and-not` (FL9), `fig-dam-break` (FL5). Each is
`simulated`, drawn by a `draw_` function from the tested code, with the
exact solution as the reference where one exists, series told apart by line
style and marker, alt text without computed values.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_fluids.py`: each component against a closed form or limit.
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/lessons`, the single-page render of the four lessons.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
