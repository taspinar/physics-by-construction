# Plan: Issue #307, F74 — Wave flume lab (W8)

- Issue: #307 (source: `docs/roadmap.md`, F74)
- Branch: `feature/307-wave-flume-lab-w8`
- Base commit: `cd92121`
- Written by the implementer: no plan existed when the feature started.
- Risk: Level 2 (Medium) by its paths: one new lesson, a new module of
  `src/pbc/waves/`, additions to `src/pbc/data/` (the flume reader, the
  sample extraction, the comparator data), a widened committed sample and its
  card and dossier, the waveform comparator generalised, and tests. No
  published claim changes: the gravitational-wave lab keeps its comparator,
  its labels, and its numbers (the e2e test of the comparator is kept and
  extended, none of its assertions dropped).
- Governing documents: `docs/architecture.md` ("Measured-data lab"),
  `docs/authoring.md` ("Measured data", "Widgets", format 2), ADR 007
  (datasets, caps, artifact types), ADR 013 (slots, the placement rule),
  ADR 016 (the experiment), ADR 019 (skills), ADR 020 (risk levels).
- Gates: F61, F62, F71, F51, F43 delivered; the go decision of F50 exists
  (`docs/datasets/aalborg-submerged-bar.md`); F113 read as the owner's
  interim full-run gate, as the earlier lesson features of this phase did.

## Findings that shape the design

- The archive's solver input files hold the geometry the dossier said was
  missing (the dossier read only the Readme and the data files): the gauge
  positions (i-VoF `waveGaugesNProbes/WGset1_sets`, the same twenty x values
  in the gauges of the D-SPH definition XML), the still-water depth 0.3 m,
  the bar (front slope from 2.813 m, crest 0.147 m deep from 4.323 to
  5.327 m, lee slope to 6.112 m in i-VoF; crest 0.150 m deep from 4.343 to
  5.347 m in D-SPH), and the wave (period 1.5 s, height 0.024 to 0.025 m).
  The lesson takes them from there, says so, and states the 3 mm and 20 mm
  differences between the two solvers' bars as a geometric uncertainty. The
  dossier and the card record the finding (their open item "gauge
  positions" is closed by it; the source paper is still not read).
- The comparison of dispersion needs every gauge, not gauge 5 alone, so the
  committed sample is widened within the caps (the Issue allows it):
  the experiment's seven columns of each other gauge for t <= 22 s, and the
  three solvers' A files with all twenty gauges for t <= 22 s. Estimated
  6.5 MB more, 7.0 MB for the dataset (cap 8 MB), no file over 2 MB.
- Exploration on the full download (scratch, not committed): the phase of
  the fundamental at every gauge follows the linear dispersion relation
  integrated along the bed to about 0.1 rad over 39 rad, once the 2 pi
  branch is fixed; the non-dispersive speed sqrt(g h) of the wave equation
  (W1) misses by about half a cycle at the last gauge. Gauge spacings inside
  three clusters (before the bar, on and behind the bar, the far flat part)
  are under half a wavelength, so the local wavenumber of each cluster is
  measured without a branch choice; between clusters the comparison is made
  on the wrapped phase, which a model wrong by a whole cycle would pass, and
  the page says so.

## Design

One lesson, `wave-flume-lab`, slot W8, in the `waves` strand at the next
free order, 8, `methods: [measured-data, simulation]`, prerequisite
`interference-and-resonance` (W2, which builds on W1).

Code:

- `src/pbc/waves/water.py`: the linear water-wave dispersion relation
  (wavenumber by Newton's method, phase and group speed, the shallow-water
  limit of the wave equation), the phase accumulated along a varying bed
  (slowly varying, WKB), and linear propagation of a record over a flat bed
  (dispersive and non-dispersive).
- `src/pbc/data/flume.py`: the gauge positions and the bed profile, with
  their source, and a least-squares fit of the harmonics of a known
  frequency in a window.
- `src/pbc/data/reference/aalborg_flume.py`: the extraction of the widened
  sample (cell text unchanged), next to the existing one.
- `src/pbc/data/comparison.py`: the comparator data of a family of named
  models (the flume), beside the existing chirp-mass family.
- `site/widgets/waveform-comparator.js`: labels, metrics, and the button
  text from the data, with the existing gravitational-wave text as what the
  chirp-mass data say; nothing computed in the browser.
- `src/pbc/waves/experiments/wave_flume_lab.py`: the experiment of the page.

The page (format 2, the measured-data page pattern):

| Step | What it shows | Status |
|---|---|---|
| Card | `data_card`, artifact labels, the geometry and where it comes from | - |
| Theory | linear dispersion, its shallow and deep limits, the wave equation of W1 as the shallow limit, group speed | - |
| Records | gauges along the flume: arrival of the wave train, the window of each gauge | processed |
| Arrival | front arrival against position, against the group speed | processed |
| Phase | phase of the fundamental at every gauge with its uncertainty, against the linear dispersion and the non-dispersive model along the bed, and the three solvers' phases | processed |
| Local wavenumber | slope of the phase in each cluster, with the repetition and the scatter uncertainty, against both models | processed |
| Waveform | gauge 1 propagated to gauge 5, dispersive and non-dispersive, and the three solvers, against the measured mean (waveform comparator) | processed |
| Harmonics | the second harmonic grows on the bar and is released behind it: where linear theory stops (a column of the phase table) | processed |
| Claim | qualified: linear dispersion within the uncertainty, the wave equation excluded, where both fail | - |

## Visual deliverables

Scientific figures, drawn by `draw_` functions of the experiment from the
tested code, through `pbc.data.plotting`, measured series solid with their
band, every model dashed and labelled by artifact
(`modelled-reference` for the solvers, our linear predictions
`simulated`), attribution on each figure, alt text without computed values:
`fig-records`, `fig-arrival`, `fig-phase` (the preview), `fig-waveform`
(the keyframe of the comparator). No conceptual diagram:
the geometry is data of the input files, drawn as the bed profile with the
gauges under the phase figure.

Discovered in verification: with five figures at the default sizes the page
transferred 3.33 MB, over the 3 MB budget (the page without its figures is
about 2.08 MB). Without raising the budget: the harmonics figure was dropped
(its second-harmonic amplitudes are a column of the phase table, which is the
claim's evidence), the records show three gauges instead of five, the
waveform comparison uses four periods and its static figure the two linear
predictions only (the solvers are in the comparator and in a table of every
model's metrics), and the canvases are smaller: 0.69 MB of figures, about
2.8 MB for the page. A unit test keeps the figures under 0.75 MB. The CI
runner writes the same PNGs about 14 % larger than macOS (778 kB, over the
limit), so the records, arrival and waveform canvases were made smaller
again, with their legends rearranged: 0.62 MB on macOS. The phase figure
keeps its size; its labels need it.

Scientific validation: every figure shows quantities that the lesson's
checks or its unit tests assert. Accessible fallback: alt text, the tables
of phases and wavenumbers, and the static figure under the comparator.

Skills: pbc-scientific-visualization@a70b501, frontend-design@dbd4588

The first for the five figures, the second for the change to the
comparator (its words and controls from the data; no new design).

## Verification

- `tests/unit/test_water.py`: the dispersion relation, its limits, group
  speed against a numerical derivative, the WKB phase on a flat bed, linear
  propagation of a monochromatic wave.
- `tests/unit/test_flume.py` or `tests/unit/test_data_samples.py`: the
  parsing test of every new sample file; the harmonic fit on a synthetic
  record.
- `tests/unit/test_comparison.py`: the named-model comparator data.
- `tests/unit/test_wave_flume_lab_experiment.py`: the claims of the page
  (phases within the stated bound, the wave equation excluded, figures
  checked with `check_figure`).
- `tests/e2e/test_comparator.py`: the flume page's comparator as well.
- `./scripts/verify.sh` (full: a widget and a shared plotting input change),
  else the tier the targeted run reports.

## Criteria and gates

| Criterion | Gate |
|---|---|
| The lab rule | implementation |
| The measured series never labelled `simulated`; the CFD series labelled by its artifact | implementation |
| The model's dispersion compared with the measured gauges with uncertainty | implementation |
