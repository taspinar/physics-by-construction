# Plan: Issue #328, F94 — Materials physics: crystal lattices and phonons, electronic band structure (MAT1, MAT2)

- Issue: #328 (source: `docs/roadmap.md`, F94)
- Branch: `feature/328-materials-physics-crystal-lattices`
- Base commit: `c8bf632`
- Risk: Medium (physics content; first lesson feature of a course), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

The first lesson feature of the `materials` course: it creates the strand
directory `site/lessons/materials/` and the package `src/pbc/materials/`.
Two lessons, one slot each, built to the experiment contract (one module
per lesson under `src/pbc/materials/experiments/`, one `draw_` function per
figure, a unit test per experiment). The course, its slots, and its atlas
concepts (`crystal-lattices-and-phonons`, `electronic-bands`) exist; the
course wiring (`pbc.authoring.path`, the atlas glyph) exists.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `crystal-lattices-and-phonons` (order 1) | MAT1 | `phonons.py`: the force-constant matrix of a ring of cells built spring by spring, the normal-mode frequencies of the ring (the eigenvalues of the mass-weighted matrix), the closed-form dispersion of the monatomic and the diatomic chain, the allowed wavenumbers of a ring, the long-wavelength sound speeds and the zone-boundary frequencies, a velocity-Verlet integration of the chain, a Gaussian wave packet on a branch and its energy-weighted centre | the ring's frequencies against the closed forms at its allowed wavenumbers (monatomic and diatomic); the sound speed and the edges of the gap against their limits; a wave packet integrated in time moving at the closed-form group velocity, not the phase velocity |
| `electronic-band-structure` (order 2) | MAT2 | `bands.py`: the tight-binding Hamiltonian of a ring with one or two sites per cell, its eigenvalues, the closed-form bands of both, the counting function of the one-band chain, the effective mass at the band bottom, the filling of the bands with electrons (the Fermi level, the gap at the Fermi level), the exact propagation of a state on an open chain with a uniform force (eigendecomposition) and its centre | the ring's energies against the closed-form bands; the counting function against its closed form to within one state; the effective mass against hbar^2/(2 t a^2); the gap 2 Delta at the zone boundary and its closing at Delta = 0; half filling metal against filled-band insulator; the Bloch oscillation of a packet against the closed form of its centre, with the period 2 pi hbar/(F a) |

Units: MAT1 K = m = a = 1 (frequencies in units of sqrt(K/m), wavenumbers in
units of 1/a); MAT2 hbar = a = 1 with the hopping t = 1 (energies in units
of t, times in units of hbar/t). Both stated on the page and on the axes.
The references are closed forms derived on the page from the model of the
page and an independent time integration; no materials package.

## Decisions

| Decision | Reason |
|---|---|
| The ring's matrix is built spring by spring (hopping by hopping) in real space, not from the closed form | The closed form is then an independent reference: the eigenvalues of the real-space matrix agree with it only if the Bloch argument on the page is right |
| Ring (periodic) boundary conditions for the dispersion | The allowed wavenumbers are exactly 2 pi n/(N a), so every eigenvalue has a closed-form partner; free ends would add surface modes |
| The comparison is set against set: the sorted eigenvalues against the sorted closed-form values at the allowed wavenumbers | It needs no assignment of a wavenumber to an eigenvector; the figure assigns them by projection on plane waves for display only |
| The wave packet is integrated by velocity Verlet, with a time step whose own dispersion error is far below the measured gap | An independent dynamic check of the group velocity; the integrator's frequency error (omega dt)^2/24 relative is stated |
| The Bloch oscillation is propagated exactly by the eigendecomposition of the open chain, and the centre is compared with the closed form x0 + (2t/F)(Re<T> - Re(<T> e^{-i omega_B t})), <T> the expectation of the one-cell translation in the initial state | The form follows from the conservation of the energy and the shift of every wavenumber by F t/hbar; it is exact for an infinite chain, so the remaining gap measures the ends of the open chain only, and the packet is kept far from them |
| No change to the architecture, ADRs, the curriculum file, the atlas, the glossary, or CI | The slots, the course, the atlas concepts, and the glossary terms exist |
| `tests/unit/test_curriculum.py` is not changed | With this feature no course is without a lesson; the test already expects no sentence then |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; reference curves labelled, not fitted; alt text without
computed values. Accessible fallback: the alt text, and the tables that
carry the same numbers.

- MAT1: the diatomic dispersion with the ring's frequencies on the
  closed-form branches (preview), the monatomic dispersion with the sound
  line, the wave packet's centre against time with the group-velocity and
  phase-velocity lines.
- MAT2: the two-site bands with the ring's energies on the closed form,
  the filled and the empty levels of one electron per site, and the bands
  without a gap (preview); the counting function against its closed form;
  the centre of a Bloch-oscillating packet against the closed form and the
  free particle of the effective mass.

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_materials.py`: each function against a closed form, a limit, or an independent computation.
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes
  what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the two lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
