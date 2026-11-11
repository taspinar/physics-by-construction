# Plan: dataset lists derived from the cards (Issue #456)

A process improvement tied to the dataset labs, not a roadmap feature
(checked: no roadmap row). Level 2: `src/pbc/data/check.py` and
`data/registry/` are sensitive paths, no protected path is touched, and
`scripts/verify.conf` keeps its `dataset-checks` line unchanged, because the
new checks run inside `python -m pbc.data.check`.

## Design

1. **The card names what the lists carried.** Four fields, validated by
   `validate_card` (`src/pbc/data/card.py`):
   - `reference_module: <name>`, the module `pbc.data.reference.<name>` of the
     reference figure; required of a `go` card.
   - `reference_figure: {status: <figure status>, residuals: <bool>}`, the
     status label the figure carries and the dossier states, and whether the
     figure has a residual panel; required of a `go` card. The card is the
     declaration the figure and the dossier are checked against (three-way).
   - `listing: {name, kind, note?}`, the README row (the display name, the
     kind, an optional note appended to the decision); required of every card
     whose decision is not `survey-only`.
   - `conversions: [{script, input, output, command, note?}]`, optional: the
     one-time conversions of the dataset, each the row of the tools table
     (`tools/datasets/README.md`) and its command block; `script` must exist.
2. **`src/pbc/data/registry.py`** (new) derives everything from the cards:
   `go_cards`, `reference_modules` (the dictionary `__main__.py` kept by
   hand), `import_reference_module`, `check_reference_modules` (a `go` card
   without a module, a module that does not import, or one without
   `make_figure` is a problem; never skipped), the generated regions of the
   two READMEs between `<!-- generated: <name> -->` and
   `<!-- end generated: <name> -->` markers, in alphabetical order of the
   card id, `check_readmes(root)` (a region that differs from the generated
   text is a problem) and `write_readmes(root)`. The CLI
   `python -m pbc.data.registry readme [--write]` prints the diff or writes
   the regions. The 25 ids of the survey of 2026-10-09 are a closed
   historical constant, `SURVEYED`, kept here so that the README's survey
   table and the test share it; no new dataset ever edits it.
3. **`check_repository`** (`src/pbc/data/check.py`) adds the module check,
   the existence of each conversion script, and the README check, so that
   criterion 3 and criterion 4 fail `python -m pbc.data.check`.
4. **The tests parametrize over the cards.** `test_data_plotting.py` (the
   figure status and residuals from `reference_figure`, the dossier's status
   line), `test_data_checks.py` (the network-blocked figure of every `go`
   card; `SURVEYED` imported, `SPIKED` stays: three fixed historical ids),
   `test_data_samples.py` (the panel test over every `go` card: 19 cases
   instead of 7). Cases per dataset do not fall; every assertion stays.
5. **The READMEs.** The two tables and the conversion paragraph of
   `docs/datasets/README.md` and the table and the command blocks of
   `tools/datasets/README.md` become generated regions with the same content,
   in a fixed order. The prose around them is hand-written and names no
   dataset list.
6. **A scratch dataset in a temporary tree** (`tests/integration/
   test_data_lists.py`): a card, a sample, a dossier, a parsing test and a
   stub reference module are added to a temporary repository, the generator
   is run, and the check passes with no edit to an existing file. **Two
   branches** in a temporary git repository each add such a dataset and
   merge without conflict; when two new ids are neighbours in the order, the
   conflict is in a generated region and `--write` resolves it (shown too).
7. **Documentation.** "Adding a dataset" in `docs/datasets/README.md` (the
   new files, the generator, the checks, the merge rule); `docs/authoring.md`
   points there; `docs/project-map.md` names `registry.py`.

## Steps

1. `card.py`: the four fields and their validation; `registry.py`; `check.py`.
2. The 19 `go` cards get `reference_module`, `reference_figure`, `listing`,
   and, where a conversion script exists, `conversions`, with the text of
   today's README cells and command blocks.
3. `__main__.py` builds its choices from `reference_modules()`.
4. The READMEs: generated regions written by `--write`, prose adjusted.
5. The tests of design 4 and 6; `tests/unit/test_data_registry.py` for the
   generator and the failure modes.
6. The documentation of design 7.
7. `uv run python -m pbc.data.check`, the dataset tests, `--only code`,
   `--targeted` (the Issue's instruction: no full run).

## Visual deliverables

Skills: none (no page, diagram, figure or animation is produced; the
reference figures are unchanged and only checked).

## Out of scope

ADR 007 (fields are added; no state or rule of the record changes), the
verification gates and `scripts/verify.conf`, lessons, the content of any
dossier, the survey-only cards (no new field).
