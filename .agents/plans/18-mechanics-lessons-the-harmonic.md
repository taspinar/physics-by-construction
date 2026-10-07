# Plan: Issue #18, F05 — Mechanics lessons: the harmonic oscillator and numerical integrators

- Issue: #18 (source: `docs/roadmap.md`, F05)
- Branch: `feature/18-mechanics-lessons-the-harmonic`
- Base commit: `406d834`
- Risk: Medium (physics and numerical correctness need independent review;
  the integrator interface is reused by F06, F07, F08, and F09)
- Governing documents: `docs/architecture.md` ("Lesson model", "Verified
  display forms", the per-lesson budget of 30 seconds), ADR 002 (code by
  reference, every number from an executed cell), `docs/authoring.md`, the
  F04 plan (the stepping interface `step(state, acceleration, dt)` that
  this feature fills), the F07 and F08 roadmap entries (the integrator
  comparison gets the first widget; the Euler energy factor gets the first
  proof)
- Written by the implementer: no plan existed when the feature started. The
  Issue asks for a short one.

## Goal

Publish M4, "The harmonic oscillator", and M5, "Numerical integrators", in
the F02 format, with explicit Euler, symplectic Euler, velocity Verlet, and
Runge-Kutta 4 behind the F04 stepping interface and unit tests of their
order.

## Current state at the base commit

F02, F03, and F04 are merged: three lessons, `pbc.mechanics.dynamics` with
`State`, `newton`, `euler_step`, and `simulate(..., step=...)`, the drag
and projectile modules, the lesson source checks, the built-site checks,
and the learning path. `simulate` already takes any stepper with the
signature `step(state, acceleration, dt)`; nothing but explicit Euler uses
it.

## Code interface

Two new modules under `src/pbc/mechanics/`; `dynamics.py` is unchanged.

| Module | Contents |
|---|---|
| `oscillator.py` | `spring(k)` (Hooke's law, serves on a line and in a plane); `angular_frequency(mass, k)`; `harmonic_motion(initial, mass, k, t)`, the exact motion; `energy(trajectory, mass, k)`, one value per instant; `euler_energy_growth(mass, k, dt)` = 1 + ω² dt², the factor F08 proves |
| `integrators.py` | `symplectic_euler_step`, `verlet_step`, `rk4_step`, each a `Stepper`; `Integrator(name, step, order, evaluations)`; `INTEGRATORS`, the four methods with explicit Euler from `dynamics`, in course order |

Decisions and reasons:

| Decision | Reason |
|---|---|
| The steppers are plain functions with the F04 signature; no class, no state between steps | F04 fixed the interface so that a lesson swaps the method through `simulate(step=...)`; F07's widget and F09's tool argument can name a stepper from `INTEGRATORS` |
| `INTEGRATORS` records the order and the evaluations per step | M5 loops over the methods for its tables; the stated order is what the cost example predicts from; a unit test checks the stated evaluation count against the calls actually made |
| Velocity Verlet evaluates the acceleration twice per step, the second time at the explicit Euler prediction of the new velocity | The interface keeps nothing between steps, so the acceleration at the new position cannot be carried over. The prediction keeps the method second order on velocity-dependent forces (tested on the linear-drag fall); for velocity-independent forces it is exactly velocity Verlet. The lesson states the count and that a loop with carry-over needs one |
| Runge-Kutta 4 is written on the pair (x, v) with the rate (v, a) | The standard method on the first-order system of M2; four evaluations |
| The oscillator helpers take `(trajectory, mass, k)` and the energy is the total mechanical energy | F06 (energy as a diagnostic, the pendulum) will need a general potential; it adds what it needs rather than inheriting a premature abstraction |
| The modified energies conserved by symplectic Euler and velocity Verlet, and the RK4 energy factor, are formulas in the lesson cells and in unit tests, not package functions | They are claims about the methods on this one force, used once on the page; the tests protect them as acceptance-criterion-4 claims |

## Lesson outline

**M4, `04-harmonic-oscillator`, id `harmonic-oscillator`, difficulty 2,
prerequisite `newtons-laws`.** Hooke's law, ω and the period, the exact
solution; phase space and the energy as the conserved quantity, so the
orbit is an ellipse; the derivation from the update rule that explicit
Euler multiplies the energy by 1 + ω² Δt² at every step (criterion 3), with
the rotation by arctan(ω Δt) as a remark; growth over a fixed time and its
first-order convergence. Code: `spring`, `angular_frequency`,
`harmonic_motion`, `energy`, `euler_energy_growth` by reference. Worked
examples (m = 0.5 kg, k = 2 N/m, ω = 2 rad/s, released from 1 m): three
periods at 64 steps per period against the exact motion; the orbit in phase
space; every energy ratio against the factor (round-off); energy on a log
axis for three steps; the logarithm of the growth halving with the step.
Exercises: steps per period for one per cent over ten periods (about
40 000); a damped oscillator whose drag exactly cancels the artificial
growth (b = k Δt), so the amplitude stays constant until the step changes;
the isotropic spring in the plane.

**M5, `05-numerical-integrators`, id `numerical-integrators`, difficulty 2,
prerequisite `harmonic-oscillator`.** The four update rules; local and
global error and the order; the energy per step from the complex form
u = v + iωx (explicit Euler 1 + z², Runge-Kutta 4 1 − z⁶/72 + z⁸/576) and
the modified energies conserved exactly by symplectic Euler and velocity
Verlet, with the stability limits z < 2 and z < 2√2; cost as acceleration
evaluations; a pointer to Hairer, Nørsett, and Wanner and to Hairer,
Lubich, and Wanner for adaptive steps and geometric integration (the
Issue's "pointer to further reading"). Code: the three steppers and
`Integrator` by reference; `INTEGRATORS` printed by a cell (`excerpt`
takes functions and classes only). Worked examples: three periods at 50
steps per period with the four methods, counted calls, phase-space panels;
accuracy as the largest phase-space distance over two periods, with
observed orders 1, 1, 2, 4 and a log-log figure; energy over twenty
periods in four panels, every formula checked on the same runs, and a
thousand periods for the three methods that survive it; the calls each
method needs for a millimetre over two periods, predicted from the order
(criterion 4). Exercises: the stability limits at 3.5, 3, and 2.2 steps
per period; the orders of velocity Verlet and Runge-Kutta 4 on the
linear-drag throw of M2; the four methods at equal cost.

Both lessons state their assumptions with what breaks for each, including
the method's own failure modes.

## Validation strategy

| Criterion | Test |
|---|---|
| 2, order of each integrator | `tests/unit/test_integrators.py::test_the_higher_order_integrators_show_their_order_on_the_oscillator` (symplectic Euler, Verlet, RK4: orders within 0.1 of 1, 2, 4 over two periods at 50 to 800 steps per period, error measured as the largest phase-space distance); `::test_explicit_euler_shows_first_order_once_the_step_is_small_enough` (within 0.05 of 1 at 1000 to 8000 steps per period); `::test_verlet_and_runge_kutta_keep_their_order_with_a_velocity_dependent_force` |
| 3, Euler energy factor | `tests/unit/test_oscillator.py::test_explicit_euler_multiplies_the_energy_by_the_same_factor_every_step` (every ratio equals 1 + ω² dt² to 1e-12, for dt from 0.01 to 2 s); `::test_explicit_euler_rotates_the_state_by_arctan_and_scales_it_every_step` (the closed form of the iterates) |
| 4, energy behaviour and cost claims | `test_integrators.py::test_symplectic_euler_conserves_a_modified_energy_exactly`, `::test_velocity_verlet_conserves_a_modified_energy_exactly`, `::test_runge_kutta_4_multiplies_the_energy_by_the_same_factor_every_step`, `::test_the_stability_limits_of_the_integrators`, `::test_each_integrator_evaluates_the_acceleration_as_often_as_it_says` |
| The exact solution is right | `test_oscillator.py::test_exact_motion_satisfies_the_equation_of_motion`, `::test_exact_motion_passes_through_the_initial_state_and_repeats_after_a_period`, `::test_energy_is_kinetic_plus_potential_and_conserved_by_the_exact_motion` |
| 1, 5 | The existing lesson source checks and built-site checks run on every lesson; `tests/e2e/test_lessons.py` pins displayed rows of M4 and M5 (`REFERENCE_ROWS`) so the Linux build must reproduce the macOS digits |

## Other changes

- `docs/authoring.md`: the example directory in "Create a lesson" was
  `04-harmonic-oscillator`, which now exists; it names a future lesson.
- `README.md`: status paragraph.
- `tests/integration/test_lesson_template.py` needs no change: it takes the
  next order of the strand from the site.

## Discoveries during implementation

| Finding | Resolution |
|---|---|
| The position error at the end of a whole number of periods shows twice the order of a method: at a turning point a phase error is second order in the position, and the first-order part of symplectic Euler's error is periodic and vanishes at whole periods | The error of a run is the largest distance in a scaled phase plane over the whole run; the lesson says why. The lesson measures it in the plane (x, v/ω), so that the error and the millimetre tolerance of the cost example are in metres (review round 1, M1); the unit tests, which only measure orders, use (ω x, v) |
| Review round 1: the damping exercise of M4 labelled the envelope e^{−bt/(2m)} as the real motion, although the damped oscillation is slightly slower and its peaks lie below the envelope (MIN1); the equal-cost exercise of M5 said Runge-Kutta 4 takes a quarter of velocity Verlet's steps instead of half (MIN2) | M4 prints the maxima of the exact damped solution over the same windows as the simulated columns and states the solution; the period-2 row, where the exact maximum (0.734) differs from the envelope (0.735) at the displayed precision, is pinned in `REFERENCE_ROWS`. M5 says half |
| Review round 2: the prose of the M4 damping exercise still called e^{−γt} the envelope and said the peaks lie below it (MIN1). The velocity of the stated solution is −(ω_d + γ²/ω_d) e^{−γt} sin(ω_d t), so the peaks fall at t = nπ/ω_d and equal e^{−γt} exactly; the bounding envelope is √(1 + (γ/ω_d)²) e^{−γt} | The passage names e^{−γt} as the curve through the peaks, states the bounding envelope, and attributes the small shortfall of the table's exact column to the later peak times within each window of the undamped period. Prose only; no row of the table changes |
| Explicit Euler's error on the oscillator grows as exp(ω² Δt t), so its observed order approaches 1 from above and reaches it only for ω² Δt t ≪ 1 | The unit test for Euler uses 1000 to 8000 steps per period over one period; M5 shows the approach and says why |
| `excerpt` takes a function or class; a module constant like `INTEGRATORS` cannot be shown by reference | M5 prints the registry from an executed cell, a verified display form. A constant excerpt is a change to the authoring helpers, out of scope |
| The first render in a fresh environment takes about 15 s because Matplotlib builds its font cache; later renders of each new page take about 8 s | None needed; the budget is 30 s per page and CI warms the cache on the first page |
| The band of velocity Verlet's energy is ω² Δt² / 4 of the energy, not / 8 as first drafted (E − Ẽ = ½ m ω² (ω² Δt² / 4) x², which swings between 0 and its value at the amplitude) | The lesson states / 4; the cell prints the band |
| An apostrophe in an outside prerequisite ("Euler's formula") is turned into a typographic one by Pandoc's smart quotes, so the built path page and lesson header no longer contain the front-matter text and two built-site checks fail. The F04 plan found the same for a title | The prerequisite is reworded without an apostrophe. Second occurrence; a normalisation in the checks, or a note in the authoring guide, is worth its own Issue |
| A Markdown table in lesson prose was the first on the site; the site styles have no rule for it on a narrow screen, so M5 was 537 px wide at phone width and the sideways-scroll check failed | The summary is a list instead. A scrolling, focusable table style is a site-format change for its own Issue |

## Deliberately not done

- Adaptive step-size methods: out of scope; a pointer to further reading
  is in M5.
- A general energy function with a potential, `Flight`-like result types,
  a widget, a Lean proof: F06, F07, F08 add what they need behind the
  same interface.
- `update-issue-with-plan.sh`: it edits the Issue on GitHub; left to the
  human.

## Steps

1. `pbc.mechanics.oscillator` and `pbc.mechanics.integrators` with unit
   tests. Done.
2. Lessons M4 and M5. Done.
3. Reference rows, docs. Done.
4. `./scripts/verify.sh`; evidence below.

## Verification evidence

2026-10-07, macOS (Darwin 24.6) on Apple M1 Max, working tree on base
`406d834` (uncommitted; `finish-feature.sh` creates the commit).

`./scripts/verify.sh`: **Verification passed**, 14 of 14 checks `PASS`. The
workflow self-tests were reported as `SKIP`: no workflow file differs from
`origin/main`. A first run before it failed three tests of `site-checks`,
all fixed (see "Discoveries"): the apostrophe in an outside prerequisite of
M5 (two learning-path checks), and the summary table of M5 at phone width
(the sideways-scroll check). No file changed after the passing run except
this plan.

| Check | Result |
|---|---|
| `unit-tests` | 136 passed, 4.0 s (27 of them in the two new test files) |
| `lean-build` | passed; axiom audit of 1 declaration |
| `check-tests` | 189 passed, 170 s |
| `lesson-checks` | 7 passed, 1.8 s |
| `site-build` | 9 pages, including both new lessons |
| `site-checks` | 54 passed, 88 s |
| `determinism` | two builds byte-identical, 43 files |

A single `quarto render` of each new page in this environment, measured
separately: M4 about 8 s, M5 about 8 s, including Quarto's start-up.

After the review round 1 fixes (M1, MIN1, MIN2; same day, same machine):
`./scripts/verify.sh` **Verification passed**, 14 of 14 checks `PASS`,
workflow self-tests `SKIP` as before. `unit-tests` 136 passed, `check-tests`
189 passed in 168 s, `lesson-checks` 7 passed, `site-checks` 54 passed in
85 s, `determinism` byte-identical. The regenerated rows of M5 (accuracy
table, cost table, equal-cost table) and the exact-maxima row of M4 are the
ones now pinned in `REFERENCE_ROWS`.

Per criterion:

| # | Evidence | State |
|---|---|---|
| 1 | Both lessons pass `lesson-checks` and every test of `tests/e2e` (sections, header and path page, excerpts identical to source, every cell executed, accessibility scan, widths, readable without JavaScript, the pinned rows of `REFERENCE_ROWS`). `test_reproduce_commands_regenerate_the_page_within_the_time_budget` regenerates each page byte for byte and asserts the render under 30 s | built and checked; publication needs the merge |
| 2 | `tests/unit/test_integrators.py::test_the_higher_order_integrators_show_their_order_on_the_oscillator` (symplectic Euler, Verlet, RK4 within 0.1 of 1, 2, 4), `::test_explicit_euler_shows_first_order_once_the_step_is_small_enough` (within 0.05 of 1) | met |
| 3 | M4, "The energy, step by step": every one of 192 ratios equals `euler_energy_growth` to 4.4e-16; the derivation is in the explanation and the factor stated as 1 + ω² Δt². `tests/unit/test_oscillator.py::test_explicit_euler_multiplies_the_energy_by_the_same_factor_every_step` (1e-12, four step sizes) | met |
| 4 | M5 worked examples: accuracy table with observed orders and log-log figure; energy over twenty periods in four panels with every per-step factor and modified energy checked on the same runs, and a thousand-period run; calls needed for a millimetre, predicted from the order and confirmed. Every number is cell output or an inline expression; the figures are drawn by cells | met; the reviewer judges the physics |
| 5 | The "Assumptions" section of each lesson: six numbered assumptions in M4 and six in M5, each with what breaks. M4 has three exercises, M5 three, each with a `.solution` whose numbers are cell output or inline expressions | met |

Not done by the implementer: `update-issue-with-plan.sh 18 <plan>`, which
edits the Issue on GitHub, and the Linux run, which is the CI run of the
pull request (it also asserts the pinned rows of `REFERENCE_ROWS`, produced
on macOS).
