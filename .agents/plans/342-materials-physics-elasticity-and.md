# Plan: Issue #342, F95 — Materials physics: elasticity and deformation, defects (MAT3, MAT4)

- Issue: #342 (source: `docs/roadmap.md`, F95)
- Branch: `feature/342-materials-physics-elasticity-and`
- Base commit: `715a297`
- Risk: Medium (physics content), Level 2
- Governing documents: `docs/architecture.md` (lesson model), `docs/authoring.md`, ADR 013, ADR 016 (the experiment of a lesson), ADR 019 (skills)
- Written by the implementer: no plan existed when the feature started.

## Design

Two lessons in the existing strand `site/lessons/materials/`, orders 3 and
4, one slot each, built to the experiment contract like MAT1 and MAT2 (one
module per lesson under `src/pbc/materials/experiments/`, one `draw_`
function per figure, a unit test per experiment). The slots, the atlas
concepts (`elasticity`, `defects-and-material-properties`), and the course
exist.

| Lesson | Slot | Code | Checks |
|---|---|---|---|
| `elasticity-and-deformation` (order 3) | MAT3 | `elasticity.py`: a bar loaded along its axis by its own weight and an end force, by linear elements (a chain of springs); a plate in plane stress with linear vector elements on a `pbc.fem` mesh (`gradients`, `edge_load`, `solve`, `residual` reused), Hooke's law, traction loads, a roller and a clamped support, the stress of every triangle | the bar's nodal displacements against the closed form of the loaded bar (exact at the nodes), the element stress exact at the element midpoints and off by q h / (2A) at its ends; the reaction against the load; the plate under uniform tension with a roller support against the closed form u_x = sigma x / E, u_y = -nu sigma y / E (the patch test, to round-off); the clamped plate: equilibrium of the reactions, Saint-Venant's decay of the disturbance away from the clamp on two meshes, and the stress at the clamped corner that grows with refinement (the limit of the model) |
| `defects-and-material-properties` (order 4) | MAT4 | `defects.py`: the free energy of n vacancies on N sites counted exactly and its minimum against the closed form; a continuous-time random walk of a vacancy on a square lattice with the Arrhenius hop rate; a vacancy moving through a periodic lattice of tagged atoms, the atoms' squared displacements | the exact minimum of the free energy within one vacancy of N e^(-E/kT) / (1 + e^(-E/kT)); the vacancy's diffusion coefficient against T1 (`pbc.thermodynamics.diffusion`: its mean squared displacement, its fit of D, and its prediction l^2 / (2 d tau)), and against T1's own walk with the same step and time; the Arrhenius fit of the migration energy; the tracer correlation factor of the vacancy mechanism against 1/(pi - 1), within three standard errors |

Units: MAT3 in SI (a steel bar and a steel plate, E = 200 GPa, nu = 0.3,
stated as illustrative). MAT4 in eV, K, nm, s with chosen illustrative
energies (formation 1.0 eV, migration 0.7 eV, attempt frequency 1e13 /s,
spacing 0.25 nm), not fitted to a material. No materials package.

## Decisions

| Decision | Reason |
|---|---|
| The plate elements are added to `pbc.materials.elasticity` on top of `pbc.fem`, not to `pbc.fem` | `pbc.fem` is the scalar solver of the thermodynamics lessons; the vector element reuses its mesh, gradients, edge load, and solver without changing it, so no thermodynamics page changes |
| The roller support (u_x = 0 on the left edge, u_y = 0 at one node) for the closed-form check | It removes the rigid motions and nothing more, so uniform tension is the exact solution and linear elements must reproduce it to round-off |
| The clamped support is shown as a measured contrast, not against a closed form | It has none; its checks are equilibrium (exact), agreement of two meshes away from the clamp, and the growth of the corner stress under refinement, stated as observed |
| T1's functions are imported and used for MAT4's diffusion coefficient | The criterion "checked against T1" is then literal: the same estimator and the same prediction |
| The tracer correlation is measured from the sum of the squared displacements of all atoms over the vacancy's jumps | Each jump moves one atom by a, so the sum equals the number of jumps times a^2 without correlation; the ratio is f, with no need to follow a single tracer |
| Monte Carlo results are compared within three standard errors, with fixed seeds | The comparison is statistical; the seed makes the page reproducible |
| No change to the architecture, ADRs, the curriculum file, the atlas, the glossary, `pbc.fem`, or CI | The slots, the course, and the atlas concepts exist |

## Visual deliverables

Scientific figures only, all `simulated`, drawn by `draw_` functions of the
experiments from the verified code; colours from `FIGURE_COLOURS` with line
style and marker; the false-colour map with a colour bar; reference curves
labelled, not fitted; alt text without computed values. Accessible
fallback: the alt text, and the tables that carry the same numbers.

- MAT3: the bar's displacement and stress against the closed form (four
  elements); the clamped and the roller plate, the stress sigma_xx in false
  colour on the deformed mesh, and the disturbance against the distance
  from the clamp on two meshes (preview).
- MAT4: the free energy of the vacancies, energy and entropy terms; the
  vacancy's mean squared displacement against T1's line; the Arrhenius
  plot of the vacancy's and the atoms' (vacancy-mediated) diffusion
  coefficients (preview).

Skills: pbc-scientific-visualization@a70b501

## Verification

- `tests/unit/test_materials.py`: each function against a closed form, a limit, or an independent computation.
- `tests/unit/test_<name>_experiment.py`, one per lesson: the command writes
  what the page shows, and the lesson's science holds on the written results.
- `tests/lessons`, the single-page render of the two lessons: the lesson rule.
- `./scripts/verify.sh --base` (new lessons change what other pages show).
