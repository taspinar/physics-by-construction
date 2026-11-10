# Dossier: grazing-flow benchmark, hot-wire boundary-layer profiles over solid and porous walls

Card: `data/registry/grazing-flow-hwa-benchmark.yaml`. Inspected 2026-11-09 for F108 (Issue #441), the measured-data lab FL8, as the second record of the pair with [tudelft-turbulent-boundary-layer](tudelft-turbulent-boundary-layer.md). The Issue and the research of 2026-11-08 call it "VKI"; the record names two TU Delft creators, and only the file names of its manuscript's figures mention VKI ("data4VKI"). This dossier uses the record's title.

**Decision: go.** Kind: normalised hot-wire profiles (mean velocity, turbulence intensity, length scale) of a tripped turbulent boundary layer over a solid wall and over two porous inserts, with their integral parameters. Recorded under the owner's approval of 2026-11-09 on Issue #441 (work towards a `go`, judged per dossier, every requirement of ADR 007 checked here). The limits are in "What the data do not give"; the main one is that the providers fitted the solid-wall y to canonical profiles.

## The files inspected

| | |
|---|---|
| Source | Zenodo record 15044105, "A benchmark dataset for the grazing flow over porous materials", O. Moriaux and R. Zamponi (Delft University of Technology), version 3, published 2025-03-18 (concept 10.5281/zenodo.10955510); v3 corrected the permeabilities in the manuscript only |
| Record | 8 files, 8.50 MB: `HWA_PROFILES_v2.zip`, `BL_PARAMETERS.zip`, `WPS_DATA.zip` (wall-pressure spectra, 3.99 MB), `README.txt`, the AIAA manuscript (4.16 MB), three geometry images |
| Used | `HWA_PROFILES_v2.zip` (121,193 B, md5 `b0aaf672c259c1785c0c8c1f1b46f94f`), `BL_PARAMETERS.zip` (6,755 B, md5 `fef62fb9bf16f0456e14e65bab2538b1`), `README.txt` (9,359 B, md5 `e3a508bccb14d722d03d20acdc5764ea`). Every md5 equals the one Zenodo publishes. |
| Accessed | 2026-11-09 |

The research of 2026-11-08 inspected the same two archives with the same md5s.

**No conversion.** The 24 CSV files of the two archives (12 profile files, 12 parameter files, 287,592 B) are committed unchanged at their paths inside the archives; their sha256s are on the card. Readers: `pbc.data.reference.grazing_flow_hwa.read_profiles` and `read_parameters` (NumPy), which refuse a file that is not CRLF-terminated or whose header differs.

## Schema, units, cadence, masks, coverage

| Item | What the README says | What this dossier established |
|---|---|---|
| Cases | walls D00 (solid), D35, D45 (porous, diamond lattice of 3.5 and 4.5 mm cells), at 15, 20, 25 m/s; upstream `UPVyy` | 9 insert cases and 3 upstream; files `HW_<case>.csv` and `BL_<case>.csv` |
| Profile schema | U/Ue, TI, length scale, their uncertainties, against y/δ | header `x/L [-], y/delta [-], U/Ue [-], Unc. U/Ue [-], TI [%], Unc. TI Upper [%], Unc. TI Lower [%], Lambda/delta [-]`; 5 stations × 43 rows per insert case, **not sorted by x**; 35 rows upstream |
| Parameter schema | δ, Ue, δ*, θ, H, atmospheric conditions | header `x/L [-], Ue [m/s], delta [m], delta_star [m], theta [m], H [-], T_atm [K], p_atm [Pa], Liner [mm], Velocity [m/s]`; one row per station; Liner and Velocity on the first row only (Liner −1 upstream) |
| x | "normalized with the streamwise length of the liners (L = 0.1 m)" | true in the profile files (−0.33333 ... 0.33333, upstream −6.6); **in the parameter files the column headed `x/L` holds x in metres** (−0.033333 ... 0.033333, upstream −0.66): it equals the profiles' x/L times 0.1 at every station (`parameter_x_is_metres`) |
| Friction velocity | used for the wall-pressure correction, "estimated with the Clauser method" | **not in the files** |
| Uncertainty columns | U/Ue ± Unc.; TI lower/upper bounds | Unc. U/Ue is a 95 % half-width, at most 0.00043; the two TI columns are the **bounds** of the interval (TI lies between them), at most 0.001 percentage points from TI |
| Cadence | logarithmic near the wall, linear further out | y/δ from 0.005 to 0.007 (y+ 5 to 13) to 1.5 to 1.8 at the insert; from 0.021 to 0.026 (y+ 15 to 24) to 2.5 to 2.9 upstream |
| Masks | length scale "only inside the boundary layer" | `Lambda/delta` empty at 8 to 12 points per insert profile and 14 upstream; nothing else missing |
| Defect | none | `HW_UPV25.csv` gives rows 5 and 6 the same y/δ, 0.04139, with U/Ue 0.555 and 0.532; the record does not say which is right; the analysis keeps both |
| Air | T and p per station | 292 to 304 K, 99.4 to 100.7 kPa; ν from Sutherland's law and the ideal gas, 1.53 to 1.62 × 10⁻⁵ m²/s |

The parsing test `tests/unit/test_data_grazing_flow_hwa.py::test_grazing_flow_sample_parses` asserts the shapes, the x unit, the first-row-only columns, the masks, the defect, the cadence, the meaning of the uncertainty columns, and the air.

## Artifact labels

| Artifact | Type |
|---|---|
| hot-wire time series (not in the record) | `raw-measured` |
| `HWA_PROFILES_v2/*.csv` (the sample) | `processed-measured`: statistics of the time series, normalised; solid-wall y refined by a fit to canonical profiles |
| `BL_PARAMETERS/*.csv` (the sample) | `processed-measured` |
| `WPS_DATA.zip`, manuscript, images (not used) | `processed-measured` |
| u_τ from Coles–Fernholz, the Blasius profile, the log law | `modelled-reference`, computed here |

## Reference figure

```
uv run python -m pbc.data.reference grazing-flow-hwa-benchmark --out grazing.png
```

The code is `src/pbc/data/reference/grazing_flow_hwa.py`, which takes the Blasius solution and the Coles–Fernholz correlation from `tudelft_boundary_layer`. **Status label: processed.** Panels: U+ against y+ for the solid wall at x = 0 and the three speeds, with the sublayer and a reference log law; U/Ue against y/δ for the solid wall and the 4.5 mm porous insert at x/L = 1/3 and 25 m/s, the upstream profile, and Blasius; TI against y/δ at x = 0 for the solid wall; H across the insert for every wall and speed.

The chain: (1) read; match each parameter row to its profile through x = 0.1 x/L; (2) ν from the recorded T and p; (3) Re_θ = Ue θ/ν, u_τ from C_f = 2 [ln(Re_θ)/0.384 + 4.127]⁻²; (4) inner scaling and the log fit over 50 < y+ and y < 0.15 δ, as for the TU Delft record; (5) H from the file, and recomputed with a linear profile to the wall as a check.

**Caption.** *Hot-wire profiles of a turbulent boundary layer over a solid wall and over porous inserts. With the friction velocity from the Coles–Fernholz correlation, the solid-wall profiles follow the log law (κ 0.39 to 0.42 over 6 to 10 points); the providers fitted the wall position of those profiles to canonical profiles, so that agreement is partly built in. The turbulent profiles are far fuller than the laminar Blasius layer (H 1.33 to 1.36 against 2.59). Over the porous inserts H grows by 0.05 to 0.06 within 67 mm, and the solid-wall law no longer describes the profile.*

| Quantity | Value |
|---|---|
| solid wall, Ue | 14.99 to 25.14 m/s |
| solid wall, Re_θ / Re_τ (u_τ from Coles–Fernholz) | 3254 to 5909 / 1060 to 1878 |
| solid wall, u_τ | 0.59 (15 m/s), 0.76 to 0.77 (20), 0.94 (25) m/s |
| solid wall, κ and B over 50 < y+, y < 0.15 δ (15 profiles) | κ 0.387 to 0.421, B 4.48 to 5.39, on 6 to 10 points |
| solid wall, H (record) | 1.326 to 1.357 |
| solid wall, H recomputed (linear to the wall) | 1.5 to 3.1 % above the record's |
| porous walls, H at x/L = −1/3 → 1/3 | 1.330–1.357 → 1.380–1.414; rise 0.046 to 0.058 |
| porous walls, "κ" with the same u_τ, from x = 0 on | below 0.31: the solid-wall law does not apply |
| upstream (x = −0.66 m), Ue / H (record) | 11.54, 15.49, 19.83 m/s / 1.283, 1.301, 1.294 |
| laminar Blasius layer | H 2.591 |

The research of 2026-11-08 found, with the same Coles–Fernholz u_τ, κ = 0.399 to 0.408 and B = 4.88 to 5.00, and a Clauser fit within −1.3 % to +2.4 % of that u_τ. Its window and choice of profiles are not recorded; with the window used here the 15 solid-wall profiles spread wider (0.387 to 0.421), which is the honest range for a fit on 6 to 10 points.

## Uncertainty and calibration

- **Statistical only, from the record.** U/Ue ± at most 0.00043 (95 %), TI within 0.001 percentage points: 10 s at 25.6 kHz per point averages the noise away. The record gives no calibration uncertainty of the hot wire and no probe-orientation error (a single wire senses the fluctuation along the mean velocity, README); these dominate and are unknown.
- **The wall position.** The robotic traverse zeroes y to ±0.0025 mm (README), but "for all solid-walled HW measurements, the y-coordinates were further refined by fitting the plus-unit representation of the boundary layer on canonical profiles". So the near-wall solid profiles were made to agree with a canonical law; their log-law κ and B are not an independent measurement, and a lab must say so. The porous-wall profiles were not refined this way, and they depart from the law.
- **u_τ is not measured.** It comes from a correlation of Re_θ, which holds for a canonical solid-wall layer. For the porous walls it is only a scale: the providers say their own Clauser estimate "is therefore not usable for porous walls".
- **The upstream station.** Its Ue (11.5 to 19.8 m/s) is not the nominal speed in the file name; its H (1.28 to 1.30) is low for Re_θ 1400 to 2900, and its first point (y+ 15 to 24, by a hand traverse to ±0.03 mm) leaves the near-wall part unresolved: H recomputed from it is 1.45, which says more about the missing points than about the layer. A lab should use the insert stations.
- **H recomputed.** A linear profile from the wall to the first point at y+ 5 to 13 overestimates δ* slightly, hence 1.5 to 3.1 % above the record's H; the record's H is used.

Asserted by `tests/unit/test_data_grazing_flow_hwa.py`: ν, Re_θ, u_τ, Re_τ of one station; the solid-wall κ and B ranges; the porous departure; H of the record and the porous rise; H recomputed against the record's.

## What the data do not give

- **No independent friction velocity** and no independent wall position for the solid wall: the log law cannot be tested here, only illustrated; the TU Delft record, with u_τ checked against Coles–Fernholz and a PTV sublayer, is the test.
- **No time series**, so no spectra or higher moments from the hot wire; the wall-pressure spectra are in `WPS_DATA.zip`, not used.
- **No laminar state**: Blasius is a model on the figure.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo record https://zenodo.org/records/15044105, licence field "Creative Commons Attribution 4.0 International" (API `license: cc-by-4.0`), read 2026-11-09; https://creativecommons.org/licenses/by/4.0/legalcode |
| Redistribution of subsets | permitted | the same record; legal code section 2(a)(1) |
| Publication of figures and derivatives | permitted | the same record; legal code section 2(a)(1) |
| Modification and attribution | permitted, with attribution and an indication of changes | legal code section 3(a); the card's `attribution`; the figure prints it |

## Size, runtime, payload

Sample 287,592 B in 24 files (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 2.3 s with the interpreter start and about 180 MB peak memory; the PNG is about 310 KB at 150 dpi. A lesson page with this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSVs are read at build time and not shipped. The learner's download is the three files of the card (`./scripts/fetch-data.sh grazing-flow-hwa-benchmark`, 137,307 B, checked against Zenodo's md5s); unzipping the two archives gives the 24 samples byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected": sizes and md5s equal to Zenodo's; the sha256 of every sample on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage" (the x unit, the TI bounds, the defect); "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure labels u_τ's source and every model |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/grazing_flow_hwa.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the statistical uncertainties of the record, the fitted wall position, u_τ from a correlation, the upstream station |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the FL8 lab, starts only when the owner says so (Issue #441).
- The manuscript in the record (downloaded, not read) may give the hot-wire calibration and the Clauser u_τ; reading it is not a condition of this `go`.
