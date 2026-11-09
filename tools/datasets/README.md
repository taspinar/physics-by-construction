# One-time conversions of dataset files

The addendum of 2026-11-08 to ADR 007 (Issue #417) converts XLSX, FITS, and
CIF files once, outside the build, by a documented, checksum-pinned script;
the committed sample is the script's output, and the card and the dossier
record the script, the checksum of its input, and that of its output. This
directory holds those scripts. The build, the verification, and CI never run
anything here; the tests run the scripts only on small files they write
themselves.

| Script | Dataset | Input (sha256) | Output (sha256) |
|---|---|---|---|
| `tess_lc_to_csv.py` | `tess-exoplanet-light-curves` | `tess2020238165205-s0029-0000000100100827-0193-s_lc.fits` (`c89434e50db863e589c9321cf29c93e449ef1526f1a9db19552446b721fd0949`) | `wasp18_s0029_lc.csv` (`96cc3d255288b4158386e035358c7a8f4787180931fbe9863acd5113d14ecf11`) |
| `bulk_water_tracks.py` | `trackpy-bulk-water` | `bulk_water_000.png` to `bulk_water_039.png` (the 40 sha256 in the script and on the card) | `bulk_water_tracks.csv` (`e676e8bb6ab18a48c789dfc0444bf0a716ae13b3548d75d32f03c3b74d88d586`), `bulk_water_green_000-002.npy` (`2e0c8355f5426c1fc23a23da8bc6f3a215747a8eee65faf5f16cf7d320feb6b7`) |
| `dwd_soil_extract.py` | `dwd-potsdam-soil-temperature` | `stundenwerte_EB_03987_19510101_20251231_hist.zip` (`6a968e6da83c783c4fa3a35196521021550bf56d1a64cde83cc9aeceb882329f`) | `eb_stunde_03987_2015_2024_6h.txt` (`d9fe4916f266c91a0f0ab1e42782682e12ae07a379fd1c98fe309afcfeb824d2`), `eb_stunde_03987_jja_2020_2024_1h.txt` (`ab6be9339237a2d66b4b552bc2ca42a6f3dbe7560c86a0803c0dcb6d067115cd`), and four metadata files re-encoded from ISO-8859-1 to UTF-8 (text unchanged) |

To repeat a conversion:

```
./scripts/fetch-data.sh tess-exoplanet-light-curves
uv run python tools/datasets/tess_lc_to_csv.py \
    data/downloads/tess-exoplanet-light-curves/tess2020238165205-s0029-0000000100100827-0193-s_lc.fits \
    data/samples/tess-exoplanet-light-curves/wasp18_s0029_lc.csv

./scripts/fetch-data.sh dwd-potsdam-soil-temperature
uv run python tools/datasets/dwd_soil_extract.py \
    data/downloads/dwd-potsdam-soil-temperature/stundenwerte_EB_03987_19510101_20251231_hist.zip \
    data/samples/dwd-potsdam-soil-temperature
```

DWD replaces its archive every year, so the second download works only
until the next one is published; the script refuses any other archive.
`fetch-data.sh` checks the download against the card's digest; the script
refuses any other input and a file whose FITS checksums do not verify. The
output is the same bytes each time, and the dataset check compares it with
the card's sha256.

`bulk_water_tracks.py` is not a format conversion but the one-time tracking
of a dataset whose frames are too large for its sample: it locates and links
the particles with `pbc.data.tracking` and writes the CSV, and the green
channel of frames 000-002 as a NumPy array (no image file is committed
outside `site/assets/`); the build repeats the tracking on that array and
compares (Issue #439):

```
./scripts/fetch-data.sh trackpy-bulk-water
uv run python tools/datasets/bulk_water_tracks.py \
    data/downloads/trackpy-bulk-water \
    data/samples/trackpy-bulk-water
```
