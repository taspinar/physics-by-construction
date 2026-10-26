# Plan: Issue #282, F76 — Heat conduction and the finite-element bridge (T6, T10)

- Issue: #282 (source: `docs/roadmap.md`, F76)
- Branch: `feature/282-heat-conduction-and-the`
- Base commit: `ec5b90e`
- Risk: Level 2 (Medium) by its paths: two new lessons, a new package
  `src/pbc/fem/`, a new module of `src/pbc/thermodynamics/`, and tests; the
  scripts derive any trigger the diff hits (a tolerance of new code)
- Governing documents: `docs/architecture.md` ("Applied capstone and
  numerical-engineering lesson", the package layout naming `fem/`),
  `docs/authoring.md` (format 2, the experiment of a lesson), ADR 007 (an
  optional tool's output is a `modelled-reference` card), ADR 013 (slots),
  ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F70 delivered; F113 read as the owner's interim
  full-run gate, since 2026-10-24 up to 110 lessons (#281). The site has 51
  lesson pages; 53 after this feature.

## Design

Two lessons in the `thermodynamics` strand at the next free orders, one slot
each (the placement rule). Both run on NumPy and SciPy only.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `heat-conduction-and-diffusion` (order 7) | T6 | `pbc.thermodynamics.conduction`: a material (k, rho, c, alpha), lumped (Newton) cooling, the explicit (FTCS) step of the 1D heat equation with fixed-temperature and convective (Robin, ghost-node) boundaries, the 2D FTCS step on a plate, the exact series of a slab cooled by convection (eigenvalues of lambda tan lambda = Bi), the measured amplification per step, the 5-point steady plate solved as a sparse system | the lumped model against the slab's mean temperature for three Biot numbers; the stability limit measured by bisection of the measured amplification, 1D and 2D, against the discrete limit 1 / (2 d cos^2(pi / (2 (N + 1)))) and its continuum value 1/(2d); grid convergence of the convective slab against its series solution at fixed r (order two in dx); time-step convergence against the semi-discrete exact solution on a fixed grid (order one in dt); the long-time 2D transient against the steady sparse solve; energy balance of the convective slab |
| `from-finite-differences-to-finite-elements` (order 8) | T10 | `pbc.fem`: triangular meshes (a structured rectangle, an annulus of rings triangulated by `scipy.spatial.Delaunay`), mesh quality (angles, radius ratio), P1 assembly of stiffness, mass and load, convective (Robin) edges, Dirichlet elimination, `scipy.sparse` solve, L2 and H1 errors by Gauss quadrature, consistent boundary fluxes from the residual | the manufactured solution with Dirichlet and convective sides: L2 error order two and H1 error order one under refinement; on a structured mesh the P1 stiffness equals the 5-point stencil of T6 and the FEM and FD solutions of the same plate agree to the discretisation error; an insulated pipe (annulus, hot inner wall, convective outer wall) against the exact heat loss per length, converging under refinement; the flux balance (heat in at the inner wall, out at the outer) closed to a relative 1e-10 with the consistent flux, and the gradient flux shown to close only at first order; mesh quality bounded under refinement |

Units: SI throughout (W, m, K, s); the manufactured problem is dimensionless,
said so on the page.

## Decisions

| Decision | Reason |
|---|---|
| `pbc.fem` is a package (`src/pbc/fem/`) with `mesh.py` and `assembly.py`, scalar P1 only | The architecture names `fem/`; T11 and MAT3 extend it; vector elements are MAT3's work, not this feature's |
| Meshes generated in the lesson by code (structured split squares; annulus rings and `scipy.spatial.Delaunay`) | A mesh generated and inspected on the page; no Gmsh. SciPy is locked |
| No optional-tool artifact (Gmsh, FEniCSx) | Not needed: the manufactured and exact pipe solutions are the references. Hence no `modelled-reference` card; the criterion holds vacuously, stated in the Limits |
| Boundary flux from the residual of the unconstrained system (the reactions) | The flux that closes the discrete balance; the gradient flux is shown for contrast |
| The stability limit measured, not assumed: bisection on the measured growth per step of a random state | The criterion asks for it measured; the discrete limit is the reference |
| Time order measured against the exact semi-discrete solution of a sine mode | Separates the time error from the space error on one grid |
| `tests/unit/test_fem.py` parses every `src/pbc/fem` source and allows only the standard library, `pbc`, and the `[project].dependencies` of `pyproject.toml` that `uv.lock` pins | The criterion "no import outside the locked environment" |
| `annulus(..., graded=True)`: rings evenly spaced in the logarithm of the radius (discovered in implementation) | The coated-wire exercise (outer radius eighty times the wire's) was under-resolved on evenly spaced rings (about 2 % error at eight layers); graded rings keep the triangles near-equilateral and the error near 0.1 % at 48 layers |
| `conduction.march` for the time loop, not `run` | An experiment's `run()` is its entry point; the model's loop must not shadow it |
| No change to the architecture, ADRs, CI, or the curriculum file | The lessons fit format 2 and their slots exist; the layout already names `fem/`. The line of `thermodynamics/` in the package layout of `docs/architecture.md` (a protected path) still names only F70's models; adding `conduction` there is left to a change the owner approves, as F75 left its own |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
alt text without computed values:

- T6: `fig-lumped-against-slab` (mean temperature against time, three Biot
  numbers, slab against lumped), `fig-stability-limit` (measured growth per
  step against r, 1D and 2D, limits marked), `fig-heat-convergence` (log-log
  error against dx and against dt with labelled reference slopes),
  `fig-plate-temperature` (preview; false-colour plate field with colour
  bar, transient and steady).
- T10: `fig-annulus-mesh` (the generated mesh and its quality histogram),
  `fig-fem-convergence` (log-log L2 and H1 errors against h with reference
  slopes), `fig-pipe-temperature` (preview; false-colour temperature on the
  mesh with colour bar, and the radial profile against the exact one).

Scientific validation: each figure shows quantities that a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_conduction.py`, `tests/unit/test_fem.py`: each component
  against a closed form or a limit; the import boundary of `pbc.fem`.
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/lessons`, the lesson source checks.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
