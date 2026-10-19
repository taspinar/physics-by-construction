# Plan: F67 — Symbolic regression and equation discovery (Issue #190)

- Issue: #190 (source: `docs/roadmap.md`, F67); lesson list D7, D8 (two
  lessons) and the scientific conditions approved by the owner on
  2026-10-15 (comment on the Issue).
- Branch: `feature/190-symbolic-regression`; base `71fa0d2` (F117 and F66
  are merged, so the lessons are built to the F117 experiment contract
  from the start; the Issue's sequencing condition is met).
- Written by the implementer: no plan existed when the feature started.

## Design

Three format 2 lessons in `agents-llm` with `course: mechanics` and
`methods: [simulation]`: no agent is used, so no replay fixture, no live
run, and the last section is "Run this experiment". The lesson count goes
from 38 to 41, within the interim full-run gate of 45.

| Dir | Id | Slot | Content |
|---|---|---|---|
| `08-symbolic-regression` | `symbolic-regression` | D7 | The period of a simulated pendulum (RK4 of `pbc.mechanics.pendulum`) over length, gravity, mass, and amplitude; an exhaustive search over power laws (the grammar); recovery of $T = 2\pi\sqrt{L/g}$ within tolerance on clean data; held-out lengths and amplitudes; identifiability (gravity not varied: a family of tied forms; dimensional analysis as the prior that removes it); noise sweep over seeds with the level where the right form stops being chosen, explained by the standard error of an exponent against the spacing of the grammar |
| `09-discovering-differential-equations` | `discovering-differential-equations` | D8 | A damped oscillator simulated from several initial conditions; derivatives by central differences; a polynomial library in $(x, v)$; sequentially thresholded least squares; recovery of $\dot x = v$, $\dot v = -\omega^2 x - 2\gamma v$ within tolerance; held-out initial condition integrated with the recovered equation; identifiability: one orbit of the undamped oscillator makes the library rank-deficient (energy conservation ties $1$, $x^2$, $v^2$), several orbits remove it; the pendulum at small amplitude cannot tell $\sin x$ from $x - x^3/6$ |
| `10-equations-from-noisy-trajectories` | `equations-from-noisy-trajectories` | none (D8, second lesson) | Noise amplification of finite differences ($\sigma/\Delta t$ against truncation $\Delta t^2$); central differences against Savitzky–Golay smoothing on the same seeded noisy trajectories; recovery against noise level over seeds for both; where each fails and why (variance of the derivative, bias of the smoothing window, errors in the library columns); failure reported as a result |

A slot is filled by at most one lesson (ADR 013; `_slot_problems`), so the
second D8 lesson has no slot: it appears in the mechanics course view and
the simulation method view, and the D8 lesson links it under `related`.

- **Module `pbc.discovery.symbolic`**: power-law grammar, the fit of the
  constant of every form, the chi-square consistency rule of
  `pbc.discovery.baselines.consistent`, the Pareto front of complexity
  against chi-square, and selection of the simplest consistent form with a
  report of ties (forms the data cannot tell apart).
- **Module `pbc.discovery.equations`**: central differences,
  Savitzky–Golay derivatives (`scipy.signal.savgol_filter`, SciPy is
  already locked), the polynomial library, sequentially thresholded least
  squares with column scaling, the singular values of the library as the
  identifiability measure, and the integration of a recovered equation.
- **Experiments** `pbc.mechanics.experiments.symbolic_regression`,
  `discovering_differential_equations`, `equations_from_noisy_trajectories`
  with their unit tests; unit tests of both modules against known answers.
- **No library is locked.** PySINDy, PySR and the like are not added; the
  methods are short and pure NumPy/SciPy. The criterion on a locked
  library's licence is therefore not applicable, and
  `docs/discovery-protocol.md` says so.

## Scientific conditions of the owner

- Identifiability: D7 (tied exponents when a variable is not varied;
  the small-angle law vs the amplitude dependence), D8 (rank-deficient
  library on one orbit; $\sin x$ against its expansion).
- Noise: D8 second lesson compares central differences with
  Savitzky–Golay smoothing; D7 sweeps the noise of the period.
- Failure as a result: seeded sweeps in D7 and the second D8 lesson report
  the level at which each method fails, and why; no tolerance is tuned to
  obtain a success.
- Claims: a recovered form is typed `numerically-verified` and scoped to
  the probed range and the held-out set; the pages say it is the law of
  the simulated data, not shown to be the physical law beyond them.

## Visual deliverables

Scientific figures only, no page layout, diagram, or animation.

Skills: pbc-scientific-visualization@a70b501

- D7: Pareto front (complexity against chi-square, log scale) with the
  chosen form marked; recovery rate against noise level. D8: recovered
  against true trajectory on the held-out initial condition; singular
  values of the library (one orbit against several). D8 second: derivative
  error against step (log-log, reference slopes), coefficient error against
  noise for both differentiators with the tolerance line.
- Validation: unit tests of the modules against closed forms (the exact
  pendulum period, the analytic derivative, the known coefficients) and
  the experiments' tests assert the science on the results.
- Fallback: alt text describing every figure; every number also in a
  result table or the prose.

## Steps

1. `pbc.discovery.symbolic`, `pbc.discovery.equations`, unit tests.
2. The three experiments with their tests.
3. The three lesson pages.
4. Docs: authoring "Discovery lessons" (the non-agent baselines of D7/D8),
   `docs/discovery-protocol.md` (baselines, no locked library),
   `docs/project-map.md`, the layout note in `docs/architecture.md`;
   curriculum test of the filled slots; glossary entries if needed.
5. Verification: `./scripts/verify.sh --base` (new lessons).

## Discoveries during the work

- **The search index exceeded its budget with these lessons.** `./scripts/verify.sh
  --base` on 2026-10-19 built `search.json` at 1,017,944 bytes against the
  then 1 MB budget of `docs/architecture.md` ("Budgets", built-site check F41).
  The owner resolved it in pull request #225 (merged into this branch): one
  budget of 3.5 MB for the planned curriculum, and the Learning path page is
  no longer indexed. This feature does not change the budget.
- **The singular values of one orbit.** An RK4 orbit of a linear equation
  makes the central-difference acceleration an exact linear function of the
  samples, so the training residual of the found equation is at round-off
  and is not shown.
