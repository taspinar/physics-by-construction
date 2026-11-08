# Dossier: NIST Numisheet 2020 DP980 tension, compression, tension

Card: `data/registry/nist-numisheet-dp980.yaml`. Inspected 2026-11-08 for F107 (Issue #421), the measured-data lab MAT6; the choice of this record is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: a mechanical test of a sheet steel with a load reversal. Recorded under the owner's decision of 2026-11-08 on Issue #421 (work towards a `go` on the strength of the research, every requirement of ADR 007 checked here); the checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | NIST record mds2-2202, doi 10.18434/M32202, "Data for Numisheet 2020 uniaxial tensile and tension/compression tests", version 1.2.0 ("data update"), first issued 2020-04-14; authors of the report William E. Luecke, Evan Rust, Mark A. Iadicola (NIST Center for Automotive Lightweighting, NCAL) |
| File | `C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv`, 131,777 bytes, sha256 `76105d4bfa640ca6502f0d44e5cb3f2edd2a9e1b3f41ec6fa7071bc7a65a68a3` (published by NIST in the record's component list, confirmed on the downloaded file) |
| Companion | `…-Stress-Strain-attributes.csv`, 265 bytes, sha256 `dbbcffe3100df64f2dd799edcd08ccb29369255ff5ebe03cca6aec30ad77256a`: the names, units, and descriptions of the five columns |
| Report read | `2020-03-Numisheet2020-tension-compression-summary-final.pdf` of the record (7,196,617 bytes, sha256 as published), the source of the protocol, the strain measurement, and the noise floor below; not committed |
| Accessed | 2026-11-08 |
| Record | 239 files: uniaxial tension of four alloys at seven angles (6–17 MB each, DIC strain profiles), and tension/compression tests of the four alloys at 0°, three repeats each |

The sample is the two files, copied byte for byte. The specimen, from the file name (the naming convention of the report's Table 3): tension/compression test (`C`), 0° to the rolling direction, iron-based dual-phase steel DP980 (Numisheet benchmark BM1), repeat R01, thickness 1.424 mm, width 17.93 mm, imaged on its side (`-S`).

Reader: `pbc.data.reference.nist_numisheet.read_stress_strain` and `read_attributes`, the standard library's `csv` and NumPy; no dependency is added.

## What the strain and the stress measure

**Strain.** Stereo digital image correlation (two 9.1 MP cameras, Correlated Solutions Vic-3D 8.2.4) of a speckle pattern painted on the edge of the sheet, the thickness face. The engineering strain column is a **virtual extensometer**: the change of distance between two points of the DIC field, a nominal gauge length G = 23.6 mm apart, centred on the reduced parallel length to within ±0.5 mm, over the original distance (equation 4 of the report). The record also holds, as separate multi-MB files, the local true (Hencky) strain along the centreline, measured with a virtual strain gauge of 45 pixels = 0.86 mm; those local strains are not in the sample. The strain is therefore an average over 23.6 mm: once the specimen necks, the extensometer averages a localised strain with the unloading material beside it.

**Stress.** Engineering stress is the force over the original cross-section, S = P/A0 (equation 3). The force is the mean of an upper and a lower load cell; between them, the specimen runs through an anti-buckling fixture pressed on it with 3,000 N (PTFE film and petroleum jelly against friction), which lets the thin sheet be compressed without buckling. The report states that the two load cells typically differ by less than 300 N.

**True columns.** `Tstrain` and `Tstress` are NIST's ln(1 + e) and S(1 + e) (equations 5 and 6), which assume uniform deformation and constant volume. They are computed columns, valid only up to the start of necking. NIST says of the stress-strain curves that they are "provided for reference only".

**Protocol** (report section 2.2.1): a short force-controlled ramp to zero force, then in displacement control at 0.54 mm/min (a nominal strain rate of 0.00025 s⁻¹, the ASTM E8 rate): tension to a strain of about 75 % of the uniform strain, a 10 s hold, compression back to an engineering strain near zero, a 10 s hold, tension until fracture. The small strain offsets in the compression are, by the report, artefacts of displacement control.

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Schema | header `"Time","Estrain","Estress","Tstrain","Tstress"`; the attributes file | 1,607 rows of five numbers; the attributes file has the columns Variable, Units, Type, Description, AxisLabel |
| Units | Time s, stress MPa, strain mm/mm (attributes file) | Tstrain = ln(1 + Estrain) to 5e-16 and Tstress = Estress(1 + Estrain) to 5e-12; tension positive; peak stresses near ±1 GPa, as for a DP980 steel |
| Cadence | 4 images/s during elastic loading, 1 image/s after yield (report) | one row per image: 0.25 s steps from 0 to 62.85 s, then 1 s steps (three of 1.25–1.33 s) to 1418.0168 s, the last row |
| Masks, missing values | none stated | no missing or non-finite value; the first 10 rows (0–2.35 s, \|S\| < 1 MPa) precede the force ramp and serve below as the noise sample |
| Time coverage | tests at NCAL, October 2019 to January 2020 | one test, 0 to 1418.0168 s from the start of image acquisition to fracture; its date is not in the file |

The parsing test `tests/unit/test_data_samples.py::test_nist_numisheet_sample_parses` asserts the field names, the units of the attributes file, the shapes, the cadence, the true-strain and true-stress relations, and the absence of masks.

## Artifact labels

| Artifact | Type |
|---|---|
| `C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv` | `processed-measured` |
| `C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain-attributes.csv` | `processed-measured` (its metadata) |

The stress and the strain are measured, but each is NIST's processing of a raw signal (two load cells averaged and divided by A0; a DIC displacement field reduced to a virtual extensometer), so the file is labelled processed. The elastic line, the 0.2 % offset line, the loop area, and the unloading chord are not artifacts of the record: `pbc.data.reference.nist_numisheet` computes them, and the figure draws the lines dashed and dotted, apart from the measured points, with the residuals of the elastic fit.

## Reference figure

```
uv run python -m pbc.data.reference nist-numisheet-dp980 --out dp980.png
```

The code is `src/pbc/data/reference/nist_numisheet.py`. **Status label: processed.** Panels: the whole engineering stress–strain path in its three segments with the hysteresis loop shaded; the elastic regime of the first tension with the fitted line, the line shifted by 0.2 %, and the offset yield; the stress against time, which shows the protocol and the two holds; and the residuals of the elastic fit against stress.

**Caption.** *A DP980 sheet steel pulled to 5.8 % strain, pushed back to zero strain, and pulled to fracture, with stress and strain measured by load cells and image correlation. The material yields gradually: a line fitted between 100 and 400 MPa gives E = 196 GPa, and the 0.2 % offset yield is 775 MPa. On reversal the stress falls along a chord of 144 GPa, not E, and compressive flow begins long before −991 MPa is reached (the Bauschinger effect); the path from the stress maximum round the compression and back to the same strain, closed by a straight segment, encloses 75.8 MJ/m³, the net work per volume done on the steel over the cycle. On reloading, the stress rises to 981 MPa at 9.1 % strain, where necking starts, and the specimen breaks at 17.7 %.*

| Quantity | Value | How |
|---|---|---|
| First tension, stress maximum (the start of the loop) | 991.3 MPa at e = 0.0575, t = 301.7 s | the measured maximum before the compression; the strain still rises by 0.0004 into the hold after it |
| End of the hold after the stress maximum | e = 0.0579 (the largest strain before the compression) at t = 307.7 s and 970.3 MPa: the stress relaxes by 21.1 MPa from the maximum | from the second row after the maximum the strain stays within 1e-4; the unloading starts at the end of the hold |
| Most compressive stress | −1006.6 MPa at e = −0.0004 | the measured minimum |
| Loop, ∮ S de over the closed path | **75.8 MJ/m³** | start: the stress maximum (e = 0.0575, 991.3 MPa); end: the first row of the reload at that strain or beyond (e = 0.0576, 964.9 MPa, t = 1065.0 s); closed by a straight segment from the end back to the start (+0.0001 in strain, −26.5 MPa), which contributes −0.1 MJ/m³. Trapezoids over the measured points plus that segment (`loop`, `Loop`). Sign: positive for a path that runs clockwise in the (e, S) plane, the reload above the unloading, as this one does; the value then equals the enclosed area (the shoelace area of the closed polygon, whose edges do not cross) and the net work per volume done on the specimen over the cycle, the plastic work dissipated or stored |
| E, window 100–400 MPa | **196.3 ± 1.1 GPa** (standard error from the scatter), intercept 7.4 MPa | `fit_curve`, 84 points |
| E over the windows 50–300, 100–300, 100–400, 150–450 MPa | 192.5 to 198.4 GPa | `window_sensitivity` |
| 0.2 % offset yield | 775 MPa | crossing of the shifted line, interpolated between samples |
| Unloading chord, 950 → 0 MPa | 143.6 GPa (130.3 GPa for 500 → 0, 159.5 GPa for 950 → 600) | `unloading_modulus` |
| Maximum of the final tension | 981.2 MPa at e = 0.0910 | the start of necking; the true columns are not valid beyond it |
| Fracture | e = 0.1771, the last row | |

Three points need care in a lab. The elastic line bends early: the residuals leave zero above about 450 MPa, and E moves from −2 % to +1 % around 196 GPa with the window, more than its standard error. The unloading chord is 20–35 % below E, so the reversal is not elastic; a lab that measures a reverse yield stress must say which line it offsets from. And the loop area is plastic work per volume over this one path, not a property of the steel independent of the strain amplitude.

## Uncertainty and calibration

The record gives **no uncertainty per point** and **no calibration values**. What it states:

- The DIC system's **noise floor of the local strain**, \|mean\| + sd over the area of interest in five static images: 263 µm/m for this test (report, Appendix 4.2, Table 2), over the 0.86 mm virtual gauge; it is a quality metric of the DIC system, not an uncertainty of the 23.6 mm extensometer.
- The **load cells** typically differ by less than 300 N, and the anti-buckling force varied by less than 300 N (section 2.2.1). Half of 300 N over A0 = 1.424 × 17.93 = 25.5 mm² is 5.9 MPa: the scale on which friction in the fixture can shift the mean force. The report gives no load-cell calibration.
- **Calibration**, qualitatively: machine alignment to ASTM E1012 Class 5; protocol and fixture qualified for sheet compression under ASTM E9; stereo DIC calibrations with a stereo angle of 22.495 ± 0.005° and an image scale of 52.6 pixel/mm. Specimen thickness and width are means of three measurements, with no stated uncertainty. No correction is applied here.

Derived here, from the sample:

- **Extensometer noise.** Before the force ramp (10 rows, \|S\| < 1 MPa) the engineering strain scatters with sd 25 µm/m, a tenth of the local noise floor: the 23.6 mm extensometer averages many local values. The stress scatters 0.18 MPa.
- **Statistical error of E.** With no per-point uncertainty, `fit_curve` scales the covariance by the residual scatter: 196.3 ± 1.1 GPa. The residual rms in the window, 4.4 MPa, equals E times the extensometer noise (196 GPa × 25 µm/m = 4.9 MPa) to 15 %, so the scatter about the line is the strain noise, not the stress.
- **Sensitivity to the window.** Over four windows E runs from 192.5 to 198.4 GPa. This is a sensitivity of the fit to where the curve is called linear, not a bound on calibration or instrument error.
- **Not known from this sample.** The repeatability between the three repeats R01–R03 (the other two files, about 130 KB each, are not inspected or committed); the calibration error of the load cells, of the extensometer, and of the dimensions, which no fit can reveal because it scales every point alike. A lab that reports E or the yield stress must say that their uncertainty is derived from one test and the fit, and that the calibration error is not given by the record.

Asserted by `tests/unit/test_data_samples.py`: the stress maximum, the end of the hold and the relaxation, the compression, the loop's endpoints, closing segment, orientation and enclosed area, the start of necking, the fracture strain, the unloading chords, E with its standard error and its window range, the offset yield, the preload noise, the agreement of the residual rms with E times that noise, and the load-cell stress scale.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the record https://data.nist.gov/od/id/mds2-2202 (licence field https://www.nist.gov/open/license, access level public), read 2026-11-08; https://www.nist.gov/open/license, "Fair Use of Other NIST Data/Works": not subject to copyright in the United States (17 U.S.C. §105), and abroad "the non-exclusive irrevocable and unconditional right to print, publish, prepare derivative works and distribute the NIST data, in any medium" |
| Redistribution of subsets | permitted | the same section: "you may copy and distribute such modifications or works" of "the data or any portion of the data" |
| Publication of figures and derivatives | permitted | the same section: the right to "print, publish, prepare derivative works and distribute" |
| Modification and attribution | permitted with attribution | the same section: modified works "should carry a notice stating that you changed the data and should note the date and nature of any such change"; NIST to be acknowledged explicitly as the source; the data are provided "AS IS". The sample is unmodified; the figure's credit names NIST and the record and says that its fits are this project's |

The card records the licence as `equivalent-permission` (ADR 007 decision 4, "an equivalent recorded permission"): the NIST statement grants, in writing and without condition beyond acknowledgement, everything CC BY 4.0 grants. The record is not Standard Reference Data, so the SRD copyright of the same page does not apply.

## Size, runtime, payload

Sample 132 KB in two files (caps: 2 MB per file, 8 MB per dataset). Figure: about 2 s including the interpreter start on a warm machine (14 s on a cold first run), about 160 MB peak memory; PNG about 220 KB. A lesson page that reads the sample and draws this figure stays inside the 30 s warning, the 60 s limit, and the 3 MB payload. The learner's full download is the same two files (`./scripts/fetch-data.sh nist-numisheet-dp980`). CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected"; sha256 on the card, equal to NIST's |
| 2. Schema, units, calibration, cadence, masks, coverage | "Schema, units, cadence, masks, coverage"; "What the strain and the stress measure"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the fit | "Artifact labels"; the figure draws the fitted and offset lines apart from the points, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/nist_numisheet.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": none per point in the record; the stated noise floor and load-cell difference quoted; E's standard error and window sensitivity derived; calibration qualitative only and stated so |
| 8. This dossier with the decision | this file |

## Open items

- Phase 2, the MAT6 lab, starts only when the owner says so (Issue #421).
- The repeats R02 and R03 (about 130 KB each, same record and rights) would give a repeatability of E, the yield, and the loop area; they are not inspected.
- The runner-up, one cycle cropped from BAM P92 `Data_RF.lis` (CC BY 4.0), is not needed: this file reverses the load.
