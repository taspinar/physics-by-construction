# Plan: Issue #290, F78 — Electromagnetism: Maxwell's equations and FDTD, RLC circuits, waveguides and antenna basics (EM4, EM5, EM6)

- Issue: #290 (source: `docs/roadmap.md`, F78)
- Branch: `feature/290-electromagnetism-maxwell-s-equations`
- Base commit: `30d179e`
- Risk: Level 2 (Medium) by its paths: three new lessons, three new modules
  of `src/pbc/electromagnetism/`, and tests; the scripts derive any trigger
  the diff hits
- Governing documents: `docs/architecture.md` (lesson model),
  `docs/authoring.md` (format 2, the experiment of a lesson), ADR 013
  (slots), ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels)
- Written by the implementer: no plan existed when the feature started.
- Gates: F61, F62, F64, F72, F71 delivered; F113 read as the owner's interim
  full-run gate, since 2026-10-24 up to 110 lessons (#281). The site has 53
  lesson pages; 56 after this feature.

## Design

Three lessons in the `electromagnetism` strand at the next free orders, one
slot each (the placement rule). NumPy and SciPy only; SI units throughout.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `maxwells-equations-and-fdtd` (order 4) | EM4 | `pbc.electromagnetism.fdtd`: the one-dimensional Yee scheme (E_z, H_y staggered in space and time) with a relative permittivity per node and perfectly conducting ends; the two-dimensional TM_z Yee scheme between perfectly conducting walls with an optional conductivity profile; the numerical dispersion relation, its group velocity, the stability limit of a grid, the amplification of the highest mode beyond it, the discrete divergence of H | the speed of a modulated pulse in vacuum and in a dielectric against c / n and against the group velocity of the numerical dispersion relation, the gap to c falling at order two in dx; the reflected and transmitted amplitudes at a dielectric interface and at a conductor against the Fresnel coefficients at normal incidence, with the energy balance; the stability limit in one and two dimensions shown by runs just below (bounded) and just above (growing at the predicted amplification of the highest mode); div H kept at round-off by the 2D scheme |
| `rlc-circuits-and-resonance` (order 5) | EM5 | `pbc.electromagnetism.circuits`: the series RLC circuit (natural frequency, damping, Q, regime), its state equations integrated by `scipy.integrate.solve_ivp`, the closed-form step response in the three regimes, the complex impedance and the phasor current and capacitor voltage, the amplitude and phase of a simulated steady state by projection over whole periods; the peak and the half-power points searched on simulated steady states (in the experiment) | the simulated step response against the closed forms in the under-, critically and over-damped regimes; the resonance curve (current and phase) simulated in time against the analytic response V / |Z|, its peak at 1 / sqrt(LC), its half-power width against R / L and Q; the capacitor-voltage peak below the resonance at omega_0 sqrt(1 - 1 / (2 Q^2)); the energy lost per cycle against 2 pi / Q of the energy stored |
| `waveguides-and-antenna-basics` (order 6) | EM6 | `pbc.electromagnetism.waveguides`: cut-off frequencies of the TE_mn and TM_mn modes of a rectangular guide, guide wavenumber, phase and group velocity, evanescent attenuation, the cut-off frequencies of a cross-section from the sparse finite-difference eigenproblem (Dirichlet for TM, Neumann for TE); the 2D FDTD of EM4 as the width-length plane of the guide carrying the TE_10 field, with a graded absorbing end (in the experiment); `pbc.electromagnetism.antennas`: the far field of a wire with a given current by superposition of short elements, the analytic short and half-wave dipole patterns, directivity and radiation resistance by quadrature, pattern multiplication for two elements | the cut-off frequencies of the lowest modes of a WR-90 cross-section from the eigenproblem against the closed form, the error falling at order two; in the FDTD guide, the measured wavenumber above cut-off against the guide dispersion relation (continuum and grid), and the measured decay below cut-off against the evanescent attenuation; the element pattern of a half-wave and a short wire from superposition against the analytic dipole patterns, directivity against 1.64 and 1.5, the radiation resistance of the half-wave dipole against about 73 ohm; two elements: direct superposition against element pattern times array factor |

## Decisions

| Decision | Reason |
|---|---|
| Three modules for EM4 to EM6 (`fdtd`, `circuits`, `waveguides`, `antennas`) in the existing package `src/pbc/electromagnetism/` | The package exists (F72); EM9 reuses `antennas` |
| Yee scheme written out in NumPy, 1D and 2D TM_z only | Transparent and fast; 3D and the TE_z polarisation add nothing the criteria ask for |
| Wave speed from the centroid of the energy of a modulated pulse, checked against the group velocity of the numerical dispersion relation | The pulse moves at the group velocity; the scheme's own relation predicts it exactly, the continuum c within the dispersion error |
| Dielectric interface at an E node with the mean permittivity | Second-order placement of the interface; the Fresnel coefficients are then met to the dispersion error |
| Stability shown, not bisected: runs at 0.99 and 1.01 of the limit of the grid, the growth beyond compared with the amplification of the highest mode from the dispersion relation | The criterion asks for the limit shown; the growth rate is a quantitative check of where it lies. The unit test builds the step as a matrix and checks the limit and the growth against its eigenvalues |
| In `Line`, H is stored half a step *earlier* than E (discovered in implementation) | `step` advances H first; a pulse launched with H half a step later split into two |
| The reflection measured with a Gaussian pulse without a carrier, from the largest field on each side; the conductor as a line that ends at the interface | The extremum of a pulse without a carrier does not depend on the carrier's phase; a line's own end is a perfect conductor |
| RLC time-domain response by `solve_ivp` (DOP853, tight tolerances) and the frequency response by the complex impedance | Two independent computations; the check is not a tautology |
| EM5 reuses no code of `pbc.mechanics.resonance` | The circuit lesson computes the response by impedance and phasors, the mechanics lesson by the closed form of the oscillator; the analogy is stated on the page |
| Waveguide transmission by the 2D FDTD of EM4 between two walls, which carries the TE_m0 fields of a rectangular guide exactly | Reuse of the solver of EM4; the guide's cut-off and dispersion are then measured in the time domain, independent of the eigenproblem |
| FDTD guide frequencies 8 to 12 GHz above and 3 to 5 GHz below the cut-off of 6.56 GHz, not closer (discovered in implementation) | Near the cut-off the transient lingers (small group velocity) and the graded absorber reflects more; at 6 and 7.5 GHz the fit missed the grid relation by about 2 % and 0.01 %. The page says why they are left out |
| Values set by an integrator's tolerance or by round-off shown as "below" a bound | `docs/authoring.md`, "Numbers": no digits that another machine would change |
| Antenna current assumed sinusoidal, not solved (no method of moments) | The analytic dipole patterns assume the same current, so the superposition is checked against them; the assumption is a stated limit |
| No reference register entries (`go-deeper`) | Optional; the lessons are complete without them |
| No change to the architecture, ADRs, CI, the curriculum file, or `site/atlas.yaml` | The lessons fit format 2, their slots exist and the atlas already places them; the package layout of `docs/architecture.md` names `electromagnetism/` without its modules |

## Visual deliverables

Scientific figures, each `simulated`, drawn by a `draw_` function from the
tested code, colours from `FIGURE_COLOURS` with line style or marker as well,
alt text without computed values:

- EM4: `fig-pulse-at-interface` (E against x at three times: incident,
  reflected and transmitted pulses, the dielectric shaded),
  `fig-fdtd-dispersion` (log-log gap of the measured speed to c against dx,
  reference slope two), `fig-fdtd-stability` (log of the largest field
  against step, just below and just above the limit, 1D and 2D),
  `fig-fdtd-plane` (preview; signed false-colour E_z of a pulse from a line
  source meeting a dielectric block, one colour bar centred on zero).
- EM5: `fig-step-response` (capacitor voltage against time in the three
  regimes, simulated against closed form), `fig-rlc-resonance`
  (preview; current amplitude and phase against frequency, simulated points
  on the analytic curve, half-power width marked).
- EM6: `fig-cutoff-convergence` (log-log error of the cut-off frequencies
  against grid spacing, reference slope two), `fig-guide-field` (preview;
  E_z in the guide above and below cut-off, false colour, with colour bar),
  `fig-guide-dispersion` (beta and alpha against frequency, FDTD markers on
  the continuum curves, cut-off marked), `fig-dipole-patterns` (polar
  patterns, superposition against analytic, short and half-wave; two-element
  pattern multiplication).

Scientific validation: each figure shows quantities that a check of the same
lesson asserts. Accessible fallback: the alt text and the result tables.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_fdtd.py`, `tests/unit/test_circuits.py`,
  `tests/unit/test_waveguides.py`: each component against a closed form or a
  limit.
- `tests/unit/test_<name>_experiment.py`, one per lesson.
- `tests/lessons`, the lesson source checks.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
