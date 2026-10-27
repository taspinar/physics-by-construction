# Plan: Issue #302, F87 — Applied capstone: thermal engineering of a hypothetical AI accelerator (T11)

- Issue: #302 (source: `docs/roadmap.md`, F87)
- Branch: `feature/302-applied-capstone-thermal-engineering`
- Base commit: `90d181e`
- Risk: Level 2 (Medium) by its paths: one new lesson, an extension of
  `src/pbc/fem/` (a coefficient per triangle, the mass matrix, time
  stepping), a new module of `src/pbc/thermodynamics/`, its experiment, and
  tests; the home and atlas tests that assumed every capstone planned are
  generalised to a published one. The scripts derive any trigger the diff
  hits; `risk_assess` is run before the completion record is written
- Governing documents: `docs/architecture.md` ("Applied capstone and
  numerical-engineering lesson"), `docs/roadmap.md` (the capstone rule, the
  definition of done of a lesson), `docs/authoring.md` (format 2, the
  experiment of a lesson, claim labels), ADR 007 (an optional tool's output
  is a `modelled-reference` card), ADR 013 (slots), ADR 016 (the
  experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F76 delivered; F113 read as the owner's interim
  full-run gate, up to 110 lessons since 2026-10-24 (#281). The site has 63
  lesson pages; 64 after this feature. F84 (the measured cross-link) is
  optional and not delivered: no cross-link.

## Design

One lesson, `thermal-engineering-of-an-ai-accelerator`, in the
`thermodynamics` strand at order 9, slot T11 (kind `applied capstone`),
difficulty 3, prerequisites T6 (`heat-conduction-and-diffusion`) and T10
(`from-finite-differences-to-finite-elements`), the precursors the
architecture names. NumPy and SciPy only; the experiment runs within the
30-second page budget with margin (no entry in `scripts/lesson-budgets.conf`).

**The model.** A hypothetical package: two compute dies and four memory
stacks (round, invented powers and sizes, no vendor data) on a rectangular
heat spreader (lid), cooled from below by a cold plate. A compact
two-dimensional plate model of the spreader, per unit area:

    rho c t dT/dt = div(k t grad T) + q''(x, y) - (T - T_coolant) / R_base,
    R_base = t / (2 k) + R_contact,lid-to-plate + 1 / h_plate,
    T_junction = T + q''_die (R_contact,die-to-lid + t / (2 k))   (over a die),

with T the temperature of the plate's middle plane, edges insulated, the
top outside the dies insulated, the coolant at a uniform temperature.
Assumptions stated on the page; the one about the thickness (heat crosses
each half of the plate straight down) is checked against a cross-section
that resolves the thickness.

**Code.**

| Module | Content |
|---|---|
| `pbc.fem.assembly` (extended) | `stiffness` with a coefficient per triangle as well as a constant; `mass`, the consistent mass matrix with a coefficient per triangle (heat capacity, and the areal exchange with the coolant); `edge_load`, a flux through boundary edges (which `convection` now uses for its vector) |
| `pbc.fem.transient` (new) | the theta method (backward Euler, Crank-Nicolson) for C du/dt = F - A u, one sparse LU factorisation per run, and the energy bookkeeping of each step |
| `pbc.thermodynamics.package` (new) | `Die`, `Package` (spreader size, thickness, material from `conduction.Material`, inserts of a second material, dies, contact resistances, cold plate, coolant), mass; the heat flux of the dies; the finite-element system on a `pbc.fem.mesh.rectangle`, steady and transient; junction temperatures; heat in, out, and stored; the finite-difference baseline of T6 (node-centred five-point grid with mirrored ghost nodes at the insulated edges, control-volume source, uniform plate only), steady and explicit (FTCS, `conduction.march`); the exact cosine-mode solution (steady and transient) of the plate model; `cross_section`, the x-z cut through the spreader that resolves the thickness |
| `pbc.thermodynamics.experiments.thermal_engineering_of_an_ai_accelerator` | everything the page shows |

**The checks of the page (each a table the build regenerates).**

1. Requirements and inputs: the hypothetical loads, geometry, materials,
   contact and cold-plate assumptions, and the constraints (junction limit,
   mass, size, heat removal h at most `H_MAX`).
2. Analytic reference: the cosine-mode load on the insulated plate has an
   exact solution; FEM and FD converge to it at order two in the
   root-mean-square error over the plate (the largest error of the elements
   sits at two corners of the one-diagonal mesh and converges more slowly,
   shown).
2a. Model-form reference: with the compute dies and inserts extended across
   the spreader, the plate model against a cross-section that resolves the
   thickness, on two meshes; the gap is the model's resolution.
3. Energy and flux balances: steady heat in equals heat to the coolant
   (relative gap stated, below 1e-10) for FEM and FD on every mesh; in the
   transient, stored plus removed equals generated, every step, below the
   same tolerance.
4. Mesh study: the junction maximum of the package by FEM and FD on four
   spacings; both converge, their difference falls under refinement. The
   design with inserts by FEM alone: it converges at a reduced order, which
   the same inserts as full-height strips (no corner inside the plate)
   restore to two.
5. Time-step study: backward Euler order one, Crank-Nicolson order two,
   against the exact semi-discrete solution (generalised eigenproblem) on a
   coarse mesh; the FD explicit step limited by its measured stability
   limit (T6's `growth_per_step`), FTCS above it diverges (a failure mode),
   and the FEM implicit transient against the FD explicit transient.
6. Scenarios and optimisation: cooling (three cold-plate coefficients),
   material (aluminium, copper, aluminium with copper inserts) at the
   thickness the mass and size limits allow, and layout (die separation);
   the junction maximum minimised over the separation by a search over the
   admissible layouts, the bounds of thickness and h shown to bind by
   sweeps; the optimum confirmed on a finer mesh.
7. Sensitivity: each uncertain input changed by plus and minus 20 per cent,
   the change of the junction maximum, by FEM and by the FD baseline
   (uniform design).
8. Trade-off table and recommendation: every scenario with its junction
   maximum, margin, mass, h, and whether it meets every constraint; the
   recommendation chosen by a stated rule from the table (the coolest
   feasible design; designs within the model's gap to the cross-section are
   tied, and the lightest of them wins), its margin compared with the
   sensitivity swings.
9. Failure modes: the explicit step above its limit; a uniform-flux
   (lumped) estimate that misses the hotspots; the plate model's own limits
   (no three-dimensional spreading in the die, no CFD of the coolant).
10. The credibility label: a claim div typed `numerically-verified` near
    the top, scope the hypothetical model, saying it is a digital-twin-style
    teaching prototype, not a calibrated twin or a model of a proprietary
    device, no vendor data, no three-dimensional CFD; a test asserts it.

Units: SI, temperatures in degrees C (differences in K).

## Decisions

| Decision | Reason |
|---|---|
| A two-dimensional spreader (plate) model with areal exchange to the coolant, contact resistances in series | The goal's "package or cold-plate proxy" with contact and convective assumptions, solvable on a small mesh within the budget; three-dimensional CFD is a non-goal |
| Structured rectangle meshes of `pbc.fem.mesh.rectangle`, die edges on mesh lines at every refinement | The geometry is rectangles; the FD baseline uses the same nodes, so the two methods compare node by node; the source integrates exactly |
| FD baseline for uniform plates only; the inserts are FEM's | A coefficient per triangle is what the elements add; stated on the page |
| The sink as the mass matrix with coefficient 1 / R_base | One matrix for capacity and exchange; the balance closes because the stiffness rows sum to zero |
| Optimisation by an exhaustive search over admissible separations (2 mm steps) and sweeps for the bounds | Transparent and robust on a mesh-dependent objective; the optimum checked on a finer mesh |
| Recommendation by a rule computed from the trade-off table | The prose names the rule; the chosen design is a result of the build, pinned by a test |
| The mid-plane plate model with the half-thickness resistances, checked against a cross-section (discovered in implementation) | Without them the neglected drop across 3 mm of aluminium was a fifth of R_base; the cross-section shows the mid-plane model within a few tenths of a kelvin, on the warm side |
| Designs within the plate model's gap to the cross-section are tied (discovered in implementation) | The two coolest designs differ by less than that gap; the discretisation error is far smaller, so the model, not the mesh, limits the decision |
| Root-mean-square error for the cosine mode (discovered in implementation) | The largest nodal error of the elements is at two corners and converges at about 1.8; the rms error at two |
| No optional tool, no `modelled-reference` card | The analytic cosine mode, the semi-discrete exact solution, and the FD baseline are the references; the Limits say so |
| No "Go deeper" reference | Optional; none needed (as T10) |
| The home and atlas tests generalised: a published capstone links to its lesson, the others stay planned | Publishing T11 changes what those pages show; the tests asserted every capstone planned |
| The capstone template of F127 not applied | F127 (the rollout) is not delivered; no capstone template exists in the CSS |
| The package-layout line of `thermodynamics/` in `docs/architecture.md` not edited | A protected path; as F76 left it |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
dimensionless axes labelled so, the alt text naming the axis scales and no
computed values:

- `fig-package-temperature` (preview): the steady temperature of the
  spreader for the baseline and the recommended design, false colour with a
  colour bar, die outlines.
- `fig-package-transient`: the junction maximum against time after a power
  step, FEM implicit and FD explicit; the energy balance residual per step.
- `fig-package-refinement`: log-log, the error of the cosine mode against
  h (FEM, FD, slope two), and the time-step errors (BE slope one, CN slope
  two).
- `fig-package-layout`: the junction maximum against the die separation for
  the materials, the admissible range and the optimum marked.
- `fig-package-sensitivity`: the change of the junction maximum for each
  input at minus and plus 20 per cent, FEM bars and FD markers.

Scientific validation: each figure shows quantities a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_fem.py` (extended): the per-triangle stiffness against a
  two-layer exact solution, the mass matrix integrates products exactly,
  the theta method's orders and its energy bookkeeping.
- `tests/unit/test_package.py`: the package model (mass, flux, balance, the
  cosine mode, FD against FEM, the FD stencil).
- `tests/unit/test_thermal_engineering_of_an_ai_accelerator_experiment.py`:
  the page and the results agree; each check of the page; the credibility
  claim present and typed.
- `tests/lessons`, the lesson source checks; the home and atlas tests.
- `./scripts/verify.sh --base` (a new lesson changes what other pages show).
