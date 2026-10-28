# Plan: Issue #311, F90 — Quantum physics: spin, entanglement and Bell inequalities, open systems

- Issue: #311 (source: `docs/roadmap.md`, F90)
- Branch: `feature/311-quantum-physics-spin-entanglement`
- Base commit: `604f151`
- Risk: Medium (physics content), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

Three lessons in the `quantum` strand after F89's Q1 to Q3, one slot each,
built to the experiment contract (one module per lesson under
`src/pbc/quantum/experiments/`, one `draw_` function per figure, a unit
test per experiment). Every random draw takes a fixed seed; a sampled value
is compared with its prediction in units of its standard error.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `spin-and-stern-gerlach` (order 4) | Q4 | `spin.py`: Pauli matrices, the state along a direction, projectors, the Born rule, a measurement with its collapse, magnets in a row, the deflection of the modelled magnet | the same sampled atoms as quantum spins (two spots at the predicted deflection) and as classical moments (a uniform band); the fraction +1 at thirteen analyser angles against cos^2(theta/2) in standard errors; z-z-z against z-x-z; the deflection against an independent integration of the trajectory (unit test) |
| `quantum-entanglement` (order 5) | Q5 | `bell.py`: the singlet and the Werner state, the joint probabilities, the correlation and its standard error from counts, sampling, a local hidden-variable model (sign of cos), the CHSH sum and its error, the sixteen deterministic strategies | correlations against -cos and the local straight line; **S computed from the sampled correlations at the standard settings and compared with the local bound 2 and Tsirelson's bound 2 sqrt(2)** in standard errors, for the singlet and the local model; the enumeration of the sixteen strategies (max abs S = 2); S along a family of settings |
| `open-quantum-systems` (order 6) | Q6 | `open_systems.py`: the Lindblad equation and its 4 x 4 generator, explicit Euler, classical Runge-Kutta, and exponential steps as matrices, the Choi matrix, purity, the partial trace, the qubit with decay and dephasing and its closed form, random phase kicks | Ramsey fringes of the exponential integrator against the closed form to round-off; **the trace and the positivity of rho, and the complete positivity of the step (Choi matrix), for the three integrators at a coarse and a very coarse step: only the exponential integrator keeps both at every step**; Euler order one, Runge-Kutta order four |

Units: SI for Q4's apparatus (CODATA electron moment, the standard atomic
weight of silver; given apparatus values, not the historical magnet);
dimensionless for Q5; hbar = 1 and the detuning as the unit of frequency
for Q6 (stated as assumptions).

## Decisions

| Decision | Reason |
|---|---|
| Unpolarised atoms drawn as spins in isotropic random directions, the same atoms for the quantum and the classical screen | One input, two physics: the mean moment agrees atom by atom, the distribution does not |
| Each CHSH setting pair sampled with its own pairs | As in an experiment; with shared hidden values the local model's S would be bounded sample by sample, which an experiment cannot do |
| The local bound shown by enumerating the sixteen deterministic strategies, not only by one model | One model reaching 2 is an example; the enumeration is the bound |
| The sampled S may lie a little above a bound it reaches in expectation; reported in standard errors, not hidden | Honest statistics; the significant figure is the distance from 2 |
| The integrators written as 4 x 4 matrices on the stacked rho | Trace preservation is then a one-line argument (identity plus powers of G), and the Choi matrix of a step decides complete positivity |
| The exponential step `scipy.linalg.expm` as "the integrator" that keeps trace and positivity | The exact semigroup of a Lindblad generator is completely positive and trace-preserving for any step; Euler and Runge-Kutta are shown losing positivity while keeping the trace |
| Shared code: `fitted_order` of `pbc.verification.estimates`; Q5 and Q6 reuse `spin.py`'s projectors and Pauli matrices; Q6 reuses `bell.py`'s singlet | No copies |
| No change to the architecture, ADRs, the curriculum file, the atlas, the glossary, the register, or CI | Slots Q4 to Q6 and the atlas concepts exist; the outside prerequisites use existing glossary terms; no reference is required |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; sampled values with one-standard-error bars; bounds and
reference slopes drawn as lines and labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- Q4: the screen, quantum against classical (preview); the sampled fractions on the Born curve.
- Q5: the correlations of both models against angle; abs S along the family with both bounds (preview).
- Q6: the fading Ramsey fringes against the closed form (preview); the Bloch-vector length of the three integrators; the convergence of Euler and Runge-Kutta.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_quantum_spin.py`: each function against a closed form, an enumeration, or an independent computation (the trajectory by `solve_ivp`, the Runge-Kutta step written stage by stage, `expm` of the generator, the transpose as a positive map that is not completely positive).
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the three lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
