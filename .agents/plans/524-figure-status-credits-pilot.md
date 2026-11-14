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
   `short` (one line, "Data: ..."), `visible` (`required` or
   `not-required`) and `source` (why, from the rights). The per-card
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
   `Copyright`, date, or software version. A card with `visible: required`
   gets a one-line credit painted under the axes by `encode()`, from the
   card (never by the draw function); the optional visualization credit
   ("Visualization: Physics by Construction · Data: ...") is a flag of
   `encode()`, off until the owner chooses (`VISUALIZATION_CREDIT`).
   ADR 016 decision 2 says "no metadata" for the deterministic figure
   output of ADR 002; the metadata here is deterministic and written by
   the one encoder, as the architecture's contract and requirements
   decision 44 require. Surfaced for the owner, not changed.
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
example with the visualization credit, and the figure with its caption in
the published page at 1280 and 390 CSS px, before and after (after: the
branch's PNG, the caption completed by `annotate`, the branch's CSS; not a
Quarto build, which is not installed here).

| Figure | Before export | After export | With visualization credit |
|---|---|---|---|
| `fig-transit-fit` | 1253 x 1140 px, 193,422 B | 1251 x 1135 px, 138,134 B | 1259 x 1162 px, 147,525 B |
| `fig-stress-strain` | 1367 x 950 px, 154,047 B | 1374 x 970 px, 110,326 B | 1374 x 970 px, 112,806 B |
| `fig-impedance-fit` | 1253 x 1368 px, 211,477 B | 1259 x 1393 px, 177,092 B | 1259 x 1393 px, 179,126 B |

- Chart area: no status box, no credit paragraph; shorter legend entries
  (status words moved to the caption and to roles on the artists); titles,
  axes, units, uncertainty, residual panels, and every record unchanged; no
  display thinning. MAT6 and the RLC figure carry one line of credit under
  the axes (their cards require it); AST8 none (public domain).
- Caption: one status label, "with simulated models" for AST8 and RLC, the
  short credit, a closed "Full provenance" disclosure (attribution,
  licence, DOI link, processing, figure identity).
- Size: 16 to 29 per cent smaller. Determinism: two encodes equal; the
  experiment's file equals the page's (`assert_declared`).
- Other figures: every figure of AST8, MAT6, the RLC lab, AI6 (four
  model-input pictures and the readings figure) and M1, drawn from `main`
  at `e7ca8ad` and from this branch on the same machine: 14 of 17
  byte-identical, the 3 that differ are the samples.
- Phone (390 px): the caption wraps and stays readable; legends and tick
  labels of all three figures are small before and after (F170's scope).

## Open questions

- The owner's branding choice (AC 5), on the examples of step 9.
- ADR 016 decision 2, "no metadata": read as the deterministic output of
  ADR 002; an addendum is the owner's choice.

## Next action

Implement steps 1 to 10.
