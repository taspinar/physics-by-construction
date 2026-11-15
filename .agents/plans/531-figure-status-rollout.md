# Plan: Issue #531, F173 — figure status and credit rollout

- Issue: #531 (source: `docs/roadmap.md`, F173; requirements decision 44,
  I37; `docs/architecture.md`, "Figure provenance off the chart area").
- Branch: `feature/531-figure-status-rollout`; base commit `e4b5b8c`.
- Written by the implementer: no plan existed when the session started.
- Gate: the owner's decision of 2026-11-14 on #524 ("Ja, naar alle
  figuren uitrollen"): status, credits, portable provenance and the subtle
  branding on every figure. F170 (#525) and F175 (#530) are merged.
- Coordination (owner, 2026-11-15): stay out of the excerpt display
  (`src/pbc/authoring/` beyond the figure-credit module, #536) and of MAT6's
  prose (#535); no restyling beyond what status, credit, provenance and
  branding need (F171 is undecided).

## Goal

The contract of the pilot F172 on every figure that paints a status or a
credit: the lesson figures that declare a dataset, the two simulated
figures that paint a status (M12's), and the reference
figures of the dataset cards (`make_figure`). AI6's model-input picture
stays byte-identical.

## Inventory (at `e4b5b8c`)

- 59 lesson figure cells name a dataset (`fig-dataset` or `fig-model-of`)
  in 18 lessons; 3 are the pilot's. One of the rest is AI6's
  `fig-picture-d` (excluded, below). The other 55 are declared by this
  feature, among them `fig-halo-model` (W9, `fig-model-of`, simulated) and
  `fig-tsunami-map` (FL10, simulated, `modelled-reference`).
- M12's `fig-profiles` and `fig-residuals` (`inverse_physics`, simulated,
  no dataset) paint a status; they stop painting and keep their caption
  status. They declare nothing (no card).
- 20 go cards, each with a reference module whose `make_figure` paints
  `label_status` and (19 of 20) `add_credit` with a hand-written string;
  `python -m pbc.data.reference` writes it with `savefig` (no page shows it).
- 17 go cards lack `rights.figure_credit`.

## Design (extends F172; nothing of the pilot is weakened)

1. **Declarations of simulated figures with a dataset.**
   `FigureProvenance.status` may be `simulated` where the card allows it
   for the artifact (`modelled-reference`), and `model_of=True` declares a
   `fig-model-of` figure (status `simulated`, no artifact). The record of a
   model-of figure writes `pbc:dataset` empty and adds `pbc:model-of` (the
   card); every other record is unchanged (the pilot's bytes stay).
   The caption check compares `data-model-of` too.
2. **Roles.** `check_roles` counts a role on any drawn artist of a panel
   (lines, collections, images, patches, containers) as drawn, so a figure
   without a legend (an image, a spectrogram, one series) is checked too;
   every legend entry still needs a declared role. The rule "a model is
   never a solid line" applies where the figure holds a measurement (as
   in the pilot, whose figures all do); a simulated figure may draw its
   simulation solid.
2a. **Discovered while rolling out** (2026-11-15). Further datasets:
   `also=(...)` names the further cards a figure draws data from (FL9's
   Strouhal figure, FL8's three figures draw two CC BY cards); their
   short credits are painted on a second line, carried as `pbc:also*`
   keys of the record (only when present), and shown at the caption with
   their full attribution, so no required attribution is lost. A role
   `REFERENCE` marks a fixed or published value (bound, limit, certified
   value, threshold, rule line), free of the style rules. The style rules
   hold within a panel. A provider's own copyright notice in its card's
   attribution (trackpy's CC BY 3.0) is not ownership wording; any other
   copyright mark still is.
3. **Cards.** Every go card has `rights.figure_credit` (now required by
   `validate_card` for a go card). CC BY cards (and trackpy's CC BY 3.0
   sample) `required`, naming the licence; NIST (fair-use acknowledgement)
   and Xu (Apache-2.0 notice) `required`; public-domain or permission cards
   (SDSS, SPARC, NOAA/USGS) `chosen`, the owner's reason for TESS.
   Each `source` says why, from the card's terms.
4. **Lesson figures.** Every dataset figure of every experiment (except
   AI6's) is passed with `provenance=`; its draw function paints neither
   `label_status` nor `add_credit`; the status words of legend entries
   ("[processed]") move to roles; the hand-written `CREDIT` strings that
   only fed `add_credit` are removed. Lesson tests use
   `support.figures.assert_declared` (status, conventions, roles, record,
   bytes, painted line).
5. **Reference figures.** Each reference module declares
   `REFERENCE = FigureProvenance(...)` (status = card's
   `reference_figure.status`); `make_figure` paints nothing;
   `pbc.data.reference` writes the PNG through `encode` with the record and
   the line, identity `pbc.data.reference.<module>:reference-figure`.
   `tests/unit/test_data_plotting.py` checks each with `check_figure(...,
   declared=)`, `check_roles`, `check_png`, and the card's status.
6. **AI6.** `pbc.agents.multimodal_lab.draw_strain` paints the status and
   credit itself, exactly as M11's draw function did, so picture D and the
   replay fixtures are byte-identical; a test pins the picture's digest.
   `label_status`/`add_credit` remain for that input only.
7. **Docs.** `docs/architecture.md` and `docs/authoring.md`: the rollout
   delivered, the AI6 exception; the skill's `add_credit` line is
   superseded as in the pilot.

## Risk classification

**Level 3.** Triggers: existing test assertions change (lesson tests,
reference-figure tests); the published figures of 17 lessons change (a
changed published figure). Paths: shared figure code and checks
(`src/pbc/experiment.py` is not changed; `src/pbc/data/*`,
`tests/support/*`), `data/registry` (sensitive), `docs/architecture.md`.
The session runs `--targeted`/`--only` and pytest (owner's rule of
2026-11-08); `review-feature.sh` runs the full verification.

| Criterion | Gate |
|---|---|
| 1 One status, card credit, portable PNG, no attribution lost | implementation |
| 2 Checks equal or stronger, reference-figure tests included | implementation |
| 3 Full run passes; deterministic; page = experiment bytes | pr_ci (the full run after the session) |
| 4 AI6 fixtures byte-identical | implementation |

## Visual deliverables and skills

Scientific figures (every dataset figure and reference figure) and their
caption presentation.

Skills: pbc-scientific-visualization

Skills: none (pbc-physics-teaching is not applicable: no lesson's teaching, prose, or caption text changes; displayed draw_ excerpts change only by role calls and shorter legend labels)

Expected artifacts: PNGs without a painted status, with the declared
record and one line of credit; captions with one status and the card's
short credit. Scientific validation: same data and models, every record
drawn, roles checked per artist. Accessible fallback: caption text and
`<details>` are HTML; `fig-alt` unchanged. Exception to the skill: its
line "the card's attribution on the figure (`add_credit`)" is superseded
by the architecture's contract (the rule wins, as the skill says).

## Steps

1. `figure_provenance`: simulated and model-of declarations, roles on any
   artist; `figure_credits`, the site and lesson source checks for
   `fig-model-of`; unit tests.
2. Cards: `figure_credit` on every go card; required for a go card.
3. Lesson experiments and their tests, course by course.
4. Reference modules, `pbc.data.reference`, the reference-figure tests.
5. AI6 picture D frozen; its digest test.
6. Docs.
7. Evidence: digests of every figure before and after; AI6 identical.
8. `./scripts/verify.sh --targeted`, pytest of the changed files.
