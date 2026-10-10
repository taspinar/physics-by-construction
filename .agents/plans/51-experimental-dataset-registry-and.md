# Plan: F50 experimental dataset registry and feasibility gate (Issue #51)

Source: Issue #51, ADR 007, docs/architecture.md "Measured-data lab", Section 8
and Appendix A of docs/changes/physics-next-phase.md.

## Layout
- `src/pbc/data/`: `card.py` (schema and validation: plain
  checks that return messages), `check.py` (the dataset check, `python -m
  pbc.data.check`, the `dataset-checks` entry of `scripts/verify.conf`), readers
  `gwosc.py`, `touchstone.py`, `flume.py`, and `reference/<dataset>.py` with
  `make_figure(data_dir)`; `python -m pbc.data.reference <dataset>` renders one.
- `data/registry/*.yaml`: 25 cards. Three spiked (full cards, dossier, samples);
  22 `survey-only` with `decision.gate`.
- `data/samples/<dataset>/`: GW150914 H1 and L1 text strain (2.5 MB), four NPL
  S2P files (230 KB), flume WC1 gauge 5 up to 30 s (480 KB).
- `scripts/fetch-data.sh`: reads `python -m pbc.data.card downloads <id>`, curl
  one file at a time, pause, digest check; refuses with `CI` set.
- `docs/datasets/`: three dossiers and `README.md` (table, recommendation).
- `docs/authoring.md` "Measured data"; architecture and project-map updated.

## Decisions taken
- Samples need `decision: go`, a licence in CC0-1.0, CC-BY-4.0, or
  equivalent-permission, and `redistribution_of_subsets: permitted`.
- GW150914 uses the plain-text product (Issue allows it): no HDF5 dependency.
- Touchstone: an in-repository parser, no dependency. Deviation from the Issue's
  wording ("ordinary locked dependencies"); recorded in the dossier and the
  architecture. Reason: no licence or lock to maintain; F51 may replace it.
- Flume archive read with csv and NumPy; sample cell text copied unchanged.
- Criterion 2: a test that runs the whole of `./scripts/verify.sh` would
  recurse (verify runs the tests). Equivalent guard instead, in
  `tests/integration/test_data_checks.py`: the check, the readers, and the
  figures run with socket connects refused; `pbc.data` imports no network
  module; no lesson, library, or verification file names a portal or
  `fetch-data`; the script refuses in CI.
- `scripts/fetch-data.sh` stays guarded by `scripts/verify-workflow.conf`:
  `tests/lib-fakes.sh` copies `scripts/*.sh` into its fake repositories, so a
  self-test does copy it (ADR 005 decision 4 forbids excluding it then).

## Spike method (each dataset)
Download the real file, check the host digest, inspect, label artifacts, write
the figure code, add a physical consistency test (strain: matched-filter chirp
mass, delay, noise control; S-parameters: passivity, reciprocity, pad order,
two instruments; flume: wave period, windowed RMS), read the rights, measure
runtime and memory, write the dossier.

## Evidence limits
The source paper of the flume and the ARFTG paper of the S-parameters were not
read; the dossiers say what a lesson must still read.
