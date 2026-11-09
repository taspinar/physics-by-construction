# Plan: F88 phase 1 — the Kamchatka 2025 tsunami inputs: card, dossier, sample, figure (Issue #444)

Phase 1 only: the inputs of the FL10 capstone (DART records, the USGS finite
fault, the ETOPO 2022 bathymetry crop) as one dataset with a card, a dossier,
a committed sample, its parsing test, and the reference figure, towards a `go`
judged per dossier (owner's approval of 2026-11-09 on the Issue). The
propagation model and the comparison are phase 2, which starts only after a
`go` and the owner's word.

## Steps

1. Download: the NCEI event files `dart21416_…_meter.txt`, `dart21415_…_meter.txt`
   and `DART_deployment_coord.txt` (https://www.ngdc.noaa.gov/hazard/data/DART/20250729_kamchatka/);
   the NDBC annual files `21416t2025.txt.gz` and `21415t2025.txt.gz`; the USGS
   finite fault `complete_inversion.fsp` and `surface_deformation.disp` of
   product `us6000qw60_1`, version 5; the ETOPO 2022 60″ crop 140E–180E,
   35N–60N, stride 4, as OPeNDAP ASCII (byte-stable over two requests).
2. Conversion (ADR 007 addendum style): `tools/datasets/etopo_ascii_to_npy.py`,
   NumPy only, input sha256 and parsed-array sha256 pinned; output an int16
   `.npy` (metres, rounded) of 375 × 600 cells. Every other file is committed
   byte for byte.
3. Reader and reference figure `src/pbc/data/reference/kamchatka_tsunami.py`:
   - readers of the NCEI event file, the NDBC annual file, the deployment
     list, the `.fsp` header and subfaults, the `.disp` grid, the ETOPO array;
   - the double conversion: NCEI raw height over NDBC height at matched
     timestamps (0.670), and NCEI mean over station depth;
   - corrected residuals (NCEI residual / 0.670), peaks and their times after
     the ComCat origin time; the seismic interval marked;
   - the moment magnitude from the subfault moments; slip and uplift extremes;
   - √(gh) travel times along great circles over the ETOPO crop, from the
     epicentre and from the nearest uplift, to each DART.
4. Tests `tests/unit/test_data_kamchatka_tsunami.py` (parsing and the
   numbers of the dossier; the converter on a small ASCII response the test
   writes), `tests/unit/test_data_plotting.py`, the network-blocked list of
   `tests/integration/test_data_checks.py`.
5. The card `data/registry/kamchatka-2025-tsunami-inputs.yaml`, the dossier
   `docs/datasets/kamchatka-2025-tsunami-inputs.md` with the ADR 007
   checklist, rows in `docs/datasets/README.md` and `tools/datasets/README.md`;
   the reference module in `pbc.data.reference.__main__`. The research page
   `docs/datasets/spike-candidates-2026-11-08.md` stays as it is (the earlier
   dossiers left it too).
6. Discovery during the work: the ETOPO full-resolution crop (to average
   instead of decimate) failed as an OPeNDAP binary request; the decimated
   ASCII crop of the research is used and the decimation disclosed.

## Visual deliverables

- Scientific figure: the reference figure of the dataset (a map of the
  bathymetry crop with the USGS vertical deformation and the two DARTs; the
  corrected residuals at 21416 and 21415 against time since the origin with
  the √(gh) arrival estimates; the NCEI/NDBC ratio that shows the double
  conversion). Status `processed`.
  Skills: pbc-scientific-visualization@a70b501
  Validation: the ratio, the peaks, the arrival estimates, Mw, and the
  deformation extremes asserted by tests. Accessible fallback: the
  dossier's caption and tables give every plotted number in text.

## Out of scope

The propagation model, the benchmark suite, any comparison of a model with
the DART records (phase 2); ADR 007, the card schema, the card-count test;
notifying NCEI (the owner's action); the lesson page.
