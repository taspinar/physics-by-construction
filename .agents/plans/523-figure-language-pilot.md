# Plan: F170, the figure language: the six-class audit and the bounded style pilot (Issue #523)

Source: `docs/roadmap.md`, F170; `docs/architecture.md`, "Figure language";
requirements decision 44. Written by the implementer at the start of the
work (the Issue expects a short plan and none existed).

**Level 2.** Paths: `src/pbc` (a new module beside `FIGURE_SETTINGS`, a
new audit tool, four lesson experiments), a new test, `docs/authoring.md`.
No protected path; no existing test or assertion changed; no published
claim, value, series, unit, or uncertainty changed (the figures' bytes
change, their data do not). `pbc.experiment`, `pbc.data.plotting`, and
`src/pbc/authoring` are not changed, so the targeted run selects the four
sample lessons only (`docs/architecture.md`, "Order and verification
cost").

## Visual deliverables

Six revised scientific figures (the samples below).

Skills: pbc-scientific-visualization@a70b501

Skills: pbc-physics-teaching@7f34987

The teaching skill is selected because the displayed `draw_` excerpts of
the four sample lessons change (ADR 023 decision 2).

- **Artifact:** the six figures, drawn by their `draw_` functions under
  `pbc.figure_language`; the audit by `python -m pbc.figure_audit`.
- **Scientific validation:** every drawn series, image, contour level, and
  axis scale identical before and after (fingerprints of the line data,
  image arrays, and levels of each figure, compared between `HEAD` and the
  working tree); the experiments' unit tests unchanged and passing; the
  lesson-pages check (the experiment against the rendered page); the
  independent science review.
- **Accessible fallback:** captions and alt text unchanged and still true
  (line styles, markers, and isotherm labels kept); colour never the only
  encoding; every line at least 3:1 against the plate; type at least
  7 CSS px on a phone.

## The samples

| Class | Lesson | Figure | Why this one |
|---|---|---|---|
| Trajectory | M8, `mechanics/08-kepler-orbit` | `fig-orbit-four-methods` | The numerical-integration figure outside M1 to M5 (F129's former pilot) |
| Multi-series numerical comparison | M8 | `fig-orbit-thousand` | Two methods, two panels over a thousand orbits |
| Phase space | M15, `mechanics/15-hamiltonian-mechanics` | `fig-phase-blob` | Closed curves of three maps |
| Convergence, log-log | T7, `thermodynamics/07-heat-conduction-and-diffusion` | `fig-heat-convergence` | Two panels, reference slopes |
| Field | T7 | `fig-plate-temperature` | Sequential false colour with isotherms |
| Measured against model, residuals | EM8, `electromagnetism/08-rlc-circuit-measurements` | `fig-impedance-fit` | Multi-panel measured data, two models, residuals |

Not chosen: M1 to M5 (the teaching pilots F165 to F167 revise them), AST8,
MAT6, and the measured figures of mechanics most likely to be F172's mixed
sample (F172, Issue #524, is in flight in parallel and changes status
labels and credits; this pilot leaves both untouched), and AI6.

## Steps

1. The audit tool `pbc.figure_audit` and the baseline of the six samples on
   the unchanged tree (below).
2. `pbc.figure_language`: dimensions, type sizes, line widths, the plate and
   axis hierarchy, the grid, the palette rule (`line_colours`), the colour
   maps by semantics, `direct_label`, `reference_slope`, `figure_style`,
   `finish`; tokens from `pbc.authoring.design`, no new colour.
3. The six `draw_` functions opt in; values unchanged.
4. `tests/unit/test_figure_language.py`.
5. `docs/authoring.md`, "Figure language (pilot)".
6. After-audit, series identity, payload, build cost, screenshots at 1280
   and 375 CSS px; the targeted verification last.

## Audit (criterion 1)

Measured with `python -m pbc.figure_audit` on `HEAD` (before) and on the
working tree (after). Desktop: the page shows a figure at its natural
width (half its pixels; measured on a built page at 1280 CSS px). Phone:
375 CSS px, a figure 306 CSS px wide (the content column of 324 px measured
on a built page, less the plate's padding and rule). Text in CSS px is the
size in points times 96/72 times the scale; the status label and the
credit are left out (F172's). Contrast is the least of any data line
against the white plate.

### Before

| Class | Figure | Bytes | Width (px) | Text (pt) | Smallest text, desktop / phone (CSS px) | Legend entries | Titles | Line widths | Markers | Colour maps | Least line contrast |
|---|---|--:|--:|---|---|--:|--:|---|--:|---|--:|
| trajectory | `fig-orbit-four-methods` | 98441 | 566 | 10 to 10 | 13.3 / 7.2 | 0 | 4 | 0.8, 1.5 | 4 | none | 7.46 |
| multi-series numerical comparison | `fig-orbit-thousand` | 104321 | 606 | 10 to 10 | 13.3 / 6.7 | 2 | 0 | 1.5 | 0 | none | 9.12 |
| phase space | `fig-phase-blob` | 45270 | 532 | 10 to 10 | 13.3 / 7.7 | 3 | 0 | 1.5 | 0 | none | 7.46 |
| convergence, log-log | `fig-heat-convergence` | 89223 | 681 | 10 to 10 | 13.3 / 6.0 | 4 | 0 | 1.5 | 10 | none | 7.46 |
| field | `fig-plate-temperature` | 111385 | 586 | 6.94 to 10 | 9.3 / 4.8 | 0 | 2 |  | 0 | viridis | 1.74 |
| measured against model, residuals | `fig-impedance-fit` | 189510 | 626 | 7.5 to 12 | 10.0 / 4.9 | 8 | 3 | 0.8, 1.2, 1.4 | 243 | none | 3.42 |

Total 638,150 bytes.

Findings, by the criteria of the Issue:

- **Legibility.** Widths from 532 to 681 CSS px: on a phone the scale falls
  to 0.45 to 0.58, and the smallest type to 4.8 (the isotherm labels) and
  4.9 CSS px (the legends of the impedance figure at 7.5 pt); the tick
  labels of the widest figure reach 6.0 px. Only the phase-space figure
  keeps 7 px.
- **Typography against the page.** Matplotlib's defaults throughout: black
  text and frames on the white plate beside the page's ink and rule
  greys; no type hierarchy (labels, ticks, and titles all 10 pt, the
  impedance figure 7 to 12 pt by hand). The face stays DejaVu Sans
  (see `docs/authoring.md`): the site's STIX Two Text is not available to
  Matplotlib, and its bundled STIXGeneral resolves to different files on
  different machines.
- **Legend placement.** The convergence figure repeats a two-entry legend
  in each panel, one entry of which, "measured", is a status word for a
  computed error; the impedance figure has eight entries in three legends,
  the first of them over the curves on a phone, and repeats the model
  names in all three panels and "[simulated]" in two.
- **Line and marker hierarchy.** One width (1.5) for data, models, and
  references alike, except the hand-set widths of M8 and EM8; the
  reference slopes as heavy as the data.
- **Colour-scale semantics.** The field uses viridis for a temperature, a
  magnitude: right. Hex values typed in a lesson (`"#00429d"`, `"#93003a"`,
  `"#555555"` in M8) where `FIGURE_COLOURS` holds them.
- **Status words, titles, markers.** The status words of the impedance
  legends are needed (a mixed figure: measurement and models); their
  presentation is F172's and stays. No duplicate titles; the 243 markers of
  the impedance figure are the samples (measured) and the residual of the
  fitted model, all needed.
- **File sizes.** 45 to 190 KB; within every budget.

### After

| Class | Figure | Bytes | Width (px) | Text (pt) | Smallest text, desktop / phone (CSS px) | Legend entries | Titles | Line widths | Markers | Colour maps | Least line contrast |
|---|---|--:|--:|---|---|--:|--:|---|--:|---|--:|
| trajectory | `fig-orbit-four-methods` | 101211 | 531 | 9.5 to 11 | 12.7 / 7.3 | 0 | 4 | 1, 1.4 | 4 | none | 7.46 |
| multi-series numerical comparison | `fig-orbit-thousand` | 107506 | 548 | 10 to 11 | 13.3 / 7.4 | 2 | 0 | 1.8 | 0 | none | 9.12 |
| phase space | `fig-phase-blob` | 47472 | 547 | 9.5 to 11 | 12.7 / 7.1 | 0 | 0 | 1.8 | 0 | none | 7.46 |
| convergence, log-log | `fig-heat-convergence` | 74339 | 548 | 9.5 to 11 | 12.7 / 7.1 | 0 | 0 | 1, 1.8 | 10 | none | 6.39 |
| field | `fig-plate-temperature` | 111163 | 547 | 9.5 to 11 | 12.7 / 7.1 | 0 | 2 |  | 0 | viridis | 3.86 |
| measured against model, residuals | `fig-impedance-fit` | 184471 | 550 | 9.5 to 11 | 12.7 / 7.0 | 3 | 3 | 0.8, 1.4 | 243 | none | 3.42 |

Total 626,162 bytes (−1.9 %).

What changed, per figure, with every value kept:

- `fig-orbit-four-methods`: `FIGURE_COLOURS` instead of typed hex values;
  the exact ellipse dotted at the model width, the runs at the guide
  width; "exact", "two orbits", and "star" named once in the explicit
  Euler panel, where the curves lie apart (before: no names at all).
- `fig-orbit-thousand`: the light grid; one legend, top panel (direct
  labels would sit on the spikes of the semi-major axis).
- `fig-phase-blob`: the three curves named beside them; no legend.
- `fig-heat-convergence`: the two legends replaced by "slope 2" and
  "slope 1" beside the reference lines, which stay dotted, below the data,
  and thinner; the word "measured" for a computed error is gone; every
  other dt tick labelled (the five ticks stay).
- `fig-plate-temperature`: the isotherm labels at the top of each arch on
  the plate's middle line, level and 9.5 pt (before: 6.9 pt, placed by
  Matplotlib along the steep sides); ticks at 0, 5, 10 cm. Each isotherm
  white or ink, whichever has the more contrast with the map's colour at
  its level (`isoline_colours`: 30 and 40 °C white, 60 and 80 °C ink;
  before: all white, 1.74:1 on the bright side of the map). Review round 1,
  M1.
- `fig-impedance-fit`: one legend of three entries in the empty upper left
  of the magnitude panel (the upper limit raised to five times the peak to
  make room: the scale stays log-log, every sample shown); the residuals named on their curves; the
  status words, the "no uncertainty per point given", the model names, and
  the credit kept.

**Series identity.** For each figure, the fingerprints of every line's
data, every image array, every contour level set, and both axis scales
are the same sets before and after (the comparison script read the six
figures from `HEAD` and from the working tree).

**Payload and build cost (criterion 4).** −12.0 KB over the six figures;
each lesson's page stays far inside the 3 MB budget, and EM8's figures
inside the 750 KB of its lab test. Drawing time of the six (three
encodings each, after a warm-up): 1.090 s before, 1.108 s after.

**Contrast.** Ink and muted grey at 17.2:1 and 6.4:1 on the plate, the
rule's grey at 4.0:1; every data line at 3:1 or more
(`tests/unit/test_figure_language.py`). The column "Least line contrast"
covers every stroke: a `Line2D` against the plate, and a stroke of a
collection (the field's isotherms, drawn by `contour`) against what lies
beneath it, sampled five times along each segment, the rendered pixel of
the field's image under the sample (the audit of review round 1, M1; the
before table's field row was measured again with it on the base's
figure). Inside the plate the least isotherm contrast is 3.86:1 (before:
1.74:1), and each isotherm label takes its line's colour at 4.5:1 or more
against its level. The samples on the image's border ring, the plate's
boundary values, are counted apart, not hidden: 10 below 3:1, all where
the isotherms end in the two bottom corners, where the hot edge (100 °C)
meets the cold ones (20 °C) and no stroke colour has 3:1 against both
(before: 24).

**Screenshots.** Each figure on the plate of `site.css` at 1280 and 375
CSS px, before and after, were taken from a scratch harness for the visual
check; nothing generated is committed.

## Skills applied

- **pbc-scientific-visualization** (digest `a70b5016…`): axes and units
  unchanged; convergence as the skill's good example (reference slopes
  labelled as such, not fits, below the data); the measurement solid
  markers and the models dashed and dotted, apart, the residual panel
  below on the same axis; colour never the only encoding; deterministic
  bytes.
- **pbc-physics-teaching** (digest `7f349871…`): the displayed `draw_`
  excerpts of the four lessons change. Purpose of each (section 7): all six
  are rendering, except `draw_impedance_fit`, whose residual line
  (`relative_residual`) is the one scientific transformation and stays in
  the excerpt as it was. The skill's choice for rendering is a Source link
  only; changing a display form is the teaching pilots' and F168's
  decision, not this pilot's, so the forms stay and the language adds as
  little displayed code as it can: one `with figure_style():` line and
  `return finish(fig)`, and named helpers (`direct_label`,
  `reference_slope`) instead of inline annotation code. For the owner's
  rollout decision: a rollout to every figure lengthens every displayed
  plotting excerpt by these lines, unless those excerpts become Source
  links first.

## Owner's decision (criterion 6)

On the Issue, after the review: all figures (F171 as planned), a selective
migration (which classes or courses), or none.
