# Plan: Issue #325, F92 — Relativity and cosmology: special relativity, relativistic orbits, cosmic expansion

- Issue: #325 (source: `docs/roadmap.md`, F92)
- Branch: `feature/325-relativity-and-cosmology-special`
- Base commit: `480130b`
- Risk: Medium (physics content), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

Three lessons in the existing `astrophysics` strand, in the teaching order
of the curriculum file (AST10, AST4, AST5 after AST3), built to the
experiment contract like F91: one module of code under
`src/pbc/astrophysics/`, one experiment per lesson, a unit test per
experiment, unit tests of the code in `tests/unit/test_astrophysics.py`.
AST4 reuses `pbc.astrophysics.central_force` (Gauss's first-order
precession of a radial perturbation) as one of its two references.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `special-relativity` (order 4) | AST10 | `special_relativity.py`: the Lorentz factor and rapidity, the boost matrix along a direction, the Minkowski interval, velocity addition, the proper time along a worldline, the length of a moving rod read off simultaneous events, four-momenta, the invariant mass, the Galilean transformation | the invariants preserved: the interval of events and the invariant mass of a collision, unchanged by boosts to round-off, the boost matrix keeping the metric, and two collinear boosts one boost of the added rapidity; the four-momentum of a collision conserved in every frame while the Newtonian momentum of the same collision is not; time dilation and length contraction computed from transformed events, not from their formulas, and checked against them; the Newtonian limit recovered: the kinetic energy, the Lorentz transformation, and velocity addition approach their Galilean forms with a gap of order beta squared |
| `relativistic-orbits` (order 5) | AST4 | `relativistic_orbits.py`: the Schwarzschild orbit equation u'' + u = m/h^2 + 3 m u^2 of a test body integrated in the angle (DOP853) with the periapses located as events, the exact turn per orbit from the complete elliptic integral of the three roots of the cubic, the first-order formula 6 pi m / p, the effective potential and the innermost stable circular orbit | the turn per orbit against the first-order formula, the gap shrinking as (m/p)^2; the integrated turn against the elliptic-integral value (an independent computation); the same first-order value from Gauss's equation with the perturbation -3 GM h^2/(c^2 r^4) (`central_force.first_order_precession`); the Newtonian limit closing the ellipse; Mercury's 43 arcseconds per century from given orbital elements |
| `cosmic-expansion` (order 6) | AST5 | `cosmology.py`: the Hubble rate of a Friedmann model with matter, radiation, curvature, and a cosmological constant; the scale factor integrated in time; the comoving, transverse, luminosity, and angular diameter distances by quadrature; the distance of a light ray integrated through a(t) as a second method; the age; the analytic distances of the Einstein-de Sitter, empty (Milne), and de Sitter models and the flat matter-plus-Lambda age | the distance-redshift relation by quadrature against the analytic cases (Einstein-de Sitter, Milne, de Sitter) to a stated tolerance; the ray integrated through the computed a(t) against the quadrature; a(t) of matter only against t^(2/3) and the flat matter-plus-Lambda age against its closed form; the low-redshift Hubble law and its first correction (q0) recovered with a gap of order z^2; the turnover of the angular diameter distance at z = 5/4 in Einstein-de Sitter |

Units: c = 1 in AST10 (stated), with SI from `scipy.constants` where a
number in metres or seconds is shown (the muon, given values). G = c = 1
with m = GM/c^2 in AST4; the Sun's mass parameter 1.32712440018e20 m^3/s^2
and Mercury's elements are given values. AST5 in units of the Hubble time
and the Hubble distance c/H0, with H0 = 70 km/s/Mpc a given toy value for
the distances in megaparsecs. The toy models' density parameters are given
values, not fitted to data; the page says so.

## Decisions

| Decision | Reason |
|---|---|
| Test-body Schwarzschild orbit as the relativistic model, the first-order formula 6 pi GM/(c^2 a (1 - e^2)) as the post-Newtonian prediction | The Issue asks for the precession checked against the first-order formula; the exact geodesic of a test body is the model whose first order that formula is, so the gap of order (m/p)^2 checks it, and the elliptic integral gives an exact second reference. Two comparable masses (the two-body 1PN problem) are stated as a limit |
| Orbit integrated as u(phi) in the Schwarzschild angle | Coordinate-independent observable (the angle between periapses), no proper-time or coordinate-time choice needed; the exact cubic's roots give the reference |
| Distances by quadrature (`scipy.integrate.quad`) and, independently, by integrating a(t) and the comoving distance of a ray in time | Two methods for the relation the Issue names; the analytic cases are the reference |
| Toy density parameters (0.3, 0.7) given, not fitted | AST5 is a simulation lesson with toy models; a measured Hubble diagram is not part of the slot |
| No change to the architecture, ADRs, the curriculum file, the atlas, the glossary, or CI | Slots AST10, AST4, AST5, the course, and the atlas concepts (`special-relativity`, `curved-spacetime`, `cosmic-expansion`) exist |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; reference curves labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- AST10: a spacetime diagram of events and their boosted images on the
  hyperbolas of constant interval (preview); the gap from the Newtonian
  limit against beta, log-log, with a slope-two reference; the total
  momentum of a collision against the boost velocity, relativistic and
  Newtonian.
- AST4: the precessing strong-field orbit beside the closed Newtonian
  ellipse (preview); the turn per orbit against m/p with the first-order
  line and the exact elliptic-integral curve; the effective potential for
  several angular momenta with the innermost stable circular orbit.
- AST5: the scale factor against time for the toy models (preview); the
  luminosity distance against redshift, numerical points on the analytic
  curves; the angular diameter distance with its turnover.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_astrophysics.py`: each new function against a closed form, a limit, or an independent computation.
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes
  what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the three lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
