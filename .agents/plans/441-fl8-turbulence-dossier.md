# Plan: F108 phase 1 — the turbulent boundary-layer cards, dossiers, and samples (Issue #441)

Phase 1 only: the cards, the dossiers, the committed samples, their parsing
tests, and the reference figures, towards a `go` judged per dossier (the
owner's approval of 2026-11-09 on the Issue). Phase 2, the FL8 lab, is a later
step and starts only when the owner says so.

The Issue names a pair of records. ADR 007 decision 2 asks for one card per
dataset, and the card has one source, so the pair is two cards, each with its
own dossier, sample, and reference figure:

- `tudelft-turbulent-boundary-layer`: 4TU.ResearchData
  doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1 (Knoop, Hassanein,
  Baars), `PIV.zip` and `PTV.zip`, CC BY 4.0. MAT v5, read in the build by
  `scipy.io.loadmat` (ADR 007 addendum, #417); the eight `EXPparam.mat` files
  committed unchanged.
- `grazing-flow-hwa-benchmark`: Zenodo 15044105 v3 (Moriaux, Zamponi; the
  research called it "VKI"; the record names TU Delft creators and its figure
  files are named "data4VKI"), `HWA_PROFILES_v2.zip` and `BL_PARAMETERS.zip`,
  CC BY 4.0; the 24 CSV files committed unchanged.

## Steps

1. Download and confirm the md5s published by 4TU and Zenodo; read both
   readmes; record their errors (TU Delft: struct layout, PTV y in mm, the
   uv and vv names, the DOI placeholder; grazing flow: `x/L` of the parameter
   files is x in metres, no u_tau, the solid-wall y fitted to canonical
   profiles, the TI bounds).
2. Reference module `src/pbc/data/reference/tudelft_boundary_layer.py`:
   read the MAT files; inner scaling; log-law fit over a stated window and its
   sensitivity to the window; H from the file and recomputed against Blasius
   2.59; Coles–Fernholz u_tau against the file's; PTV against PIV in their
   overlap; Reynolds shear stress plateau. Figure: U+ against y+ with the
   sublayer and the log law; U/U_inf against y/delta with Blasius; -u'v'+.
3. Reference module `src/pbc/data/reference/grazing_flow_hwa.py`: read the
   CSVs; u_tau from Coles–Fernholz Cf(Re_theta) with nu from the recorded
   T and p; U+ against y+ of the solid wall; H of solid and porous walls; TI
   with its bounds. Figure status `processed`.
4. Tests: `tests/unit/test_data_tudelft_boundary_layer.py`,
   `tests/unit/test_data_grazing_flow.py` (parsing, units, checksums, the
   dossier's numbers), `tests/unit/test_data_plotting.py`, and the
   network-blocked list of `tests/integration/test_data_checks.py`.
5. The cards, the dossiers with the ADR 007 checklist, rows in
   `docs/datasets/README.md`, `pbc.data.reference.__main__`.

## Visual deliverables

- Scientific figure: the reference figure of each dataset (status
  `processed`).
  Skills: pbc-scientific-visualization@a70b501
  Validation: the log-law parameters, H, u_tau comparisons and the stress
  plateau asserted by tests. Accessible fallback: the dossiers' tables give
  every plotted number in text.

## Out of scope

The Rostock, Sheffield, and OpenPIV cards (stay `survey-only`), the TU Delft
hot-wire time series (5.9 GB), ADR 007, the card schema, the card-count test,
the lesson page.
