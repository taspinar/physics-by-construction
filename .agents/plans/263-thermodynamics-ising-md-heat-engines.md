# Plan: Issue #263, F75 — Thermodynamics: Ising model, molecular dynamics, heat engines (T4, T5, T9)

- Issue: #263 (source: `docs/roadmap.md`, F75)
- Branch: `feature/263-thermodynamics-ising-model-molecular`
- Base commit: `3e21eb3`
- Risk: Level 2 (Medium): three new lessons, their code under
  `src/pbc/thermodynamics/`, and tests; no published claim changes
- Governing documents: `docs/architecture.md` (lesson model),
  `docs/authoring.md` (format 2, the experiment of a lesson), ADR 013 (slots),
  ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64 delivered; F113 read as the owner's interim full-run
  gate, since 2026-10-21 up to 64 lessons (#253). The site has 45 lessons; 48
  after this feature.

## Design

Three lessons in the `thermodynamics` strand at the next free orders, one slot
each. The strand order (4, 5, 6) is the address order; the course view orders
by the curriculum file, where T6 stays planned between T5 and T9.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `ising-model-and-phase-transitions` (order 4) | T4 | `ising.py`: energy and magnetisation of a periodic square lattice, a checkerboard Metropolis sweep over a batch of lattices, the exact enumeration of a small lattice, Onsager's critical temperature and spontaneous magnetisation, the Binder cumulant and the crossing of two cumulant curves | the sampler against the exact enumeration of a 4 x 4 lattice (energy and magnetisation within four standard errors at three temperatures); the magnetisation against Onsager's curve below Tc, with its finite-size rounding near and above Tc shown; Tc estimated from the crossings of the Binder cumulants of L = 4, 8, 16 (moments pooled over twelve runs, straight lines fitted near Tc, jackknife errors) and compared with 2 / ln(1 + sqrt 2), the finite-size shift stated; the susceptibility peaks of L = 8, 16, 32 as a second view of the shift |
| `molecular-dynamics` (order 5) | T5 | `molecular.py`: the shifted-force Lennard-Jones pair potential, forces, energy, and virial with the minimum image in a periodic square box, velocity Verlet, the kinetic temperature per species, the virial pressure | energy conservation: the fluctuation of the total energy scales as dt^2 (measured order) and has no secular drift at the chosen step; equipartition: a two-mass mixture started with unequal temperatures relaxes to equal kinetic temperatures per species and per component within four standard errors over twelve independent runs; the virial pressure against the ideal gas at the same density and temperature (reported, not a check) |
| `heat-engines-and-thermodynamic-cycles` (order 6) | T9 | `cycles.py`: ideal-gas legs (isotherm, adiabat, isochore, isobar) as sampled p-V-T paths, work as the integral of p dV and heat as the integral of T dS along a path, the Carnot, Otto, Stirling (with and without an ideal regenerator), and Brayton cycles, efficiency, and the entropy given to two reservoirs | the first law per leg and per cycle (Q - W - dU vanishing at second order in the path step); the Carnot efficiency against 1 - Tc/Th and the Otto efficiency against 1 - r^(1 - gamma); every cycle between the same extreme temperatures at or below the Carnot bound, with the entropy given to the two reservoirs non-negative and zero only for Carnot and the regenerated Stirling cycle |

Units: the Ising lesson in units of J and k_B; the molecular-dynamics lesson
in Lennard-Jones reduced units (sigma, epsilon, the lighter mass); the heat
engines in SI (one mole of a diatomic ideal gas, gamma = 7/5).

## Decisions

| Decision | Reason |
|---|---|
| Metropolis with a checkerboard update, vectorised over a batch of lattices (temperatures times independent replicas) | The algorithm a reader meets first; fast enough in NumPy for L up to 32 within the 30 s page budget. Critical slowing down is a stated limit, not hidden |
| Standard errors from independent replicas, never from correlated sweeps of one chain | As in T1 to T3; the replicas are independent by construction |
| Tc from the crossing of Binder cumulants, not from the peak of a response | The crossing needs no critical exponent; the shift of the peaks with L is shown as the finite-size caveat |
| Binder crossings from L = 4, 8, 16, not 32 (discovered in implementation) | With Metropolis, L = 32 near Tc does not equilibrate well enough within the page budget (its crossing scattered by more than its jackknife error between seeds); L = 32 stays in the magnetisation curve. The crossings lie below Tc by a finite-size shift larger than their error (4/8 about -1.5 %, 8/16 about -0.5 %), which the lesson states instead of extrapolating |
| Cumulants from moments pooled over runs | The mean of per-run cumulants is a biased ratio estimator |
| One uniform draw per site and sweep in the checkerboard sweep | A third faster, needed for the page budget; checked unbiased against the exact 4 x 4 averages to 2e-4 |
| Kinetic temperature with the centre-of-mass share 1 - m_i / M | With zero total momentum the species would otherwise differ by order 1 / N |
| Shifted-force Lennard-Jones potential | Force and energy continuous at the cut-off, so the energy error of velocity Verlet is the integrator's, of order dt^2, and not a cut-off artefact |
| Equipartition checked on a two-mass mixture started out of equilibrium | Equal temperatures of species with a mass ratio of four are a consequence of the dynamics, not of the initial draw |
| Heat as the integral of T dS, work as the integral of p dV, both by the trapezoidal rule along the sampled path | The first law is then a check between two independent integrals and the state function U, not an identity built into the code |
| No reference register entries (`go-deeper`) | Optional; the lessons are complete without them |
| No change to the architecture, ADRs, CI, or the curriculum file | The lessons fit format 2 and their slots exist. The package layout line of `docs/architecture.md` (a protected path) still names only F70's models of `thermodynamics/`; adding `ising`, `molecular`, and `cycles` there is left to a change the owner approves |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
alt text without computed values:

- T4: `fig-ising-magnetisation` (preview; |m| against T for three sizes, with
  Onsager's curve as the reference), `fig-binder-crossing` (the cumulants of
  three sizes, the exact Tc marked).
- T5: `fig-energy-drift` (energy change against time for three steps, and
  the fluctuation against the step log-log with a slope-two reference),
  `fig-equipartition` (preview; kinetic temperature of the two species
  against time, relaxing to one value).
- T9: `fig-cycles-pv` (preview; log-log p-V diagrams of the Carnot, Otto, and
  Stirling cycles, one panel each, with the two reservoir isotherms), `fig-otto-against-carnot` (Otto efficiency
  and work against compression ratio, with the Carnot bound).

Scientific validation: each figure shows quantities that a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_thermodynamics.py`: each new component against a closed
  form or a limit.
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/unit/test_curriculum.py` if it lists the published slots.
- `tests/lessons`, the single-page render of the three lessons.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
