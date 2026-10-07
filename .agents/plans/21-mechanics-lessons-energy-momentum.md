# Plan: Issue #21, F06 — Mechanics lessons: energy, momentum, and a capstone orbit

- Issue: #21 (source: `docs/roadmap.md`, F06)
- Branch: `feature/21-mechanics-lessons-energy-momentum`
- Base commit: `4343fe0`
- Risk: Medium (physics and numerical correctness need independent review;
  three lessons make this the largest content feature; the pairwise-force
  interface is reused by F11)
- Governing documents: `docs/architecture.md` ("Lesson model", "Verified
  display forms", the per-lesson budget of 30 seconds), ADR 002 (code by
  reference, every number from an executed cell), `docs/authoring.md`, the
  F04 and F05 plans (the stepping interface `step(state, acceleration, dt)`
  and `INTEGRATORS`, which every new module and lesson here runs on), the
  F11 roadmap entry (many colliding particles build on the pairwise forces
  defined here)
- Written by the implementer: no plan existed when the feature started. The
  Issue asks for a short one.

## Goal

Publish M6, "Energy conservation", M7, "Momentum and collisions", and M8,
"The Kepler orbit", in the F02 format, so that the mechanics strand is
complete at eight lessons, with the conservation laws as diagnostics of a
simulation and a capstone that reuses the code of every lesson before it.

## Current state at the base commit

F02 to F05 are merged: five lessons, `pbc.mechanics.dynamics` (`State`,
`newton`, `simulate(..., step=...)`), `drag`, `projectile`, `oscillator`,
and `integrators` (`INTEGRATORS`: explicit Euler, symplectic Euler,
velocity Verlet, Runge-Kutta 4), the lesson source checks, the built-site
checks with pinned reference rows, and the learning path.

## Code interface

Four new modules under `src/pbc/mechanics/`; nothing existing changes.

| Module | Contents |
|---|---|
| `energy.py` | `Potential` (U(x) -> J); `kinetic_energy(trajectory, mass)`, `potential_energy(trajectory, potential)`, `mechanical_energy(trajectory, mass, potential)`, one value per instant; `energy_drift(energies)`, the largest relative deviation from the initial energy, the one number a run is judged by |
| `pendulum.py` | The pendulum as a particle on the arc, coordinate s = L θ in metres: `pendulum_force(mass, length, g)` (the tangential component of the weight, -m g sin(s/L), a `Force` for `newton`), `pendulum_potential(mass, length, g)`, `small_angle_period(length, g)`, `pendulum_period(length, amplitude, g)` (exact, from the complete elliptic integral) |
| `particles.py` | n particles in d dimensions as one state vector of length n d: `PairwiseForce` (F(r) on the first particle of a pair, with r its position relative to the second; the second feels -F), `stack`, `unstack`, `interacting(masses, pairwise) -> Acceleration`; `centre_of_mass`, `total_momentum`, `kinetic_energy` with per-particle masses; `reduced_mass`; the pair forces `spring_pair(k, rest_length)` and `soft_sphere(k, diameter)`; `first_contact(r, u, diameter)` and `hard_sphere_collision(m1, v1, m2, v2, normal)`, the exact elastic collision the soft spheres tend to |
| `orbit.py` | `gravitational_attraction(G, m1, m2)` (a `PairwiseForce`), `central_gravity(gm, mass)` (a `Force`), `gravitational_potential(gm, mass)`, `angular_momentum(trajectory, mass)` in the plane, `Orbit(semi_major_axis, eccentricity, period)` with `orbital_elements(state, gm)` from energy and angular momentum, `eccentricity_vector(state, gm)`, and `kepler_motion(initial, gm, t)`, the exact bound orbit from Kepler's equation |

Decisions and reasons:

| Decision | Reason |
|---|---|
| The pendulum's coordinate is the arc length, not the angle | The state stays in metres and metres per second, the tangential weight is a `Force` for `newton` like every other force of the course, and the small-angle limit is literally `spring(m g / L)` of M4 |
| Many particles are one long state vector; `interacting` reshapes | `simulate` and all four steppers are reused unchanged (criterion 3); Newton's third law is built into `PairwiseForce`, so momentum conservation is a property of the interface, tested for every integrator |
| A collision is a brief, strong, position-dependent force (soft spheres), not an event | The course models forces as functions; the hard-sphere formula is the limit the soft spheres tend to as the stiffness grows, which the lesson measures. Event detection would need another simulation loop |
| The two-body problem is reduced to the relative coordinate under `central_gravity(G (m1 + m2), mu)` | One particle, every tool of M4 to M6 applies; the full two-body simulation with `interacting` and `gravitational_attraction` is shown to agree with it, and the centre of mass moves uniformly (M7) |
| `kepler_motion` solves Kepler's equation for the exact orbit | Like `harmonic_motion` and `fall_with_linear_drag`, the exact motion is what the convergence tables and the unit tests compare with |
| Functions take G or GM as an argument; M8 uses astronomical units | The stepping interface is unit-agnostic; years and astronomical units keep every printed number readable. The modules say so |
| The energy helpers take a `Potential` callable | The F05 plan deferred the general potential to this feature; the pendulum, the spring, and gravity each give one |

## Lesson outline

**M6, `06-energy-conservation`, id `energy-conservation`, difficulty 2,
prerequisite `numerical-integrators`.** Work and the work-energy theorem;
conservative forces and the potential; the pendulum on the arc, its
potential, the small-angle limit as the oscillator of M4, the exact period
from the elliptic integral, and the energy 2 m g L that separates swinging
from going over the top. Energy drift as a diagnostic: the four integrators
on a large-amplitude pendulum; the drift converges at the order of the
method, a convergence check without an exact solution; what the energy does
not catch (the phase error of symplectic Euler against the exact period);
a pendulum near the top that explicit Euler sends over it. Exercises: the
amplitude at which the period is one per cent long; the energy balance with
drag (the loss equals the work of the drag force); the step for a stated
drift over a long run.

**M7, `07-momentum-and-collisions`, id `momentum-and-collisions`,
difficulty 2, prerequisites `energy-conservation`.** Pairwise forces and
Newton's third law; total momentum and the centre of mass; the proof that
every integrator of the course conserves the total momentum exactly;
elastic collisions and the hard-sphere result; the soft-sphere model and
its contact time. Worked examples: two masses on a spring (centre of mass
in a straight line to round-off, relative motion is M4's oscillator with
the reduced mass); a head-on collision against the hard-sphere formula, the
step against the contact time; an off-centre collision whose scattering
angle tends to the hard-sphere angle as the stiffness grows. Exercises:
energy transfer against the mass ratio; a cradle of three balls; the
centre-of-mass frame.

**M8, `08-kepler-orbit`, id `kepler-orbit`, difficulty 3, prerequisites
`energy-conservation`, `momentum-and-collisions`.** The two-body problem
and its reduction; the inverse-square force, energy and angular momentum,
the orbital elements from them, Kepler's laws; the exact orbit from
Kepler's equation; the proof that the symplectic methods conserve angular
momentum exactly for any central force. Worked examples: one orbit with
each method against the exact motion; energy and angular momentum per
step; convergence at the orders 1, 1, 2, 4; a thousand orbits, with the
semi-major axis and the perihelion direction over time (bounded energy
with precession for velocity Verlet, a steady drain for Runge-Kutta 4);
the two bodies simulated together with M7's code against the reduced
problem. Exercises: Kepler's third law from measured periods; escape;
the wobble of the star.

## Validation strategy

| Criterion | Test |
|---|---|
| 2, momentum | `tests/unit/test_particles.py`: total momentum and the straight-line centre of mass to round-off for every integrator of `INTEGRATORS`, on three unequal particles in the plane |
| 2, orbit | `tests/unit/test_orbit.py`: velocity Verlet and symplectic Euler conserve the angular momentum to round-off (any central force); velocity Verlet's energy stays within a stated relative bound over many orbits and does not drift; the position error converges at order 2 against `kepler_motion` |
| Pendulum | `tests/unit/test_pendulum.py`: the small-angle limit is M4's oscillator; the simulated period matches `pendulum_period` within a stated tolerance; energy drift bounded for Verlet and growing for explicit Euler |
| Exact references solve their equations | `kepler_motion` passes through the initial state, conserves energy and angular momentum, satisfies the equation of motion (central differences), has the period of the third law; `pendulum_period` tends to the small-angle period |
| 1, 3, 4, 5 | The existing lesson source checks and built-site checks on every lesson; `REFERENCE_ROWS` pins displayed rows of M6, M7, M8 |

## Steps

1. Modules and unit tests. Done.
2. Lessons M6, M7, M8. Done.
3. Reference rows, docs (README status, authoring example directory). Done.
4. `./scripts/verify.sh`; evidence below. Done.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| Symplectic Euler's period error on the pendulum depends on the initial state: for a release from rest at exactly 90° it nearly vanishes, while at 120° it is of the same size as velocity Verlet's with the opposite sign. The first-order error of the method is a phase shift between position and velocity, not a plain period error | The worked examples of M6 use 120°, and the lesson measures the lag of the bob directly rather than claiming an order for the period error |
| Explicit Euler's energy on the 170° pendulum crosses 2 m g L during the first passage through the bottom, not in a later swing: the method feeds energy fastest where the bob is fastest | The prose and the alt text say so; the cell prints the crossing time |
| The energy drift of Runge-Kutta 4 converges at about order 5 on the pendulum, as its per-step energy factor on the oscillator (1 - z⁶/72) predicts | M6 says "at least the order of the method" and explains the extra power |
| The outcome error of a soft-sphere collision does not shrink smoothly with the step: the contact force has a kink where the spheres touch (assumption 3 of M5) | M7 prints the table as it is and explains the kink; the energy drift during the contact, which is smooth and follows the M5 band formula, is the quantity to judge the step by |
| For a Hookean contact, a head-on soft-sphere collision gives the hard-sphere velocities for any stiffness; only an off-centre collision depends on the stiffness, through the rotation of the line of centres during the contact, with a difference that falls as 1/sqrt(k) | M7's third example measures exactly this; the first exercise uses the head-on identity |
| Round-off-level outputs (momentum conservation to 1e-15, angular momentum spread to 1e-15) can differ between platforms | They are not among the pinned `REFERENCE_ROWS`; the unit tests assert them with tolerances |
| The two-body check in the exploration script disagreed with the one-body reduction by the size of the orbit | A sign error in the script, not the code: the planet was the second particle, so the relative coordinate was the negative. The lesson defines the relative position as planet minus star in both forms |
| A `ValueError` printed on the page (the unbound orbit of M8, exercise 2) carried an unformatted float | `orbital_elements` formats the energy per unit mass with four significant digits |

## Review 01: approved FIX_NOW findings

Triage artifact `.agents/triage/feature-21-mechanics-lessons-energy-momentum-review-01-triage.json`.

| Finding | Resolution |
|---|---|
| M1, exact circular orbits collapse to the origin: `orbital_elements` took e from sqrt(1 + 2 ε h²/GM²), which leaves a round-off residual of about 1e-8 near a circle, and `kepler_motion` divided the near-zero eccentricity vector by it | `orbital_elements` evaluates e as the length of `eccentricity_vector`, so the two agree to round-off; `kepler_motion` divides whenever e > 0 and falls back to the position direction only at e = 0. Regression tests: 40 circular states over five radii, four orientations, both senses, and three near-circular states with e from 1e-10 to 1e-4, all of which failed before the fix |
| M2, separation dependence does not imply a conservative force | Assumption 3 of M7 now requires a central pair force F(r) = f(r) r/r, says the interface does not enforce it, gives the non-central counter-example, and notes that both pair forces of the lesson are central |
| MIN1, the cradle explanation reversed the contact-time regime | The sound-transit sentence is gone. The solution says the stiffness of a linear contact only sets the time scale (checked: the final velocities agree to four digits at 1e3, 1e4, and 1e5 N/m) and points to the nonlinear Hertz contact as the different model |
| MIN2, finite-run energy bounds presented as perpetual | M6 qualifies the symplectic band to long runs at a stable fixed step with a smooth potential, and states the measured twenty swings; M8 states the measured thousand orbits |
| MIN3, an orbit assertion was unconditionally true | The `or True` assertion is removed; the following assertion bounds every distance by the periapsis and apoapsis |

## Verification evidence

2026-10-07, macOS (Darwin 24.6) on Apple M1, working tree on base `4343fe0`
(uncommitted; `finish-feature.sh` creates the commit).

`./scripts/verify.sh`: **Verification passed**, 14 of 14 checks `PASS`. The
workflow self-tests were reported as `SKIP`: no workflow file differs from
`origin/main`. No file changed after the passing run except this plan.

| Check | Result |
|---|---|
| `unit-tests` | 185 passed, 6.0 s (49 of them in the four new test files) |
| `lean-build` | passed; axiom audit of 1 declaration |
| `check-tests` | 189 passed, 196 s |
| `lesson-checks` | 7 passed, 2.6 s |
| `site-build` | 12 pages, including the three new lessons |
| `site-checks` | 72 passed, 138 s |
| `determinism` | two builds byte-identical, 55 files |

A single `quarto render` of each new page in this environment, measured
separately, including Quarto's start-up: M6 about 13 s, M7 about 8 s, M8
about 12 s.

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | All three lessons pass `lesson-checks` and every test of `tests/e2e` (sections, header and path page, excerpts identical to source, every cell executed, accessibility scan, widths, readable without JavaScript, the pinned rows of `REFERENCE_ROWS`). `test_reproduce_commands_regenerate_the_page_within_the_time_budget` regenerates each page byte for byte and asserts the render under 30 s | built and checked; publication needs the merge |
| 2 | Momentum: `tests/unit/test_particles.py::test_every_integrator_conserves_the_total_momentum_to_round_off` (all four integrators, three unequal particles in the plane, 500 steps: total momentum within 1e-13, centre of mass on its line within 1e-12). Orbit: `tests/unit/test_orbit.py::test_the_symplectic_methods_conserve_the_angular_momentum_to_round_off` (symplectic Euler and velocity Verlet within 1e-12 relative at a coarse step; explicit Euler and RK4 shown not to), `::test_verlet_keeps_the_energy_of_the_orbit_in_a_band_and_runge_kutta_drains_it` (e = 0.5, 200 orbits at 100 steps per orbit: Verlet drift below 2 per cent and no larger over the whole run than over its first half; RK4 drift grows), `::test_the_position_error_on_the_orbit_converges_at_the_order_of_the_method` (orders within 0.15 of 2 and 4 against `kepler_motion`) | met |
| 3 | M8 imports `State`, `newton`, `simulate` (M2), `INTEGRATORS` (M5), `mechanical_energy` and `energy_drift` (M6), `interacting`, `centre_of_mass`, `reduced_mass`, `stack`, `unstack` (M7); `pbc.mechanics.orbit` adds only the gravitational force, the conserved quantities, the elements, and the exact motion. The two-body example runs M7's code on M8's force and agrees with the one-body reduction to 7e-13 AU. No function is copied | met |
| 4 | "Assumptions" sections: six numbered assumptions in M6, six in M7, seven in M8, each with what breaks. Three exercises in each lesson, each with a `.solution` whose numbers are cell output or inline expressions | met; the reviewer judges the physics |
| 5 | `lesson-checks` validates the path (orders 1 to 8 without a gap, prerequisites earlier in the path); `tests/e2e/test_learning_path.py` checks the path page lists the eight mechanics lessons in order with their prerequisites and that every header matches. Prerequisites: M6 needs M5; M7 needs M6; M8 needs M6 and M7 | met |

Not done by the implementer: `update-issue-with-plan.sh 21 <plan>`, which
edits the Issue on GitHub, and the Linux run, which is the CI run of the
pull request (it also asserts the pinned rows of `REFERENCE_ROWS`, produced
on macOS; round-off-level outputs were deliberately not pinned).

No manual steps: the feature needs no repository setting, secret, or
one-time command, so `.agents/manual-steps/21.md` is not created.
