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
| `sdss_spec_to_csv.py` | `sdss-balmer-spectrum` | `spec-1949-53433-0480.fits` (`0f9aa3f5f187dde1fb42e6b58ab9b428e48a2d45f73e7254d954f48121a6a813`) | `spec-1949-53433-0480.csv` (`90dff68b9df582a8deba83f21f0eefbd510d00866481c875abf4202ebdb1b163`), not committed: the decision is `defer` |

To repeat a conversion:

```
./scripts/fetch-data.sh tess-exoplanet-light-curves
uv run python tools/datasets/tess_lc_to_csv.py \
    data/downloads/tess-exoplanet-light-curves/tess2020238165205-s0029-0000000100100827-0193-s_lc.fits \
    data/samples/tess-exoplanet-light-curves/wasp18_s0029_lc.csv
```

The SDSS spectrum is converted the same way into its download directory,
where the reference figure reads it (`docs/datasets/sdss-balmer-spectrum.md`):

```
./scripts/fetch-data.sh sdss-balmer-spectrum
uv run python tools/datasets/sdss_spec_to_csv.py \
    data/downloads/sdss-balmer-spectrum/spec-1949-53433-0480.fits \
    data/downloads/sdss-balmer-spectrum/spec-1949-53433-0480.csv
```

`sdss_spec_to_csv.py` reads the FITS file with the header and table reader of
`tess_lc_to_csv.py`, which it loads from beside itself.

`fetch-data.sh` checks the download against the card's digest; the script
refuses any other input and a file whose FITS checksums do not verify. The
output is the same bytes each time, and the dataset check compares it with
the card's sha256.
