# Dossier: TU Delft turbulent boundary layer, PIV and PTV profiles

Card: `data/registry/tudelft-turbulent-boundary-layer.yaml`. Inspected 2026-11-09 for F108 (Issue #441), the measured-data lab FL8. The lab pairs this record with the grazing-flow hot-wire benchmark ([grazing-flow-hwa-benchmark](grazing-flow-hwa-benchmark.md)), which has its own card. Why these two and not Rostock (Zenodo 17720136) or Sheffield is in [the dataset research](spike-candidates-2026-11-08.md); those cards stay `survey-only`.

**Decision: go.** Kind: mean-velocity and Reynolds-stress profiles of a zero-pressure-gradient turbulent boundary layer at four Reynolds numbers, by two techniques. Recorded under the owner's approval of 2026-11-09 on Issue #441 (work towards a `go`, judged per dossier, every requirement of ADR 007 checked here). The checklist below names the evidence for each; the limits are in "What the data do not give".

## The files inspected

| | |
|---|---|
| Source | 4TU.ResearchData, "Dataset underlying the publication: Development and characterisation of a turbulent boundary layer facility at the Delft University of Technology", M. Knoop, A. Hassanein, W. Baars, version 1, published 2025-09-26, doi 10.4121/d0af5e8b-6bde-4c02-a165-c752b5ab435a.v1; the article is Knoop, Hassanein, Baars, *Aerospace Science and Technology* (2025), doi 10.1016/j.ast.2025.110972 (not read) |
| Record | 6 files, 7.96 GB: `HWA.zip` (5.86 GB of hot-wire time series), `wall-pressure.zip` (1.19 GB), `Freestream microphone.zip` (0.92 GB), `PIV.zip`, `PTV.zip`, `readme.txt` |
| Used | `PIV.zip` (78,642 B, md5 `fa1cd9e0cd70adb33c9941813b3a7743`), `PTV.zip` (10,144 B, md5 `b874c3c5764daf56db31cbdd227eca2f`), `readme.txt` (4,016 B, md5 `7920e7c012f640b8d496944428f779a3`). Every md5 equals the `computed_md5` that 4TU publishes in the record's file list. |
| Accessed | 2026-11-09 |

The research of 2026-11-08 inspected the same two archives and found the same md5s. The three large archives are not downloaded: a lab that wants spectra needs its own download and inspection (the research: "a learner download plus a small extract").

**No conversion.** MAT v5 is read in the build by `scipy.io.loadmat` (ADR 007 addendum of #417; SciPy is already locked), so the eight `EXPparam.mat` files are committed unchanged at their paths inside the archives (`PIV/U05/EXPparam.mat` ... `PTV/U20/EXPparam.mat`, 86,772 B together); their sha256s are on the card. Readers: `pbc.data.reference.tudelft_boundary_layer.read_piv` and `read_ptv`, which refuse a file whose variables are not exactly the expected doubles.

## Schema, units, cadence, masks, coverage

| Item | What the readme says | What this dossier established |
|---|---|---|
| Layout | variables in a struct `EXPparam` | **top-level variables**, all doubles; no struct (header `MATLAB 5.0 MAT-file, Platform: PCWIN64`) |
| PIV variables | `Uinf, Utau, mu, rho, y, Ubar, uu, uu, uu, delta, deltastar, theta, H` | `H, Ubar, Uinf, Utau, delta, deltastar, mu, rho, theta, uu, uv, vv, y`: the readme names `uu` three times for `uu`, `uv`, `vv`; profiles of 496, 496, 497, 493 points for U05, U10, U15, U20 |
| PTV variables | `Uinf, Utau, mu, rho, y, Ubar` | the same; 133, 132, 134, 129 points |
| Units | SI; y in m | SI, **except PTV y, which is in millimetres**: in mm the PTV points below y+ = 5 give U+/y+ − 1 between −0.019 and +0.007 and continue the PIV profile; in m they would lie beyond y+ = 570, where the log law gives U+ above 20, while every PTV U+ is below 18 |
| Cadence | not stated | PIV y in equal steps of 0.282 to 0.283 mm, from 0.47 to 0.73 mm to 140 mm (1.28 to 1.30 δ); PTV y unequally spaced, 0.048 mm to 2.08 to 2.16 mm |
| Coverage | four speeds, "x = 6.8 m" (record description) | U_inf 4.57, 9.16, 13.73, 18.28 m/s (PIV; PTV states 4.6, 9.2, 13.8, 18.3); Re_τ 1351, 2415, 3552, 4647; Re_θ 3079, 6533, 9240, 12020 |
| Masks | none | no NaN or fill value; the PIV profile begins at y+ 9 to 20, so the sublayer is PTV's alone (y+ 0.6 to 89) |
| DOI | "[insert doi]" | a placeholder in the readme; the record's DOI is above |

The parsing test `tests/unit/test_data_tudelft_boundary_layer.py::test_tudelft_sample_parses` asserts the MAT header, the variable names and shapes, the steps, the absence of missing values, the millimetre unit of PTV y, and the signs of the stresses.

## Artifact labels

| Artifact | Type |
|---|---|
| `HWA.zip`, `wall-pressure.zip`, `Freestream microphone.zip` (not downloaded) | `raw-measured` |
| `PIV/*/EXPparam.mat` (the sample) | `processed-measured`: profiles averaged by the creators from PIV fields |
| `PTV/*/EXPparam.mat` (the sample) | `processed-measured`: near-wall profiles averaged from PTV |
| the Blasius profile, the log law, the Coles–Fernholz skin friction | `modelled-reference`, computed here |

The inner scaling, the fits, the recomputed H, and the splice of PTV and PIV are computed by `pbc.data.reference.tudelft_boundary_layer`; the figure draws the models in grey dash-dot, dashed, or dotted lines, labelled "(model)" or "(reference, not fitted)", apart from the measured curves.

## Reference figure

```
uv run python -m pbc.data.reference tudelft-turbulent-boundary-layer --out tudelft.png
```

The code is `src/pbc/data/reference/tudelft_boundary_layer.py`. **Status label: processed.** Panels: U+ against y+ (PIV lines, PTV markers) with the viscous sublayer and a reference log law; U/U_inf against y/δ with the Blasius laminar layer against y/δ₉₉; the Reynolds shear stress −u′v′/u_τ² against y/δ; and H against Re_θ, from the file and recomputed, with Blasius's H.

**The physics, for FL2 and FL3.** A laminar boundary layer on a flat plate without pressure gradient is the Blasius solution: U/U_inf = f′(η) with f‴ + f f″/2 = 0, and its shape factor H = δ*/θ is 2.591. A turbulent layer mixes momentum toward the wall, so its profile is far fuller (H 1.3 to 1.4 here), its wall shear is set by u_τ, and near the wall it follows U+ = y+ and then the log law U+ = ln(y+)/κ + B. The data test where the laminar model stops and what replaces it.

The chain, each step in the code:

1. **Read and convert.** SI from the files; PTV y × 10⁻³.
2. **u_τ check.** The file's u_τ against Coles–Fernholz, C_f = 2 [ln(Re_θ)/0.384 + 4.127]⁻², at the file's Re_θ.
3. **Log law.** A straight line of U+ against ln y+ over 50 < y+ and y < 0.15 δ (40 to 53 points); the same fit over 15 windows (lower bound 30, 50, 80, 100, or 3√Re_τ; upper 0.1, 0.15, or 0.2 δ) gives the sensitivity.
4. **H.** δ* and θ by the trapezoid rule from the wall (U = 0) through the PTV points below the first PIV point, each technique as U/U_inf with its own U_inf, to y = δ.
5. **Blasius.** Shooting on f″(0) with `solve_ivp` (rtol 10⁻¹¹): f″(0) = 0.332057, η₉₉ = 4.910, δ*/√(νx/U) = 1.7208, θ/√(νx/U) = 0.6641, H = 2.5911 (`test_the_blasius_layer`).
6. **PTV against PIV.** (U/U_inf)_PTV / (U/U_inf)_PIV, PIV interpolated at the PTV y where both measure.

**Caption.** *Mean velocity and Reynolds shear stress of a turbulent boundary layer at four speeds (TU Delft, PIV and PTV profiles). In wall units the four profiles collapse onto the viscous sublayer and the log law; the log law fitted over 50 < y+ < 0.15 Re_τ gives κ 0.400 to 0.410 and B 4.77 to 5.17 with the file's friction velocity, which agrees with the Coles–Fernholz correlation within 1.1 %. Against the outer scale the turbulent profiles are far fuller than the laminar Blasius layer: H 1.33 to 1.37 against 2.59. The record states no uncertainty; the spread of κ over common fit windows (0.36 to 0.43) is larger than the spread between the speeds.*

| Quantity | U05 | U10 | U15 | U20 |
|---|---|---|---|---|
| U_inf [m/s] (PIV) | 4.574 | 9.157 | 13.733 | 18.278 |
| u_τ [m/s] (file, PIV) | 0.1846 | 0.3352 | 0.4919 | 0.6408 |
| u_τ / Coles–Fernholz − 1 | +1.07 % | −1.14 % | −0.05 % | +0.23 % |
| Re_τ | 1351 | 2415 | 3552 | 4647 |
| Re_θ | 3079 | 6533 | 9240 | 12020 |
| κ, B (50 < y+, y < 0.15 δ) | 0.410, 5.07 | 0.400, 4.77 | 0.405, 4.98 | 0.409, 5.17 |
| κ over 15 windows | 0.364–0.428 | 0.355–0.418 | 0.367–0.419 | 0.373–0.421 |
| B over 15 windows | 3.52–5.54 | 3.02–5.27 | 3.49–5.38 | 3.75–5.55 |
| H (file) | 1.3675 | 1.3618 | 1.3381 | 1.3312 |
| H recomputed | 1.387 | 1.375 | 1.346 | 1.330 |
| PTV / PIV where both measure, mean (max) | 1.003 (1.032) | 1.043 (1.057) | 1.032 (1.055) | 1.070 (1.099) |
| peak −u′v′/u_τ² | 0.910 | 0.961 | 0.962 | 0.973 |

The research of 2026-11-08 found κ = 0.400–0.410, B = 4.77–5.17, H = 1.331–1.367, and −u′v′⁺ plateaus of 0.91 to 0.97; this dossier repeats those numbers from the committed files.

## Uncertainty and calibration

The record gives **no uncertainty** for any value, does not say how u_τ or δ were determined, and holds none of the PIV or PTV calibration (magnification, pulse separation, interrogation window); the article (not read) may. What can be checked from the files:

- **u_τ.** Within 1.1 % of the Coles–Fernholz correlation at every speed. The correlation is empirical and independent of these profiles, so the agreement supports the file's u_τ to about 1 %, which moves U+ by about 1 % and B by about 0.2.
- **The log-law window dominates.** κ moves from 0.36 to 0.43 and B from 3.0 to 5.5 across 15 windows that are all in use in the literature; the nominal window gives κ 0.400 to 0.410. A lab must state its window and show this sensitivity; it should not quote κ to three figures. Since the file's u_τ may itself come from a fit to a log law (the record does not say), the fitted κ is not an independent measurement of the von Kármán constant; the Coles–Fernholz check is what ties u_τ to something else.
- **PIV against PTV.** Where both measure (y+ about 9 to 89), PTV reads 0.3 % (U05) to 7.0 % (U20) higher on average, up to 9.9 % at U20 next to the wall. The difference grows with speed, as the near-wall gradient steepens across a fixed PIV interrogation spacing (0.28 mm, 12 wall units at U20); that is consistent with spatial averaging by the PIV, but the record does not state the window, so it is an interpretation. PTV and PIV also state slightly different U_inf and u_τ (U15: 0.4718 against 0.4919 m/s), being separate runs or processings.
- **H.** Recomputed with the PTV points near the wall, H lies within 1.5 % of the file's (θ within 0.3 %); a linear profile to the wall instead of PTV gives up to 0.6 % more. The file's H decreases with Re_θ, as a turbulent layer's does.
- **Shear stress.** −u′v′⁺ peaks below 1 (0.91 to 0.97), as it must: the total shear stress at the wall is ρu_τ², and near the wall part of it is viscous. Its rise with Re_τ is expected; its fall toward the wall (y/δ below a few hundredths) is partly physical, as the viscous stress takes over, and partly the PIV's resolution, which the record does not let one separate.

Asserted by `tests/unit/test_data_tudelft_boundary_layer.py`: the Reynolds numbers, the u_τ comparison, the nominal fits and the window range, the Blasius constants, H file and recomputed against Blasius, PTV against PIV, and the stress peaks.

## What the data do not give

- **No time series and no spectra** in the committed part: those are in the 5.86 GB hot-wire archive, which is neither downloaded nor inspected.
- **No uncertainty** of any profile value, and not the method of u_τ or δ.
- **No laminar or transitional state:** every case is turbulent, so the laminar layer is a model on the figure, not a measurement. The grazing-flow benchmark adds a second facility and porous walls, not a laminar case.
- **No streamwise development:** one station per speed, so dδ/dx and the momentum-integral balance cannot be checked from this record.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | 4TU.ResearchData record https://data.4tu.nl/datasets/d0af5e8b-6bde-4c02-a165-c752b5ab435a/1, licence field "CC BY 4.0" (API: license url https://creativecommons.org/licenses/by/4.0/), read 2026-11-09; https://creativecommons.org/licenses/by/4.0/legalcode |
| Redistribution of subsets | permitted | the same record; legal code section 2(a)(1) |
| Publication of figures and derivatives | permitted | the same record; legal code section 2(a)(1) |
| Modification and attribution | permitted, with attribution and an indication of changes | legal code section 3(a); the card's `attribution` names the creators, the record, the licence, and the reading of PTV y in millimetres; the figure prints it |

## Size, runtime, payload

Sample 86,772 B in eight files (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 2.3 s with the interpreter start and about 180 MB peak memory; the PNG is about 290 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the MAT files are read at build time and not shipped. The learner's download is the three files of the card (`./scripts/fetch-data.sh tudelft-turbulent-boundary-layer`, 92,802 B, checked against 4TU's md5s); unzipping `PIV.zip` and `PTV.zip` gives the eight samples byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected": sizes and md5s equal to 4TU's; the sha256 of every sample on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage" (the struct, the PTV unit, the stress names corrected); "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure labels each model and draws it apart |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/tudelft_boundary_layer.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": none in the record, stated; u_τ against Coles–Fernholz; the window sensitivity of κ and B; PTV against PIV; H recomputed |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the FL8 lab, starts only when the owner says so (Issue #441). Its roadmap dependencies include FL7 (F53, not started) for the shared PIV conventions.
- The article (paywalled) may give u_τ's method, δ's definition, and the PIV window; reading it would sharpen the PIV–PTV interpretation. It is not a condition of this `go`.
- The hot-wire time series would add spectra and higher moments; a lab that wants them needs its own small extract and inspection.
