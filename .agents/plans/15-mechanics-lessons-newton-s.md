# Plan: Issue #15, F04 — Mechanics lessons: Newton's laws and projectile motion with drag

- Issue: #15 (source: `docs/roadmap.md`, F04)
- Branch: `feature/15-mechanics-lessons-newton-s`
- Base commit: `f38d16c`
- Risk: Medium (physics and numerical correctness need independent review;
  passing checks do not prove a lesson teaches the right thing)
- Governing documents: `docs/architecture.md` ("Lesson model", "Verified
  display forms", the per-lesson budget of 30 seconds), ADR 002 (code by
  reference, every number from an executed cell), `docs/authoring.md` (the
  format F02 fixed), the F05 and F09 roadmap entries (they reuse the
  stepping interface and the projectile functions defined here)
- Written by the implementer: no plan existed when the feature started. The
  Issue asks for a short one: lesson outline, code interface, validation
  strategy.

## Goal

Publish M2, "Newton's laws as a first-order system", and M3, "Projectile
motion with quadratic drag", in the F02 format, on top of a stepping
interface in `pbc.mechanics` that F05 extends with other integrators and
F09 calls from an agent.

## Current state at the base commit

F02 and F03 are merged: one lesson (M1, `pbc.mechanics.kinematics`, with
the acceleration a function of time only and a scalar state), the lesson
source checks, the built-site checks, the learning path. The F02 plan left
"the general stepping interface" to F04.

## Code interface

Three new modules under `src/pbc/mechanics/`. `kinematics.py` is unchanged:
M1 keeps its deliberately small interface, and a unit test shows the new
stepper reproduces it on a line.

| Module | Contents |
|---|---|
| `dynamics.py` | `State(t, x, v)` with `x` and `v` as vectors (one entry per dimension; lists and numbers are converted); `Trajectory(t, x, v)` with one row per instant; the type aliases `Force`, `Acceleration` (both `f(t, x, v) -> vector`) and `Stepper` (`step(state, acceleration, dt) -> State`); `newton(mass, *forces) -> Acceleration`; `weight(mass, g)` with `g` a vector; `euler_step`; `simulate(initial, acceleration, dt, n_steps, step=euler_step, until=None)` |
| `drag.py` | `linear_drag(b)` (kg/s), `quadratic_drag(c)` (kg/m), `drag_constant(density, drag_coefficient, area)`, and the exact `fall_with_linear_drag(initial, mass, b, g, t)` |
| `projectile.py` | `launch(speed, angle, height)`, `fly(initial, acceleration, dt, step, max_steps)` (stops after the first state below the ground), `landing(trajectory) -> Landing(t, x)` (linear interpolation within the last step), `projectile_range(speed, angle, mass, drag, dt, *, height, g, step)`, `drag_free_range(speed, angle, g)` |

Decisions and reasons:

| Decision | Reason |
|---|---|
| The stepping interface is `step(state, acceleration, dt)` on a position and velocity split, not `f(t, y)` on one state vector | F05's symplectic Euler and velocity Verlet need the split; Runge-Kutta 4 can be written on it. The signature is M1's `euler_step` with the acceleration now a function of the whole state, so the lesson reads as a continuation |
| Forces are plain functions and `newton` sums them | "Forces as functions" is the Issue's goal; superposition becomes `newton(m, weight(...), drag(...))` and a learner adds a force model in one line (M2, exercise 3) |
| `g` is a vector argument of `weight` | The same code runs on a line and in a plane; the page, not the reader, decides which way is down |
| `simulate` takes `until` | A flight ends at the ground, not after a fixed number of steps; F09's tool functions need the same |
| `projectile_range` has scalar, documented, unit-carrying parameters and keyword-only extras | Acceptance criterion 6, and the shape of an agent tool with bounded arguments (ADR 004) |
| Only explicit Euler | The Issue puts other integrators out of scope (F05). The lessons say what a first-order method costs and point forward |

## Lesson outline

**M2, `02-newtons-laws`, id `newtons-laws`, difficulty 2, prerequisite
`kinematics`.** Newton's second law as a first-order system in vectors;
force models as functions; the update rule with the acceleration evaluated
at the state; the exact solution of the fall with linear drag (time constant
τ = m/b, terminal velocity g τ); what explicit Euler does to it exactly
(factor 1 − Δt/τ per step, instability for Δt > 2τ). Code: `State`,
`newton`, `weight`, `linear_drag`, `euler_step`, `simulate`,
`fall_with_linear_drag` by reference. Worked examples: the fall from rest
against the exact solution and against the exact formula for the method's
own iterates (to round-off); halving the time step; a throw in the plane
with and without drag. Exercises: the stability limit (Δt = 1.5τ and
2.5τ), time to 99 per cent of the terminal speed, a spring force through the
same interface (the amplitude grows; M4 explains).

**M3, `03-projectile-motion-with-drag`, id `projectile-with-drag`,
difficulty 2, prerequisite `newtons-laws`.** Quadratic drag and the terminal
speed as the scale of the problem; why the coupled equations have no closed
form; the validation strategy for a problem without one (limiting cases,
convergence with Richardson extrapolation, physical sense); finding the
ground. Code: `quadratic_drag`, `drag_constant`, `launch`, `fly`,
`landing`, `projectile_range`, `drag_free_range` by reference. Worked
examples, for a tennis ball thrown at 25 m/s (about its terminal speed):
one throw with and without drag; the drag-free limit, with the error
predicted by M1 (v_x Δt); convergence with drag (differences halve,
extrapolated limit, log-log error plot); the range against the launch angle
with the best angle from a bounded minimiser (about 40.5° with drag, 45°
without). Exercises: the terminal speed as the other limit, the step for a
millimetre, a steel ball of the same size.

Both lessons state their assumptions with what breaks for each, including
the method's own failure modes (instability, interpolation of the landing).

## Validation strategy

| Criterion | Test |
|---|---|
| 2, M2 against the analytic solution | `tests/unit/test_drag.py::test_euler_matches_the_exact_fall_within_an_explicit_tolerance` (dt = τ/2000 over 5τ: velocity within 2.5e-3 m/s, position within 5e-3 m; about 1.4 times the observed error); `::test_euler_relaxes_to_terminal_velocity_by_the_factor_one_minus_dt_over_tau` (the iterates equal the closed form of the method to 1e-12, including the unstable step); `::test_euler_error_halves_when_the_time_step_halves_under_linear_drag`; `::test_exact_fall_satisfies_the_equation_of_motion` (the reference itself solves the ODE) |
| 3, M3 drag-free limit | `tests/unit/test_projectile.py::test_without_drag_the_simulated_range_tends_to_the_closed_form` (within 5e-3 m at dt = 1e-4, and the error equals v_x dt up to the interpolation bound) |
| 3, M3 convergence | `::test_with_drag_the_range_converges_at_first_order_under_refinement` (orders within 0.05 of 1 over four halvings; Richardson limits agree within 1 cm); `tests/unit/test_drag.py::test_a_long_fall_under_quadratic_drag_reaches_the_terminal_speed` |
| Physics the lessons claim | `::test_drag_shortens_the_range_and_lowers_the_best_angle`, `::test_launching_from_a_height_lengthens_the_flight` |
| Stepping interface for F05 and F09 | `tests/unit/test_dynamics.py::test_another_stepper_with_the_same_signature_replaces_explicit_euler`, `::test_on_a_line_with_a_time_dependent_acceleration_it_is_the_first_lesson`, `::test_simulation_stops_after_the_first_state_that_meets_the_condition`; `test_projectile.py::test_another_stepper_is_used_when_given` |
| 1, 4, 5 | The existing lesson source checks and built-site checks run on every lesson; `tests/e2e/test_lessons.py` now also pins displayed rows of M2 and M3 (`REFERENCE_ROWS`) so the Linux build must reproduce the macOS digits |

## Other changes

- `tests/integration/test_lesson_template.py`: the lesson made from the
  template took order 2, which M2 now has. It takes the next order of the
  mechanics strand, read from the site, so no later lesson needs this edit.
- `docs/authoring.md`: the example directory in "Create a lesson" was
  `02-newtons-laws`, which now exists; it names a future lesson.
- `README.md`: status paragraph.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| The best angle with drag for the tennis ball is about 40°, and the range at 35° is below the one at 45° | The unit test and the lesson compare 40° with 45° |
| The convergence table of M3 already puts two steps within 1 cm | Exercise 2 asks for 1 cm from the table and 1 mm by continued halving |
| The observed order under linear drag approaches 1 from below | The M2 prose says so, instead of "from above" |
| Pandoc's smart quotes turn the straight apostrophe of "Newton's" into a typographic one in the generated headers, so the built text no longer equals the front matter title and the built-site header check fails on the neighbours of M2 | The title carries the typographic apostrophe in the front matter. A title with a straight apostrophe cannot pass that check as it stands; worth a note in the authoring guide or a normalisation in the check if it recurs (not changed here: checks are out of scope) |
| The path page links every prerequisite of a lesson, so the template test's count of lesson links was off once lessons had prerequisites | The test counts the prerequisites of the mechanics lessons too |

## Deliberately not done

- Other integrators, a `Flight` result type, or terminal-speed helpers: F05
  and F09 add what they need behind the same interface.
- `update-issue-with-plan.sh`: it edits the Issue on GitHub; left to the
  human.

## Steps

1. `pbc.mechanics.dynamics`, `drag`, `projectile` with unit tests. Done.
2. Lessons M2 and M3. Done.
3. Template test, reference rows, docs. Done.
4. `./scripts/verify.sh`; evidence below.

## Verification evidence

2026-10-07, macOS (Darwin 24.6) on Apple M1 Max, working tree on base
`f38d16c` (uncommitted; `finish-feature.sh` creates the commit).

`./scripts/verify.sh`: **Verification passed**, 14 of 14 checks `PASS`, wall
time 247 s. The workflow self-tests were reported as `SKIP`: no workflow
file differs from `origin/main`. A first run before it failed on two tests,
both fixed (see "Discoveries"): the template test's count of path page
links, and the header check on the neighbours of M2 because of the
apostrophe in its title. No file changed after the passing run except this
plan.

| Check | Result |
|---|---|
| `unit-tests` | 109 passed, 2.0 s (42 of them in the three new test files) |
| `lean-build` | passed; axiom audit of 1 declaration |
| `check-tests` | 189 passed, 139 s |
| `lesson-checks` | 7 passed, 0.9 s |
| `site-build` | 7 pages, including both new lessons |
| `site-checks` | 42 passed, 52 s |
| `determinism` | two builds byte-identical, 35 files |

A single `quarto render` of each new page in this environment, measured
separately: M2 about 5 s, M3 about 7 s, including Quarto's start-up.

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | Both lessons pass `lesson-checks` and every test of `tests/e2e` (sections, header and path page, excerpts identical to source, every cell executed, accessibility scan, widths, readable without JavaScript). `test_reproduce_commands_regenerate_the_page_within_the_time_budget` regenerates each page byte for byte and asserts the render under 30 s | built and checked; publication needs the merge |
| 2 | `tests/unit/test_drag.py::test_euler_matches_the_exact_fall_within_an_explicit_tolerance` (2.5e-3 m/s, 5e-3 m), `::test_euler_relaxes_to_terminal_velocity_by_the_factor_one_minus_dt_over_tau` (1e-12), `::test_euler_error_halves_when_the_time_step_halves_under_linear_drag` | met |
| 3 | `tests/unit/test_projectile.py::test_without_drag_the_simulated_range_tends_to_the_closed_form`, `::test_with_drag_the_range_converges_at_first_order_under_refinement`, and `test_drag.py::test_a_long_fall_under_quadratic_drag_reaches_the_terminal_speed` | met |
| 4 | The "Assumptions" section of each lesson: seven numbered assumptions in M2 and six in M3, each with what breaks, including the method's own failure modes | met; the reviewer judges the physics |
| 5 | M2 has three exercises, M3 three, each with a `.solution` whose numbers are cell output or inline expressions; `check_sections` requires a solution per exercise and the built-site check that every cell ran covers the solutions | met |
| 6 | `pbc.mechanics.projectile` (`launch`, `fly`, `landing`, `projectile_range`, `drag_free_range`) and `pbc.mechanics.drag` (`quadratic_drag`, `drag_constant`), each with parameters and units in its docstring, shown by reference on the M3 page | met |

Not done by the implementer: `update-issue-with-plan.sh 15 <plan>`, which
edits the Issue on GitHub, and the Linux run, which is the CI run of the pull
request (it also asserts the pinned rows of `REFERENCE_ROWS`, produced on
macOS).
