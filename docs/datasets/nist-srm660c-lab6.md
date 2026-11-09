# Dossier: NIST SRM 660c (LaB6), the X-ray powder patterns of its certification

Card: `data/registry/nist-srm660c-lab6.yaml`. Inspected 2026-11-09 for F106 (Issue #443), the measured-data lab MAT5; the choice of this record over the runner-up (Exler's mineral mixture, no standard) is in [the dataset research](spike-candidates-2026-11-08.md).

**Decision: go.** Kind: X-ray powder diffraction of a certified line-position standard, 20 specimens, with NIST's model of each pattern. Recorded under the owner's approval of 2026-11-09 on Issue #443 (work towards a `go`, every requirement of ADR 007 checked here); the checklist below names the evidence for each.

## The file inspected

| | |
|---|---|
| Source | NIST record mds2-2315, doi 10.18434/mds2-2315, "Diffraction Data for SRM 660c", version 1.0.1 ("metadata update"; data of 2020-10-29); authors David Black, James Cline, Marcus Mendenhall (NIST); supplement to Black et al., "Certification of Standard Reference Material 660c for powder diffraction", Powder Diffraction 35 (2020) 17–22 |
| File | `srm_660c_cifs_20201029_081700.zip`, 1,719,632 bytes, sha256 `92034d06498161db365420831fe35d91ec18bad4ed17385329a1761658da2c42` (published by NIST in the record's component list and in its `.sha256` file, confirmed on the download) |
| Content | 20 CIFs of 433,012 to 433,026 bytes, `660_cert_cif_mosaic_consensus_<bottle><specimen>.cif` for bottles 100 to 1000 and specimens a and b, and a `__MACOSX` folder of Finder metadata (ignored) |
| Read beside it | the certificate of SRM 660c (issue date 29 October 2015, 5 pages, from https://tsapps.nist.gov/srmext/certificates/660c.pdf): the certified value, the wavelength, the 24 reflections of Table 1, the instrument and the procedure; not committed |
| Accessed | 2026-11-09 |

The certificate states the procedure: ten bottles chosen in a stratified random manner, two specimens prepared from each, and 24 regions of the pattern scanned, each around one reflection between 20° and 150° 2θ, with a count time inversely proportional to the intensity, about 24 h per specimen. The instrument is NIST's divergent-beam diffractometer: a copper tube at 1.8 kW, goniometer radius 217.5 mm, a graphite analyzer after the specimen, a scintillation detector, the specimen spun at 0.5 Hz, the room held to ±0.1 K.

## What a CIF holds

Each CIF has eight data blocks. Four are the same in all files (radiation `Cu K\a`, the detector, the citations, the cell `cell_LaB6_660c` with NIST's refined `_cell_length_a`); four are per specimen: `pd_spec_<id>` (temperature 20.85 °C, a refined vertical specimen displacement), `pd_instr_<id>` (the instrument parameters of NIST's model), and two pattern blocks, each a loop of `_pd_proc_2theta_corrected`, `_pd_proc_intensity_total`, `_pd_proc_ls_weight` on one grid of 5,332 points:

- `pd_proc_<id>_meas`: the measurement, "exactly the raw data sets used for certification" in the CIF's words, given as counts over counting time and their weights.
- `pd_proc_<id>_calc`: NIST's fundamental-parameters model of it, with re-refined instrument parameters: "not the fits actually used in certification ... but give essentially the same results" (the record).

The CIF calls the 2θ "corrected" without saying for what. The specimen displacement is not removed from it: the slope of each specimen's Nelson–Riley line below follows the displacement of its CIF with a correlation of 0.9996.

## Conversion and reader

ADR 007's addendum (Issue #417): a CIF is converted once, outside the build, by a checksum-pinned script.

- Script: `tools/datasets/srm660c_cif_to_csv.py`, standard library only. It refuses any zip but the one of sha256 `92034d06…2c42`, requires exactly the 20 CIFs, requires each pattern block to have three numeric columns and as many rows as its `_pd_proc_number_of_points`, and the measured and calculated blocks to share their 2θ tokens row by row.
- Output: per specimen `660c_<id>.csv` with the columns `two_theta, intensity, weight` of the measured block and `calc_intensity` of the calculated one, every token unchanged; the weight of the calculated block is not carried. `specimens.csv` holds per specimen the temperature, the displacement, NIST's a, and the number of points. The sha256 of every output is on the card; each CSV names its CIF member and that member's sha256 in its first line.
- Check: a second parser, written independently for the inspection, read the 20 CIFs and gave the same numbers as the CSVs in every row.
- Reader: `pbc.data.reference.srm660c.read_pattern` and `read_specimens`, the standard library and NumPy; no dependency is added.

## Schema, units, cadence, masks, coverage

| Item | What the record documents | What this dossier established |
|---|---|---|
| Schema | the CIF dictionary items above | 20 × 5,332 rows; 24 scan windows per specimen (gaps of 1.9 to 7.6° between them), 171 to 276 points each |
| Units | 2θ in degrees, cell length in Å, temperature in °C, displacement in mm (dictionary); weight 1/σ² with σ² = (N + 1)/τ² (the CIF's citation of Mendenhall et al. 2018) | intensity is N/τ: solving the weight for τ gives counting times of 1 to 49 per point, near whole numbers; the CIF does not name the unit of τ, so intensity is "counts per counting time" |
| Cadence | none | steps of 0.008 to 0.016° within a window, wider at high angle; the grids of the specimens differ slightly (adaptive rebinning) |
| Masks, missing values | none stated | none: every value finite, every weight positive, no negative intensity |
| Coverage | 20.3 to 150.908° 2θ per specimen; temperature 20.85 °C | the maximum of each window within 0.07° of the certificate's Table 1 position for its reflection; all 24 reflections from 100 to 511 present in every specimen |
| Model | `_calc` blocks | NIST's model follows the measurement with a mean squared residual of 1.6 to 1.8 counting variances per point |

The parsing test `tests/unit/test_data_srm660c.py::test_srm660c_sample_parses` asserts the field names, shapes, the 24 windows and their steps, the range in degrees, the Poisson form of the weights, the absence of masks, the indexing against Table 1, and the per-specimen items.

## Artifact labels

| Artifact | Type |
|---|---|
| the `_meas` blocks, the columns `two_theta, intensity, weight` | `processed-measured` |
| the `_calc` blocks, the column `calc_intensity`, and NIST's `_cell_length_a` | `modelled-reference` |
| `660c_<id>.csv`, `specimens.csv` | `processed-measured` (with the modelled column named as such) |

The counts are measured, but NIST rebinned them, divided them by the counting time, and "corrected" the angle, so the pattern is labelled processed. The doublet fits, the lattice parameters, and the extrapolation are not artifacts of the record: `pbc.data.reference.srm660c` computes them, and the figure draws them dashed and dotted, apart from the measured points, with residuals.

## Reference figure

```
uv run python -m pbc.data.reference nist-srm660c-lab6 --out lab6.png
```

The code is `src/pbc/data/reference/srm660c.py`. **Status label: processed.** Panels: the 24 scan windows of specimen 100a on a log scale; the 510 reflection with its counting errors, the fitted Kα1 + Kα2 doublet, and NIST's model, and below it the residuals of both in counting errors; a from each reflection of 100a against the Nelson–Riley function, for the measurement and for NIST's model by the same method, with the lines of all 20 specimens meeting near θ = 90°; and the extrapolated a of each specimen beside NIST's refined a and the certified band.

**Caption.** *Lanthanum hexaboride, the NIST line-position standard, measured in 24 windows around its reflections. Bragg's law with the Cu Kα1 wavelength turns each peak into a lattice parameter a; the values fall with the angle because the specimen sits slightly off the focusing circle, and the Nelson–Riley line removes that error at θ = 90°. Over 20 specimens the extrapolated a is 4.156485 Å with a standard deviation of 0.000014 Å, 73 ppm below NIST's own refinement of the same data. The same simple analysis applied to NIST's model pattern, whose a is known, falls short by 74 ppm: the gap is the method's (a symmetric peak shape for an asymmetric instrument profile), not the measurement's, which agrees with the model to 1 ppm.*

**The method.** Per window: a straight background and a Kα1/Kα2 doublet of pseudo-Voigt profiles with one width and one Lorentzian fraction, weighted by the record's weights (`fit_peak`). The Kα2/Kα1 wavelength ratio and height ratio are the medians over the doublets resolved above 2θ = 94° (`free_doublet`), then fixed. d = λ/(2 sin θ) with λ = 1.5405929 Å, a = d √(h² + k² + l²). An ordinary least-squares line of a against cos²θ/sin θ + cos²θ/θ over the 18 reflections above 60° (`extrapolate`), extrapolated to zero. The same steps on NIST's calculated pattern with the measured weights (`analyse_model`).

| Quantity | Value | How |
|---|---|---|
| Kα1 position of 510 in specimen 100a | 141.815° | `fit_peak`; Table 1: 141.780° |
| Fitted positions against Table 1, mean of 20 | −0.007° (100) to +0.038° (511) | higher with the angle: the displacement and the temperature |
| a from one reflection, worst specimen | off by 0.0067 Å (100) falling to 0.0005 Å (511) | the error of the displacement falls with the angle, which is what the extrapolation uses |
| Kα2/Kα1 wavelength ratio | 1.0024799, SD 0.0000015 (20 specimens); λ(Kα2) = 1.544413 Å | resolved doublets; on NIST's model 1.0024812 |
| Kα2/Kα1 height ratio | 0.515, SD 0.002 | the same doublets |
| Reduced χ² of the doublet fits | median 2.4; up to 26 below 2θ = 40°, at most 7.7 above | the symmetric profile misses the low-angle asymmetry |
| **a, measured, Nelson–Riley** | **4.156485 Å, SD 0.000014, standard error 0.0000030** | 20 specimens; range 4.156453 to 4.156508 |
| a, NIST's model, same method | 4.156480 Å, SD 0.000014 | |
| NIST's refined a in the CIFs | 4.156789 Å, SD 0.0000085 (20.85 °C) | `_cell_length_a`, NIST's fundamental-parameters fit |
| Bias of the method on NIST's model | **−74 ppm** (4.156480 against 4.156789) | the model's a is known, so the bias is measured |
| Measured − model, same method | **+1.1 ppm** (+0.0000047 Å, SD 0.0000044) | the comparison the method's bias cancels in |
| Measured against the certified value | −82 ppm, 4.3 times U | certified 4.156826 ± 0.000080 Å (k = 2) at 22.5 °C, no temperature adjustment |
| Statistical error of one intercept (100a) | 0.0000093 Å | the scatter of 18 points about the line |

## Uncertainty and calibration

**Calibration.** The wavelength is the certificate's (Table 1: λ = 0.15405929 nm for Cu Kα; its analysis used the Kα spectrum of Hölzer et al. 1997); the CIFs name the radiation but carry no wavelength, so a lab must take it from the certificate. The material is the calibrant: the certified lattice parameter 0.4156826 nm ± 0.000008 nm (k = 2), Type B dominated, at 22.5 °C, traceable to the SI metre through the Cu Kα emission spectrum. The certificate adjusts NIST's values to 22.5 °C with the thermal expansion of Sirota et al. (1998) but states no coefficient. NIST's own values in these CIFs (20.85 °C) average 8.9 ppm below the certified one, which is what an expansion of 5.4 ppm/K over 1.65 K would give; that coefficient is derived here, not quoted.

**Uncertainty per point.** The record's Poisson weight; σ is shown as the error bar of the peak panel.

**Uncertainty of a.** Three parts, of very different size:

- Repeatability over the 20 specimens: SD 0.000014 Å (3.3 ppm), standard error of the mean 0.0000030 Å. The certificate's Type A expanded uncertainty, from NIST's own analysis, is 0.00000037 nm = 0.0000037 Å (k = 2).
- The statistical error of one specimen's intercept, 0.0000093 Å, is comparable with the spread between specimens.
- **The bias of the method, −74 ppm (−0.00031 Å), dominates.** A symmetric pseudo-Voigt does not describe the instrument's asymmetric profile (axial divergence above all at low angle, the flat specimen, the analyzer), which NIST's fundamental-parameters approach models. Because the same method applied to NIST's model pattern, whose a the CIF states, reproduces the gap, the gap is known and the measurement itself agrees with NIST's model to +1.1 ppm. A simple-fit lab therefore does not reach the certified value within U, and must say so; it can measure its own bias exactly as done here.

Asserted by `tests/unit/test_data_srm660c.py`: the indexing against Table 1, the falling error of single reflections, a and its spread, the model's a by the same method, NIST's a, the bias, the measured-minus-model difference, the distance to the certified value in units of U, NIST's values against the certified one, the correlation of the slope with the displacement, and the Kα2 ratios.

## Rights

| Question | Answer | Source |
|---|---|---|
| Local download | permitted | the record https://data.nist.gov/od/id/mds2-2315 (licence field https://www.nist.gov/open/license, access level public), read 2026-11-09; https://www.nist.gov/open/license, "Fair Use of Other NIST Data/Works": not subject to copyright in the United States (17 U.S.C. §105), and abroad "the non-exclusive irrevocable and unconditional right to print, publish, prepare derivative works and distribute the NIST data, in any medium" |
| Redistribution of subsets | permitted | the same section: "You may improve, modify, and create derivative works of the data or any portion of the data, and you may copy and distribute such modifications or works" |
| Publication of figures and derivatives | permitted | the same section: the right to "print, publish, prepare derivative works and distribute" |
| Modification and attribution | permitted with attribution | the same section: modified works "should carry a notice stating that you changed the data and should note the date and nature of any such change"; NIST to be acknowledged explicitly as the source; provided "AS IS". The sample is the CIFs' values reformatted, with the calculated weights left out; the card's attribution says so and gives the date, and the figure's credit names NIST and the record and says that its fits are this project's |

The card records the licence as `equivalent-permission` (ADR 007 decision 4), as for the NIST Numisheet record of MAT6: the NIST statement grants in writing, with no condition beyond acknowledgement and a notice of change, everything CC BY 4.0 grants. The record is certification data of a Standard Reference *Material*, not Standard Reference *Data*, so the SRD copyright section of the same page does not apply. The certificate is read for its values (the wavelength, the certified a, the reflections); it is not committed or reproduced.

## Size, runtime, payload

Sample 2,964,966 bytes in 21 files, the largest 148,369 bytes (caps: 2 MB per file, 8 MB per dataset); all samples together 20.2 MB after it, of the 32 MB cap. All 20 specimens are committed because the repeatability over them is the measured uncertainty; one specimen alone would leave the lab with only a statistical error. Figure: about 9 s including the interpreter start (40 patterns, 24 windows each, fitted), about 170 MB peak memory; PNG about 410 KB. A lesson page that fits fewer specimens, or all of them once, stays inside the 30 s warning, the 60 s limit, and the 3 MB payload. The learner's full download is the 1.7 MB zip (`./scripts/fetch-data.sh nist-srm660c-lab6`). CI reads only the committed files.

## The requirements of ADR 007 and where they are met

| Requirement | Evidence |
|---|---|
| 1. An actual small file inspected, checksum, size, version | "The file inspected"; sha256 on the card, equal to NIST's |
| 2. Schema, units, calibration, cadence, masks, coverage | "What a CIF holds"; "Schema, units, cadence, masks, coverage"; "Uncertainty and calibration"; the parsing test |
| 3. Every artifact labelled, measurement apart from the model | "Artifact labels"; the figure draws the fit and NIST's model apart from the points, with residuals |
| 4. Reproducible reference figure from source-controlled code | `src/pbc/data/reference/srm660c.py`, regenerated from the committed sample; `tests/unit/test_data_plotting.py` checks its status and conventions |
| 5. Rights, four answers with their source | "Rights"; the card's `rights` |
| 6. Download, build time, payload | "Size, runtime, payload" |
| 7. Uncertainty and calibration | "Uncertainty and calibration": Poisson weights per point; the certified value and wavelength as the calibration; repeatability over 20 specimens; the method's bias measured on NIST's model |
| 8. This dossier with the decision | this file |
| Format (addendum of #417) | CIF converted once by `tools/datasets/srm660c_cif_to_csv.py`; input and output checksums on the card, in the script, and in `tools/datasets/README.md` |

## Open items

- Phase 2, the MAT5 lab, starts only when the owner says so (Issue #443).
- **Where the Bragg model lives** (the open point of the Issue): MAT1 is a lesson on the dispersion of a one-dimensional chain, so Bragg's law, the indexing of a cubic lattice, and the Nelson–Riley extrapolation are not in the course yet. For the lab, either MAT5 introduces them itself or a lesson before it does; a decision for Phase 2 and the owner, not for this gate.
- The temperature: the CIFs give 20.85 °C and the certified value is at 22.5 °C; the certificate cites the thermal expansion but gives no coefficient. A lab that compares with the certified value must say that its own adjustment, if any, is its own.
- The meaning of "corrected" in `_pd_proc_2theta_corrected` is not stated in the record; the analysis shows that the specimen displacement is still in it.
