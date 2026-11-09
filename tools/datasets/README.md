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
| `lycopodium_xlsx_to_csv.py` | `lycopodium-spore-diffraction` | `Intensity_profile_diffraction_lambda0.6328um.xlsx` (`2efdb178052814c982f3870746cf3173c671d1a997765b02af06335e0c496b87`); `Intensity_profile_diffraction_lambda0.405um.xlsx` (`f7b6caf8daf2c90c2cb923515a3e55a2700d91e11373ca50714f193e83083e56`) | `profile_633nm.csv` (`f115399d9acc7d21b3dfe4f52b8b35b140666f044fe6f9b2a265a520af9df0e8`); `profile_405nm.csv` (`2906362fdd402ff5968095516a50b39e686edf1635a78e4392c3d65c90262d58`) |
| `lycopodium_morphometry_to_utf8.py` | `lycopodium-spore-diffraction` | `Lycopodium_Morphometry_x160.csv` (`03648277f9fda3d561a8fbab048133e72333877feec65e103159a1baeb08d7dc`); `Lycopodium_Morphometry_x80.csv` (`eb6a0c5c922add8b3f962b00374b6f52bfca2297bf4f45d5617c0aff5ca1644d`), Latin-1 | the same names, UTF-8 (`c72892f18b6d4250c195e43aab6d9b71b831b9e24a540d7d721faeb4dedf2fcc`; `3676fe56f4d5c1e96693687f415f6b64d829717359c3eed602e524d1805dfe53`) |
| `srm660c_cif_to_csv.py` | `nist-srm660c-lab6` | `srm_660c_cifs_20201029_081700.zip` (`92034d06498161db365420831fe35d91ec18bad4ed17385329a1761658da2c42`), its 20 CIFs | `660c_100a.csv` to `660c_1000b.csv` and `specimens.csv` (the 21 sha256 on the card) |
| `bulk_water_tracks.py` | `trackpy-bulk-water` | `bulk_water_000.png` to `bulk_water_039.png` (the 40 sha256 in the script and on the card) | `bulk_water_tracks.csv` (`e676e8bb6ab18a48c789dfc0444bf0a716ae13b3548d75d32f03c3b74d88d586`), `bulk_water_green_000-002.npy` (`2e0c8355f5426c1fc23a23da8bc6f3a215747a8eee65faf5f16cf7d320feb6b7`) |
| `sdss_spec_to_csv.py` | `sdss-balmer-spectrum` | `spec-1949-53433-0480.fits` (`0f9aa3f5f187dde1fb42e6b58ab9b428e48a2d45f73e7254d954f48121a6a813`) | `spec-1949-53433-0480.csv` (`90dff68b9df582a8deba83f21f0eefbd510d00866481c875abf4202ebdb1b163`) |
| `etopo_ascii_to_npy.py` | `kamchatka-2025-tsunami-inputs` | `etopo2022_60s_bed_35N60N_140E180E_stride4.txt`, the OPeNDAP ASCII response (`454b00a5aaaaf4406523e1f39fc38dbd40ea3c6799d5cde209d25b75701bf198`; its parsed array `8bd4f1e5c02b1a39c7706cf6b1c76771c4bbde2716310e55af0f743978bb719d`) | `etopo2022_60s_bed_35N60N_140E180E_stride4.npy` (`27bf15f585aa7289f2eb90624628f4d30601f49a0be4f2dd6c730b9fae5ead93`); the seven other files of the dataset are committed byte for byte |
| `cylinder_wake_extract.py` | `piv-cylinder-wake` | `cylinder_vel.mat` (md5 `4cc876439c48f7970afa477ea17d217a`, sha256 `328cd8d17cd2eb42faef6e4766bc8e515e0eac06868152972adab9bdf91926e7`) | `wake_u.npy`, `wake_v.npy`, `wake_mask.npy`, `wake_mean.npy`, `probes.npy`, `wake_meta.json` (the six sha256 on the card) |
| `ost_hotwire_extract.py` | `ost-hotwire-cylinder-wakes` | the ten `Velocity_1C*.txt` (the ten sha256 in the script and on the card) | `ost_hotwire_16s.csv` (`551871f95aa42c10153568444695c19334e78a2332329aa89e0e8e5c70162754`), `runs.csv` (`573b0d40a6d59a4c56e1783603b3dde2a5ccd760ae34381bfe36bf2f3ab93b72`) |
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

The SDSS spectrum is converted the same way into its committed sample:

```
./scripts/fetch-data.sh sdss-balmer-spectrum
uv run python tools/datasets/sdss_spec_to_csv.py \
    data/downloads/sdss-balmer-spectrum/spec-1949-53433-0480.fits \
    data/samples/sdss-balmer-spectrum/spec-1949-53433-0480.csv
```

`sdss_spec_to_csv.py` reads the FITS file with the header and table reader of
`tess_lc_to_csv.py`, which it loads from beside itself.

DWD replaces its archive every year, so the second download works only
until the next one is published; the script refuses any other archive.

and, for the two Lycopodium profiles:

```
./scripts/fetch-data.sh lycopodium-spore-diffraction
for nm in 0.6328:633 0.405:405; do
  uv run python tools/datasets/lycopodium_xlsx_to_csv.py \
      "data/downloads/lycopodium-spore-diffraction/Intensity_profile_diffraction_lambda${nm%%:*}um.xlsx" \
      "data/samples/lycopodium-spore-diffraction/profile_${nm##*:}nm.csv"
done
for m in x160 x80; do
  uv run python tools/datasets/lycopodium_morphometry_to_utf8.py \
      "data/downloads/lycopodium-spore-diffraction/Lycopodium_Morphometry_${m}.csv" \
      "data/samples/lycopodium-spore-diffraction/Lycopodium_Morphometry_${m}.csv"
done
```

and, for the 20 SRM 660c CIFs:

```
./scripts/fetch-data.sh nist-srm660c-lab6
uv run python tools/datasets/srm660c_cif_to_csv.py \
    data/downloads/nist-srm660c-lab6/srm_660c_cifs_20201029_081700.zip \
    data/samples/nist-srm660c-lab6
```

and, for the ETOPO 2022 crop of the Kamchatka tsunami inputs (a generated
OPeNDAP response: the script refuses a response with another sha256 unless
`--allow-other-input` is given and its parsed array equals the pinned one):

```
./scripts/fetch-data.sh kamchatka-2025-tsunami-inputs
uv run python tools/datasets/etopo_ascii_to_npy.py \
    data/downloads/kamchatka-2025-tsunami-inputs/etopo2022_60s_bed_35N60N_140E180E_stride4.txt \
    data/samples/kamchatka-2025-tsunami-inputs/etopo2022_60s_bed_35N60N_140E180E_stride4.npy
```

`fetch-data.sh` checks the download against the card's digest; the TESS script
refuses any other input and a file whose FITS checksums do not verify; the
DWD script refuses any other archive; the Lycopodium scripts refuse any other
input, a sheet of another layout, and a morphometry file with a byte above 127
other than the micro sign; the SRM 660c script refuses any other zip, a
missing or extra CIF, a pattern block of another layout, and measured and
calculated blocks on different 2θ grids. The
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

`cylinder_wake_extract.py` and `ost_hotwire_extract.py` extract the samples
of the two FL7 datasets (Issue #454): the first reads the 1.1 GB MAT 5.0
file of the PIV record with `scipy.io.loadmat` (about 1.8 GB of memory) and
writes 60 frames of the near wake with their mask, the time mean, and two
probe series as NumPy arrays; the second keeps the first 16.384 s of each
hot-wire run, rounded to 1 mm/s, and the runs' parameters from the record's
file descriptions:

```
./scripts/fetch-data.sh piv-cylinder-wake
uv run python tools/datasets/cylinder_wake_extract.py \
    data/downloads/piv-cylinder-wake/cylinder_vel.mat \
    data/samples/piv-cylinder-wake

./scripts/fetch-data.sh ost-hotwire-cylinder-wakes
uv run python tools/datasets/ost_hotwire_extract.py \
    data/downloads/ost-hotwire-cylinder-wakes \
    data/samples/ost-hotwire-cylinder-wakes
```
