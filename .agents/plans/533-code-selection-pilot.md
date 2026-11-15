# Plan: F176, the code-selection pilot on MAT6, W7, FL2, SA5, and L1 (Issue #533)

Source: `docs/roadmap.md`, F176; `docs/changes/teaching-by-construction.md`,
sections 4, 11 (U1e, U1h, U1i), and 17; requirements decision 44; ADR 023
decisions 3, 4, and 7; the display forms of F175 (`docs/authoring.md`,
"Code"). Written by the implementer at the start of the work (the Issue
expects a short plan and none existed).

**Level 2.** Five lesson sources and this plan. No source module, test,
protected path, front matter, number, figure, caption, alt text, or claim
changes: only the `excerpt(...)` calls of the lessons' code blocks and the
sentences that introduce or read them. The Lean lesson is
`lean/01-proving-what-the-simulation-showed` (L1); its `lean_excerpt` and
`lean_evidence` calls are untouched, so every proof is shown as before.
The targeted run selects the five lessons.

## Visual deliverables

Lesson code display; no new figure, diagram, or animation (every figure is
the same file).

Skills: pbc-physics-teaching@7f34987

- **Artifact:** the code blocks of the five pages.
- **Scientific validation:** the experiments are untouched, so the values,
  tables, and figures are the same; the built-site excerpt check compares
  every selection part by part with the source, its omission markers and
  line numbers; the single-page render and reproduction of each lesson; the
  independent science review of each selection (criterion 5).
- **Accessible fallback:** no script; selections, omission markers, and the
  Source links are text (F175).

## Rules applied to every block

- A block is shown when it carries the physics or the processing the
  conclusion rests on; its purpose is recorded below (the skill, section 7).
- A `draw_*` function is read before it is linked. Lines that compute a
  residual, a smoothing, a scaling, a model curve, or a selection of data the
  figure depends on stay visible as an exact selection (ADR 023 decision 3);
  the rest is plot layout and becomes a `source_link(f, figure=True)` after
  the figure (one action to the whole function at the built commit).
- No computation moves between functions, and no source line changes.
- Positive examples, unchanged: T11 (`thermodynamics/11-brownian-motion-tracking`)
  and AST8 (`astrophysics/09-exoplanet-light-curves`) keep analysis and
  drawing apart, so their drawing functions hold no transformation; they are
  cited, not edited.

## MAT6, `materials/05-stress-strain-measurements`

| Block | Purpose | Decision |
|---|---|---|
| `stress_strain.hooke_stress` | The model line with an intercept | Exact full, unchanged |
| `stress_strain.offset_crossing` | The construction of the offset yield: the gap to the shifted line, the guard that skips the foot, the linear interpolation | Generated signature + exact selection of lines 15 to 21 (`gap = ...` through the return, the guard included); the prose says what `e` and `s` are (the input arrays as floats) and what the docstring says |
| `elastic_unloading`, `closed_loop_work`, region `choices` | Model and integral; the lab's choices | Exact, unchanged |
| `ellipse_check`, `landmarks`, `fit_modulus`, `newey_west_slope_error`, `sensitivity`, `offset_yields`, `unloading`, `loop`, `true_stress_strain`, exercises | Validation and analysis | Exact, unchanged |
| `draw_stress_strain` | None. Dependency check: plots the three segments of `segments(test)`, shades the rows of the loop (`loop`, shown), marks three landmarks (`landmarks`, shown); no computation | Figure source link |
| `draw_elastic_regime` | The residuals against both lines and the 0.2 % offset line, from which the end of the elastic regime is read | Exact selection: lines 5 to 8 (the data, grid, fitted values), 27 to 28 and 37 to 38 (the fitted and the model line with their display limits; owner's correction of 2026-11-15), 47 to 48 (the shifted line and its display limits), 65 to 69 and 76 to 78 (the two residuals); layout omitted; Source link to the whole |
| `draw_unloading` | None. Dependency check: the elastic line is `elastic_unloading` (shown); the lower panel is `behind_elastic` | Figure source link; `behind_elastic` (the inelastic strain the panel plots, an analysis function) shown exact full in its place |

## W7, `waves/09-lycopodium-diffraction-lab`

| Block | Purpose | Decision |
|---|---|---|
| `halo.*`, `lycopodium.centre`, `lycopodium.dark_ring`, exercises | Model and the ring analysis | Exact, unchanged |
| `draw_diameters` | None. Dependency check: histograms of `whole_spores` (the cut the prose and the table state) in fixed bins; the numbers of the claim come from the diameter table | Figure source link; the prose names the cut and the density histogram |
| `draw_halo_model` | None. Dependency check: evaluates `halo.halo` (shown) for one disk and for the diameters; markers at the minima of the table | Figure source link |
| `draw_profiles` | None. Dependency check: the profiles minus `centre` (shown), the ring and its range from the ring table | Figure source link |
| `draw_scaling` | The scaling test: the fold with its processed status, the moving average of the analysis, radius over wavelength, the ratio, and its residual against the prediction | Exact selection: lines 12 to 31, 37, 45 to 46, 72 to 74; layout omitted |

## FL2, `fluids/05-navier-stokes-fundamentals`

| Block | Purpose | Decision |
|---|---|---|
| `divergence`, `advection`, `solve_poisson`, `project`, `step`, `pressure` | The projection stages and the solver | Exact, unchanged |
| Regions, `projection_example`, `solve_manufactured`, `budget_history`, runs | Examples | Exact, unchanged |
| `draw_projection` | None. Dependency check: colours the `divergence` (shown) of each field on the diverging map `PuOr` limited symmetrically by the largest divergence before; arrows are the face velocities averaged to the centres | Figure source link; the prose states the false colour, the diverging scale centred on zero, and the averaging; figure unchanged |
| `draw_energy_budget` | The budget the figure reads: start minus dissipated, and the relative difference | Exact selection: lines 8 to 9 and 26 to 28 |

## SA5, `agents-llm/01-an-agent-runs-an-experiment`

| Block | Purpose | Decision |
|---|---|---|
| `ModelClient`, `Tool`, `Allowlist`, `run`, `load_client`, `replay` | The trust boundary: validation of every call, the loop that only runs what passes | Exact full, unchanged |
| `misbehaving_calls`, `run` region `replay`, `rough_ball`, `agent_conclusion`, exercises | The attacks and the replay check | Exact, unchanged |
| `draw_tool_flow`, `draw_replay_check` | None. Dependency check: boxes and arrows, computes nothing (status conceptual) | Figure source link |
| `draw_agent_evidence` | The evidence: the independent scan and the agent's accepted calls at the fine step | Exact selection lines 1 to 15 without the docstring; layout omitted |

## L1, `lean/01-proving-what-the-simulation-showed`

| Block | Purpose | Decision |
|---|---|---|
| Every `lean_excerpt` | Formal proof | Unchanged |
| Regions, `shown`, `exact_residual`, `euler_residual`, `energy_factor`, exercise code | The checks against the theorems | Exact, unchanged |
| `draw_theorem_pipeline` | None. Dependency check: boxes and brackets, computes nothing | Figure source link |
| `draw_proved_energy_growth` | The simulation and the theorem's factor at three steps | Exact selection lines 4 to 9; layout omitted |

## Steps

1. The five lessons: the calls above; the sentences that introduce a
   selection or read a figure where a listing was.
2. Before and after: single-page renders of the five pages, screenshots of
   each changed block at 1280 px in the handoff folder 533-screenshots
   (criterion 4), Git-ignored.
3. The independent science review (criterion 5) and the owner's review of
   MAT6's elastic-regime figure and its source navigation are later gates.
4. `./scripts/verify.sh --targeted`, last.
