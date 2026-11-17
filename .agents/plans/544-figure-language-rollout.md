# Plan: F171, the figure language rollout, targeted (Issue #544)

Source: Issue #544 and the owner's decision of 2026-11-15 quoted there;
`docs/roadmap.md`, F171; F170's plan (`.agents/plans/523-figure-language-pilot.md`)
and its module `pbc.figure_language`; F173's plan
(`.agents/plans/531-figure-status-rollout.md`). Written by the implementer
at the start of the work; no plan existed.

**Two phases, the owner's approval between them.** Phase 1 (this
document) is the scope proposal and changes no source, figure, test or
lesson. Phase 2 starts only after the owner approves the scope below, or
a narrower one, on the Issue.

**Level.** Phase 1: Level 1 (this plan only). Phase 2, expected: Level 2
by its paths (lesson experiment modules under `src/pbc/*/experiments/`,
`tests/unit/test_figure_language.py`, `docs/authoring.md`), unless the
owner's approval adds a shared module. No published claim, value, unit or
uncertainty is to change. The full verification runs after the rollout
in any case (the owner's decision: shared figure code; P7).

## Visual deliverables

Scientific figures: the restyled figures of the approved list (phase 2).

Skills: pbc-scientific-visualization@a70b501

Skills: none (phase 1 changes no lesson's teaching; phase 2 selects
pbc-physics-teaching@7f34987, because the displayed `draw_` excerpts of
the changed figures change: 27 of the 32 figures below are shown in their
lesson)

- **Artifact:** phase 1, this proposal with its images under
  `.agents/handoffs/544-scope/` (Git ignores them; the paths are below).
  Phase 2, the figures of the approved list, drawn by their `draw_`
  functions under `pbc.figure_language`.
- **Scientific validation:** every drawn series, axis scale, axis limit
  and axis label identical before and after (fingerprints, P4); the
  experiments' numbers and tables byte-identical; the experiments' unit
  tests unchanged and passing; the lesson-pages check; the full run with
  the determinism and reproduction checks.
- **Accessible fallback:** captions and alt text unchanged and still true
  (no line style, marker or label that an alt text names is removed);
  colour never the only encoding; every line at least 3:1 against the
  plate; text at least 7.07 CSS px at a 375 px phone (the language's
  floor, `tests/unit/test_figure_language.py`); under the revised
  language R (phase 2a, below), if approved, at least 9.0 CSS px at a
  320 px phone.

## How the proposal was made

Every lesson experiment was run on `HEAD` (0cdde75), and every one of its
275 figures was drawn and measured with F170's audit
(`pbc.figure_audit.measure`) and classified by what it draws (axes off,
images and contours, log scales, equal aspect, twin axes, bands, error
bars, bars, scatter, number of panels and of curves per panel, legend
entries, colour maps). Each figure that would change was then looked at
by eye. Three candidates were restyled in a scratch copy of `src` (not in
the repository) to test the rollout outside the pilot's six. Tools, data
and images, for phase 2 and for the owner:

- `.agents/handoffs/544-scope/tools/`: `inventory2.py` (run and measure
  every figure), `static.py` (the draw function, whether the lesson shows
  it, typed hex values), `sort.py` and `tables.py` (the groups below),
  `shoot.py` (screenshots on a lesson-like plate at 1280, 390 and
  320 CSS px), `write_samples.py`, `proto_render.py` (render, audit and
  fingerprint before and after).
- `.agents/handoffs/544-scope/data/`: `final.json` (every figure, its
  group, the reason, the audit), `tables.md` (the tables below),
  `sheet0.png` to `sheet4.png` (contact sheets of the candidates).
- `.agents/handoffs/544-scope/pairs/`: before and after side by side,
  per figure and width: `fig-*--{1280,390,320}.png` (the pilot's six,
  before = `a53018c`, the commit before F170), and
  `proto--fig-*--{1280,390,320}.png` (the three prototypes, before =
  `HEAD`). `proto-src-diff/prototype.diff` is the prototypes' code.

The screenshot harness shows a figure on a white plate with an 8 px
padding and a 1 px rule, at its natural width (half its pixels) and at
most the content column: 680 CSS px at 1280, 321 at 390, 251 at 320 (the
column measured by F170 at 375 is 324 px; it is about the viewport less
51 px). It is an approximation of the built page, not the page.

## P1. The style choices taken over, as exact changes

Each is a change inside a figure's own `draw_` function; nothing global.
`FIGURE_SETTINGS` (`pbc.experiment`) and `pbc.figure_language` stay as
they are, so a figure outside the list keeps every byte.

| | The change (exact) | Before/after example (pilot) |
|---|---|---|
| S1 | The drawing inside `with figure_style():` (the `RC` of `pbc.figure_language`: DejaVu Sans; ticks and legends 10 pt, labels and titles 11 pt, notes 9.5 pt; labels in ink `#1c1b19`, tick labels muted `#57606a`, axes and ticks in the rule's `#857f73`; no top or right spine; frameless legend; `FIGURE_COLOURS` as the colour cycle; constrained layout), `return finish(fig)` or `finish(fig, grid=True)` where values are read off (convergence, a series over time); `fig.tight_layout()` removed (constrained layout does it); explicit font sizes below the language's (`fontsize=7`, `"small"`, `"x-small"`) removed so the `TEXT` sizes apply | `fig-phase-blob`, `fig-orbit-thousand` |
| S2 | `figsize=figsize(kind)` instead of the figure's own size: one width, 5.6 in (538 CSS px on a desktop); heights from `ASPECTS` (`"line"` 0.62, `"pair"` 0.5, `"square"` 0.9, `"stacked"` 0.95) by the figure's panel layout | all six; `fig-heat-convergence` (681 → 548 px) |
| S3 | Line widths from `LINE`: data 1.8 pt (the `RC` default), models 1.4, guides, references and runs over many revolutions 1.0, where the figure sets a width by hand; a typed hex that equals a palette colour or a token becomes the name (`FIGURE_COLOURS[i]`, `MUTED`); a line colour under 3:1 against the plate becomes the next `FIGURE_COLOURS` entry not yet used in the figure (`line_colours`) | `fig-orbit-four-methods` (`"#00429d"` → `FIGURE_COLOURS[0]`, widths 0.8 → 1.0 and the exact orbit 1.4) |
| S4 | A reference slope on log-log axes drawn by `reference_slope(ax, h, anchor, order)` (dotted, muted, 1.0 pt, "slope N" on the plot) instead of a legend entry, **only where the figure's own reference line is `0.5 * anchor * (h / h[0]) ** order`**, the line `reference_slope` draws, so the reference's values stay the same; elsewhere the reference keeps its values and its legend entry and takes only S3's width and colour | `fig-heat-convergence` |

Not taken over in this rollout (each needs a judgement per figure, which
F170 made by hand on its six):

- **S5, labels:** direct labels instead of a legend (`direct_label`), one
  legend of at most three entries, panel titles only where panels differ.
  Needed by list B below; proposed there, for the owner to approve or
  not.
- **S6, fields:** `isoline_colours` and `cased` isolines, `SEQUENTIAL`
  and `DIVERGING` colour maps by semantics. No field outside the pilot's
  is in a tested variant (P2), so S6 changes no figure now.
- Tick thinning, raised axis limits, and moved isotherm labels: F170 did
  these on single figures; this rollout changes no tick set and no limit.

## P2. Where the pilot is representative, and where it is not

F170's six samples and what they tested: a trajectory with equal axes (four
panels), a multi-series comparison (two stacked panels, one legend), a
phase-space plot (closed curves, one panel), a convergence plot on log-log
axes (two panels side by side, reference slopes), a field (a sequential
image of a grid, two panels, isotherms, a colour bar), and measured data
against two models with residuals (three stacked panels).

**Representative (in the rollout):** line plots on linear axes and log-log
plots with one panel, or two panels stacked, at most five curves in a
panel and at most three legend entries; trajectories and phase-space
curves of one panel with equal axes; convergence plots with a reference
slope.

**Not tested (out until the owner has reviewed a representative example),
with the number of figures of each type:** a legend of more than three
entries (41), a family of more than five curves in a panel (24), semi-log
axes (23), error bars (7), bars or histograms (7), a diverging colour map
(5), a band of uncertainty or range (2), a scatter of points (2), more than
four panels, contours or field lines without an image, polar axes, three
panels side by side (two figures), a finite-element mesh field, a
likelihood map, a deliberately cased line (one each): 119 figures. The
largest three types would each need one reviewed example first; the
proposal for that example is under "Open questions for the owner".

**Out for another reason (92):**

- **Measured data with declared provenance (58, all of F172/F173's
  figures).** The class was tested (EM8's `fig-impedance-fit`), but since
  F173 the painted credit line ("Visualization: Physics by Construction ·
  Data: …") sets the width of such a figure: EM8's pilot figure is 548
  CSS px without it and 621 with it on the page, so its smallest text on
  a 375 px phone is 6.2 CSS px, not the 7.1 the audit reports (the audit
  draws the figure without the credit). The rollout cannot fix this
  without changing the credit's painting, which is F173's rule (P5), so
  the class stays out. See "Open questions".
- **M1 to M5 (17):** the teaching pilots F165 to F167 revise them; F167
  (M5 and the review of the sequence) is open.
- **AI6 (8):** the four draw functions that make AI6's model-input
  pictures (`draw_forces_on_a_falling_particle`,
  `draw_fall_with_linear_drag`, `draw_dipole_field`, `draw_strain`), in
  AI6 and in their own lessons, and AI6's own result figure (I37).
- **Conceptual diagrams (6):** `pbc.authoring.diagrams`; the language
  changes none of it.
- **Not lesson figures (3):** the home page's two and the lesson
  template's example.

## P3. The figures that change, and the figures that stay

Rule: a figure in a representative type changes only when the audit
finds something the language fixes and the reader can see: text under the
phone floor (7.07 CSS px at 375 px), or a line under 3:1. A typed hex
equal to a palette colour or a token changes no pixel; a figure with only
that stays as it is (a source cleanup is not this rollout's purpose).

**List A (28 figures, S1 to S4, the mechanical change):** one panel or
two stacked panels with the legend inside the axes. **List B (4 figures,
S1 to S4 and S5):** a legend outside the axes or two panels side by side;
the scratch prototype showed that the mechanical change alone does not
improve them (P6), so each needs S5, and is out unless the owner
approves S5 for it.

Phase 2's gate per figure: a figure is kept only if (a) its smallest text
at 375 px is at least 7.07 CSS px and every line has 3:1, (b) its
fingerprint is identical (P4), and (c) at 390 and 320 px no legend or
label covers data and its plot area is not smaller than before. A figure
of list A that fails (c) is not given S5 without the owner's approval:
it is restored to its old form and reported.

#### Would change (A: the mechanical change; B: also needs S5)

| # | List | Class | Lesson | Figure | Width (CSS px) | Smallest phone text (CSS px) | Legend entries | What the audit finds | Draw function shown in the lesson |
|--:|---|---|---|---|--:|--:|--:|---|---|
| 1 | B | trajectory | `electromagnetism/02-charged-particles-in-fields` | `fig-drift` | 636 | 5.1 | 2 | phone 5.1 px | yes |
| 2 | B | trajectory | `mechanics/17-many-body-gravitation` | `fig-solar-system` | 605 | 5.6 | 3 | phone 5.6 px | no |
| 3 | B | phase space | `mechanics/18-nonlinear-dynamics-and-bifurcations` | `fig-limit-cycle` | 711 | 4.8 | 3 | phone 4.8 px | yes |
| 4 | A | log-log | `astrophysics/02-modified-gravity` | `fig-power-law` | 555 | 6.1 | 3 | phone 6.1 px | yes |
| 5 | A | log-log | `astrophysics/02-modified-gravity` | `fig-yukawa` | 555 | 6.1 | 2 | phone 6.1 px | yes |
| 6 | A | log-log | `electromagnetism/04-maxwells-equations-and-fdtd` | `fig-fdtd-dispersion` | 603 | 6.8 | 3 | phone 6.8 px | yes |
| 7 | A | log-log | `electromagnetism/06-waveguides-and-antenna-basics` | `fig-cutoff-convergence` | 603 | 6.8 | 2 | phone 6.8 px | yes |
| 8 | A | log-log | `mechanics/19-rotational-motion` | `fig-precession-rate` | 555 | 6.1 | 2 | phone 6.1 px | yes |
| 9 | A | log-log | `quantum/06-open-quantum-systems` | `fig-convergence` | 561 | 6.1 | 2 | phone 6.1 px | yes |
| 10 | A | log-log | `waves/06-diffraction-and-imaging` | `fig-fraunhofer-limit` | 574 | 5.7 | 2 | phone 5.7 px | yes |
| 11 | A | line | `agents-llm/10-equations-from-noisy-trajectories` | `fig-held-out` | 625 | 5.2 | 2 | phone 5.2 px | yes |
| 12 | A | line | `astrophysics/03-gravitational-lensing` | `fig-light-curves` | 545 | 6.2 | 3 | phone 6.2 px | yes |
| 13 | A | line | `astrophysics/04-special-relativity` | `fig-collision` | 549 | 6.2 | 3 | phone 6.2 px | yes |
| 14 | A | line | `astrophysics/08-exoplanet-transit` | `fig-limb` | 606 | 5.6 | 3 | phone 5.6 px | yes |
| 15 | A | line | `electromagnetism/03-faradays-law-and-induction` | `fig-moving-loop` | 553 | 5.9 | 2 | phone 5.9 px | yes |
| 16 | A | line | `electromagnetism/04-maxwells-equations-and-fdtd` | `fig-pulse-at-interface` | 606 | 6.7 | 3 | phone 6.7 px | yes |
| 17 | A | line | `electromagnetism/05-rlc-circuits-and-resonance` | `fig-rlc-resonance` | 605 | 6.7 | 2 | phone 6.7 px | yes |
| 18 | A | line | `electromagnetism/07-adaptive-phased-array-beam-steering` | `fig-quantisation` | 605 | 5.6 | 2 | phone 5.6 px | no |
| 19 | A | line | `fluids/05-navier-stokes-fundamentals` | `fig-energy-budget` | 605 | 6.7 | 2 | phone 6.7 px | yes |
| 20 | A | line | `fluids/06-vortex-formation-and-flow-around-obstacles` | `fig-wake-signal` | 606 | 5.6 | 3 | phone 5.6 px | yes |
| 21 | A | line | `materials/02-electronic-band-structure` | `fig-bloch` | 540 | 6.3 | 3 | phone 6.3 px | yes |
| 22 | A | line | `materials/02-electronic-band-structure` | `fig-counting` | 540 | 6.3 | 2 | phone 6.3 px | yes |
| 23 | A | line | `materials/04-defects-and-material-properties` | `fig-msd` | 605 | 5.6 | 3 | phone 5.6 px | yes |
| 24 | A | line | `mechanics/12-inverse-physics-parameter-discovery` | `fig-residuals` | 683 | 6.0 | 2 | phone 6.0 px | no |
| 25 | A | line | `thermodynamics/03-entropy-from-ensembles` | `fig-entropy-growth` | 532 | 7.7 | 3 | the orange #e08214 at 2.85:1 | yes |
| 26 | A | line | `thermodynamics/06-heat-engines-and-thermodynamic-cycles` | `fig-otto-against-carnot` | 606 | 6.7 | 3 | phone 6.7 px | yes |
| 27 | A | line | `waves/02-interference-and-resonance` | `fig-interference` | 545 | 6.0 | 3 | phone 6.0 px | yes |
| 28 | A | line | `waves/02-interference-and-resonance` | `fig-resonance` | 582 | 7.0 | 2 | phone 7.0 px | yes |
| 29 | A | line | `waves/04-refraction-and-snells-law` | `fig-interface-pulse` | 556 | 5.1 | 3 | phone 5.1 px | yes |
| 30 | B | line | `waves/06-diffraction-and-imaging` | `fig-airy-rayleigh` | 682 | 4.2 | 3 | phone 4.2 px | yes |
| 31 | A | line | `waves/06-diffraction-and-imaging` | `fig-doublet` | 564 | 5.1 | 3 | phone 5.1 px | no |
| 32 | A | line | `waves/07-inverse-optics` | `fig-fit` | 606 | 4.7 | 2 | phone 4.7 px | no |

32 figures in 26 lessons (A 28, B 4), 2.60 MB of PNG today.

Notes per figure, from looking at each:

- `fig-fraunhofer-limit`: its reference line is drawn above the data on
  purpose ("drawn above" in its legend), not with S4's factor; it keeps its
  line and legend entry (S4's exception).
- `fig-precession-rate`: its legend calls a computed difference
  "measured"; F170 removed that word from its convergence sample. Renaming
  a legend entry is S5 and is not in list A; it is named here for the
  owner, the figure changes by S1 to S4 only.
- `fig-convergence` of `quantum/06-open-quantum-systems` already labels its slopes on the plot;
  it changes by S1 to S3.
- `fig-entropy-growth`: its orange (`#e08214`, not a palette colour)
  draws the exact distribution at 2.85:1; S3 gives it the next free
  `FIGURE_COLOURS` entry. Its style (dotted) and its legend name stay, so
  the alt text and caption stay true; phase 2 checks them.
- `fig-fit` (inverse optics): a synthetic measurement with a model and a
  residual panel of more than a thousand points; simulated, no declared
  provenance; it changes by S1 to S3.

#### Already good: unchanged

| Class | Lesson | Figure | Width (CSS px) | Smallest phone text (CSS px) | Note |
|---|---|---|--:|--:|---|
| trajectory | `electromagnetism/02-charged-particles-in-fields` | `fig-gyration` | 416 | 7.8 |  |
| trajectory | `mechanics/07-momentum-and-collisions` | `fig-pair-on-a-spring` | 553 | 7.4 | typed hex = palette or muted token (no visible change) |
| trajectory | `mechanics/08-kepler-orbit` | `fig-two-bodies` | 565 | 7.2 | typed hex = palette or muted token (no visible change) |
| trajectory | `mechanics/14-lagrangian-mechanics` | `fig-planet-orbit` | 378 | 10.8 |  |
| trajectory | `mechanics/19-rotational-motion` | `fig-axis-path` | 363 | 9.4 | typed hex = palette or muted token (no visible change) |
| log-log | `agents-llm/03-three-reviewers` | `fig-review-evidence` | 554 | 7.4 | typed hex = palette or muted token (no visible change) |
| log-log | `lean/02-momentum-in-a-collision-proved` | `fig-momentum-residual` | 561 | 7.3 | typed hex = palette or muted token (no visible change) |
| log-log | `quantum/01-the-schrodinger-equation` | `fig-convergence` | 555 | 7.4 |  |
| line | `agents-abm/01-particles-in-a-box` | `fig-relaxation` | 547 | 7.5 | typed hex = palette or muted token (no visible change) |
| line | `agents-llm/01-an-agent-runs-an-experiment` | `fig-agent-evidence` | 562 | 7.3 | typed hex = palette or muted token (no visible change) |
| line | `agents-llm/17-interpretable-physics-explanations` | `fig-explanation-picture` | 553 | 7.4 |  |
| line | `fluids/01-advection-and-diffusion` | `fig-advected-pulse` | 556 | 7.3 |  |
| line | `fluids/03-finite-volume-methods-and-conservation-laws` | `fig-conservative-and-not` | 545 | 7.5 |  |
| line | `lean/03-what-symplectic-euler-conserves` | `fig-modified-energy` | 553 | 7.4 | typed hex = palette or muted token (no visible change) |
| line | `lean/05-the-chirp-law-proved` | `fig-countdown` | 569 | 7.2 | typed hex = palette or muted token (no visible change) |
| line | `mechanics/06-energy-conservation` | `fig-pendulum-over-the-top` | 569 | 7.2 | typed hex = palette or muted token (no visible change) |
| line | `mechanics/06-energy-conservation` | `fig-pendulum-swings` | 565 | 7.2 | typed hex = palette or muted token (no visible change) |
| line | `mechanics/15-hamiltonian-mechanics` | `fig-modified-energy-pendulum` | 565 | 7.2 |  |
| line | `mechanics/16-resonance` | `fig-resonance-curve` | 545 | 7.5 | typed hex = palette or muted token (no visible change) |
| line | `mechanics/16-resonance` | `fig-transient` | 556 | 7.3 |  |
| line | `quantum/02-quantum-tunnelling` | `fig-packet` | 559 | 7.3 |  |
| line | `thermodynamics/01-random-walks-and-diffusion` | `fig-msd` | 555 | 7.4 | typed hex = palette or muted token (no visible change) |
| line | `thermodynamics/02-kinetic-theory-of-gases` | `fig-speed-distribution` | 545 | 7.5 | typed hex = palette or muted token (no visible change) |
| line | `thermodynamics/05-molecular-dynamics` | `fig-equipartition` | 545 | 7.5 |  |
| line | `waves/02-interference-and-resonance` | `fig-superposition` | 514 | 7.9 | typed hex = palette or muted token (no visible change) |
| line | `waves/03-sound-and-the-doppler-effect` | `fig-sweep` | 545 | 7.5 | typed hex = palette or muted token (no visible change) |

26 figures: the text meets the floor, every line has 3:1. The rollout
cannot show them to improve, so they stay.

The full lists of the untested and the out figures, per figure, are in
`.agents/handoffs/544-scope/data/tables.md` and `final.json`.

## P4. Data, calculations, axes, uncertainties and meaning are kept

No change of S1 to S4 touches a computation: each is inside a `draw_`
function, after the values are computed, and changes only how they are
drawn (face, sizes, colours of text and frame, line widths, the canvas,
a reference slope's label). Per change:

- **S1 and S2** change type, frame, colours of text and the canvas size;
  no series, scale, limit, tick set or label text.
- **S3** changes the width and the colour of a line, never its style or
  marker (the encodings that alt texts name and that tell series apart
  without colour); one colour changes (`fig-entropy-growth`).
- **S4** replaces a reference line by the same line (same values: S4
  applies only where the factor is the same) with a label on the plot,
  and removes its legend entry. A reference is a comparison, never a fit,
  before and after.
- No uncertainty is drawn in any figure of list A or B (bands and error
  bars are untested types); none is added or removed.

How phase 2 shows it:

1. **Fingerprints, per figure:** the SHA-256 of every line's data, the
   axis scales, the limits, the axis labels, and the legend texts, for
   `HEAD` and the working tree (`tools/proto_render.py` does it for the
   prototypes: series, scales, limits and labels identical; only the
   reference's legend entry gone in `fig-fdtd-dispersion`). Recorded in
   this plan per figure.
2. **Numbers and tables:** each changed experiment's `results.json` (its
   numbers and tables, not its figures) byte-identical before and after.
3. **The experiments' unit tests** unchanged and passing; no assertion
   changed.
4. **The full run** (P7): determinism (two builds, same bytes) and the
   reproduction check; the lesson-pages check of every changed lesson
   (the experiment against the rendered page).
5. **AI6:** the PNG bytes of its four model-input figures and of its
   result figure identical before and after (their SHA-256 recorded);
   none of their draw functions is touched.

## P5. The status and credit rules of F172/F173 are kept

No figure that declares its provenance is in the rollout (P2), so no
declared provenance, `check_roles` role, status at the caption, credit at
the caption, PNG record or painted credit line changes. No caption, no
`fig-status`, `fig-dataset` or `fig-model-of` line changes. The figures of
the rollout are simulated and paint no status or credit (F173: no figure
paints a status, only provenance figures paint a credit). Checked by:
the changed draw functions are compared against the labels of
`Experiment.provenance` of every module (empty intersection, a scripted
check recorded in this plan); `tests/unit/test_figure_provenance.py` and
the lesson checks of the figure captions pass unchanged; the full run's
built-site checks of the figure status and credit pass.

## P6. The examples at desktop and phone width

Images: `.agents/handoffs/544-scope/pairs/`. The pilot's six (before
`a53018c`, after `HEAD`) and the three prototypes (before `HEAD`, after the
scratch change), each at 1280, 390 and 320 CSS px.

What they show:

- **Labels.** At a 375 px phone (the audit's width; 390 px shows a little
  more) the pilot's figures and the prototypes keep text at 7.07 to
  7.45 CSS px (before: 4.2 to 6.8 for the prototypes). **At
  320 px no figure reaches 7 px**: a figure of 548 CSS px is shown at
  251 px, so 9.5 pt is 5.8 CSS px. The language's floor is defined at
  375 px; it still improves 320 px in proportion (`fig-airy-rayleigh`
  3.4 → 5.9 CSS px), but it does not meet a floor there. A floor at
  320 px would need a narrower figure or larger type for every figure,
  a change of the language itself, not of this rollout.
- **Legends.** In a single panel with the legend inside the axes the
  legend grows with the type and stays clear (`fig-fdtd-dispersion`,
  `fig-orbit-thousand`). **In two panels side by side the 10 pt legend
  covers the curves** (`proto--fig-airy-rayleigh--390.png`: the
  three-entry legend lies over the two-point images, which its 7 pt
  legend did not). **A legend outside the axes takes about 40 % of the
  width**, and the plot of an equal-aspect figure becomes smaller than
  before (`proto--fig-limit-cycle--390.png`). These are list B.
- **Multi-panel figures.** Four panels in a square (`fig-orbit-four-methods`)
  and two or three stacked panels (`fig-orbit-thousand`,
  `fig-impedance-fit`) stay legible at 390 px; two panels side by side
  with long y-labels (`fig-heat-convergence`) are tight at 320 px: the
  right panel's y-label nearly touches the left panel.
- **Credit lines.** On a measured figure the painted credit is about
  4 CSS px at 320 px and widens the figure (P2); out of this rollout.

## P7. Verification, payload and build time

- **Verification.** Phase 2 changes the `draw_` functions of 32 figures in
  26 lessons' experiment modules (28 if list B is not approved), the
  tests, and `docs/authoring.md`. The targeted selection would be those
  lessons; the owner asked for a full run after changes of shared figure
  code, so phase 2 ends with the full `./scripts/verify.sh` (after the
  session; sessions run targeted or `--only` tiers), with the determinism
  and the reproduction checks.
- **Payload.** Today the 32 figures weigh 2.60 MB (list A 2.17 MB).
  Measured on the prototypes: +1.7 % (`fig-airy-rayleigh`), −40 %
  (`fig-limit-cycle`, a smaller canvas), −2.5 % (`fig-fdtd-dispersion`);
  F170's five figures other than the cased field: −3.5 % (515 → 497 KB). Expected: within ±10 % of
  2.60 MB in total, every page far inside its 3 MB budget.
- **Build time.** The drawing is the same work on a smaller canvas; F170
  measured 1.090 s → 1.108 s for its six (+1.7 %). Expected: no measurable
  change of the build.
- **Displayed code.** 27 of the 32 draw functions are shown in their
  lessons (24 of list A); each excerpt changes by the `with
  figure_style():` line, the indentation, and `return finish(fig)`.
  Phase 2 selects `pbc-physics-teaching` and checks that every excerpt
  selection still finds its lines (F175's exact selections).

## Phase 2 steps (after the owner's approval)

1. The approved figures opt in, one module at a time (S1 to S4; S5 only
   for the approved figures of list B).
2. Per figure: the gate of P3 (audit, fingerprints, screenshots at 390
   and 320 px); a figure that fails is restored and reported.
3. `tests/unit/test_figure_language.py`: the rollout's figures under the
   same rules as the samples (floor, contrast, opted in).
4. `docs/authoring.md`, "Figure language": the rollout's scope and the
   types left out.
5. The P4 and P5 records in this plan; the targeted run in the session;
   the full run after it.

## Open questions for the owner (phase 1 ends here)

1. **Approve the scope:** list A (28 figures, S1 to S4), with the gate of
   P3; or a narrower list.
2. **List B (4 figures):** approve S5 for them (one legend inside the axes
   where the curves leave room, or the series named beside the curves, as
   F170 did), or leave them out.
3. **Untested types:** which representative examples to review next, if
   any. Proposed: one figure each of the three largest types: a legend of
   more than three entries (41 figures), a family of more than five
   curves (24), semi-log axes (23).
4. **Measured figures:** the painted credit line widens a figure with
   declared provenance beyond the language's width (EM8's pilot figure:
   548 → 621 CSS px, smallest phone text 6.2 CSS px). Fixing it changes
   the painting of F173's credit (a wrapped or shorter line), which is
   outside F171; a follow-up Issue if the owner wants it.
5. **The 320 px floor:** the language meets its 7.07 CSS px floor at 375 px,
   not at 320 px (5.8 CSS px). Keep it so, or ask for a change of the
   language itself (a separate decision).

## The owner's decisions (2026-11-16) and phase 2a

The owner answered the five questions on Issue #544
(issuecomment-6907348958): list A approved with P3's gate; list B one
example first; the three untested types as the next examples; the credit
line of measured figures a separate Issue (#546, outside F171); and **the
figure language changes**: 320 px stays a supported width, and 5.8 CSS px
there and 7.07 CSS px at 375 px are too small. The rollout of list A waits
until the owner approves the revised language from its examples. Phase 2a
(this section) makes those examples and changes no source, figure, test
or lesson.

Examples, with an index of figure, variant, width and smallest text:
`.agents/handoffs/544-scope/examples/` (`README.md` there; the scratch
prototype's code in `src-diff/revised.diff`).

### R. The revised language (proposed, for the owner's approval)

The text-to-width ratio decides the phone size, because one PNG serves
every width: the page shows a figure at its natural width on a desktop
and at 306 CSS px (375 px phone) or 251 CSS px (320 px phone). Larger text
on the old 5.6 in canvas would make desktop text about 19 px; the
proposal therefore narrows the canvas and raises the type together.

| | F170 (today) | Revised (proposed) |
|---|---|---|
| `WIDTH` | 5.6 in (538 CSS px; ~548 cropped) | **4.1 in** (394 CSS px; ~404 cropped) |
| `TEXT` (pt) | tick 10, label 11, title 11, legend 10, note 9.5 | **tick 11, label 12, title 12, legend 11, note 11** |
| `MIN_TEXT` | 9.5 pt | **11 pt** |
| `ASPECTS` | line 0.62, pair 0.5 (side by side), square 0.9, stacked 0.95, measured 1.15 | **line 0.78, pair 1.3 (two panels stacked, never side by side), square 1.0, stacked 1.3, measured 1.6** |
| Ticks | Matplotlib's automatic locator | **at most 5 major ticks** on a linear axis with the automatic locator (`finish`: `MaxNLocator(5, steps=[1, 2, 2.5, 5, 10])`); explicit tick sets unchanged; limits unchanged |
| Legend | inside the axes | **at most three entries inside the axes, where they cover no data**; otherwise the series are named beside the curves (`direct_label`, S5) or, for four or more entries or long names, the legend goes **under the plot in one column** (`fig.legend(loc="outside lower center")`), which takes height, not width |
| Long y-labels | one line | **wrapped onto two lines** where they would take more than about a fifth of the width (text only; same words) |
| Smallest text shown | desktop 12.7, 375 px 7.07, 320 px 5.8 CSS px | **desktop 14.7, 375 px 11.1, 320 px 9.1 CSS px** (measured: 9.1 to 9.3 at 320 on all seven examples) |
| Floor in the tests | 7.07 CSS px at 306 px | **9.0 CSS px at 251 px** (and so ≥ 11 at 306 px) |

Colours, line widths, the hierarchy, the grid rule, S3, S4 and S6 stay as
they are.

What it costs, stated for the owner: on a desktop a figure becomes
narrower (about 404 CSS px instead of about 548, in a 680 px column), with
text at 14.7 px, close to the body text. Two panels side by side become
two stacked panels (taller figure). A legend of four or more entries moves
under the plot (taller figure). Payload of the seven examples: −14 % (733
→ 632 KB); `fig-heat-convergence`, stacked, +22 %.

Considered and not proposed: (a) larger type on the 5.6 in canvas (desktop
text about 19 px, and side-by-side panels no longer fit); (b) two PNGs per
figure, a desktop and a phone rendition chosen by the page with
`<picture>` and a media query: the best of both, but it changes `encode`,
`FigureImage`, the credit painting of F173, every figure's bytes and the
payload (about double), a shared-input change well beyond F171; it would
need its own decision.

**ADRs and protected paths.** No accepted ADR fixes the figure's width, its
type sizes or its phone floor (they are in `pbc.figure_language`,
`tests/unit/test_figure_language.py` and `docs/authoring.md`, "Figure
language"); `docs/PROJECT_REQUIREMENTS.md` (protected) names the figure
language but no number, so it needs no change. The revised language
changes `src/pbc/figure_language.py` (shared figure code, not protected),
the floor of `tests/unit/test_figure_language.py` (a changed test bound:
it is raised, not weakened), `docs/authoring.md`, and the six F170 pilot
figures (they opt in and change with the language). `docs/architecture.md`
(sensitive) needs no change of its words. Expected level of phase 2b:
Level 2 by its paths; the full verification after the session (shared
figure code), as decided.

### The examples (decisions 5, 2, 3)

At 1280, 375 and 320 px, current and revised side by side
(`<figure>--<width>.png`):

- **Decision 5, the revised language:** `fig-heat-convergence` and
  `fig-orbit-four-methods` (F170's pilot: before F170, F170, revised) and
  `fig-fdtd-dispersion` of list A (current, F170 S1–S4, revised). The
  convergence pair is now stacked; the four orbit panels stay a 2 × 2 grid
  and are legible at 320 px (9.3 CSS px); the dispersion figure keeps its
  two-entry legend inside the axes, clear of the data.
- **Decision 2, list B with S5:** `fig-limit-cycle` (equal axes; its
  legend was outside the axes, three of list B's four are of this kind):
  the legend is replaced by the names beside the curves ("start inside"
  with a thin leader line from below right, "start outside", "circle,
  radius 2√μ"); no plot area is given to a legend, so the phase plane
  fills the width at every size.
- **Decision 3, untested types:** a legend of four entries
  (`fig-expansion`: under the plot, one column); a family of six levels
  (`fig-levels`: the levels named "n = 0…5" on the plot as before, the
  three series in a legend under the plot); semi-log axes
  (`fig-separation`: the series named beside the curves; with the 11 pt
  legend inside the axes it covered the regular start's curve, so the
  legend went).

Problems seen: in `fig-levels` the dashed Hermite function lies exactly on
the grid eigenfunction (as before; it is the result). In `fig-separation`
the label "slope of the exponent" sits close to the y tick labels at
320 px, but clear of them. No legend or label covers data in any revised
example at 1280, 375 or 320 px.

Fingerprints (current against revised): every series, axis scale, axis
limit and axis-label text identical in all seven (`audit-*.json`).

### Open questions for the owner (phase 2a ends here)

6. **Approve the revised language R** (4.1 in, 11 pt minimum, at most
   5 ticks, two panels stacked, legend rules; 9.1 CSS px at 320 px, 11.1 at
   375 px, 14.7 on a desktop), or ask for another size.
7. **List B:** approve S5 as shown on `fig-limit-cycle` for the four list B
   figures, or leave them out.
8. **Untested types:** approve the three types for the rollout in the
   revised language, as shown, or keep them out.

Phase 2b, after the approval: the revised language in
`pbc.figure_language` (the six pilot figures follow), list A opted in with
P3's gate (the floor raised to R's), list B and the untested types only as
approved, tests, `docs/authoring.md`, the P4/P5 records; targeted run in
the session, the full run after it.


## Phase 2b: the rollout (2026-11-16)

The owner approved the revised language R on Issue #544
(issuecomment-6908894960), with list A (approved earlier with P3's gate).
Questions 7 (S5 for list B) and 8 (the three untested types) are still
open: their figures are unchanged.

**What changed.**

- `pbc.figure_language`: R exactly (`WIDTH` 4.1 in; `TEXT` 11/12/12/11/11;
  `MIN_TEXT` 11; `ASPECTS` line 0.78, pair 1.3 stacked, square 1.0,
  stacked 1.3, measured 1.6; `TICKS` 5 through `finish`, only on a linear
  axis whose ticks Matplotlib places).
- The six pilot figures follow the language; `fig-heat-convergence` and
  `fig-plate-temperature` are now stacked (their caption and alt text in
  `thermodynamics/07` say top and bottom instead of left and right).
- List A, 28 figures in 23 modules: S1 to S4 and R's legend rule. S4 on
  `fig-fdtd-dispersion` and `fig-cutoff-convergence` (their factor is
  `reference_slope`'s); `fig-fraunhofer-limit` and `fig-precession-rate`
  keep their own reference line and legend entry (another factor);
  `fig-entropy-growth`'s orange `#e08214` (2.85:1) became
  `FIGURE_COLOURS[2]`, its dotted style and width kept so the exact curve
  stays visible over the ensemble.
- P3's gate (c) moved the legend under the plot, in one column, where it
  covered data at R's size: `fig-collision`, `fig-msd`, `fig-bloch`,
  `fig-counting`, `fig-doublet`, `fig-fraunhofer-limit`,
  `fig-moving-loop`, `fig-light-curves`, `fig-interference`, waves
  `fig-resonance`, `fig-residuals`, `fig-pulse-at-interface`,
  `fig-power-law`, `fig-yukawa`, quantum `fig-convergence`,
  `fig-interface-pulse`, `fig-wake-signal`, `fig-fit`; elsewhere it moved
  to a free corner (`fig-energy-budget`, `fig-precession-rate`). No figure
  of list A failed the gate, so none was restored.
- Text only, same words: long axis labels and the long panel titles of
  `fig-impedance-fit` broken onto two or three lines; the legend entry
  "relativistic momentum m gamma v (conserved)" on two lines; the Otto
  annotation "compression reaches 600 K" on two lines. Quantum
  `fig-convergence` turns its explicit step labels by 30 degrees (its tick
  set kept).
- `fig-impedance-fit` (pilot, measured): its legend is the top panel's,
  anchored above the plot and its title, because at 11 pt it covered the
  peak and the credit line takes the foot of the figure; `check_figure`
  (F172) reads the panel's legend, so it stays an axes legend.
- `fluids/05`: the excerpt selection of `draw_energy_budget` follows the
  moved lines (`lines=[(5, 6), (27, 29)]`, the same statements).
- Tests: `ROLLOUT` and `rollout_figures` in `pbc.figure_audit`;
  `tests/unit/test_figure_language.py` holds the floor 9.0 CSS px at
  320 px (and 11.07 at 375 px, 14.5 on a desktop), the canvas width, 3:1,
  at most three legend entries, determinism, and at most five placed ticks
  on every sample and every rollout figure.
- `docs/authoring.md`, "Figure language": R, the legend rule, and the
  rollout's scope with the types left out.

**P4 record (data, values, axes).** Tool:
`.agents/handoffs/544-scope/rollout/tools/gate.py`, run on `HEAD`
(0cdde75, a copy of `src`) and on the working tree, over all 28 modules
(the 23 of list A, the 4 of the pilot, AI6's lesson module);
`compare.py` compares (`rollout/compare.md`, `gate-*.json`).

- `Experiment.results()` (every number, table, output and display)
  identical in all 28 modules.
- Every figure of those modules outside the 34 targets: PNG bytes
  identical.
- AI6: the PNG bytes of the four model-input pictures
  (`pbc.agents.multimodal_lab.pictures()`) identical.
- Per target: every line's data, every image array, the axis scales and
  limits, the axis-label words identical. Differences, all expected: the
  legend entry "reference, slope two" removed by S4 (two figures); line
  breaks in labels, titles and two legend entries; `fig-plate-temperature`
  labels x once under the stack and y on both panels, and its contour
  paths differ only by the wider inline-label gaps of the larger type
  (`test_the_isotherms_are_the_contours_of_the_whole_displayed_field`
  passes).
- Unit tests of the 26 changed modules, the audit, the provenance and the
  excerpts: 226 passed, after the fix of `fig-impedance-fit`'s legend
  (one failure of `check_figure` before it, an axes legend required).

**P5 record (status and credit).** One changed figure declares provenance:
`fig-impedance-fit` (a scripted check of `Experiment.provenance` over the
28 modules). Its declaration, roles, status at the caption, PNG record and
credit line are unchanged; `tests/unit/test_rlc_circuit_measurements_experiment.py`
(the F172 conventions and the PNG record) and
`tests/unit/test_figure_provenance.py` pass. Its page width stays 621 CSS
px, set by the painted credit line, so its smallest text on a 320 px phone
is 5.9 CSS px until Issue #546 wraps the credit (the owner's decision 4).

**Gate per figure (P3), widths in CSS px, smallest text in CSS px at 375
and 320 px, PNG bytes.** All list A figures are 404 px wide and show
11.1 px at 375 and 9.1 px at 320 (before: 4.2 to 7.7 and 3.9 to 6.3).

| figure | width before | after | 375 before | after | 320 before | after | bytes before | after | least line contrast | legend | fingerprint |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| fig-limb | 606 | 404 | 5.61 | 11.11 | 4.6 | 9.11 | 68317 | 54134 | 7.46 | 3 |  |
| fig-light-curves | 545 | 404 | 6.24 | 11.11 | 5.12 | 9.11 | 74730 | 60014 | 7.46 | 3 |  |
| fig-power-law | 555 | 404 | 6.12 | 11.11 | 5.02 | 9.11 | 71545 | 69531 | 7.46 | 3 |  |
| fig-yukawa | 555 | 404 | 6.12 | 11.11 | 5.02 | 9.11 | 63844 | 62939 | 6.39 | 2 |  |
| fig-collision | 549 | 404 | 6.19 | 11.11 | 5.08 | 9.11 | 72212 | 66708 | 9.12 | 3 |  legend ['relativistic momentum m gamma v (conserved)'] -> ['relativistic momentum m gamma v\n(conserved)'] |
| fig-quantisation | 605 | 404 | 5.62 | 11.11 | 4.61 | 9.11 | 47162 | 43774 | 9.12 | 2 |  |
| fig-moving-loop | 553 | 404 | 5.9 | 11.11 | 4.84 | 9.11 | 83254 | 81456 | 7.46 | 2 |  |
| fig-fdtd-dispersion | 603 | 404 | 6.77 | 11.11 | 5.55 | 9.11 | 70016 | 60776 | 6.39 | 2 |  legend ['reference, slope two'] -> [] |
| fig-pulse-at-interface | 606 | 404 | 6.73 | 11.11 | 5.52 | 9.11 | 64219 | 48846 | 7.46 | 3 |  |
| fig-rlc-resonance | 605 | 404 | 6.74 | 11.11 | 5.53 | 9.11 | 86430 | 84072 | 7.46 | 2 |  |
| fig-cutoff-convergence | 603 | 404 | 6.77 | 11.11 | 5.55 | 9.11 | 60004 | 54023 | 6.39 | 1 |  legend ['reference, slope two'] -> [] |
| fig-energy-budget | 605 | 404 | 6.74 | 11.11 | 5.53 | 9.11 | 79565 | 65856 | 7.46 | 2 |  |
| fig-wake-signal | 606 | 404 | 5.61 | 11.11 | 4.6 | 9.11 | 100441 | 72965 | 9.12 | 3 |  |
| fig-msd | 605 | 404 | 5.62 | 11.11 | 4.61 | 9.11 | 79203 | 58406 | 7.46 | 3 |  |
| fig-counting | 540 | 404 | 6.29 | 11.11 | 5.16 | 9.11 | 52070 | 50138 | 9.12 | 2 |  |
| fig-bloch | 540 | 404 | 6.29 | 11.11 | 5.16 | 9.11 | 84785 | 70135 | 7.46 | 3 |  |
| fig-held-out | 625 | 404 | 5.22 | 11.11 | 4.28 | 9.11 | 93355 | 90998 | 9.12 | 2 |  |
| fig-residuals | 683 | 404 | 5.97 | 11.11 | 4.9 | 9.11 | 124790 | 80181 | 3.36 | 2 |  |
| fig-precession-rate | 555 | 404 | 6.12 | 11.11 | 5.02 | 9.11 | 56879 | 55461 | 6.39 | 2 |  |
| fig-convergence | 561 | 405 | 6.06 | 11.08 | 4.97 | 9.09 | 57359 | 64193 | 7.46 | 2 |  |
| fig-entropy-growth | 532 | 404 | 7.67 | 11.11 | 6.29 | 9.11 | 42855 | 41033 | 7.46 | 3 |  |
| fig-otto-against-carnot | 606 | 404 | 6.73 | 11.11 | 5.52 | 9.11 | 79449 | 83682 | 7.46 | 3 |  |
| fig-doublet | 564 | 404 | 5.06 | 11.11 | 4.15 | 9.11 | 89841 | 73542 | 5.93 | 3 |  |
| fig-fraunhofer-limit | 574 | 404 | 5.69 | 11.11 | 4.66 | 9.11 | 71610 | 75236 | 7.46 | 2 |  |
| fig-resonance | 582 | 404 | 7.01 | 11.11 | 5.75 | 9.11 | 105951 | 83528 | 9.12 | 2 |  |
| fig-interference | 545 | 404 | 5.99 | 11.11 | 4.91 | 9.11 | 84007 | 65355 | 3.95 | 3 |  |
| fig-fit | 606 | 404 | 4.71 | 11.11 | 3.87 | 9.11 | 148028 | 140271 | 7.46 | 2 |  |
| fig-interface-pulse | 556 | 404 | 5.14 | 11.11 | 4.21 | 9.11 | 58926 | 57541 | 7.46 | 3 |  |
| fig-orbit-four-methods | 531 | 396 | 7.3 | 11.33 | 5.99 | 9.3 | 101211 | 78411 | 7.46 | 0 |  |
| fig-orbit-thousand | 548 | 404 | 7.45 | 11.11 | 6.11 | 9.11 | 107506 | 96179 | 9.12 | 2 |  |
| fig-phase-blob | 547 | 405 | 7.09 | 11.08 | 5.81 | 9.09 | 47472 | 39210 | 7.46 | 0 |  |
| fig-heat-convergence | 548 | 404 | 7.07 | 11.11 | 5.8 | 9.11 | 74339 | 91042 | 6.39 | 0 |  |
| fig-plate-temperature | 547 | 371 | 7.09 | 12.1 | 5.81 | 9.92 | 137892 | 149599 | 4.17 | 0 | AXES DIFFER |
| fig-impedance-fit | 621 | 621 | 6.24 | 7.23 | 5.12 | 5.93 | 165292 | 157447 | 3.42 | 3 | AXES DIFFER |

Payload of the 34 figures: 2,804,559 to 2,526,682 bytes (−9.9 %).
Screenshots at 1280, 375 and 320 px, before and after side by side:
`rollout/shots/<module>--<figure>--<width>.png`; one per class at 320 px in
`rollout/spot320.png`.


## Phase 2c: list B and the three tested types (2026-11-16)

The owner answered questions 7 and 8 on Issue #544
(issuecomment-6909100974): S5 for all four figures of list B, the series
named beside the curves and checked at 320 px; and the three tested types
in the rollout, with the approved examples as the starting point (a legend
of four entries under the plot, `fig-expansion`; a family of six curves,
`fig-levels`; semi-log with labels beside the curves, `fig-separation`),
every figure of these types from the phase 1 inventory, each through the
gate of list A, a figure that fails left out and listed.

**What changed.**

- `pbc.figure_language`: `figsize(kind, legend=n)` adds `n` times
  `LEGEND_ROW` (0.24 in) for a legend of `n` entries under the plot, so the
  plot keeps its height; nothing else of R changed.
- `pbc.figure_audit`: `ROLLOUT_LIST_B_AND_TYPES` (88 figures since review round 1, below) joins
  `ROLLOUT`; `Audit.axes_legend_entries`, the most entries of one legend
  inside an axes (a legend under the plot is a figure legend and is not
  limited to three).
- 92 figures in 56 modules were drawn in the language (the per-figure
  record, with the change and the 320 px check of each:
  `.agents/handoffs/544-scope/phase2c/record.md`); 88 passed the gate
  and opted in, 4 failed and were restored to their old code (below; the
  fourth, `fig-pythagorean`, at review round 1).
- The patterns used, each from an approved example: a legend of four or
  more entries, or of three long names over the data, goes under the plot
  in one column; two side-by-side panels are stacked (two of equal axes at
  1.7 times the width, so each keeps the full width); a legend of a stacked
  panel stays inside where it covers no data, otherwise its entries go
  under the plot (each entry once); a log axis whose minor labels ran into
  each other shows its own steps as ticks (the approved convergence
  example's pattern); a linear axis whose limits are a multiple of the
  tick step and would show six ticks gets four intervals.
- S3 on three typed colours under 3:1: `#9aa4ae` (2.53:1, the grid's
  readings of AI5 and AI7) became the muted grey, `#c9a227` (2.42:1,
  `fig-cfl`) became `FIGURE_COLOURS[3]`. S4 where the reference line is
  `reference_slope`'s (`fig-particle-gradient`, `fig-fem-convergence`).
- Text only, same words: long axis labels and titles broken onto two or
  three lines; notes at the note size.

**List B with S5, checked at 320 px** (screenshots in
`.agents/handoffs/544-scope/phase2c/shots/`):

- `fig-limit-cycle`: as the approved example; "start inside" by a thin
  leader from its start at the centre, "start outside" above the start of
  its curve, "circle, radius 2√μ" beside the circle's upper right, in
  grey; each name next to its own curve and clear of the other names and
  of the curves.
- `fig-drift`: "proton" and "electron" beside the ends of their paths, on
  their own side of the starting line; three y ticks on the flat
  equal-aspect plot (with five their labels touched).
- `fig-solar-system`: stacked; "Jupiter" inside the top of its orbit,
  "Saturn" above the top of its own, "Sun" beside the dot; clear.
- `fig-airy-rayleigh`: stacked; each separation by a thin leader to a
  point no other curve hides (the two closer pairs from above their peaks,
  the widest pair from the empty space under its dip); no leader crosses
  another curve and no label touches a curve.

**Failed the gate, restored and left out:**

- `fig-pendulum-energy` (`mechanics/06`): four panels in a 2 x 2 grid;
  at R's width the crop is 412 px (8.94 CSS px at 320) and the Runge-Kutta
  panel's offset label (1e-6+9.9999e-1) crowds its title. A grid with
  offset labels is not a tested form.
- `fig-proved-energy-growth` (`lean/01`): the theorem is drawn as white
  dashes inside each simulated line on purpose; the least line contrast is
  1.0:1, under the gate's 3:1 (the cased-line form, untested).
- `fig-plate` (`materials/03`): an equal-aspect plate (4:1) of a
  finite-element field with its colour bar above a line panel; at R's width
  the field becomes a strip about a third of its old size and its x label
  runs into the colour bar (a finite-element field, untested).
- `fig-pythagorean` (`astrophysics/01`, review round 1): two stacked
  panels of paths at equal aspect; the automatic limits followed the new
  panel shape, so the limits differ (the gate requires them identical).

**Captions, alt text and prose.** Eighteen figures are now stacked where
they were side by side: their captions, alt texts and the lesson prose
that named "left" and "right" now say top and bottom (17 lessons); the alt
text of `fig-fem-convergence` names the references as the dotted lines
labelled slope 2 and slope 1 (S4). No displayed excerpt selects lines of a
changed draw function (checked: the `lines=` selections of every lesson).

**P4 record (data, values, axes).** `gate.py` of phase 2b, run on `HEAD`
(0cdde75, a copy of `src`) and on the working tree over the 56 modules of
phase 2c; `.agents/handoffs/544-scope/phase2c/compare.md` and
`phase2c/gate/gate-*.json`.

- `Experiment.results()` identical in all 56 modules.
- Every figure of those modules outside phase 2c's and phase 2b's targets:
  PNG bytes identical. AI6's four model-input pictures: identical.
- Per figure of phase 2c: every line's data, every collection and image,
  the axis scales and the axis-label words identical. The differences, all
  expected: legend entries removed where the series are now named on the
  plot (list B, `fig-separation`, the top panel of `fig-head-on-collision`)
  or by S4 (`fig-particle-gradient`, `fig-fem-convergence`); the lower
  panel of a stacked pair that shared the y axis of its neighbour now names
  it too, with the same words (`fig-same-chirp-mass`, `fig-pythagorean`,
  `fig-fdtd-stability`, `fig-dispersion`, `fig-profiles`, `fig-malus`,
  `fig-fresnel`); line breaks in labels and titles; and
  `fig-pythagorean`'s limits, which Matplotlib sets from the panel's shape
  for equal axes (`adjustable="datalim"`), every point of both stretches
  still inside them.
- Unit tests of the changed modules, the audit, the provenance and the
  excerpts: 349 passed; `tests/unit/test_figure_language.py`: 146 passed
  (the floor, the canvas width, 3:1, at most three entries in a legend
  inside an axes, at most five placed ticks, and the same bytes on every
  draw, for each of the 117 figures of `ROLLOUT` then; 116 since review
  round 1).

**P5 record (status and credit).** No figure of phase 2c declares
provenance (a scripted check of `Experiment.provenance` over the 56
modules: the only declarations are the tsunami map and comparison of
`fluids/10`, whose PNG bytes are identical before and after). No status,
credit, role or PNG record changed.

**Review round 1: `fig-pythagorean` failed the gate.** The gate requires
the same axis limits before and after; the stacked panels of
`fig-pythagorean` keep equal aspect by `adjustable="datalim"`, so
Matplotlib widened the automatic limits to the new panel shape (the P4
record above names it). That is a failed gate, not an expected
difference, so the figure is restored to its old code and alt text and
left out, like the three below; `ROLLOUT` has 116 figures and
`ROLLOUT_LIST_B_AND_TYPES` 88, the test lists it among those left out,
and `docs/authoring.md` names it. Its lesson keeps the stacked
`fig-stability`, so the 17 lessons with stacked figures stay 17. The gate
and payload numbers below were measured over the 89 figures with
`fig-pythagorean`; it now draws its old bytes.

**Gate per figure.** Each of the 89 figures is 389 to 404 CSS px wide and
shows at least 11.08 CSS px at 375 px and 9.09 at 320 px (before: 3.3 to
6.5 at 320 px); the least line contrast of each is 3:1 or more; no
legend inside an axes holds more than three entries. Screenshots before
and after at 1280, 375 and 320 px:
`.agents/handoffs/544-scope/phase2c/shots/png-{before,after}--<module>--<figure>--<width>.png`.
Payload of the 89 figures: 8,222,027 to 8,255,796 bytes (+0.4 %); the
largest is `fig-annulus-mesh` (226 KB), every page far inside its budget.
Rendering is the same work on a smaller canvas; the 56 modules ran in about
the same time before and after (no measurable build-time change).
