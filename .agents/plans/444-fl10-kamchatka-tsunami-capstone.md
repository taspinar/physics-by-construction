# Plan: Issue #444, F88 phase 2 — Applied capstone: reconstructing the 2025 Kamchatka tsunami (FL10)

- Issue: #444 (source: `docs/roadmap.md`, F88); phase 1 (card
  `kamchatka-2025-tsunami-inputs`, dossier, samples, reference figure, `go`)
  is on `main` (`.agents/plans/444-fl10-tsunami-inputs-dossier.md`). Phase 2
  started by the owner's word of 2026-11-13 on the Issue.
- Branch: `feature/444-fl10-kamchatka-tsunami-capstone`; base commit `69afda9`.
- Written by the implementer: no phase 2 plan existed.
- Roadmap row checked (owner's rule of 2026-11-07): the block of F88 is
  present and not retired; `site/curriculum.yaml` lists the planned slot
  FL10 (kind "applied capstone"). The lesson fills it with `lesson.slot`;
  `site/curriculum.yaml` is not edited.
- Lesson order: fluids order **10** (supervisor, 2026-11-13: FL7, PR #503,
  takes order 9 and merges first; main is merged into this branch after
  that and before the full verification, since orders run without gaps,
  `src/pbc/authoring/path.py`).
- Risk: **Level 3** (owner's decision of 2026-11-13, option B). Publishing
  FL10 breaks two existing tests that pinned FL10 as a planned slot; they are
  rewritten once to derive their planned-slot example from
  `site/curriculum.yaml` and the lessons' front matter
  (`tests/support/slots.py`), independently of the code under test, so a
  later published slot does not break them again. Approval request
  `.agents/approvals/444.md`; the full `./scripts/verify.sh` is the final
  tier. Otherwise: one new lesson, a new model module
  `src/pbc/fluids/tsunami.py`, a new experiment module, one adapter in
  `src/pbc/data/adapters.py` (alphabetical position by dataset module), new
  tests. `shallow_water.py` and `finite_volume.py` are reused unchanged; no
  existing assertion, tolerance, budget, protected path, or published claim
  (FL5, FL9) changes. A new lesson changes the learning path: the
  verification tier is `--base`.
- Governing documents: `docs/architecture.md` ("Applied capstone and
  numerical-engineering lesson", "Measured-data lab"), `docs/authoring.md`
  ("Lesson format 2", "Measured data"), ADR 007, ADR 013, ADR 016, ADR 019,
  ADR 020; the capstone rule and the lab rule of `docs/roadmap.md`; the
  dossier `docs/datasets/kamchatka-2025-tsunami-inputs.md` and its card.

## Slicing decision

Both deliverables on one page, one pull request: the prototype shows that
the simulation core, the benchmarks, and the comparison fit the page budget
on the cropped grid (an 8′ run of two hours takes about 8 s; the 16′ and
32′ runs about 1 s and 0.3 s). If the render or the payload does not fit,
stop after part (1) and say so on the Issue.

## Learning outcomes

1. Turn the question "what does a long-wave model on a cropped grid say
   about the 2025 Kamchatka tsunami at two deep-ocean stations?" into a
   model with stated inputs, assumptions, a comparison metric fixed before
   the comparison, and a credibility boundary.
2. Extend the one-dimensional finite volumes and hydrostatic reconstruction
   of FL9 and FL5 to two dimensions on a sphere, with the pressure on faces
   of unequal length balanced, and second order by limited reconstruction.
3. Verify the model by still water, linear propagation against √(gh),
   conservation and the volume budget, positivity, the CFL limit, the
   boundaries, and grid convergence.
4. Compare the computed waves with the DART records through arrival time,
   peak height, and residuals with their uncertainties, and state what the
   comparison supports and what it does not.

## The model and its place

`src/pbc/fluids/tsunami.py`: the 2-D shallow-water equations on a plane or
latitude-longitude grid. `src/pbc/fluids/tsunami_benchmarks.py`: the exact
linear solutions (d'Alembert, the Hankel transform of a round hump), the
benchmark runs and the convergence figure, apart from the experiment so that
the lesson checks' name-based data analysis does not count the data-free
figure as a figure of the dataset (discovery during the work). Each face is the 1-D Riemann problem of FL5: the
mass and normal momentum from `shallow_water.hll_flux` (reused, unchanged),
the transverse momentum carried by the mass flux upstream; hydrostatic
reconstruction at each face (Audusse et al. 2004, as in FL5), second order
by limited slopes of h, η, u, v (first order where a neighbour is dry), Heun
in time; the limiter (minmod or monotonized central) chosen on the
plane-wave benchmark, not on the records: monotonized central, error 3.2
times smaller than minmod's on the finest grid; the north and south faces of a sphere's cell differ in length and
the source carries the pressure difference, so water at rest stays at rest.
Coriolis as a source; curvature terms of order u²/R left out. Open
boundaries by copying (transmissive, the FL5 equivalence and the plane
benchmark), or radiating against the sea at rest (`sea_level`: outgoing
Riemann invariant of the cell, incoming of water at rest), which every
Kamchatka run uses; walls by reflection. Discovery of 2026-11-13: with
copied ghost cells the 8′ base run drained about 1,700 km³ through the
west edge where it crosses the Kuril arc (a linear instability of the
boundary: in proportion to the source, independent of the Courant number,
the limiter and the order, absent with walls); the page states it as a
failure mode (budget section) and a test pins it. Volume and
outflow recorded each step (budget), the largest surface and the first
arrival above 1 cm per cell, gauges by bilinear interpolation. A source in
time: the bed and the surface of a cell rise by the uplift at its onset.
The FL5 interface is reused as the first-order special case: a one-row grid
at first order must give FL5's `well_balanced` + `finite_volume.evolve` to
round-off (test).

## Benchmarks and tolerances

| Benchmark | Case | Tolerance (test) |
|---|---|---|
| Still water | ETOPO bed on the sphere, rotating, 16′, 1 h | max \|η\|, \|u\| below 1e-9 m, m/s |
| Linear wave | plane Gaussian hump, flat 4000 m bed, 3 grids, against d'Alembert | second-order scheme: observed order ≥ 1.5; first order ≈ 1 |
| Speed | radial hump, arrival along axis and diagonal vs r/√(gh) | within 2 % |
| Conservation | closed basin (walls) and the Kamchatka run (open) | volume budget residual below 1e-12 relative |
| Positivity | every run | min depth ≥ 0 |
| CFL | flat-bed hump at Courant 0.4 to 1.2 | stable to 1.1, blow-up at 1.2; operating 0.8 (positivity checked on every run, not guaranteed by theory at that step) |
| Boundary | open 16′ base domain against a larger domain and against walls | difference in the windows reported against the signal |
| Grid | 32′, 16′, 8′ over the domain; 4′ on a smaller domain near 21416 for 45 min | arrival changes shrink; the crest does not converge (reported as such) |

## The source and its uncertainty

The USGS surface deformation (vertical, 40 × 40 grid, `us6000qw60_1` v5)
interpolated onto the cells, tapered by a cosine over the outer three steps
of its grid (it does not reach zero at its edge, up to 1.13 m); the bed and
the surface rise together. Two source timings: instantaneous, and at each
cell's onset = the rupture time plus half the rise time of the nearest
subfault of the `.fsp` (kinematic, the base). Stated as a transparent
assumed initial sea surface from a finite-fault model; its uncertainty is
not published by the USGS: the variants (instantaneous/kinematic,
taper/none) are sensitivities, not an uncertainty of the fault.

## The comparison metric (fixed before the comparison)

Per station, in a window (21416: +26 to +70 min, after the shaking;
21415: +50 to +118 min): the arrival as the half-peak crossing of the first
crest (the reference module's definition), the peak height, the model minus
measurement residual (model interpolated onto the record's times), its rms
against the dossier's floor (0.020 m, 0.007 m), and the rms after shifting
the model by the arrival difference. The record: NCEI residual divided by
0.670 (said on the page). Uncertainty of a model number: the spread over
the grid (16′ to 8′), the source timing, the boundary, and rotation; of an
observed number: the sampling (1 min) and the floor. No claim of agreement
the numbers do not give.

## Figures (Skills: pbc-scientific-visualization@a70b501)

| Cell | Content | Status | Validation | Fallback |
|---|---|---|---|---|
| `fig-tsunami-benchmarks` | log-log error against cell size, first order, minmod, monotonized central, reference slopes | simulated (no dataset) | orders asserted | table `linear-wave` |
| `fig-tsunami-map` (preview) | largest height (banded), arrival contours every 15 min, USGS uplift contours, DARTs | simulated, `fig-dataset` + `fig-artifact: modelled-reference` | budget; arrival in the table | tables, prose |
| `fig-tsunami-comparison` | both stations: record solid, model dashed (8′; 4′ at 21416 to 45 min), residuals below, windows shaded, credit | processed, `fig-dataset` + `fig-artifact: processed-measured` | `check_figure(residuals=True)`, legend statuses | table `comparison` |

Five figures were 846 kB; three keep the local payload at 81 % of 525,000
bytes. No animation, no widget. Byte-identical draws (test).

## Claims

numerically-verified: still water, linear wave orders, speed, budget,
positivity, CFL, boundary, grid. experimentally-supported or observational:
the comparison numbers (what the record shows; what the model gives against
it, qualified). The credibility boundary as a typed claim div:
teaching-scale, not for warning, inundation or hazard forecasting.

## Tests

- `tests/unit/test_tsunami.py`: one-row grid = FL5 1-D to round-off; lake at
  rest flat, bumpy, sphere, rotating; closed-basin volume; positivity over a
  dry bed; x/y symmetry; plane-wave speed; uplift onset keeps depth.
- `tests/unit/test_reconstructing_the_2025_kamchatka_tsunami_experiment.py`:
  results written, series carry the card's status, every numbered claim,
  figures follow the conventions, byte-identical figures, payload bound,
  no printed number blocks.
- Changed (Level 3): `tests/unit/test_atlas.py::test_the_planned_capstones_description_is_only_the_manifests_explanation`
  expects the unfilled capstone slots of the curriculum (not empty, T11 not
  among them) instead of a fixed list;
  `tests/unit/test_introductions.py::test_a_reference_to_a_planned_slot_in_prose_is_text`
  takes the first unfilled slot. The same behaviour is asserted.

## Runtime and payload estimate

Measured: experiment ≈ 15 s CPU (8′ run ≈ 5 s, 4′ near run ≈ 5 s, 16′
variants ≈ 3 s, benchmarks ≈ 2 s); figures 425 kB locally. Heavy rerun
(`fine_check()`, the whole domain at 4′, about a minute) outside
`verify.conf`, shown as not verified.

## Steps

1. Model module and its tests. 2. Adapter. 3. Experiment module. 4. Page.
5. Experiment tests. 6. Lesson checks, `--only code`, `--only default`,
   `pbc.data.check`, render at 1280 × 800 and 390 × 844. 7. The two
   slot-pinned tests rewritten (Level 3); map legend moved below the axis
   label. 8. Full `./scripts/verify.sh` after the session (Level 3).

## Out of scope

Dispersion, friction, a nested grid, inundation, an inversion of the
source, a new dataset (GEBCO), changes to FL5/FL9 or their claims.
