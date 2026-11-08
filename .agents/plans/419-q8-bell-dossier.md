# Plan: F103 phase 1 — the Munich Bell-test card, dossier, and sample (Issue #419)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's decision
of 2026-11-08 on the Issue). Phase 2, the Q8 lab, is a later step.

## Steps

1. Download `Bell_2016-04-15.zip` and `README.txt` of Zenodo 22936124,
   confirm the md5s, inspect the three CSV files and the Readme.
2. Commit the four members unmodified as the sample
   `data/samples/munich-bell-event-ready/` (1.2 MB, within the caps).
3. Reader and reference figure `src/pbc/data/reference/munich_bell.py`:
   the correlators and S per state (Eq. S1 and S2 of the Supplemental),
   pooled, with binomial standard errors; the stopping rule of 5000 events
   per state; the pairing check against the lab files; the maintenance
   exclusions as a sensitivity check.
4. Tests in `tests/unit/test_data_samples.py` (parsing: field names,
   shapes, units, cadence, masks; the reproduction of the published
   correlators and S; the whole archive and the exclusions) and
   `tests/unit/test_data_plotting.py` (status and conventions).
5. The card `data/registry/munich-bell-event-ready.yaml`, the dossier
   `docs/datasets/munich-bell-event-ready.md` with the ADR 007 checklist and
   the loopholes closed and not closed, the row in `docs/datasets/README.md`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (correlators per
  state with standard errors; running S with its band, the bound 2, the
  quantum maximum, the stopping rule). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: the correlators and S equal the PRL's Fig. 3 and text, asserted
  by tests. Accessible fallback: the dossier's caption and table give every
  plotted number in text.

## Out of scope

The card-count test (relaxed by #418), ADR 007, the card schema, any new
state before `go`, the lesson page.
