# Plan: F106 phase 1 — the NIST SRM 660c (LaB6) card, dossier, and sample (Issue #443)

Phase 1 only: the card, the dossier, the committed sample, its parsing test,
and the reference figure, towards a `go` judged per dossier (owner's approval
of 2026-11-09 on the Issue). Phase 2, the MAT5 lab, is a later step that
starts only after a `go` and the owner's word.

## Steps

1. Download from NIST record mds2-2315 (doi 10.18434/mds2-2315) the zip
   `srm_660c_cifs_20201029_081700.zip` and confirm its sha256 against the
   record; read the record's metadata (licence field, description) and the
   SRM 660c certificate (certified a, its temperature and U, the Cu Kα1
   wavelength of Table 1, the 24 reflections, the 20 specimens).
2. Conversion (ADR 007 addendum, #417): `tools/datasets/srm660c_cif_to_csv.py`,
   standard library only, the zip's sha256 pinned; for each of the 20 CIFs
   the measured block (2θ, intensity, weight) and NIST's calculated pattern
   on the same 2θ grid, tokens copied unchanged, into one CSV per specimen,
   plus `specimens.csv` with the per-specimen items of the CIF (temperature,
   specimen displacement, NIST's refined a).
3. Reader and reference figure `src/pbc/data/reference/srm660c.py`:
   - the 24 scan windows, each one reflection (hkl) of Pm-3m;
   - per window a Kα1/Kα2 pseudo-Voigt doublet on a linear background,
     weighted by the file's weights; the Kα2/Kα1 wavelength ratio and
     intensity ratio from the resolved doublets (2θ > 94°);
   - d = λ/(2 sin θ) with the certificate's λ(Cu Kα1), a = d √(h²+k²+l²);
   - the Nelson–Riley extrapolation over the reflections above 2θ = 60°;
   - the same method on NIST's calculated pattern, whose a is known (the
     CIF), so the method's bias is measured, not assumed;
   - per-specimen spread (20 specimens) as the repeatability.
4. Tests `tests/unit/test_data_srm660c.py` (parsing: field names, shapes,
   units, the windows, cadence, masks; the numbers of the dossier; the
   converter on a zip the test writes), `tests/unit/test_data_plotting.py`
   (status and conventions), the network-blocked list of
   `tests/integration/test_data_checks.py`, the CLI map in
   `src/pbc/data/reference/__main__.py`.
5. The card `data/registry/nist-srm660c-lab6.yaml`, the dossier
   `docs/datasets/nist-srm660c-lab6.md` with the ADR 007 checklist, rows in
   `docs/datasets/README.md` and `tools/datasets/README.md` (the research
   note `docs/datasets/spike-candidates-2026-11-08.md` stays as it is: its
   MAT5 round-3 numbers, 4.156498 Å with SD 0.000012 by a weighted fit, agree
   with the dossier's to 3 ppm and need no correction).

## Discoveries during the work

- The Nelson-Riley fit is unweighted over the 18 reflections above 60°,
  so the measurement and NIST's model are treated identically (the
  prototype's weighted fit gave 4.156491 against 4.156485).
- The per-reflection spread between specimens is the specimen
  displacement (slope against the CIF's displacement: correlation 0.9996);
  the figure shows one specimen's points and all 20 lines instead of a
  mean with an SD.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (one specimen's
  24 windows; one high-angle reflection with the doublet fit, NIST's model,
  and the residuals; a(hkl) against the Nelson–Riley function for the
  measurement and for NIST's model with their extrapolations; a per
  specimen against the certified and NIST's in-file values). Status
  `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: the peak positions against the certificate's Table 1, a, its
  spread, and the method's bias on NIST's model asserted by tests.
  Accessible fallback: the dossier's caption and tables give every plotted
  number in text.

## Out of scope

The electron-diffraction card (stays `survey-only`), ADR 007, the card
schema, the card-count test, any new state before `go`, the lesson page,
where the Bragg model lives in the course (a Phase 2 question, recorded as
an open item).
