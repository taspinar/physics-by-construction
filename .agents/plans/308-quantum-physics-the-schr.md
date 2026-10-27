# Plan: Issue #308, F89 — Quantum physics: the Schrödinger equation, tunnelling, the harmonic oscillator

- Issue: #308 (source: `docs/roadmap.md`, F89)
- Branch: `feature/308-quantum-physics-the-schr`
- Base commit: `cd92121`
- Risk: Medium (physics content; first lesson feature of a course), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

The first lesson feature of the `quantum` course: it creates the strand
directory `site/lessons/quantum/` and the package `src/pbc/quantum/`. Three
lessons, one slot each, built to the experiment contract (one module per
lesson under `src/pbc/quantum/experiments/`, one `draw_` function per
figure, a unit test per experiment). The finite differences are those of W1
(`wave-equation`), which is Q1's prerequisite.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `schrodinger-equation` (order 1) | Q1 | `schrodinger.py`: the finite-difference Hamiltonian, Crank-Nicolson and explicit Euler steps, the norm and moments, the Gaussian packet and its exact free evolution, the dispersion of the grid and of the scheme | the norm kept to round-off by Crank-Nicolson, and gained by explicit Euler at the rate its spectrum predicts; the centre and width of a free packet against the closed form; the whole wave function converging to the exact one at order two; the frequency of each grid mode against the closed form of the scheme, and against the free-particle dispersion omega = hbar k^2 / 2m |
| `quantum-tunnelling` (order 2) | Q2 | `barrier.py`: the closed-form transmission of a rectangular barrier, the stationary scattering problem integrated by the classical fourth-order Runge-Kutta method from the transmitted side, the barrier on a grid as its cell average, the transmitted probability of a packet | T and R against the energy, below and above the barrier, against the closed form; Runge-Kutta converging at order four; the thick-barrier law; R + T = 1; the transmitted probability of a time-dependent packet (Q1's solver) against T averaged over the packet's momenta |
| `quantum-harmonic-oscillator` (order 3) | Q3 | `eigenstates.py`: the lowest eigenpairs of the finite-difference Hamiltonian (tridiagonal), the Hermite functions, the oscillator spectrum, the predicted leading error -(h^2/32)(2n^2 + 2n + 1) | the eigenvalues converging to (n + 1/2) hbar omega at order two with the predicted coefficient; the eigenfunctions against the Hermite functions; the box that is too small raising the levels |

Units: hbar = m = 1 for Q1 and Q3 (stated as assumptions); eV, nm, and fs
for an electron in Q2 (`scipy.constants`, CODATA). QuTiP is not used: it is
an optional comparator only, and nothing here needs it (stated in Q1's
limits).

## Decisions

| Decision | Reason |
|---|---|
| Crank-Nicolson in time, the three-point Laplacian in space, walls at the ends | A Cayley transform of a Hermitian matrix: unitary, so the norm is kept exactly up to round-off; the same centred differences as W1 |
| Explicit Euler as the counter-example | Its amplification 1 - i dt E has modulus above one for every mode; the norm growth is predicted from the discrete spectrum |
| The exact free packet checked in the unit tests against an FFT propagation | The closed form is not trusted by itself; the FFT applies the exact free propagator independently |
| The transmission computed by fixed-step Runge-Kutta across the barrier from the transmitted side, not by a transfer matrix | A transfer matrix of a rectangle is the closed form itself; Runge-Kutta is a different method with its own order (four), takes any smooth shape on the barrier, and steps exactly onto its edges (Numerov was the first plan; it was not used because the edges of a rectangle are jumps of the potential, where its fourth order is not assured without special treatment) |
| The barrier of the packet run placed on the grid as the mean of the potential over each cell | Sampling V0 on the nodes in [0, a] gives the grid a barrier of another width, and the transmitted probability was off by 5 to 10 per cent; the cell average makes it exact to second order |
| The packet-on-a-barrier check uses T averaged over the momentum distribution | A packet is not a single energy; the comparison is between two independent computations of the same probability |
| Orders fitted with `pbc.verification.estimates.fitted_order` | The shared estimate, not a copy per course |
| No change to the architecture, ADRs, the curriculum file, the atlas, or CI | Slots Q1 to Q3 and the atlas concepts exist; the course tests derive the planned courses from the sources |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; reference slopes labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- Q1: the packet at several times against the exact one (preview), the
  convergence of the wave function, the dispersion of the grid and the scheme.
- Q2: T and R against energy with the Runge-Kutta points (preview), T
  against the width with the thick-barrier law, the packet at a barrier.
- Q3: the levels and eigenfunctions in the potential (preview), the
  convergence of the eigenvalues with the predicted error.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_quantum.py`: each function against a closed form, a limit, or an independent computation.
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes
  what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the three lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
