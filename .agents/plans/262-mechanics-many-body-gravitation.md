# Plan: F69 — Mechanics: many-body gravitation, nonlinear dynamics, rotational motion (Issue #262)

- Issue: #262 (source: `docs/roadmap.md`, F69); slots M13, M14, M17.
- Branch: `feature/262-mechanics-many-body-gravitation`; base `3e21eb3`, brought up to `origin/main` 19108b2.
- Written by the implementer: no plan existed when the feature started.
- Gate: 45 lessons before, 48 after, within the interim full-run capacity
  of 64 lessons (ADR 014 status, amendment of 2026-10-21).
- Risk: Level 3 by the owner's decision of 2026-10-24 ("Level 3 + CI als
  poort"). The trigger is the changed planned-slot assertion of
  `tests/unit/test_curriculum.py` (M13, now filled, gives way to M15). No
  protected path is changed: `docs/architecture.md` and `docs/roadmap.md` are
  left as they are (the layout note names the mechanics modules as examples,
  not as a list; the roadmap's slot table is updated by the planning cycles,
  not by a lesson feature). No dependency is added.

## Design

Three format 2 lessons in the `mechanics` strand, built to the F117
experiment contract (one experiment module per lesson, one `draw_`
function per figure, a unit test per experiment, "Run this experiment").

| Dir | Id | Slot | Code | Checks |
|---|---|---|---|---|
| `17-many-body-gravitation` | `many-body-gravitation` | M13 | `pbc.mechanics.nbody`: the gravitational acceleration of n bodies (vectorised over pairs), the potential and total energy, the total angular momentum, the centre of mass, barycentric start | the two-body case against the exact Kepler motion of `pbc.mechanics.orbit`; energy and angular-momentum drift per integrator of `INTEGRATORS` over many orbits of a Sun, Jupiter, Saturn system (band against trend); the figure-eight choreography of three equal masses closing on itself after its measured period, with the bodies permuted after a third of it |
| `18-nonlinear-dynamics-and-bifurcations` | `nonlinear-dynamics-and-bifurcations` | M14 | `pbc.mechanics.bifurcation`: the damped bead on a rotating hoop (pitchfork at the known threshold Ω_c = sqrt(g/R), branch arccos(g/(R Ω²)), linearised rates), the Hopf normal-form oscillator x'' - (μ - x²) x' + x = 0 (limit cycle with amplitude 2 sqrt(μ) for small μ), the attractor reached from a start, many parameters in one vectorised run | the bifurcation diagram of the hoop simulated and checked against the threshold and the branch; the decay rate near the threshold against the linearised rate, and the algebraic decay t^(-1/2) at the threshold where linearisation fails; the limit-cycle amplitude against 2 sqrt(μ) |
| `19-rotational-motion` | `rotational-motion` | M17 | `pbc.mechanics.rigid_body`: the inertia tensor of point masses, the parallel-axis theorem, the heavy symmetric top as a rigid body in space (unit quaternion and angular momentum, torque of gravity, RK4), its energy and the conserved components of the angular momentum, the precession of the axis, the steady-precession rates and the fast-top limit m g l / (I₃ ω₃) | the inertia tensor of a discretised disc against ½ m r² and ¼ m r²; dL/dt against the torque; energy, vertical, and axial angular momentum conserved by the run; the measured mean precession rate converging to m g l / (I₃ ω₃) as the spin grows; a start on steady precession reproducing the exact slow root; the unit check: the run in centimetres and grams gives the same rate in rad/s |

## Decisions

| Decision | Reason |
|---|---|
| No REBOUND reference artifact is declared for M13 | The roadmap makes it optional; REBOUND may never be in a required path (architecture, "Lesson code package"), and its output would be a `modelled-reference` card under ADR 007 that needs the owner's review of its provenance and rights. The independent references are the exact Kepler motion (two bodies) and the closure of the figure-eight (three bodies). The lesson's limits name REBOUND's integrators as the place to go further, marked as not computed by the build. |
| M14 is mechanical: the bead on a rotating hoop and a self-excited oscillator | The course is mechanics; both have closed-form thresholds, so the diagram is checked against a known threshold, not a fitted one |
| The rigid body is integrated in space (quaternion and angular momentum), not in Euler angles | It shows torque = dL/dt and the inertia tensor directly, has no coordinate singularity at the vertical, and lets the checks use the conserved quantities |
| Integration by the course's own steppers (`rk4_step`, `INTEGRATORS`), or a first-order RK4 for the rigid body in `rigid_body` | No new dependency; the reader sees one stepping idea throughout |
| M17 lists `lagrangian-mechanics` (M10) and `hamiltonian-mechanics` (M11) among its prerequisites | The Issue links M17 to M10 and M11; D13 does not exist yet |
| `tests/unit/test_curriculum.py` updated | The published lessons that fill a slot change; the planned-slot assertion names M13, which this feature fills |

## Visual deliverables

Scientific figures only; no page layout, diagram, or animation.

Skills: pbc-scientific-visualization@a70b501

- M13: relative energy error over time per integrator (log scale, line
  styles and markers), the figure-eight orbit (preview), the Sun, Jupiter,
  Saturn orbits.
- M14: the bifurcation diagram of the hoop (simulated points over the
  analytic branches, the threshold marked; preview), the decay at and near
  the threshold (log-log, reference slope labelled), the limit cycle in
  phase space.
- M17: the path of the top's axis (precession with nutation; preview), the
  measured precession rate against the fast-top limit over the spin.
- Validation: unit tests of the modules against closed forms; the
  experiments' tests assert the science on the written results.
- Fallback: alt text for every figure; every number also in a result table
  or the prose.

## Steps

1. `nbody.py`, `bifurcation.py`, `rigid_body.py` with unit tests.
2. The three experiments with their tests.
3. The three lesson pages.
4. `tests/unit/test_curriculum.py`.
5. Verification: lint, format, unit and lesson tests locally; the full
   verification is the CI full run of the pull request (the owner's
   decision of 2026-10-24; locally the cold-clone render exceeds 30 s, #267).
