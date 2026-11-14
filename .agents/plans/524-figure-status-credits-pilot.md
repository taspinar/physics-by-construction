# Plan: Issue #524, F172 — figure status, credits, and portable provenance (pilot)

- Issue: #524 (source: `docs/roadmap.md`, F172; requirements decision 44,
  "Figure status, credits, and portable provenance (V2)";
  `docs/architecture.md`, "Figure provenance off the chart area").
- Branch: `feature/524-figure-status-credits-pilot`; base commit `e7ca8ad`.
- Written by the implementer: no plan existed when the session started.
- Roadmap row checked (owner's rule of 2026-11-07): F172 is present and not
  retired; F173 (the rollout) waits for the owner's decision on this Issue.

## Goal

One validated provenance contract for the page and the exported PNG,
proven on three sample figures, with every other figure byte-identical.

## Samples

| Lesson | Cell | Draw function | Card | Roles |
|---|---|---|---|---|
| AST8 (`astrophysics/09-exoplanet-light-curves`) | `fig-transit-fit` | `draw_transit_fit` | `tess-exoplanet-light-curves` (public domain, MAST) | processed measurement with simulated (fitted) models |
| MAT6 (`materials/05-stress-strain-measurements`) | `fig-stress-strain` | `draw_stress_strain` | `nist-numisheet-dp980` (NIST, 17 U.S.C. 105) | processed measurement only |
| EM (`electromagnetism/08-rlc-circuit-measurements`) | `fig-impedance-fit` | `draw_impedance_fit` | the card of `rlc_circuit.json` (CC BY 4.0, Zenodo) | processed measurement with simulated models: the mixed figure of another course, and the one whose licence requires attribution |

All three are the `lesson.preview` of their lesson.

## Current state (findings)

- Each sample paints `label_status()` (a box "status: processed") and
  `add_credit()` (a wrapped paragraph of four to six lines) into the PNG;
  the caption also opens with the `fig-status` label: two statuses.
- `encode()` writes no metadata (`metadata={"Software": None}`);
  `tests/unit/test_experiment.py::test_the_file_carries_no_metadata`.
- The three lesson tests assert `figure_status(figure) == "processed"`,
  `check_figure(...) == []`, and the `[processed]`/`[simulated]` words of
  the legend entries.
- Pillow (pinned, Matplotlib's PNG writer) writes `metadata` keys as
  `tEXt` (Latin-1) or `iTXt` chunks, in the order given; two encodes give
  the same bytes (prototype).
- Quarto passes the cell's image bytes to `index_files/figure-html/`
  unchanged (ADR 016), so the page's PNG is the experiment's PNG.
- Quarto is not installed in the implementer's environment: no local site
  build; CI builds the site.

## Design

1. **The declaration** (`pbc.data.figure_provenance.FigureProvenance`):
   status, dataset, optional artifact, the statuses the figure combines
   with its measurement (`combines`, for example `("simulated",)`), and a
   processing note (what the lesson's code did, not a credit). The
   experiment declares it: `experiment.figure(label, draw,
   provenance=...)`; only a declared figure opts in.
2. **The card's figure credit** (`rights.figure_credit` of the card):
   `short` (one line, "Data: ..."), `visible` (`required` by the terms,
   `chosen` by the project for clear attribution, or `not-required`) and
   `source` (why, from the rights). The per-card
   rights check (`validate_card` and `figure_provenance.check_card`): the
   short credit starts with "Data: ", is at most 100 characters, names no
   ownership; a CC BY licence needs `visible: required`; the publication
   and attribution answers are `permitted`.
3. **The PNG** (`encode(draw, metadata=None)`): without metadata, the
   code path and bytes are unchanged. With a declaration,
   `Experiment.png()` passes deterministic text chunks built from the
   declaration and the card: `Title` (identity), `Description` (status
   sentence and short credit), `Source` (DOI or URL), and the
   machine-readable `pbc:figure`, `pbc:status`, `pbc:combines`,
   `pbc:dataset`, `pbc:artifact`, `pbc:licence`, `pbc:credit`,
   `pbc:attribution`, `pbc:processing`, `pbc:schema`. No `Author`,
   `Copyright`, date, or software version. A card with `visible:
   required` or `chosen` gets a one-line credit painted under the axes by `encode()`, from the
   card (never by the draw function); the visualization credit
   ("Visualization: Physics by Construction · Data: ...") is
   `VISUALIZATION_CREDIT`, on since the owner's choice of 2026-11-14 (see
   "Owner's decision" below).
   ADR 016 decision 2 says "no metadata" for the deterministic figure
   output of ADR 002; at the owner's request (design review of
   2026-11-14) an addendum to that decision allows the one exception: a
   fixed, deterministic provenance record for declared figures, with no
   timestamps and no machine-dependent fields, every other figure
   unchanged. `docs/architecture.md` and `docs/authoring.md` say the
   same.
4. **The page**: the cell keeps `fig-status` and `fig-dataset`; a new
   post-render step `site/figure-credits.py` reads the PNG of every
   figure, and for a PNG that carries `pbc:` metadata it requires that the
   caption's status and dataset equal it (the build fails otherwise),
   adds after the status label "with simulated models" when the figure
   combines statuses, and appends to the caption the short credit and a
   native closed `<details>` with the full attribution, licence, source
   link, and processing, all from the card through
   `figure_provenance.caption_html`. Pages without such a PNG are not
   touched. No change to `site/_filters/lesson.lua`.
5. **Checks** (equally strong or stronger):
   - `check_figure(fig, residuals=..., declared=status)`: for a declared
     figure the painted status must be absent (one status) and the
     declared one valid; the painted credit paragraph is absent; every
     other rule (units, titles, legend, residual panel, false colour)
     unchanged. Without `declared` the function is unchanged.
   - `figure_provenance.check_roles(fig, provenance)`: every legend entry
     carries a role (`role(artist, status)`), the roles equal
     `{status} | combines`, a simulated role is never drawn as a solid
     line: replaces the words "[processed]"/"[simulated]" of the legend
     text, which the shorter labels drop.
   - `figure_provenance.check_png(png, provenance, card, identity)`: the
     metadata equals what the declaration and the card give; no ownership
     wording; a required visible credit is declared.
   - The lesson source check: a cell whose experiment figure is declared
     has the same `fig-status` and `fig-dataset`.
   - The built-site check: every figure whose PNG carries `pbc:` metadata
     has its caption status, combined statuses, and credit as the card
     and the metadata give; every page PNG without metadata is untouched.
6. **The samples**: no `label_status`/`add_credit`; shorter legend
   entries (the status words move to the roles and the caption); legend
   and titles kept; no display thinning (all cadences and rows drawn).

## Risk classification

**Level 3.** Triggers: existing test assertions change (the status and
legend assertions of the three lesson tests and of
`tests/unit/test_experiment.py`, migrated to stronger ones; Issue comment
of the owner); the published figures of three lessons change (a changed
published figure, not a changed claim). Paths: `src/pbc/experiment.py`
and `src/pbc/data/plotting.py` (shared inputs: the targeted run reports a
full run), `site/_quarto.yml` (sensitive), `data/registry` (sensitive),
`docs/architecture.md` (sensitive). No protected path. The session runs
`--targeted`/`--only` and pytest on its files (owner's rule of
2026-11-08); `review-feature.sh` runs the full verification of the final
tree, and a full review follows it.

| Criterion | Gate |
|---|---|
| 1 Before/after evidence, desktop, phone, exported PNG | implementation |
| 2 One documented, validated strategy; metadata consistent with the card; deterministic; page = experiment bytes | implementation |
| 3 Checks equal or stronger; no attribution lost; no ownership wording | implementation |
| 4 Opt-in only; every other PNG byte-identical; AI6 unchanged | implementation (unit evidence) and pr_ci (the full run's comparisons) |
| 5 Owner's branding choice and the F173 decision recorded on the Issue | owner_approval |
| 6 Verification tier passes, run last | pr_ci (the full run after the session) |

## Visual deliverables and skills

Scientific figures (the three samples) and their caption presentation.

Skills: pbc-scientific-visualization

Skills: none (pbc-physics-teaching is not applicable: no lesson's teaching, prose, or caption text changes; the displayed draw_ excerpts change only by the role calls and shorter legend labels)

Expected artifacts: the three PNGs without painted status, with the
declared metadata; the captions with one status and a short credit.
Scientific validation: the same data and models, all records drawn, the
roles checked per artist. Accessible fallback: the caption text and
`<details>` are HTML text; `fig-alt` unchanged. Exception to the skill:
its line "the card's attribution on the figure (`add_credit`)" is
superseded for the declared figures by the architecture's contract (the
rule wins, as the skill says).

## Steps

1. `src/pbc/data/figure_provenance.py` and its unit tests.
2. `encode(..., metadata=)`, `Experiment.figure(..., provenance=)` and
   their tests; the no-metadata test kept for undeclared figures.
3. `check_figure(declared=)` and tests in `tests/unit/test_data_plotting.py`.
4. The three cards' `rights.figure_credit`; `validate_card` reads it.
5. The three draw functions and their experiments; their tests migrated.
6. `site/figure-credits.py`, `site/_quarto.yml`, `site/assets/site.css`;
   the built-site check and its unit test.
7. The lesson source check of the declaration.
8. Docs: `docs/architecture.md` (the delivered pilot), `docs/authoring.md`
   (declaring a figure's provenance).
9. Evidence (see "Evidence" below; the images in the ignored
   `.agents/handoffs/524-evidence/`, since the lesson checks allow no
   committed image outside `site/assets/`): before (from the
   published site) and after PNGs, with and without the visualization
   credit, caption renderings at 1280 and 390 px, digests and sizes.
10. `./scripts/verify.sh --targeted` (it reports the full run), pytest of
    the changed files, `--only` groups that can run here.

## Evidence (acceptance criterion 1; recorded 2026-11-14)

Images, in the ignored `.agents/handoffs/524-evidence/` of the worktree
(regenerate the exports with `uv run python -m pbc.data.figure_provenance
examples <directory>`; the "before" exports are the published site's PNGs
from `main` at `e7ca8ad`): per sample, the before and after export, the
export without the visualization credit, and the figure with its caption in
the published page at 1280 and 390 CSS px, before and after (after: the
branch's PNG, the caption completed by `annotate`, the branch's CSS; not a
Quarto build, which is not installed here).

| Figure | Before export | After export (with the visualization credit) | Without visualization credit |
|---|---|---|---|
| `fig-transit-fit` | 1253 x 1140 px, 193,422 B | 1259 x 1162 px, 143,868 B | 1259 x 1162 px, 141,251 B |
| `fig-stress-strain` | 1367 x 950 px, 154,047 B | 1374 x 970 px, 112,806 B | 1374 x 970 px, 110,326 B |
| `fig-impedance-fit` | 1253 x 1368 px, 211,477 B | 1259 x 1393 px, 179,126 B | 1259 x 1393 px, 177,092 B |

- Chart area: no status box, no credit paragraph; shorter legend entries
  (status words moved to the caption and to roles on the artists); titles,
  axes, units, uncertainty, residual panels, and every record unchanged; no
  display thinning. One small line under the axes: "Visualization:
  Physics by Construction · Data: ..." on MAT6 and the RLC figure (their
  cards require the data credit) and "Visualization: Physics by
  Construction · Data: NASA TESS / MAST" on AST8 (public domain; the
  owner's choice of the design review, `visible: chosen`).
- Caption: one status label, "with simulated models" for AST8 and RLC, the
  short credit, a closed "Full provenance" disclosure (attribution,
  licence, DOI link, processing, the line on the image, figure identity).
- Size: 15 to 27 per cent smaller. Determinism: two encodes equal; the
  experiment's file equals the page's (`assert_declared`).
- Other figures: every figure of AST8, MAT6, the RLC lab, AI6 (four
  model-input pictures and the readings figure) and M1, drawn from `main`
  at `e7ca8ad` and from this branch on the same machine: 14 of 17
  byte-identical, the 3 that differ are the samples.
- Phone (390 px): the caption wraps and stays readable; legends and tick
  labels of all three figures are small before and after (F170's scope).

## Owner's decision (2026-11-14)

The owner chose the credit in the comment on Issue #524: **with subtle
branding.** Every declared figure carries the small line "Visualization:
Physics by Construction" under the figure, outside the plot area, so that
a downloaded or shared image still shows where the visualization comes
from. Where the card requires a visible dataset credit (MAT6, the RLC lab)
the two are one line, "Visualization: Physics by Construction · Data: …";
the public-domain TESS figure showed the branding alone until the design
review below added its data source. Implemented as
`VISUALIZATION_CREDIT = True` and `visible_credit()`: the type size (7 pt)
and grey (0.25) of the figure credits, no box or logo. The PNG record's
`pbc:visible-credit` is the painted line; the caption's "Full provenance"
names it ("On the image"); the post-render step and the built-site check
`check_figure_credits` fail when the record's line is not the one the card
gives. The decision on the rollout (F173) is still the owner's.

## Owner's design review (2026-11-14)

The owner's design review of #526 at 640e4c2 (comment on Issue #524)
keeps the design and asks for three refinements, made on this branch:

1. **AST8 names its data source visibly.** The TESS card's short credit is
   "Data: NASA TESS / MAST" with `visible: chosen` (a new value: the
   terms do not require it, the project shows it for clear scientific
   attribution when a screenshot or re-export loses the metadata); the
   line is "Visualization: Physics by Construction · Data: NASA TESS /
   MAST", and the PNG record, the caption, and the tests follow.
2. **ADR 016 addendum** to decision 2 (dated, naming #524): the fixed,
   deterministic provenance record of declared figures is the one
   exception to "no metadata"; no timestamps or machine-dependent fields;
   every other figure unchanged. `docs/architecture.md` and
   `docs/authoring.md` agree.
3. **The branding, precisely.** `VISUALIZATION_CREDIT = True` is a
   constant, not a per-figure choice: it applies to every declared
   figure, which in this pilot are its three (AST8, MAT6, the RLC lab);
   an undeclared figure has no line; any further rollout goes through
   F173. No settings mechanism. The architecture's sentence on a
   "mandatory brand" now forbids a brand on a figure the owner's decision
   does not cover.

The chart size is unchanged; a barely readable line on a phone is
acceptable while the caption's credit stays readable; the RLC legends are
F170's.

## Owner's approval of the digest change (2026-11-14)

`tests/integration/test_lesson_digest.py::test_the_tools_of_the_data_package_are_those_of_the_data_use_analysis`
requires the digest's `_DATA_TOOLS` to equal `TOOLS` of
`tests/support/data_use.py`, which lists `pbc.data.figure_provenance` (a
module that reads no data). The owner approved on Issue #524 ("Ja dat
mag", 2026-11-14) adding `figure_provenance` to `_DATA_TOOLS` in the
protected `src/pbc/authoring/digest.py`; the change is that one line.

## Reproduction fix (2026-11-14)

The full run of 03fc080 failed the e2e reproduction check for the three
declared figures: run as `python -m <module> results`, Python names the
experiment's module `__main__`, so the record's `pbc:figure` read
`__main__:<label>` and the learner's PNG differed from the page's.
`Experiment.identity` now names the module by its import name (the
`__spec__` of the draw function's module), and
`tests/unit/test_figure_provenance.py::test_the_program_writes_the_pages_declared_png_byte_for_byte`
runs the RLC experiment as a program and compares its PNG with the page's
byte for byte. It fails without the fix. Running AST8 and MAT6 the same way gives the page's
bytes.

## Open questions

- The decision on the rollout (F173), part of AC 5.

## Next action

Implement steps 1 to 10.
