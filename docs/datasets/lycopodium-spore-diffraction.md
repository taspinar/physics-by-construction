# Dossier: Lycopodium spores, diffraction at two wavelengths and microscope morphometry

Card: `data/registry/lycopodium-spore-diffraction.yaml`. Inspected 2026-11-09 for F52 (Issue #440), the measured-data lab W7; the choice of this record over the Fraunhofer microstructures (Zenodo 19436924, whose card stays `survey-only`) is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: line profiles of a diffraction halo at two wavelengths, with an independent size measurement of the diffracting particles. Recorded under the owner's decision of 2026-11-08 on Issue #440 (work towards a `go`, judged per dossier, every requirement of ADR 007 checked here; "screen distance and image scale are not in the record: say so"). The checklist below names the evidence for each; the limits are in "What the data do not give".

## The files inspected

| | |
|---|---|
| Source | Zenodo record 15846643 (concept 15846642), "Morphometry and Optical Data of Lycopodium Spores for the Study of Diffraction and Interference", O. Voronkin and S. Lushchin, published 2025-07-09; supplement to Voronkin and Lushchin, *Eur. J. Phys.* 46 (2025) 055802, doi 10.1088/1361-6404/adf7e6 |
| Record | 29 files, 71.6 MB: micrographs at x80 to x1280 with their scale bars, binarised TIFFs, diffraction and interference photographs (JPEG from a Nokia 5, CR3 from a Canon EOS RP), three morphometry CSVs, three intensity-profile XLSX |
| Used | `Intensity_profile_diffraction_lambda0.6328um.xlsx` (88,771 B, md5 `ebe9a4cce61d4ab8879d3b3436e1d3f1`, sha256 `2efdb178052814c982f3870746cf3173c671d1a997765b02af06335e0c496b87`); `Intensity_profile_diffraction_lambda0.405um.xlsx` (43,485 B, md5 `f48dca39781ba647c352d0d3b0d26926`, sha256 `f7b6caf8daf2c90c2cb923515a3e55a2700d91e11373ca50714f193e83083e56`); `Lycopodium_Morphometry_x160.csv` (19,837 B, md5 `bf607a6ee0b547b614067f4be793d9cc`); `Lycopodium_Morphometry_x80.csv` (83,863 B, md5 `ac827547093505ab1867d17b19be8521`). Every md5 equals the one Zenodo publishes. |
| Accessed | 2026-11-09 |

The research of 2026-11-08 inspected the same XLSX files and the x160 CSV and found the same md5s. The x80 CSV is added here as a second, independently calibrated size measurement. The third morphometry file (x640) measures wall fragments only, and the interference profile belongs to the reflected-light experiment; neither is used.

**Conversion (ADR 007, addendum of #417).** XLSX is converted once, outside the build: `tools/datasets/lycopodium_xlsx_to_csv.py` reads the zip archive and its XML parts with the standard library alone, refuses an input whose sha256 is not one of the two above, checks that the workbook has one sheet whose first row is the title `profile_A` and whose second is the header `n, x, y, luma`, and that `n` counts 0, 1, 2, ... without a gap. It writes every row in its order, `n` as an integer and the other values as the shortest decimal of the stored float64, under three comment lines (source and checksum, conversion, units). Outputs: `profile_633nm.csv`, 91,646 B, sha256 `f115399d9acc7d21b3dfe4f52b8b35b140666f044fe6f9b2a265a520af9df0e8`; `profile_405nm.csv`, 38,979 B, sha256 `2906362fdd402ff5968095516a50b39e686edf1635a78e4392c3d65c90262d58`. Two runs give the same bytes. The two morphometry CSVs of the record are Latin-1 (the micro sign of three headers is the byte 0xB5, their only byte above 127); a committed file is UTF-8, so `tools/datasets/lycopodium_morphometry_to_utf8.py` re-encodes them once, outside the build, from Latin-1 to UTF-8 and changes nothing else (the same numbers, `;` separators, and CRLF line endings). It refuses an input whose sha256 is not that of the record's file (x160 `03648277f9fda3d561a8fbab048133e72333877feec65e103159a1baeb08d7dc`, x80 `eb6a0c5c922add8b3f962b00374b6f52bfca2297bf4f45d5617c0aff5ca1644d`) and one with another byte above 127. Outputs: `Lycopodium_Morphometry_x160.csv`, 19,840 B, sha256 `c72892f18b6d4250c195e43aab6d9b71b831b9e24a540d7d721faeb4dedf2fcc`; `Lycopodium_Morphometry_x80.csv`, 83,866 B, sha256 `3676fe56f4d5c1e96693687f415f6b64d829717359c3eed602e524d1805dfe53`; encoded back to Latin-1, each has the md5 that Zenodo publishes. `tools/datasets/README.md` says how to repeat both conversions.

Readers of the sample: `pbc.data.reference.lycopodium.read_profile` and `read_morphometry` (NumPy).

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Profile schema | "radial intensity profile values ... along a horizontal scanline crossing the central part of the pattern using Tracker software" | one sheet: title `profile_A`, header `n x y luma`, 2,211 rows (632.8 nm) and 932 rows (405 nm); no other columns |
| Profile units | none | `x` and `y` in Tracker's calibrated world unit, **not stated** (not pixels: the steps are 0.0530 and 0.0830, different per photograph); `luma` the camera brightness 0 to 255, averaged across the line, so not integers |
| Profile cadence | one scanline | one sample per pixel, equal steps of x (to 1e-8); x from −61.50 to 55.71 and from −39.15 to 38.13; `y` constant (the scanline's height) |
| Morphometry schema | the ImageJ columns and the creators' `r, d (µm)` | `;`-separated, CRLF, Latin-1 in the record and UTF-8 in the sample; an unnamed particle number, ImageJ's measurements (x80 lacks `Perim.`), an empty column, then `r^2 (µm^2)`, `r (µm)`, `d (µm)`; 150 rows (x160), 642 rows (x80) |
| Morphometry units | "Area (in pixels²)" | **Area is in µm²**: the creators' r² equals Area/3.14 to 5e-9 in every row, so d = 2√(Area/3.14), the diameter of the circle of equal area with π taken as 3.14 (0.025 % too large, negligible here) |
| Calibration | a scale bar of 10 µm per division for each magnification | the two magnifications agree (below) |
| Masks | none | no missing value; saturated samples (luma ≥ 250): 37 at 632.8 nm, 57 at 405 nm, all in the central spot; at 632.8 nm a plateau near luma 80 out to radius 13 is the red channel at its limit (luma weighs red by about 0.3) |

The parsing test `tests/unit/test_data_lycopodium.py::test_lycopodium_sample_parses` asserts the field names, shapes, steps, the saturated counts, the absence of missing values, and the area-to-diameter relation; `test_the_samples_are_the_record_files_and_the_conversion_outputs` asserts the checksums.

## Artifact labels

| Artifact | Type |
|---|---|
| diffraction photographs of the record (not committed, not inspected) | `raw-measured` |
| the two XLSX profiles | `processed-measured` (extracted from a photograph by Tracker) |
| `profile_633nm.csv`, `profile_405nm.csv` (the sample) | `processed-measured` |
| `Lycopodium_Morphometry_x160.csv`, `_x80.csv` (the sample) | `processed-measured` (ImageJ on a binarised micrograph) |
| the polydisperse Airy model | `modelled-reference`, computed here |

The record does not say from which photograph either profile was taken. The centring, folding, smoothing, ring radii, and the model are not artifacts of the record: `pbc.data.reference.lycopodium` computes them, and the figure draws the model dashed and apart from the measured points.

## Reference figure

```
uv run python -m pbc.data.reference lycopodium-spore-diffraction --out lycopodium.png
```

The code is `src/pbc/data/reference/lycopodium.py`. **Status label: processed.** Panels: the two profiles about their centres with the dark ring marked; the folded, smoothed profiles against radius over wavelength; the histograms of the microscope diameters of whole spores at both magnifications; and the dark-ring radius against wavelength with the proportional model.

**The physics.** A layer of spores scatters the beam into a halo. By Babinet's principle each opaque spore diffracts like a hole of the same size, and spores at random places add intensities, so the halo is the Airy pattern of one disk averaged over the diameters present: I(q) ∝ Σ d⁴ [2J₁(πdq)/(πdq)]², with q = sin θ / λ. The pattern depends on q only, so every ring's sin θ is proportional to the wavelength. That is the test this record supports without its missing calibration.

The chain, each step in the code:

1. **Whole spores.** Particles with d > 15 µm; the rest are fragments of walls (at x160 no particle lies between 10 and 20 µm, so the cut sits in a gap; at x80 seven particles lie between 10 and 20 µm).
2. **Centre.** The x about which the profile is most nearly mirror-symmetric (least squares of luma at c + r against c − r for r > 3, grid 0.005): 1.245 at 632.8 nm, 0.075 at 405 nm.
3. **Fold and smooth.** The mean of both sides, by radius, smoothed by a moving average of 1.0 in x.
4. **Dark ring.** The most prominent local minimum (prominence at least 2 luma) outside the saturated core, refined by a parabola through three samples.
5. **Uncertainty.** The radius for smoothing widths 0.5, 0.75, 1.0, 1.5, 2.0; half the range is taken as the uncertainty (below).
6. **Model.** `ensemble` with the 72 x160 diameters gives the q of each minimum and maximum; it reduces to the Airy pattern of one disk (first zero 1.2197/d, `test_the_ensemble_model_reduces_to_the_airy_pattern_of_one_disk`).

**Caption.** *Diffraction halos of Lycopodium spores at 632.8 nm and 405 nm, from line profiles of two photographs. On a radius divided by the wavelength, the dark rings of the two halos fall nearly together: the ring at 405 nm is 0.661 ± 0.024 times the radius of that at 632.8 nm, against the wavelength ratio 0.640, as diffraction by one population of particles requires. The microscope measures that population at 29.9 µm (x160) and 30.4 µm (x80) mean diameter. The centre of each photograph is saturated, and the record states neither the unit of the profile nor the distance to the screen, so the figure tests the scaling with wavelength and does not infer the diameter.*

| Quantity | Value |
|---|---|
| whole spores, x160 | n = 72, mean 29.91 ± 0.34 µm (standard error), sd 2.87 µm |
| whole spores, x80 | n = 605, mean 30.36 ± 0.13 µm, sd 3.22 µm |
| difference of the two means | 0.45 µm, 1.2 combined standard errors |
| dark ring, 632.8 nm | 16.68 ± 0.34 (units of x); widths 0.5 to 2.0 give 16.69, 16.72, 16.68, 16.50, 17.18 |
| dark ring, 405 nm | 11.02 ± 0.33; widths give 10.71, 10.75, 11.02, 11.29, 11.37 |
| ratio r(405)/r(632.8) | 0.661 ± 0.024 |
| wavelength ratio | 0.640 (difference 0.9 standard errors) |
| model minima, q·d̄ (72 spores) | 1.232, 2.231, 3.258 (one disk: 1.220, 2.233, 3.238) |
| bright-to-dark radius ratio | measured 1.19 (632.8 nm), 1.11 (405 nm); model 1.31 if the dark ring is the first minimum, 1.17 if the second |
| implied distance to the screen, units of x | 640 (632.8 nm) and 661 (405 nm) if the first minimum; 353 and 365 if the second |

The research of 2026-11-08 found r₁ = 16.76 ± 0.23 and 11.25 ± 0.56 and a ratio of 0.671 ± 0.035 by another method; the values agree within their uncertainties.

## Uncertainty and calibration

**Microscope.** Each magnification is calibrated by its own scale bar (10 µm per division, per the record); the means at x160 and x80 differ by 1.2 combined standard errors, so the two calibrations agree. The standard errors are statistical; the record gives no uncertainty of the scale bars or of the binarisation threshold, and the equal-area diameter of a spore that is not round (circularity 0.71 on average at x160) is a convention. The spread (sd about 3 µm, 10 %) is real and enters the model.

**Diffraction profiles.** The record gives no uncertainty, no unit of x, no distance to the screen, no camera settings, and not the photograph each profile comes from. The camera's tone curve is unknown and the centre saturates, so intensities are not compared with the model; only ring positions are used, and only their ratio is free of the missing calibration (it needs only that both profiles share one length unit, which the agreement of the implied screen distances, 640 and 661 or 353 and 365, supports to 3 %).

- **Sensitivity range, not a statistical error.** The ring radius moves with the smoothing width by ±0.34 (632.8 nm) and ±0.33 (405 nm); this half-range is the uncertainty used. Speckle (a finite number of spores in the beam) makes the profile bumpy on the scale of the ring, which is why a smoothing is needed and why its width matters.
- **The two sides.** At 632.8 nm the left and right minima (16.65 and 16.76) agree. At 405 nm the left side has a clear dip at 10.92 and the right side none (its lowest point near the fold's radius is 13.99, the edge of the search window): the 405 nm radius rests on the left side, carried through the fold. A lab must say so.
- **Ring order.** With one dark ring per profile, the record does not settle whether it is the first or the second minimum of the Airy pattern. The spacing to the next bright ring (1.19 and 1.11 times the dark-ring radius) is closer to the model's 1.17 for the second minimum than to 1.31 for the first, which suggests the first minimum is hidden in the saturated centre; the bright-ring positions are speckled, so this is not decisive. The scale-free ratio holds for either order.
- **Small angles.** The ring lies at sin θ ≈ 0.026 (order 1) or 0.047 (order 2); a flat screen measures tan θ, which changes the ratio by less than 0.001.

Asserted by `tests/unit/test_data_lycopodium.py`: the diameters at both magnifications and their agreement, the centres, the ring radii and their ranges, the ratio and its comparison with 0.640, the sides, the model minima, the bright-to-dark ratios, and the implied screen distances.

## What the data do not give

- **No absolute size from the diffraction.** Without the distance to the screen and the unit of x, the diffraction gives d only as λL/r times a known constant. The owner's comment of 2026-11-08 asks to say so: the record's description and the companion article's landing page (read 2026-11-09; the article itself is paywalled and not read) state neither. A lab can use the microscope's diameter to infer the screen distance in the profile's unit, as in the table, or ask the learner which ring order is plausible for a tabletop setup if the unit were the millimetre (0.64 m or 0.35 m); it cannot check the microscope against the diffraction absolutely.
- **No intensity model.** The halo's intensity against the model would need the camera's linear response.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | Zenodo record https://zenodo.org/records/15846643, licence field "Creative Commons Attribution 4.0 International" (API `license: cc-by-4.0`; the record's copyright field is empty), read 2026-11-09; https://creativecommons.org/licenses/by/4.0/legalcode |
| Redistribution of subsets | permitted | the same record; legal code section 2(a)(1) |
| Publication of figures and derivatives | permitted | the same record; legal code section 2(a)(1) |
| Modification and attribution | permitted, with attribution and an indication of changes | legal code section 3(a); the card's `attribution` names the creators, the record, the licence, and the conversion; the figure prints it |

The sister record of the same creators (Zenodo 19436924, the Fraunhofer microstructures) shows a copyright line beside its licence; this record has none, and its licence is CC BY 4.0 at record level, which covers its files.

## Size, runtime, payload

Sample 234 KB in four files (caps: 2 MB per file, 8 MB per dataset). The reference figure takes about 3.2 s with the interpreter start and about 320 MB peak memory; the PNG is about 280 KB at 150 dpi. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload; the CSVs are read at build time and not shipped. The learner's download is the four files of the card (`./scripts/fetch-data.sh lycopodium-spore-diffraction`, checked against the card's digests), and the two conversions repeat the four samples byte for byte. CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The files inspected": sizes, md5s equal to Zenodo's, sha256 of the XLSX inputs and of every sample on the card |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage" (the unit of x stated as unknown, the area unit corrected); "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure draws the proportional model dashed |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/lycopodium.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": the microscope's standard errors and the agreement of two calibrations; the ring radii's sensitivity range, the sides, the ring order; the missing calibration of the profiles stated |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the W7 lab, starts only when the owner says so (Issue #440).
- The distance to the screen and the unit of x would turn the ratio test into an absolute check of the diameter. They may be in the article (not read) or obtainable from the creators; asking them is the owner's choice, not a condition of this `go`.
- The raw photographs (JPEG, CR3) are not inspected; a lab that wants a second line profile, or the rings in two dimensions, would need its own inspection of one of them.
