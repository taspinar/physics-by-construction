# Plan: F52 phase 1 — the Lycopodium diffraction card, dossier, and sample (Issue #440)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's decision
of 2026-11-08 on the Issue). Phase 2, the W7 lab, is a later step.

## Steps

1. Download from Zenodo 15846643 the two intensity-profile XLSX files and the
   morphometry CSVs at x160 and x80; confirm the md5s of the record; read the
   record's description and the companion article's landing page (paywalled:
   no screen distance, no image scale).
2. Conversion (ADR 007 addendum, #417): `tools/datasets/lycopodium_xlsx_to_csv.py`,
   standard library only (zip + XML), input sha256 pinned, every row and
   column unchanged; outputs `profile_633nm.csv` and `profile_405nm.csv`.
   The two morphometry CSVs are committed unmodified (the record's bytes).
3. Reader and reference figure `src/pbc/data/reference/lycopodium.py`:
   - microscope diameters of whole spores (d > 15 um) at both magnifications;
   - the dark ring of each profile: centre by mirror symmetry, the profile
     folded, the most prominent minimum outside the saturated core; the
     sensitivity to the smoothing width as its uncertainty;
   - the scale-free test: ratio of the dark-ring radii against the
     wavelength ratio 0.640; the polydisperse Airy model of the measured
     diameters for the ring positions; the ring order (first or second
     minimum) reported as not settled by the record; the implied screen
     distance in the profile's (undocumented) unit for both orders.
4. Tests `tests/unit/test_data_lycopodium.py` (parsing: field names, shapes,
   units, cadence, masks; the numbers of the dossier; the converter on an
   XLSX the test writes), `tests/unit/test_data_plotting.py` (status and
   conventions), the network-blocked list of `tests/integration/test_data_checks.py`.
5. The card `data/registry/lycopodium-spore-diffraction.yaml`, the dossier
   `docs/datasets/lycopodium-spore-diffraction.md` with the ADR 007
   checklist, rows in `docs/datasets/README.md` and `tools/datasets/README.md`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (the two measured
  profiles with their dark rings; the folded profiles against radius over
  wavelength; the microscope diameters; ring radius against wavelength with
  the proportional model). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: ring radii, ratio, diameters, and the model ring positions
  asserted by tests. Accessible fallback: the dossier's caption and tables
  give every plotted number in text.

## Out of scope

The Fraunhofer microstructure card (stays `survey-only`), ADR 007, the card
schema, the card-count test, any new state before `go`, the lesson page.
