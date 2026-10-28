# Plan: Issue #315, F91 — Astrophysics: the three-body problem, modified gravity, lensing

- Issue: #315 (source: `docs/roadmap.md`, F91)
- Branch: `feature/315-astrophysics-the-three-body`
- Base commit: `8b6ebd5`
- Risk: Medium (physics content; first lesson feature of a course), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

The first lesson feature of the `astrophysics` course: it creates the strand
directory `site/lessons/astrophysics/` and the package `src/pbc/astrophysics/`.
Three lessons, one slot each, built to the experiment contract (one module
per lesson under `src/pbc/astrophysics/experiments/`, one `draw_` function
per figure, a unit test per experiment). AST1 reuses the N-body code of F69
(`pbc.mechanics.nbody`: the acceleration, the energy, the angular momentum,
the barycentric start) and the course's integrators.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `three-body-problem` (order 1) | AST1 | `three_body.py`: Lagrange's equilateral solution of any three masses and its exact rigid rotation, Routh's parameter and the predicted growth rate of a perturbation, the departure of the triangle from its shape, an adaptive integration (DOP853) of the F69 acceleration, the Pythagorean start, the escaper of a final state | the known periodic solution reproduced: Lagrange's triangle against its exact rotation at order four (the course's Runge-Kutta method), its energy and angular momentum tracked; the growth rate of a perturbation against the linear-stability prediction (Routh) on both sides of the threshold 27 beta = 1; the Pythagorean problem with its energy tracked through close encounters, two tolerances that agree on the escape of the lightest body, and the divergence of nearby starts |
| `modified-gravity` (order 2) | AST2 | `central_force.py`: power-law and Yukawa central forces, an orbit integrated with periapsis passages located as events, the energy and angular momentum along it, the first-order (Gauss) precession of any radial perturbation by quadrature, its closed form for a power law, the near-circular apsidal angle | the inverse square closing (Bertrand); the precession per orbit against the perturbative prediction, the gap shrinking in proportion to the perturbation (second order); the Yukawa precession against its quadrature, largest where the range is near the orbit's size |
| `gravitational-lensing` (order 3) | AST3 | `lensing.py`: the exact Schwarzschild deflection by Gauss-Legendre quadrature, the weak-field and Newtonian deflections, the point lens (lens map, images, magnification), inverse ray shooting of a finite source, the disk average of the point-source magnification, the Einstein radius and time, the microlensing light curve | the deflection angle against the weak-field formula 4GM/(c^2 b), the remainder against the second-order coefficient 15 pi / 4; the ray-shot magnification against the disk-averaged closed form; three lenses of different mass with the same Einstein time and the same light curve (the limit of mass inference) |

Units: G = 1 for AST1 and AST2 (stated); G = c = 1 with m = GM/c^2 for the
deflection; SI (`scipy.constants`) with the solar mass parameter
GM_sun = 1.32712440018e20 m^3/s^2 (a given value) for the lensing scales.
No REBOUND, astropy, or lensing package: the references are closed forms,
perturbation theory, and independent computations.

## Decisions

| Decision | Reason |
|---|---|
| The known periodic solution is Lagrange's triangle, not the figure-eight | M13 (F69) already reproduces the figure-eight; Lagrange's solution has an exact closed form for all times and any masses, and its stability has an analytic criterion to check against |
| Adaptive DOP853 (`scipy.integrate.solve_ivp`) for the long and close-encounter runs | The Pythagorean problem passes within 1e-3 of a collision; a fixed step would need to be tiny throughout. The course's Runge-Kutta method keeps the convergence check of the periodic solution |
| The perturbation measured as the departure of the triangle from equilateral | The neutral modes (rotation, a homographic change of size) keep the triangle equilateral, so the measure isolates the modes Routh's criterion is about |
| Periapsis located as an event of the radial velocity crossing zero upwards | The event is found to the tolerance of the integrator, which the precession at small perturbations needs |
| The first-order precession by quadrature along the unperturbed ellipse (Gauss's equation with a radial force) | Any radial perturbation, checked in the unit tests against its closed form for a power law |
| The exact deflection by Gauss-Legendre quadrature after the substitution that removes the turning-point singularity, checked in the unit tests against the photon orbit equation integrated by DOP853 | A smooth integrand, no warning from adaptive quadrature, and an independent second method |
| Magnification checked by inverse ray shooting against the disk average of the point-source formula | Both compute the magnification of the same finite source independently; the disk average is exact for a uniform source |
| No change to the architecture, ADRs, the curriculum file, the atlas, or CI | Slots AST1 to AST3, the course, and the atlas concepts exist |
| `tests/unit/test_curriculum.py` matches the singular sentence of the learning path ("1 further course has") | With this feature only one course (`materials`) has no lesson; `pbc.authoring.path` already writes the singular, and the test looked only for the plural. Found by the unit suite; the test keeps its strength (the exact sentence, once) |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; reference curves labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- AST1: the Pythagorean trajectories (preview), the growth rate against
  Routh's prediction, the divergence of nearby runs with the energy error.
- AST2: the rosette of a modified law beside the closed Kepler ellipse
  (preview), the precession against the perturbation with the first-order
  line, the Yukawa precession against its range.
- AST3: the images of a finite source by ray shooting (preview), the
  deflection against the impact parameter with the weak-field and Newtonian
  lines, the light curves of three lenses with one Einstein time.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_astrophysics.py`: each function against a closed form, a limit, or an independent computation.
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes
  what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the three lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
