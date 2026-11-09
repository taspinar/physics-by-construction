# Plan: F84 phase 1 — the DWD Potsdam soil-temperature card, dossier, and sample (Issue #438)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's decision
of 2026-11-08 on the Issue). Phase 2, the T7 lab, is a later step.

## Steps

1. Download `stundenwerte_EB_03987_19510101_20251231_hist.zip` from DWD's
   CDC open-data area, confirm the sha256 of the research
   (`6a968e6d...`), inspect the product file and the metadata files.
2. A checksum-pinned extraction script `tools/datasets/dwd_soil_extract.py`
   (standard library only) writing lines of the product file unchanged:
   the rows at 00, 06, 12, 18 h of 2015–2024 (annual wave) and every hourly
   row of June–August 2020–2024 (diurnal wave), each with the header line;
   plus four small metadata files copied unchanged (station geography,
   instruments, parameters, operator). Sample about 1.9 MB, within the caps.
3. Reader and reference figure `src/pbc/data/reference/dwd_soil.py`: the
   annual and diurnal harmonics per depth by least squares, the damping
   depth from the amplitude decay and from the phase lag of the
   heat-equation solution for a periodic surface temperature, the
   diffusivity per year and per summer, mean and standard error across
   them; pairwise depth estimates as a check of homogeneity.
4. Tests `tests/unit/test_data_dwd_soil.py` (parsing: field names, shapes,
   units, cadence, masks, coverage; the extraction script on a small zip
   written by the test; the damped-wave solution against the FTCS scheme of
   T6 `pbc.thermodynamics.conduction`; the dossier's numbers), and the
   rows of `tests/unit/test_data_plotting.py` and
   `tests/integration/test_data_checks.py`.
5. The card `data/registry/dwd-potsdam-soil-temperature.yaml`, the dossier
   `docs/datasets/dwd-potsdam-soil-temperature.md` with the ADR 007
   checklist, the rows in `docs/datasets/README.md` and
   `tools/datasets/README.md`, the module entry in
   `pbc.data.reference.__main__`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (6-hourly
  temperatures at five depths; annual amplitude and phase against depth
  with the fitted lines and residuals; a summer week hourly; diurnal
  amplitude and phase against depth). Status `processed` (rows selected,
  harmonics fitted).
  Skills: pbc-scientific-visualization@a70b501
  Validation: the diffusivities agree with the research's round-3 numbers
  in order of magnitude and with each other within the stated spread; the
  damped-wave formula is checked against the T6 FTCS scheme; numbers
  asserted by tests. Accessible fallback: the dossier's caption and tables
  give every plotted number in text.

## Out of scope

ADR 007, the card schema, any new state before `go`, the lesson page, the
runner-up KIT dataset.
