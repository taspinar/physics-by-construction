# Plan: F83 phase 1 — the Xu damped-pendulum card, dossier, and sample (Issue #437)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's decision
of 2026-11-08 on the Issue). Phase 2, the M15 lab, is a later step.

## Steps

1. Download from GitHub `EnzeXu/Damped_Pendulum_Dataset` at commit
   `cbf82673641ecd65e902ad5c38a048387649a2a0` the raw and cleaned files,
   `pendulum_length.json`, `process.py`, `column_names.py`, the README and the
   LICENSE; confirm each file's Git blob SHA-1 against the commit's tree;
   inspect them (schema, units, encoder step, cadence, empty cells, the
   cleaning window).
2. Commit as the sample `data/samples/xu-damped-pendulum/`, unmodified: the
   raw first trial in air of each of the five lengths
   (`raw_data/len<k>_cond1_1.csv`, about 1.6 MB, so that the period can be
   compared with the stated lengths), the cleaned `cleaned_data/len1_cond1_1.csv`
   (the file the README plots), `pendulum_length.json`, and the Apache-2.0
   `LICENSE` (section 4(a) asks that a copy travels with the files). The
   README is not committed; the card and dossier record what it says.
3. Reader and reference figure `src/pbc/data/reference/xu_pendulum.py`: the
   raw and cleaned readers, the cycle periods from interpolated crossings of
   the centre, the large-amplitude correction with the complete elliptic
   integral, the exponential amplitude envelope, the effective length
   `g T0^2 / (4 pi^2)` per length and a straight-line fit of `T0^2` against
   the stated length.
4. Tests `tests/unit/test_data_xu_pendulum.py` (parsing: fields, shapes,
   units, encoder step, cadence, empty cells; the cleaned file is the raw
   window 5 to 65 s; the angular velocity is the software's derivative of the
   angle; the dossier's numbers), and the parametrised figure tests of
   `tests/unit/test_data_plotting.py`, `tests/unit/test_data_samples.py`, and
   `tests/integration/test_data_checks.py`.
5. The card `data/registry/xu-damped-pendulum.yaml` (licence recorded as
   `equivalent-permission`, Apache-2.0 named, per the ADR 007 addendum), the
   dossier `docs/datasets/xu-damped-pendulum.md` with the ADR 007 checklist
   and what the data can say about the undefined length L, the row in
   `docs/datasets/README.md`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (raw angle of the
  shortest pendulum with its fitted envelope; the period per cycle against
  amplitude, raw and corrected, with 2π√(L/g) of the stated L; T0² against
  the stated length with the line 4π²L/g and the fitted line; the residual of
  the simple-pendulum model as L_eff − L). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: every plotted number is computed by the module and asserted by
  tests; the elliptic correction is checked against the series expansion.
  Accessible fallback: the dossier's caption and tables give every plotted
  number in text.

## Out of scope

ADR 007, the card schema, the dataset check, any new state before `go`, the
other 40 files of the record (phase 2 decides), the lesson page.
