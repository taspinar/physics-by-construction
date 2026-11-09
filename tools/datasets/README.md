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

To repeat a conversion:

```
./scripts/fetch-data.sh tess-exoplanet-light-curves
uv run python tools/datasets/tess_lc_to_csv.py \
    data/downloads/tess-exoplanet-light-curves/tess2020238165205-s0029-0000000100100827-0193-s_lc.fits \
    data/samples/tess-exoplanet-light-curves/wasp18_s0029_lc.csv
```

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

`fetch-data.sh` checks the download against the card's digest; the TESS script
refuses any other input and a file whose FITS checksums do not verify; the
Lycopodium scripts refuse any other input, a sheet of another layout, and a
morphometry file with a byte above 127 other than the micro sign. The
output is the same bytes each time, and the dataset check compares it with
the card's sha256.
