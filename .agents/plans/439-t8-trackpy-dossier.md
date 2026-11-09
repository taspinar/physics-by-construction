# Plan: F85 phase 1 — the trackpy `bulk_water` card, dossier, and sample (Issue #439)

Phase 1 only: the card, the dossier, the committed sample, its parsing
tests, and the reference figure, towards a `go` judged per dossier (owner's
decision of 2026-11-08 on the Issue). Phase 2, the T8 lab, is a later step.
The roadmap row (F85, T8) is checked: not retired.

## Steps

1. Download frames 000–039 and the `README` of `sample_data/bulk_water` at
   trackpy-examples commit `09fb3074`; confirm every git blob SHA-1 against
   the GitHub tree; record the sha256 of each; read the licence and the
   walkthrough notebook (scale, frame rate, its own result).
2. The tracking, the project's own processing with NumPy and SciPy (no
   trackpy): `src/pbc/data/tracking.py` (band-pass, local maxima, centroid
   and mass, mutual-nearest-neighbour linking, drift, ensemble MSD).
3. The one-time tracking `tools/datasets/bulk_water_tracks.py`, pinned to the
   sha256 of the 40 frames, writes the detections and their links as
   `bulk_water_tracks.csv`; same bytes on each run.
4. The sample `data/samples/trackpy-bulk-water/`: the tracks CSV, the
   green channel of frames 000–002 as a uint8 NumPy array written by the
   same script (so that the build can redo the detection and the linking on
   them and compare with the CSV), and the provider's `README`. About
   1.5 MB, within the caps. Discovery during the work: the PNGs themselves
   cannot be committed, since the committed-artifact check rejects any image
   outside `site/assets/` (invariant I6); the array is the data of the one
   channel analysed, values unchanged.
5. The reference figure `src/pbc/data/reference/trackpy_bulk_water.py`:
   frame 000 with the tracks, the drift-corrected ensemble MSD with the
   linear fit and its residuals, the step distribution against a Gaussian;
   D with a bootstrap over tracks; Stokes–Einstein at 20 and 25 °C; the
   sensitivity to the link range, the mass cut, the track length, the lag
   range, and the drift subtraction.
6. Tests `tests/unit/test_data_bulk_water.py` (parsing: field names, shapes,
   units, cadence, masks; the re-detection of frames 000–002; the tracking
   on synthetic images; the numbers of the dossier) and the figure
   conventions in `tests/unit/test_data_plotting.py` and the offline test of
   `tests/integration/test_data_checks.py`.
7. The card `data/registry/trackpy-bulk-water.yaml`, the dossier
   `docs/datasets/trackpy-bulk-water.md` with the ADR 007 checklist, the rows
   in `docs/datasets/README.md` and `tools/datasets/README.md`.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (frame 000 with the
  tracks; ensemble MSD with bootstrap bars, the linear fit dashed and apart,
  the residuals; lag-1 steps against a Gaussian). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: D and the intercept asserted by tests; the tracking checked on
  synthetic images with known positions and on the re-detection of the
  committed frames. Accessible fallback: the dossier's caption and tables
  give every plotted number in text.

## Out of scope

The card-count test, ADR 007, the card schema, any new state before `go`,
the lesson page (phase 2).
