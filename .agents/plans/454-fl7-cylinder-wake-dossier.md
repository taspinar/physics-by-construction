# Plan: F53 phase 1 — the cylinder-wake PIV and hot-wire cards, dossiers, and samples (Issue #454)

Phase 1 only: the cards, the dossiers, the committed samples, their parsing
tests, and the reference figures, towards a `go` judged per dossier (owner's
approval of 2026-11-09 on the Issue for datasets A and B and their
downloads). Phase 2, the FL7 lab, starts only after the owner says so. The
roadmap row (F53, FL7) is checked: not retired.

## Steps

1. Download `cylinder_vel.mat` of Zenodo 20765567 once into a new empty
   directory outside the repository; check the md5 of the record; read it
   with `scipy.io.loadmat` (the header says MAT 5.0: no `h5py`). Read the
   record's description and the experiment section of Tu et al. (arXiv
   1401.7047, the accepted text of Exp. Fluids 2014): D, U, Re, the PIV
   processing, the shedding frequency.
2. Download the ten `Velocity_1C*.txt` files of Mendeley xy8ggx9hn6 v1,
   each into its own new empty directory; check each sha256 against the
   Mendeley API; read them as plain text only.
3. Extract A: `tools/datasets/cylinder_wake_extract.py`, md5- and
   sha256-pinned input, writes a NumPy `.npz` (no pickle) with a crop of
   the near wake, float32 u and v, an explicit boolean mask, x and y, about
   60 frames at 20 Hz, and a long probe series (all frames, one or a few
   points) for the spectrum; under 2 MB.
4. Extract B: `tools/datasets/ost_hotwire_extract.py`, sha256-pinned,
   writes the first 2^14 samples of each run (16.384 s) as one CSV and the
   runs' metadata from the record's file descriptions; about 1.1 MB or less.
5. Reference figures, `src/pbc/data/reference/cylinder_wake_piv.py`
   (vorticity, derived, with the mask and streamlines; the probe spectrum
   and the shedding frequency against 0.889 Hz; St from D and U of the
   paper) and `src/pbc/data/reference/ost_hotwire.py` (spectrum of one run;
   St against Re for the ten runs, with the PIV point).
6. Tests: `tests/unit/test_data_cylinder_wake.py`, `tests/unit/test_data_ost_hotwire.py`
   (field names, shapes, units, cadence, masks; the numbers of the dossiers;
   the tools refuse other inputs), and the rows in
   `tests/unit/test_data_plotting.py` and `tests/integration/test_data_checks.py`.
7. Cards `data/registry/piv-cylinder-wake.yaml` (the survey card, now
   inspected) and `data/registry/ost-hotwire-cylinder-wakes.yaml`; dossiers
   `docs/datasets/piv-cylinder-wake.md` and
   `docs/datasets/ost-hotwire-cylinder-wakes.md`; rows in
   `docs/datasets/README.md`, `tools/datasets/README.md`,
   `docs/datasets/spike-candidates-2026-11-08.md`.

## Visual deliverables

- Scientific figure: the reference figure of `piv-cylinder-wake` (a
  vorticity snapshot computed from the PIV field, masked region grey,
  streamlines; the cross-stream velocity at a probe and its spectrum with
  the shedding peak). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: the peak frequency and St asserted by tests; the vorticity
  checked on an analytic field. Accessible fallback: the dossier's caption
  and tables give every plotted number in text.
- Scientific figure: the reference figure of `ost-hotwire-cylinder-wakes`
  (spectrum of one run; St against Re for the ten runs). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: each run's peak frequency asserted by tests. Accessible
  fallback: the dossier's table of the ten runs.

## Out of scope

ADR 007, the card schema, any new state before `go`, the lesson page and
the animation (phase 2), `scripts/fetch-data.sh`.
